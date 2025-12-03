"""Research cache repository for vector similarity search and caching.

Handles:
- Vector similarity search with pgvector
- Research result caching
- Cache statistics and analytics
"""

import logging
from typing import Any

from psycopg2.extras import Json, RealDictCursor

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class CacheRepository(BaseRepository):
    """Repository for research cache with vector similarity search."""

    def find_by_embedding(
        self,
        question_embedding: list[float],
        similarity_threshold: float = 0.85,
        category: str | None = None,
        industry: str | None = None,
        max_age_days: int | None = None,
    ) -> dict[str, Any] | None:
        """Find cached research result using vector similarity search.

        Uses pgvector's HNSW index for fast cosine similarity search.

        Args:
            question_embedding: Vector embedding of the question
            similarity_threshold: Minimum cosine similarity (0.0-1.0)
            category: Optional category filter
            industry: Optional industry filter
            max_age_days: Maximum age in days

        Returns:
            Cached research result with highest similarity, or None
        """
        if max_age_days is not None:
            self._validate_positive_int(max_age_days, "max_age_days")

        similar_results = self.find_similar(
            question_embedding=question_embedding,
            similarity_threshold=similarity_threshold,
            limit=100,
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

        return filtered_results[0] if filtered_results else None

    def find_similar(
        self,
        question_embedding: list[float],
        similarity_threshold: float = 0.85,
        limit: int = 5,
        max_age_days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar research questions using vector similarity search.

        Uses HNSW index for fast cosine similarity search with pgvector.

        Args:
            question_embedding: Vector embedding of the query question
            similarity_threshold: Minimum cosine similarity (0.0-1.0)
            limit: Maximum number of results
            max_age_days: Only return results from last N days

        Returns:
            List of similar research results, ordered by similarity
        """
        with db_session() as conn:
            with conn.cursor() as cur:
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

                if max_age_days is not None:
                    query += " AND research_date > NOW() - INTERVAL '%s days'"
                    params.append(max_age_days)

                query += """
                    AND (1 - (question_embedding <=> %s::vector)) >= %s
                    ORDER BY question_embedding <=> %s::vector
                    LIMIT %s
                """
                params.extend([question_embedding, similarity_threshold, question_embedding, limit])

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def save(
        self,
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
            embedding: Vector embedding of the question
            summary: Summarized answer
            sources: List of source URLs/citations
            confidence: high, medium, or low
            category: Category (e.g., 'saas_metrics')
            industry: Industry (e.g., 'saas')
            freshness_days: How long result stays fresh
            tokens_used: Number of tokens used
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
                        Json(sources) if sources else None,
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
                        freshness_days
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


# Singleton instance for convenience
cache_repository = CacheRepository()
