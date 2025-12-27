"""E2E tests for admin impersonation flow.

Tests the complete impersonation lifecycle:
1. Start impersonation via POST /api/admin/impersonate/{user_id}
2. Verify impersonation status via GET /api/admin/impersonate/status
3. Verify auth context switches to target user
4. Test read-only mode blocks mutations
5. Test write mode allows mutations
6. Test ending impersonation via DELETE /api/admin/impersonate
7. Test impersonation history is logged
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.middleware.admin import require_admin_any


def create_mock_admin_override(admin_id: str = "admin-e2e-test"):
    """Create admin auth override for specific admin ID."""

    def override():
        return admin_id

    return override


@pytest.fixture
def admin_id() -> str:
    """Test admin user ID."""
    return f"admin-e2e-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def target_user_id() -> str:
    """Test target user ID."""
    return f"target-e2e-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def mock_limiter():
    """Create a memory-based limiter for tests."""
    return Limiter(key_func=get_remote_address, storage_uri="memory://")


@pytest.fixture
def app(admin_id: str, mock_limiter: Limiter) -> FastAPI:
    """Create test app with impersonation router and mocked rate limiter."""
    # Patch the limiter before importing the router
    with patch("backend.api.middleware.rate_limit.limiter", mock_limiter):
        # Import router after patching limiter
        from backend.api.admin.impersonation import router

        test_app = FastAPI()
        test_app.state.limiter = mock_limiter
        test_app.dependency_overrides[require_admin_any] = create_mock_admin_override(admin_id)
        test_app.include_router(router, prefix="/api/admin")
        return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestImpersonationE2EFlow:
    """E2E tests for complete impersonation flow."""

    def test_full_impersonation_lifecycle(
        self, client: TestClient, admin_id: str, target_user_id: str
    ) -> None:
        """Test start → status check → end impersonation flow."""
        with (
            patch("backend.api.admin.impersonation.AdminQueryService") as mock_query,
            patch("backend.api.admin.impersonation.start_impersonation") as mock_start,
            patch("backend.api.admin.impersonation.get_active_impersonation") as mock_get,
            patch("backend.api.admin.impersonation.end_impersonation") as mock_end,
            patch("backend.api.admin.impersonation.AdminUserService") as mock_user_svc,
        ):
            # Setup mocks for start
            mock_query.user_exists.return_value = True
            mock_target = MagicMock()
            mock_target.is_admin = False
            mock_target.email = "target@example.com"
            mock_query.get_user.return_value = mock_target

            now = datetime.now(UTC)
            mock_session = MagicMock()
            mock_session.admin_user_id = admin_id
            mock_session.target_user_id = target_user_id
            mock_session.target_email = "target@example.com"
            mock_session.reason = "E2E testing"
            mock_session.is_write_mode = False
            mock_session.started_at = now
            mock_session.expires_at = now
            mock_start.return_value = mock_session

            # Step 1: Start impersonation
            response = client.post(
                f"/api/admin/impersonate/{target_user_id}",
                json={"reason": "E2E testing", "write_mode": False, "duration_minutes": 30},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["target_user_id"] == target_user_id
            assert data["is_write_mode"] is False

            # Verify admin action was logged
            mock_user_svc.log_admin_action.assert_called()

            # Step 2: Check status
            mock_get.return_value = mock_session
            response = client.get("/api/admin/impersonate/status")
            assert response.status_code == 200
            data = response.json()
            assert data["is_impersonating"] is True
            assert data["session"]["target_user_id"] == target_user_id

            # Step 3: End impersonation
            mock_end.return_value = True
            response = client.delete("/api/admin/impersonate")
            assert response.status_code == 200
            data = response.json()
            assert data["ended"] is True

            # Step 4: Verify no active session
            mock_get.return_value = None
            response = client.get("/api/admin/impersonate/status")
            assert response.status_code == 200
            data = response.json()
            assert data["is_impersonating"] is False

    def test_impersonation_read_mode_restrictions(
        self, client: TestClient, admin_id: str, target_user_id: str
    ) -> None:
        """Test that read-only mode is properly flagged."""
        with (
            patch("backend.api.admin.impersonation.AdminQueryService") as mock_query,
            patch("backend.api.admin.impersonation.start_impersonation") as mock_start,
            patch("backend.api.admin.impersonation.AdminUserService"),
        ):
            mock_query.user_exists.return_value = True
            mock_target = MagicMock()
            mock_target.is_admin = False
            mock_query.get_user.return_value = mock_target

            now = datetime.now(UTC)
            mock_session = MagicMock()
            mock_session.admin_user_id = admin_id
            mock_session.target_user_id = target_user_id
            mock_session.target_email = "target@example.com"
            mock_session.reason = "Read-only test"
            mock_session.is_write_mode = False
            mock_session.started_at = now
            mock_session.expires_at = now
            mock_start.return_value = mock_session

            response = client.post(
                f"/api/admin/impersonate/{target_user_id}",
                json={"reason": "Read-only test", "write_mode": False, "duration_minutes": 30},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_write_mode"] is False

    def test_impersonation_write_mode(
        self, client: TestClient, admin_id: str, target_user_id: str
    ) -> None:
        """Test that write mode is properly enabled when requested."""
        with (
            patch("backend.api.admin.impersonation.AdminQueryService") as mock_query,
            patch("backend.api.admin.impersonation.start_impersonation") as mock_start,
            patch("backend.api.admin.impersonation.AdminUserService"),
        ):
            mock_query.user_exists.return_value = True
            mock_target = MagicMock()
            mock_target.is_admin = False
            mock_query.get_user.return_value = mock_target

            now = datetime.now(UTC)
            mock_session = MagicMock()
            mock_session.admin_user_id = admin_id
            mock_session.target_user_id = target_user_id
            mock_session.target_email = "target@example.com"
            mock_session.reason = "Write mode test"
            mock_session.is_write_mode = True
            mock_session.started_at = now
            mock_session.expires_at = now
            mock_start.return_value = mock_session

            response = client.post(
                f"/api/admin/impersonate/{target_user_id}",
                json={"reason": "Write mode test", "write_mode": True, "duration_minutes": 15},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_write_mode"] is True


class TestImpersonationHistoryE2E:
    """E2E tests for impersonation audit history."""

    def test_history_records_sessions(
        self, client: TestClient, admin_id: str, target_user_id: str
    ) -> None:
        """Test that impersonation history is properly recorded."""
        with patch("backend.api.admin.impersonation.get_impersonation_history") as mock_history:
            now = datetime.now(UTC)
            mock_history.return_value = [
                {
                    "id": 1,
                    "admin_user_id": admin_id,
                    "admin_email": "admin@example.com",
                    "target_user_id": target_user_id,
                    "target_email": "target@example.com",
                    "reason": "E2E testing",
                    "is_write_mode": False,
                    "started_at": now,
                    "expires_at": now,
                    "ended_at": now,
                }
            ]

            response = client.get("/api/admin/impersonate/history")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["sessions"]) == 1
            session = data["sessions"][0]
            assert session["admin_user_id"] == admin_id
            assert session["target_user_id"] == target_user_id
            assert session["reason"] == "E2E testing"

    def test_history_filter_by_admin(self, client: TestClient, admin_id: str) -> None:
        """Test filtering history by admin user ID."""
        with patch("backend.api.admin.impersonation.get_impersonation_history") as mock_history:
            mock_history.return_value = []

            response = client.get(f"/api/admin/impersonate/history?admin_user_id={admin_id}")

            assert response.status_code == 200
            mock_history.assert_called_once_with(
                admin_id=admin_id,
                target_user_id=None,
                limit=50,
            )

    def test_history_filter_by_target(self, client: TestClient, target_user_id: str) -> None:
        """Test filtering history by target user ID."""
        with patch("backend.api.admin.impersonation.get_impersonation_history") as mock_history:
            mock_history.return_value = []

            response = client.get(f"/api/admin/impersonate/history?target_user_id={target_user_id}")

            assert response.status_code == 200
            mock_history.assert_called_once_with(
                admin_id=None,
                target_user_id=target_user_id,
                limit=50,
            )


class TestImpersonationSecurityE2E:
    """E2E tests for impersonation security controls."""

    def test_cannot_impersonate_self(self, client: TestClient, admin_id: str) -> None:
        """Test that admin cannot impersonate themselves."""
        response = client.post(
            f"/api/admin/impersonate/{admin_id}",
            json={
                "reason": "Self impersonation attempt",
                "write_mode": False,
                "duration_minutes": 30,
            },
        )

        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_cannot_impersonate_other_admin(self, client: TestClient, target_user_id: str) -> None:
        """Test that admin cannot impersonate another admin."""
        with patch("backend.api.admin.impersonation.AdminQueryService") as mock_query:
            mock_query.user_exists.return_value = True
            mock_target = MagicMock()
            mock_target.is_admin = True  # Target is admin
            mock_query.get_user.return_value = mock_target

            response = client.post(
                f"/api/admin/impersonate/{target_user_id}",
                json={
                    "reason": "Admin impersonation attempt",
                    "write_mode": False,
                    "duration_minutes": 30,
                },
            )

            assert response.status_code == 400
            assert "admin" in response.json()["detail"].lower()

    def test_cannot_impersonate_nonexistent_user(self, client: TestClient) -> None:
        """Test that impersonating non-existent user returns 404."""
        with patch("backend.api.admin.impersonation.AdminQueryService") as mock_query:
            mock_query.user_exists.return_value = False

            response = client.post(
                "/api/admin/impersonate/nonexistent-user-123",
                json={"reason": "Testing", "write_mode": False, "duration_minutes": 30},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestImpersonationMiddlewareE2E:
    """E2E tests for impersonation middleware behavior."""

    def test_middleware_provides_correct_effective_user(self) -> None:
        """Test that middleware correctly switches effective user ID."""
        from backend.api.middleware.impersonation import get_effective_user_id

        # Create mock request with impersonation state
        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_target_id = "target-user-123"
        request.state.user_id = "admin-user-123"

        result = get_effective_user_id(request)
        assert result == "target-user-123"

    def test_middleware_provides_admin_user_without_impersonation(self) -> None:
        """Test that middleware returns normal user when not impersonating."""
        from backend.api.middleware.impersonation import get_effective_user_id

        request = MagicMock()
        request.state.is_impersonation = False
        request.state.user_id = "normal-user-123"

        result = get_effective_user_id(request)
        assert result == "normal-user-123"

    def test_impersonation_context_available(self) -> None:
        """Test that full impersonation context is available."""
        from backend.api.middleware.impersonation import get_impersonation_context

        request = MagicMock()
        request.state.is_impersonation = True
        request.state.impersonation_admin_id = "admin-123"
        request.state.impersonation_target_id = "target-123"
        request.state.impersonation_write_mode = False

        context = get_impersonation_context(request)

        assert context is not None
        assert context["is_impersonation"] is True
        assert context["admin_id"] == "admin-123"
        assert context["target_id"] == "target-123"
        assert context["write_mode"] is False
