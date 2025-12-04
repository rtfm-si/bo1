"""Parallel sub-problems execution nodes.

This module contains nodes for parallel sub-problem execution:
- analyze_dependencies_node: Analyzes dependencies and creates execution batches
- parallel_subproblems_node: Executes independent sub-problems in parallel
"""

import asyncio
import logging
import time
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from bo1.graph.deliberation import (
    deliberate_subproblem as _deliberate_subproblem_impl,
)
from bo1.graph.deliberation import (
    topological_batch_sort as _topological_batch_sort,
)
from bo1.graph.deliberation.subgraph.state import (
    SubProblemGraphState,
)
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationPhase, SubProblemResult

logger = logging.getLogger(__name__)


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

    Examples:
        If sub-problems are: [A (no deps), B (depends on A), C (no deps)]
        Then execution_batches = [[0, 2], [1]]  # A and C parallel, then B
        And parallel_mode = True (batch 0 has 2 sub-problems)
    """
    from bo1.feature_flags.features import ENABLE_PARALLEL_SUBPROBLEMS

    logger.info("analyze_dependencies_node: Starting dependency analysis")

    problem = state.get("problem")
    if not problem:
        raise ValueError("analyze_dependencies_node called without problem")

    sub_problems = problem.sub_problems

    # Check if parallel sub-problems feature is enabled
    if not ENABLE_PARALLEL_SUBPROBLEMS or len(sub_problems) <= 1:
        # Sequential mode or single sub-problem
        logger.info(
            f"analyze_dependencies_node: Sequential mode "
            f"(feature_flag={ENABLE_PARALLEL_SUBPROBLEMS}, sub_problems={len(sub_problems)})"
        )
        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
            "current_node": "analyze_dependencies",
        }

    # Perform topological sort to find execution batches
    try:
        batches = topological_batch_sort(sub_problems)

        # Check if any batch has more than 1 sub-problem (actual parallelism)
        has_parallelism = any(len(batch) > 1 for batch in batches)

        # CRITICAL: Use subgraph execution for ALL multi-sub-problem scenarios,
        # not just when there's true parallelism. This ensures:
        # 1. all_subproblems_complete event is emitted BEFORE meta-synthesis
        # 2. Synthesis doesn't happen after each individual sub-problem
        # 3. Proper event streaming via get_stream_writer()
        use_subgraph = len(sub_problems) > 1

        logger.info(
            f"analyze_dependencies_node: Complete - {len(batches)} batches, "
            f"has_parallelism={has_parallelism}, use_subgraph={use_subgraph}, batches={batches}"
        )

        return {
            "execution_batches": batches,
            "parallel_mode": use_subgraph,  # Route to subgraph for any multi-sub-problem case
            "current_node": "analyze_dependencies",
        }

    except ValueError as e:
        # Circular dependency detected
        logger.error(f"analyze_dependencies_node: {e}. Falling back to sequential execution.")

        # Fallback: execute all sub-problems sequentially
        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
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
    event_bridge: Any | None = None,  # EventBridge | None (avoid circular import)
) -> SubProblemResult:
    """Run complete deliberation for a single sub-problem.

    This encapsulates the full deliberation lifecycle:
    - Persona selection for this specific sub-problem
    - Initial round
    - Multi-round deliberation (up to 6 rounds)
    - Convergence checking
    - Voting/recommendations collection
    - Synthesis generation

    This function is designed to be called in parallel for independent sub-problems.

    Args:
        sub_problem: The sub-problem to deliberate
        problem: The parent problem (for context)
        all_personas: Available personas (persona selection will choose subset)
        previous_results: Results from previously completed sub-problems (for expert memory)
        sub_problem_index: Index of this sub-problem (0-based) for event tracking
        user_id: Optional user ID for context persistence
        event_bridge: Optional EventBridge for emitting real-time events during parallel execution

    Returns:
        SubProblemResult with synthesis, votes, costs, and expert summaries

    Example:
        >>> # Parallel execution of independent sub-problems
        >>> tasks = [
        ...     _deliberate_subproblem(sp1, problem, personas, []),
        ...     _deliberate_subproblem(sp2, problem, personas, []),
        ... ]
        >>> results = await asyncio.gather(*tasks)
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

    NEW IMPLEMENTATION: Uses get_stream_writer() for per-expert event streaming.

    Key improvements over legacy EventBridge approach:
    - contribution_started fires BEFORE LLM call (instant feedback)
    - contribution fires AFTER LLM call (with content)
    - No more 3-5 minute UI blackouts
    - Single event system (no EventBridge/EventCollector duality)

    Args:
        state: Current graph state (must have execution_batches, problem)

    Returns:
        Dictionary with state updates
    """
    from langgraph.config import get_stream_writer

    from bo1.graph.deliberation.subgraph import (
        build_expert_memory,
        create_subproblem_initial_state,
        get_subproblem_graph,
        result_from_subgraph_state,
    )

    logger.info("_parallel_subproblems_subgraph: Starting subgraph-based parallel execution")

    writer = get_stream_writer()
    problem = state.get("problem")
    if not problem:
        raise ValueError("_parallel_subproblems_subgraph called without problem")

    session_id = state.get("session_id")
    user_id = state.get("user_id")

    execution_batches = state.get("execution_batches", [])
    if not execution_batches:
        logger.warning("No execution_batches in state, creating sequential batches")
        execution_batches = [[i] for i in range(len(problem.sub_problems))]

    sub_problems = problem.sub_problems

    # Get all available personas for selection
    from bo1.data import get_active_personas

    all_personas_dicts = get_active_personas()
    all_personas = [PersonaProfile.model_validate(p) for p in all_personas_dicts]

    # Track all results across batches
    all_results: list[SubProblemResult] = []
    total_batches = len(execution_batches)

    # Get the compiled subgraph (singleton for efficiency)
    subproblem_graph = get_subproblem_graph()

    logger.info(
        f"_parallel_subproblems_subgraph: Executing {total_batches} batches for {len(sub_problems)} sub-problems"
    )

    # Execute batches sequentially, sub-problems within batch in parallel
    for batch_idx, batch in enumerate(execution_batches):
        logger.info(
            f"_parallel_subproblems_subgraph: Starting batch {batch_idx + 1}/{total_batches} with {len(batch)} sub-problems"
        )

        # Emit batch_started event
        writer(
            {
                "event_type": "batch_started",
                "batch_index": batch_idx,
                "total_batches": total_batches,
                "sub_problem_indices": batch,
            }
        )

        # Build expert memory from previous results
        expert_memory = build_expert_memory(all_results)

        # Create tasks for all sub-problems in this batch
        async def run_subproblem(
            sp_index: int, expert_memory: dict[str, Any] = expert_memory
        ) -> tuple[int, SubProblemResult, float]:
            """Run a single sub-problem through the subgraph."""
            if sp_index >= len(sub_problems):
                raise ValueError(f"Invalid sub-problem index {sp_index}")

            sub_problem = sub_problems[sp_index]
            start_time = time.time()

            # Emit subproblem_started event
            writer(
                {
                    "event_type": "subproblem_started",
                    "sub_problem_index": sp_index,
                    "sub_problem_id": sub_problem.id,
                    "goal": sub_problem.goal,
                    "total_sub_problems": len(sub_problems),
                }
            )

            # Create initial state for subgraph
            sp_state = create_subproblem_initial_state(
                session_id=session_id or f"subproblem_{sub_problem.id}",
                sub_problem=sub_problem,
                sub_problem_index=sp_index,
                parent_problem=problem,
                all_available_personas=all_personas,
                expert_memory=expert_memory,
                user_id=user_id,
            )

            # Execute subgraph with unique thread_id
            config: RunnableConfig = {
                "configurable": {
                    "thread_id": f"{session_id}:subproblem:{sp_index}",
                },
                "recursion_limit": 50,
            }

            # Run the subgraph - events stream via get_stream_writer() in nodes
            final_state = await subproblem_graph.ainvoke(sp_state, config=config)

            # Extract result
            result = result_from_subgraph_state(cast(SubProblemGraphState, final_state))
            duration = time.time() - start_time

            # Update duration (not available in subgraph state)
            result = SubProblemResult(
                sub_problem_id=result.sub_problem_id,
                sub_problem_goal=result.sub_problem_goal,
                synthesis=result.synthesis,
                votes=result.votes,
                contribution_count=result.contribution_count,
                cost=result.cost,
                duration_seconds=duration,
                expert_panel=result.expert_panel,
                expert_summaries=result.expert_summaries,
            )

            # Emit subproblem_complete event
            writer(
                {
                    "event_type": "subproblem_complete",
                    "sub_problem_index": sp_index,
                    "goal": result.sub_problem_goal,
                    "synthesis": result.synthesis,
                    "recommendations_count": len(result.votes),
                    "expert_panel": result.expert_panel,
                    "contribution_count": result.contribution_count,
                    "cost": result.cost,
                    "duration_seconds": duration,
                }
            )

            return sp_index, result, duration

        # Execute batch in parallel
        batch_tasks = [run_subproblem(sp_idx) for sp_idx in batch]
        batch_results_raw = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process results
        batch_results: list[tuple[int, SubProblemResult]] = []
        failed_count = 0

        for raw_result in batch_results_raw:
            if isinstance(raw_result, BaseException):
                failed_count += 1
                logger.error(f"_parallel_subproblems_subgraph: Sub-problem failed: {raw_result}")
                # Emit error event
                writer(
                    {
                        "event_type": "subproblem_failed",
                        "error": str(raw_result),
                        "error_type": type(raw_result).__name__,
                    }
                )
            else:
                # Type is now narrowed to tuple[int, SubProblemResult, float]
                sp_index, sp_result, _ = raw_result
                batch_results.append((sp_index, sp_result))

        # Emit batch_complete event
        writer(
            {
                "event_type": "batch_complete",
                "batch_index": batch_idx,
                "succeeded": len(batch_results),
                "failed": failed_count,
            }
        )

        # If any failed, raise error
        if failed_count > 0:
            raise RuntimeError(f"{failed_count} sub-problem(s) failed in batch {batch_idx}")

        # Add to all_results in order
        for _sp_index, result in sorted(batch_results, key=lambda x: x[0]):
            all_results.append(result)

        logger.info(
            f"_parallel_subproblems_subgraph: Batch {batch_idx + 1}/{total_batches} complete"
        )

    # Calculate totals
    total_cost = sum(r.cost for r in all_results)
    total_contributions = sum(r.contribution_count for r in all_results)

    logger.info(
        f"_parallel_subproblems_subgraph: Complete - {len(all_results)} sub-problems, "
        f"{total_contributions} contributions, ${total_cost:.4f}"
    )

    # ISSUE FIX #1: Emit all_subproblems_complete event as synchronization barrier
    # This ensures the frontend knows all sub-problems are done before meta-synthesis starts
    writer(
        {
            "event_type": "all_subproblems_complete",
            "total_sub_problems": len(all_results),
            "total_contributions": total_contributions,
            "total_cost": total_cost,
            "sub_problem_ids": [r.sub_problem_id for r in all_results],
        }
    )

    # Small delay to ensure event is flushed before transitioning to meta-synthesis
    await asyncio.sleep(0.1)

    # Update metrics
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


# AUDIT FIX (Priority 4, Task 4.2): Deleted _parallel_subproblems_legacy function (lines 407-597)
# Legacy implementation removed - USE_SUBGRAPH_DELIBERATION is now always enabled


# AUDIT FIX (Priority 4, Task 4.2): Removed router and legacy implementation
# Directly use subgraph implementation (USE_SUBGRAPH_DELIBERATION confirmed stable)
async def parallel_subproblems_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute independent sub-problems in parallel using subgraph implementation.

    AUDIT FIX (Priority 4, Task 4.2): Renamed from _parallel_subproblems_subgraph
    and removed legacy fallback. USE_SUBGRAPH_DELIBERATION is now always enabled.

    This node implements the core parallel sub-problem execution strategy:
    1. Reads execution_batches from state (computed by analyze_dependencies_node)
    2. For each batch, runs all sub-problems in that batch concurrently
    3. Passes completed results to next batch (for expert memory)
    4. Returns all SubProblemResult objects

    Batching respects dependencies: sub-problems in batch N can depend on
    results from batches 0..N-1, but not on other sub-problems in batch N.

    Args:
        state: Current graph state (must have execution_batches, problem)

    Returns:
        Dictionary with state updates:
        - sub_problem_results: All results from all batches
        - current_sub_problem: None (all complete)
        - phase: SYNTHESIS (ready for meta-synthesis)

    Example:
        Given execution_batches = [[0, 1], [2]]:
        - Batch 0: Deliberate sub-problems 0 and 1 in parallel
        - Batch 1: Deliberate sub-problem 2 (can reference results from 0, 1)
        - Return all 3 results
    """
    # AUDIT FIX (Priority 4, Task 4.2): Direct implementation without router
    return await _parallel_subproblems_subgraph(state)
