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
) -> Literal["vote", "moderator_intervene", "persona_contribute", "END"]:
    """Route based on facilitator's decision.

    Routes to different nodes based on the facilitator's action:
    - "vote" → Move to voting phase
    - "moderator" → Trigger moderator intervention
    - "continue" → Persona contributes next round
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

    action = decision.action
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
    elif action == "research":
        # Research not implemented - pick a random persona to continue discussion
        import random

        personas = state.get("personas", [])
        if personas:
            # Randomly select a speaker since facilitator didn't specify one
            random_speaker = random.choice(personas)  # noqa: S311
            decision.next_speaker = random_speaker.code
            logger.warning(
                f"route_facilitator_decision: Research requested but not implemented. "
                f"Selected random speaker '{random_speaker.code}' to continue discussion"
            )
            return "persona_contribute"
        else:
            logger.error("route_facilitator_decision: Research requested but no personas available")
            return "END"
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
