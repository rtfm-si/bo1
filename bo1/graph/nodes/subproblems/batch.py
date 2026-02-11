"""Batch execution for parallel sub-problems.

Contains the batch-mode execution functions:
- _run_single_subproblem: Execute a single sub-problem through the subgraph
- _execute_batch: Execute a batch of sub-problems in parallel
"""

import asyncio
import logging
import time
from typing import Any, cast

from langchain_core.runnables import RunnableConfig

from bo1.graph.deliberation.context import extract_recommendation_from_synthesis
from bo1.graph.deliberation.subgraph.state import SubProblemGraphState
from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.models.persona import PersonaProfile
from bo1.models.state import SubProblemResult

logger = logging.getLogger(__name__)


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
        votes=result.recommendations,
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
            "recommendations_count": len(result.recommendations),
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
