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

    def test_admin_also_excludes_soft_deleted_actions(self, mock_connection, mock_cursor):
        """Verify admin query also excludes soft-deleted actions from list view.

        Admins can use separate restore endpoint to view/restore deleted actions.
        """
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=True)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Admin should also have deleted_at filter (always applied now)
        assert "a.deleted_at IS NULL" in executed_query


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


class TestAcknowledgedFailureVisibility:
    """Test action visibility for acknowledged failed sessions."""

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

    def test_non_admin_query_includes_acknowledged_failures(self, mock_connection, mock_cursor):
        """Verify non-admin query allows actions from acknowledged failed sessions."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=False)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Non-admin should now include actions from acknowledged failed sessions
        assert "s.status = 'completed'" in executed_query
        assert "s.status = 'failed'" in executed_query
        assert "failure_acknowledged_at IS NOT NULL" in executed_query

    def test_query_structure_for_visibility_with_acknowledged_failures(
        self, mock_connection, mock_cursor
    ):
        """Verify the SQL structure correctly handles all visibility cases."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", is_admin=False)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Should have OR condition structure allowing:
        # 1. Completed sessions
        # 2. Actions without sessions (NULL session)
        # 3. Failed sessions that are acknowledged
        assert "OR" in executed_query
        assert "s.id IS NULL" in executed_query


class TestTagFilteringWithCTE:
    """Test CTE + JOIN pattern for tag filtering."""

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

    def test_no_tag_filter_no_cte(self, mock_connection, mock_cursor):
        """Verify query has no CTE when no tag_ids provided."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123")

        executed_query = mock_cursor.execute.call_args[0][0]

        # Should NOT have CTE or matched_actions join
        assert "WITH matched_actions" not in executed_query
        assert "INNER JOIN matched_actions" not in executed_query

    def test_single_tag_filter_uses_cte(self, mock_connection, mock_cursor):
        """Verify query uses CTE pattern when one tag_id is provided."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", tag_ids=["tag_abc"])

        executed_query = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        # Should have CTE and INNER JOIN
        assert "WITH matched_actions AS" in executed_query
        assert "INNER JOIN matched_actions ma ON a.id = ma.action_id" in executed_query
        # CTE body should have correct structure
        assert "at.tag_id = ANY(%s)" in executed_query
        assert "GROUP BY at.action_id" in executed_query
        assert "HAVING COUNT(DISTINCT at.tag_id) = %s" in executed_query
        # Params: [tag_ids, len(tag_ids), user_id, limit, offset]
        assert params[0] == ["tag_abc"]
        assert params[1] == 1

    def test_multiple_tags_filter_uses_cte(self, mock_connection, mock_cursor):
        """Verify query uses CTE pattern when multiple tag_ids are provided."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", tag_ids=["tag_abc", "tag_def"])

        executed_query = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        # Should have CTE with correct count for AND logic
        assert "WITH matched_actions AS" in executed_query
        assert "HAVING COUNT(DISTINCT at.tag_id) = %s" in executed_query
        # Params: [tag_ids, len(tag_ids)=2, user_id, limit, offset]
        assert params[0] == ["tag_abc", "tag_def"]
        assert params[1] == 2

    def test_tag_filter_combined_with_status_filter(self, mock_connection, mock_cursor):
        """Verify tag CTE works with status filter."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", tag_ids=["tag_abc"], status_filter="todo")

        executed_query = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]

        # Should have both CTE and status filter
        assert "WITH matched_actions AS" in executed_query
        assert "a.status = %s" in executed_query
        # Params: [tag_ids, len(tag_ids), user_id, status_filter, limit, offset]
        assert "todo" in params

    def test_tag_filter_with_admin_excludes_visibility_filter(self, mock_connection, mock_cursor):
        """Verify admin with tag filter doesn't have session status filter."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", tag_ids=["tag_abc"], is_admin=True)

        executed_query = mock_cursor.execute.call_args[0][0]

        # Should have CTE but NOT session status filter
        assert "WITH matched_actions AS" in executed_query
        assert "s.status = 'completed'" not in executed_query

    def test_tag_filter_preserves_no_correlated_subquery(self, mock_connection, mock_cursor):
        """Verify the old correlated subquery pattern is NOT present."""
        from bo1.state.repositories.action_repository import ActionRepository

        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_connection

            repo = ActionRepository()
            repo.get_by_user("user_123", tag_ids=["tag_abc"])

        executed_query = mock_cursor.execute.call_args[0][0]

        # Should NOT have the old correlated IN subquery pattern
        assert "AND a.id IN (" not in executed_query
        assert "a.id IN (SELECT at.action_id" not in executed_query
