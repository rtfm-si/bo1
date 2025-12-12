"""Tests for onboarding analytics service."""

from unittest.mock import MagicMock, patch

from backend.services import onboarding_analytics


class TestGetFunnelMetrics:
    """Tests for get_funnel_metrics function."""

    @patch("backend.services.onboarding_analytics.db_session")
    def test_returns_funnel_metrics(self, mock_db_session: MagicMock) -> None:
        """Test that funnel metrics are returned correctly."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock query results for all funnel stages
        mock_cursor.fetchone.side_effect = [
            {"count": 1000},  # total signups
            {"count": 700},  # context completed
            {"count": 500},  # first meeting
            {"count": 400},  # meeting completed
            {"count": 100},  # cohort 7d signups
            {"count": 70},  # cohort 7d context
            {"count": 50},  # cohort 7d meeting
            {"count": 40},  # cohort 7d completed
            {"count": 300},  # cohort 30d signups
            {"count": 210},  # cohort 30d context
            {"count": 150},  # cohort 30d meeting
            {"count": 120},  # cohort 30d completed
        ]

        result = onboarding_analytics.get_funnel_metrics()

        assert result.total_signups == 1000
        assert result.context_completed == 700
        assert result.first_meeting == 500
        assert result.meeting_completed == 400

        # Check conversion rates
        assert result.signup_to_context == 70.0  # 700/1000 * 100
        assert result.context_to_meeting == 71.4  # 500/700 * 100, rounded
        assert result.meeting_to_complete == 80.0  # 400/500 * 100
        assert result.overall_conversion == 40.0  # 400/1000 * 100

        # Check cohorts
        assert result.cohort_7d.signups == 100
        assert result.cohort_7d.context_completed == 70
        assert result.cohort_30d.signups == 300
        assert result.cohort_30d.meeting_completed == 120

    @patch("backend.services.onboarding_analytics.db_session")
    def test_handles_zero_denominator(self, mock_db_session: MagicMock) -> None:
        """Test that zero denominators don't cause division errors."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # All zeros
        mock_cursor.fetchone.return_value = {"count": 0}

        result = onboarding_analytics.get_funnel_metrics()

        assert result.total_signups == 0
        assert result.signup_to_context == 0.0
        assert result.overall_conversion == 0.0


class TestGetFunnelStages:
    """Tests for get_funnel_stages function."""

    @patch("backend.services.onboarding_analytics.get_funnel_metrics")
    def test_returns_stages_list(self, mock_get_funnel: MagicMock) -> None:
        """Test that funnel stages are returned as a list."""
        mock_get_funnel.return_value = onboarding_analytics.OnboardingFunnel(
            total_signups=100,
            context_completed=80,
            first_meeting=60,
            meeting_completed=40,
            signup_to_context=80.0,
            context_to_meeting=75.0,
            meeting_to_complete=66.7,
            overall_conversion=40.0,
            cohort_7d=onboarding_analytics.OnboardingCohort(
                period_days=7,
                signups=10,
                context_completed=8,
                first_meeting=6,
                meeting_completed=4,
            ),
            cohort_30d=onboarding_analytics.OnboardingCohort(
                period_days=30,
                signups=30,
                context_completed=24,
                first_meeting=18,
                meeting_completed=12,
            ),
        )

        stages = onboarding_analytics.get_funnel_stages()

        assert len(stages) == 4
        assert stages[0].name == "Signups"
        assert stages[0].count == 100
        assert stages[0].conversion_rate == 100.0  # First stage always 100%

        assert stages[1].name == "Context Setup"
        assert stages[1].count == 80
        assert stages[1].conversion_rate == 80.0

        assert stages[2].name == "First Meeting"
        assert stages[3].name == "Meeting Completed"
