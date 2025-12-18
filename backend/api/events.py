"""Server-Sent Events (SSE) formatting utilities.

Provides functions to format deliberation events as SSE messages for
real-time streaming to web clients.

Includes sequence tracking for session resume support via Last-Event-ID.

Schema Documentation:
    See docs/SSE_EVENTS.md for complete event schema contracts.

Pydantic Schemas:
    See bo1/events/schemas.py for typed Pydantic models.

TypeScript Interfaces:
    See frontend/src/lib/api/sse-events.ts for frontend types.

Event Types (30 total):
    Session: session_started
    Decomposition: decomposition_started, decomposition_complete
    Persona: persona_selection_started, persona_selected, persona_selection_complete
    Sub-Problem: subproblem_started, subproblem_complete
    Round: initial_round_started, round_started, contribution, moderator_intervention
    Convergence: convergence
    Voting: voting_started, persona_vote, voting_complete
    Synthesis: synthesis_started, synthesis_complete, meta_synthesis_started, meta_synthesis_complete
    Completion: complete
    Error: error
    Clarification: clarification_required, clarification_requested, clarification_answered
    Context: context_insufficient
    Quality: quality_metrics_update
    Cost: phase_cost_breakdown
    Node: node_start, node_end
    Facilitator: facilitator_decision
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# SSE event version for forward compatibility
SSE_EVENT_VERSION = 1


def get_next_sequence(redis_client: Any, session_id: str) -> int:
    """Get the next sequence number for a session's events.

    Uses Redis INCR for atomic sequence generation.

    Args:
        redis_client: Redis client instance
        session_id: Session identifier

    Returns:
        Next sequence number (1-indexed)
    """
    if redis_client is None:
        return 0  # No Redis = no sequence tracking

    key = f"event_sequence:{session_id}"
    return redis_client.incr(key)


def make_event_id(session_id: str, sequence: int) -> str:
    """Create event ID from session and sequence.

    Format: {session_id}:{sequence}

    Args:
        session_id: Session identifier
        sequence: Event sequence number

    Returns:
        Event ID string
    """
    return f"{session_id}:{sequence}"


def parse_event_id(event_id: str) -> tuple[str, int] | None:
    """Parse event ID into session_id and sequence.

    Args:
        event_id: Event ID string (format: session_id:sequence)

    Returns:
        Tuple of (session_id, sequence) or None if invalid
    """
    if not event_id or ":" not in event_id:
        return None

    try:
        # Handle session IDs that contain colons (e.g., "bo1_abc123:456")
        parts = event_id.rsplit(":", 1)
        if len(parts) != 2:
            return None

        session_id, seq_str = parts
        sequence = int(seq_str)
        return (session_id, sequence)
    except (ValueError, IndexError):
        return None


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
        SSE-formatted string with event_version field

    Examples:
        >>> event = format_sse_event("test", {"message": "hello"})
        >>> print(event)
        event: test
        data: {"message": "hello", "event_version": 1}

        >>>
    """
    lines = []

    # Add event ID if provided
    if event_id:
        lines.append(f"id: {event_id}")

    # Add event type
    lines.append(f"event: {event_type}")

    # Add event_version to data for forward compatibility (P1: SSE versioning)
    versioned_data = {**data, "event_version": SSE_EVENT_VERSION}

    # Add data as JSON
    data_json = json.dumps(versioned_data)
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
    archetype: str | None = None,
    domain_expertise: list[str] | None = None,
    summary: dict[str, Any] | None = None,
    contribution_type: str | None = None,
    sub_problem_index: int | None = None,
) -> str:
    """Create SSE event for persona contribution.

    Args:
        session_id: Session identifier
        persona_code: Persona code (e.g., "CFO")
        persona_name: Persona display name
        contribution: The contribution text
        round_number: Current round number
        archetype: Persona archetype/role (e.g., "Financial Strategy Advisor")
        domain_expertise: List of expertise areas
        summary: Structured summary of the contribution
        contribution_type: Type of contribution ("initial" or "parallel")
        sub_problem_index: Sub-problem index for tab filtering

    Returns:
        SSE-formatted event string
    """
    data: dict[str, Any] = {
        "session_id": session_id,
        "persona_code": persona_code,
        "persona_name": persona_name,
        "content": contribution,
        "round": round_number,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Include optional fields if provided
    if archetype is not None:
        data["archetype"] = archetype
    if domain_expertise is not None:
        data["domain_expertise"] = domain_expertise
    if summary is not None:
        data["summary"] = summary
    if contribution_type is not None:
        data["contribution_type"] = contribution_type
    if sub_problem_index is not None:
        data["sub_problem_index"] = sub_problem_index

    return format_sse_event("contribution", data)


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
    sub_problem_index: int = 0,
    novelty_score: float | None = None,
    conflict_score: float | None = None,
    drift_events: int = 0,
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
        sub_problem_index: Sub-problem index for tab filtering
        novelty_score: Average novelty of recent contributions (0-1)
        conflict_score: Level of disagreement between experts (0-1)
        drift_events: Number of problem drift events detected

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
            "sub_problem_index": sub_problem_index,
            "novelty_score": novelty_score,
            "conflict_score": conflict_score,
            "drift_events": drift_events,
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


def clarification_required_event(
    session_id: str,
    questions: list[dict[str, Any]],
    phase: str,
    reason: str,
) -> str:
    """Create SSE event for pre-deliberation clarification questions.

    This event is emitted when critical information gaps are identified
    during problem decomposition, BEFORE deliberation starts.

    Args:
        session_id: Session identifier
        questions: List of question dicts with 'question', 'reason', 'priority'
        phase: Phase when clarification is needed ('pre_deliberation' or 'mid_deliberation')
        reason: Overall reason why clarification is needed

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "clarification_required",
        {
            "session_id": session_id,
            "questions": questions,
            "phase": phase,
            "reason": reason,
            "question_count": len(questions),
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
    sub_problem_index: int | None = None,
) -> str:
    """Create SSE event for individual persona selection.

    Args:
        session_id: Session identifier
        persona: Persona dict with code, name, display_name, domain_expertise
        rationale: Why this expert was chosen
        order: Selection order (1-indexed)
        sub_problem_index: Sub-problem index for multi-problem meetings

    Returns:
        SSE-formatted event string
    """
    data = {
        "session_id": session_id,
        "persona": persona,
        "rationale": rationale,
        "order": order,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if sub_problem_index is not None:
        data["sub_problem_index"] = sub_problem_index
    return format_sse_event("persona_selected", data)


def persona_selection_complete_event(
    session_id: str,
    personas: list[str],
    sub_problem_index: int | None = None,
) -> str:
    """Create SSE event for persona selection completion.

    Args:
        session_id: Session identifier
        personas: List of selected persona codes
        sub_problem_index: Sub-problem index for multi-problem meetings

    Returns:
        SSE-formatted event string
    """
    data = {
        "session_id": session_id,
        "personas": personas,
        "count": len(personas),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if sub_problem_index is not None:
        data["sub_problem_index"] = sub_problem_index
    return format_sse_event("persona_selection_complete", data)


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
    sub_problem_index: int | None = None,
) -> str:
    """Create SSE event for synthesis completion.

    Args:
        session_id: Session identifier
        synthesis: Full synthesis markdown text
        word_count: Word count of synthesis
        sub_problem_index: Sub-problem index for tab filtering (None = meta-synthesis)

    Returns:
        SSE-formatted event string
    """
    data: dict[str, Any] = {
        "session_id": session_id,
        "synthesis": synthesis,
        "word_count": word_count,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if sub_problem_index is not None:
        data["sub_problem_index"] = sub_problem_index

    return format_sse_event("synthesis_complete", data)


def subproblem_complete_event(
    session_id: str,
    sub_problem_index: int,
    sub_problem_id: str,
    goal: str,
    synthesis: str,
    cost: float,
    duration_seconds: float,
    expert_panel: list[str],
    contribution_count: int,
    expert_summaries: dict[str, str] | None = None,
) -> str:
    """Create SSE event for sub-problem completion.

    AUDIT FIX (Priority 3, Task 3.2): Added expert_summaries parameter.

    Args:
        session_id: Session identifier
        sub_problem_index: 0-indexed sub-problem number
        sub_problem_id: Sub-problem identifier
        goal: Sub-problem goal
        synthesis: Conclusion/synthesis text for this sub-problem
        cost: Cost in USD for this sub-problem
        duration_seconds: Time taken in seconds
        expert_panel: List of expert codes who deliberated
        contribution_count: Number of contributions made
        expert_summaries: Per-expert contribution summaries (persona_code → summary text)

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
            "synthesis": synthesis,
            "cost": cost,
            "duration_seconds": duration_seconds,
            "expert_panel": expert_panel,
            "contribution_count": contribution_count,
            "expert_summaries": expert_summaries or {},
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


def context_insufficient_event(
    session_id: str,
    meta_ratio: float,
    expert_questions: list[str],
    reason: str,
    round_number: int,
    sub_problem_index: int = 0,
) -> str:
    """Create SSE event for context insufficiency detection.

    This event is emitted when >50% of contributions indicate experts
    are struggling with insufficient context. It gives users 3 choices:
    1. Provide additional details (answer expert questions)
    2. Continue with available information (best effort mode)
    3. End meeting with current insights

    Args:
        session_id: Session identifier
        meta_ratio: Ratio of meta-discussion contributions (0.0-1.0)
        expert_questions: Questions extracted from expert contributions
        reason: Human-readable explanation of the insufficiency
        round_number: Current round number
        sub_problem_index: Sub-problem index for context

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "context_insufficient",
        {
            "session_id": session_id,
            "meta_ratio": round(meta_ratio, 2),
            "expert_questions": expert_questions,
            "reason": reason,
            "round_number": round_number,
            "sub_problem_index": sub_problem_index,
            "choices": [
                {
                    "id": "provide_more",
                    "label": "Provide Additional Details",
                    "description": "Answer the questions our experts have raised",
                },
                {
                    "id": "continue",
                    "label": "Continue with Available Information",
                    "description": "Proceed with best-effort analysis based on what we know",
                },
                {
                    "id": "end",
                    "label": "End Meeting",
                    "description": "Generate summary with current insights and end",
                },
            ],
            "timeout_seconds": 120,  # 2 minute timeout
            "timeout_default": "continue",  # Default if no response
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def gap_detected_event(
    session_id: str,
    expected_seq: int,
    actual_seq: int,
    missed_count: int,
) -> str:
    """Create SSE event for sequence gap detection during reconnection.

    Emitted when a client reconnects and gaps are detected in the event
    sequence, indicating some events may have been lost.

    Args:
        session_id: Session identifier
        expected_seq: Expected next sequence number (resume_from + 1)
        actual_seq: Actual first sequence in replayed events
        missed_count: Number of events that appear to be missing

    Returns:
        SSE-formatted event string
    """
    return format_sse_event(
        "gap_detected",
        {
            "session_id": session_id,
            "expected_sequence": expected_seq,
            "actual_sequence": actual_seq,
            "missed_count": missed_count,
            "message": f"Detected {missed_count} potentially missed event(s). Consider refreshing for full data.",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def quality_metrics_update_event(
    session_id: str,
    round_number: int,
    exploration_score: float | None,
    convergence_score: float | None,
    focus_score: float | None,
    novelty_score: float | None,
    meeting_completeness_index: float | None,
    missing_aspects: list[str] | None = None,
    facilitator_guidance: str | None = None,
) -> str:
    """Create SSE event for meeting quality metrics update.

    Args:
        session_id: Session identifier
        round_number: Current round number
        exploration_score: Exploration coverage score (0-1)
        convergence_score: Agreement/convergence score (0-1)
        focus_score: On-topic ratio score (0-1)
        novelty_score: Novelty/uniqueness score (0-1)
        meeting_completeness_index: Composite quality metric (0-1)
        missing_aspects: List of aspect names that are missing/shallow
        facilitator_guidance: Guidance for next round (if any)

    Returns:
        SSE-formatted event string
    """
    data: dict[str, Any] = {
        "session_id": session_id,
        "round_number": round_number,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Add scores (always include with 0.0 default to prevent undefined in frontend)
    data["exploration_score"] = (
        round(exploration_score, 2) if exploration_score is not None else 0.0
    )
    data["convergence_score"] = (
        round(convergence_score, 2) if convergence_score is not None else 0.0
    )
    data["focus_score"] = round(focus_score, 2) if focus_score is not None else 0.0
    data["novelty_score"] = round(novelty_score, 2) if novelty_score is not None else 0.0
    data["meeting_completeness_index"] = (
        round(meeting_completeness_index, 2) if meeting_completeness_index is not None else 0.0
    )

    # Add missing aspects and guidance
    if missing_aspects:
        data["missing_aspects"] = missing_aspects
    if facilitator_guidance:
        data["facilitator_guidance"] = facilitator_guidance

    return format_sse_event("quality_metrics_update", data)
