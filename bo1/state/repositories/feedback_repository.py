"""Feedback repository for managing feature requests and problem reports.

Provides:
- Create feedback submissions
- List feedback with filters
- Get feedback by ID
- Update feedback status
- Get feedback statistics
"""

import logging
from typing import Any
from uuid import uuid4

from psycopg2.extras import Json

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FeedbackRepository(BaseRepository):
    """Repository for the feedback table."""

    def create_feedback(
        self,
        user_id: str,
        feedback_type: str,
        title: str,
        description: str,
        context: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new feedback submission.

        Args:
            user_id: Submitter's user ID
            feedback_type: Type (feature_request or problem_report)
            title: Brief title/summary
            description: Detailed description
            context: Optional auto-attached context
            analysis: Optional sentiment/themes analysis

        Returns:
            Created feedback dict
        """
        self._validate_id(user_id, "user_id")
        feedback_id = str(uuid4())

        query = """
            INSERT INTO feedback (id, user_id, type, title, description, context, analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, type, title, description, context, analysis,
                      status, created_at, updated_at
        """
        return self._execute_returning(
            query,
            (
                feedback_id,
                user_id,
                feedback_type,
                title,
                description,
                Json(context) if context else None,
                Json(analysis) if analysis else None,
            ),
            user_id=user_id,
        )

    def get_feedback_by_id(
        self, feedback_id: str, user_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get feedback by ID.

        Args:
            feedback_id: The feedback UUID
            user_id: Optional user ID for RLS

        Returns:
            Feedback dict or None if not found
        """
        self._validate_id(feedback_id, "feedback_id")
        query = """
            SELECT id, user_id, type, title, description, context, analysis,
                   status, created_at, updated_at
            FROM feedback
            WHERE id = %s
        """
        return self._execute_one(query, (feedback_id,), user_id=user_id)

    def list_feedback(
        self,
        feedback_type: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        sentiment: str | None = None,
        theme: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List feedback with optional filters.

        Args:
            feedback_type: Filter by type (feature_request or problem_report)
            status: Filter by status (new, reviewing, resolved, closed)
            user_id: Filter by user (None = all users for admin)
            sentiment: Filter by sentiment (positive, negative, neutral, mixed)
            theme: Filter by theme (e.g., "usability", "performance")
            limit: Max results to return
            offset: Number of results to skip

        Returns:
            List of feedback dicts
        """
        conditions: list[str] = []
        params: list[Any] = []

        if feedback_type:
            conditions.append("type = %s")
            params.append(feedback_type)

        if status:
            conditions.append("status = %s")
            params.append(status)

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        if sentiment:
            conditions.append("analysis->>'sentiment' = %s")
            params.append(sentiment)

        if theme:
            conditions.append("analysis->'themes' ? %s")
            params.append(theme)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT id, user_id, type, title, description, context, analysis,
                   status, created_at, updated_at
            FROM feedback
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        return self._execute_query(query, tuple(params))

    def count_feedback(
        self,
        feedback_type: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        sentiment: str | None = None,
        theme: str | None = None,
    ) -> int:
        """Count feedback with optional filters.

        Args:
            feedback_type: Filter by type
            status: Filter by status
            user_id: Filter by user
            sentiment: Filter by sentiment
            theme: Filter by theme

        Returns:
            Total count
        """
        conditions: list[str] = []
        params: list[Any] = []

        if feedback_type:
            conditions.append("type = %s")
            params.append(feedback_type)

        if status:
            conditions.append("status = %s")
            params.append(status)

        if user_id:
            conditions.append("user_id = %s")
            params.append(user_id)

        if sentiment:
            conditions.append("analysis->>'sentiment' = %s")
            params.append(sentiment)

        if theme:
            conditions.append("analysis->'themes' ? %s")
            params.append(theme)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT COUNT(*) as count
            FROM feedback
            {where_clause}
        """
        result = self._execute_one(query, tuple(params) if params else None)
        return result["count"] if result else 0

    def update_status(self, feedback_id: str, status: str) -> dict[str, Any] | None:
        """Update feedback status.

        Args:
            feedback_id: The feedback UUID
            status: New status

        Returns:
            Updated feedback dict or None if not found
        """
        self._validate_id(feedback_id, "feedback_id")
        query = """
            UPDATE feedback
            SET status = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, user_id, type, title, description, context, analysis,
                      status, created_at, updated_at
        """
        return self._execute_one(query, (status, feedback_id))

    def get_stats(self) -> dict[str, Any]:
        """Get feedback statistics.

        Returns:
            Stats dict with total, by_type, and by_status counts
        """
        # Get total
        total_query = "SELECT COUNT(*) as count FROM feedback"
        total_result = self._execute_one(total_query)
        total = total_result["count"] if total_result else 0

        # Get counts by type
        type_query = """
            SELECT type, COUNT(*) as count
            FROM feedback
            GROUP BY type
        """
        type_rows = self._execute_query(type_query)
        by_type = {row["type"]: row["count"] for row in type_rows}

        # Get counts by status
        status_query = """
            SELECT status, COUNT(*) as count
            FROM feedback
            GROUP BY status
        """
        status_rows = self._execute_query(status_query)
        by_status = {row["status"]: row["count"] for row in status_rows}

        return {
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
        }

    def get_analysis_summary(self) -> dict[str, Any]:
        """Get aggregated analysis stats (sentiment and themes).

        Returns:
            Dict with sentiment_counts and top_themes
        """
        # Get sentiment distribution
        sentiment_query = """
            SELECT analysis->>'sentiment' as sentiment, COUNT(*) as count
            FROM feedback
            WHERE analysis IS NOT NULL
            GROUP BY analysis->>'sentiment'
        """
        sentiment_rows = self._execute_query(sentiment_query)
        sentiment_counts = {
            row["sentiment"]: row["count"] for row in sentiment_rows if row["sentiment"]
        }

        # Get top themes (flatten JSONB array and count)
        themes_query = """
            SELECT theme, COUNT(*) as count
            FROM feedback, jsonb_array_elements_text(analysis->'themes') as theme
            WHERE analysis IS NOT NULL
            GROUP BY theme
            ORDER BY count DESC
            LIMIT 15
        """
        theme_rows = self._execute_query(themes_query)
        top_themes = [{"theme": row["theme"], "count": row["count"]} for row in theme_rows]

        # Get total analyzed count
        analyzed_query = """
            SELECT COUNT(*) as count
            FROM feedback
            WHERE analysis IS NOT NULL
        """
        analyzed_result = self._execute_one(analyzed_query)
        analyzed_count = analyzed_result["count"] if analyzed_result else 0

        return {
            "analyzed_count": analyzed_count,
            "sentiment_counts": sentiment_counts,
            "top_themes": top_themes,
        }

    def get_feedback_by_theme(self, theme: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get feedback items that mention a specific theme.

        Args:
            theme: Theme tag to filter by
            limit: Max results

        Returns:
            List of feedback dicts with the theme
        """
        query = """
            SELECT id, user_id, type, title, description, context, analysis,
                   status, created_at, updated_at
            FROM feedback
            WHERE analysis->'themes' ? %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        return self._execute_query(query, (theme, limit))

    def get_user_recent_count(self, user_id: str, hours: int = 1) -> int:
        """Get count of feedback submitted by user in the last N hours.

        Used for rate limiting.

        Args:
            user_id: The user ID
            hours: Time window in hours

        Returns:
            Count of feedback in time window
        """
        self._validate_id(user_id, "user_id")
        query = """
            SELECT COUNT(*) as count
            FROM feedback
            WHERE user_id = %s
              AND created_at > NOW() - INTERVAL '%s hours'
        """
        result = self._execute_one(query, (user_id, hours), user_id=user_id)
        return result["count"] if result else 0


# Singleton instance
feedback_repository = FeedbackRepository()
