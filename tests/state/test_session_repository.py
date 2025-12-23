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

    def test_list_by_user_query_uses_denormalized_counts(self, mock_connection, mock_cursor):
        """Verify the executed query reads denormalized counts from sessions."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_cursor.fetchall.return_value = []

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.list_by_user("user_test")

        # Verify execute was called
        mock_cursor.execute.assert_called_once()
        executed_query = mock_cursor.execute.call_args[0][0]

        # Verify all denormalized columns are selected directly (no JOINs)
        assert "s.expert_count" in executed_query
        assert "s.contribution_count" in executed_query
        assert "s.focus_area_count" in executed_query
        assert "s.task_count" in executed_query
        # No JOIN needed - all counts are denormalized
        assert "LEFT JOIN" not in executed_query
        # No aggregation needed for denormalized counts
        assert "GROUP BY" not in executed_query

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


class TestSaveEventCountIncrements:
    """Test save_event and save_events_batch increment denormalized counts."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with context manager support."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        # fetchone returns a result dict (event was inserted)
        cursor.fetchone.return_value = {
            "id": 1,
            "session_id": "bo1_test",
            "event_type": "contribution",
            "sequence": 1,
            "created_at": datetime.now(),
        }
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_save_event_increments_expert_count(self, mock_connection, mock_cursor):
        """Verify persona_selected event increments expert_count."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_event("bo1_test", "persona_selected", 1, {"persona": "expert"})

        # Check that UPDATE was called with expert_count increment
        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "expert_count = expert_count + 1" in str(c)]
        assert len(update_call) == 1

    def test_save_event_increments_contribution_count(self, mock_connection, mock_cursor):
        """Verify contribution event increments contribution_count."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_event("bo1_test", "contribution", 1, {"content": "test"})

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "contribution_count = contribution_count + 1" in str(c)]
        assert len(update_call) == 1

    def test_save_event_increments_focus_area_count(self, mock_connection, mock_cursor):
        """Verify subproblem_started event increments focus_area_count."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_event("bo1_test", "subproblem_started", 1, {"subproblem": "test"})

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "focus_area_count = focus_area_count + 1" in str(c)]
        assert len(update_call) == 1

    def test_save_event_no_increment_for_other_types(self, mock_connection, mock_cursor):
        """Verify non-trackable event types don't trigger count increment."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_event("bo1_test", "synthesis_complete", 1, {"text": "done"})

        # Only INSERT should be called, no UPDATE for counts
        calls = mock_cursor.execute.call_args_list
        # Should have exactly 1 call (the INSERT)
        assert len(calls) == 1
        assert "INSERT INTO session_events" in str(calls[0])


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

    def test_save_events_batch_increments_counts(self, mock_connection, mock_cursor):
        """Verify batch insert increments denormalized counts."""
        from bo1.state.repositories.session_repository import SessionRepository

        events = [
            ("bo1_test1", "persona_selected", 1, {"persona": "a"}),
            ("bo1_test1", "persona_selected", 2, {"persona": "b"}),
            ("bo1_test1", "contribution", 3, {"content": "first"}),
            ("bo1_test1", "subproblem_started", 4, {"sp": "test"}),
        ]

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_events_batch(events)

        # Check UPDATE was called with batched increments
        calls = mock_cursor.execute.call_args_list
        # Should have UPDATE call with all three count columns
        update_calls = [c for c in calls if "UPDATE sessions SET" in str(c)]
        assert len(update_calls) == 1
        update_query = str(update_calls[0])
        assert "expert_count = expert_count +" in update_query
        assert "contribution_count = contribution_count +" in update_query
        assert "focus_area_count = focus_area_count +" in update_query

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
        # phase, total_cost, round_number have defaults matching DB server_default
        assert session.phase == "problem_decomposition"
        assert session.total_cost == 0.0
        assert session.round_number == 0
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


class TestSaveEventWithCachedUserId:
    """Test save_event user_id caching optimization."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with context manager support."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.fetchone.return_value = {
            "id": 1,
            "session_id": "bo1_test",
            "event_type": "contribution",
            "sequence": 1,
            "created_at": datetime.now(),
        }
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_save_event_with_user_id_avoids_subquery(self, mock_connection, mock_cursor):
        """Verify providing user_id avoids SELECT subquery."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_event("bo1_test", "contribution", 1, {"content": "test"}, user_id="user_123")

        # Check the INSERT query doesn't have subquery
        calls = mock_cursor.execute.call_args_list
        insert_call = [c for c in calls if "INSERT INTO session_events" in str(c)]
        assert len(insert_call) >= 1
        # When user_id is provided, should NOT have SELECT subquery
        insert_query = str(insert_call[0])
        assert "SELECT user_id FROM sessions" not in insert_query

    def test_save_event_without_user_id_uses_subquery(self, mock_connection, mock_cursor):
        """Verify missing user_id falls back to SELECT subquery."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_event("bo1_test", "contribution", 1, {"content": "test"})

        calls = mock_cursor.execute.call_args_list
        insert_call = [c for c in calls if "INSERT INTO session_events" in str(c)]
        assert len(insert_call) >= 1
        # When user_id is NOT provided, should have SELECT subquery
        insert_query = str(insert_call[0])
        assert "SELECT user_id FROM sessions" in insert_query


class TestSaveEventsBatchWithCachedUserIds:
    """Test save_events_batch user_id caching optimization."""

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

    def test_save_events_batch_with_user_ids_avoids_subquery(self, mock_connection, mock_cursor):
        """Verify providing user_ids dict avoids SELECT subqueries."""
        from bo1.state.repositories.session_repository import SessionRepository

        events = [
            ("bo1_test1", "contribution", 1, {"content": "first"}),
            ("bo1_test1", "contribution", 2, {"content": "second"}),
        ]
        user_ids = {"bo1_test1": "user_123"}

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            count = repo.save_events_batch(events, user_ids=user_ids)

        assert count == 2
        # Check executemany calls - should use direct user_id
        calls = mock_cursor.executemany.call_args_list
        assert len(calls) >= 1
        # First query should NOT have subquery (cached events)
        query = calls[0][0][0]
        assert "SELECT user_id FROM sessions" not in query

    def test_save_events_batch_mixed_cached_uncached(self, mock_connection, mock_cursor):
        """Verify batch handles mix of cached and uncached user_ids."""
        from bo1.state.repositories.session_repository import SessionRepository

        events = [
            ("bo1_cached", "contribution", 1, {"content": "cached"}),
            ("bo1_uncached", "contribution", 2, {"content": "uncached"}),
        ]
        user_ids = {"bo1_cached": "user_123"}  # Only one session cached

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            count = repo.save_events_batch(events, user_ids=user_ids)

        assert count == 2
        # Should have 2 executemany calls - one for cached, one for uncached
        calls = mock_cursor.executemany.call_args_list
        assert len(calls) == 2

    def test_save_events_batch_no_user_ids_uses_subquery(self, mock_connection, mock_cursor):
        """Verify missing user_ids falls back to SELECT subqueries."""
        from bo1.state.repositories.session_repository import SessionRepository

        events = [
            ("bo1_test1", "contribution", 1, {"content": "first"}),
        ]

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_events_batch(events)  # No user_ids provided

        calls = mock_cursor.executemany.call_args_list
        assert len(calls) >= 1
        # Query should have SELECT subquery
        query = calls[0][0][0]
        assert "SELECT user_id FROM sessions" in query


class TestPartitionPruning:
    """Test partition pruning for session_events queries.

    Validates that queries on partitioned tables include created_at
    filters to enable partition pruning and avoid full table scans.
    """

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

    def test_get_events_includes_partition_filter(self, mock_connection, mock_cursor):
        """Verify get_events() includes created_at filter for partition pruning."""
        from bo1.state.repositories.session_repository import SessionRepository

        # Patch base repository's db_session since _execute_query uses that import
        with patch("bo1.state.repositories.base.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.get_events("bo1_test123")

        # Check the SELECT query includes created_at filter
        calls = mock_cursor.execute.call_args_list
        select_call = [c for c in calls if "SELECT" in str(c) and "session_events" in str(c)]
        assert len(select_call) >= 1
        query = str(select_call[0])
        # Must include partition key filter for efficient pruning
        assert "created_at >=" in query, (
            "get_events() query must include created_at filter for partition pruning"
        )


class TestSaveMetadata:
    """Test save_metadata() method for Redis fallback persistence."""

    @pytest.fixture
    def mock_cursor(self):
        """Create a mock cursor with context manager support."""
        cursor = MagicMock()
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        cursor.rowcount = 1  # Simulate successful update
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Create a mock connection."""
        conn = MagicMock()
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        conn.cursor.return_value = mock_cursor
        return conn

    def test_save_metadata_updates_phase(self, mock_connection, mock_cursor):
        """Verify phase is persisted to sessions table."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            result = repo.save_metadata("bo1_test", {"phase": "exploration"})

        assert result is True
        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "UPDATE sessions" in str(c)]
        assert len(update_call) == 1
        query = str(update_call[0])
        assert "phase = %s" in query

    def test_save_metadata_updates_round_number(self, mock_connection, mock_cursor):
        """Verify round_number is persisted."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_metadata("bo1_test", {"round_number": 3})

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "UPDATE sessions" in str(c)]
        query = str(update_call[0])
        assert "round_number = %s" in query

    def test_save_metadata_updates_denormalized_counts(self, mock_connection, mock_cursor):
        """Verify expert_count, contribution_count, focus_area_count are persisted."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_metadata(
                "bo1_test",
                {"expert_count": 5, "contribution_count": 12, "focus_area_count": 3},
            )

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "UPDATE sessions" in str(c)]
        query = str(update_call[0])
        assert "expert_count = %s" in query
        assert "contribution_count = %s" in query
        assert "focus_area_count = %s" in query

    def test_save_metadata_stores_sub_problem_index_in_context(self, mock_connection, mock_cursor):
        """Verify sub_problem_index is stored in problem_context JSONB."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_metadata("bo1_test", {"sub_problem_index": 2})

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "UPDATE sessions" in str(c)]
        query = str(update_call[0])
        assert "problem_context" in query
        assert "::jsonb" in query

    def test_save_metadata_returns_false_when_session_not_found(self, mock_connection, mock_cursor):
        """Verify returns False when session doesn't exist."""
        from bo1.state.repositories.session_repository import SessionRepository

        mock_cursor.rowcount = 0  # No rows updated

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            result = repo.save_metadata("bo1_nonexistent", {"phase": "test"})

        assert result is False

    def test_save_metadata_with_empty_dict_returns_true(self, mock_connection, mock_cursor):
        """Verify empty metadata dict is handled gracefully."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            result = repo.save_metadata("bo1_test", {})

        # Returns True but no UPDATE is executed (only updated_at)
        assert result is True

    def test_save_metadata_uses_current_node_as_phase_fallback(self, mock_connection, mock_cursor):
        """Verify current_node is used as phase when phase not provided."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_metadata("bo1_test", {"current_node": "synthesis_node"})

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "UPDATE sessions" in str(c)]
        query = str(update_call[0])
        assert "phase = %s" in query

    def test_save_metadata_prefers_phase_over_current_node(self, mock_connection, mock_cursor):
        """Verify phase is preferred when both phase and current_node provided."""
        from bo1.state.repositories.session_repository import SessionRepository

        with patch("bo1.state.repositories.session_repository.db_session") as mock_db:
            mock_db.return_value = mock_connection

            repo = SessionRepository()
            repo.save_metadata(
                "bo1_test",
                {"phase": "exploration", "current_node": "synthesis_node"},
            )

        calls = mock_cursor.execute.call_args_list
        update_call = [c for c in calls if "UPDATE sessions" in str(c)]
        # Should only have one phase = %s, not two
        params = update_call[0][0][1]  # Get params tuple
        assert "exploration" in params


class TestExtractSessionMetadata:
    """Test extract_session_metadata() helper function."""

    def test_extract_metadata_from_full_state(self):
        """Verify all metadata fields are extracted from state."""
        from bo1.state.repositories.session_repository import extract_session_metadata

        state = {
            "current_phase": "exploration",
            "current_node": "rounds_node",
            "round_number": 2,
            "sub_problem_index": 1,
            "personas": [{"code": "CFO"}, {"code": "CTO"}, {"code": "CEO"}],
            "contributions": [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}],
            "sub_problems": [{"id": 1}, {"id": 2}],
        }

        metadata = extract_session_metadata(state)

        assert metadata["phase"] == "exploration"
        assert metadata["current_node"] == "rounds_node"
        assert metadata["round_number"] == 2
        assert metadata["sub_problem_index"] == 1
        assert metadata["expert_count"] == 3
        assert metadata["contribution_count"] == 5
        assert metadata["focus_area_count"] == 2

    def test_extract_metadata_uses_phase_fallback(self):
        """Verify phase is extracted from 'phase' key if current_phase missing."""
        from bo1.state.repositories.session_repository import extract_session_metadata

        state = {"phase": "synthesis", "round_number": 3}

        metadata = extract_session_metadata(state)

        assert metadata["phase"] == "synthesis"
        assert metadata["round_number"] == 3

    def test_extract_metadata_empty_state(self):
        """Verify empty state returns empty metadata dict."""
        from bo1.state.repositories.session_repository import extract_session_metadata

        metadata = extract_session_metadata({})

        assert metadata == {}

    def test_extract_metadata_partial_state(self):
        """Verify partial state only extracts available fields."""
        from bo1.state.repositories.session_repository import extract_session_metadata

        state = {"round_number": 1, "personas": [{"code": "CFO"}]}

        metadata = extract_session_metadata(state)

        assert metadata == {"round_number": 1, "expert_count": 1}
        assert "phase" not in metadata
        assert "contribution_count" not in metadata

    def test_extract_metadata_handles_none_values(self):
        """Verify None values are skipped."""
        from bo1.state.repositories.session_repository import extract_session_metadata

        state = {
            "current_phase": None,
            "round_number": None,
            "personas": [],
        }

        metadata = extract_session_metadata(state)

        assert "phase" not in metadata
        assert "round_number" not in metadata
        assert "expert_count" not in metadata

    def test_extract_metadata_current_phase_preferred_over_phase(self):
        """Verify current_phase takes precedence over phase."""
        from bo1.state.repositories.session_repository import extract_session_metadata

        state = {"current_phase": "exploration", "phase": "synthesis"}

        metadata = extract_session_metadata(state)

        assert metadata["phase"] == "exploration"
