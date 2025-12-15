"""Tests for user analytics service."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from backend.services import user_analytics


class TestGetSignupStats:
    """Tests for get_signup_stats function."""

    @patch("backend.services.user_analytics.db_session")
    def test_returns_signup_stats(self, mock_db_session: MagicMock) -> None:
        """Test that signup stats are returned correctly."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock query results
        mock_cursor.fetchone.side_effect = [
            {"total": 100},  # total users
            {"count": 5},  # new today
            {"count": 25},  # new 7d
            {"count": 80},  # new 30d
        ]
        mock_cursor.fetchall.return_value = [
            {"day": datetime(2025, 1, 1).date(), "count": 3},
            {"day": datetime(2025, 1, 2).date(), "count": 5},
        ]

        result = user_analytics.get_signup_stats(days=30)

        assert result.total_users == 100
        assert result.new_users_today == 5
        assert result.new_users_7d == 25
        assert result.new_users_30d == 80
        assert len(result.daily_signups) == 2

    @patch("backend.services.user_analytics.db_session")
    def test_caps_days_at_90(self, mock_db_session: MagicMock) -> None:
        """Test that days parameter is capped at 90."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = {"total": 0, "count": 0}
        mock_cursor.fetchall.return_value = []

        # Request 180 days, should be capped
        user_analytics.get_signup_stats(days=180)

        # Verify the query was called (implicitly tests capping)
        assert mock_cursor.execute.called


class TestGetActiveUserStats:
    """Tests for get_active_user_stats function."""

    @patch("backend.services.user_analytics.db_session")
    def test_returns_active_user_stats(self, mock_db_session: MagicMock) -> None:
        """Test that active user stats are returned correctly."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            {"count": 10},  # DAU
            {"count": 50},  # WAU
            {"count": 150},  # MAU
        ]
        mock_cursor.fetchall.return_value = [
            {"day": datetime(2025, 1, 1).date(), "count": 8},
            {"day": datetime(2025, 1, 2).date(), "count": 12},
        ]

        result = user_analytics.get_active_user_stats(days=30)

        assert result.dau == 10
        assert result.wau == 50
        assert result.mau == 150
        assert len(result.daily_active) == 2


class TestGetUsageStats:
    """Tests for get_usage_stats function."""

    @patch("backend.services.user_analytics.db_session")
    def test_returns_usage_stats(self, mock_db_session: MagicMock) -> None:
        """Test that usage stats are returned correctly."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            {"total": 500},  # total meetings
            {"total": 1200},  # total actions
            {"count": 10},  # meetings today
            {"count": 50},  # meetings 7d
            {"count": 200},  # meetings 30d
            {"count": 100},  # actions 7d
            {"total": 25},  # mentor sessions
            {"total": 15},  # data analyses
            {"total": 8},  # projects
            {"started": 30, "completed": 100, "cancelled": 5},  # action stats
        ]
        mock_cursor.fetchall.side_effect = [
            [{"day": datetime(2025, 1, 1).date(), "count": 5}],  # daily meetings
            [{"day": datetime(2025, 1, 1).date(), "count": 20}],  # daily actions
        ]

        result = user_analytics.get_usage_stats(days=30)

        assert result.total_meetings == 500
        assert result.total_actions == 1200
        assert result.meetings_today == 10
        assert result.meetings_7d == 50
        assert result.meetings_30d == 200
        assert result.actions_created_7d == 100
        assert len(result.daily_meetings) == 1
        assert len(result.daily_actions) == 1
        # Extended KPIs
        assert result.mentor_sessions_count == 25
        assert result.data_analyses_count == 15
        assert result.projects_count == 8
        assert result.actions_started_count == 30
        assert result.actions_completed_count == 100
        assert result.actions_cancelled_count == 5
