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
            in_progress_count=3,
            sessions_run=2,
            mentor_sessions=4,
        )
        assert stat.date == "2025-12-01"
        assert stat.completed_count == 5
        assert stat.in_progress_count == 3
        assert stat.sessions_run == 2
        assert stat.mentor_sessions == 4

    def test_daily_action_stat_defaults(self):
        """Test DailyActionStat default values."""
        stat = DailyActionStat(date="2025-12-01")
        assert stat.completed_count == 0
        assert stat.in_progress_count == 0
        assert stat.sessions_run == 0
        assert stat.mentor_sessions == 0
        assert stat.estimated_starts == 0
        assert stat.estimated_completions == 0

    def test_daily_action_stat_with_estimates(self):
        """Test DailyActionStat with estimated future counts."""
        stat = DailyActionStat(
            date="2025-12-20",
            completed_count=0,
            in_progress_count=0,
            sessions_run=0,
            mentor_sessions=0,
            estimated_starts=3,
            estimated_completions=2,
        )
        assert stat.date == "2025-12-20"
        assert stat.estimated_starts == 3
        assert stat.estimated_completions == 2
        # Actuals should be 0 for future dates
        assert stat.completed_count == 0
        assert stat.in_progress_count == 0

    def test_daily_action_stat_mixed_actuals_and_estimates(self):
        """Test edge case: today could have both actuals and estimates."""
        stat = DailyActionStat(
            date="2025-12-14",  # "today"
            completed_count=2,
            in_progress_count=1,
            sessions_run=1,
            mentor_sessions=0,
            estimated_starts=1,  # Actions due to start today but not yet started
            estimated_completions=3,  # Actions due today but not yet completed
        )
        # Both actuals and estimates can coexist on today's date
        assert stat.completed_count == 2
        assert stat.estimated_completions == 3
        assert stat.in_progress_count == 1
        assert stat.estimated_starts == 1

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
            DailyActionStat(
                date="2025-12-01",
                completed_count=2,
                in_progress_count=1,
                sessions_run=1,
                mentor_sessions=2,
            ),
            DailyActionStat(
                date="2025-12-02",
                completed_count=3,
                in_progress_count=2,
                sessions_run=2,
                mentor_sessions=3,
            ),
        ]
        totals = ActionStatsTotals(completed=10, in_progress=3, todo=5)

        response = ActionStatsResponse(daily=daily, totals=totals)

        assert len(response.daily) == 2
        assert response.daily[0].date == "2025-12-01"
        assert response.daily[0].sessions_run == 1
        assert response.daily[0].mentor_sessions == 2
        assert response.totals.completed == 10


class TestActionStatsEndpointLogic:
    """Test stats endpoint business logic."""

    def test_stats_response_structure(self):
        """Test that stats response has expected structure."""
        daily = [
            DailyActionStat(
                date="2025-12-10",
                completed_count=0,
                in_progress_count=0,
                sessions_run=0,
                mentor_sessions=0,
                estimated_starts=0,
                estimated_completions=0,
            )
            for _ in range(14)
        ]
        totals = ActionStatsTotals(completed=5, in_progress=2, todo=8)

        response = ActionStatsResponse(daily=daily, totals=totals)

        # Verify response can be serialized to JSON
        json_data = response.model_dump()
        assert "daily" in json_data
        assert "totals" in json_data
        assert len(json_data["daily"]) == 14
        # Verify all daily stats have heatmap fields
        for stat in json_data["daily"]:
            assert "sessions_run" in stat
            assert "in_progress_count" in stat
            assert "mentor_sessions" in stat
            assert "estimated_starts" in stat
            assert "estimated_completions" in stat

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
            in_progress_count=2,
        )

        # Verify date can be parsed back
        parsed_date = date.fromisoformat(stat.date)
        assert parsed_date == today
