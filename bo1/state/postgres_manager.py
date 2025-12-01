"""PostgreSQL manager for context collection and research caching.

Provides CRUD operations for:
- user_context: Persistent business context per user
- session_clarifications: Expert clarification questions during deliberation
- research_cache: External research results with semantic embeddings

Uses connection pooling for improved performance and resource management.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from typing import Any

from psycopg2 import pool
from psycopg2.extras import Json, RealDictCursor

from bo1.config import Settings

logger = logging.getLogger(__name__)

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

        # Import constants for pool configuration
        from bo1.constants import DatabaseConfig

        # Create connection pool with configurable limits
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=DatabaseConfig.POOL_MIN_CONNECTIONS,
            maxconn=DatabaseConfig.POOL_MAX_CONNECTIONS,
            dsn=settings.database_url,
            cursor_factory=RealDictCursor,
        )

    return _connection_pool


def get_pool_health() -> dict[str, Any]:
    """Get health status of the PostgreSQL connection pool.

    Returns:
        Dictionary with pool health metrics:
        - healthy: Whether pool is functioning correctly
        - pool_initialized: Whether pool exists
        - min_connections: Configured minimum connections
        - max_connections: Configured maximum connections
        - test_query_success: Whether SELECT 1 succeeded
        - error: Error message if unhealthy

    Examples:
        >>> health = get_pool_health()
        >>> print(health['healthy'])
        True
        >>> print(health['max_connections'])
        20
    """
    from bo1.constants import DatabaseConfig

    result: dict[str, Any] = {
        "healthy": False,
        "pool_initialized": _connection_pool is not None,
        "min_connections": DatabaseConfig.POOL_MIN_CONNECTIONS,
        "max_connections": DatabaseConfig.POOL_MAX_CONNECTIONS,
        "test_query_success": False,
        "error": None,
    }

    try:
        # Ensure pool exists
        pool_instance = get_connection_pool()
        result["pool_initialized"] = True

        # Test connection from pool with simple query
        conn = pool_instance.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS health_check")
                row = cur.fetchone()
                result["test_query_success"] = row is not None
                result["healthy"] = True
        finally:
            pool_instance.putconn(conn)

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"Pool health check failed: {e}")

    return result


def reset_connection_pool() -> None:
    """Reset the global connection pool.

    Closes all connections and clears the pool.
    Use after detecting unhealthy state to force reconnection.

    Note:
        This should be called cautiously as it may interrupt active queries.
    """
    global _connection_pool

    if _connection_pool is not None:
        try:
            _connection_pool.closeall()
            logger.info("Connection pool closed and reset")
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
        finally:
            _connection_pool = None


@contextmanager
def db_session(
    user_id: str | None = None,
) -> Any:  # Generator[connection, None, None] would be ideal but psycopg2 typing is complex
    """Context manager for database transactions with RLS support.

    Provides automatic connection pooling, commit/rollback, cleanup, and
    Row-Level Security (RLS) context setting.

    Args:
        user_id: Optional user ID for RLS policies. When provided, sets
                 app.current_user_id session variable for RLS enforcement.

    Yields:
        psycopg2.extensions.connection: PostgreSQL connection from pool

    Examples:
        >>> # Without RLS context (admin operations)
        >>> with db_session() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT * FROM user_context WHERE user_id = %s", (user_id,))
        ...         result = cur.fetchone()

        >>> # With RLS context (user-scoped queries)
        >>> with db_session(user_id="user_123") as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT * FROM sessions")  # RLS automatically filters to user_123
        ...         result = cur.fetchall()

    Note:
        Return type is Any due to psycopg2's complex typing. The actual type is
        psycopg2.extensions.connection, but avoiding the import for simplicity.
    """
    pool_instance = get_connection_pool()
    conn = pool_instance.getconn()

    try:
        # Set RLS context if user_id provided
        if user_id:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_user_id = %s", (user_id,))
                logger.debug(f"RLS context set for user: {user_id}")

        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool_instance.putconn(conn)


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
    """Find cached research result using vector similarity search with HNSW index.

    Uses pgvector's HNSW index for fast cosine similarity search.
    Returns the most similar cached result that meets the threshold.

    Args:
        question_embedding: Vector embedding of the question (1024 dimensions for voyage-3)
        similarity_threshold: Minimum cosine similarity (0.0-1.0, default 0.85)
        category: Optional category filter (e.g., 'saas_metrics')
        industry: Optional industry filter (e.g., 'saas')
        max_age_days: Maximum age in days (uses freshness_days if not specified)

    Returns:
        Cached research result with highest similarity, or None if no match found
    """
    # Validate max_age_days BEFORE database connection (prevents injection early)
    if max_age_days is not None:
        if not isinstance(max_age_days, int):
            raise ValueError(f"days must be an integer, got {type(max_age_days).__name__}")
        if max_age_days < 0:
            raise ValueError(f"days must be non-negative, got {max_age_days}")

    # Use new vector similarity search function
    similar_results = find_similar_research(
        question_embedding=question_embedding,
        similarity_threshold=similarity_threshold,
        limit=10,  # Get top 10 for filtering by category/industry
        max_age_days=max_age_days,
    )

    if not similar_results:
        return None

    # Filter by category/industry if specified
    filtered_results = similar_results
    if category:
        filtered_results = [r for r in filtered_results if r.get("category") == category]
    if industry:
        filtered_results = [r for r in filtered_results if r.get("industry") == industry]

    # Return the most similar result (first in list, already ordered by similarity)
    return filtered_results[0] if filtered_results else None


def find_similar_research(
    question_embedding: list[float],
    similarity_threshold: float = 0.85,
    limit: int = 5,
    max_age_days: int | None = None,
) -> list[dict[str, Any]]:
    """Find similar research questions using vector similarity search.

    Uses HNSW index for fast cosine similarity search with pgvector.

    Args:
        question_embedding: Vector embedding of the query question (1024 dimensions)
        similarity_threshold: Minimum cosine similarity (0.0-1.0, default 0.85)
        limit: Maximum number of results to return
        max_age_days: Only return results from last N days (None = no limit)

    Returns:
        List of similar research results, ordered by similarity (highest first)
        Each result includes:
        - All research_cache fields
        - similarity: float (cosine similarity score 0.0-1.0)

    Example:
        >>> from bo1.llm.embeddings import generate_embedding
        >>> embedding = generate_embedding("What is the market size?", input_type="query")
        >>> similar = find_similar_research(embedding, similarity_threshold=0.85)
        >>> if similar:
        ...     print(f"Found cached answer (similarity={similar[0]['similarity']:.3f})")
        ...     print(similar[0]['answer_summary'])
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Build query with vector similarity using cosine distance operator (<=>)
            # Note: 1 - (vec1 <=> vec2) converts distance to similarity
            # pgvector's <=> operator returns cosine distance (0=identical, 2=opposite)
            # So similarity = 1 - (distance / 2) to get range 0.0-1.0

            query = """
                SELECT
                    id, question, answer_summary, confidence, sources,
                    source_count, category, industry, research_date,
                    access_count, last_accessed_at, freshness_days,
                    tokens_used, research_cost_usd,
                    1 - (question_embedding <=> %s::vector) AS similarity
                FROM research_cache
                WHERE question_embedding IS NOT NULL
            """

            params: list[Any] = [question_embedding]

            # Add age filter if specified
            if max_age_days is not None:
                query += " AND research_date > NOW() - INTERVAL '%s days'"
                params.append(max_age_days)

            # Filter by similarity threshold and order by similarity
            query += """
                AND (1 - (question_embedding <=> %s::vector)) >= %s
                ORDER BY question_embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([question_embedding, similarity_threshold, question_embedding, limit])

            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]

            return results


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


def save_research_results_batch(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Batch save multiple research results in a single transaction.

    More efficient than individual save_research_result() calls when
    saving multiple results (e.g., from parallel research).

    Args:
        results: List of research result dicts, each containing:
            - question: str
            - embedding: list[float] (1536 dimensions)
            - summary: str
            - sources: list[dict] (optional)
            - confidence: str (default "medium")
            - category: str (optional)
            - industry: str (optional)
            - freshness_days: int (default 90)
            - tokens_used: int (optional)
            - research_cost_usd: float (optional)

    Returns:
        List of saved research records with IDs
    """
    if not results:
        return []

    with db_session() as conn:
        with conn.cursor() as cur:
            # Use executemany with RETURNING for batch insert
            saved_results = []
            for result in results:
                sources = result.get("sources")
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
                        result.get("question"),
                        result.get("embedding"),
                        result.get("summary"),
                        result.get("confidence", "medium"),
                        Json(sources) if sources else None,
                        len(sources) if sources else 0,
                        result.get("category"),
                        result.get("industry"),
                        result.get("freshness_days", 90),
                        result.get("tokens_used"),
                        result.get("research_cost_usd"),
                    ),
                )
                row = cur.fetchone()
                if row:
                    saved_results.append(dict(row))

            return saved_results


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


# =============================================================================
# Session Persistence Functions (Events, Tasks, Synthesis)
# =============================================================================


def save_session_event(
    session_id: str,
    event_type: str,
    sequence: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Save a session event to PostgreSQL for long-term storage.

    Args:
        session_id: Session identifier
        event_type: Event type (e.g., 'contribution', 'synthesis_complete')
        sequence: Event sequence number within session
        data: Event payload (will be stored as JSONB)

    Returns:
        Saved event record with id and created_at

    Examples:
        >>> save_session_event(
        ...     session_id="bo1_abc123",
        ...     event_type="contribution",
        ...     sequence=1,
        ...     data={"persona_name": "CTO", "content": "..."}
        ... )
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO session_events (session_id, event_type, sequence, data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id, sequence, created_at) DO NOTHING
                RETURNING id, session_id, event_type, sequence, created_at
                """,
                (session_id, event_type, sequence, Json(data)),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


def get_session_events(session_id: str) -> list[dict[str, Any]]:
    """Get all events for a session from PostgreSQL.

    Args:
        session_id: Session identifier

    Returns:
        List of event records ordered by sequence

    Examples:
        >>> events = get_session_events("bo1_abc123")
        >>> print(f"Session has {len(events)} events")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, event_type, sequence, data, created_at
                FROM session_events
                WHERE session_id = %s
                ORDER BY sequence ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]


def save_session_tasks(
    session_id: str,
    tasks: list[dict[str, Any]],
    total_tasks: int,
    extraction_confidence: float,
    synthesis_sections_analyzed: list[str],
) -> dict[str, Any]:
    """Save extracted tasks to PostgreSQL.

    Args:
        session_id: Session identifier
        tasks: List of ExtractedTask dictionaries
        total_tasks: Total number of tasks
        extraction_confidence: Confidence score (0.0-1.0)
        synthesis_sections_analyzed: List of analyzed sections

    Returns:
        Saved task record

    Examples:
        >>> save_session_tasks(
        ...     session_id="bo1_abc123",
        ...     tasks=[{"id": "task_1", "description": "..."}],
        ...     total_tasks=5,
        ...     extraction_confidence=0.92,
        ...     synthesis_sections_analyzed=["implementation", "timeline"]
        ... )
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO session_tasks (
                    session_id, tasks, total_tasks, extraction_confidence,
                    synthesis_sections_analyzed
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE
                SET tasks = EXCLUDED.tasks,
                    total_tasks = EXCLUDED.total_tasks,
                    extraction_confidence = EXCLUDED.extraction_confidence,
                    synthesis_sections_analyzed = EXCLUDED.synthesis_sections_analyzed,
                    extracted_at = NOW()
                RETURNING id, session_id, total_tasks, extraction_confidence, extracted_at
                """,
                (
                    session_id,
                    Json(tasks),
                    total_tasks,
                    extraction_confidence,
                    synthesis_sections_analyzed,
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


def get_session_tasks(session_id: str) -> dict[str, Any] | None:
    """Get extracted tasks for a session from PostgreSQL.

    Args:
        session_id: Session identifier

    Returns:
        Task record with tasks array, or None if not found

    Examples:
        >>> tasks = get_session_tasks("bo1_abc123")
        >>> if tasks:
        ...     print(f"Found {tasks['total_tasks']} tasks")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, tasks, total_tasks, extraction_confidence,
                       synthesis_sections_analyzed, extracted_at
                FROM session_tasks
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def save_session_synthesis(session_id: str, synthesis_text: str) -> bool:
    """Save synthesis text to sessions table.

    Args:
        session_id: Session identifier
        synthesis_text: Final synthesis XML

    Returns:
        True if saved successfully

    Examples:
        >>> save_session_synthesis("bo1_abc123", "<synthesis>...</synthesis>")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sessions
                SET synthesis_text = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (synthesis_text, session_id),
            )
            return bool(cur.rowcount and cur.rowcount > 0)


def get_session_synthesis(session_id: str) -> str | None:
    """Get synthesis text from sessions table.

    Args:
        session_id: Session identifier

    Returns:
        Synthesis text, or None if not found

    Examples:
        >>> synthesis = get_session_synthesis("bo1_abc123")
        >>> if synthesis:
        ...     print("Found synthesis")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT synthesis_text
                FROM sessions
                WHERE id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return row["synthesis_text"] if row else None


# =============================================================================
# Session Management Functions
# =============================================================================


def save_session(
    session_id: str,
    user_id: str,
    problem_statement: str,
    problem_context: dict[str, Any] | None = None,
    status: str = "created",
) -> dict[str, Any]:
    """Save a new session to PostgreSQL.

    Args:
        session_id: Session identifier (e.g., bo1_uuid)
        user_id: User who created the session (from SuperTokens)
        problem_statement: Original problem statement
        problem_context: Additional context as dict (optional)
        status: Initial status (default: 'created')

    Returns:
        Saved session record with timestamps

    Examples:
        >>> save_session(
        ...     session_id="bo1_abc123",
        ...     user_id="user_456",
        ...     problem_statement="How do we scale to 10M users?",
        ...     problem_context={"industry": "saas", "stage": "series_a"}
        ... )
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (
                    id, user_id, problem_statement, problem_context, status
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET user_id = EXCLUDED.user_id,
                    problem_statement = EXCLUDED.problem_statement,
                    problem_context = EXCLUDED.problem_context,
                    status = EXCLUDED.status,
                    updated_at = NOW()
                RETURNING id, user_id, problem_statement, problem_context, status,
                          phase, total_cost, round_number, created_at, updated_at
                """,
                (
                    session_id,
                    user_id,
                    problem_statement,
                    Json(problem_context) if problem_context else None,
                    status,
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


def update_session_status(
    session_id: str,
    status: str,
    phase: str | None = None,
    total_cost: float | None = None,
    round_number: int | None = None,
    synthesis_text: str | None = None,
    final_recommendation: str | None = None,
) -> bool:
    """Update session status and optional fields.

    Args:
        session_id: Session identifier
        status: New status (e.g., 'running', 'completed', 'failed', 'killed')
        phase: Current deliberation phase (optional)
        total_cost: Total cost in USD (optional)
        round_number: Current round number (optional)
        synthesis_text: Final synthesis text (optional)
        final_recommendation: Final recommendation (optional)

    Returns:
        True if updated successfully, False otherwise

    Examples:
        >>> update_session_status(
        ...     session_id="bo1_abc123",
        ...     status="completed",
        ...     total_cost=0.42,
        ...     synthesis_text="<synthesis>...</synthesis>"
        ... )
        True
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Build dynamic UPDATE query based on provided fields
            update_fields = ["status = %s", "updated_at = NOW()"]
            params: list[Any] = [status]

            if phase is not None:
                update_fields.append("phase = %s")
                params.append(phase)

            if total_cost is not None:
                update_fields.append("total_cost = %s")
                params.append(total_cost)

            if round_number is not None:
                update_fields.append("round_number = %s")
                params.append(round_number)

            if synthesis_text is not None:
                update_fields.append("synthesis_text = %s")
                params.append(synthesis_text)

            if final_recommendation is not None:
                update_fields.append("final_recommendation = %s")
                params.append(final_recommendation)

            params.append(session_id)

            # Safe: update_fields contains only controlled column names, values are parameterized
            query = f"""
                UPDATE sessions
                SET {", ".join(update_fields)}
                WHERE id = %s
            """  # noqa: S608

            cur.execute(query, params)
            return bool(cur.rowcount and cur.rowcount > 0)


def get_session(session_id: str) -> dict[str, Any] | None:
    """Get a single session by ID.

    Args:
        session_id: Session identifier

    Returns:
        Session record with all fields, or None if not found

    Examples:
        >>> session = get_session("bo1_abc123")
        >>> if session:
        ...     print(f"Session status: {session['status']}")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, problem_statement, problem_context, status,
                       phase, total_cost, round_number, created_at, updated_at,
                       synthesis_text, final_recommendation
                FROM sessions
                WHERE id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def ensure_user_exists(
    user_id: str,
    email: str | None = None,
    auth_provider: str = "supertokens",
    subscription_tier: str = "free",
) -> bool:
    """Ensure a user exists in the PostgreSQL users table.

    Creates the user if they don't exist, or updates their info if they do.
    This is critical for FK constraints - sessions require a valid user_id.

    When updating existing users:
    - Real emails (not @placeholder.local) always replace placeholder emails
    - auth_provider is updated when a real email is provided (OAuth sync)
    - Placeholder emails never overwrite real emails
    - Admin status is auto-set if email is in ADMIN_EMAILS config

    Args:
        user_id: User identifier (from SuperTokens or auth provider)
        email: User email (optional, may not be available from all providers)
        auth_provider: Authentication provider (default: supertokens)
        subscription_tier: Subscription tier (default: free)

    Returns:
        True if user exists or was created successfully

    Examples:
        >>> ensure_user_exists("user_123", "user@example.com", "google")
        True
    """
    from bo1.config import get_settings

    settings = get_settings()

    # Determine if this is a real email or placeholder
    is_real_email = email is not None and not email.endswith("@placeholder.local")
    final_email = email or f"{user_id}@placeholder.local"

    # Check if email should be auto-admin
    is_admin = is_real_email and final_email.lower() in settings.admin_email_set

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                if is_real_email:
                    # Real email from OAuth - always update email and auth_provider
                    # Also set is_admin if email is in admin list
                    cur.execute(
                        """
                        INSERT INTO users (id, email, auth_provider, subscription_tier, is_admin)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET email = EXCLUDED.email,
                            auth_provider = EXCLUDED.auth_provider,
                            is_admin = CASE
                                WHEN EXCLUDED.is_admin = true THEN true
                                ELSE users.is_admin
                            END,
                            updated_at = NOW()
                        """,
                        (user_id, final_email, auth_provider, subscription_tier, is_admin),
                    )
                    if is_admin:
                        logger.info(f"User {user_id} ({final_email}) auto-set as admin")
                    else:
                        logger.info(f"User {user_id} synced with real email ({auth_provider})")
                else:
                    # Placeholder email - only insert, don't overwrite real data
                    cur.execute(
                        """
                        INSERT INTO users (id, email, auth_provider, subscription_tier)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (user_id, final_email, auth_provider, subscription_tier),
                    )
                return True
    except Exception as e:
        logger.error(f"Failed to ensure user exists: {e}")
        return False


def get_user(user_id: str) -> dict[str, Any] | None:
    """Get user data from PostgreSQL.

    Args:
        user_id: User identifier (from SuperTokens)

    Returns:
        User data dict or None if not found

    Examples:
        >>> user = get_user("user_123")
        >>> if user:
        ...     print(f"Email: {user['email']}")
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, auth_provider, subscription_tier,
                           is_admin, gdpr_consent_at, created_at, updated_at
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {e}")
        return None


def get_user_sessions(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    """Get all sessions for a user, ordered by created_at DESC.

    Args:
        user_id: User identifier (from SuperTokens)
        limit: Maximum number of sessions to return (default: 50)
        offset: Number of sessions to skip for pagination (default: 0)
        status_filter: Optional status filter (e.g., 'completed', 'running')
        include_deleted: If False (default), excludes deleted sessions

    Returns:
        List of session records, ordered by created_at DESC (most recent first)

    Examples:
        >>> sessions = get_user_sessions("user_456", limit=10)
        >>> print(f"Found {len(sessions)} sessions")

        >>> completed = get_user_sessions("user_456", status_filter="completed")
        >>> print(f"User has {len(completed)} completed sessions")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Build query with optional status filter
            query = """
                SELECT id, user_id, problem_statement, problem_context, status,
                       phase, total_cost, round_number, created_at, updated_at,
                       synthesis_text, final_recommendation
                FROM sessions
                WHERE user_id = %s
            """
            params: list[Any] = [user_id]

            # Exclude deleted sessions by default
            if not include_deleted:
                query += " AND status != 'deleted'"

            if status_filter:
                query += " AND status = %s"
                params.append(status_filter)

            query += """
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])

            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]


def get_session_metadata(session_id: str) -> dict[str, Any] | None:
    """Get session metadata from PostgreSQL in Redis-compatible format.

    This function provides a fallback when Redis doesn't have the session metadata
    (e.g., after Redis restart). Returns metadata in the same format as Redis
    for compatibility with existing code.

    Args:
        session_id: Session identifier (e.g., "bo1_abc123")

    Returns:
        Metadata dict compatible with Redis format, or None if session not found.
        Format: {
            "status": "completed",
            "phase": "synthesis",
            "user_id": "user_123",
            "created_at": "2025-01-01T10:00:00+00:00",
            "updated_at": "2025-01-01T11:00:00+00:00",
            "problem_statement": "Should we...",
            "problem_context": {...}
        }

    Examples:
        >>> metadata = get_session_metadata("bo1_abc123")
        >>> if metadata:
        ...     print(f"Session owned by: {metadata['user_id']}")
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, problem_statement, problem_context,
                           status, phase, created_at, updated_at
                    FROM sessions
                    WHERE id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                row_dict = dict(row)
                # Convert to Redis-compatible metadata format
                return {
                    "status": row_dict["status"],
                    "phase": row_dict["phase"],
                    "user_id": row_dict["user_id"],
                    "created_at": row_dict["created_at"].isoformat(),
                    "updated_at": row_dict["updated_at"].isoformat(),
                    "problem_statement": row_dict["problem_statement"],
                    "problem_context": row_dict["problem_context"] or {},
                }
    except Exception as e:
        logger.error(f"Failed to get session metadata for {session_id}: {e}")
        return None


# =============================================================================
# Contribution Persistence Functions
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
    """Save a persona contribution to PostgreSQL.

    Args:
        session_id: Session identifier
        persona_code: Persona code (e.g., 'growth_hacker')
        content: Contribution text content
        round_number: Round number when contribution was made
        phase: Phase (initial_round, deliberation, moderator_intervention)
        cost: Cost in USD
        tokens: Token count
        model: Model used
        embedding: Optional embedding vector (1024 dimensions for Voyage AI)
        user_id: User ID (optional - will be fetched from session if not provided)

    Returns:
        Saved contribution record with id and created_at
    """
    # Fetch user_id from session if not provided
    if user_id is None:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
                result = cur.fetchone()
                if result:
                    user_id = result[0]
                else:
                    logger.warning(
                        f"Session {session_id} not found, cannot fetch user_id for contribution"
                    )
                    user_id = "unknown"

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO contributions (
                    session_id, persona_code, content, round_number, phase,
                    cost, tokens, model, embedding, user_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, persona_code, round_number, phase, created_at
                """,
                (
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
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


def save_contribution_embedding(contribution_id: str, embedding: list[float]) -> bool:
    """Update a contribution's embedding vector.

    This function is called after generating an embedding for semantic deduplication.
    Saves ~$0.0001 per contribution on repeat analysis.

    Args:
        contribution_id: Contribution record ID (UUID as string)
        embedding: Embedding vector (1024 dimensions for Voyage AI voyage-3)

    Returns:
        True if updated successfully, False otherwise

    Examples:
        >>> from bo1.llm.embeddings import generate_embedding
        >>> embedding = generate_embedding("We should focus on user experience", input_type="document")
        >>> save_contribution_embedding("contrib_uuid", embedding)
        True
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE contributions
                SET embedding = %s
                WHERE id = %s
                """,
                (embedding, contribution_id),
            )
            return bool(cur.rowcount and cur.rowcount > 0)


def get_contribution_embedding(contribution_id: str) -> list[float] | None:
    """Get a contribution's embedding vector if it exists.

    Used by semantic deduplication to avoid regenerating embeddings.

    Args:
        contribution_id: Contribution record ID (UUID as string)

    Returns:
        Embedding vector if exists, None otherwise

    Examples:
        >>> embedding = get_contribution_embedding("contrib_uuid")
        >>> if embedding:
        ...     print(f"Found cached embedding ({len(embedding)} dimensions)")
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT embedding
                FROM contributions
                WHERE id = %s AND embedding IS NOT NULL
                """,
                (contribution_id,),
            )
            row = cur.fetchone()
            return row["embedding"] if row and row.get("embedding") else None


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
    """Save an expert recommendation to PostgreSQL.

    Args:
        session_id: Session identifier
        persona_code: Persona code
        recommendation: Free-form recommendation text
        reasoning: Reasoning behind recommendation
        confidence: Confidence score (0.0-1.0)
        conditions: List of conditions for the recommendation
        weight: Weight/importance of recommendation
        sub_problem_index: Sub-problem index (optional)
        persona_name: Display name of persona

    Returns:
        Saved recommendation record
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recommendations (
                    session_id, sub_problem_index, persona_code, persona_name,
                    recommendation, reasoning, confidence, conditions, weight
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, persona_code, created_at
                """,
                (
                    session_id,
                    sub_problem_index,
                    persona_code,
                    persona_name,
                    recommendation,
                    reasoning,
                    confidence,
                    Json(conditions) if conditions else None,
                    weight,
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


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
    """Save sub-problem result to PostgreSQL.

    Args:
        session_id: Session identifier
        sub_problem_index: Index of sub-problem
        goal: Sub-problem goal text
        synthesis: Synthesis text for this sub-problem
        expert_summaries: Dict of persona_code -> summary
        cost: Total cost for this sub-problem
        duration_seconds: Time taken
        contribution_count: Number of contributions

    Returns:
        Saved result record
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sub_problem_results (
                    session_id, sub_problem_index, goal, synthesis,
                    expert_summaries, cost, duration_seconds, contribution_count
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, sub_problem_index) DO UPDATE
                SET goal = EXCLUDED.goal,
                    synthesis = EXCLUDED.synthesis,
                    expert_summaries = EXCLUDED.expert_summaries,
                    cost = EXCLUDED.cost,
                    duration_seconds = EXCLUDED.duration_seconds,
                    contribution_count = EXCLUDED.contribution_count
                RETURNING id, session_id, sub_problem_index, created_at
                """,
                (
                    session_id,
                    sub_problem_index,
                    goal,
                    synthesis,
                    Json(expert_summaries) if expert_summaries else None,
                    cost,
                    duration_seconds,
                    contribution_count,
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}


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
    """Save facilitator decision to PostgreSQL.

    Args:
        session_id: Session identifier
        round_number: Round when decision was made
        action: Decision action (continue, vote, moderator, research, clarify)
        reasoning: Reasoning behind decision
        next_speaker: Next persona to speak (if action=continue)
        moderator_type: Type of moderator intervention (if action=moderator)
        research_query: Research query (if action=research)
        sub_problem_index: Current sub-problem index

    Returns:
        Saved decision record
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO facilitator_decisions (
                    session_id, round_number, sub_problem_index, action,
                    reasoning, next_speaker, moderator_type, research_query
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, session_id, round_number, action, created_at
                """,
                (
                    session_id,
                    round_number,
                    sub_problem_index,
                    action,
                    reasoning,
                    next_speaker,
                    moderator_type,
                    research_query,
                ),
            )
            result = cur.fetchone()
            return dict(result) if result else {}
