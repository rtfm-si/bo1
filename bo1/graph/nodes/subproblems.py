"""Parallel sub-problems execution nodes.

This module contains nodes for parallel sub-problem execution:
- analyze_dependencies_node: Analyzes dependencies and creates execution batches
- parallel_subproblems_node: Executes independent sub-problems in parallel
- Speculative parallelization: Allows dependent sub-problems to start early

Speculative Parallelization (ENABLE_SPECULATIVE_PARALLELISM=true):
Instead of strict batch-by-batch execution, dependent sub-problems can start
when their dependencies reach the early start threshold (default: round 2).
This provides 40-60% time savings over sequential execution.

Example with dependencies SP0 -> SP1 -> SP2:
- Traditional: [SP0 completes] -> [SP1 completes] -> [SP2 completes] = 10 min
- Speculative: [SP0 starts] -> [SP0 round 2, SP1 starts] -> [SP0 complete, SP1 round 2, SP2 starts] = ~5 min
"""

import asyncio
import logging
import time
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from bo1.graph.deliberation import (
    PartialContextProvider,
)
from bo1.graph.deliberation import (
    deliberate_subproblem as _deliberate_subproblem_impl,
)
from bo1.graph.deliberation import (
    topological_batch_sort as _topological_batch_sort,
)
from bo1.graph.deliberation.context import extract_recommendation_from_synthesis
from bo1.graph.deliberation.subgraph.state import SubProblemGraphState
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
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
    if isinstance(problem, dict):
        sub_problems_raw = problem.get("sub_problems", [])
    else:
        sub_problems_raw = problem.sub_problems

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

        # BUG FIX (P0 #1): ALWAYS set current_sub_problem when NOT using subgraph
        # This fixes the crash when resuming after clarification in sequential mode.
        # When use_subgraph=False, we route to select_personas which requires current_sub_problem.
        first_sub_problem = None
        if not use_subgraph and sub_problems:
            first_sub_problem = sub_problems[0]  # Already normalized to SubProblem
            logger.info(
                f"analyze_dependencies_node: Sequential mode - set current_sub_problem={first_sub_problem.id}"
            )

        return {
            "execution_batches": batches,
            "parallel_mode": use_subgraph,  # Route to subgraph for any multi-sub-problem case
            "current_sub_problem": first_sub_problem,  # BUG FIX: Set for sequential mode
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

        # BUG FIX (P0 #1): Also set current_sub_problem in fallback case
        first_sub_problem = sub_problems[0] if sub_problems else None  # Already normalized

        # Fallback: execute all sub-problems sequentially
        return {
            "execution_batches": [[i] for i in range(len(sub_problems))],
            "parallel_mode": False,
            "current_sub_problem": first_sub_problem,  # BUG FIX: Set for sequential fallback
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


async def _run_single_subproblem(
    sp_index: int,
    sub_problems: list[Any],
    subproblem_graph: Any,
    session_id: str | None,
    problem: Any,
    all_personas: list[PersonaProfile],
    expert_memory: dict[str, Any],
    user_id: str | None,
    writer: Any,
) -> tuple[int, SubProblemResult, float]:
    """Execute a single sub-problem through the subgraph.

    Args:
        sp_index: Index of the sub-problem to execute
        sub_problems: List of all sub-problems
        subproblem_graph: Compiled LangGraph subgraph
        session_id: Session ID for thread configuration
        problem: Parent problem object
        all_personas: Available personas for expert selection
        expert_memory: Context from previous sub-problems
        user_id: User ID for context
        writer: Stream writer for events

    Returns:
        Tuple of (index, result, duration)
    """
    from bo1.graph.deliberation.subgraph import (
        create_subproblem_initial_state,
        result_from_subgraph_state,
    )

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
    # CRITICAL: Use astream() instead of ainvoke() to capture custom events
    # from get_stream_writer() calls in subgraph nodes (contribution, convergence, etc.)
    config: RunnableConfig = {
        "configurable": {"thread_id": f"{session_id}:subproblem:{sp_index}"},
        "recursion_limit": 50,
    }

    # Stream with custom events to forward contribution/convergence events to parent
    final_state = None
    async for chunk in subproblem_graph.astream(
        sp_state, config=config, stream_mode=["updates", "custom"]
    ):
        mode, data = chunk
        if mode == "custom" and isinstance(data, dict) and "event_type" in data:
            # Forward custom events from subgraph to parent's stream writer
            # This enables real-time contribution/convergence events to reach the frontend
            writer(data)
        elif mode == "updates" and isinstance(data, dict):
            # Capture the last state update (final state)
            for _node_name, node_output in data.items():
                final_state = node_output

    # Ensure we have a final state
    if final_state is None:
        raise RuntimeError(f"Subgraph {sp_index} completed without producing final state")

    result = result_from_subgraph_state(cast(SubProblemGraphState, final_state))
    duration = time.time() - start_time
    emit_node_duration(f"subproblem_{sp_index}", duration * 1000)

    # Update duration and cache extracted recommendation (not available in subgraph state)
    extracted_rec = extract_recommendation_from_synthesis(result.synthesis)
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
        extracted_recommendation=extracted_rec,
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


async def _execute_batch(
    batch: list[int],
    batch_idx: int,
    total_batches: int,
    sub_problems: list[Any],
    subproblem_graph: Any,
    session_id: str | None,
    problem: Any,
    all_personas: list[PersonaProfile],
    all_results: list[SubProblemResult],
    user_id: str | None,
    writer: Any,
) -> list[SubProblemResult]:
    """Execute a batch of sub-problems in parallel.

    Args:
        batch: List of sub-problem indices to execute
        batch_idx: Index of this batch
        total_batches: Total number of batches
        sub_problems: List of all sub-problems
        subproblem_graph: Compiled LangGraph subgraph
        session_id: Session ID
        problem: Parent problem
        all_personas: Available personas
        all_results: Results from previous batches (for context)
        user_id: User ID
        writer: Stream writer for events

    Returns:
        List of results from this batch
    """
    from bo1.graph.deliberation.subgraph import build_expert_memory

    logger.info(f"Batch {batch_idx + 1}/{total_batches}: Starting {len(batch)} sub-problems")

    writer(
        {
            "event_type": "batch_started",
            "batch_index": batch_idx,
            "total_batches": total_batches,
            "sub_problem_indices": batch,
        }
    )

    expert_memory = build_expert_memory(all_results)

    # Execute all sub-problems in batch in parallel
    batch_tasks = [
        _run_single_subproblem(
            sp_idx,
            sub_problems,
            subproblem_graph,
            session_id,
            problem,
            all_personas,
            expert_memory,
            user_id,
            writer,
        )
        for sp_idx in batch
    ]
    batch_results_raw = await asyncio.gather(*batch_tasks, return_exceptions=True)

    # Process results
    batch_results: list[tuple[int, SubProblemResult]] = []
    failed_count = 0

    for idx, raw_result in enumerate(batch_results_raw):
        sp_idx = batch[idx]  # Get actual sub-problem index from batch
        if isinstance(raw_result, BaseException):
            failed_count += 1
            log_with_session(
                logger,
                logging.ERROR,
                session_id,
                f"Sub-problem failed: {raw_result}",
                sub_problem_index=sp_idx,
            )
            writer(
                {
                    "event_type": "subproblem_failed",
                    "error": str(raw_result),
                    "error_type": type(raw_result).__name__,
                    "sub_problem_index": sp_idx,
                }
            )
        else:
            sp_index, sp_result, _ = raw_result
            batch_results.append((sp_index, sp_result))

    writer(
        {
            "event_type": "batch_complete",
            "batch_index": batch_idx,
            "succeeded": len(batch_results),
            "failed": failed_count,
        }
    )

    if failed_count > 0:
        raise RuntimeError(f"{failed_count} sub-problem(s) failed in batch {batch_idx}")

    logger.info(f"Batch {batch_idx + 1}/{total_batches}: Complete")
    return [result for _, result in sorted(batch_results, key=lambda x: x[0])]


def _get_dependency_indices(
    sub_problems: list[SubProblem],
) -> dict[int, list[int]]:
    """Map each sub-problem index to its dependency indices.

    Args:
        sub_problems: List of sub-problems with dependencies

    Returns:
        Dictionary mapping sp_index -> list of dependency sp_indices
    """
    id_to_idx = {sp.id: i for i, sp in enumerate(sub_problems)}
    dep_map: dict[int, list[int]] = {}

    for i, sp in enumerate(sub_problems):
        dep_indices = []
        for dep_id in sp.dependencies:
            if dep_id in id_to_idx:
                dep_indices.append(id_to_idx[dep_id])
        dep_map[i] = dep_indices

    return dep_map


async def _run_subproblem_speculative(
    sp_index: int,
    sub_problems: list[SubProblem],
    subproblem_graph: Any,
    session_id: str | None,
    problem: Problem,
    all_personas: list[PersonaProfile],
    user_id: str | None,
    writer: Any,
    context_provider: PartialContextProvider,
    dependency_indices: list[int],
    max_rounds: int = 6,
) -> tuple[int, SubProblemResult, float]:
    """Execute a single sub-problem with speculative dependency waiting.

    This function:
    1. Waits for dependencies to reach the early start threshold (not full completion)
    2. Gets partial context from in-progress dependencies
    3. Starts execution with available context
    4. Updates the context provider as rounds complete
    5. Gets full context when dependencies complete (for later rounds)

    Args:
        sp_index: Index of the sub-problem to execute
        sub_problems: List of all sub-problems
        subproblem_graph: Compiled LangGraph subgraph
        session_id: Session ID for thread configuration
        problem: Parent problem object
        all_personas: Available personas for expert selection
        user_id: User ID for context
        writer: Stream writer for events
        context_provider: Shared context provider for cross-SP communication
        dependency_indices: Indices of sub-problems this one depends on
        max_rounds: Maximum deliberation rounds

    Returns:
        Tuple of (index, result, duration)
    """
    from bo1.graph.deliberation.subgraph import (
        create_subproblem_initial_state,
        result_from_subgraph_state,
    )

    sub_problem = sub_problems[sp_index]
    start_time = time.time()

    # Register with context provider
    await context_provider.register_subproblem(
        sp_index=sp_index,
        sp_id=sub_problem.id,
        goal=sub_problem.goal,
        max_rounds=max_rounds,
    )

    # Wait for dependencies to be ready (reach early start threshold)
    if dependency_indices:
        logger.info(
            f"Sub-problem {sp_index}: Waiting for dependencies {dependency_indices} "
            f"to reach round {context_provider.get_early_start_threshold()}"
        )
        writer(
            {
                "event_type": "subproblem_waiting",
                "sub_problem_index": sp_index,
                "waiting_for": dependency_indices,
                "threshold": context_provider.get_early_start_threshold(),
            }
        )

        await context_provider.wait_for_ready(
            dependency_indices=dependency_indices,
            timeout=600.0,  # 10 minute max wait
        )

        logger.info(f"Sub-problem {sp_index}: Dependencies ready, starting execution")

    # Get partial context from dependencies
    partial_context = await context_provider.get_partial_context(
        sp_index=sp_index,
        dependency_indices=dependency_indices,
    )

    # Build expert memory from partial context
    expert_memory: dict[str, str] = {}
    if partial_context.available_context:
        # Add dependency context to all experts
        expert_memory["__dependency_context__"] = partial_context.available_context
        logger.info(
            f"Sub-problem {sp_index}: Starting with partial context from "
            f"{len(partial_context.dependency_progress)} dependencies "
            f"(all_ready={partial_context.all_dependencies_ready}, "
            f"all_complete={partial_context.all_dependencies_complete})"
        )

    # Emit subproblem_started event
    writer(
        {
            "event_type": "subproblem_started",
            "sub_problem_index": sp_index,
            "sub_problem_id": sub_problem.id,
            "goal": sub_problem.goal,
            "total_sub_problems": len(sub_problems),
            "has_partial_context": bool(partial_context.available_context),
            "dependencies_complete": partial_context.all_dependencies_complete,
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
        "configurable": {"thread_id": f"{session_id}:subproblem:{sp_index}"},
        "recursion_limit": 50,
    }

    # Execute the subgraph using astream() with stream_mode=["updates", "custom"]
    # This allows us to capture custom events from get_stream_writer() calls in subgraph nodes
    # Note: astream_events() was NOT capturing custom events reliably
    final_state = None
    current_round = 0
    event_count = 0
    custom_event_count = 0

    async for chunk in subproblem_graph.astream(
        sp_state, config=config, stream_mode=["updates", "custom"]
    ):
        event_count += 1
        mode, data = chunk

        # DEBUG: Log every 10th event
        if event_count <= 5 or event_count % 10 == 1:
            logger.info(f"[SP{sp_index}] Event #{event_count}: mode={mode}")

        if mode == "custom" and isinstance(data, dict) and "event_type" in data:
            custom_event_count += 1
            custom_type = data.get("event_type")

            # Forward custom events to parent's stream writer
            writer(data)
            logger.debug(f"[SP{sp_index}] Forwarded custom event: {custom_type}")

            # Update context provider when a round completes
            if custom_type == "round_started":
                round_num = data.get("round_number") or data.get("round")
                if round_num is not None:
                    current_round = int(round_num)

            elif custom_type in ("convergence", "convergence_checked", "voting_started"):
                # Round is complete, update context provider
                await context_provider.update_round_context(
                    sp_index=sp_index,
                    round_num=current_round,
                    round_summary=f"Round {current_round} complete",
                    early_insights=None,
                )
                current_round += 1

        elif mode == "updates" and isinstance(data, dict):
            # Capture the last state update (final state)
            for _node_name, node_output in data.items():
                final_state = node_output

    logger.info(
        f"[SP{sp_index}] Streaming complete: {event_count} total events, {custom_event_count} custom events"
    )

    if final_state is None:
        raise RuntimeError(f"Sub-problem {sp_index} execution did not produce final state")

    result = result_from_subgraph_state(cast(SubProblemGraphState, final_state))
    duration = time.time() - start_time
    emit_node_duration(f"speculative_subproblem_{sp_index}", duration * 1000)

    # Extract recommendation once and cache it
    recommendation = extract_recommendation_from_synthesis(result.synthesis)

    # Update result with duration and cached recommendation
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
        extracted_recommendation=recommendation,
    )

    # Mark complete in context provider (reuse already-extracted recommendation)
    await context_provider.mark_complete(
        sp_index=sp_index,
        final_synthesis=result.synthesis,
        final_recommendation=recommendation,
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


async def _execute_speculative_parallel(
    sub_problems: list[SubProblem],
    subproblem_graph: Any,
    session_id: str | None,
    problem: Problem,
    all_personas: list[PersonaProfile],
    user_id: str | None,
    writer: Any,
    early_start_threshold: int = 2,
) -> list[SubProblemResult]:
    """Execute all sub-problems with speculative parallelization.

    This function starts ALL sub-problems concurrently, but dependent
    sub-problems wait for their dependencies to reach the early start
    threshold before beginning their deliberation.

    Benefits over batch execution:
    - 40-60% time savings on dependency chains (SP0 -> SP1 -> SP2)
    - Dependent SPs get early context instead of waiting for full completion
    - Maximum parallelism while respecting logical dependencies

    Args:
        sub_problems: List of all sub-problems to execute
        subproblem_graph: Compiled LangGraph subgraph
        session_id: Session ID
        problem: Parent problem
        all_personas: Available personas
        user_id: User ID
        writer: Stream writer for events
        early_start_threshold: Rounds before dependents can start (default: 2)

    Returns:
        List of results in sub-problem order

    Example:
        Given: SP0 (no deps), SP1 (deps: SP0), SP2 (deps: SP0, SP1)

        Traditional batches: [[0], [1], [2]] = ~10 minutes
        Speculative: All start, SP1 waits for SP0 round 2, SP2 waits for SP0+SP1 round 2
                     = ~5-6 minutes (40-50% faster)
    """
    if not sub_problems:
        return []

    # Create context provider for cross-SP communication
    context_provider = PartialContextProvider(early_start_threshold=early_start_threshold)

    # Build dependency map
    dep_map = _get_dependency_indices(sub_problems)

    logger.info(
        f"_execute_speculative_parallel: Starting {len(sub_problems)} sub-problems "
        f"with early_start_threshold={early_start_threshold}"
    )
    writer(
        {
            "event_type": "speculative_execution_started",
            "total_sub_problems": len(sub_problems),
            "early_start_threshold": early_start_threshold,
            "dependency_map": {str(k): v for k, v in dep_map.items()},
        }
    )

    # Start all sub-problems concurrently
    # Dependent ones will wait internally for their dependencies
    tasks = [
        _run_subproblem_speculative(
            sp_index=i,
            sub_problems=sub_problems,
            subproblem_graph=subproblem_graph,
            session_id=session_id,
            problem=problem,
            all_personas=all_personas,
            user_id=user_id,
            writer=writer,
            context_provider=context_provider,
            dependency_indices=dep_map[i],
        )
        for i in range(len(sub_problems))
    ]

    results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    results: list[tuple[int, SubProblemResult]] = []
    failed_count = 0

    for sp_idx, raw_result in enumerate(results_raw):
        if isinstance(raw_result, BaseException):
            failed_count += 1
            log_with_session(
                logger,
                logging.ERROR,
                session_id,
                f"Sub-problem failed in speculative execution: {raw_result}",
                sub_problem_index=sp_idx,
            )
            writer(
                {
                    "event_type": "subproblem_failed",
                    "error": str(raw_result),
                    "error_type": type(raw_result).__name__,
                    "sub_problem_index": sp_idx,
                }
            )
        else:
            sp_index, sp_result, _ = raw_result
            results.append((sp_index, sp_result))

    if failed_count > 0:
        raise RuntimeError(f"{failed_count} sub-problem(s) failed in speculative execution")

    # Sort by index and return results
    results.sort(key=lambda x: x[0])
    return [r for _, r in results]


async def _parallel_subproblems_subgraph(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute sub-problems using LangGraph subgraphs with real-time streaming.

    Uses get_stream_writer() for per-expert event streaming.

    Supports two execution modes:
    1. Batch execution (default): Batches execute sequentially, SPs within batch in parallel
    2. Speculative execution (ENABLE_SPECULATIVE_PARALLELISM=true): All SPs start concurrently,
       dependent ones wait for dependencies to reach early start threshold

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
        # Convert to Problem object for downstream compatibility
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
    # Also update the problem object's sub_problems
    problem.sub_problems = sub_problems

    all_personas = [PersonaProfile.model_validate(p) for p in get_active_personas()]
    subproblem_graph = get_subproblem_graph()

    # Check if we should use speculative parallelization
    # Only use speculative mode if there are dependencies to parallelize
    has_dependencies = any(sp.dependencies for sp in sub_problems)
    use_speculative = ENABLE_SPECULATIVE_PARALLELISM and has_dependencies and len(sub_problems) > 1

    all_results: list[SubProblemResult] = []

    if use_speculative:
        # SPECULATIVE MODE: Start all sub-problems concurrently
        # Dependent ones wait for dependencies to reach early start threshold
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
        # BATCH MODE: Execute batches sequentially (traditional approach)
        execution_batches: list[list[int]] = parallel_state.get("execution_batches", [])
        if not execution_batches:
            execution_batches = [[i] for i in range(len(sub_problems))]

        total_batches = len(execution_batches)
        logger.info(
            f"_parallel_subproblems_subgraph: Using BATCH execution "
            f"({total_batches} batches for {len(sub_problems)} sub-problems)"
        )

        # Execute batches sequentially
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
