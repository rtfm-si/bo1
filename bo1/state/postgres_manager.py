"""PostgreSQL manager - backward compatibility shim.

This module re-exports all functions from the new repository pattern.
Import from here for backward compatibility, or import directly from:
- bo1.state.database (for db_session, connection pool functions)
- bo1.state.repositories (for domain-specific operations)
"""

from datetime import datetime
from typing import Any

# =============================================================================
# Re-export from database.py
# =============================================================================
from bo1.state.database import db_session, get_connection_pool

# =============================================================================
# Re-export from repositories
# =============================================================================
from bo1.state.repositories import (
    cache_repository,
    contribution_repository,
    session_repository,
    user_repository,
)

__all__ = [
    "db_session",
    "get_connection_pool",
    "cache_repository",
    "contribution_repository",
    "session_repository",
    "user_repository",
]

# =============================================================================
# User Context Functions
# =============================================================================


def load_user_context(user_id: str) -> dict[str, Any] | None:
    return user_repository.get_context(user_id)


def save_user_context(user_id: str, context: dict[str, Any]) -> dict[str, Any]:
    return user_repository.save_context(user_id, context)


def delete_user_context(user_id: str) -> bool:
    return user_repository.delete_context(user_id)


def ensure_user_exists(
    user_id: str,
    email: str | None = None,
    auth_provider: str = "supertokens",
    subscription_tier: str = "free",
) -> bool:
    return user_repository.ensure_exists(user_id, email, auth_provider, subscription_tier)


def get_user(user_id: str) -> dict[str, Any] | None:
    return user_repository.get(user_id)


# =============================================================================
# Session Functions
# =============================================================================


def save_session(
    session_id: str,
    user_id: str,
    problem_statement: str,
    problem_context: dict[str, Any] | None = None,
    status: str = "created",
) -> dict[str, Any]:
    return session_repository.create(
        session_id, user_id, problem_statement, problem_context, status
    )


def get_session(session_id: str) -> dict[str, Any] | None:
    return session_repository.get(session_id)


def update_session_status(
    session_id: str,
    status: str,
    phase: str | None = None,
    total_cost: float | None = None,
    round_number: int | None = None,
    synthesis_text: str | None = None,
    final_recommendation: str | None = None,
) -> bool:
    return session_repository.update_status(
        session_id, status, phase, total_cost, round_number, synthesis_text, final_recommendation
    )


def update_session_phase(session_id: str, phase: str) -> bool:
    return session_repository.update_phase(session_id, phase)


def get_user_sessions(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    return session_repository.list_by_user(user_id, limit, offset, status_filter, include_deleted)


def get_session_metadata(session_id: str) -> dict[str, Any] | None:
    return session_repository.get_metadata(session_id)


def save_session_event(
    session_id: str,
    event_type: str,
    sequence: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    return session_repository.save_event(session_id, event_type, sequence, data)


def get_session_events(session_id: str) -> list[dict[str, Any]]:
    return session_repository.get_events(session_id)


def save_session_tasks(
    session_id: str,
    tasks: list[dict[str, Any]],
    total_tasks: int,
    extraction_confidence: float,
    synthesis_sections_analyzed: list[str],
    user_id: str | None = None,
) -> dict[str, Any]:
    return session_repository.save_tasks(
        session_id, tasks, total_tasks, extraction_confidence, synthesis_sections_analyzed, user_id
    )


def get_session_tasks(session_id: str) -> dict[str, Any] | None:
    return session_repository.get_tasks(session_id)


def save_session_synthesis(session_id: str, synthesis_text: str) -> bool:
    return session_repository.save_synthesis(session_id, synthesis_text)


def get_session_synthesis(session_id: str) -> str | None:
    return session_repository.get_synthesis(session_id)


# =============================================================================
# Session Clarifications
# =============================================================================


def save_clarification(
    session_id: str,
    question: str,
    asked_by_persona: str | None = None,
    priority: str | None = None,
    reason: str | None = None,
    answer: str | None = None,
    answered_at: datetime | None = None,
    asked_at_round: int | None = None,
) -> dict[str, Any]:
    return session_repository.save_clarification(
        session_id,
        question,
        asked_by_persona,
        priority,
        reason,
        answer,
        answered_at,
        asked_at_round,
    )


def get_session_clarifications(session_id: str) -> list[dict[str, Any]]:
    return session_repository.get_clarifications(session_id)


# =============================================================================
# Research Cache Functions
# =============================================================================


def find_cached_research(
    question_embedding: list[float],
    similarity_threshold: float = 0.85,
    category: str | None = None,
    industry: str | None = None,
    max_age_days: int | None = None,
) -> dict[str, Any] | None:
    return cache_repository.find_by_embedding(
        question_embedding, similarity_threshold, category, industry, max_age_days
    )


def find_similar_research(
    question_embedding: list[float],
    similarity_threshold: float = 0.85,
    limit: int = 5,
    max_age_days: int | None = None,
) -> list[dict[str, Any]]:
    return cache_repository.find_similar(
        question_embedding, similarity_threshold, limit, max_age_days
    )


def save_research_result(
    question: str,
    embedding: list[float],
    summary: str,
    sources: list[dict[str, Any]] | None = None,
    confidence: str = "medium",
    category: str | None = None,
    industry: str | None = None,
    freshness_days: int = 90,
    tokens_used: int | None = None,
    research_cost_usd: float | None = None,
) -> dict[str, Any]:
    return cache_repository.save(
        question,
        embedding,
        summary,
        sources,
        confidence,
        category,
        industry,
        freshness_days,
        tokens_used,
        research_cost_usd,
    )


def save_research_results_batch(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return cache_repository.save_batch(results)


def update_research_access(cache_id: str) -> None:
    return cache_repository.update_access(cache_id)


def get_research_cache_stats() -> dict[str, Any]:
    return cache_repository.get_stats()


def delete_research_cache_entry(cache_id: str) -> bool:
    return cache_repository.delete(cache_id)


def get_stale_research_cache_entries(days_old: int = 90) -> list[dict[str, Any]]:
    return cache_repository.get_stale(days_old)


# =============================================================================
# Contribution Functions
# =============================================================================


def save_contribution(
    session_id: str,
    persona_code: str,
    content: str,
    round_number: int,
    phase: str,
    cost: float = 0.0,
    tokens: int = 0,
    model: str = "unknown",
    embedding: list[float] | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    return contribution_repository.save_contribution(
        session_id,
        persona_code,
        content,
        round_number,
        phase,
        cost,
        tokens,
        model,
        embedding,
        user_id,
    )


def save_contribution_embedding(contribution_id: str, embedding: list[float]) -> bool:
    return contribution_repository.save_contribution_embedding(contribution_id, embedding)


def get_contribution_embedding(contribution_id: str) -> list[float] | None:
    return contribution_repository.get_contribution_embedding(contribution_id)


def save_recommendation(
    session_id: str,
    persona_code: str,
    recommendation: str,
    reasoning: str | None = None,
    confidence: float | None = None,
    conditions: list[str] | None = None,
    weight: float | None = None,
    sub_problem_index: int | None = None,
    persona_name: str | None = None,
) -> dict[str, Any]:
    return contribution_repository.save_recommendation(
        session_id,
        persona_code,
        recommendation,
        reasoning,
        confidence,
        conditions,
        weight,
        sub_problem_index,
        persona_name,
    )


def save_sub_problem_result(
    session_id: str,
    sub_problem_index: int,
    goal: str,
    synthesis: str | None = None,
    expert_summaries: dict[str, str] | None = None,
    cost: float | None = None,
    duration_seconds: int | None = None,
    contribution_count: int | None = None,
) -> dict[str, Any]:
    return contribution_repository.save_sub_problem_result(
        session_id,
        sub_problem_index,
        goal,
        synthesis,
        expert_summaries,
        cost,
        duration_seconds,
        contribution_count,
    )


def save_facilitator_decision(
    session_id: str,
    round_number: int,
    action: str,
    reasoning: str | None = None,
    next_speaker: str | None = None,
    moderator_type: str | None = None,
    research_query: str | None = None,
    sub_problem_index: int | None = None,
) -> dict[str, Any]:
    return contribution_repository.save_facilitator_decision(
        session_id,
        round_number,
        action,
        reasoning,
        next_speaker,
        moderator_type,
        research_query,
        sub_problem_index,
    )
