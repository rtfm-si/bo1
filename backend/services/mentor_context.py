"""Mentor context injection service.

Gathers context from multiple sources for mentor chat:
- Business context from user_context table
- Recent meetings/sessions
- Active actions
- Dataset summaries
"""

import logging
from dataclasses import dataclass
from typing import Any

from bo1.state.repositories.action_repository import ActionRepository
from bo1.state.repositories.dataset_repository import DatasetRepository
from bo1.state.repositories.session_repository import SessionRepository
from bo1.state.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@dataclass
class FailurePatternContext:
    """Container for failure pattern data."""

    failure_rate: float = 0.0
    patterns: list[dict[str, Any]] | None = None
    by_project: dict[str, int] | None = None
    by_category: dict[str, int] | None = None

    def should_inject(self) -> bool:
        """Return True if failure rate warrants context injection."""
        return self.failure_rate >= 0.3 and bool(self.patterns)


@dataclass
class MentorContext:
    """Container for all mentor context data."""

    business_context: dict[str, Any] | None = None
    recent_meetings: list[dict[str, Any]] | None = None
    active_actions: list[dict[str, Any]] | None = None
    datasets: list[dict[str, Any]] | None = None
    failure_patterns: FailurePatternContext | None = None

    def sources_used(self) -> list[str]:
        """Return list of context sources that have data."""
        sources = []
        if self.business_context:
            sources.append("business_context")
        if self.recent_meetings:
            sources.append("recent_meetings")
        if self.active_actions:
            sources.append("active_actions")
        if self.datasets:
            sources.append("datasets")
        if self.failure_patterns and self.failure_patterns.should_inject():
            sources.append("failure_patterns")
        return sources


class MentorContextService:
    """Service for gathering mentor context from multiple sources."""

    def __init__(
        self,
        user_repo: UserRepository | None = None,
        session_repo: SessionRepository | None = None,
        action_repo: ActionRepository | None = None,
        dataset_repo: DatasetRepository | None = None,
    ) -> None:
        """Initialize service with repositories.

        Args:
            user_repo: User repository instance
            session_repo: Session repository instance
            action_repo: Action repository instance
            dataset_repo: Dataset repository instance
        """
        self._user_repo = user_repo or UserRepository()
        self._session_repo = session_repo or SessionRepository()
        self._action_repo = action_repo or ActionRepository()
        self._dataset_repo = dataset_repo or DatasetRepository()

    def get_business_context(self, user_id: str) -> dict[str, Any] | None:
        """Get user's business context.

        Args:
            user_id: User identifier

        Returns:
            Business context dict or None
        """
        try:
            return self._user_repo.get_context(user_id)
        except Exception as e:
            logger.warning(f"Failed to get business context for {user_id}: {e}")
            return None

    def get_recent_meetings(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get user's recent completed meetings/sessions.

        Args:
            user_id: User identifier
            limit: Maximum number of meetings to return

        Returns:
            List of recent session dicts
        """
        try:
            sessions = self._session_repo.list_by_user(
                user_id=user_id,
                status_filter="completed",
                limit=limit,
            )
            return sessions or []
        except Exception as e:
            logger.warning(f"Failed to get recent meetings for {user_id}: {e}")
            return []

    def get_active_actions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Get user's active actions (in_progress, todo, blocked).

        Args:
            user_id: User identifier
            limit: Maximum number of actions to return

        Returns:
            List of action dicts
        """
        try:
            # Get actions with different statuses and combine
            actions = []
            for status in ["in_progress", "todo", "blocked"]:
                status_actions = self._action_repo.get_by_user(
                    user_id=user_id,
                    status_filter=status,
                    limit=limit,
                )
                actions.extend(status_actions or [])
            return actions[:limit]  # Respect limit after combining
        except Exception as e:
            logger.warning(f"Failed to get active actions for {user_id}: {e}")
            return []

    def get_dataset_summaries(self, user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get summaries of user's datasets.

        Args:
            user_id: User identifier
            limit: Maximum number of datasets to return

        Returns:
            List of dataset summary dicts
        """
        try:
            datasets, _ = self._dataset_repo.list_by_user(
                user_id=user_id,
                limit=limit,
            )
            return datasets or []
        except Exception as e:
            logger.warning(f"Failed to get datasets for {user_id}: {e}")
            return []

    def get_failure_patterns(self, user_id: str, days: int = 30) -> FailurePatternContext:
        """Get action failure patterns for proactive mentoring.

        Args:
            user_id: User identifier
            days: Days to look back

        Returns:
            FailurePatternContext with patterns and statistics
        """
        try:
            from backend.services.action_failure_detector import get_action_failure_detector

            detector = get_action_failure_detector()
            summary = detector.detect_failure_patterns(
                user_id=user_id,
                days=days,
                min_failures=3,
            )

            # Convert patterns to dicts for serialization
            patterns_dicts = [
                {
                    "action_id": p.action_id,
                    "title": p.title,
                    "project_name": p.project_name,
                    "status": p.status,
                    "failure_reason": p.failure_reason,
                    "failure_category": p.failure_category,
                }
                for p in summary.patterns
            ]

            return FailurePatternContext(
                failure_rate=summary.failure_rate,
                patterns=patterns_dicts,
                by_project=summary.by_project,
                by_category=summary.by_category,
            )
        except Exception as e:
            logger.warning(f"Failed to get failure patterns for {user_id}: {e}")
            return FailurePatternContext()

    def gather_context(self, user_id: str) -> MentorContext:
        """Gather all context for mentor chat.

        Args:
            user_id: User identifier

        Returns:
            MentorContext with all available data
        """
        return MentorContext(
            business_context=self.get_business_context(user_id),
            recent_meetings=self.get_recent_meetings(user_id),
            active_actions=self.get_active_actions(user_id),
            datasets=self.get_dataset_summaries(user_id),
            failure_patterns=self.get_failure_patterns(user_id),
        )


# Singleton instance
_mentor_context_service: MentorContextService | None = None


def get_mentor_context_service() -> MentorContextService:
    """Get or create the mentor context service singleton."""
    global _mentor_context_service
    if _mentor_context_service is None:
        _mentor_context_service = MentorContextService()
    return _mentor_context_service
