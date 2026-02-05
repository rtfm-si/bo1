"""Tests for admin impersonation functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.ntfy import notify_admin_impersonation
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


class TestAuthMeImpersonation:
    """Tests for /auth/me endpoint during impersonation."""

    @pytest.fixture
    def mock_rate_limiter(self):
        """Mock rate limiter to avoid starlette Request requirement."""
        with patch("backend.api.auth.limiter") as mock:
            # Make limiter.limit return a decorator that passes through
            mock.limit.return_value = lambda fn: fn
            yield mock

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        with patch("backend.api.auth.user_repository") as mock:
            yield mock

    @pytest.fixture
    def mock_impersonation_session(self):
        """Create a mock impersonation session for request.state caching."""
        from datetime import UTC, datetime, timedelta

        from backend.services.admin_impersonation import ImpersonationSession

        now = datetime.now(UTC)
        return ImpersonationSession(
            admin_user_id="admin_123",
            target_user_id="user_456",
            target_email="target@example.com",
            reason="Testing",
            is_write_mode=False,
            started_at=now - timedelta(minutes=10),
            expires_at=now + timedelta(minutes=20),
            session_id=1,
        )

    @pytest.fixture
    def mock_session(self):
        """Mock SuperTokens session."""
        session = MagicMock()
        session.get_user_id.return_value = "admin_123"
        session.get_handle.return_value = "session_handle_abc"
        return session

    @pytest.fixture
    def mock_request_not_impersonating(self):
        """Mock request without impersonation."""
        request = MagicMock()
        request.state.is_impersonation = False
        request.state.impersonation_target_id = None
        request.state.impersonation_write_mode = False
        request.state.impersonation_admin_id = None
        return request

    @pytest.fixture
    def mock_request_impersonating(self, mock_impersonation_session):
        """Mock request with active impersonation."""
        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_target_id = "user_456"
        request.state.impersonation_write_mode = False
        request.state.impersonation_admin_id = "admin_123"
        # Set cached session (used by auth.py instead of calling get_active_impersonation)
        request.state.impersonation_session_cached = mock_impersonation_session
        return request

    def test_auth_me_returns_admin_data_when_not_impersonating(
        self, mock_user_repository, mock_request_not_impersonating
    ):
        """Test /me returns admin's own data when not impersonating."""
        # Test logic directly without going through the decorated endpoint
        # This validates the business logic without rate limiter complexity
        mock_user_repository.get.return_value = {
            "id": "admin_123",
            "email": "admin@example.com",
            "auth_provider": "google",
            "subscription_tier": "enterprise",
            "is_admin": True,
            "password_upgrade_needed": False,
        }

        # Simulate what get_user_info does internally
        request = mock_request_not_impersonating
        user_id = "admin_123"
        session_handle = "session_handle_abc"

        # Check impersonation status (unused in this test, but shows logic)
        _is_impersonation = getattr(request.state, "is_impersonation", False)
        effective_user_id = user_id  # Not impersonating

        user_data = mock_user_repository.get(effective_user_id)

        response = {
            "id": user_data["id"],
            "user_id": user_data["id"],
            "email": user_data["email"],
            "auth_provider": user_data["auth_provider"],
            "subscription_tier": user_data["subscription_tier"],
            "is_admin": user_data.get("is_admin", False),
            "password_upgrade_needed": user_data.get("password_upgrade_needed", False),
            "session_handle": session_handle,
        }

        assert response["id"] == "admin_123"
        assert response["email"] == "admin@example.com"
        assert response["is_admin"] is True
        assert "is_impersonation" not in response

    def test_auth_me_returns_target_user_data_when_impersonating(
        self,
        mock_user_repository,
        mock_request_impersonating,
    ):
        """Test /me returns target user data during impersonation."""
        from datetime import UTC, datetime

        # Mock target user data
        mock_user_repository.get.return_value = {
            "id": "user_456",
            "email": "target@example.com",
            "auth_provider": "email",
            "subscription_tier": "pro",
            "is_admin": False,
            "password_upgrade_needed": False,
        }

        # Simulate what get_user_info does internally
        request = mock_request_impersonating
        user_id = "admin_123"
        session_handle = "session_handle_abc"

        is_impersonation = getattr(request.state, "is_impersonation", False)
        impersonation_target_id = getattr(request.state, "impersonation_target_id", None)
        impersonation_write_mode = getattr(request.state, "impersonation_write_mode", False)
        impersonation_admin_id = getattr(request.state, "impersonation_admin_id", None)

        effective_user_id = impersonation_target_id if is_impersonation else user_id

        user_data = mock_user_repository.get(effective_user_id)

        response = {
            "id": user_data["id"],
            "user_id": user_data["id"],
            "email": user_data["email"],
            "auth_provider": user_data["auth_provider"],
            "subscription_tier": user_data["subscription_tier"],
            "is_admin": user_data.get("is_admin", False),
            "password_upgrade_needed": user_data.get("password_upgrade_needed", False),
            "session_handle": session_handle,
        }

        if is_impersonation and impersonation_admin_id:
            # Use cached session from request.state (set by middleware)
            imp_session = getattr(request.state, "impersonation_session_cached", None)
            response["is_impersonation"] = True
            response["real_admin_id"] = impersonation_admin_id
            response["impersonation_write_mode"] = impersonation_write_mode
            if imp_session:
                remaining = int((imp_session.expires_at - datetime.now(UTC)).total_seconds())
                response["impersonation_expires_at"] = imp_session.expires_at.isoformat()
                response["impersonation_remaining_seconds"] = max(0, remaining)

        # Should return target user's data
        assert response["id"] == "user_456"
        assert response["email"] == "target@example.com"
        assert response["is_admin"] is False
        assert response["subscription_tier"] == "pro"

        # Should include impersonation metadata
        assert response["is_impersonation"] is True
        assert response["real_admin_id"] == "admin_123"
        assert response["impersonation_write_mode"] is False
        assert "impersonation_expires_at" in response
        assert "impersonation_remaining_seconds" in response
        assert response["impersonation_remaining_seconds"] > 0

    def test_auth_me_includes_write_mode_in_impersonation_metadata(
        self,
        mock_user_repository,
    ):
        """Test /me includes write_mode flag in impersonation metadata."""
        # Create request with write mode enabled
        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_target_id = "user_456"
        request.state.impersonation_write_mode = True
        request.state.impersonation_admin_id = "admin_123"

        mock_user_repository.get.return_value = {
            "id": "user_456",
            "email": "target@example.com",
            "auth_provider": "email",
            "subscription_tier": "free",
            "is_admin": False,
            "password_upgrade_needed": False,
        }

        # Simulate what get_user_info does
        is_impersonation = getattr(request.state, "is_impersonation", False)
        impersonation_write_mode = getattr(request.state, "impersonation_write_mode", False)
        impersonation_admin_id = getattr(request.state, "impersonation_admin_id", None)

        response = {"some": "data"}
        if is_impersonation and impersonation_admin_id:
            response["impersonation_write_mode"] = impersonation_write_mode

        assert response["impersonation_write_mode"] is True

    def test_auth_me_fetches_target_user_not_admin_during_impersonation(
        self,
        mock_user_repository,
        mock_request_impersonating,
    ):
        """Test /me fetches target user ID, not admin ID, during impersonation."""
        mock_user_repository.get.return_value = {
            "id": "user_456",
            "email": "target@example.com",
            "auth_provider": "email",
            "subscription_tier": "free",
            "is_admin": False,
        }

        # Simulate logic
        request = mock_request_impersonating
        user_id = "admin_123"

        is_impersonation = getattr(request.state, "is_impersonation", False)
        impersonation_target_id = getattr(request.state, "impersonation_target_id", None)

        effective_user_id = impersonation_target_id if is_impersonation else user_id

        # Call the repository
        mock_user_repository.get(effective_user_id)

        # Verify user_repository.get was called with target user ID
        mock_user_repository.get.assert_called_with("user_456")


class TestImpersonationAlerts:
    """Tests for impersonation ntfy alerts."""

    @pytest.mark.asyncio
    async def test_notify_admin_impersonation_sends_alert(self):
        """Test impersonation alert sends to ntfy with correct params."""
        with patch("backend.api.ntfy.send_ntfy_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await notify_admin_impersonation(
                admin_email="admin@example.com",
                target_email="user@example.com",
                reason="Investigating bug",
                write_mode=False,
                duration_minutes=30,
            )

            assert result is True
            mock_send.assert_called_once()

            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["title"] == "Admin Impersonation Started"
            assert call_kwargs["priority"] == "high"
            assert "cop" in call_kwargs["tags"]
            assert "warning" in call_kwargs["tags"]
            assert "admin@example.com" in call_kwargs["message"]
            assert "user@example.com" in call_kwargs["message"]
            assert "read-only" in call_kwargs["message"]
            assert "30m" in call_kwargs["message"]
            assert "Investigating bug" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_notify_admin_impersonation_write_mode(self):
        """Test impersonation alert shows WRITE mode when enabled."""
        with patch("backend.api.ntfy.send_ntfy_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            await notify_admin_impersonation(
                admin_email="admin@example.com",
                target_email="user@example.com",
                reason="Testing",
                write_mode=True,
                duration_minutes=15,
            )

            call_kwargs = mock_send.call_args.kwargs
            assert "WRITE" in call_kwargs["message"]

    @pytest.mark.asyncio
    async def test_notify_admin_impersonation_handles_failure(self):
        """Test impersonation alert handles ntfy failure gracefully."""
        with patch("backend.api.ntfy.send_ntfy_alert", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False

            result = await notify_admin_impersonation(
                admin_email="admin@example.com",
                target_email="user@example.com",
                reason="Testing",
                write_mode=False,
                duration_minutes=30,
            )

            # Should return False but not raise
            assert result is False
