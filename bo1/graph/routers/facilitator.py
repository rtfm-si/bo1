"""Facilitator routing for LangGraph conditional edges.

Routes based on facilitator decisions, convergence checks, and clarification handling.
"""

import logging
from typing import Literal

from bo1.graph.router_utils import log_routing_decision, validate_state_field
from bo1.graph.state import DeliberationGraphState
from bo1.logging import ErrorCode, log_error

logger = logging.getLogger(__name__)


@log_routing_decision("route_facilitator_decision")
def route_facilitator_decision(
    state: DeliberationGraphState,
) -> Literal[
    "vote",
    "persona_contribute",
    "research",
    "moderator_intervene",
    "clarification",
    "data_analysis",
    "END",
]:
    """Route based on facilitator's decision.

    Routes to different nodes based on the facilitator's action:
    - "vote" → Move to voting phase
    - "continue" → Persona contributes next round
    - "research" → Execute external research
    - "moderator" → Moderator intervenes (premature consensus only)
    - "clarify" → Request clarification from user
    - "analyze_data" → Execute dataset analysis

    Args:
        state: Current graph state with facilitator_decision

    Returns:
        Next node name to execute
    """
    decision = validate_state_field(state, "facilitator_decision", "route_facilitator_decision")
    if not decision:
        return "END"

    action = decision["action"]

    if action == "vote":
        return "vote"
    elif action == "continue":
        return "persona_contribute"
    elif action == "research":
        return "research"
    elif action == "moderator":
        return "moderator_intervene"
    elif action == "clarify":
        return "clarification"
    elif action == "analyze_data":
        return "data_analysis"
    else:
        log_error(
            logger,
            ErrorCode.GRAPH_STATE_ERROR,
            f"route_facilitator_decision: Unknown action {action}, falling back to persona_contribute",
        )
        return "persona_contribute"


@log_routing_decision("route_convergence_check")
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

    if should_stop:
        return "vote"
    else:
        return "facilitator_decide"


@log_routing_decision("route_clarification")
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

    if should_stop:
        return "END"
    else:
        return "persona_contribute"


@log_routing_decision("route_after_identify_gaps")
def route_after_identify_gaps(state: DeliberationGraphState) -> Literal["END", "continue"]:
    """Route based on whether critical information gaps require user input.

    After clarification answers are submitted, the checkpoint is updated with:
    - clarification_answers: dict of question->answer pairs
    - should_stop: False (reset to continue)
    - stop_reason: None (cleared)

    The router then sees should_stop=False and routes to "continue".

    Args:
        state: Current graph state

    Returns:
        - "END" if clarification needed (pause for Q&A)
        - "continue" if ready to proceed with deliberation
    """
    should_stop = state.get("should_stop")
    stop_reason = state.get("stop_reason")

    if should_stop and stop_reason == "clarification_needed":
        return "END"

    return "continue"
