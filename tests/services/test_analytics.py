"""Tests for cost analytics service."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from backend.services.analytics import (
    CostSummary,
    DailyCost,
    UserCost,
    get_cost_summary,
    get_daily_costs,
    get_full_report,
    get_session_cost,
    get_user_costs,
)


class TestCostSummary:
    """Tests for get_cost_summary function."""

    @patch("backend.services.analytics.db_session")
    def test_returns_all_time_periods(self, mock_db_session: MagicMock) -> None:
        """Test summary returns today, week, month, all-time totals."""
        mock_cursor = MagicMock()
        # Mock 4 sequential fetchone calls for each time period
        mock_cursor.fetchone.side_effect = [
            {"total": 100.0, "count": 50},  # all_time
            {"total": 10.0, "count": 5},  # today
            {"total": 30.0, "count": 15},  # this_week
            {"total": 60.0, "count": 30},  # this_month
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_cost_summary()

        assert result.all_time == 100.0
        assert result.today == 10.0
        assert result.this_week == 30.0
        assert result.this_month == 60.0
        assert result.session_count_total == 50
        assert result.session_count_today == 5

    @patch("backend.services.analytics.db_session")
    def test_handles_empty_results(self, mock_db_session: MagicMock) -> None:
        """Test summary handles no sessions gracefully."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"total": 0, "count": 0}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_cost_summary()

        assert result.all_time == 0.0
        assert result.session_count_total == 0


class TestUserCosts:
    """Tests for get_user_costs function."""

    @patch("backend.services.analytics.db_session")
    def test_returns_paginated_users(self, mock_db_session: MagicMock) -> None:
        """Test user costs returns paginated list."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"total": 3}  # Total count
        mock_cursor.fetchall.return_value = [
            {"user_id": "u1", "email": "a@test.com", "total_cost": 50.0, "session_count": 10},
            {"user_id": "u2", "email": "b@test.com", "total_cost": 30.0, "session_count": 5},
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        users, total = get_user_costs(limit=10, offset=0)

        assert total == 3
        assert len(users) == 2
        assert users[0].user_id == "u1"
        assert users[0].total_cost == 50.0

    @patch("backend.services.analytics.db_session")
    def test_date_filtering(self, mock_db_session: MagicMock) -> None:
        """Test date range filtering is applied."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"total": 1}
        mock_cursor.fetchall.return_value = [
            {"user_id": "u1", "email": "a@test.com", "total_cost": 25.0, "session_count": 3},
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        start = date(2025, 1, 1)
        end = date(2025, 1, 31)
        users, total = get_user_costs(start_date=start, end_date=end)

        assert len(users) == 1
        # Verify execute was called with date parameters
        calls = mock_cursor.execute.call_args_list
        assert len(calls) == 2  # count query + data query


class TestDailyCosts:
    """Tests for get_daily_costs function."""

    @patch("backend.services.analytics.db_session")
    def test_returns_daily_breakdown(self, mock_db_session: MagicMock) -> None:
        """Test daily costs returns day-by-day breakdown."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"day": date(2025, 1, 1), "total_cost": 10.0, "session_count": 5},
            {"day": date(2025, 1, 2), "total_cost": 15.0, "session_count": 7},
            {"day": date(2025, 1, 3), "total_cost": 8.0, "session_count": 3},
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_daily_costs(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 3),
        )

        assert len(result) == 3
        assert result[0].date == date(2025, 1, 1)
        assert result[0].total_cost == 10.0
        assert result[2].session_count == 3

    @patch("backend.services.analytics.db_session")
    def test_defaults_to_last_30_days(self, mock_db_session: MagicMock) -> None:
        """Test daily costs defaults to 30 days when no dates provided."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_daily_costs()

        assert result == []
        # Check that query was called (defaults applied internally)
        mock_cursor.execute.assert_called_once()


class TestSessionCost:
    """Tests for get_session_cost function."""

    @patch("backend.services.analytics.db_session")
    def test_returns_session_breakdown(self, mock_db_session: MagicMock) -> None:
        """Test session cost returns cost details."""
        now = datetime.now(UTC)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": "bo1_abc123",
            "total_cost": 2.50,
            "status": "completed",
            "created_at": now,
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_session_cost("bo1_abc123")

        assert result is not None
        assert result["session_id"] == "bo1_abc123"
        assert result["total_cost"] == 2.50
        assert result["status"] == "completed"

    @patch("backend.services.analytics.db_session")
    def test_returns_none_for_missing_session(self, mock_db_session: MagicMock) -> None:
        """Test returns None when session not found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_session_cost("nonexistent")

        assert result is None


class TestFullReport:
    """Tests for get_full_report function."""

    @patch("backend.services.analytics.get_daily_costs")
    @patch("backend.services.analytics.get_user_costs")
    @patch("backend.services.analytics.get_cost_summary")
    def test_combines_all_analytics(
        self,
        mock_summary: MagicMock,
        mock_users: MagicMock,
        mock_daily: MagicMock,
    ) -> None:
        """Test full report combines summary, users, and daily."""
        mock_summary.return_value = CostSummary(
            today=10.0,
            this_week=30.0,
            this_month=60.0,
            all_time=100.0,
            session_count_today=5,
            session_count_week=15,
            session_count_month=30,
            session_count_total=50,
        )
        mock_users.return_value = (
            [
                UserCost(user_id="u1", email="a@test.com", total_cost=50.0, session_count=10),
            ],
            1,
        )
        mock_daily.return_value = [
            DailyCost(date=date(2025, 1, 1), total_cost=10.0, session_count=5),
        ]

        report = get_full_report(top_users=5)

        assert report.summary.all_time == 100.0
        assert len(report.by_user) == 1
        assert len(report.by_day) == 1
        assert report.by_model == []  # Not implemented yet
