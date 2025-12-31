"""Tests for admin email API endpoints.

Tests:
- POST /api/admin/users/{user_id}/send-email - Send branded email to user
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.email import router
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import limiter


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with email router and admin auth override."""
    # Disable rate limiter for tests (to avoid Redis connection)
    original_enabled = limiter.enabled
    limiter.enabled = False

    test_app = FastAPI()
    test_app.dependency_overrides[require_admin_any] = mock_admin_override
    test_app.include_router(router, prefix="/api/admin")

    yield test_app

    # Restore original limiter state
    limiter.enabled = original_enabled


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def main_app_client():
    """Create test client using main app (for auth tests)."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestSendUserEmail:
    """Tests for POST /api/admin/users/{user_id}/send-email."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.post(
            "/api/admin/users/user-123/send-email",
            json={"template_type": "welcome"},
        )
        assert response.status_code == 403

    def test_send_welcome_email_successfully(self, client: TestClient):
        """Admin should be able to send welcome email."""
        with (
            patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists,
            patch("backend.api.utils.db_helpers.execute_query") as mock_execute,
            patch("backend.api.admin.email.send_email") as mock_send,
            patch("backend.api.admin.helpers.AdminUserService.log_admin_action") as mock_log,
        ):
            mock_exists.return_value = True
            mock_execute.return_value = {
                "email": "test@example.com",
                "name": "Test User",
            }
            mock_send.return_value = {"id": "resend-123"}

            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={"template_type": "welcome"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-123"
            assert data["email"] == "test@example.com"
            assert data["template_type"] == "welcome"
            assert data["sent"] is True
            assert "Welcome to Board of One" in data["subject"]

            # Verify audit logging was called
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs["action"] == "email_sent"
            assert call_args.kwargs["resource_id"] == "user-123"

    def test_send_custom_email_successfully(self, client: TestClient):
        """Admin should be able to send custom email."""
        with (
            patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists,
            patch("backend.api.utils.db_helpers.execute_query") as mock_execute,
            patch("backend.api.admin.email.send_email") as mock_send,
            patch("backend.api.admin.helpers.AdminUserService.log_admin_action"),
        ):
            mock_exists.return_value = True
            mock_execute.return_value = {
                "email": "test@example.com",
                "name": "Test User",
            }
            mock_send.return_value = {"id": "resend-123"}

            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={
                    "template_type": "custom",
                    "subject": "Important Update",
                    "body": "This is a test message.",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["template_type"] == "custom"
            assert data["subject"] == "Important Update"
            assert data["sent"] is True

    def test_custom_email_requires_subject_and_body(self, client: TestClient):
        """Custom email without subject/body should return 400."""
        with patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists:
            mock_exists.return_value = True

            # Missing subject
            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={
                    "template_type": "custom",
                    "body": "Test message",
                },
            )
            assert response.status_code == 400
            assert "subject" in response.json()["detail"].lower()

            # Missing body
            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={
                    "template_type": "custom",
                    "subject": "Test Subject",
                },
            )
            assert response.status_code == 400
            assert "body" in response.json()["detail"].lower()

    def test_user_not_found(self, client: TestClient):
        """Sending to non-existent user should return 404."""
        with patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists:
            mock_exists.return_value = False

            response = client.post(
                "/api/admin/users/nonexistent/send-email",
                json={"template_type": "welcome"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_user_without_email(self, client: TestClient):
        """User without valid email should return 400."""
        with (
            patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists,
            patch("backend.api.utils.db_helpers.execute_query") as mock_execute,
        ):
            mock_exists.return_value = True
            mock_execute.return_value = {"email": None, "name": None}

            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={"template_type": "welcome"},
            )

            assert response.status_code == 400
            assert "email" in response.json()["detail"].lower()

    def test_placeholder_email_rejected(self, client: TestClient):
        """Placeholder emails should be rejected."""
        with (
            patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists,
            patch("backend.api.utils.db_helpers.execute_query") as mock_execute,
        ):
            mock_exists.return_value = True
            mock_execute.return_value = {
                "email": "user123@placeholder.local",
                "name": None,
            }

            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={"template_type": "welcome"},
            )

            assert response.status_code == 400
            assert "placeholder" in response.json()["detail"].lower()

    def test_email_send_failure_logged(self, client: TestClient):
        """Failed email send should be logged and return sent=False."""
        with (
            patch("backend.api.admin.helpers.AdminQueryService.user_exists") as mock_exists,
            patch("backend.api.utils.db_helpers.execute_query") as mock_execute,
            patch("backend.api.admin.email.send_email") as mock_send,
            patch("backend.api.admin.helpers.AdminUserService.log_admin_action") as mock_log,
        ):
            mock_exists.return_value = True
            mock_execute.return_value = {
                "email": "test@example.com",
                "name": "Test User",
            }
            mock_send.side_effect = Exception("Resend API error")

            response = client.post(
                "/api/admin/users/user-123/send-email",
                json={"template_type": "welcome"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["sent"] is False
            assert "failed" in data["message"].lower()

            # Verify audit logging still occurred
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs["details"]["sent"] is False


class TestEmailTemplateRendering:
    """Tests for email template rendering."""

    def test_render_admin_custom_email(self):
        """Custom email template should render correctly."""
        from backend.services.email_templates import render_admin_custom_email

        html, text = render_admin_custom_email(
            subject="Test Subject",
            body="Line 1\nLine 2\nLine 3",
            user_name="Alice",
        )

        # HTML assertions
        assert "Test Subject" in html
        assert "Hi Alice," in html
        assert "<p>Line 1</p>" in html
        assert "<p>Line 2</p>" in html
        assert "Board of One" in html

        # Plain text assertions
        assert "Test Subject" in text
        assert "Hi Alice," in text
        assert "Line 1" in text
        assert "Board of One team" in text

    def test_render_admin_custom_email_no_name(self):
        """Custom email without user name should use generic greeting."""
        from backend.services.email_templates import render_admin_custom_email

        html, text = render_admin_custom_email(
            subject="Test",
            body="Message",
            user_name=None,
        )

        assert "Hello," in html
        assert "Hello," in text
