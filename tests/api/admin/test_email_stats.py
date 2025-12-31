"""Tests for admin email stats API endpoints.

Tests:
- GET /api/admin/email-stats
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.middleware.rate_limit import limiter


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    # Disable rate limiter for tests (to avoid Redis connection)
    original_enabled = limiter.enabled
    limiter.enabled = False

    yield TestClient(app, raise_server_exceptions=False)

    # Restore original limiter state
    limiter.enabled = original_enabled


@pytest.fixture
def admin_headers():
    """Admin API key headers."""
    return {"X-Admin-Key": "test-admin-key"}


class TestEmailStatsEndpoint:
    """Tests for GET /api/admin/email-stats."""

    def test_returns_403_without_admin(self, client: TestClient):
        """Non-admin users should get 403."""
        response = client.get("/api/admin/email-stats")
        assert response.status_code == 403

    def test_returns_email_stats(self, client: TestClient, admin_headers: dict):
        """Admin users should get email stats."""
        with (
            patch("backend.api.admin.email_stats.db_session") as mock_db_session,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            # Set up mock cursor
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Mock query results - now includes event counts
            mock_cursor.fetchall.side_effect = [
                # by_type counts
                [
                    {"email_type": "welcome", "count": 50},
                    {"email_type": "meeting_completed", "count": 30},
                    {"email_type": "action_reminder", "count": 20},
                ],
                # by_type event counts
                [
                    {
                        "email_type": "welcome",
                        "sent_count": 50,
                        "delivered_count": 48,
                        "opened_count": 24,
                        "clicked_count": 10,
                        "bounced_count": 1,
                        "failed_count": 1,
                    },
                    {
                        "email_type": "meeting_completed",
                        "sent_count": 30,
                        "delivered_count": 30,
                        "opened_count": 20,
                        "clicked_count": 5,
                        "bounced_count": 0,
                        "failed_count": 0,
                    },
                    {
                        "email_type": "action_reminder",
                        "sent_count": 20,
                        "delivered_count": 18,
                        "opened_count": 6,
                        "clicked_count": 2,
                        "bounced_count": 1,
                        "failed_count": 1,
                    },
                ],
            ]
            mock_cursor.fetchone.side_effect = [
                {"count": 5},  # today
                {"count": 35},  # week
                # Overall event counts
                {
                    "sent_count": 100,
                    "delivered_count": 96,
                    "opened_count": 50,
                    "clicked_count": 17,
                    "bounced_count": 2,
                    "failed_count": 2,
                },
            ]

            response = client.get("/api/admin/email-stats", headers=admin_headers)
            assert response.status_code == 200

            data = response.json()

            # Verify total
            assert data["total"] == 100  # 50 + 30 + 20

            # Verify by_type
            assert data["by_type"]["welcome"] == 50
            assert data["by_type"]["meeting_completed"] == 30
            assert data["by_type"]["action_reminder"] == 20

            # Verify by_period
            assert data["by_period"]["today"] == 5
            assert data["by_period"]["week"] == 35
            assert data["by_period"]["month"] == 100

            # Verify event counts (new)
            assert data["event_counts"]["sent_count"] == 100
            assert data["event_counts"]["delivered_count"] == 96
            assert data["event_counts"]["opened_count"] == 50
            assert data["event_counts"]["clicked_count"] == 17
            assert data["event_counts"]["bounced_count"] == 2
            assert data["event_counts"]["failed_count"] == 2

            # Verify rates (new)
            assert "rates" in data
            assert data["rates"]["open_rate"] == pytest.approx(50 / 96, rel=0.01)
            assert data["rates"]["click_rate"] == pytest.approx(17 / 96, rel=0.01)
            assert data["rates"]["failed_rate"] == pytest.approx(4 / 100, rel=0.01)

            # Verify by_type_rates (new)
            assert "by_type_rates" in data
            assert "welcome" in data["by_type_rates"]

    def test_handles_empty_data(self, client: TestClient, admin_headers: dict):
        """Should handle empty email log gracefully."""
        with (
            patch("backend.api.admin.email_stats.db_session") as mock_db_session,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Empty results
            mock_cursor.fetchall.side_effect = [[], []]  # type counts, type event counts
            mock_cursor.fetchone.side_effect = [
                {"count": 0},  # today
                {"count": 0},  # week
                {  # overall event counts
                    "sent_count": 0,
                    "delivered_count": 0,
                    "opened_count": 0,
                    "clicked_count": 0,
                    "bounced_count": 0,
                    "failed_count": 0,
                },
            ]

            response = client.get("/api/admin/email-stats", headers=admin_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 0
            assert data["by_type"] == {}
            assert data["by_period"]["today"] == 0
            assert data["by_period"]["week"] == 0
            assert data["by_period"]["month"] == 0
            # Verify rates are 0.0 when no data (division by zero handling)
            assert data["rates"]["open_rate"] == 0.0
            assert data["rates"]["click_rate"] == 0.0
            assert data["rates"]["failed_rate"] == 0.0
            assert data["by_type_rates"] == {}

    def test_accepts_days_parameter(self, client: TestClient, admin_headers: dict):
        """Should accept custom days parameter."""
        with (
            patch("backend.api.admin.email_stats.db_session") as mock_db_session,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            mock_cursor.fetchall.side_effect = [[], []]  # type counts, type event counts
            mock_cursor.fetchone.side_effect = [
                {"count": 0},
                {"count": 0},
                {
                    "sent_count": 0,
                    "delivered_count": 0,
                    "opened_count": 0,
                    "clicked_count": 0,
                    "bounced_count": 0,
                    "failed_count": 0,
                },
            ]

            response = client.get("/api/admin/email-stats?days=7", headers=admin_headers)
            assert response.status_code == 200


class TestRateCalculation:
    """Tests for rate calculation helper."""

    def test_calculate_rate_normal(self):
        """Test rate calculation with normal values."""
        from backend.api.admin.email_stats import _calculate_rate

        # 50% open rate
        assert _calculate_rate(50, 100) == 0.5
        # 25% click rate
        assert _calculate_rate(25, 100) == 0.25

    def test_calculate_rate_division_by_zero(self):
        """Test rate calculation handles division by zero."""
        from backend.api.admin.email_stats import _calculate_rate

        assert _calculate_rate(50, 0) == 0.0
        assert _calculate_rate(0, 0) == 0.0

    def test_calculate_rate_rounding(self):
        """Test rate calculation rounds to 4 decimal places."""
        from backend.api.admin.email_stats import _calculate_rate

        # 33.33...% should round to 0.3333
        result = _calculate_rate(1, 3)
        assert result == 0.3333


class TestEmailTypeExtraction:
    """Tests for _extract_email_type function."""

    def test_extracts_from_tags(self):
        """Should extract email type from tags first."""
        from backend.services.email import _extract_email_type

        tags = [{"name": "email_type", "value": "custom_type"}]
        result = _extract_email_type("Some subject", tags)
        assert result == "custom_type"

    def test_derives_welcome_from_subject(self):
        """Should detect welcome emails from subject."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Welcome to Board of One!")
        assert result == "welcome"

    def test_derives_meeting_completed_from_subject(self):
        """Should detect meeting completed emails."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Your meeting is complete")
        assert result == "meeting_completed"

    def test_derives_meeting_failed_from_subject(self):
        """Should detect meeting failed emails."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Your meeting failed unexpectedly")
        assert result == "meeting_failed"

    def test_derives_action_reminder_from_subject(self):
        """Should detect action reminder emails."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Action reminder: Complete task")
        assert result == "action_reminder"

    def test_derives_weekly_digest_from_subject(self):
        """Should detect weekly digest emails."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Your weekly digest")
        assert result == "weekly_digest"

    def test_derives_workspace_invitation_from_subject(self):
        """Should detect workspace invitation emails."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Workspace invitation: Join the team")
        assert result == "workspace_invitation"

    def test_returns_other_for_unknown(self):
        """Should return 'other' for unrecognized subjects."""
        from backend.services.email import _extract_email_type

        result = _extract_email_type("Some random email subject")
        assert result == "other"


class TestEmailLogging:
    """Tests for _log_email_send function."""

    def test_logs_email_to_database(self):
        """Should insert email log record."""
        with patch("bo1.state.database.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            from backend.services.email import _log_email_send

            _log_email_send("welcome", "test@example.com", "re_abc123", "sent")

            # Verify INSERT was called
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "INSERT INTO email_log" in call_args[0][0]
            assert call_args[0][1] == ("welcome", "test@example.com", "sent", "re_abc123")

    def test_handles_database_error_gracefully(self):
        """Should not raise on database error."""
        with patch("bo1.state.database.db_session") as mock_db_session:
            mock_db_session.return_value.__enter__ = MagicMock(side_effect=Exception("DB error"))

            from backend.services.email import _log_email_send

            # Should not raise
            _log_email_send("welcome", "test@example.com", "re_abc123", "sent")
