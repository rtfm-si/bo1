"""Action failure pattern detector for proactive mentoring.

Analyzes user actions to detect patterns of failures/cancellations
to enable proactive improvement suggestions.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """A detected action failure pattern."""

    action_id: str
    title: str
    project_id: str | None
    project_name: str | None
    status: str  # cancelled or blocked
    priority: str
    failure_reason: str | None
    failure_category: str | None  # blocker/scope_creep/dependency/unknown
    failed_at: str  # ISO timestamp
    tags: list[str]


@dataclass
class FailurePatternSummary:
    """Summary of failure patterns for a user."""

    patterns: list[FailurePattern]
    failure_rate: float  # 0.0 to 1.0
    total_actions: int
    failed_actions: int
    period_days: int
    by_project: dict[str, int]  # project_name -> failure count
    by_category: dict[str, int]  # failure_category -> count


class ActionFailureDetector:
    """Detects action failure patterns for proactive mentoring.

    Analyzes cancelled and blocked actions to identify:
    - High failure rates
    - Patterns by project
    - Patterns by failure reason category
    """

    def detect_failure_patterns(
        self,
        user_id: str,
        days: int = 30,
        min_failures: int = 3,
    ) -> FailurePatternSummary:
        """Detect action failure patterns for a user.

        Args:
            user_id: User ID to analyze
            days: Days to look back (7-90)
            min_failures: Minimum failures to include pattern (2-10)

        Returns:
            FailurePatternSummary with patterns and statistics
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        # Get failed actions (cancelled or blocked)
        failed_actions = self._get_failed_actions(user_id, cutoff)

        # Get total action count for failure rate
        total_count = self._get_total_action_count(user_id, cutoff)

        # Build patterns list
        patterns: list[FailurePattern] = []
        by_project: dict[str, int] = {}
        by_category: dict[str, int] = {}

        for action in failed_actions:
            pattern = FailurePattern(
                action_id=str(action["id"]),
                title=action.get("title", "Untitled"),
                project_id=str(action["project_id"]) if action.get("project_id") else None,
                project_name=action.get("project_name"),
                status=action.get("status", "cancelled"),
                priority=action.get("priority", "medium"),
                failure_reason=action.get("cancellation_reason") or action.get("blocking_reason"),
                failure_category=action.get("failure_reason_category"),
                failed_at=(action.get("cancelled_at") or action.get("blocked_at") or "").isoformat()
                if isinstance(action.get("cancelled_at") or action.get("blocked_at"), datetime)
                else str(action.get("cancelled_at") or action.get("blocked_at") or ""),
                tags=action.get("tags", []) or [],
            )
            patterns.append(pattern)

            # Aggregate by project
            project_key = pattern.project_name or "No Project"
            by_project[project_key] = by_project.get(project_key, 0) + 1

            # Aggregate by category
            category_key = pattern.failure_category or "unknown"
            by_category[category_key] = by_category.get(category_key, 0) + 1

        # Calculate failure rate
        failed_count = len(patterns)
        failure_rate = failed_count / total_count if total_count > 0 else 0.0

        return FailurePatternSummary(
            patterns=patterns,
            failure_rate=failure_rate,
            total_actions=total_count,
            failed_actions=failed_count,
            period_days=days,
            by_project=by_project,
            by_category=by_category,
        )

    def _get_failed_actions(self, user_id: str, cutoff: datetime) -> list[dict[str, Any]]:
        """Get cancelled/blocked actions with context."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        a.id,
                        a.title,
                        a.project_id,
                        p.name as project_name,
                        a.status,
                        a.priority,
                        a.cancellation_reason,
                        a.cancelled_at,
                        a.blocking_reason,
                        a.blocked_at,
                        a.failure_reason_category,
                        COALESCE(
                            (SELECT array_agg(t.name)
                             FROM action_tags at
                             JOIN tags t ON t.id = at.tag_id
                             WHERE at.action_id = a.id),
                            '{}'::text[]
                        ) as tags
                    FROM actions a
                    LEFT JOIN projects p ON p.id = a.project_id
                    WHERE a.user_id = %s
                    AND a.status IN ('cancelled', 'blocked')
                    AND (a.cancelled_at >= %s OR a.blocked_at >= %s OR a.updated_at >= %s)
                    AND a.deleted_at IS NULL
                    ORDER BY COALESCE(a.cancelled_at, a.blocked_at, a.updated_at) DESC
                    LIMIT 100
                    """,
                    (user_id, cutoff, cutoff, cutoff),
                )
                return [dict(row) for row in cur.fetchall()]

    def _get_total_action_count(self, user_id: str, cutoff: datetime) -> int:
        """Get total action count in the period."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM actions
                    WHERE user_id = %s
                    AND created_at >= %s
                    AND deleted_at IS NULL
                    """,
                    (user_id, cutoff),
                )
                result = cur.fetchone()
                return result["count"] if result else 0


# Module-level singleton


@lru_cache(maxsize=1)
def get_action_failure_detector() -> ActionFailureDetector:
    """Get or create the action failure detector singleton."""
    return ActionFailureDetector()
