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
    threshold: float = 0.85,
    should_stop: bool = False,
    stop_reason: str | None = None,
    max_rounds: int = 10,
) -> str:
    """Create SSE event for convergence check result.

    Args:
        session_id: Session identifier
        score: Convergence score (0.0-1.0)
        converged: Whether deliberation has converged
        round_number: Current round number
        threshold: Convergence threshold (default 0.85)
        should_stop: Whether deliberation should stop
        stop_reason: Optional reason for stopping
        max_rounds: Maximum number of rounds

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
            "threshold": threshold,
            "should_stop": should_stop,
            "stop_reason": stop_reason,
            "max_rounds": max_rounds,
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


# Additional event formatters for complete streaming support


def session_started_event(
    session_id: str,
    problem_statement: str,
    max_rounds: int,
    user_id: str,
) -> str:
    """Create SSE event for session initialization.

    Args:
        session_id: Session identifier
        problem_statement: Problem being deliberated
        max_rounds: Maximum deliberation rounds
        user_id: User who started the session

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "session_started",
        {
            "session_id": session_id,
            "problem_statement": problem_statement,
            "max_rounds": max_rounds,
            "user_id": user_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def decomposition_started_event(session_id: str) -> str:
    """Create SSE event for decomposition start.

    Args:
        session_id: Session identifier

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "decomposition_started",
        {
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def decomposition_complete_event(
    session_id: str,
    sub_problems: list[dict[str, Any]],
) -> str:
    """Create SSE event for decomposition completion.

    Args:
        session_id: Session identifier
        sub_problems: List of sub-problem dicts with id, goal, rationale, etc.

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "decomposition_complete",
        {
            "session_id": session_id,
            "sub_problems": sub_problems,
            "count": len(sub_problems),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def persona_selection_started_event(session_id: str) -> str:
    """Create SSE event for persona selection start.

    Args:
        session_id: Session identifier

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "persona_selection_started",
        {
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def persona_selected_event(
    session_id: str,
    persona: dict[str, Any],
    rationale: str,
    order: int,
) -> str:
    """Create SSE event for individual persona selection.

    Args:
        session_id: Session identifier
        persona: Persona dict with code, name, display_name, domain_expertise
        rationale: Why this expert was chosen
        order: Selection order (1-indexed)

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "persona_selected",
        {
            "session_id": session_id,
            "persona": persona,
            "rationale": rationale,
            "order": order,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def persona_selection_complete_event(
    session_id: str,
    personas: list[str],
) -> str:
    """Create SSE event for persona selection completion.

    Args:
        session_id: Session identifier
        personas: List of selected persona codes

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "persona_selection_complete",
        {
            "session_id": session_id,
            "personas": personas,
            "count": len(personas),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def subproblem_started_event(
    session_id: str,
    sub_problem_index: int,
    sub_problem_id: str,
    goal: str,
    total_sub_problems: int,
) -> str:
    """Create SSE event for sub-problem deliberation start.

    Args:
        session_id: Session identifier
        sub_problem_index: 0-indexed sub-problem number
        sub_problem_id: Sub-problem identifier
        goal: Sub-problem goal
        total_sub_problems: Total number of sub-problems

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "subproblem_started",
        {
            "session_id": session_id,
            "sub_problem_index": sub_problem_index,
            "sub_problem_id": sub_problem_id,
            "goal": goal,
            "total_sub_problems": total_sub_problems,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def initial_round_started_event(
    session_id: str,
    experts: list[str],
) -> str:
    """Create SSE event for initial round start.

    Args:
        session_id: Session identifier
        experts: List of participating expert codes

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "initial_round_started",
        {
            "session_id": session_id,
            "round_number": 1,
            "experts": experts,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def moderator_intervention_event(
    session_id: str,
    moderator_type: str,
    content: str,
    trigger_reason: str,
    round_number: int,
) -> str:
    """Create SSE event for moderator intervention.

    Args:
        session_id: Session identifier
        moderator_type: Type of intervention (contrarian, skeptic, optimist)
        content: Intervention message
        trigger_reason: Why moderator intervened
        round_number: Current round number

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "moderator_intervention",
        {
            "session_id": session_id,
            "moderator_type": moderator_type,
            "content": content,
            "trigger_reason": trigger_reason,
            "round": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def round_started_event(session_id: str, round_number: int) -> str:
    """Create SSE event for new round start.

    Args:
        session_id: Session identifier
        round_number: Round number (1-indexed)

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "round_started",
        {
            "session_id": session_id,
            "round_number": round_number,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def voting_started_event(
    session_id: str,
    experts: list[str],
) -> str:
    """Create SSE event for voting phase start.

    Args:
        session_id: Session identifier
        experts: List of expert codes who will vote

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "voting_started",
        {
            "session_id": session_id,
            "experts": experts,
            "count": len(experts),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def persona_vote_event(
    session_id: str,
    persona_code: str,
    persona_name: str,
    recommendation: str,
    confidence: float,
    reasoning: str,
    conditions: list[str],
) -> str:
    """Create SSE event for individual persona vote/recommendation.

    Args:
        session_id: Session identifier
        persona_code: Persona code (e.g., "CFO")
        persona_name: Persona display name
        recommendation: Free-form recommendation text
        confidence: Confidence level (0.0-1.0)
        reasoning: Reasoning behind recommendation
        conditions: List of prerequisite conditions

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "persona_vote",
        {
            "session_id": session_id,
            "persona_code": persona_code,
            "persona_name": persona_name,
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": reasoning,
            "conditions": conditions,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def voting_complete_event(
    session_id: str,
    votes_count: int,
    consensus_level: str,
) -> str:
    """Create SSE event for voting phase completion.

    Args:
        session_id: Session identifier
        votes_count: Number of votes collected
        consensus_level: Level of consensus (strong, moderate, weak)

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "voting_complete",
        {
            "session_id": session_id,
            "votes_count": votes_count,
            "consensus_level": consensus_level,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def synthesis_started_event(session_id: str) -> str:
    """Create SSE event for synthesis start.

    Args:
        session_id: Session identifier

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "synthesis_started",
        {
            "session_id": session_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def synthesis_complete_event(
    session_id: str,
    synthesis: str,
    word_count: int,
) -> str:
    """Create SSE event for synthesis completion.

    Args:
        session_id: Session identifier
        synthesis: Full synthesis markdown text
        word_count: Word count of synthesis

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "synthesis_complete",
        {
            "session_id": session_id,
            "synthesis": synthesis,
            "word_count": word_count,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def subproblem_complete_event(
    session_id: str,
    sub_problem_index: int,
    sub_problem_id: str,
    goal: str,
    cost: float,
    duration_seconds: float,
    expert_panel: list[str],
    contribution_count: int,
) -> str:
    """Create SSE event for sub-problem completion.

    Args:
        session_id: Session identifier
        sub_problem_index: 0-indexed sub-problem number
        sub_problem_id: Sub-problem identifier
        goal: Sub-problem goal
        cost: Cost in USD for this sub-problem
        duration_seconds: Time taken in seconds
        expert_panel: List of expert codes who deliberated
        contribution_count: Number of contributions made

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "subproblem_complete",
        {
            "session_id": session_id,
            "sub_problem_index": sub_problem_index,
            "sub_problem_id": sub_problem_id,
            "goal": goal,
            "cost": cost,
            "duration_seconds": duration_seconds,
            "expert_panel": expert_panel,
            "contribution_count": contribution_count,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def meta_synthesis_started_event(
    session_id: str,
    sub_problem_count: int,
    total_contributions: int,
    total_cost: float,
) -> str:
    """Create SSE event for meta-synthesis start.

    Args:
        session_id: Session identifier
        sub_problem_count: Number of sub-problems synthesized
        total_contributions: Total contributions across all sub-problems
        total_cost: Total cost so far

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "meta_synthesis_started",
        {
            "session_id": session_id,
            "sub_problem_count": sub_problem_count,
            "total_contributions": total_contributions,
            "total_cost": total_cost,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def meta_synthesis_complete_event(
    session_id: str,
    synthesis: str,
    word_count: int,
) -> str:
    """Create SSE event for meta-synthesis completion.

    Args:
        session_id: Session identifier
        synthesis: Full meta-synthesis markdown text
        word_count: Word count of meta-synthesis

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "meta_synthesis_complete",
        {
            "session_id": session_id,
            "synthesis": synthesis,
            "word_count": word_count,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def phase_cost_breakdown_event(
    session_id: str,
    phase_costs: dict[str, float],
    total_cost: float,
) -> str:
    """Create SSE event for phase cost breakdown.

    Args:
        session_id: Session identifier
        phase_costs: Dict mapping phase names to costs
        total_cost: Total cost across all phases

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "phase_cost_breakdown",
        {
            "session_id": session_id,
            "phase_costs": phase_costs,
            "total_cost": total_cost,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
