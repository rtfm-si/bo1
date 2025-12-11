"""Tests for GDPR audit logging service."""

from unittest.mock import MagicMock, patch

from backend.services.audit import (
    GDPR_ACTIONS,
    get_recent_deletion_request,
    get_recent_export_request,
    get_user_audit_log,
    log_gdpr_event,
)


class TestGdprActions:
    """Tests for GDPR action constants."""

    def test_valid_actions_defined(self) -> None:
        """Test all expected GDPR actions are defined."""
        expected = {
            "export_requested",
            "export_completed",
            "deletion_requested",
            "deletion_completed",
            "deletion_failed",
        }
        assert GDPR_ACTIONS == expected


class TestLogGdprEvent:
    """Tests for log_gdpr_event function."""

    @patch("backend.services.audit.db_session")
    def test_log_valid_action(self, mock_db_session: MagicMock) -> None:
        """Test logging a valid GDPR action."""
        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 123}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = log_gdpr_event(
            user_id="test-user",
            action="export_requested",
            details={"source": "api"},
            ip_address="192.168.1.1",
        )

        assert result == 123
        mock_cursor.execute.assert_called_once()

    def test_log_invalid_action(self) -> None:
        """Test that invalid actions are rejected."""
        result = log_gdpr_event(
            user_id="test-user",
            action="invalid_action",
        )
        assert result is None

    @patch("backend.services.audit.db_session")
    def test_log_db_error(self, mock_db_session: MagicMock) -> None:
        """Test graceful handling of database errors."""
        mock_db_session.side_effect = Exception("DB error")

        result = log_gdpr_event(
            user_id="test-user",
            action="export_requested",
        )
        assert result is None


class TestGetUserAuditLog:
    """Tests for get_user_audit_log function."""

    @patch("backend.services.audit.db_session")
    def test_get_audit_log_returns_list(self, mock_db_session: MagicMock) -> None:
        """Test audit log retrieval returns list."""
        from datetime import UTC, datetime

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "user_id": "test-user",
                "action": "export_requested",
                "details": None,
                "ip_address": "127.0.0.1",
                "created_at": datetime(2024, 1, 1, tzinfo=UTC),
            }
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_user_audit_log("test-user", limit=50)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["action"] == "export_requested"

    @patch("backend.services.audit.db_session")
    def test_get_audit_log_empty(self, mock_db_session: MagicMock) -> None:
        """Test empty audit log returns empty list."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_user_audit_log("no-logs-user")

        assert result == []


class TestGetRecentExportRequest:
    """Tests for get_recent_export_request function."""

    @patch("backend.services.audit.db_session")
    def test_recent_export_found(self, mock_db_session: MagicMock) -> None:
        """Test finding recent export request."""
        from datetime import UTC, datetime

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 5,
            "created_at": datetime(2024, 1, 15, tzinfo=UTC),
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_recent_export_request("test-user", window_hours=24)

        assert result is not None
        assert result["id"] == 5

    @patch("backend.services.audit.db_session")
    def test_no_recent_export(self, mock_db_session: MagicMock) -> None:
        """Test when no recent export exists."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_recent_export_request("test-user", window_hours=24)

        assert result is None


class TestGetRecentDeletionRequest:
    """Tests for get_recent_deletion_request function."""

    @patch("backend.services.audit.db_session")
    def test_recent_deletion_found(self, mock_db_session: MagicMock) -> None:
        """Test finding recent deletion request."""
        from datetime import UTC, datetime

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 10,
            "action": "deletion_requested",
            "created_at": datetime(2024, 1, 15, tzinfo=UTC),
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_recent_deletion_request("test-user", window_hours=24)

        assert result is not None
        assert result["action"] == "deletion_requested"

    @patch("backend.services.audit.db_session")
    def test_deletion_completed_detected(self, mock_db_session: MagicMock) -> None:
        """Test detecting completed deletion."""
        from datetime import UTC, datetime

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 11,
            "action": "deletion_completed",
            "created_at": datetime(2024, 1, 15, tzinfo=UTC),
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_recent_deletion_request("test-user", window_hours=24)

        assert result is not None
        assert result["action"] == "deletion_completed"
