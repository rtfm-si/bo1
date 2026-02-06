"""Speculative parallel execution for sub-problems.

Speculative Parallelization (ENABLE_SPECULATIVE_PARALLELISM=true):
Instead of strict batch-by-batch execution, dependent sub-problems can start
when their dependencies reach the early start threshold (default: round 2).
This provides 40-60% time savings over sequential execution.

Example with dependencies SP0 -> SP1 -> SP2:
- Traditional: [SP0 completes] -> [SP1 completes] -> [SP2 completes] = 10 min
- Speculative: [SP0 starts] -> [SP0 round 2, SP1 starts] -> ... = ~5 min
"""

import asyncio
import logging
import time
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from bo1.graph.deliberation import PartialContextProvider
from bo1.graph.deliberation.context import extract_recommendation_from_synthesis
from bo1.graph.deliberation.subgraph.state import SubProblemGraphState
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import SubProblemResult

logger = logging.getLogger(__name__)


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
