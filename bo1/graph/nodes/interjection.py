"""Interjection response node: routes user questions to all personas."""

import logging
import time
from typing import Any

from bo1.graph.nodes.utils import emit_node_duration, log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_control_state,
    get_core_state,
    get_participant_state,
    get_phase_state,
    get_problem_state,
)

logger = logging.getLogger(__name__)


async def interjection_response_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Generate brief expert responses to a user interjection.

    Each persona receives the interjection as custom expert_memory and
    produces a short (~100 word) response. Responses are emitted as SSE
    events so the frontend can display them in real time.

    Args:
        state: Current graph state (must have user_interjection set)

    Returns:
        State update clearing the interjection and storing responses
    """
    from bo1.graph.nodes.rounds.contribution import _generate_parallel_contributions

    _start_time = time.perf_counter()

    core = get_core_state(state)
    control = get_control_state(state)
    participant = get_participant_state(state)
    phase = get_phase_state(state)
    problem = get_problem_state(state)

    session_id = core.get("session_id")
    interjection = control.get("user_interjection") or ""
    personas = participant.get("personas", [])
    round_number = phase.get("round_number", 1)

    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"interjection_response_node: Processing interjection from user ({len(interjection)} chars)",
    )

    if not interjection or not personas:
        return {
            "needs_interjection_response": False,
            "user_interjection": None,
            "current_node": "interjection_response",
        }

    # Build per-expert memory with the interjection question
    expert_memories: dict[str, str] = {}
    for persona in personas:
        expert_memories[persona.code] = (
            f"A user has raised their hand with a question during the deliberation.\n\n"
            f"USER QUESTION: {interjection}\n\n"
            f"Provide a brief, direct response (max 100 words) from your expert perspective. "
            f"Address their question specifically — do not repeat your previous analysis."
        )

    # Generate parallel contributions using the same engine as regular rounds
    contributions = await _generate_parallel_contributions(
        experts=personas,
        state=state,
        phase="interjection",
        round_number=round_number,
        contribution_type="response",
        expert_memories=expert_memories,
    )

    # Format responses for state storage
    interjection_responses = []
    for contrib in contributions:
        interjection_responses.append(
            {
                "persona_code": contrib.persona_code,
                "persona_name": contrib.persona_name,
                "response": contrib.content,
                "round_number": round_number,
            }
        )

    # SSE events are emitted by EventCollector when it observes node output

    log_with_session(
        logger,
        logging.INFO,
        session_id,
        f"interjection_response_node: {len(interjection_responses)} experts responded",
    )

    emit_node_duration("interjection_response_node", (time.perf_counter() - _start_time) * 1000)

    return {
        "needs_interjection_response": False,
        "interjection_responses": interjection_responses,
        "user_interjection": None,
        "current_node": "interjection_response",
        "sub_problem_index": problem.get("sub_problem_index", 0),
    }
