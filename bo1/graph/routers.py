"""Router functions for LangGraph conditional edges.

Routers determine the next node to execute based on the current state.
"""

import logging
from typing import Literal

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


def route_phase(
    state: DeliberationGraphState,
) -> Literal["select_personas", "initial_round", "END"]:
    """Route based on current deliberation phase.

    This is a simple linear router for Day 27 (Week 4).
    Will be expanded in Week 5 with facilitator decisions.

    Args:
        state: Current graph state

    Returns:
        Next node name to execute
    """
    phase = state.get("phase")

    logger.info(f"route_phase: Current phase = {phase}")

    # Linear flow for now
    if phase == "decomposition":
        logger.info("route_phase: Routing to select_personas")
        return "select_personas"
    elif phase == "selection":
        logger.info("route_phase: Routing to initial_round")
        return "initial_round"
    elif phase == "discussion":
        # For now, end after initial round
        # Week 5 will add facilitator_decide here
        logger.info("route_phase: Routing to END (Week 5 will add facilitator)")
        return "END"
    else:
        logger.warning(f"route_phase: Unknown phase {phase}, routing to END")
        return "END"
