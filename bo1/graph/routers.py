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
) -> Literal["vote", "moderator_intervene", "persona_contribute", "clarification", "END"]:
    """Route based on facilitator's decision.

    Routes to different nodes based on the facilitator's action:
    - "vote" → Move to voting phase
    - "moderator" → Trigger moderator intervention
    - "continue" → Persona contributes next round
    - "clarify" → Request clarification from user (Day 37)
    - "research" → Treat as continue (research not implemented)

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
    elif action == "moderator":
        logger.info("route_facilitator_decision: Routing to moderator_intervene")
        return "moderator_intervene"
    elif action == "continue":
        logger.info("route_facilitator_decision: Routing to persona_contribute")
        return "persona_contribute"
    elif action == "clarify":
        logger.info("route_facilitator_decision: Routing to clarification (Day 37)")
        return "clarification"
    elif action == "research":
        # Research not implemented in Week 5 - transition to voting instead
        logger.warning(
            "route_facilitator_decision: Research requested but not implemented in Week 5. "
            "Routing to vote (research will be implemented in Week 6)."
        )
        return "vote"
    else:
        logger.warning(f"route_facilitator_decision: Unknown action {action}, routing to END")
        return "END"


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

    Args:
        state: Current graph state

    Returns:
        - "next_subproblem" if more sub-problems exist
        - "meta_synthesis" if all complete and multiple sub-problems
        - "END" if atomic problem (only 1 sub-problem)
    """
    problem = state.get("problem")
    sub_problem_index = state.get("sub_problem_index", 0)

    if not problem:
        logger.error("route_after_synthesis: No problem in state!")
        return "END"

    total_sub_problems = len(problem.sub_problems)

    logger.info(
        f"route_after_synthesis: Sub-problem {sub_problem_index + 1}/{total_sub_problems} complete"
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
    else:
        # All complete → meta-synthesis
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
