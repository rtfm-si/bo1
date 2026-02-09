"""Topic bank repository for decision topic research CRUD.

Handles:
- Bulk creation of researched topics
- Listing/filtering banked topics
- Status management (banked/used/dismissed)
- Deduplication via existing titles
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TopicBankRepository(BaseRepository):
    """Repository for decision topic bank operations."""

    def bulk_create(self, topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Insert multiple topics in a single transaction.

        Args:
            topics: List of topic dicts with title, description, category,
                    keywords, seo_score, reasoning, bo1_alignment, source

        Returns:
            List of created topic records
        """
        if not topics:
            return []

        created = []
        with db_session() as conn:
            with conn.cursor() as cur:
                for topic in topics:
                    topic_id = str(uuid4())
                    cur.execute(
                        """
                        INSERT INTO decision_topic_bank
                            (id, title, description, category, keywords,
                             seo_score, reasoning, bo1_alignment, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                        """,
                        (
                            topic_id,
                            topic["title"],
                            topic["description"],
                            topic["category"],
                            topic.get("keywords", []),
                            topic.get("seo_score", 0.0),
                            topic["reasoning"],
                            topic["bo1_alignment"],
                            topic.get("source", "llm-generated"),
                        ),
                    )
                    row = cur.fetchone()
                    if row:
                        created.append(dict(row))

        logger.info(f"Bulk created {len(created)} topic bank entries")
        return created

    def list_banked(
        self,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List banked topics ordered by SEO score descending.

        Args:
            category: Optional category filter
            limit: Max results
            offset: Pagination offset

        Returns:
            List of banked topic records
        """
        query = "SELECT * FROM decision_topic_bank WHERE status = 'banked'"
        params: list[Any] = []

        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY seo_score DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return self._execute_query(query, tuple(params))

    def count_banked(self, category: str | None = None) -> int:
        """Count banked topics.

        Args:
            category: Optional category filter

        Returns:
            Count of banked topics
        """
        query = "SELECT COUNT(*) as count FROM decision_topic_bank WHERE status = 'banked'"
        params: list[Any] = []

        if category:
            query += " AND category = %s"
            params.append(category)

        result = self._execute_one(query, tuple(params) if params else None)
        return result["count"] if result else 0

    def get_by_id(self, topic_id: str) -> dict[str, Any] | None:
        """Get topic by ID.

        Args:
            topic_id: Topic UUID

        Returns:
            Topic record or None
        """
        return self._execute_one(
            "SELECT * FROM decision_topic_bank WHERE id = %s",
            (topic_id,),
        )

    def dismiss(self, topic_id: str) -> bool:
        """Dismiss a topic (set status to 'dismissed').

        Args:
            topic_id: Topic UUID

        Returns:
            True if topic was dismissed
        """
        count = self._execute_count(
            """
            UPDATE decision_topic_bank
            SET status = 'dismissed', updated_at = NOW()
            WHERE id = %s AND status = 'banked'
            """,
            (topic_id,),
        )
        return count > 0

    def mark_used(self, topic_id: str) -> dict[str, Any] | None:
        """Mark topic as used and record timestamp.

        Args:
            topic_id: Topic UUID

        Returns:
            Updated topic record or None
        """
        return self._execute_one(
            """
            UPDATE decision_topic_bank
            SET status = 'used', used_at = NOW(), updated_at = NOW()
            WHERE id = %s AND status = 'banked'
            RETURNING *
            """,
            (topic_id,),
        )

    def get_existing_titles(self) -> list[str]:
        """Get titles of banked and used topics for deduplication.

        Returns:
            List of existing topic titles
        """
        rows = self._execute_query(
            "SELECT title FROM decision_topic_bank WHERE status IN ('banked', 'used')"
        )
        return [row["title"] for row in rows]

    def delete(self, topic_id: str) -> bool:
        """Hard delete a topic.

        Args:
            topic_id: Topic UUID

        Returns:
            True if topic was deleted
        """
        count = self._execute_count(
            "DELETE FROM decision_topic_bank WHERE id = %s",
            (topic_id,),
        )
        return count > 0


topic_bank_repository = TopicBankRepository()
