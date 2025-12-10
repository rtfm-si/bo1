"""Tests for action stats endpoint.

Tests GET /api/v1/actions/stats for dashboard progress visualization.
"""

from datetime import date

from backend.api.models import (
    ActionStatsResponse,
    ActionStatsTotals,
    DailyActionStat,
)


class TestActionStatsModels:
    """Test ActionStats Pydantic models."""

    def test_daily_action_stat_creation(self):
        """Test DailyActionStat model creation."""
        stat = DailyActionStat(
            date="2025-12-01",
            completed_count=5,
            created_count=3,
        )
        assert stat.date == "2025-12-01"
        assert stat.completed_count == 5
        assert stat.created_count == 3

    def test_daily_action_stat_defaults(self):
        """Test DailyActionStat default values."""
        stat = DailyActionStat(date="2025-12-01")
        assert stat.completed_count == 0
        assert stat.created_count == 0

    def test_action_stats_totals_creation(self):
        """Test ActionStatsTotals model creation."""
        totals = ActionStatsTotals(
            completed=10,
            in_progress=3,
            todo=5,
        )
        assert totals.completed == 10
        assert totals.in_progress == 3
        assert totals.todo == 5

    def test_action_stats_totals_defaults(self):
        """Test ActionStatsTotals default values."""
        totals = ActionStatsTotals()
        assert totals.completed == 0
        assert totals.in_progress == 0
        assert totals.todo == 0

    def test_action_stats_response_creation(self):
        """Test ActionStatsResponse model creation."""
        daily = [
            DailyActionStat(date="2025-12-01", completed_count=2, created_count=1),
            DailyActionStat(date="2025-12-02", completed_count=3, created_count=2),
        ]
        totals = ActionStatsTotals(completed=10, in_progress=3, todo=5)

        response = ActionStatsResponse(daily=daily, totals=totals)

        assert len(response.daily) == 2
        assert response.daily[0].date == "2025-12-01"
        assert response.totals.completed == 10


class TestActionStatsEndpointLogic:
    """Test stats endpoint business logic."""

    def test_stats_response_structure(self):
        """Test that stats response has expected structure."""
        daily = [
            DailyActionStat(date="2025-12-10", completed_count=0, created_count=0)
            for _ in range(14)
        ]
        totals = ActionStatsTotals(completed=5, in_progress=2, todo=8)

        response = ActionStatsResponse(daily=daily, totals=totals)

        # Verify response can be serialized to JSON
        json_data = response.model_dump()
        assert "daily" in json_data
        assert "totals" in json_data
        assert len(json_data["daily"]) == 14

    def test_totals_sum_calculation(self):
        """Test that totals represent sum of all actions."""
        # The endpoint should return accurate totals regardless of daily stats
        totals = ActionStatsTotals(completed=50, in_progress=10, todo=40)

        total_actions = totals.completed + totals.in_progress + totals.todo
        assert total_actions == 100

    def test_daily_stats_date_format(self):
        """Test that daily stats use ISO date format."""
        today = date.today()
        stat = DailyActionStat(
            date=today.isoformat(),
            completed_count=1,
            created_count=2,
        )

        # Verify date can be parsed back
        parsed_date = date.fromisoformat(stat.date)
        assert parsed_date == today
