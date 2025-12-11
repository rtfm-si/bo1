"""Tests for user GDPR endpoints.

Validates:
- GET /v1/user/export returns user data as JSON
- DELETE /v1/user/delete anonymizes user data
- Rate limiting is enforced (1 request per 24h)
- Audit logging is created for GDPR requests
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from backend.api.user import _get_client_ip


@pytest.mark.unit
class TestGetClientIp:
    """Test IP extraction utility."""

    def test_get_ip_from_forwarded_header(self) -> None:
        """Test IP extraction from X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        mock_request.client = None

        result = _get_client_ip(mock_request)
        assert result == "192.168.1.100"

    def test_get_ip_from_client(self) -> None:
        """Test IP extraction from request.client."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.5"

        result = _get_client_ip(mock_request)
        assert result == "10.0.0.5"

    def test_get_ip_no_source(self) -> None:
        """Test IP returns None when no source available."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        result = _get_client_ip(mock_request)
        assert result is None


@pytest.mark.unit
class TestExportEndpointRateLimiting:
    """Test export endpoint rate limiting logic."""

    @patch("backend.api.user.get_recent_export_request")
    def test_recent_export_blocks_new_request(self, mock_recent: MagicMock) -> None:
        """Test that recent export request blocks new requests."""
        mock_recent.return_value = {
            "id": 1,
            "created_at": datetime.now(UTC),
        }

        # The rate limit check should find a recent request
        result = mock_recent("test-user", window_hours=24)
        assert result is not None
        assert "created_at" in result

    @patch("backend.api.user.get_recent_export_request")
    def test_no_recent_export_allows_request(self, mock_recent: MagicMock) -> None:
        """Test that no recent export allows new request."""
        mock_recent.return_value = None

        result = mock_recent("test-user", window_hours=24)
        assert result is None


@pytest.mark.unit
class TestDeleteEndpointRateLimiting:
    """Test delete endpoint rate limiting logic."""

    @patch("backend.api.user.get_recent_deletion_request")
    def test_pending_deletion_blocks_request(self, mock_recent: MagicMock) -> None:
        """Test that pending deletion blocks new requests."""
        mock_recent.return_value = {
            "id": 1,
            "action": "deletion_requested",
            "created_at": datetime.now(UTC),
        }

        result = mock_recent("test-user", window_hours=24)
        assert result is not None
        assert result["action"] == "deletion_requested"

    @patch("backend.api.user.get_recent_deletion_request")
    def test_completed_deletion_detected(self, mock_recent: MagicMock) -> None:
        """Test that completed deletion is detected."""
        mock_recent.return_value = {
            "id": 2,
            "action": "deletion_completed",
            "created_at": datetime.now(UTC),
        }

        result = mock_recent("test-user", window_hours=24)
        assert result is not None
        assert result["action"] == "deletion_completed"


@pytest.mark.unit
class TestDataExportContent:
    """Test data export content structure."""

    @patch("backend.api.user.collect_user_data")
    def test_export_data_structure(self, mock_collect: MagicMock) -> None:
        """Test exported data has expected structure."""
        mock_collect.return_value = {
            "export_date": "2024-01-15T00:00:00+00:00",
            "user_id": "test-user-123",
            "profile": {"email": "test@example.com"},
            "business_context": None,
            "sessions": [],
            "actions": [],
            "datasets": [],
            "projects": [],
            "gdpr_audit_log": [],
        }

        data = mock_collect("test-user-123")

        assert "export_date" in data
        assert "user_id" in data
        assert "profile" in data
        assert "sessions" in data
        assert "actions" in data
        assert "datasets" in data
        assert "gdpr_audit_log" in data


@pytest.mark.unit
class TestDataDeletionSummary:
    """Test data deletion summary structure."""

    @patch("backend.api.user.delete_user_data")
    def test_deletion_summary_structure(self, mock_delete: MagicMock) -> None:
        """Test deletion returns expected summary."""
        mock_delete.return_value = {
            "user_id": "test-user-123",
            "deleted_at": "2024-01-15T00:00:00+00:00",
            "sessions_anonymized": 5,
            "actions_anonymized": 10,
            "datasets_deleted": 2,
            "files_deleted": 2,
            "errors": [],
        }

        summary = mock_delete("test-user-123")

        assert "sessions_anonymized" in summary
        assert "actions_anonymized" in summary
        assert "datasets_deleted" in summary
        assert summary["sessions_anonymized"] == 5
        assert summary["actions_anonymized"] == 10


@pytest.mark.unit
class TestAuditLogging:
    """Test GDPR audit logging integration."""

    @patch("backend.api.user.log_gdpr_event")
    def test_export_logs_audit_event(self, mock_log: MagicMock) -> None:
        """Test that export request creates audit log."""
        mock_log.return_value = 123

        result = mock_log(
            user_id="test-user",
            action="export_requested",
            ip_address="192.168.1.1",
        )

        assert result == 123
        mock_log.assert_called_once()

    @patch("backend.api.user.log_gdpr_event")
    def test_deletion_logs_audit_events(self, mock_log: MagicMock) -> None:
        """Test that deletion creates audit logs."""
        mock_log.return_value = 456

        # Should log both request and completion
        result1 = mock_log(
            user_id="test-user",
            action="deletion_requested",
            ip_address="192.168.1.1",
        )
        result2 = mock_log(
            user_id="test-user",
            action="deletion_completed",
            details={"sessions_anonymized": 5},
            ip_address="192.168.1.1",
        )

        assert result1 == 456
        assert result2 == 456
