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
    - "research" → End (research not implemented in Week 5)

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
        # Research not implemented in Week 5, end for now
        logger.info("route_facilitator_decision: Research requested, ending (not implemented)")
        return "END"
    else:
        logger.warning(f"route_facilitator_decision: Unknown action {action}, routing to END")
        return "END"
