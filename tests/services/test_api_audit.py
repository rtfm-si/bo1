"""Tests for API audit logging service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backend.services.api_audit import (
    DEFAULT_RETENTION_DAYS,
    cleanup_old_logs,
    get_request_stats,
    get_user_requests,
    log_api_request,
)


class TestLogApiRequest:
    """Tests for log_api_request function."""

    @patch("backend.services.api_audit.db_session")
    def test_log_request_success(self, mock_db_session: MagicMock) -> None:
        """Test logging an API request successfully."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 42}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = log_api_request(
            method="GET",
            path="/api/v1/sessions",
            status_code=200,
            duration_ms=150,
            user_id="user-123",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            request_id="req-abc-123",
        )

        assert result == 42
        mock_cursor.execute.assert_called_once()

        # Verify SQL params
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert params[0] == "GET"
        assert params[1] == "/api/v1/sessions"
        assert params[2] == "user-123"
        assert params[3] == 200
        assert params[4] == 150

    @patch("backend.services.api_audit.db_session")
    def test_log_request_without_user(self, mock_db_session: MagicMock) -> None:
        """Test logging request without authenticated user."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 43}
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = log_api_request(
            method="GET",
            path="/api/health",
            status_code=200,
            duration_ms=5,
        )

        assert result == 43

    @patch("backend.services.api_audit.db_session")
    def test_log_request_db_error(self, mock_db_session: MagicMock) -> None:
        """Test graceful handling of database errors."""
        mock_db_session.side_effect = Exception("Connection error")

        result = log_api_request(
            method="GET",
            path="/api/v1/sessions",
            status_code=200,
            duration_ms=100,
        )

        assert result is None


class TestGetUserRequests:
    """Tests for get_user_requests function."""

    @patch("backend.services.api_audit.db_session")
    def test_get_requests_success(self, mock_db_session: MagicMock) -> None:
        """Test retrieving user requests."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "timestamp": datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
                "method": "GET",
                "path": "/api/v1/sessions",
                "status_code": 200,
                "duration_ms": 100,
                "ip_address": "192.168.1.1",
                "user_agent": "test-agent",
                "request_id": "req-1",
            },
            {
                "id": 2,
                "timestamp": datetime(2024, 1, 15, 10, 31, tzinfo=UTC),
                "method": "POST",
                "path": "/api/v1/sessions",
                "status_code": 201,
                "duration_ms": 250,
                "ip_address": "192.168.1.1",
                "user_agent": "test-agent",
                "request_id": "req-2",
            },
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_user_requests("user-123", limit=50, offset=0)

        assert len(result) == 2
        assert result[0]["method"] == "GET"
        assert result[1]["method"] == "POST"

    @patch("backend.services.api_audit.db_session")
    def test_get_requests_empty(self, mock_db_session: MagicMock) -> None:
        """Test empty result for user with no requests."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_user_requests("no-requests-user")

        assert result == []


class TestCleanupOldLogs:
    """Tests for cleanup_old_logs function."""

    def test_default_retention_days(self) -> None:
        """Test default retention period is defined."""
        assert DEFAULT_RETENTION_DAYS == 30

    @patch("backend.services.api_audit.db_session")
    def test_cleanup_success(self, mock_db_session: MagicMock) -> None:
        """Test successful cleanup of old logs."""
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1500
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = cleanup_old_logs(retention_days=30)

        assert result["deleted"] == 1500
        assert result["errors"] == 0

    @patch("backend.services.api_audit.db_session")
    def test_cleanup_db_error(self, mock_db_session: MagicMock) -> None:
        """Test cleanup handles database errors gracefully."""
        mock_db_session.side_effect = Exception("DB connection lost")

        result = cleanup_old_logs(retention_days=30)

        assert result["deleted"] == 0
        assert result["errors"] == 1


class TestGetRequestStats:
    """Tests for get_request_stats function."""

    @patch("backend.services.api_audit.db_session")
    def test_get_stats_success(self, mock_db_session: MagicMock) -> None:
        """Test retrieving request statistics."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "total_requests": 10000,
            "unique_users": 150,
            "avg_duration_ms": 120,
            "max_duration_ms": 5000,
            "error_count": 50,
            "server_error_count": 5,
        }
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = get_request_stats(hours=24)

        assert result["total_requests"] == 10000
        assert result["unique_users"] == 150
        assert result["error_count"] == 50

    @patch("backend.services.api_audit.db_session")
    def test_get_stats_db_error(self, mock_db_session: MagicMock) -> None:
        """Test stats handles database errors gracefully."""
        mock_db_session.side_effect = Exception("Query timeout")

        result = get_request_stats(hours=24)

        assert result == {}
