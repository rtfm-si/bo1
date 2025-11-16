"""PostgreSQL manager for context collection and research caching.

Provides CRUD operations for:
- user_context: Persistent business context per user
- session_clarifications: Expert clarification questions during deliberation
- research_cache: External research results with semantic embeddings
"""

from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from bo1.config import Settings


def get_connection() -> psycopg2.extensions.connection:
    """Get PostgreSQL database connection.

    Returns:
        Database connection with RealDictCursor for dict-like rows
    """
    settings = Settings(
        anthropic_api_key="dummy",  # Not needed for DB operations
        voyage_api_key="dummy",  # Not needed for DB operations
    )
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=RealDictCursor,
    )


# =============================================================================
# User Context Functions
# =============================================================================


def load_user_context(user_id: str) -> dict[str, Any] | None:
    """Load user's business context from database.

    Args:
        user_id: User ID (from Supabase auth)

    Returns:
        Dictionary with context fields or None if not found
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT business_model, target_market, product_description,
                       revenue, customers, growth_rate, competitors, website,
                       created_at, updated_at
                FROM user_context
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def save_user_context(user_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Save or update user's business context.

    Args:
        user_id: User ID (from Supabase auth)
        context: Dictionary with context fields (business_model, target_market, etc.)

    Returns:
        Saved context with timestamps
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_context (
                    user_id, business_model, target_market, product_description,
                    revenue, customers, growth_rate, competitors, website
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    business_model = EXCLUDED.business_model,
                    target_market = EXCLUDED.target_market,
                    product_description = EXCLUDED.product_description,
                    revenue = EXCLUDED.revenue,
                    customers = EXCLUDED.customers,
                    growth_rate = EXCLUDED.growth_rate,
                    competitors = EXCLUDED.competitors,
                    website = EXCLUDED.website,
                    updated_at = NOW()
                RETURNING business_model, target_market, product_description,
                          revenue, customers, growth_rate, competitors, website,
                          created_at, updated_at
                """,
                (
                    user_id,
                    context.get("business_model"),
                    context.get("target_market"),
                    context.get("product_description"),
                    context.get("revenue"),
                    context.get("customers"),
                    context.get("growth_rate"),
                    context.get("competitors"),
                    context.get("website"),
                ),
            )
            result = cur.fetchone()
            conn.commit()
            return dict(result) if result else {}
    finally:
        conn.close()


def delete_user_context(user_id: str) -> bool:
    """Delete user's business context.

    Args:
        user_id: User ID (from Supabase auth)

    Returns:
        True if context was deleted, False if not found
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_context WHERE user_id = %s",
                (user_id,),
            )
            deleted: bool = cur.rowcount > 0
            conn.commit()
            return deleted
    finally:
        conn.close()


# =============================================================================
# Session Clarifications Functions
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
    """Save a clarification question from an expert.

    Args:
        session_id: Deliberation session ID (string, not UUID)
        question: The clarification question
        asked_by_persona: Persona code who asked (optional)
        priority: CRITICAL or NICE_TO_HAVE (optional)
        reason: Why this question is important (optional)
        answer: User's answer (optional)
        answered_at: When answer was provided (optional)
        asked_at_round: Round number when question was asked (optional)

    Returns:
        Saved clarification record
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO session_clarifications (
                    session_id, question, asked_by_persona, priority,
                    reason, answer, answered_at, asked_at_round
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, question, asked_by_persona, priority,
                          reason, answer, answered_at, asked_at_round, created_at
                """,
                (
                    session_id,
                    question,
                    asked_by_persona,
                    priority,
                    reason,
                    answer,
                    answered_at,
                    asked_at_round,
                ),
            )
            result = cur.fetchone()
            conn.commit()
            return dict(result) if result else {}
    finally:
        conn.close()


def get_session_clarifications(session_id: str) -> list[dict[str, Any]]:
    """Get all clarifications for a session.

    Args:
        session_id: Deliberation session ID (string, not UUID)

    Returns:
        List of clarification records
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, question, asked_by_persona, priority,
                       reason, answer, answered_at, asked_at_round, created_at
                FROM session_clarifications
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


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
    """Find cached research result using semantic similarity.

    Args:
        question_embedding: Vector embedding of the question (1536 dimensions for ada-002)
        similarity_threshold: Minimum cosine similarity (0.0-1.0)
        category: Optional category filter (e.g., 'saas_metrics')
        industry: Optional industry filter (e.g., 'saas')
        max_age_days: Maximum age in days (uses freshness_days if not specified)

    Returns:
        Cached research result or None if no match found
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # For now, we'll use a simple approach without vector similarity
            # because pgvector requires proper setup. We'll use category/industry filters
            # and return the most recent match.
            # TODO: Implement proper vector similarity search with pgvector

            query = """
                SELECT id, question, answer_summary, confidence, sources,
                       source_count, category, industry, research_date,
                       access_count, last_accessed_at, freshness_days,
                       tokens_used, research_cost_usd
                FROM research_cache
                WHERE 1=1
            """
            params: list[Any] = []

            if category:
                query += " AND category = %s"
                params.append(category)

            if industry:
                query += " AND industry = %s"
                params.append(industry)

            if max_age_days:
                query += " AND research_date >= NOW() - INTERVAL '%s days'"
                params.append(max_age_days)
            else:
                query += " AND research_date >= NOW() - (freshness_days || ' days')::interval"

            query += " ORDER BY research_date DESC LIMIT 1"

            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


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
    """Save research result to cache.

    Args:
        question: The research question
        embedding: Vector embedding of the question (1536 dimensions)
        summary: Summarized answer
        sources: List of source URLs/citations (optional)
        confidence: high, medium, or low
        category: Category (e.g., 'saas_metrics', 'pricing')
        industry: Industry (e.g., 'saas', 'ecommerce')
        freshness_days: How long result stays fresh (default 90)
        tokens_used: Number of tokens used in research
        research_cost_usd: Cost of research in USD

    Returns:
        Saved research record
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO research_cache (
                    question, question_embedding, answer_summary, confidence,
                    sources, source_count, category, industry, freshness_days,
                    tokens_used, research_cost_usd
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, question, answer_summary, confidence, sources,
                          source_count, category, industry, research_date,
                          access_count, last_accessed_at, freshness_days,
                          tokens_used, research_cost_usd
                """,
                (
                    question,
                    embedding,
                    summary,
                    confidence,
                    sources,
                    len(sources) if sources else 0,
                    category,
                    industry,
                    freshness_days,
                    tokens_used,
                    research_cost_usd,
                ),
            )
            result = cur.fetchone()
            conn.commit()
            return dict(result) if result else {}
    finally:
        conn.close()


def update_research_access(cache_id: str) -> None:
    """Update access count and last_accessed_at for cached research.

    Args:
        cache_id: Research cache record ID (string representation of UUID)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE research_cache
                SET access_count = access_count + 1,
                    last_accessed_at = NOW()
                WHERE id = %s
                """,
                (cache_id,),
            )
            conn.commit()
    finally:
        conn.close()
