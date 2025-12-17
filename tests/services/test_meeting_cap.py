"""Tests for meeting cap service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.services.meeting_cap import (
    MeetingCapExceededError,
    MeetingCapStatus,
    check_meeting_cap,
    get_recent_meeting_count,
    require_meeting_cap,
)
from bo1.constants import BetaMeetingCap


class TestBetaMeetingCapConfig:
    """Tests for BetaMeetingCap configuration."""

    def test_default_values(self):
        """Default cap values should be set."""
        assert BetaMeetingCap.MAX_MEETINGS == 4
        assert BetaMeetingCap.WINDOW_HOURS == 24

    @patch.dict("os.environ", {"BETA_MEETING_CAP_ENABLED": "true"})
    def test_is_enabled_true(self):
        """Cap should be enabled when env var is true."""
        assert BetaMeetingCap.is_enabled() is True

    @patch.dict("os.environ", {"BETA_MEETING_CAP_ENABLED": "false"})
    def test_is_enabled_false(self):
        """Cap should be disabled when env var is false."""
        assert BetaMeetingCap.is_enabled() is False

    @patch.dict("os.environ", {}, clear=True)
    def test_is_enabled_default(self):
        """Cap should be enabled by default (no env var)."""
        # Default is "true"
        assert BetaMeetingCap.is_enabled() is True


class TestMeetingCapStatus:
    """Tests for MeetingCapStatus dataclass."""

    def test_to_dict(self):
        """to_dict should serialize properly."""
        reset_time = datetime(2025, 12, 17, 12, 0, 0, tzinfo=UTC)
        status = MeetingCapStatus(
            allowed=True,
            remaining=2,
            limit=4,
            reset_time=reset_time,
            exceeded=False,
            recent_count=2,
        )
        result = status.to_dict()

        assert result["allowed"] is True
        assert result["remaining"] == 2
        assert result["limit"] == 4
        assert result["reset_time"] == "2025-12-17T12:00:00+00:00"
        assert result["exceeded"] is False
        assert result["recent_count"] == 2

    def test_to_dict_null_reset_time(self):
        """to_dict should handle null reset_time."""
        status = MeetingCapStatus(
            allowed=True,
            remaining=4,
            limit=4,
            reset_time=None,
            exceeded=False,
            recent_count=0,
        )
        result = status.to_dict()
        assert result["reset_time"] is None


class TestGetRecentMeetingCount:
    """Tests for get_recent_meeting_count function."""

    @patch("backend.services.meeting_cap.db_session")
    def test_counts_only_started_sessions(self, mock_db_session):
        """Should count sessions that have started (not 'created', 'failed', 'deleted')."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (3,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock()
        mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db_session.return_value.__exit__ = MagicMock()

        count = get_recent_meeting_count("user-123", hours=24)

        assert count == 3
        # Verify the SQL excludes 'created', 'failed', 'deleted'
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "status NOT IN ('created', 'failed', 'deleted')" in sql

    @patch("backend.services.meeting_cap.db_session")
    def test_returns_zero_on_db_error(self, mock_db_session):
        """Should fail open (return 0) on database errors."""
        mock_db_session.return_value.__enter__ = MagicMock(side_effect=Exception("DB error"))
        mock_db_session.return_value.__exit__ = MagicMock()

        count = get_recent_meeting_count("user-123")
        assert count == 0


class TestCheckMeetingCap:
    """Tests for check_meeting_cap function."""

    @patch("backend.services.meeting_cap.BetaMeetingCap.is_enabled")
    def test_disabled_cap_always_allows(self, mock_is_enabled):
        """When cap is disabled, should always allow."""
        mock_is_enabled.return_value = False

        status = check_meeting_cap("user-123")

        assert status.allowed is True
        assert status.remaining == -1
        assert status.limit == -1
        assert status.exceeded is False

    @patch("backend.services.meeting_cap.BetaMeetingCap.is_enabled")
    @patch("backend.services.meeting_cap.get_recent_meeting_count")
    def test_under_cap_allows(self, mock_count, mock_is_enabled):
        """When under cap, should allow and show remaining."""
        mock_is_enabled.return_value = True
        mock_count.return_value = 2

        status = check_meeting_cap("user-123")

        assert status.allowed is True
        assert status.remaining == 2
        assert status.limit == 4
        assert status.exceeded is False
        assert status.recent_count == 2

    @patch("backend.services.meeting_cap.BetaMeetingCap.is_enabled")
    @patch("backend.services.meeting_cap.get_recent_meeting_count")
    @patch("backend.services.meeting_cap.get_oldest_meeting_time")
    def test_at_cap_denies(self, mock_oldest, mock_count, mock_is_enabled):
        """When at or over cap, should deny and show reset time."""
        mock_is_enabled.return_value = True
        mock_count.return_value = 4
        oldest_time = datetime.now(UTC) - timedelta(hours=20)
        mock_oldest.return_value = oldest_time

        status = check_meeting_cap("user-123")

        assert status.allowed is False
        assert status.remaining == 0
        assert status.exceeded is True
        assert status.reset_time is not None
        # Reset time should be oldest_time + window_hours
        expected_reset = oldest_time + timedelta(hours=24)
        assert status.reset_time == expected_reset

    @patch("backend.services.meeting_cap.BetaMeetingCap.is_enabled")
    @patch("backend.services.meeting_cap.get_recent_meeting_count")
    def test_over_cap_denies(self, mock_count, mock_is_enabled):
        """When over cap, should deny."""
        mock_is_enabled.return_value = True
        mock_count.return_value = 5

        status = check_meeting_cap("user-123")

        assert status.allowed is False
        assert status.remaining == 0
        assert status.exceeded is True


class TestRequireMeetingCap:
    """Tests for require_meeting_cap function."""

    @patch("backend.services.meeting_cap.check_meeting_cap")
    def test_returns_status_when_allowed(self, mock_check):
        """Should return status when under cap."""
        mock_check.return_value = MeetingCapStatus(
            allowed=True,
            remaining=2,
            limit=4,
            reset_time=None,
            exceeded=False,
            recent_count=2,
        )

        status = require_meeting_cap("user-123")
        assert status.allowed is True

    @patch("backend.services.meeting_cap.check_meeting_cap")
    def test_raises_when_exceeded(self, mock_check):
        """Should raise MeetingCapExceededError when cap exceeded."""
        reset_time = datetime.now(UTC) + timedelta(hours=4)
        mock_check.return_value = MeetingCapStatus(
            allowed=False,
            remaining=0,
            limit=4,
            reset_time=reset_time,
            exceeded=True,
            recent_count=4,
        )

        with pytest.raises(MeetingCapExceededError) as exc_info:
            require_meeting_cap("user-123")

        assert exc_info.value.status.exceeded is True
        assert "Meeting limit reached" in str(exc_info.value)


class TestMeetingCapExceededError:
    """Tests for MeetingCapExceededError exception."""

    def test_message_with_reset_hours(self):
        """Error message should include hours/minutes when > 1 hour."""
        reset_time = datetime.now(UTC) + timedelta(hours=3, minutes=30)
        status = MeetingCapStatus(
            allowed=False,
            remaining=0,
            limit=4,
            reset_time=reset_time,
            exceeded=True,
            recent_count=4,
        )

        error = MeetingCapExceededError(status)
        message = str(error)

        assert "Meeting limit reached" in message
        assert "3h" in message

    def test_message_with_reset_minutes(self):
        """Error message should show minutes only when < 1 hour."""
        reset_time = datetime.now(UTC) + timedelta(minutes=45)
        status = MeetingCapStatus(
            allowed=False,
            remaining=0,
            limit=4,
            reset_time=reset_time,
            exceeded=True,
            recent_count=4,
        )

        error = MeetingCapExceededError(status)
        message = str(error)

        assert "Meeting limit reached" in message
        # Allow for timing variance (44-46 minutes)
        assert " minutes" in message
        assert "4" in message  # Should contain 44, 45, or 46

    def test_message_without_reset_time(self):
        """Error message should work without reset time."""
        status = MeetingCapStatus(
            allowed=False,
            remaining=0,
            limit=4,
            reset_time=None,
            exceeded=True,
            recent_count=4,
        )

        error = MeetingCapExceededError(status)
        message = str(error)

        assert "Meeting limit reached" in message
        assert "Try again" not in message
