"""Tests for replanning service rollback logic.

Tests:
- Rollback on project link failure
- Rollback on action update failure
- Double-failure handling (rollback fails gracefully)
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bo1.services.replanning_service import ReplanningService


class TestReplanningServiceRollback:
    """Tests for rollback logic in ReplanningService."""

    @pytest.fixture
    def service(self):
        """Create ReplanningService with mocked Redis."""
        mock_redis = MagicMock()
        mock_redis.create_session.return_value = f"bo1_{uuid4()}"
        mock_redis.save_metadata.return_value = True
        mock_redis.load_metadata.return_value = {"status": "created"}
        return ReplanningService(redis_manager=mock_redis)

    @pytest.fixture
    def blocked_action(self):
        """Create a mock blocked action."""
        return {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "status": "blocked",
            "title": "Test action",
            "description": "Test description",
            "blocking_reason": "Test reason",
            "project_id": str(uuid4()),
        }

    @patch("bo1.services.replanning_service.action_repository")
    @patch("bo1.services.replanning_service.session_repository")
    @patch("bo1.services.replanning_service.project_repository")
    @patch("bo1.services.replanning_service.replanning_context_builder")
    def test_rollback_on_project_link_failure(
        self,
        mock_context_builder,
        mock_project_repo,
        mock_session_repo,
        mock_action_repo,
        service,
        blocked_action,
    ):
        """Test that session is rolled back when project linking fails."""
        # Setup
        mock_action_repo.get.return_value = blocked_action
        mock_context_builder.gather_related_context.return_value = {}
        mock_context_builder.build_replan_problem_statement.return_value = "Problem"
        mock_context_builder.build_problem_context.return_value = {}
        mock_session_repo.create.return_value = {"id": service.redis_manager.create_session()}

        # Make project link fail
        mock_project_repo.link_session.side_effect = Exception("DB connection error")

        # Execute
        with pytest.raises(RuntimeError, match="Failed to link session to project"):
            service.create_replan_session(
                action_id=blocked_action["id"],
                user_id=blocked_action["user_id"],
            )

        # Verify rollback was called
        mock_session_repo.delete.assert_called_once()
        service.redis_manager.delete_state.assert_called_once()
        service.redis_manager.remove_session_from_user_index.assert_called_once()

    @patch("bo1.services.replanning_service.action_repository")
    @patch("bo1.services.replanning_service.session_repository")
    @patch("bo1.services.replanning_service.project_repository")
    @patch("bo1.services.replanning_service.replanning_context_builder")
    def test_rollback_on_action_update_failure(
        self,
        mock_context_builder,
        mock_project_repo,
        mock_session_repo,
        mock_action_repo,
        service,
        blocked_action,
    ):
        """Test that session is rolled back when action update fails."""
        # Setup
        mock_action_repo.get.return_value = blocked_action
        mock_context_builder.gather_related_context.return_value = {}
        mock_context_builder.build_replan_problem_statement.return_value = "Problem"
        mock_context_builder.build_problem_context.return_value = {}
        mock_session_repo.create.return_value = {"id": service.redis_manager.create_session()}
        mock_project_repo.link_session.return_value = {}

        # Make action update fail via db_session
        with patch("bo1.services.replanning_service.db_session") as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.execute.side_effect = Exception("Action update failed")

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor

            mock_db.return_value = mock_conn

            # Execute
            with pytest.raises(RuntimeError, match="Failed to update action"):
                service.create_replan_session(
                    action_id=blocked_action["id"],
                    user_id=blocked_action["user_id"],
                )

        # Verify unlink was called before rollback
        mock_project_repo.unlink_session.assert_called_once_with(
            blocked_action["project_id"],
            mock_session_repo.create.return_value["id"],
        )

        # Verify rollback was called
        mock_session_repo.delete.assert_called_once()
        service.redis_manager.delete_state.assert_called_once()

    @patch("bo1.services.replanning_service.action_repository")
    @patch("bo1.services.replanning_service.session_repository")
    @patch("bo1.services.replanning_service.project_repository")
    @patch("bo1.services.replanning_service.replanning_context_builder")
    def test_rollback_continues_on_redis_failure(
        self,
        mock_context_builder,
        mock_project_repo,
        mock_session_repo,
        mock_action_repo,
        blocked_action,
    ):
        """Test that rollback logs but doesn't re-raise on Redis failure."""
        # Create service with Redis that fails during cleanup
        mock_redis = MagicMock()
        session_id = f"bo1_{uuid4()}"
        mock_redis.create_session.return_value = session_id
        mock_redis.save_metadata.return_value = True
        mock_redis.delete_state.side_effect = Exception("Redis connection lost")
        mock_redis.remove_session_from_user_index.side_effect = Exception("Redis unavailable")

        service = ReplanningService(redis_manager=mock_redis)

        # Setup
        mock_action_repo.get.return_value = blocked_action
        mock_context_builder.gather_related_context.return_value = {}
        mock_context_builder.build_replan_problem_statement.return_value = "Problem"
        mock_context_builder.build_problem_context.return_value = {}
        mock_session_repo.create.return_value = {"id": session_id}

        # Make project link fail to trigger rollback
        mock_project_repo.link_session.side_effect = Exception("DB error")

        # Execute - should raise the original error, not Redis error
        with pytest.raises(RuntimeError, match="Failed to link session to project"):
            service.create_replan_session(
                action_id=blocked_action["id"],
                user_id=blocked_action["user_id"],
            )

        # Verify PostgreSQL delete was still attempted
        mock_session_repo.delete.assert_called_once()

    @patch("bo1.services.replanning_service.action_repository")
    @patch("bo1.services.replanning_service.session_repository")
    @patch("bo1.services.replanning_service.project_repository")
    @patch("bo1.services.replanning_service.replanning_context_builder")
    def test_no_rollback_on_success(
        self,
        mock_context_builder,
        mock_project_repo,
        mock_session_repo,
        mock_action_repo,
        service,
        blocked_action,
    ):
        """Test that rollback is NOT called when everything succeeds."""
        # Setup
        session_id = service.redis_manager.create_session()
        mock_action_repo.get.return_value = blocked_action
        mock_context_builder.gather_related_context.return_value = {}
        mock_context_builder.build_replan_problem_statement.return_value = "Problem"
        mock_context_builder.build_problem_context.return_value = {}
        mock_session_repo.create.return_value = {"id": session_id}
        mock_project_repo.link_session.return_value = {}

        # Mock successful db_session for action update
        with patch("bo1.services.replanning_service.db_session") as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.rowcount = 1

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor

            mock_db.return_value = mock_conn

            # Execute
            result = service.create_replan_session(
                action_id=blocked_action["id"],
                user_id=blocked_action["user_id"],
            )

        # Verify success
        assert result["session_id"] == session_id
        assert result["is_existing"] is False

        # Verify rollback was NOT called
        mock_session_repo.delete.assert_not_called()
        service.redis_manager.delete_state.assert_not_called()

    @patch("bo1.services.replanning_service.action_repository")
    @patch("bo1.services.replanning_service.session_repository")
    @patch("bo1.services.replanning_service.project_repository")
    @patch("bo1.services.replanning_service.replanning_context_builder")
    def test_no_project_unlink_when_no_project(
        self,
        mock_context_builder,
        mock_project_repo,
        mock_session_repo,
        mock_action_repo,
        service,
    ):
        """Test that unlink is NOT called during rollback if action has no project."""
        # Setup action WITHOUT project
        action_without_project = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "status": "blocked",
            "title": "Test action",
            "blocking_reason": "Test reason",
            "project_id": None,  # No project
        }

        mock_action_repo.get.return_value = action_without_project
        mock_context_builder.gather_related_context.return_value = {}
        mock_context_builder.build_replan_problem_statement.return_value = "Problem"
        mock_context_builder.build_problem_context.return_value = {}
        mock_session_repo.create.return_value = {"id": service.redis_manager.create_session()}

        # Make action update fail via db_session
        with patch("bo1.services.replanning_service.db_session") as mock_db:
            mock_cursor = MagicMock()
            mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
            mock_cursor.__exit__ = MagicMock(return_value=False)
            mock_cursor.execute.side_effect = Exception("Action update failed")

            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value = mock_cursor

            mock_db.return_value = mock_conn

            # Execute
            with pytest.raises(RuntimeError, match="Failed to update action"):
                service.create_replan_session(
                    action_id=action_without_project["id"],
                    user_id=action_without_project["user_id"],
                )

        # Verify unlink was NOT called (no project to unlink)
        mock_project_repo.unlink_session.assert_not_called()

        # But rollback should still happen
        mock_session_repo.delete.assert_called_once()
