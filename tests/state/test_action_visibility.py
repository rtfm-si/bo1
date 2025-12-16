"""Tests for action visibility based on session status (P1-007).

P1-007: Non-admin users only see actions from completed sessions.
Admin users see all actions regardless of session status.

This is intentional design, not a bug.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestActionVisibilityBySessionStatus:
    """Test action_repository.get_by_user filters by session status correctly."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with RealDictCursor-like behavior."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_non_admin_only_sees_completed_sessions(self, mock_connection, mock_cursor):
        """Verify non-admin query includes session status filter (P1-007)."""
        from bo1.state.repositories.action_repository import ActionRepository

        # Patch at both base.py and action_repository.py locations
        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=False)

        # Verify execute was called
        mock_cursor.execute.assert_called_once()
        executed_query = mock_cursor.execute.call_args[0][0]

        # Non-admin should filter by completed session status
        assert "s.status = 'completed'" in executed_query or (
            "(s.status = 'completed' OR s.id IS NULL)" in executed_query
        )

    def test_admin_sees_all_sessions(self, mock_connection, mock_cursor):
        """Verify admin query does NOT filter by session status."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=True)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Admin should NOT have session status filter
        assert "s.status = 'completed'" not in executed_query

    def test_non_admin_excludes_soft_deleted_actions(self, mock_connection, mock_cursor):
        """Verify non-admin query excludes soft-deleted actions (P1-005)."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=False)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Non-admin should exclude soft-deleted actions
        assert "deleted_at IS NULL" in executed_query

    def test_admin_can_see_soft_deleted_actions(self, mock_connection, mock_cursor):
        """Verify admin query does not exclude soft-deleted actions."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=True)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Admin should NOT have deleted_at filter
        assert "a.deleted_at IS NULL" not in executed_query


class TestActionVisibilityWithFilters:
    """Test action visibility with additional filters."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchall.return_value = []
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_status_filter_combined_with_visibility(self, mock_connection, mock_cursor):
        """Verify status filter works with visibility rules."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", status_filter="todo", is_admin=False)

        executed_query = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        # Should have both visibility and status filter
        assert "s.status = 'completed'" in executed_query or (
            "(s.status = 'completed' OR s.id IS NULL)" in executed_query
        )
        assert "a.status = %s" in executed_query
        assert "todo" in params

    def test_session_filter_combined_with_visibility(self, mock_connection, mock_cursor):
        """Verify session_id filter works with visibility rules."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", session_id="session_456", is_admin=False)

        executed_query = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        # Should have both visibility and session filter
        assert "s.status = 'completed'" in executed_query or (
            "(s.status = 'completed' OR s.id IS NULL)" in executed_query
        )
        assert "a.source_session_id = %s" in executed_query
        assert "session_456" in params


class TestActionVisibilityReturnsCorrectData:
    """Test that visibility rules return correct action data."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_returns_actions_from_completed_session(self, mock_connection, mock_cursor):
        """Verify actions from completed sessions are returned for non-admin."""
        from bo1.state.repositories.action_repository import ActionRepository

        mock_action = {
            "id": "action_123",
            "user_id": "user_123",
            "source_session_id": "session_completed",
            "project_id": None,
            "title": "Test Action",
            "description": "A test action",
            "what_and_how": [],
            "success_criteria": [],
            "kill_criteria": [],
            "status": "todo",
            "priority": "medium",
            "category": "implementation",
            "timeline": None,
            "estimated_duration_days": None,
            "target_start_date": None,
            "target_end_date": None,
            "estimated_start_date": None,
            "estimated_end_date": None,
            "actual_start_date": None,
            "actual_end_date": None,
            "blocking_reason": None,
            "blocked_at": None,
            "auto_unblock": False,
            "replan_session_id": None,
            "replan_requested_at": None,
            "replanning_reason": None,
            "cancellation_reason": None,
            "cancelled_at": None,
            "confidence": 0.0,
            "source_section": None,
            "sub_problem_index": None,
            "sort_order": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        mock_cursor.fetchall.return_value = [mock_action]

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            results = repo.get_by_user("user_123", is_admin=False)

        assert len(results) == 1
        assert results[0]["id"] == "action_123"
        assert results[0]["title"] == "Test Action"

    def test_admin_returns_all_actions(self, mock_connection, mock_cursor):
        """Verify admin sees actions from all session statuses."""
        from bo1.state.repositories.action_repository import ActionRepository

        mock_actions = [
            {
                "id": "action_completed",
                "user_id": "user_123",
                "source_session_id": "session_completed",
                "project_id": None,
                "title": "Action from Completed Session",
                "description": "",
                "what_and_how": [],
                "success_criteria": [],
                "kill_criteria": [],
                "status": "todo",
                "priority": "medium",
                "category": "implementation",
                "timeline": None,
                "estimated_duration_days": None,
                "target_start_date": None,
                "target_end_date": None,
                "estimated_start_date": None,
                "estimated_end_date": None,
                "actual_start_date": None,
                "actual_end_date": None,
                "blocking_reason": None,
                "blocked_at": None,
                "auto_unblock": False,
                "replan_session_id": None,
                "replan_requested_at": None,
                "replanning_reason": None,
                "cancellation_reason": None,
                "cancelled_at": None,
                "confidence": 0.0,
                "source_section": None,
                "sub_problem_index": None,
                "sort_order": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "id": "action_running",
                "user_id": "user_123",
                "source_session_id": "session_running",
                "project_id": None,
                "title": "Action from Running Session",
                "description": "",
                "what_and_how": [],
                "success_criteria": [],
                "kill_criteria": [],
                "status": "todo",
                "priority": "medium",
                "category": "implementation",
                "timeline": None,
                "estimated_duration_days": None,
                "target_start_date": None,
                "target_end_date": None,
                "estimated_start_date": None,
                "estimated_end_date": None,
                "actual_start_date": None,
                "actual_end_date": None,
                "blocking_reason": None,
                "blocked_at": None,
                "auto_unblock": False,
                "replan_session_id": None,
                "replan_requested_at": None,
                "replanning_reason": None,
                "cancellation_reason": None,
                "cancelled_at": None,
                "confidence": 0.0,
                "source_section": None,
                "sub_problem_index": None,
                "sort_order": 1,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ]
        mock_cursor.fetchall.return_value = mock_actions

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            results = repo.get_by_user("user_123", is_admin=True)

        # Admin should see both actions
        assert len(results) == 2
        titles = [r["title"] for r in results]
        assert "Action from Completed Session" in titles
        assert "Action from Running Session" in titles
