"""Tests for goal_tracker service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch


class TestRecordGoalChange:
    """Tests for record_goal_change function."""

    def test_records_new_goal(self):
        """Should record a new goal in history."""
        from backend.services.goal_tracker import record_goal_change

        mock_result = {"id": 42}
        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=mock_result,
        ) as mock_query:
            result = record_goal_change(
                user_id="user-123",
                new_goal="Reach $1M ARR",
                previous_goal=None,
            )

            assert result == 42
            mock_query.assert_called_once()
            args = mock_query.call_args
            assert "INSERT INTO goal_history" in args[0][0]
            assert args[0][1][0] == "user-123"
            assert args[0][1][1] == "Reach $1M ARR"
            assert args[0][1][2] is None

    def test_records_goal_change_with_previous(self):
        """Should record goal change with previous goal reference."""
        from backend.services.goal_tracker import record_goal_change

        mock_result = {"id": 43}
        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=mock_result,
        ) as mock_query:
            result = record_goal_change(
                user_id="user-123",
                new_goal="Reach $2M ARR",
                previous_goal="Reach $1M ARR",
            )

            assert result == 43
            args = mock_query.call_args
            assert args[0][1][2] == "Reach $1M ARR"

    def test_skips_recording_when_unchanged(self):
        """Should return None when goal hasn't changed."""
        from backend.services.goal_tracker import record_goal_change

        with patch(
            "backend.services.goal_tracker.execute_query",
        ) as mock_query:
            result = record_goal_change(
                user_id="user-123",
                new_goal="Same goal",
                previous_goal="Same goal",
            )

            assert result is None
            mock_query.assert_not_called()

    def test_returns_none_when_insert_fails(self):
        """Should return None when insert returns no result."""
        from backend.services.goal_tracker import record_goal_change

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=None,
        ):
            result = record_goal_change(
                user_id="user-123",
                new_goal="New goal",
                previous_goal="Old goal",
            )

            assert result is None


class TestGetGoalHistory:
    """Tests for get_goal_history function."""

    def test_returns_history_list(self):
        """Should return list of goal history entries."""
        from backend.services.goal_tracker import get_goal_history

        mock_rows = [
            {
                "id": 1,
                "goal_text": "Goal A",
                "previous_goal": None,
                "changed_at": datetime(2025, 1, 15, tzinfo=UTC),
            },
            {
                "id": 2,
                "goal_text": "Goal B",
                "previous_goal": "Goal A",
                "changed_at": datetime(2025, 1, 10, tzinfo=UTC),
            },
        ]
        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=mock_rows,
        ):
            result = get_goal_history("user-123", limit=10)

            assert len(result) == 2
            assert result[0]["goal_text"] == "Goal A"
            assert result[1]["previous_goal"] == "Goal A"

    def test_returns_empty_list_when_no_history(self):
        """Should return empty list when no history exists."""
        from backend.services.goal_tracker import get_goal_history

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=None,
        ):
            result = get_goal_history("user-123")

            assert result == []

    def test_respects_limit_parameter(self):
        """Should pass limit to query."""
        from backend.services.goal_tracker import get_goal_history

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=[],
        ) as mock_query:
            get_goal_history("user-123", limit=5)

            args = mock_query.call_args
            assert args[0][1][1] == 5


class TestGetDaysSinceLastChange:
    """Tests for get_days_since_last_change function."""

    def test_returns_days_since_change(self):
        """Should calculate days since last change."""
        from backend.services.goal_tracker import get_days_since_last_change

        # Mock a change from 10 days ago
        ten_days_ago = datetime.now(UTC) - timedelta(days=10)
        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value={"changed_at": ten_days_ago},
        ):
            result = get_days_since_last_change("user-123")

            assert result == 10

    def test_returns_none_when_no_history(self):
        """Should return None when no history exists."""
        from backend.services.goal_tracker import get_days_since_last_change

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value=None,
        ):
            result = get_days_since_last_change("user-123")

            assert result is None

    def test_returns_none_when_changed_at_is_none(self):
        """Should return None when changed_at is null."""
        from backend.services.goal_tracker import get_days_since_last_change

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value={"changed_at": None},
        ):
            result = get_days_since_last_change("user-123")

            assert result is None

    def test_handles_timezone_naive_datetime(self):
        """Should handle timezone-naive datetimes from database."""
        from backend.services.goal_tracker import get_days_since_last_change

        # Simulate a naive datetime (no tzinfo)
        five_days_ago = datetime.now() - timedelta(days=5)
        five_days_ago = five_days_ago.replace(tzinfo=None)

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value={"changed_at": five_days_ago},
        ):
            result = get_days_since_last_change("user-123")

            assert result == 5

    def test_returns_zero_for_today(self):
        """Should return 0 if changed today."""
        from backend.services.goal_tracker import get_days_since_last_change

        just_now = datetime.now(UTC) - timedelta(hours=1)
        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value={"changed_at": just_now},
        ):
            result = get_days_since_last_change("user-123")

            assert result == 0
