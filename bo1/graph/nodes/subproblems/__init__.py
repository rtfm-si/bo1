"""Parallel sub-problems execution nodes.

This package contains nodes for parallel sub-problem execution:
- analyze_dependencies_node: Analyzes dependencies and creates execution batches
- parallel_subproblems_node: Executes independent sub-problems in parallel
- Speculative parallelization: Allows dependent sub-problems to start early

Modules:
- batch.py: Batch-mode execution (_run_single_subproblem, _execute_batch)
- speculative.py: Speculative parallel execution
"""

import asyncio
import logging
from typing import Any

from bo1.graph.deliberation import (
    deliberate_subproblem as _deliberate_subproblem_impl,
)
from bo1.graph.deliberation import (
    topological_batch_sort as _topological_batch_sort,
)
from bo1.graph.nodes.subproblems.batch import _execute_batch, _run_single_subproblem
from bo1.graph.nodes.subproblems.speculative import (
    _execute_speculative_parallel,
    _get_dependency_indices,
    _run_subproblem_speculative,
)
from bo1.graph.nodes.utils import log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_parallel_state,
    get_problem_state,
)
from bo1.graph.utils import ensure_metrics
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationPhase, SubProblemResult
from bo1.utils.checkpoint_helpers import get_attr_safe

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = [
    "topological_batch_sort",
    "analyze_dependencies_node",
    "_deliberate_subproblem",
    "_run_single_subproblem",
    "_execute_batch",
    "_get_dependency_indices",
    "_run_subproblem_speculative",
    "_execute_speculative_parallel",
    "_parallel_subproblems_subgraph",
    "parallel_subproblems_node",
]


def topological_batch_sort(sub_problems: list[SubProblem]) -> list[list[int]]:
    """Sort sub-problems into execution batches respecting dependencies.

    Delegates to bo1.graph.deliberation.batch_sort.topological_batch_sort.

    Returns list of batches, where each batch contains indices of
    sub-problems that can run in parallel.

    Args:
        sub_problems: List of SubProblem objects with dependencies

    Returns:
        List of batches, where each batch is a list of sub-problem indices
        that can be executed in parallel

    Raises:
        ValueError: If circular dependency detected
    """
    return _topological_batch_sort(sub_problems)


async def analyze_dependencies_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Analyze sub-problem dependencies and create execution batches.

    This node runs after decomposition to determine which sub-problems
    can be executed in parallel vs sequentially.

    Args:
        state: Current graph state (must have problem with sub_problems)

    Returns:
        Dictionary with state updates:
        - execution_batches: List of batches (each batch = list of sub-problem indices)
        - parallel_mode: Boolean indicating if any batches have >1 sub-problem
    """
    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)

    session_id = core_state.get("session_id")
    request_id = core_state.get("request_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "analyze_dependencies_node: Starting dependency analysis",
        request_id=request_id,
    )

    problem = problem_state.get("problem")
    if not problem:
        raise ValueError("analyze_dependencies_node called without problem")

    # Handle both dict (from checkpoint) and Problem object
    sub_problems_raw = get_attr_safe(problem, "sub_problems", [])

    # Normalize sub_problems to SubProblem objects (may be dicts after checkpoint recovery)
    sub_problems: list[SubProblem] = []
    for sp in sub_problems_raw:
        if isinstance(sp, dict):
            sub_problems.append(SubProblem.model_validate(sp))
        else:
            sub_problems.append(sp)

    # Single sub-problem: use sequential mode
    if len(sub_problems) <= 1:
        first_sub_problem = sub_problems[0] if sub_problems else None
        logger.info(
            f"analyze_dependencies_node: Sequential mode (sub_problems={len(sub_problems)})"
        )
        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
            "current_sub_problem": first_sub_problem,
            "current_node": "analyze_dependencies",
        }

    # Perform topological sort to find execution batches
    try:
        batches = topological_batch_sort(sub_problems)

        # Check if any batch has more than 1 sub-problem (actual parallelism)
        has_parallelism = any(len(batch) > 1 for batch in batches)

        # CRITICAL: Use subgraph execution for ALL multi-sub-problem scenarios
        use_subgraph = len(sub_problems) > 1

        logger.info(
            f"analyze_dependencies_node: Complete - {len(batches)} batches, "
            f"has_parallelism={has_parallelism}, use_subgraph={use_subgraph}, batches={batches}"
        )

        # BUG FIX (P0 #1): ALWAYS set current_sub_problem when NOT using subgraph
        first_sub_problem = None
        if not use_subgraph and sub_problems:
            first_sub_problem = sub_problems[0]
            logger.info(
                f"analyze_dependencies_node: Sequential mode - set current_sub_problem={first_sub_problem.id}"
            )

        return {
            "execution_batches": batches,
            "parallel_mode": use_subgraph,
            "current_sub_problem": first_sub_problem,
            "current_node": "analyze_dependencies",
        }

    except ValueError as e:
        # Circular dependency detected
        log_with_session(
            logger,
            logging.ERROR,
            session_id,
            f"analyze_dependencies_node: {e}. Falling back to sequential execution.",
            request_id=request_id,
        )

        first_sub_problem = sub_problems[0] if sub_problems else None

        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
            "current_sub_problem": first_sub_problem,
            "dependency_error": str(e),
            "current_node": "analyze_dependencies",
        }


async def _deliberate_subproblem(
    sub_problem: SubProblem,
    problem: Problem,
    all_personas: list[PersonaProfile],
    previous_results: list[SubProblemResult],
    sub_problem_index: int,
    user_id: str | None = None,
    event_bridge: Any | None = None,
) -> SubProblemResult:
    """Run complete deliberation for a single sub-problem.

    This encapsulates the full deliberation lifecycle.
    Designed to be called in parallel for independent sub-problems.

    Args:
        sub_problem: The sub-problem to deliberate
        problem: The parent problem (for context)
        all_personas: Available personas (persona selection will choose subset)
        previous_results: Results from previously completed sub-problems
        sub_problem_index: Index of this sub-problem (0-based)
        user_id: Optional user ID for context persistence
        event_bridge: Optional EventBridge for emitting real-time events

    Returns:
        SubProblemResult with synthesis, votes, costs, and expert summaries
    """
    return await _deliberate_subproblem_impl(
        sub_problem=sub_problem,
        problem=problem,
        all_personas=all_personas,
        previous_results=previous_results,
        sub_problem_index=sub_problem_index,
        user_id=user_id,
        event_bridge=event_bridge,
    )


async def _parallel_subproblems_subgraph(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute sub-problems using LangGraph subgraphs with real-time streaming.

    Supports two execution modes:
    1. Batch execution (default): Batches execute sequentially, SPs within batch in parallel
    2. Speculative execution (ENABLE_SPECULATIVE_PARALLELISM=true): All SPs start concurrently

    Args:
        state: Current graph state (must have execution_batches, problem)

    Returns:
        Dictionary with state updates
    """
    from langgraph.config import get_stream_writer

    from bo1.data import get_active_personas
    from bo1.feature_flags import EARLY_START_THRESHOLD, ENABLE_SPECULATIVE_PARALLELISM
    from bo1.graph.deliberation.subgraph import get_subproblem_graph

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)
    parallel_state = get_parallel_state(state)

    request_id = core_state.get("request_id") or "no-request-id"
    logger.info(f"[{request_id}] _parallel_subproblems_subgraph: Starting")

    writer = get_stream_writer()
    problem = problem_state.get("problem")
    if not problem:
        raise ValueError("_parallel_subproblems_subgraph called without problem")

    session_id = core_state.get("session_id")
    user_id = core_state.get("user_id")

    # Handle dict (from checkpoint recovery) vs Problem object
    if isinstance(problem, dict):
        sub_problems_raw = problem.get("sub_problems", [])
        problem = Problem.model_validate(problem)
    else:
        sub_problems_raw = problem.sub_problems

    # Normalize sub_problems to SubProblem objects
    sub_problems: list[SubProblem] = []
    for sp in sub_problems_raw:
        if isinstance(sp, dict):
            sub_problems.append(SubProblem.model_validate(sp))
        else:
            sub_problems.append(sp)
    problem.sub_problems = sub_problems

    all_personas = [PersonaProfile.model_validate(p) for p in get_active_personas()]
    subproblem_graph = get_subproblem_graph()

    # Check if we should use speculative parallelization
    has_dependencies = any(sp.dependencies for sp in sub_problems)
    use_speculative = ENABLE_SPECULATIVE_PARALLELISM and has_dependencies and len(sub_problems) > 1

    all_results: list[SubProblemResult] = []

    if use_speculative:
        logger.info(
            f"_parallel_subproblems_subgraph: Using SPECULATIVE execution "
            f"(early_start_threshold={EARLY_START_THRESHOLD})"
        )

        all_results = await _execute_speculative_parallel(
            sub_problems=sub_problems,
            subproblem_graph=subproblem_graph,
            session_id=session_id,
            problem=problem,
            all_personas=all_personas,
            user_id=user_id,
            writer=writer,
            early_start_threshold=EARLY_START_THRESHOLD,
        )
    else:
        execution_batches: list[list[int]] = parallel_state.get("execution_batches", [])
        if not execution_batches:
            execution_batches = [[i] for i in range(len(sub_problems))]

        total_batches = len(execution_batches)
        logger.info(
            f"_parallel_subproblems_subgraph: Using BATCH execution "
            f"({total_batches} batches for {len(sub_problems)} sub-problems)"
        )

        for batch_idx, batch in enumerate(execution_batches):
            batch_results = await _execute_batch(
                batch,
                batch_idx,
                total_batches,
                sub_problems,
                subproblem_graph,
                session_id,
                problem,
                all_personas,
                all_results,
                user_id,
                writer,
            )
            all_results.extend(batch_results)

    # Emit completion event
    total_cost = sum(r.cost for r in all_results)
    total_contributions = sum(r.contribution_count for r in all_results)

    logger.info(
        f"[{request_id}] Complete: {len(all_results)} sub-problems, "
        f"{total_contributions} contributions, ${total_cost:.4f}"
    )

    writer(
        {
            "event_type": "all_subproblems_complete",
            "total_sub_problems": len(all_results),
            "total_contributions": total_contributions,
            "total_cost": total_cost,
            "sub_problem_ids": [r.sub_problem_id for r in all_results],
            "execution_mode": "speculative" if use_speculative else "batch",
        }
    )

    await asyncio.sleep(0.1)  # Ensure event is flushed

    metrics = ensure_metrics(state)
    for result in all_results:
        metrics.total_cost += result.cost

    return {
        "sub_problem_results": all_results,
        "current_sub_problem": None,
        "phase": DeliberationPhase.SYNTHESIS,
        "metrics": metrics,
        "current_node": "parallel_subproblems",
    }


async def parallel_subproblems_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute independent sub-problems in parallel using subgraph implementation.

    This node implements the core parallel sub-problem execution strategy:
    1. Reads execution_batches from state (computed by analyze_dependencies_node)
    2. For each batch, runs all sub-problems in that batch concurrently
    3. Passes completed results to next batch (for expert memory)
    4. Returns all SubProblemResult objects

    Args:
        state: Current graph state (must have execution_batches, problem)

    Returns:
        Dictionary with state updates
    """
    return await _parallel_subproblems_subgraph(state)
