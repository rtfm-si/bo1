"""Tests for session monitoring service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from backend.services.monitoring import (
    RunawaySessionResult,
    detect_runaway_sessions,
    get_session_kill_history,
    record_session_kill,
)


class TestRunawaySessionResult:
    """Tests for RunawaySessionResult dataclass."""

    def test_duration_reason_description(self) -> None:
        """Test reason description for duration exceeded."""
        result = RunawaySessionResult(
            session_id="test-123",
            user_id="user-1",
            reason="duration",
            duration_minutes=45.5,
            cost_usd=1.50,
            last_event_minutes_ago=2.0,
            started_at=datetime.now(UTC),
        )
        assert "Duration exceeded: 45.5 mins" in result.reason_description

    def test_cost_reason_description(self) -> None:
        """Test reason description for cost exceeded."""
        result = RunawaySessionResult(
            session_id="test-123",
            user_id="user-1",
            reason="cost",
            duration_minutes=15.0,
            cost_usd=8.75,
            last_event_minutes_ago=1.0,
            started_at=datetime.now(UTC),
        )
        assert "Cost exceeded: $8.75" in result.reason_description

    def test_stale_reason_description(self) -> None:
        """Test reason description for stale session."""
        result = RunawaySessionResult(
            session_id="test-123",
            user_id="user-1",
            reason="stale",
            duration_minutes=10.0,
            cost_usd=0.50,
            last_event_minutes_ago=7.5,
            started_at=datetime.now(UTC),
        )
        assert "No events for 7.5 mins" in result.reason_description


class TestDetectRunawaySessions:
    """Tests for detect_runaway_sessions function."""

    @patch("backend.services.monitoring.db_session")
    def test_detects_cost_exceeded(self, mock_db_session: MagicMock) -> None:
        """Test detection of cost-exceeded sessions."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "session-1",
                "user_id": "user-1",
                "total_cost": 10.0,  # Exceeds default $5
                "created_at": now - timedelta(minutes=10),
                "last_event_at": now - timedelta(minutes=1),
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = detect_runaway_sessions()

        assert len(results) == 1
        assert results[0].reason == "cost"
        assert results[0].session_id == "session-1"

    @patch("backend.services.monitoring.db_session")
    def test_detects_duration_exceeded(self, mock_db_session: MagicMock) -> None:
        """Test detection of duration-exceeded sessions."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "session-2",
                "user_id": "user-2",
                "total_cost": 1.0,  # Under threshold
                "created_at": now - timedelta(minutes=45),  # Exceeds 30 min default
                "last_event_at": now - timedelta(minutes=1),
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = detect_runaway_sessions()

        assert len(results) == 1
        assert results[0].reason == "duration"

    @patch("backend.services.monitoring.db_session")
    def test_detects_stale_session(self, mock_db_session: MagicMock) -> None:
        """Test detection of stale sessions (no recent events)."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "session-3",
                "user_id": "user-3",
                "total_cost": 0.5,  # Under threshold
                "created_at": now - timedelta(minutes=10),  # Under duration threshold
                "last_event_at": now - timedelta(minutes=10),  # Exceeds 5 min stale
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = detect_runaway_sessions()

        assert len(results) == 1
        assert results[0].reason == "stale"

    @patch("backend.services.monitoring.db_session")
    def test_no_runaways_when_all_healthy(self, mock_db_session: MagicMock) -> None:
        """Test no runaways detected for healthy sessions."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "healthy-1",
                "user_id": "user-1",
                "total_cost": 0.5,  # Under threshold
                "created_at": now - timedelta(minutes=5),  # Under duration threshold
                "last_event_at": now - timedelta(minutes=1),  # Recent event
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = detect_runaway_sessions()

        assert len(results) == 0

    @patch("backend.services.monitoring.db_session")
    def test_custom_thresholds(self, mock_db_session: MagicMock) -> None:
        """Test custom threshold parameters are respected."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "session-custom",
                "user_id": "user-1",
                "total_cost": 2.0,  # Would be under default, over custom
                "created_at": now - timedelta(minutes=5),
                "last_event_at": now - timedelta(minutes=1),
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = detect_runaway_sessions(max_cost_usd=1.5)

        assert len(results) == 1
        assert results[0].reason == "cost"

    @patch("backend.services.monitoring.db_session")
    def test_cost_priority_over_duration(self, mock_db_session: MagicMock) -> None:
        """Test cost reason takes priority over duration."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "multi-issue",
                "user_id": "user-1",
                "total_cost": 10.0,  # Exceeds cost
                "created_at": now - timedelta(minutes=60),  # Also exceeds duration
                "last_event_at": now - timedelta(minutes=10),  # Also stale
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = detect_runaway_sessions()

        assert len(results) == 1
        # Cost is checked first, so cost reason should be returned
        assert results[0].reason == "cost"


class TestRecordSessionKill:
    """Tests for record_session_kill function."""

    @patch("backend.services.monitoring.db_session")
    def test_record_kill_success(self, mock_db_session: MagicMock) -> None:
        """Test successful kill audit record creation."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 42}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = record_session_kill(
            session_id="session-123",
            killed_by="admin-user",
            reason="cost_exceeded",
            cost_at_kill=8.50,
        )

        assert result == 42
        mock_cursor.execute.assert_called_once()


class TestGetSessionKillHistory:
    """Tests for get_session_kill_history function."""

    @patch("backend.services.monitoring.db_session")
    def test_get_history_all(self, mock_db_session: MagicMock) -> None:
        """Test getting all kill history."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "session_id": "session-1",
                "killed_by": "admin",
                "reason": "cost_exceeded",
                "cost_at_kill": 5.50,
                "created_at": now,
            },
            {
                "id": 2,
                "session_id": "session-2",
                "killed_by": "system",
                "reason": "duration_exceeded",
                "cost_at_kill": 1.20,
                "created_at": now - timedelta(hours=1),
            },
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = get_session_kill_history(limit=10)

        assert len(results) == 2
        assert results[0]["killed_by"] == "admin"

    @patch("backend.services.monitoring.db_session")
    def test_get_history_by_session(self, mock_db_session: MagicMock) -> None:
        """Test getting kill history for specific session."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "session_id": "session-1",
                "killed_by": "admin",
                "reason": "cost_exceeded",
                "cost_at_kill": 5.50,
                "created_at": datetime.now(UTC),
            },
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        results = get_session_kill_history(session_id="session-1")

        assert len(results) == 1
        assert results[0]["session_id"] == "session-1"
