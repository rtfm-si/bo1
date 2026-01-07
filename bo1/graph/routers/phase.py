"""Phase routing for LangGraph conditional edges."""

import logging
from typing import Literal

from bo1.graph.router_utils import log_routing_decision
from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


@log_routing_decision("route_phase")
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

    if phase == "decomposition":
        return "select_personas"
    elif phase == "selection":
        return "initial_round"
    elif phase == "discussion":
        return "facilitator_decide"
    else:
        logger.warning(f"route_phase: Unknown phase {phase}")
        return "END"
