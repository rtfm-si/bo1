"""Tests for admin user metrics API endpoints.

Tests:
- GET /api/admin/metrics/users
- GET /api/admin/metrics/usage
- GET /api/admin/metrics/onboarding
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_headers():
    """Admin API key headers."""
    return {"X-Admin-Key": "test-admin-key"}


class TestUserMetricsEndpoint:
    """Tests for GET /api/admin/metrics/users."""

    def test_returns_403_without_admin(self, client: TestClient):
        """Non-admin users should get 403."""
        # No API key, no session
        response = client.get("/api/admin/metrics/users")
        assert response.status_code == 403

    def test_returns_user_metrics(self, client: TestClient, admin_headers: dict):
        """Admin users should get user metrics."""
        with (
            patch("backend.api.admin.user_metrics.user_analytics") as mock_analytics,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            # Mock signup stats
            mock_signup = MagicMock()
            mock_signup.total_users = 100
            mock_signup.new_users_today = 5
            mock_signup.new_users_7d = 25
            mock_signup.new_users_30d = 80
            mock_signup.daily_signups = [(date(2025, 1, 1), 3), (date(2025, 1, 2), 5)]
            mock_analytics.get_signup_stats.return_value = mock_signup

            # Mock active stats
            mock_active = MagicMock()
            mock_active.dau = 10
            mock_active.wau = 50
            mock_active.mau = 150
            mock_active.daily_active = [(date(2025, 1, 1), 8)]
            mock_analytics.get_active_user_stats.return_value = mock_active

            response = client.get("/api/admin/metrics/users", headers=admin_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["total_users"] == 100
            assert data["new_users_today"] == 5
            assert data["dau"] == 10
            assert data["wau"] == 50
            assert data["mau"] == 150
            assert len(data["daily_signups"]) == 2

    def test_respects_days_parameter(self, client: TestClient, admin_headers: dict):
        """Days parameter should be passed to analytics."""
        with (
            patch("backend.api.admin.user_metrics.user_analytics") as mock_analytics,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            # Setup minimal mocks
            mock_signup = MagicMock()
            mock_signup.total_users = 0
            mock_signup.new_users_today = 0
            mock_signup.new_users_7d = 0
            mock_signup.new_users_30d = 0
            mock_signup.daily_signups = []
            mock_active = MagicMock()
            mock_active.dau = 0
            mock_active.wau = 0
            mock_active.mau = 0
            mock_active.daily_active = []
            mock_analytics.get_signup_stats.return_value = mock_signup
            mock_analytics.get_active_user_stats.return_value = mock_active

            response = client.get("/api/admin/metrics/users?days=7", headers=admin_headers)
            assert response.status_code == 200

            # Verify days parameter was passed
            mock_analytics.get_signup_stats.assert_called_once_with(7)
            mock_analytics.get_active_user_stats.assert_called_once_with(7)


class TestUsageMetricsEndpoint:
    """Tests for GET /api/admin/metrics/usage."""

    def test_returns_usage_metrics(self, client: TestClient, admin_headers: dict):
        """Admin users should get usage metrics."""
        with (
            patch("backend.api.admin.user_metrics.user_analytics") as mock_analytics,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_usage = MagicMock()
            mock_usage.total_meetings = 500
            mock_usage.meetings_today = 10
            mock_usage.meetings_7d = 50
            mock_usage.meetings_30d = 200
            mock_usage.total_actions = 1200
            mock_usage.actions_created_7d = 100
            mock_usage.daily_meetings = [(date(2025, 1, 1), 5)]
            mock_usage.daily_actions = [(date(2025, 1, 1), 20)]
            mock_analytics.get_usage_stats.return_value = mock_usage

            response = client.get("/api/admin/metrics/usage", headers=admin_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["total_meetings"] == 500
            assert data["meetings_today"] == 10
            assert data["total_actions"] == 1200
            assert len(data["daily_meetings"]) == 1


class TestOnboardingMetricsEndpoint:
    """Tests for GET /api/admin/metrics/onboarding."""

    def test_returns_onboarding_funnel(self, client: TestClient, admin_headers: dict):
        """Admin users should get onboarding funnel metrics."""
        with (
            patch("backend.api.admin.user_metrics.onboarding_analytics") as mock_analytics,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            # Mock funnel metrics
            mock_funnel = MagicMock()
            mock_funnel.total_signups = 1000
            mock_funnel.context_completed = 700
            mock_funnel.first_meeting = 500
            mock_funnel.meeting_completed = 400
            mock_funnel.signup_to_context = 70.0
            mock_funnel.context_to_meeting = 71.4
            mock_funnel.meeting_to_complete = 80.0
            mock_funnel.overall_conversion = 40.0

            # Mock cohorts
            mock_funnel.cohort_7d = MagicMock()
            mock_funnel.cohort_7d.period_days = 7
            mock_funnel.cohort_7d.signups = 100
            mock_funnel.cohort_7d.context_completed = 70
            mock_funnel.cohort_7d.first_meeting = 50
            mock_funnel.cohort_7d.meeting_completed = 40

            mock_funnel.cohort_30d = MagicMock()
            mock_funnel.cohort_30d.period_days = 30
            mock_funnel.cohort_30d.signups = 300
            mock_funnel.cohort_30d.context_completed = 210
            mock_funnel.cohort_30d.first_meeting = 150
            mock_funnel.cohort_30d.meeting_completed = 120

            mock_analytics.get_funnel_metrics.return_value = mock_funnel

            # Mock stages
            mock_stage1 = MagicMock()
            mock_stage1.name = "Signups"
            mock_stage1.count = 1000
            mock_stage1.conversion_rate = 100.0

            mock_stage2 = MagicMock()
            mock_stage2.name = "Context Setup"
            mock_stage2.count = 700
            mock_stage2.conversion_rate = 70.0

            mock_analytics.get_funnel_stages.return_value = [mock_stage1, mock_stage2]

            response = client.get("/api/admin/metrics/onboarding", headers=admin_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["total_signups"] == 1000
            assert data["context_completed"] == 700
            assert data["overall_conversion"] == 40.0
            assert len(data["stages"]) == 2
            assert data["stages"][0]["name"] == "Signups"
            assert data["cohort_7d"]["signups"] == 100
            assert data["cohort_30d"]["signups"] == 300
