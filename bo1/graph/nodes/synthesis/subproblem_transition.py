"""Next sub-problem transition node: Handles transition between sub-problems."""

import asyncio
import logging
from typing import Any

from bo1.graph.nodes.utils import log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_discussion_state,
    get_participant_state,
    get_phase_state,
    get_problem_state,
)
from bo1.models.state import DeliberationPhase, SubProblemResult
from bo1.utils.checkpoint_helpers import (
    get_problem_attr,
    get_subproblem_attr,
)

logger = logging.getLogger(__name__)


async def next_subproblem_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Move to next sub-problem after synthesis.

    This node:
    1. Saves the current sub-problem result (synthesis, votes, costs)
    2. Generates per-expert summaries for memory
    3. Increments sub_problem_index
    4. If more sub-problems: resets deliberation state and sets next sub-problem
    5. If all complete: triggers meta-synthesis by setting current_sub_problem=None

    GUARD: Checks if result already exists for current sub_problem_index to prevent
    double-processing on graph retry (atomicity fix).

    Args:
        state: Current graph state

    Returns:
        Dictionary with state updates
    """
    from bo1.agents.summarizer import SummarizerAgent

    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)
    discussion_state = get_discussion_state(state)
    participant_state = get_participant_state(state)
    phase_state = get_phase_state(state)

    # Extract current sub-problem data from accessors
    current_sp = problem_state.get("current_sub_problem")
    problem = problem_state.get("problem")
    sub_problem_index = problem_state.get("sub_problem_index", 0)
    previous_results = problem_state.get("sub_problem_results", [])

    # Debug logging to trace state corruption after checkpoint restore
    session_id = core_state.get("session_id")
    log_with_session(
        logger,
        logging.DEBUG,
        session_id,
        f"next_subproblem_node: current_sub_problem type={type(current_sp).__name__}, "
        f"value={current_sp if isinstance(current_sp, dict) else repr(current_sp)[:200]}",
    )

    # GUARD: Check if result already exists for current index (prevents double-processing)
    # This can happen on graph retry or checkpoint edge cases
    current_sp_id = get_subproblem_attr(current_sp, "id", None) if current_sp else None

    # Guard: Ensure current_sp_id is hashable (string expected)
    # State corruption after checkpoint restore can cause id to be a list
    if current_sp_id and not isinstance(current_sp_id, str):
        log_with_session(
            logger,
            logging.ERROR,
            session_id,
            f"next_subproblem_node: current_sub_problem.id is not a string! "
            f"Got type={type(current_sp_id).__name__}, value={current_sp_id}. "
            f"This indicates state corruption. Skipping guard check.",
        )
        current_sp_id = None  # Skip guard check, proceed with normal flow

    if current_sp_id:
        # Build set of existing result IDs, handling both object and dict forms
        existing_result_ids: set[str] = set()
        for r in previous_results:
            sp_id = (
                r.get("sub_problem_id")
                if isinstance(r, dict)
                else getattr(r, "sub_problem_id", None)
            )
            if isinstance(sp_id, str):
                existing_result_ids.add(sp_id)

        if current_sp_id in existing_result_ids:
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"next_subproblem_node: Result already exists for sub-problem {current_sp_id} "
                f"(index {sub_problem_index}) - skipping to avoid double-processing",
            )
            # Return minimal update - don't add duplicate result
            sub_problems = get_problem_attr(problem, "sub_problems", [])
            next_index = sub_problem_index + 1
            if next_index < len(sub_problems):
                return {
                    "current_sub_problem": sub_problems[next_index],
                    "sub_problem_index": next_index,
                    "current_node": "next_subproblem_skipped",
                }
            else:
                return {
                    "current_sub_problem": None,
                    "current_node": "next_subproblem_skipped",
                }
    contributions = discussion_state.get("contributions", [])
    votes = discussion_state.get("recommendations", [])
    personas = participant_state.get("personas", [])
    synthesis = discussion_state.get("synthesis", "")
    metrics = state.get("metrics")  # metrics is not in any accessor yet
    # sub_problem_index and previous_results already declared above (for guard check)

    # Enhanced logging for sub-problem progression (Bug #3 fix)
    # session_id already obtained from core_state above
    sub_problems = get_problem_attr(problem, "sub_problems", [])
    total_sub_problems = len(sub_problems) if sub_problems else 0
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"next_subproblem_node: Saving result for sub-problem {sub_problem_index + 1}/{total_sub_problems}: "
        f"{get_subproblem_attr(current_sp, 'goal', 'unknown')}",
    )

    if not current_sp:
        raise ValueError("next_subproblem_node called without current_sub_problem")

    if not problem:
        raise ValueError("next_subproblem_node called without problem")

    # Calculate cost for this sub-problem (all phase costs accumulated)
    # For simplicity, use total_cost - sum of previous sub-problem costs
    total_cost_so_far = metrics.total_cost if metrics else 0.0
    # previous_results already declared above (for guard check)
    previous_cost: float = sum(
        (
            float(r.cost if hasattr(r, "cost") else r.get("cost", 0.0))  # type: ignore[attr-defined]
            for r in previous_results
        ),
        0.0,
    )
    sub_problem_cost = total_cost_so_far - previous_cost

    # Track duration (placeholder - could enhance with actual timing)
    duration_seconds = 0.0

    # Generate per-expert summaries for memory (if there are contributions)
    expert_summaries: dict[str, str] = {}

    if contributions:
        summarizer = SummarizerAgent()

        # P2 BATCH FIX: Run all expert summarizations in PARALLEL using asyncio.gather
        # This reduces latency by 60-80% (from sequential N*200ms to parallel ~200ms)
        async def summarize_expert(persona: Any) -> tuple[str, str, Any] | None:
            """Summarize a single expert's contributions."""
            expert_contributions = [c for c in contributions if c.persona_code == persona.code]
            if not expert_contributions:
                return None

            # Convert contributions to dict format for summarizer
            contribution_dicts = [
                {"persona": c.persona_name, "content": c.content} for c in expert_contributions
            ]

            # Summarize expert's contributions
            response = await summarizer.summarize_round(
                round_number=phase_state.get("round_number", 1),
                contributions=contribution_dicts,
                problem_statement=get_subproblem_attr(current_sp, "goal", ""),
                target_tokens=75,  # Concise summary for memory
            )

            return (persona.code, persona.display_name, response)

        # Run all summarizations in parallel
        logger.info(f"Running {len(personas)} expert summarizations in parallel (BATCH)")
        results = await asyncio.gather(
            *[summarize_expert(p) for p in personas],
            return_exceptions=True,
        )

        # Process results
        total_memory_cost = 0.0
        for gather_result in results:
            if gather_result is None:
                continue  # No contributions for this expert
            if isinstance(gather_result, BaseException):
                logger.warning(f"Expert summarization failed: {gather_result}")
                continue

            persona_code, display_name, response = gather_result
            expert_summaries[persona_code] = response.content
            total_memory_cost += response.cost_total

            logger.info(
                f"Generated memory summary for {display_name}: "
                f"{response.token_usage.output_tokens} tokens, ${response.cost_total:.6f}"
            )

        # Track total cost once (not per-expert)
        if metrics and total_memory_cost > 0:
            phase_costs = metrics.phase_costs
            phase_costs["expert_memory"] = phase_costs.get("expert_memory", 0.0) + total_memory_cost

    # Create SubProblemResult
    result = SubProblemResult(
        sub_problem_id=get_subproblem_attr(current_sp, "id", ""),
        sub_problem_goal=get_subproblem_attr(current_sp, "goal", ""),
        synthesis=synthesis or "",  # Ensure not None
        votes=votes,
        contribution_count=len(contributions),
        cost=sub_problem_cost,
        duration_seconds=duration_seconds,
        expert_panel=[p.code for p in personas],
        expert_summaries=expert_summaries,
    )

    # Add to results
    sub_problem_results = list(previous_results)
    sub_problem_results.append(result)

    # Save SP boundary checkpoint to PostgreSQL for resume capability
    if session_id:
        try:
            from bo1.state.repositories.session_repository import session_repository

            # Determine if this is the first SP (need to set total_sub_problems)
            is_first_sp = sub_problem_index == 0
            session_repository.update_sp_checkpoint(
                session_id=session_id,
                last_completed_sp_index=sub_problem_index,
                total_sub_problems=total_sub_problems if is_first_sp else None,
            )
            log_with_session(
                logger,
                logging.INFO,
                session_id,
                f"next_subproblem_node: Saved SP checkpoint {sub_problem_index + 1}/{total_sub_problems}",
            )
        except Exception as e:
            # Non-blocking: checkpoint failure shouldn't stop deliberation
            log_with_session(
                logger,
                logging.WARNING,
                session_id,
                f"next_subproblem_node: Failed to save SP checkpoint: {e}",
            )

    # Increment index
    next_index = sub_problem_index + 1

    # Check if more sub-problems
    if next_index < len(sub_problems):
        next_sp = sub_problems[next_index]

        logger.info(
            f"Moving to sub-problem {next_index + 1}/{len(sub_problems)}: {get_subproblem_attr(next_sp, 'goal', 'unknown')}"
        )

        return {
            "current_sub_problem": next_sp,
            "sub_problem_index": next_index,
            "sub_problem_results": sub_problem_results,
            "round_number": 0,  # Will be set to 1 by initial_round_node
            "contributions": [],
            "recommendations": [],
            "synthesis": None,
            "facilitator_decision": None,
            "should_stop": False,
            "stop_reason": None,
            "round_summaries": [],  # Reset for new sub-problem
            "personas": [],  # Will be re-selected by select_personas_node
            "phase": DeliberationPhase.DECOMPOSITION,  # Ready for new sub-problem
            "metrics": metrics,  # Keep metrics (accumulates across sub-problems)
            "current_node": "next_subproblem",
            "completed_research_queries": [],  # Reset research tracking for new sub-problem
        }
    else:
        # All complete -> meta-synthesis
        logger.info("All sub-problems complete, proceeding to meta-synthesis")
        return {
            "current_sub_problem": None,
            "sub_problem_results": sub_problem_results,
            "phase": DeliberationPhase.SYNTHESIS,  # Meta-synthesis phase
            "current_node": "next_subproblem",
        }
