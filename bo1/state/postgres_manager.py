"""PostgreSQL manager for context collection and research caching.

Provides CRUD operations for:
- user_context: Persistent business context per user
- session_clarifications: Expert clarification questions during deliberation
- research_cache: External research results with semantic embeddings

Uses connection pooling for improved performance and resource management.
"""

from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json, RealDictCursor

from bo1.config import Settings

# Global connection pool (initialized once)
_connection_pool: pool.ThreadedConnectionPool | None = None


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    """Get cached Settings instance.

    Returns:
        Settings instance (cached)
    """
    return Settings(
        anthropic_api_key="dummy",  # Not needed for DB operations
        voyage_api_key="dummy",  # Not needed for DB operations
    )


def get_connection_pool() -> pool.ThreadedConnectionPool:
    """Get or create the global connection pool.

    Returns:
        ThreadedConnectionPool instance

    Raises:
        ValueError: If DATABASE_URL is not configured
    """
    global _connection_pool

    if _connection_pool is None:
        settings = _get_settings()

        if not settings.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Create connection pool with min=1, max=20 connections
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            dsn=settings.database_url,
            cursor_factory=RealDictCursor,
        )

    return _connection_pool


@contextmanager
def db_session() -> Any:
    """Context manager for database transactions.

    Provides automatic connection pooling, commit/rollback, and cleanup.

    Yields:
        Database connection from pool

    Examples:
        >>> with db_session() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT * FROM user_context WHERE user_id = %s", (user_id,))
        ...         result = cur.fetchone()
    """
    pool_instance = get_connection_pool()
    conn = pool_instance.getconn()

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool_instance.putconn(conn)


def get_connection() -> psycopg2.extensions.connection:
    """Get PostgreSQL database connection.

    DEPRECATED: Use db_session() context manager instead for automatic cleanup.

    Returns:
        Database connection with RealDictCursor for dict-like rows
    """
    settings = _get_settings()
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
    with db_session() as conn:
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


def save_user_context(user_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """Save or update user's business context.

    Args:
        user_id: User ID (from Supabase auth)
        context: Dictionary with context fields (business_model, target_market, etc.)

    Returns:
        Saved context with timestamps
    """
    with db_session() as conn:
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
            return dict(result) if result else {}


def delete_user_context(user_id: str) -> bool:
    """Delete user's business context.

    Args:
        user_id: User ID (from Supabase auth)

    Returns:
        True if context was deleted, False if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_context WHERE user_id = %s",
                (user_id,),
            )
            deleted: bool = cur.rowcount > 0
            return deleted


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
    with db_session() as conn:
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
            return dict(result) if result else {}


def get_session_clarifications(session_id: str) -> list[dict[str, Any]]:
    """Get all clarifications for a session.

    Args:
        session_id: Deliberation session ID (string, not UUID)

    Returns:
        List of clarification records
    """
    with db_session() as conn:
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
    # Validate max_age_days BEFORE database connection (prevents injection early)
    if max_age_days is not None:
        if not isinstance(max_age_days, int):
            raise ValueError(f"days must be an integer, got {type(max_age_days).__name__}")
        if max_age_days < 0:
            raise ValueError(f"days must be non-negative, got {max_age_days}")

    with db_session() as conn:
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
                # Use SafeQueryBuilder for interval filter (prevents SQL injection)
                from bo1.utils.sql_safety import SafeQueryBuilder

                # Create builder from existing query
                builder = SafeQueryBuilder.__new__(SafeQueryBuilder)
                builder.query = query
                builder.params = params
                builder.add_interval_filter("research_date", max_age_days)
                query, params = builder.build()
            else:
                query += " AND research_date >= NOW() - (freshness_days || ' days')::interval"

            query += " ORDER BY research_date DESC LIMIT 1"

            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None


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
    with db_session() as conn:
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
                    Json(sources) if sources else None,  # Use psycopg2.extras.Json for JSONB
                    len(sources) if sources else 0,
                    category,
                    industry,
                    freshness_days,
                    tokens_used,
                    research_cost_usd,
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


def update_research_access(cache_id: str) -> None:
    """Update access count and last_accessed_at for cached research.

    Args:
        cache_id: Research cache record ID (string representation of UUID)
    """
    with db_session() as conn:
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


def get_research_cache_stats() -> dict[str, Any]:
    """Get research cache analytics and statistics.

    Returns:
        Dictionary with cache statistics:
        {
            "total_cached_results": int,
            "cache_hit_rate_30d": float,  # Percentage (0-100)
            "cost_savings_30d": float,  # USD
            "top_cached_questions": [  # Top 10 by access_count
                {
                    "id": str,
                    "question": str,
                    "category": str,
                    "access_count": int,
                    "last_accessed_at": str,
                }
            ]
        }
    """
    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total cached results
            cur.execute("SELECT COUNT(*) as total FROM research_cache")
            total_result = cur.fetchone()
            total_cached_results = total_result["total"] if total_result else 0

            # Cache hit rate (30 days) - access_count > 1 means cache hit
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE access_count > 1) as hits,
                    COUNT(*) as total
                FROM research_cache
                WHERE research_date >= NOW() - INTERVAL '30 days'
                """
            )
            hit_rate_result = cur.fetchone()
            hits = hit_rate_result["hits"] if hit_rate_result else 0
            total_30d = hit_rate_result["total"] if hit_rate_result else 0
            cache_hit_rate_30d = (hits / total_30d * 100) if total_30d > 0 else 0.0

            # Cost savings (30 days)
            # Assumption: Each cache hit saves $0.07 (avg web search + summarization)
            # vs $0.00006 embedding cost
            cost_per_hit_savings = 0.07 - 0.00006
            cost_savings_30d = hits * cost_per_hit_savings

            # Top cached questions by access_count
            cur.execute(
                """
                SELECT
                    id::text,
                    question,
                    category,
                    access_count,
                    last_accessed_at
                FROM research_cache
                ORDER BY access_count DESC
                LIMIT 10
                """
            )
            top_questions = [dict(row) for row in cur.fetchall()]

            # Convert datetime to ISO string
            for q in top_questions:
                if q.get("last_accessed_at"):
                    q["last_accessed_at"] = q["last_accessed_at"].isoformat()

            return {
                "total_cached_results": total_cached_results,
                "cache_hit_rate_30d": round(cache_hit_rate_30d, 2),
                "cost_savings_30d": round(cost_savings_30d, 2),
                "top_cached_questions": top_questions,
            }


def delete_research_cache_entry(cache_id: str) -> bool:
    """Delete a specific research cache entry.

    Args:
        cache_id: Research cache record ID (string representation of UUID)

    Returns:
        True if deleted, False if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM research_cache
                WHERE id = %s
                """,
                (cache_id,),
            )
            # Cast to int to satisfy mypy
            rowcount: int = cur.rowcount if cur.rowcount is not None else 0
            return rowcount > 0


def get_stale_research_cache_entries(days_old: int = 90) -> list[dict[str, Any]]:
    """Get research cache entries that are older than specified days.

    Args:
        days_old: Number of days to consider stale (default: 90)

    Returns:
        List of stale cache entries with id, question, category, research_date
    """
    # Validate days_old BEFORE database connection (prevents injection early)
    if not isinstance(days_old, int):
        raise ValueError(f"days must be an integer, got {type(days_old).__name__}")
    if days_old < 0:
        raise ValueError(f"days must be non-negative, got {days_old}")

    # Use SafeQueryBuilder to prevent SQL injection
    from bo1.utils.sql_safety import SafeQueryBuilder

    with db_session() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build safe query with parameterized interval
            builder = SafeQueryBuilder(
                """
                SELECT
                    id::text,
                    question,
                    category,
                    industry,
                    research_date,
                    freshness_days
                FROM research_cache
                WHERE 1=1
                """
            )
            # Add interval filter (safe - validates integer and uses f-string internally)
            builder.add_interval_filter("research_date", days_old, operator="<")
            builder.add_order_by("research_date", "ASC")

            query, params = builder.build()
            cur.execute(query, params)
            entries = [dict(row) for row in cur.fetchall()]

            # Convert datetime to ISO string
            for entry in entries:
                if entry.get("research_date"):
                    entry["research_date"] = entry["research_date"].isoformat()

            return entries
