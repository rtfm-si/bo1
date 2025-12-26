"""Ratings repository for thumbs up/down feedback on meetings and actions.

Provides:
- Create/update user ratings for entities
- Get user's rating for an entity
- Aggregate metrics (up/down counts, trends)
- Get recent negative feedback for admin triage
"""

import logging
from datetime import datetime
from typing import Any

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class RatingsRepository(BaseRepository):
    """Repository for the user_ratings table."""

    def upsert_rating(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        rating: int,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Create or update a rating for an entity.

        Args:
            user_id: User's ID
            entity_type: 'meeting' or 'action'
            entity_id: UUID of the entity
            rating: -1 (thumbs down) or +1 (thumbs up)
            comment: Optional text comment

        Returns:
            Created/updated rating dict
        """
        self._validate_id(user_id, "user_id")
        self._validate_id(entity_id, "entity_id")

        if entity_type not in ("meeting", "action"):
            raise ValueError(f"entity_type must be 'meeting' or 'action', got '{entity_type}'")
        if rating not in (-1, 1):
            raise ValueError(f"rating must be -1 or 1, got {rating}")

        query = """
            INSERT INTO user_ratings (user_id, entity_type, entity_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, entity_type, entity_id)
            DO UPDATE SET rating = EXCLUDED.rating,
                         comment = EXCLUDED.comment,
                         created_at = NOW()
            RETURNING id, user_id, entity_type, entity_id, rating, comment, created_at
        """
        return self._execute_returning(
            query,
            (user_id, entity_type, entity_id, rating, comment),
            user_id=user_id,
        )

    def get_user_rating(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Get user's rating for a specific entity.

        Args:
            user_id: User's ID
            entity_type: 'meeting' or 'action'
            entity_id: UUID of the entity

        Returns:
            Rating dict or None if not rated
        """
        self._validate_id(user_id, "user_id")
        self._validate_id(entity_id, "entity_id")

        query = """
            SELECT id, user_id, entity_type, entity_id, rating, comment, created_at
            FROM user_ratings
            WHERE user_id = %s AND entity_type = %s AND entity_id = %s
        """
        return self._execute_one(query, (user_id, entity_type, entity_id), user_id=user_id)

    def get_metrics(
        self,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get aggregated rating metrics.

        Args:
            days: Number of days to aggregate (default 30)

        Returns:
            Dict with total, by_type, by_rating, and thumbs_up_pct
        """
        # Total counts by entity type and rating
        query = """
            SELECT
                entity_type,
                rating,
                COUNT(*) as count
            FROM user_ratings
            WHERE created_at > NOW() - INTERVAL '%s days'
            GROUP BY entity_type, rating
            ORDER BY entity_type, rating
        """
        rows = self._execute_query(query, (days,))

        by_type: dict[str, dict[str, int]] = {
            "meeting": {"up": 0, "down": 0},
            "action": {"up": 0, "down": 0},
        }
        total_up = 0
        total_down = 0

        for row in rows:
            etype = row["entity_type"]
            r = row["rating"]
            c = row["count"]
            if r == 1:
                by_type[etype]["up"] = c
                total_up += c
            else:
                by_type[etype]["down"] = c
                total_down += c

        total = total_up + total_down
        thumbs_up_pct = round((total_up / total * 100), 1) if total > 0 else 0.0

        return {
            "period_days": days,
            "total": total,
            "thumbs_up": total_up,
            "thumbs_down": total_down,
            "thumbs_up_pct": thumbs_up_pct,
            "by_type": by_type,
        }

    def get_trend(
        self,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get daily rating trend.

        Args:
            days: Number of days (default 7)

        Returns:
            List of {date, up, down, total} dicts ordered by date
        """
        query = """
            SELECT
                DATE(created_at) as date,
                COUNT(*) FILTER (WHERE rating = 1) as up,
                COUNT(*) FILTER (WHERE rating = -1) as down,
                COUNT(*) as total
            FROM user_ratings
            WHERE created_at > NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """
        rows = self._execute_query(query, (days,))
        return [
            {
                "date": row["date"].isoformat()
                if isinstance(row["date"], datetime)
                else str(row["date"]),
                "up": row["up"],
                "down": row["down"],
                "total": row["total"],
            }
            for row in rows
        ]

    def get_recent_negative(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent thumbs-down ratings for admin triage.

        Includes user email and entity info for context.

        Args:
            limit: Max number of results (default 10)

        Returns:
            List of negative ratings with user/entity context
        """
        query = """
            SELECT
                r.id,
                r.user_id,
                r.entity_type,
                r.entity_id,
                r.rating,
                r.comment,
                r.created_at,
                u.email as user_email,
                CASE
                    WHEN r.entity_type = 'meeting' THEN
                        (SELECT s.problem_statement FROM sessions s WHERE s.id = r.entity_id)
                    WHEN r.entity_type = 'action' THEN
                        (SELECT a.title FROM actions a WHERE a.id = r.entity_id)
                    ELSE NULL
                END as entity_title
            FROM user_ratings r
            JOIN users u ON u.id = r.user_id
            WHERE r.rating = -1
            ORDER BY r.created_at DESC
            LIMIT %s
        """
        return self._execute_query(query, (limit,))

    def count_by_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, int]:
        """Count ratings for a specific entity.

        Args:
            entity_type: 'meeting' or 'action'
            entity_id: UUID of the entity

        Returns:
            Dict with up and down counts
        """
        self._validate_id(entity_id, "entity_id")

        query = """
            SELECT
                COUNT(*) FILTER (WHERE rating = 1) as up,
                COUNT(*) FILTER (WHERE rating = -1) as down
            FROM user_ratings
            WHERE entity_type = %s AND entity_id = %s
        """
        result = self._execute_one(query, (entity_type, entity_id))
        return (
            {"up": result["up"] or 0, "down": result["down"] or 0}
            if result
            else {"up": 0, "down": 0}
        )


# Singleton instance
ratings_repository = RatingsRepository()
