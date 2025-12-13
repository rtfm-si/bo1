"""Tests for admin impersonation functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from backend.services.admin_impersonation import (
    end_impersonation,
    get_active_impersonation,
    get_impersonation_history,
    is_impersonating,
    start_impersonation,
)


class TestImpersonationService:
    """Tests for admin impersonation service."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock db_session context manager."""
        with patch("backend.services.admin_impersonation.db_session") as mock:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock.return_value = mock_conn
            yield mock, mock_cursor

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis manager."""
        with patch("backend.services.admin_impersonation._get_redis") as mock:
            redis_manager = MagicMock()
            redis_manager.is_available = True
            redis_manager.redis = MagicMock()
            mock.return_value = redis_manager
            yield redis_manager

    def test_start_impersonation_success(self, mock_db_session, mock_redis):
        """Test starting an impersonation session."""
        mock, cursor = mock_db_session

        # Mock user exists check
        cursor.fetchone.side_effect = [
            {"email": "target@example.com"},  # Target user lookup
            {"id": 1},  # Session ID from INSERT
        ]

        session = start_impersonation(
            admin_id="admin_123",
            target_user_id="user_456",
            reason="Investigating bug report",
            write_mode=False,
            duration_minutes=30,
        )

        assert session is not None
        assert session.admin_user_id == "admin_123"
        assert session.target_user_id == "user_456"
        assert session.target_email == "target@example.com"
        assert session.reason == "Investigating bug report"
        assert session.is_write_mode is False
        assert session.session_id == 1

        # Verify Redis was called to store session
        mock_redis.redis.setex.assert_called_once()

    def test_start_impersonation_target_not_found(self, mock_db_session, mock_redis):
        """Test starting impersonation for non-existent user."""
        mock, cursor = mock_db_session
        cursor.fetchone.return_value = None  # User not found

        session = start_impersonation(
            admin_id="admin_123",
            target_user_id="nonexistent",
            reason="Test",
        )

        assert session is None

    def test_end_impersonation_success(self, mock_db_session, mock_redis):
        """Test ending an impersonation session."""
        mock, cursor = mock_db_session
        cursor.rowcount = 1  # One row updated

        result = end_impersonation("admin_123")

        assert result is True
        mock_redis.redis.delete.assert_called_once()

    def test_end_impersonation_no_active_session(self, mock_db_session, mock_redis):
        """Test ending when no active session."""
        mock, cursor = mock_db_session
        cursor.rowcount = 0  # No rows updated

        result = end_impersonation("admin_123")

        assert result is False

    def test_get_active_impersonation_from_redis(self, mock_db_session, mock_redis):
        """Test getting active session from Redis cache."""
        import json

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=15)
        session_data = {
            "admin_user_id": "admin_123",
            "target_user_id": "user_456",
            "target_email": "target@example.com",
            "reason": "Testing",
            "is_write_mode": False,
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "session_id": 1,
        }
        mock_redis.redis.get.return_value = json.dumps(session_data)

        session = get_active_impersonation("admin_123")

        assert session is not None
        assert session.admin_user_id == "admin_123"
        assert session.target_user_id == "user_456"
        assert session.target_email == "target@example.com"

    def test_get_active_impersonation_expired(self, mock_db_session, mock_redis):
        """Test getting expired session from Redis returns None."""
        import json

        now = datetime.now(UTC)
        expires_at = now - timedelta(minutes=5)  # Expired
        session_data = {
            "admin_user_id": "admin_123",
            "target_user_id": "user_456",
            "target_email": "target@example.com",
            "reason": "Testing",
            "is_write_mode": False,
            "started_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": expires_at.isoformat(),
            "session_id": 1,
        }
        mock_redis.redis.get.return_value = json.dumps(session_data)

        # Should fall back to DB, mock DB returns nothing
        mock, cursor = mock_db_session
        cursor.fetchone.return_value = None

        session = get_active_impersonation("admin_123")

        assert session is None

    def test_is_impersonating_true(self, mock_db_session, mock_redis):
        """Test is_impersonating returns True when session active."""
        import json

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=15)
        session_data = {
            "admin_user_id": "admin_123",
            "target_user_id": "user_456",
            "target_email": "target@example.com",
            "reason": "Testing",
            "is_write_mode": False,
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "session_id": 1,
        }
        mock_redis.redis.get.return_value = json.dumps(session_data)

        result = is_impersonating("admin_123")

        assert result is True

    def test_is_impersonating_false(self, mock_db_session, mock_redis):
        """Test is_impersonating returns False when no session."""
        mock_redis.redis.get.return_value = None
        mock, cursor = mock_db_session
        cursor.fetchone.return_value = None

        result = is_impersonating("admin_123")

        assert result is False

    def test_get_impersonation_history(self, mock_db_session, mock_redis):
        """Test getting impersonation history."""
        mock, cursor = mock_db_session
        now = datetime.now(UTC)
        cursor.fetchall.return_value = [
            {
                "id": 1,
                "admin_user_id": "admin_123",
                "target_user_id": "user_456",
                "reason": "Bug investigation",
                "is_write_mode": False,
                "started_at": now,
                "expires_at": now + timedelta(minutes=30),
                "ended_at": now + timedelta(minutes=15),
                "admin_email": "admin@example.com",
                "target_email": "user@example.com",
            }
        ]

        history = get_impersonation_history(admin_id="admin_123", limit=50)

        assert len(history) == 1
        assert history[0]["admin_user_id"] == "admin_123"
        assert history[0]["target_user_id"] == "user_456"
        assert history[0]["admin_email"] == "admin@example.com"


class TestImpersonationMiddleware:
    """Tests for impersonation middleware."""

    def test_get_effective_user_id_impersonating(self):
        """Test effective user ID when impersonating."""
        from backend.api.middleware.impersonation import get_effective_user_id

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_target_id = "user_456"
        request.state.user_id = "admin_123"

        result = get_effective_user_id(request)

        assert result == "user_456"

    def test_get_effective_user_id_not_impersonating(self):
        """Test effective user ID when not impersonating."""
        from backend.api.middleware.impersonation import get_effective_user_id

        request = MagicMock()
        request.state.is_impersonation = False
        request.state.user_id = "admin_123"

        result = get_effective_user_id(request)

        assert result == "admin_123"

    def test_get_real_admin_id_impersonating(self):
        """Test getting real admin ID during impersonation."""
        from backend.api.middleware.impersonation import get_real_admin_id

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_admin_id = "admin_123"

        result = get_real_admin_id(request)

        assert result == "admin_123"

    def test_get_real_admin_id_not_impersonating(self):
        """Test getting real admin ID when not impersonating returns None."""
        from backend.api.middleware.impersonation import get_real_admin_id

        request = MagicMock()
        request.state.is_impersonation = False

        result = get_real_admin_id(request)

        assert result is None

    def test_is_impersonating_function(self):
        """Test is_impersonating function."""
        from backend.api.middleware.impersonation import is_impersonating

        request_impersonating = MagicMock()
        request_impersonating.state.is_impersonation = True

        request_not_impersonating = MagicMock()
        request_not_impersonating.state.is_impersonation = False

        assert is_impersonating(request_impersonating) is True
        assert is_impersonating(request_not_impersonating) is False

    def test_require_write_mode_read_only(self):
        """Test require_write_mode raises in read-only mode."""
        from fastapi import HTTPException

        from backend.api.middleware.impersonation import require_write_mode

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_write_mode = False

        with pytest.raises(HTTPException) as exc_info:
            require_write_mode(request)

        assert exc_info.value.status_code == 403

    def test_require_write_mode_write_allowed(self):
        """Test require_write_mode passes in write mode."""
        from backend.api.middleware.impersonation import require_write_mode

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_write_mode = True

        # Should not raise
        require_write_mode(request)

    def test_get_impersonation_context(self):
        """Test getting full impersonation context."""
        from backend.api.middleware.impersonation import get_impersonation_context

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_admin_id = "admin_123"
        request.state.impersonation_target_id = "user_456"
        request.state.impersonation_write_mode = False

        context = get_impersonation_context(request)

        assert context is not None
        assert context["is_impersonation"] is True
        assert context["admin_id"] == "admin_123"
        assert context["target_id"] == "user_456"
        assert context["write_mode"] is False

    def test_get_impersonation_context_not_impersonating(self):
        """Test impersonation context is None when not impersonating."""
        from backend.api.middleware.impersonation import get_impersonation_context

        request = MagicMock()
        request.state.is_impersonation = False

        context = get_impersonation_context(request)

        assert context is None
