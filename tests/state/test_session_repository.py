"""Tests for SessionRepository optimizations and Session model.

Validates:
- list_by_user JOIN query (replaces correlated subqueries)
- save_events_batch batch insert (replaces individual inserts)
- Session Pydantic model from_db_row conversion
- get_session() and create_session() typed methods
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from bo1.models.session import Session, SessionStatus


class TestListByUserQuery:
    """Test list_by_user method returns correct aggregate counts."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with RealDictCursor-like behavior."""
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

    def test_list_by_user_returns_aggregate_counts(self, mock_connection, mock_cursor):
        """Verify JOIN query returns expected aggregate columns."""
        from bo1.state.repositories.session_repository import SessionRepository

        # Mock row data matching new query structure
        mock_row = {
            "id": "bo1_test123",
            "user_id": "user_abc",
            "problem_statement": "Test problem",
            "problem_context": None,
            "status": "completed",
            "phase": "synthesis",
            "total_cost": 0.05,
            "round_number": 3,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "synthesis_text": "Final synthesis",
            "final_recommendation": "Do it",
            "expert_count": 4,
            "contribution_count": 12,
            "task_count": 5,
            "focus_area_count": 2,
        }
        mock_cursor.fetchall.return_value = [mock_row]

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            results = repo.list_by_user("user_abc")

        assert len(results) == 1
        result = results[0]
        assert result["expert_count"] == 4
        assert result["contribution_count"] == 12
        assert result["task_count"] == 5
        assert result["focus_area_count"] == 2

    def test_list_by_user_with_no_events(self, mock_connection, mock_cursor):
        """Verify zero counts returned when no events exist."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_row = {
            "id": "bo1_empty",
            "user_id": "user_new",
            "problem_statement": "New problem",
            "problem_context": None,
            "status": "created",
            "phase": None,
            "total_cost": 0.0,
            "round_number": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "synthesis_text": None,
            "final_recommendation": None,
            "expert_count": 0,
            "contribution_count": 0,
            "task_count": 0,
            "focus_area_count": 0,
        }
        mock_cursor.fetchall.return_value = [mock_row]

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            results = repo.list_by_user("user_new")

        assert len(results) == 1
        assert results[0]["expert_count"] == 0
        assert results[0]["contribution_count"] == 0
        assert results[0]["task_count"] == 0
        assert results[0]["focus_area_count"] == 0

    def test_list_by_user_query_uses_filter_clause(self, mock_connection, mock_cursor):
        """Verify the executed query uses FILTER clause pattern."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_cursor.fetchall.return_value = []

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.list_by_user("user_test")

        # Verify execute was called
        mock_cursor.execute.assert_called_once()
        executed_query = mock_cursor.execute.call_args[0][0]

        # Verify FILTER clause is used (not subqueries)
        assert "FILTER (WHERE" in executed_query
        assert "LEFT JOIN session_events" in executed_query
        assert "LEFT JOIN session_tasks" in executed_query
        assert "GROUP BY" in executed_query

    def test_list_by_user_excludes_deleted_by_default(self, mock_connection, mock_cursor):
        """Verify deleted sessions excluded by default."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_cursor.fetchall.return_value = []

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.list_by_user("user_test", include_deleted=False)

        executed_query = mock_cursor.execute.call_args[0][0]
        assert "status != 'deleted'" in executed_query

    def test_list_by_user_status_filter(self, mock_connection, mock_cursor):
        """Verify status filter is applied correctly."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_cursor.fetchall.return_value = []

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.list_by_user("user_test", status_filter="completed")

        params = mock_cursor.execute.call_args[0][1]
        # user_id, status_filter, limit, offset
        assert params[0] == "user_test"
        assert "completed" in params


class TestSaveEventsBatch:
    """Test save_events_batch method for batch event persistence."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with context manager support."""
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

    def test_save_events_batch_inserts_multiple(self, mock_connection, mock_cursor):
        """Verify batch insert is called with multiple events."""
        from bo1.state.repositories.session_repository import SessionRepository

        events = [
            ("bo1_test1", "contribution", 1, {"content": "first"}),
            ("bo1_test1", "contribution", 2, {"content": "second"}),
            ("bo1_test1", "synthesis_complete", 3, {"text": "done"}),
        ]

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            count = repo.save_events_batch(events)

        assert count == 3
        mock_cursor.executemany.assert_called_once()
        # Verify the prepared data has 3 tuples
        prepared_data = mock_cursor.executemany.call_args[0][1]
        assert len(prepared_data) == 3

    def test_save_events_batch_empty_list(self, mock_connection, mock_cursor):
        """Verify empty list returns 0 without DB call."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            count = repo.save_events_batch([])

        assert count == 0
        mock_cursor.executemany.assert_not_called()

    def test_save_events_batch_uses_on_conflict(self, mock_connection, mock_cursor):
        """Verify the query uses ON CONFLICT DO NOTHING for duplicates."""
        from bo1.state.repositories.session_repository import SessionRepository

        events = [("bo1_test1", "test_event", 1, {"data": "test"})]

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_events_batch(events)

        executed_query = mock_cursor.executemany.call_args[0][0]
        assert "ON CONFLICT" in executed_query
        assert "DO NOTHING" in executed_query


class TestSessionModel:
    """Test Session Pydantic model validation and conversion."""

    def test_session_model_from_db_row(self):
        """Verify Session.from_db_row converts dict correctly."""
        row = {
            "id": "bo1_test123",
            "user_id": "user_abc",
            "problem_statement": "Test problem statement",
            "problem_context": {"key": "value"},
            "status": "running",
            "phase": "discussion",
            "total_cost": 0.15,
            "round_number": 3,
            "created_at": datetime(2025, 1, 1, 12, 0, 0),
            "updated_at": datetime(2025, 1, 1, 12, 30, 0),
            "synthesis_text": None,
            "final_recommendation": None,
        }

        session = Session.from_db_row(row)

        assert session.id == "bo1_test123"
        assert session.user_id == "user_abc"
        assert session.problem_statement == "Test problem statement"
        assert session.problem_context == {"key": "value"}
        assert session.status == SessionStatus.RUNNING
        assert session.phase == "discussion"
        assert session.total_cost == 0.15
        assert session.round_number == 3

    def test_session_model_validation_status_enum(self):
        """Verify status field accepts valid enum values."""
        for status in ["created", "running", "completed", "failed", "killed"]:
            row = {
                "id": "bo1_test",
                "user_id": "user",
                "problem_statement": "test",
                "status": status,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            session = Session.from_db_row(row)
            assert session.status == SessionStatus(status)

    def test_session_model_optional_fields(self):
        """Verify optional fields default to None."""
        row = {
            "id": "bo1_minimal",
            "user_id": "user",
            "problem_statement": "minimal",
            "status": "created",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        session = Session.from_db_row(row)

        assert session.problem_context is None
        assert session.phase is None
        assert session.total_cost is None
        assert session.round_number is None
        assert session.synthesis_text is None
        assert session.final_recommendation is None

    def test_session_model_dump(self):
        """Verify model_dump() returns dict for backward compat."""
        row = {
            "id": "bo1_dump",
            "user_id": "user",
            "problem_statement": "test",
            "status": "completed",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        session = Session.from_db_row(row)
        dumped = session.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["id"] == "bo1_dump"
        assert dumped["status"] == SessionStatus.COMPLETED


class TestGetSessionTyped:
    """Test get_session() returns typed Session model."""

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

    def test_get_session_returns_model(self):
        """Verify get_session returns Session instance."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_row = {
            "id": "bo1_typed",
            "user_id": "user",
            "problem_statement": "typed test",
            "problem_context": None,
            "status": "running",
            "phase": "discussion",
            "total_cost": 0.05,
            "round_number": 2,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "synthesis_text": None,
            "final_recommendation": None,
        }

        repo = SessionRepository()
        # Mock the internal get() method that returns dict
        with patch.object(repo, "get", return_value=mock_row):
            session = repo.get_session("bo1_typed")

        assert isinstance(session, Session)
        assert session.id == "bo1_typed"
        assert session.status == SessionStatus.RUNNING

    def test_get_session_returns_none_when_not_found(self):
        """Verify get_session returns None when session doesn't exist."""
        from bo1.state.repositories.session_repository import SessionRepository

        repo = SessionRepository()
        with patch.object(repo, "get", return_value=None):
            session = repo.get_session("bo1_nonexistent")

        assert session is None
