"""Tests for admin email stats API endpoints.

Tests:
- GET /api/admin/email-stats
"""

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

            # Mock query results
            mock_cursor.fetchall.return_value = [
                {"email_type": "welcome", "count": 50},
                {"email_type": "meeting_completed", "count": 30},
                {"email_type": "action_reminder", "count": 20},
            ]
            mock_cursor.fetchone.side_effect = [
                {"count": 5},  # today
                {"count": 35},  # week
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
            mock_cursor.fetchall.return_value = []
            mock_cursor.fetchone.side_effect = [
                {"count": 0},
                {"count": 0},
            ]

            response = client.get("/api/admin/email-stats", headers=admin_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 0
            assert data["by_type"] == {}
            assert data["by_period"]["today"] == 0
            assert data["by_period"]["week"] == 0
            assert data["by_period"]["month"] == 0

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

            mock_cursor.fetchall.return_value = []
            mock_cursor.fetchone.side_effect = [{"count": 0}, {"count": 0}]

            response = client.get("/api/admin/email-stats?days=7", headers=admin_headers)
            assert response.status_code == 200


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
