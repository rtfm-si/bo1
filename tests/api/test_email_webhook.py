"""Tests for email webhook endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.email import EVENT_TO_COLUMN

# Check if svix is available
try:
    from svix.webhooks import WebhookVerificationError

    HAS_SVIX = True
except ImportError:
    HAS_SVIX = False
    WebhookVerificationError = Exception  # type: ignore


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def webhook_payload():
    """Base webhook payload."""
    return {
        "type": "email.delivered",
        "data": {"email_id": "re_abc123xyz"},
    }


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    with patch("backend.api.email.db_session") as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=None)
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock_cursor


@pytest.fixture
def mock_settings_no_secret():
    """Mock settings without webhook secret."""
    with patch("backend.api.email.get_settings") as mock:
        settings = MagicMock()
        settings.resend_webhook_secret = None
        mock.return_value = settings
        yield settings


@pytest.fixture
def mock_settings_with_secret():
    """Mock settings with webhook secret."""
    with patch("backend.api.email.get_settings") as mock:
        settings = MagicMock()
        settings.resend_webhook_secret = "whsec_test_secret_key_12345"  # noqa: S105
        mock.return_value = settings
        yield settings


class TestWebhookEndpoint:
    """Tests for POST /v1/email/webhook."""

    def test_webhook_delivered_event_updates_db(
        self, client: TestClient, webhook_payload, mock_db_session, mock_settings_no_secret
    ):
        """Test delivered event updates delivered_at column."""
        mock_db_session.fetchone.return_value = {"id": 1}

        response = client.post(
            "/api/v1/email/webhook",
            json=webhook_payload,
        )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify SQL was executed with correct column
        mock_db_session.execute.assert_called_once()
        sql_call = mock_db_session.execute.call_args[0][0]
        assert "delivered_at" in sql_call
        assert "COALESCE" in sql_call  # Idempotent update

    def test_webhook_opened_event(
        self, client: TestClient, mock_db_session, mock_settings_no_secret
    ):
        """Test opened event updates opened_at column."""
        mock_db_session.fetchone.return_value = {"id": 1}
        payload = {"type": "email.opened", "data": {"email_id": "re_xyz789"}}

        response = client.post("/api/v1/email/webhook", json=payload)

        assert response.status_code == 200
        sql_call = mock_db_session.execute.call_args[0][0]
        assert "opened_at" in sql_call

    def test_webhook_clicked_event(
        self, client: TestClient, mock_db_session, mock_settings_no_secret
    ):
        """Test clicked event updates clicked_at column."""
        mock_db_session.fetchone.return_value = {"id": 1}
        payload = {"type": "email.clicked", "data": {"email_id": "re_click123"}}

        response = client.post("/api/v1/email/webhook", json=payload)

        assert response.status_code == 200
        sql_call = mock_db_session.execute.call_args[0][0]
        assert "clicked_at" in sql_call

    def test_webhook_bounced_event(
        self, client: TestClient, mock_db_session, mock_settings_no_secret
    ):
        """Test bounced event updates bounced_at column."""
        mock_db_session.fetchone.return_value = {"id": 1}
        payload = {"type": "email.bounced", "data": {"email_id": "re_bounce456"}}

        response = client.post("/api/v1/email/webhook", json=payload)

        assert response.status_code == 200
        sql_call = mock_db_session.execute.call_args[0][0]
        assert "bounced_at" in sql_call

    def test_webhook_delivery_failed_event(
        self, client: TestClient, mock_db_session, mock_settings_no_secret
    ):
        """Test delivery_failed event updates failed_at column."""
        mock_db_session.fetchone.return_value = {"id": 1}
        payload = {"type": "email.delivery_failed", "data": {"email_id": "re_fail789"}}

        response = client.post("/api/v1/email/webhook", json=payload)

        assert response.status_code == 200
        sql_call = mock_db_session.execute.call_args[0][0]
        assert "failed_at" in sql_call

    def test_webhook_unknown_resend_id_returns_ok(
        self, client: TestClient, webhook_payload, mock_db_session, mock_settings_no_secret
    ):
        """Test unknown resend_id returns 200 (idempotent)."""
        mock_db_session.fetchone.return_value = None  # No row found

        response = client.post("/api/v1/email/webhook", json=webhook_payload)

        # Should still return 200 - idempotent
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_webhook_duplicate_events_ignored(
        self, client: TestClient, webhook_payload, mock_db_session, mock_settings_no_secret
    ):
        """Test duplicate events don't overwrite existing timestamp (COALESCE)."""
        mock_db_session.fetchone.return_value = {"id": 1}

        # First call
        response1 = client.post("/api/v1/email/webhook", json=webhook_payload)
        assert response1.status_code == 200

        # Second call (duplicate)
        response2 = client.post("/api/v1/email/webhook", json=webhook_payload)
        assert response2.status_code == 200

        # Both should succeed - COALESCE in SQL prevents overwrite
        sql_call = mock_db_session.execute.call_args[0][0]
        assert "COALESCE" in sql_call

    def test_webhook_unknown_event_type_ignored(self, client: TestClient, mock_settings_no_secret):
        """Test unknown event types are ignored."""
        payload = {"type": "email.sent", "data": {"email_id": "re_sent123"}}

        response = client.post("/api/v1/email/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}

    def test_webhook_missing_email_id_ignored(self, client: TestClient, mock_settings_no_secret):
        """Test events missing email_id are ignored."""
        payload = {"type": "email.delivered", "data": {}}

        response = client.post("/api/v1/email/webhook", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}

    def test_webhook_invalid_json_returns_400(self, client: TestClient, mock_settings_no_secret):
        """Test invalid JSON payload returns 400."""
        response = client.post(
            "/api/v1/email/webhook",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

    @pytest.mark.skipif(not HAS_SVIX, reason="svix library not installed")
    def test_webhook_signature_verification_enabled(
        self, client: TestClient, webhook_payload, mock_settings_with_secret
    ):
        """Test signature verification is enforced when secret is configured."""
        # Mock Webhook to raise WebhookVerificationError
        with patch("backend.api.email.Webhook") as mock_webhook_class:
            mock_wh = MagicMock()
            mock_wh.verify.side_effect = WebhookVerificationError("Invalid signature")
            mock_webhook_class.return_value = mock_wh

            response = client.post("/api/v1/email/webhook", json=webhook_payload)

            assert response.status_code == 400
            assert "Invalid webhook signature" in response.json()["detail"]

    def test_webhook_signature_verification_with_valid_signature(
        self, client: TestClient, webhook_payload, mock_db_session, mock_settings_with_secret
    ):
        """Test valid signature passes verification."""
        mock_db_session.fetchone.return_value = {"id": 1}

        # Mock the Webhook.verify to pass
        with patch("backend.api.email.Webhook") as mock_webhook_class:
            mock_wh = MagicMock()
            mock_webhook_class.return_value = mock_wh

            response = client.post(
                "/api/v1/email/webhook",
                json=webhook_payload,
                headers={
                    "svix-id": "msg_test123",
                    "svix-timestamp": "1234567890",
                    "svix-signature": "v1,valid_signature",
                },
            )

            assert response.status_code == 200
            mock_wh.verify.assert_called_once()


class TestEventToColumnMapping:
    """Tests for EVENT_TO_COLUMN mapping."""

    def test_all_event_types_mapped(self):
        """Verify all expected event types are in the mapping."""
        expected_events = [
            "email.delivered",
            "email.opened",
            "email.clicked",
            "email.bounced",
            "email.delivery_failed",
        ]
        for event in expected_events:
            assert event in EVENT_TO_COLUMN

    def test_columns_are_valid(self):
        """Verify all column names are valid timestamp columns."""
        valid_columns = ["delivered_at", "opened_at", "clicked_at", "bounced_at", "failed_at"]
        for column in EVENT_TO_COLUMN.values():
            assert column in valid_columns
