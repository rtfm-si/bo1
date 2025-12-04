"""Router functions for LangGraph conditional edges.

Routers determine the next node to execute based on the current state.
"""

import logging
from typing import Literal

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


def route_phase(
    state: DeliberationGraphState,
) -> Literal["select_personas", "initial_round", "facilitator_decide", "END"]:
    """Route based on current deliberation phase.

    Updated in Week 5 to route to facilitator after initial round.

    Args:
        state: Current graph state

    Returns:
        Next node name to execute
    """
    phase = state.get("phase")

    logger.info(f"route_phase: Current phase = {phase}")

    # Linear flow
    if phase == "decomposition":
        logger.info("route_phase: Routing to select_personas")
        return "select_personas"
    elif phase == "selection":
        logger.info("route_phase: Routing to initial_round")
        return "initial_round"
    elif phase == "discussion":
        # Week 5: Route to facilitator to decide next action
        logger.info("route_phase: Routing to facilitator_decide")
        return "facilitator_decide"
    else:
        logger.warning(f"route_phase: Unknown phase {phase}, routing to END")
        return "END"


def route_facilitator_decision(
    state: DeliberationGraphState,
) -> Literal[
    "vote", "persona_contribute", "research", "moderator_intervene", "clarification", "END"
]:
    """Route based on facilitator's decision.

    Routes to different nodes based on the facilitator's action:
    - "vote" → Move to voting phase
    - "continue" → Persona contributes next round
    - "research" → Execute external research
    - "moderator" → Moderator intervenes (premature consensus only)
    - "clarify" → Request clarification from user

    Args:
        state: Current graph state with facilitator_decision

    Returns:
        Next node name to execute
    """
    decision = state.get("facilitator_decision")

    if not decision:
        logger.error("route_facilitator_decision: No facilitator decision in state!")
        return "END"

    # decision is now a dict (converted from dataclass using asdict())
    action = decision["action"]
    logger.info(f"route_facilitator_decision: Routing based on action = {action}")

    if action == "vote":
        logger.info("route_facilitator_decision: Routing to vote")
        return "vote"
    elif action == "continue":
        logger.info("route_facilitator_decision: Routing to persona_contribute")
        return "persona_contribute"
    elif action == "research":
        logger.info("route_facilitator_decision: Routing to research")
        return "research"
    elif action == "moderator":
        logger.info("route_facilitator_decision: Routing to moderator_intervene")
        return "moderator_intervene"
    elif action == "clarify":
        logger.info("route_facilitator_decision: Routing to clarification")
        return "clarification"
    else:
        # Fallback: continue deliberation instead of terminating
        logger.error(
            f"route_facilitator_decision: Unknown action {action}, falling back to persona_contribute"
        )
        return "persona_contribute"


def route_convergence_check(
    state: DeliberationGraphState,
) -> Literal["facilitator_decide", "vote"]:
    """Route after convergence check based on should_stop flag.

    This router is called after persona_contribute or moderator_intervene nodes.
    It checks if convergence has been reached or round limits exceeded.

    Args:
        state: Current graph state with should_stop flag

    Returns:
        - "facilitator_decide" if deliberation should continue
        - "vote" if stopping condition met (max rounds, convergence, etc.) - Day 31
    """
    should_stop = state.get("should_stop", False)
    stop_reason = state.get("stop_reason")
    round_number = state.get("round_number", 0)

    logger.info(f"route_convergence_check: Round {round_number}, should_stop={should_stop}")

    if should_stop:
        logger.info(
            f"route_convergence_check: Stopping deliberation (reason: {stop_reason}) -> routing to vote"
        )
        return "vote"
    else:
        logger.info("route_convergence_check: Continuing to facilitator_decide")
        return "facilitator_decide"


def route_after_synthesis(
    state: DeliberationGraphState,
) -> Literal["next_subproblem", "meta_synthesis", "END"]:
    """Route after sub-problem synthesis.

    This router determines whether to:
    - Move to next sub-problem (if more exist)
    - Perform meta-synthesis (if all sub-problems complete and >1 sub-problem)
    - End directly (if only 1 sub-problem - atomic problem)

    AUDIT FIX (Issue #3): Added validation to check that ALL sub-problems have
    completed successfully before proceeding to meta-synthesis. Without this check,
    failures in some sub-problems could lead to incomplete syntheses.

    Args:
        state: Current graph state

    Returns:
        - "next_subproblem" if more sub-problems exist
        - "meta_synthesis" if all complete and multiple sub-problems
        - "END" if atomic problem (only 1 sub-problem) OR if sub-problems failed
    """
    problem = state.get("problem")
    sub_problem_index = state.get("sub_problem_index", 0)
    sub_problem_results = state.get("sub_problem_results", [])

    if not problem:
        logger.error("route_after_synthesis: No problem in state!")
        return "END"

    total_sub_problems = len(problem.sub_problems)

    logger.info(
        f"route_after_synthesis: Sub-problem {sub_problem_index + 1}/{total_sub_problems} complete, "
        f"total results collected: {len(sub_problem_results)}"
    )

    # Atomic optimization: If only 1 sub-problem, skip meta-synthesis
    if total_sub_problems == 1:
        logger.info("route_after_synthesis: Atomic problem (1 sub-problem) -> routing to END")
        return "END"

    # Check if more sub-problems exist
    if sub_problem_index + 1 < total_sub_problems:
        logger.info(
            f"route_after_synthesis: More sub-problems exist ({sub_problem_index + 2}/{total_sub_problems}) "
            f"-> routing to next_subproblem"
        )
        return "next_subproblem"

    # All sub-problems have been processed. Now validate we have results for ALL of them.
    # CRITICAL: This prevents incomplete syntheses when some sub-problems fail
    if len(sub_problem_results) < total_sub_problems:
        failed_count = total_sub_problems - len(sub_problem_results)
        completed_ids = {r.sub_problem_id for r in sub_problem_results}
        expected_ids = [sp.id for sp in problem.sub_problems]
        failed_ids = [sp_id for sp_id in expected_ids if sp_id not in completed_ids]

        logger.error(
            f"route_after_synthesis: Cannot proceed to meta-synthesis - "
            f"{failed_count} sub-problem(s) failed. "
            f"Failed sub-problem IDs: {failed_ids}. "
            f"Expected {total_sub_problems} results, got {len(sub_problem_results)}."
        )

        # Emit error event to UI so user knows what happened
        from backend.api.dependencies import get_event_publisher

        try:
            event_publisher = get_event_publisher()
            session_id = state.get("session_id")

            if event_publisher and session_id:
                # Get goals for failed sub-problems by ID
                failed_goals = [sp.goal for sp in problem.sub_problems if sp.id in failed_ids]

                event_publisher.publish_event(
                    session_id,
                    "meeting_failed",
                    {
                        "reason": f"{failed_count} sub-problem(s) failed to complete",
                        "failed_count": failed_count,
                        "failed_ids": failed_ids,
                        "failed_goals": failed_goals,
                        "completed_count": len(sub_problem_results),
                        "total_count": total_sub_problems,
                    },
                )
                logger.info(f"Published meeting_failed event for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to publish meeting_failed event: {e}")

        # Stop the graph - don't proceed with incomplete data
        return "END"

    # All sub-problems complete with results → meta-synthesis
    logger.info(
        f"route_after_synthesis: All {total_sub_problems} sub-problems complete "
        f"-> routing to meta_synthesis"
    )
    return "meta_synthesis"


def route_clarification(
    state: DeliberationGraphState,
) -> Literal["persona_contribute", "END"]:
    """Route after clarification based on should_stop flag.

    This router determines whether to:
    - Continue deliberation (if clarification answered or skipped)
    - Pause session (if user requested pause)

    Args:
        state: Current graph state

    Returns:
        - "persona_contribute" if continuing deliberation
        - "END" if session paused
    """
    should_stop = state.get("should_stop", False)
    pending_clarification = state.get("pending_clarification")

    logger.info(
        f"route_clarification: should_stop={should_stop}, pending={pending_clarification is not None}"
    )

    if should_stop:
        logger.info("route_clarification: Session paused by user -> routing to END")
        return "END"
    else:
        logger.info("route_clarification: Clarification handled -> routing to persona_contribute")
        return "persona_contribute"


def route_subproblem_execution(
    state: DeliberationGraphState,
) -> Literal["parallel_subproblems", "select_personas"]:
    """Route after dependency analysis to parallel or sequential execution.

    This router checks the parallel_mode flag set by analyze_dependencies_node:
    - If parallel_mode=True: Route to parallel_subproblems for concurrent execution
    - If parallel_mode=False: Route to select_personas for sequential execution

    Note: context_collection now happens BEFORE decomposition (Issue #3 fix),
    so sequential mode goes directly to select_personas.

    Args:
        state: Current graph state (must have parallel_mode set)

    Returns:
        - "parallel_subproblems" if parallel execution enabled
        - "select_personas" if sequential execution
    """
    parallel_mode = state.get("parallel_mode", False)

    logger.info(f"route_subproblem_execution: parallel_mode={parallel_mode}")

    if parallel_mode:
        logger.info("route_subproblem_execution: Routing to parallel_subproblems")
        return "parallel_subproblems"
    else:
        logger.info("route_subproblem_execution: Routing to select_personas (sequential)")
        return "select_personas"
