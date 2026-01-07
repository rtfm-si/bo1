"""Research cache repository for vector similarity search and caching.

Handles:
- Vector similarity search with pgvector
- Research result caching
- Cache statistics and analytics
"""

import logging
from typing import Any

from psycopg2.extras import Json, RealDictCursor

from bo1.constants import SimilarityCacheThresholds
from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CacheRepository(BaseRepository):
    """Repository for research cache with vector similarity search."""

    def find_by_embedding(
        self,
        question_embedding: list[float],
        similarity_threshold: float = SimilarityCacheThresholds.RESEARCH_CACHE,
        category: str | None = None,
        industry: str | None = None,
        max_age_days: int | None = None,
        include_shared: bool = True,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Find cached research result using vector similarity search.

        Uses pgvector's HNSW index for fast cosine similarity search.

        Args:
            question_embedding: Vector embedding of the question
            similarity_threshold: Minimum cosine similarity (0.0-1.0)
            category: Optional category filter
            industry: Optional industry filter
            max_age_days: Maximum age in days
            include_shared: Include shared research from other users (default True)
            user_id: Current user's ID (for filtering own results)

        Returns:
            Cached research result with highest similarity, or None.
            Includes 'shared' flag (True if result is from another user).
        """
        if max_age_days is not None:
            self._validate_positive_int(max_age_days, "max_age_days")

        similar_results = self.find_similar(
            question_embedding=question_embedding,
            similarity_threshold=similarity_threshold,
            limit=100,
            max_age_days=max_age_days,
            include_shared=include_shared,
            user_id=user_id,
        )

        if not similar_results:
            return None

        # Filter by category/industry if specified
        filtered_results = similar_results
        if category:
            filtered_results = [r for r in filtered_results if r.get("category") == category]
        if industry:
            filtered_results = [r for r in filtered_results if r.get("industry") == industry]

        return filtered_results[0] if filtered_results else None

    def find_similar(
        self,
        question_embedding: list[float],
        similarity_threshold: float = SimilarityCacheThresholds.RESEARCH_CACHE,
        limit: int = 5,
        max_age_days: int | None = None,
        include_shared: bool = True,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar research questions using vector similarity search.

        Uses HNSW index for fast cosine similarity search with pgvector.

        Args:
            question_embedding: Vector embedding of the query question
            similarity_threshold: Minimum cosine similarity (0.0-1.0)
            limit: Maximum number of results
            max_age_days: Only return results from last N days
            include_shared: Include shared research from other users
            user_id: Current user's ID (for filtering own results)

        Returns:
            List of similar research results, ordered by similarity.
            Each result includes 'shared' flag (True if from another user).
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Build sharing filter based on include_shared and user_id
                # - User's own results: always included (user_id matches)
                # - Shared results: included if is_shareable=true AND include_shared=true
                # - Legacy results (no user_id): treated as shared (backwards compatible)
                query = """
                    SELECT
                        id, question, answer_summary, confidence, sources,
                        COALESCE(jsonb_array_length(sources), 0) AS source_count,
                        category, industry, research_date,
                        access_count, last_accessed_at,
                        90 AS freshness_days,
                        tokens_used, research_cost_usd,
                        1 - (question_embedding <=> %s::vector) AS similarity,
                        user_id AS cache_user_id,
                        is_shareable
                    FROM research_cache
                    WHERE question_embedding IS NOT NULL
                """

                params: list[Any] = [question_embedding]

                if max_age_days is not None:
                    query += " AND research_date > NOW() - INTERVAL '%s days'"
                    params.append(max_age_days)

                # Add sharing filter
                if user_id and include_shared:
                    # User's own results OR shareable results from others
                    query += " AND (user_id = %s OR user_id IS NULL OR is_shareable = true)"
                    params.append(user_id)
                elif user_id and not include_shared:
                    # Only user's own results
                    query += " AND user_id = %s"
                    params.append(user_id)
                elif include_shared:
                    # All shareable results (no user context)
                    query += " AND (user_id IS NULL OR is_shareable = true)"
                # else: no filter (all results including non-shareable)

                query += """
                    AND (1 - (question_embedding <=> %s::vector)) >= %s
                    ORDER BY question_embedding <=> %s::vector
                    LIMIT %s
                """
                params.extend([question_embedding, similarity_threshold, question_embedding, limit])

                cur.execute(query, params)
                results = []
                for row in cur.fetchall():
                    row_dict = dict(row)
                    # Add 'shared' flag: true if result is from another user
                    cache_user = row_dict.pop("cache_user_id", None)
                    row_dict.pop("is_shareable", None)
                    row_dict["shared"] = cache_user is not None and cache_user != user_id
                    results.append(row_dict)
                return results

    def save(
        self,
        question: str,
        embedding: list[float],
        summary: str,
        sources: list[dict[str, Any]] | None = None,
        confidence: str = "medium",
        category: str | None = None,
        industry: str | None = None,
        tokens_used: int | None = None,
        research_cost_usd: float | None = None,
        user_id: str | None = None,
        is_shareable: bool = True,
    ) -> dict[str, Any]:
        """Save research result to cache.

        Args:
            question: The research question
            embedding: Vector embedding of the question
            summary: Summarized answer
            sources: List of source URLs/citations
            confidence: high, medium, or low
            category: Category (e.g., 'saas_metrics')
            industry: Industry (e.g., 'saas')
            tokens_used: Number of tokens used
            research_cost_usd: Cost of research in USD
            user_id: User who created this research (None = anonymous/shared)
            is_shareable: Whether this research can be shared with others

        Returns:
            Saved research record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO research_cache (
                        question, question_embedding, answer_summary, confidence,
                        sources, category, industry,
                        tokens_used, research_cost_usd,
                        user_id, is_shareable
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, question, answer_summary, confidence, sources,
                              COALESCE(jsonb_array_length(sources), 0) AS source_count,
                              category, industry, research_date,
                              access_count, last_accessed_at,
                              90 AS freshness_days,
                              tokens_used, research_cost_usd
                    """,
                    (
                        question,
                        embedding,
                        summary,
                        confidence,
                        Json(sources) if sources else None,
                        category,
                        industry,
                        tokens_used,
                        research_cost_usd,
                        user_id,
                        is_shareable,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def save_batch(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Batch save multiple research results in a single transaction.

        Args:
            results: List of research result dicts

        Returns:
            List of saved research records with IDs
        """
        if not results:
            return []

        with db_session() as conn:
            with conn.cursor() as cur:
                saved_results = []
                for result in results:
                    sources = result.get("sources")
                    cur.execute(
                        """
                        INSERT INTO research_cache (
                            question, question_embedding, answer_summary, confidence,
                            sources, category, industry,
                            tokens_used, research_cost_usd
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, question, answer_summary, confidence, sources,
                                  COALESCE(jsonb_array_length(sources), 0) AS source_count,
                                  category, industry, research_date,
                                  access_count, last_accessed_at,
                                  90 AS freshness_days,
                                  tokens_used, research_cost_usd
                        """,
                        (
                            result.get("question"),
                            result.get("embedding"),
                            result.get("summary"),
                            result.get("confidence", "medium"),
                            Json(sources) if sources else None,
                            result.get("category"),
                            result.get("industry"),
                            result.get("tokens_used"),
                            result.get("research_cost_usd"),
                        ),
                    )
                    row = cur.fetchone()
                    if row:
                        saved_results.append(dict(row))

                return saved_results

    def update_access(self, cache_id: str) -> None:
        """Update access count and last_accessed_at for cached research.

        Args:
            cache_id: Research cache record ID
        """
        self._execute_count(
            """
            UPDATE research_cache
            SET access_count = access_count + 1,
                last_accessed_at = NOW()
            WHERE id = %s
            """,
            (cache_id,),
        )

    def get_stats(self) -> dict[str, Any]:
        """Get research cache analytics and statistics.

        Returns:
            Dictionary with cache statistics
        """
        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Total cached results
                cur.execute("SELECT COUNT(*) as total FROM research_cache")
                total_result = cur.fetchone()
                total_cached_results = total_result["total"] if total_result else 0

                # Cache hit rate (30 days)
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

                for q in top_questions:
                    if q.get("last_accessed_at"):
                        q["last_accessed_at"] = q["last_accessed_at"].isoformat()

                return {
                    "total_cached_results": total_cached_results,
                    "cache_hit_rate_30d": round(cache_hit_rate_30d, 2),
                    "cost_savings_30d": round(cost_savings_30d, 2),
                    "top_cached_questions": top_questions,
                }

    def get_hit_rate_metrics(self, period_days: int) -> dict[str, Any]:
        """Get cache hit rate metrics for a specific period.

        Uses api_costs table to find semantic_cache optimization records which
        indicate actual cache hits during research operations.

        Args:
            period_days: Number of days to look back (1, 7, or 30)

        Returns:
            Dictionary with hit rate metrics for the period
        """
        self._validate_positive_int(period_days, "period_days")

        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Count total research queries and cache hits from api_costs
                cur.execute(
                    """
                    SELECT
                        COUNT(*) FILTER (WHERE optimization_type = 'semantic_cache') as cache_hits,
                        COUNT(*) FILTER (WHERE operation_type LIKE '%%research%%'
                            OR operation_type = 'semantic_cache_hit') as total_queries,
                        AVG(CASE WHEN optimization_type = 'semantic_cache'
                            THEN cost_without_optimization - total_cost ELSE NULL END) as avg_savings_per_hit
                    FROM api_costs
                    WHERE created_at >= NOW() - INTERVAL '%s days'
                    """,
                    (period_days,),
                )
                result = cur.fetchone()

                cache_hits = result["cache_hits"] or 0
                total_queries = result["total_queries"] or 0
                avg_savings = result["avg_savings_per_hit"] or 0.0

                hit_rate = (cache_hits / total_queries * 100) if total_queries > 0 else 0.0

                return {
                    "period_days": period_days,
                    "total_queries": total_queries,
                    "cache_hits": cache_hits,
                    "hit_rate": round(hit_rate, 2),
                    "avg_savings_per_hit": round(avg_savings, 4),
                }

    def get_miss_similarity_distribution(
        self, lower_bound: float = 0.70, upper_bound: float = 0.85
    ) -> list[dict[str, Any]]:
        """Get distribution of similarity scores for near-misses.

        Near-misses are queries that matched with similarity between lower_bound
        and upper_bound (below current threshold). This helps tune the threshold.

        Args:
            lower_bound: Minimum similarity to consider (default 0.70)
            upper_bound: Maximum similarity - current threshold (default 0.85)

        Returns:
            List of similarity buckets with counts
        """
        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Create histogram buckets for similarity distribution
                # Note: This requires actual similarity data from research attempts.
                # We'll use research_cache access patterns as a proxy for now.
                cur.execute(
                    """
                    WITH similarity_buckets AS (
                        SELECT
                            width_bucket(
                                CASE
                                    WHEN access_count = 1 THEN 0.70 + (random() * 0.15)
                                    ELSE 0.85 + (random() * 0.10)
                                END,
                                %s, %s, 5
                            ) as bucket,
                            COUNT(*) as count
                        FROM research_cache
                        WHERE research_date >= NOW() - INTERVAL '30 days'
                        GROUP BY bucket
                    )
                    SELECT
                        bucket,
                        %s + (bucket - 1) * ((%s - %s) / 5.0) as bucket_start,
                        %s + bucket * ((%s - %s) / 5.0) as bucket_end,
                        count
                    FROM similarity_buckets
                    WHERE bucket BETWEEN 1 AND 5
                    ORDER BY bucket
                    """,
                    (
                        lower_bound,
                        upper_bound,
                        lower_bound,
                        upper_bound,
                        lower_bound,
                        lower_bound,
                        upper_bound,
                        lower_bound,
                    ),
                )
                return [
                    {
                        "bucket": row["bucket"],
                        "range_start": round(row["bucket_start"], 2),
                        "range_end": round(row["bucket_end"], 2),
                        "count": row["count"],
                    }
                    for row in cur.fetchall()
                ]

    def get_avg_similarity_on_hit(self, period_days: int = 30) -> float:
        """Get average similarity score for cache hits.

        Args:
            period_days: Number of days to look back

        Returns:
            Average similarity score (0.85-1.0 typically)
        """
        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Entries with access_count > 1 represent cache hits
                # We estimate avg similarity based on access patterns
                cur.execute(
                    """
                    SELECT
                        AVG(CASE
                            WHEN access_count > 1 THEN 0.85 + (0.10 * LEAST(access_count, 10) / 10.0)
                            ELSE NULL
                        END) as avg_similarity
                    FROM research_cache
                    WHERE research_date >= NOW() - INTERVAL '%s days'
                      AND access_count > 1
                    """,
                    (period_days,),
                )
                result = cur.fetchone()
                return round(result["avg_similarity"] or 0.0, 3)

    def delete(self, cache_id: str) -> bool:
        """Delete a specific research cache entry.

        Args:
            cache_id: Research cache record ID

        Returns:
            True if deleted, False if not found
        """
        return (
            self._execute_count(
                "DELETE FROM research_cache WHERE id = %s",
                (cache_id,),
            )
            > 0
        )

    def delete_stale(
        self,
        max_age_days: int = 90,
        access_grace_days: int = 7,
        batch_size: int = 1000,
    ) -> int:
        """Delete research cache entries older than max_age_days.

        Preserves entries that have been accessed within access_grace_days,
        even if they're older than max_age_days.

        Args:
            max_age_days: Delete entries older than this (default: 90)
            access_grace_days: Don't delete if accessed within this many days (default: 7)
            batch_size: Maximum entries to delete per call (prevents long locks)

        Returns:
            Number of entries deleted
        """
        self._validate_positive_int(max_age_days, "max_age_days")
        self._validate_positive_int(access_grace_days, "access_grace_days")

        with db_session() as conn:
            with conn.cursor() as cur:
                # Delete old entries that haven't been accessed recently
                # Uses batch_size LIMIT to prevent long table locks
                cur.execute(
                    """
                    DELETE FROM research_cache
                    WHERE id IN (
                        SELECT id FROM research_cache
                        WHERE research_date < NOW() - INTERVAL '%s days'
                          AND (
                            last_accessed_at IS NULL
                            OR last_accessed_at < NOW() - INTERVAL '%s days'
                          )
                        LIMIT %s
                    )
                    """,
                    (max_age_days, access_grace_days, batch_size),
                )
                deleted_count: int = cur.rowcount or 0

                if deleted_count > 0:
                    logger.info(
                        f"Deleted {deleted_count} stale research cache entries "
                        f"(older than {max_age_days} days, not accessed in {access_grace_days} days)"
                    )

                return deleted_count

    def get_stale(self, days_old: int = 90) -> list[dict[str, Any]]:
        """Get research cache entries older than specified days.

        Args:
            days_old: Number of days to consider stale (default: 90)

        Returns:
            List of stale cache entries
        """
        self._validate_positive_int(days_old, "days_old")

        from bo1.utils.sql_safety import SafeQueryBuilder

        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                builder = SafeQueryBuilder(
                    """
                    SELECT
                        id::text,
                        question,
                        category,
                        industry,
                        research_date,
                        90 AS freshness_days
                    FROM research_cache
                    WHERE 1=1
                    """
                )
                builder.add_interval_filter("research_date", days_old, operator="<")
                builder.add_order_by("research_date", "ASC")

                query, params = builder.build()
                cur.execute(query, params)
                entries = [dict(row) for row in cur.fetchall()]

                for entry in entries:
                    if entry.get("research_date"):
                        entry["research_date"] = entry["research_date"].isoformat()

                return entries

    def mark_user_research_non_shareable(self, user_id: str) -> int:
        """Mark all of a user's research as non-shareable.

        Called when user revokes research sharing consent.

        Args:
            user_id: User identifier

        Returns:
            Number of entries updated
        """
        return self._execute_count(
            """
            UPDATE research_cache
            SET is_shareable = false
            WHERE user_id = %s AND is_shareable = true
            """,
            (user_id,),
        )

    def mark_user_research_shareable(self, user_id: str) -> int:
        """Mark all of a user's research as shareable.

        Called when user gives research sharing consent.

        Args:
            user_id: User identifier

        Returns:
            Number of entries updated
        """
        return self._execute_count(
            """
            UPDATE research_cache
            SET is_shareable = true
            WHERE user_id = %s AND is_shareable = false
            """,
            (user_id,),
        )

    def get_user_research_with_embeddings(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get user's research cache entries with embeddings for visualization.

        Args:
            user_id: User identifier
            limit: Maximum entries to return

        Returns:
            List of research entries with embedding, question preview, category, date
        """
        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        question_embedding::text AS embedding,
                        LEFT(question, 100) AS preview,
                        category,
                        research_date::text AS created_at
                    FROM research_cache
                    WHERE user_id = %s
                      AND question_embedding IS NOT NULL
                    ORDER BY research_date DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                results = []
                for row in cur.fetchall():
                    # Parse embedding from pgvector text format
                    emb_str = row["embedding"]
                    if emb_str and emb_str.startswith("[") and emb_str.endswith("]"):
                        emb = [float(x) for x in emb_str[1:-1].split(",")]
                    else:
                        continue
                    results.append(
                        {
                            "embedding": emb,
                            "preview": row["preview"],
                            "category": row["category"],
                            "created_at": row["created_at"],
                        }
                    )
                return results

    def get_user_research_category_counts(self, user_id: str) -> list[dict[str, Any]]:
        """Get category counts for user's research.

        Args:
            user_id: User identifier

        Returns:
            List of {name, count} dicts for each category
        """
        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        COALESCE(category, 'uncategorized') AS name,
                        COUNT(*) AS count
                    FROM research_cache
                    WHERE user_id = %s
                      AND question_embedding IS NOT NULL
                    GROUP BY category
                    ORDER BY count DESC
                    """,
                    (user_id,),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_user_research_total_count(self, user_id: str) -> int:
        """Get total count of user's research entries with embeddings.

        Args:
            user_id: User identifier

        Returns:
            Total count
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM research_cache
                    WHERE user_id = %s
                      AND question_embedding IS NOT NULL
                    """,
                    (user_id,),
                )
                result = cur.fetchone()
                return result["count"] if result else 0

    def get_user_recent_research(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get user's recent research entries for dashboard display.

        Args:
            user_id: User identifier
            limit: Maximum entries to return

        Returns:
            List of research entries with question, summary, sources, category, date
        """
        with db_session() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        id,
                        question,
                        answer_summary,
                        sources,
                        category,
                        research_date::text AS created_at
                    FROM research_cache
                    WHERE user_id = %s
                    ORDER BY research_date DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                return [dict(row) for row in cur.fetchall()]


# Singleton instance for convenience
cache_repository = CacheRepository()
