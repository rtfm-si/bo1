"""Server-Sent Events (SSE) formatting utilities.

Provides functions to format deliberation events as SSE messages for
real-time streaming to web clients.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def format_sse_event(
    event_type: str,
    data: dict[str, Any],
    event_id: str | None = None,
) -> str:
    """Format a dictionary as an SSE event.

    Args:
        event_type: Type of event (e.g., "node_start", "contribution")
        data: Event data to send
        event_id: Optional event ID for client tracking

    Returns:
        SSE-formatted string

    Examples:
        >>> event = format_sse_event("test", {"message": "hello"})
        >>> print(event)
        event: test
        data: {"message": "hello"}

        >>>
    """
    lines = []

    # Add event ID if provided
    if event_id:
        lines.append(f"id: {event_id}")

    # Add event type
    lines.append(f"event: {event_type}")

    # Add data as JSON
    data_json = json.dumps(data)
    lines.append(f"data: {data_json}")

    # SSE format requires double newline at end
    return "\n".join(lines) + "\n\n"


def node_start_event(node_name: str, session_id: str) -> str:
    """Create SSE event for node execution start.

    Args:
        node_name: Name of the node starting
        session_id: Session identifier

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "node_start",
        {
            "node": node_name,
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def node_end_event(node_name: str, session_id: str, duration_ms: float | None = None) -> str:
    """Create SSE event for node execution completion.

    Args:
        node_name: Name of the node that completed
        session_id: Session identifier
        duration_ms: Optional execution duration in milliseconds

    Returns:
        SSE-formatted event string
    """
    data: dict[str, Any] = {
        "node": node_name,
        "session_id": session_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if duration_ms is not None:
        data["duration_ms"] = duration_ms

    return format_sse_event("node_end", data)


def contribution_event(
    session_id: str,
    persona_code: str,
    persona_name: str,
    contribution: str,
    round_number: int,
) -> str:
    """Create SSE event for persona contribution.

    Args:
        session_id: Session identifier
        persona_code: Persona code (e.g., "CFO")
        persona_name: Persona display name
        contribution: The contribution text
        round_number: Current round number

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "contribution",
        {
            "session_id": session_id,
            "persona_code": persona_code,
            "persona_name": persona_name,
            "contribution": contribution,
            "round": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def facilitator_decision_event(
    session_id: str,
    action: str,
    reasoning: str,
    round_number: int,
) -> str:
    """Create SSE event for facilitator decision.

    Args:
        session_id: Session identifier
        action: Facilitator action (continue, vote, clarify, etc.)
        reasoning: Decision reasoning
        round_number: Current round number

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "facilitator_decision",
        {
            "session_id": session_id,
            "action": action,
            "reasoning": reasoning,
            "round": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def convergence_event(
    session_id: str,
    score: float,
    converged: bool,
    round_number: int,
) -> str:
    """Create SSE event for convergence check result.

    Args:
        session_id: Session identifier
        score: Convergence score (0.0-1.0)
        converged: Whether deliberation has converged
        round_number: Current round number

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "convergence",
        {
            "session_id": session_id,
            "score": score,
            "converged": converged,
            "round": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def complete_event(
    session_id: str,
    final_output: str,
    total_cost: float,
    total_rounds: int,
) -> str:
    """Create SSE event for deliberation completion.

    Args:
        session_id: Session identifier
        final_output: Final synthesized output
        total_cost: Total cost in USD
        total_rounds: Total number of rounds

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "complete",
        {
            "session_id": session_id,
            "final_output": final_output,
            "total_cost": total_cost,
            "total_rounds": total_rounds,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def error_event(
    session_id: str,
    error: str,
    error_type: str | None = None,
) -> str:
    """Create SSE event for error.

    Args:
        session_id: Session identifier
        error: Error message
        error_type: Optional error type/category

    Returns:
        SSE-formatted event string
    """
    data: dict[str, Any] = {
        "session_id": session_id,
        "error": error,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if error_type:
        data["error_type"] = error_type

    return format_sse_event("error", data)


def clarification_requested_event(
    session_id: str,
    question: str,
    reason: str,
    round_number: int,
) -> str:
    """Create SSE event for clarification request.

    Args:
        session_id: Session identifier
        question: Clarification question
        reason: Reason for clarification
        round_number: Current round number

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "clarification_requested",
        {
            "session_id": session_id,
            "question": question,
            "reason": reason,
            "round": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def clarification_answered_event(
    session_id: str,
    question: str,
    answer: str,
    round_number: int,
) -> str:
    """Create SSE event for clarification answer.

    Args:
        session_id: Session identifier
        question: Original clarification question
        answer: User's answer
        round_number: Current round number

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "clarification_answered",
        {
            "session_id": session_id,
            "question": question,
            "answer": answer,
            "round": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
