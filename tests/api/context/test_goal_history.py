"""Tests for goal history API endpoints.

These tests verify the endpoint logic by mocking dependencies,
without requiring full API client setup.
"""

from datetime import UTC, datetime
from unittest.mock import patch


class TestGetGoalHistoryEndpointLogic:
    """Tests for goal history endpoint logic."""

    def test_formats_history_entries(self):
        """Should format history entries correctly."""
        from backend.api.context.models import GoalHistoryEntry, GoalHistoryResponse

        # Create entries using the model
        entries = [
            GoalHistoryEntry(
                goal_text="Reach $1M ARR",
                changed_at=datetime(2025, 1, 15, tzinfo=UTC),
                previous_goal=None,
            ),
            GoalHistoryEntry(
                goal_text="Expand to Europe",
                changed_at=datetime(2025, 1, 10, tzinfo=UTC),
                previous_goal="Reach $1M ARR",
            ),
        ]

        response = GoalHistoryResponse(entries=entries, count=len(entries))

        assert response.count == 2
        assert response.entries[0].goal_text == "Reach $1M ARR"
        assert response.entries[0].previous_goal is None
        assert response.entries[1].previous_goal == "Reach $1M ARR"

    def test_empty_entries(self):
        """Should handle empty entries list."""
        from backend.api.context.models import GoalHistoryResponse

        response = GoalHistoryResponse(entries=[], count=0)

        assert response.count == 0
        assert response.entries == []


class TestGetGoalStalenessEndpointLogic:
    """Tests for goal staleness endpoint logic."""

    def test_staleness_response_with_prompt(self):
        """Should create response with prompt flag for stale goals."""
        from backend.api.context.models import GoalStalenessResponse

        response = GoalStalenessResponse(
            days_since_change=45,
            should_prompt=True,
            last_goal="Test Goal",
        )

        assert response.days_since_change == 45
        assert response.should_prompt is True
        assert response.last_goal == "Test Goal"

    def test_staleness_response_without_prompt(self):
        """Should create response without prompt for recent goals."""
        from backend.api.context.models import GoalStalenessResponse

        response = GoalStalenessResponse(
            days_since_change=10,
            should_prompt=False,
            last_goal="Recent Goal",
        )

        assert response.days_since_change == 10
        assert response.should_prompt is False
        assert response.last_goal == "Recent Goal"

    def test_staleness_response_no_goal(self):
        """Should create response for no goal state."""
        from backend.api.context.models import GoalStalenessResponse

        response = GoalStalenessResponse(
            days_since_change=None,
            should_prompt=False,
            last_goal=None,
        )

        assert response.days_since_change is None
        assert response.should_prompt is False
        assert response.last_goal is None

    def test_staleness_threshold_constant(self):
        """Staleness threshold should be 180 days for strategic position."""
        from backend.api.context.routes import GOAL_STALENESS_THRESHOLD_DAYS

        assert GOAL_STALENESS_THRESHOLD_DAYS == 180


class TestGoalHistoryModels:
    """Tests for Pydantic models."""

    def test_goal_history_entry_required_fields(self):
        """GoalHistoryEntry should require goal_text and changed_at."""
        from backend.api.context.models import GoalHistoryEntry

        entry = GoalHistoryEntry(
            goal_text="Test",
            changed_at=datetime.now(UTC),
        )
        assert entry.goal_text == "Test"
        assert entry.previous_goal is None  # Optional field

    def test_goal_history_entry_with_previous(self):
        """GoalHistoryEntry should accept previous_goal."""
        from backend.api.context.models import GoalHistoryEntry

        entry = GoalHistoryEntry(
            goal_text="New Goal",
            changed_at=datetime.now(UTC),
            previous_goal="Old Goal",
        )
        assert entry.previous_goal == "Old Goal"

    def test_goal_staleness_response_defaults(self):
        """GoalStalenessResponse should have sensible defaults."""
        from backend.api.context.models import GoalStalenessResponse

        response = GoalStalenessResponse()
        assert response.days_since_change is None
        assert response.should_prompt is False
        assert response.last_goal is None


class TestGoalChangeRecording:
    """Tests for goal change recording integration."""

    def test_goal_change_should_be_recorded(self):
        """When goal changes, it should be recorded in history."""
        from backend.services.goal_tracker import record_goal_change

        with patch(
            "backend.services.goal_tracker.execute_query",
            return_value={"id": 1},
        ) as mock_query:
            result = record_goal_change(
                user_id="test-user",
                new_goal="New Goal",
                previous_goal="Old Goal",
            )

            assert result == 1
            # Verify INSERT was called
            call_args = mock_query.call_args[0]
            assert "INSERT INTO goal_history" in call_args[0]
            assert call_args[1][1] == "New Goal"
            assert call_args[1][2] == "Old Goal"

    def test_unchanged_goal_not_recorded(self):
        """When goal is unchanged, no record should be created."""
        from backend.services.goal_tracker import record_goal_change

        with patch(
            "backend.services.goal_tracker.execute_query",
        ) as mock_query:
            result = record_goal_change(
                user_id="test-user",
                new_goal="Same Goal",
                previous_goal="Same Goal",
            )

            assert result is None
            mock_query.assert_not_called()
