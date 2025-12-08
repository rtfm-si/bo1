"""Replanning service for managing AI-assisted replanning workflows.

Handles:
- Creating replanning sessions for blocked actions
- Linking sessions to projects
- Updating actions with replanning references
"""

from datetime import UTC, datetime
from typing import Any

from bo1.services.replanning_context import replanning_context_builder
from bo1.state.database import db_session
from bo1.state.redis_manager import RedisManager
from bo1.state.repositories import session_repository
from bo1.state.repositories.action_repository import action_repository
from bo1.state.repositories.project_repository import project_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)


class ReplanningService:
    """Service for managing replanning workflows."""

    def __init__(self, redis_manager: RedisManager | None = None) -> None:
        """Initialize the replanning service.

        Args:
            redis_manager: Optional Redis manager instance. If not provided,
                          will be created on first use.
        """
        self._redis_manager = redis_manager

    @property
    def redis_manager(self) -> RedisManager:
        """Get or create the Redis manager."""
        if self._redis_manager is None:
            self._redis_manager = RedisManager()
        return self._redis_manager

    def create_replan_session(
        self,
        action_id: str,
        user_id: str,
        additional_context: str | None = None,
    ) -> dict[str, Any]:
        """Create a replanning session for a blocked action.

        Steps:
        1. Get action details and verify blocked status
        2. Build replanning context
        3. Create session with merged context
        4. Link session to project with 'replanning' relationship
        5. Update action with replan_session_id
        6. Return session details

        Args:
            action_id: ID of the blocked action to replan
            user_id: ID of the user requesting replanning
            additional_context: Optional user-provided context

        Returns:
            Dictionary with session_id, action_id, message, and redirect_url

        Raises:
            ValueError: If action not found, not owned by user, or not blocked
        """
        # 1. Get action and verify it's blocked
        action = action_repository.get(action_id)
        if not action or action.get("user_id") != user_id:
            raise ValueError(f"Action {action_id} not found or not accessible")

        if action.get("status") != "blocked":
            raise ValueError(
                f"Action is not blocked (status: {action.get('status')}). "
                "Only blocked actions can be replanned."
            )

        # Check if there's already a replanning session
        existing_replan = action.get("replan_session_id")
        if existing_replan:
            return {
                "session_id": existing_replan,
                "action_id": action_id,
                "message": "A replanning session already exists for this action.",
                "redirect_url": f"/meeting/{existing_replan}",
                "is_existing": True,
            }

        # 2. Build replanning context
        related_context = replanning_context_builder.gather_related_context(action_id, user_id)
        problem_statement = replanning_context_builder.build_replan_problem_statement(
            action, additional_context
        )
        problem_context = replanning_context_builder.build_problem_context(related_context)

        # 3. Create new session
        session_id = self.redis_manager.create_session()
        now = datetime.now(UTC)

        # Create session metadata
        metadata = {
            "status": "created",
            "phase": None,
            "user_id": user_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "problem_statement": problem_statement,
            "problem_context": problem_context,
            "is_replanning": True,
            "original_action_id": action_id,
        }

        # Save to Redis
        if not self.redis_manager.save_metadata(session_id, metadata):
            raise RuntimeError("Failed to save replanning session metadata to Redis")

        # Add to user's session index
        self.redis_manager.add_session_to_user_index(user_id, session_id)

        # Save to PostgreSQL
        try:
            session_repository.create(
                session_id=session_id,
                user_id=user_id,
                problem_statement=problem_statement,
                problem_context=problem_context,
                status="created",
            )
            logger.info(f"Created replanning session {session_id} for action {action_id}")
        except Exception as e:
            # Clean up Redis on PostgreSQL failure
            logger.error(f"Failed to save replanning session to PostgreSQL: {e}")
            try:
                self.redis_manager.delete_state(session_id)
                self.redis_manager.remove_session_from_user_index(user_id, session_id)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up Redis: {cleanup_error}")
            raise RuntimeError("Failed to create replanning session") from e

        # 4. Link session to project (if action has a project)
        project_id = action.get("project_id")
        if project_id:
            try:
                project_repository.link_session(
                    project_id=project_id,
                    session_id=session_id,
                    relationship="replanning",
                )
                logger.info(f"Linked replanning session {session_id} to project {project_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to link replanning session to project: {e}. "
                    "Session created but not linked."
                )

        # 5. Update action with replan_session_id
        try:
            self._update_action_replan_fields(
                action_id=action_id,
                user_id=user_id,
                replan_session_id=session_id,
                replanning_reason=additional_context,
            )
        except Exception as e:
            logger.warning(
                f"Failed to update action with replanning info: {e}. "
                "Session created but action not updated."
            )

        # 6. Return session details
        return {
            "session_id": session_id,
            "action_id": action_id,
            "message": "Replanning session created successfully.",
            "redirect_url": f"/meeting/{session_id}",
            "is_existing": False,
        }

    def _update_action_replan_fields(
        self,
        action_id: str,
        user_id: str,
        replan_session_id: str,
        replanning_reason: str | None,
    ) -> None:
        """Update action with replanning session info.

        Args:
            action_id: ID of the action to update
            user_id: ID of the user (for verification)
            replan_session_id: ID of the created replanning session
            replanning_reason: User-provided reason for replanning
        """
        now = datetime.now(UTC)

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET replan_session_id = %s,
                        replan_requested_at = %s,
                        replanning_reason = %s,
                        updated_at = %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (
                        replan_session_id,
                        now,
                        replanning_reason,
                        now,
                        action_id,
                        user_id,
                    ),
                )

                if cur.rowcount == 0:
                    raise ValueError(
                        f"Failed to update action {action_id} - not found or not owned by user"
                    )

            conn.commit()

        logger.info(f"Updated action {action_id} with replan_session_id={replan_session_id}")

    def get_replan_status(
        self,
        action_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Get replanning status for an action.

        Args:
            action_id: ID of the action
            user_id: ID of the user

        Returns:
            Dictionary with replanning status info
        """
        action = action_repository.get(action_id)
        if not action or action.get("user_id") != user_id:
            raise ValueError(f"Action {action_id} not found")

        replan_session_id = action.get("replan_session_id")
        if not replan_session_id:
            return {
                "has_replan_session": False,
                "can_replan": action.get("status") == "blocked",
            }

        # Get session status
        metadata = self.redis_manager.load_metadata(replan_session_id)
        session_status = metadata.get("status") if metadata else "unknown"

        return {
            "has_replan_session": True,
            "replan_session_id": replan_session_id,
            "replan_requested_at": action.get("replan_requested_at"),
            "replanning_reason": action.get("replanning_reason"),
            "session_status": session_status,
            "can_replan": False,  # Already has a session
        }


# Singleton instance
replanning_service = ReplanningService()
