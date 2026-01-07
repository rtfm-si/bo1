"""Tests for admin impersonation API endpoints.

Tests:
- POST /api/admin/impersonate/{user_id} - Start impersonation
- DELETE /api/admin/impersonate - End impersonation
- GET /api/admin/impersonate/status - Check impersonation status
- GET /api/admin/impersonate/history - Get impersonation audit log
- Security: write protection during impersonation
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.impersonation import router
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import limiter


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with impersonation router and admin auth override."""
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


class TestStartImpersonation:
    """Tests for POST /api/admin/impersonate/{user_id}."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.post(
            "/api/admin/impersonate/target-user-123",
            json={"reason": "Testing", "write_mode": False, "duration_minutes": 30},
        )
        assert response.status_code == 403

    def test_starts_impersonation_successfully(self, client: TestClient):
        """Admin should be able to start impersonation."""
        with (
            patch("backend.api.admin.impersonation.AdminQueryService") as mock_query_svc,
            patch("backend.api.admin.impersonation.start_impersonation") as mock_start,
            patch("backend.api.admin.impersonation.AdminUserService") as mock_user_svc,
        ):
            # Mock target user exists and is not admin
            mock_query_svc.user_exists.return_value = True
            mock_query_svc.get_user.return_value = MagicMock(is_admin=False)

            # Mock successful impersonation start
            now = datetime.now(UTC)
            mock_start.return_value = MagicMock(
                admin_user_id="admin-123",
                target_user_id="target-user-123",
                target_email="target@example.com",
                reason="Testing",
                is_write_mode=False,
                started_at=now,
                expires_at=now + timedelta(minutes=30),
            )

            response = client.post(
                "/api/admin/impersonate/target-user-123",
                json={"reason": "Testing", "write_mode": False, "duration_minutes": 30},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["target_user_id"] == "target-user-123"
            assert data["target_email"] == "target@example.com"
            assert data["is_write_mode"] is False
            assert data["remaining_seconds"] >= 0

            # Verify admin action was logged
            mock_user_svc.log_admin_action.assert_called_once()

    def test_cannot_impersonate_nonexistent_user(self, client: TestClient):
        """Should return 404 for non-existent user."""
        with patch("backend.api.admin.impersonation.AdminQueryService") as mock_query_svc:
            mock_query_svc.user_exists.return_value = False

            response = client.post(
                "/api/admin/impersonate/nonexistent-user",
                json={"reason": "Testing", "write_mode": False, "duration_minutes": 30},
            )

            assert response.status_code == 404
            detail = response.json()["detail"]
            message = detail["message"] if isinstance(detail, dict) else detail
            assert "not found" in message.lower()

    def test_cannot_impersonate_another_admin(self, client: TestClient):
        """Should return 400 when trying to impersonate another admin."""
        with patch("backend.api.admin.impersonation.AdminQueryService") as mock_query_svc:
            mock_query_svc.user_exists.return_value = True
            mock_query_svc.get_user.return_value = MagicMock(is_admin=True)

            response = client.post(
                "/api/admin/impersonate/other-admin-123",
                json={"reason": "Testing", "write_mode": False, "duration_minutes": 30},
            )

            assert response.status_code == 400
            detail = response.json()["detail"]
            message = detail["message"] if isinstance(detail, dict) else detail
            assert "admin" in message.lower()

    def test_cannot_impersonate_self(self, client: TestClient):
        """Should return 400 when trying to impersonate self."""
        response = client.post(
            "/api/admin/impersonate/admin-user-id",  # Same as mock_admin_override returns
            json={"reason": "Testing", "write_mode": False, "duration_minutes": 30},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        message = detail["message"] if isinstance(detail, dict) else detail
        assert "yourself" in message.lower()


class TestEndImpersonation:
    """Tests for DELETE /api/admin/impersonate."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.delete("/api/admin/impersonate")
        assert response.status_code == 403

    def test_ends_impersonation_successfully(self, client: TestClient):
        """Admin should be able to end impersonation."""
        with (
            patch("backend.api.admin.impersonation.get_active_impersonation") as mock_get,
            patch("backend.api.admin.impersonation.end_impersonation") as mock_end,
            patch("backend.api.admin.impersonation.AdminUserService") as mock_user_svc,
        ):
            # Mock active session exists
            mock_get.return_value = MagicMock(target_user_id="target-user-123")
            mock_end.return_value = True

            response = client.delete("/api/admin/impersonate")

            assert response.status_code == 200
            data = response.json()
            assert data["ended"] is True
            assert "ended" in data["message"].lower()

            # Verify admin action was logged
            mock_user_svc.log_admin_action.assert_called_once()

    def test_no_active_session(self, client: TestClient):
        """Should handle case when no active impersonation."""
        with (
            patch("backend.api.admin.impersonation.get_active_impersonation") as mock_get,
            patch("backend.api.admin.impersonation.end_impersonation") as mock_end,
        ):
            mock_get.return_value = None
            mock_end.return_value = False

            response = client.delete("/api/admin/impersonate")

            assert response.status_code == 200
            data = response.json()
            assert data["ended"] is False


class TestImpersonationStatus:
    """Tests for GET /api/admin/impersonate/status."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/impersonate/status")
        assert response.status_code == 403

    def test_returns_active_session(self, client: TestClient):
        """Should return active impersonation session details."""
        with patch("backend.api.admin.impersonation.get_active_impersonation") as mock_get:
            now = datetime.now(UTC)
            mock_get.return_value = MagicMock(
                admin_user_id="admin-123",
                target_user_id="target-user-123",
                target_email="target@example.com",
                reason="Testing",
                is_write_mode=False,
                started_at=now,
                expires_at=now + timedelta(minutes=30),
            )

            response = client.get("/api/admin/impersonate/status")

            assert response.status_code == 200
            data = response.json()
            assert data["is_impersonating"] is True
            assert data["session"]["target_user_id"] == "target-user-123"
            assert data["session"]["target_email"] == "target@example.com"

    def test_returns_no_active_session(self, client: TestClient):
        """Should return is_impersonating=False when no active session."""
        with patch("backend.api.admin.impersonation.get_active_impersonation") as mock_get:
            mock_get.return_value = None

            response = client.get("/api/admin/impersonate/status")

            assert response.status_code == 200
            data = response.json()
            assert data["is_impersonating"] is False
            assert data["session"] is None


class TestImpersonationHistory:
    """Tests for GET /api/admin/impersonate/history."""

    def test_requires_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/impersonate/history")
        assert response.status_code == 403

    def test_returns_history(self, client: TestClient):
        """Should return impersonation audit history."""
        with patch("backend.api.admin.impersonation.get_impersonation_history") as mock_history:
            now = datetime.now(UTC)
            mock_history.return_value = [
                {
                    "id": 1,
                    "admin_user_id": "admin-123",
                    "admin_email": "admin@example.com",
                    "target_user_id": "user-123",
                    "target_email": "user@example.com",
                    "reason": "Bug investigation",
                    "is_write_mode": False,
                    "started_at": now - timedelta(hours=2),
                    "expires_at": now - timedelta(hours=1, minutes=30),
                    "ended_at": now - timedelta(hours=1, minutes=45),
                },
                {
                    "id": 2,
                    "admin_user_id": "admin-456",
                    "admin_email": "admin2@example.com",
                    "target_user_id": "user-456",
                    "target_email": "user2@example.com",
                    "reason": "Support ticket",
                    "is_write_mode": True,
                    "started_at": now - timedelta(hours=1),
                    "expires_at": now - timedelta(minutes=30),
                    "ended_at": None,
                },
            ]

            response = client.get("/api/admin/impersonate/history")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["sessions"]) == 2
            assert data["sessions"][0]["admin_email"] == "admin@example.com"
            assert data["sessions"][0]["target_email"] == "user@example.com"

    def test_filters_by_admin_user_id(self, client: TestClient):
        """Should filter history by admin_user_id."""
        with patch("backend.api.admin.impersonation.get_impersonation_history") as mock_history:
            mock_history.return_value = []

            response = client.get("/api/admin/impersonate/history?admin_user_id=admin-123")

            assert response.status_code == 200
            mock_history.assert_called_once_with(
                admin_id="admin-123", target_user_id=None, limit=50
            )


class TestImpersonationService:
    """Tests for impersonation service functions."""

    def test_start_impersonation_creates_session(self):
        """Should create impersonation session in Redis and DB."""
        from backend.services.admin_impersonation import start_impersonation

        with (
            patch("backend.services.admin_impersonation.db_session") as mock_db_session,
            patch("backend.services.admin_impersonation._get_redis") as mock_get_redis,
        ):
            # Mock DB
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # First query returns target user email, second returns session ID
            mock_cursor.fetchone.side_effect = [
                {"email": "target@example.com"},  # Target user query
                {"id": 1},  # Insert returning ID
            ]

            # Mock Redis
            mock_redis_manager = MagicMock()
            mock_redis_manager.is_available = True
            mock_redis_manager.redis = MagicMock()
            mock_get_redis.return_value = mock_redis_manager

            result = start_impersonation(
                admin_id="admin-123",
                target_user_id="target-user-123",
                reason="Testing",
                write_mode=False,
                duration_minutes=30,
            )

            assert result is not None
            assert result.admin_user_id == "admin-123"
            assert result.target_user_id == "target-user-123"
            assert result.target_email == "target@example.com"
            assert result.is_write_mode is False

            # Verify Redis was updated
            mock_redis_manager.redis.setex.assert_called_once()

    def test_end_impersonation_clears_session(self):
        """Should clear impersonation session from Redis and DB."""
        from backend.services.admin_impersonation import end_impersonation

        with (
            patch("backend.services.admin_impersonation.db_session") as mock_db_session,
            patch("backend.services.admin_impersonation._get_redis") as mock_get_redis,
        ):
            # Mock DB
            mock_cursor = MagicMock()
            mock_cursor.rowcount = 1  # Indicates session was ended
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Mock Redis
            mock_redis_manager = MagicMock()
            mock_redis_manager.is_available = True
            mock_redis_manager.redis = MagicMock()
            mock_get_redis.return_value = mock_redis_manager

            result = end_impersonation("admin-123")

            assert result is True

            # Verify Redis key was deleted
            mock_redis_manager.redis.delete.assert_called_once_with("impersonation:admin-123")

    def test_get_active_impersonation_from_redis(self):
        """Should get active session from Redis cache."""
        import json

        from backend.services.admin_impersonation import get_active_impersonation

        with patch("backend.services.admin_impersonation._get_redis") as mock_get_redis:
            now = datetime.now(UTC)
            session_data = {
                "admin_user_id": "admin-123",
                "target_user_id": "target-123",
                "target_email": "target@example.com",
                "reason": "Testing",
                "is_write_mode": False,
                "started_at": now.isoformat(),
                "expires_at": (now + timedelta(minutes=30)).isoformat(),
                "session_id": 1,
            }

            mock_redis_manager = MagicMock()
            mock_redis_manager.is_available = True
            mock_redis_manager.redis = MagicMock()
            mock_redis_manager.redis.get.return_value = json.dumps(session_data)
            mock_get_redis.return_value = mock_redis_manager

            result = get_active_impersonation("admin-123")

            assert result is not None
            assert result.admin_user_id == "admin-123"
            assert result.target_user_id == "target-123"
            assert result.target_email == "target@example.com"


class TestImpersonationMiddleware:
    """Tests for impersonation middleware behavior."""

    def test_get_effective_user_id_during_impersonation(self):
        """get_effective_user_id should return target user during impersonation."""
        from backend.api.middleware.impersonation import get_effective_user_id

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_target_id = "target-user-123"
        request.state.user_id = "admin-123"

        result = get_effective_user_id(request)
        assert result == "target-user-123"

    def test_get_effective_user_id_without_impersonation(self):
        """get_effective_user_id should return actual user when not impersonating."""
        from backend.api.middleware.impersonation import get_effective_user_id

        request = MagicMock()
        request.state.is_impersonation = False
        request.state.user_id = "user-123"

        result = get_effective_user_id(request)
        assert result == "user-123"

    def test_is_impersonating_helper(self):
        """is_impersonating should return correct state."""
        from backend.api.middleware.impersonation import is_impersonating

        request_impersonating = MagicMock()
        request_impersonating.state.is_impersonation = True

        request_normal = MagicMock()
        request_normal.state.is_impersonation = False

        assert is_impersonating(request_impersonating) is True
        assert is_impersonating(request_normal) is False

    def test_get_real_admin_id_during_impersonation(self):
        """get_real_admin_id should return admin ID during impersonation."""
        from backend.api.middleware.impersonation import get_real_admin_id

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_admin_id = "admin-123"

        result = get_real_admin_id(request)
        assert result == "admin-123"

    def test_get_real_admin_id_without_impersonation(self):
        """get_real_admin_id should return None when not impersonating."""
        from backend.api.middleware.impersonation import get_real_admin_id

        request = MagicMock()
        request.state.is_impersonation = False

        result = get_real_admin_id(request)
        assert result is None

    def test_get_impersonation_context_during_impersonation(self):
        """get_impersonation_context should return full context when impersonating."""
        from backend.api.middleware.impersonation import get_impersonation_context

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_admin_id = "admin-123"
        request.state.impersonation_target_id = "target-123"
        request.state.impersonation_write_mode = False

        result = get_impersonation_context(request)

        assert result is not None
        assert result["is_impersonation"] is True
        assert result["admin_id"] == "admin-123"
        assert result["target_id"] == "target-123"
        assert result["write_mode"] is False

    def test_get_impersonation_context_without_impersonation(self):
        """get_impersonation_context should return None when not impersonating."""
        from backend.api.middleware.impersonation import get_impersonation_context

        request = MagicMock()
        request.state.is_impersonation = False

        result = get_impersonation_context(request)
        assert result is None
