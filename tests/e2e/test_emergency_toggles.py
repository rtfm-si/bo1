"""E2E tests for emergency runtime config toggles.

Tests the complete emergency toggle flow:
1. GET /api/admin/runtime-config - returns toggle state
2. PATCH /api/admin/runtime-config/{key} - sets override
3. DELETE /api/admin/runtime-config/{key} - clears override
4. Verify toggles affect behavior (e.g., disable prompt injection → injection not blocked)
"""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.middleware.auth import get_current_user


def create_mock_admin_user(user_id: str = "admin-e2e-test") -> dict[str, Any]:
    """Create mock admin user."""
    return {
        "id": user_id,
        "email": "admin@example.com",
        "is_admin": True,
        "role": "admin",
    }


def create_mock_non_admin_user(user_id: str = "user-e2e-test") -> dict[str, Any]:
    """Create mock non-admin user."""
    return {
        "id": user_id,
        "email": "user@example.com",
        "is_admin": False,
        "role": "user",
    }


@pytest.fixture
def admin_user() -> dict[str, Any]:
    """Test admin user."""
    return create_mock_admin_user()


@pytest.fixture
def mock_limiter():
    """Create a memory-based limiter for tests."""
    return Limiter(key_func=get_remote_address, storage_uri="memory://")


@pytest.fixture
def app(mock_limiter: Limiter) -> FastAPI:
    """Create test app with runtime config router and mocked rate limiter."""
    with patch("backend.api.middleware.rate_limit.limiter", mock_limiter):
        from backend.api.admin.runtime_config import router

        test_app = FastAPI()
        test_app.state.limiter = mock_limiter
        # Router already has prefix="/runtime-config", add /api/admin
        test_app.include_router(router, prefix="/api/admin")
        return test_app


@pytest.fixture
def admin_client(app: FastAPI, admin_user: dict[str, Any]) -> TestClient:
    """Create test client with admin auth."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def non_admin_client(app: FastAPI) -> TestClient:
    """Create test client with non-admin auth."""
    app.dependency_overrides[get_current_user] = lambda: create_mock_non_admin_user()
    return TestClient(app, raise_server_exceptions=False)


class TestRuntimeConfigE2EFlow:
    """E2E tests for complete runtime config toggle flow."""

    def test_full_toggle_lifecycle(self, admin_client: TestClient) -> None:
        """Test list → set → verify → clear → verify flow."""
        with patch("backend.api.admin.runtime_config.runtime_config") as mock_config:
            # Setup mock for list
            mock_config.get_all_overrides.return_value = {
                "prompt_injection_block_suspicious": {
                    "key": "prompt_injection_block_suspicious",
                    "override_value": None,
                    "default_value": True,
                    "effective_value": True,
                    "is_overridden": False,
                }
            }
            mock_config.ALLOWED_OVERRIDES = {"prompt_injection_block_suspicious": bool}

            # Step 1: List current config
            response = admin_client.get("/api/admin/runtime-config")
            assert response.status_code == 200
            data = response.json()
            assert data["count"] >= 1
            item = next(
                (i for i in data["items"] if i["key"] == "prompt_injection_block_suspicious"),
                None,
            )
            assert item is not None
            assert item["effective_value"] is True
            assert item["is_overridden"] is False

            # Step 2: Set override to False
            mock_config.set_override.return_value = True
            mock_config.get_all_overrides.return_value = {
                "prompt_injection_block_suspicious": {
                    "key": "prompt_injection_block_suspicious",
                    "override_value": False,
                    "default_value": True,
                    "effective_value": False,
                    "is_overridden": True,
                }
            }

            response = admin_client.patch(
                "/api/admin/runtime-config/prompt_injection_block_suspicious",
                json={"value": False},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["key"] == "prompt_injection_block_suspicious"
            assert data["override_value"] is False
            assert data["effective_value"] is False
            assert data["is_overridden"] is True

            # Step 3: Verify override is active
            response = admin_client.get("/api/admin/runtime-config")
            assert response.status_code == 200
            data = response.json()
            item = next(
                (i for i in data["items"] if i["key"] == "prompt_injection_block_suspicious"),
                None,
            )
            assert item is not None
            assert item["is_overridden"] is True
            assert item["effective_value"] is False

            # Step 4: Clear override
            mock_config.clear_override.return_value = True
            mock_config.get_all_overrides.return_value = {
                "prompt_injection_block_suspicious": {
                    "key": "prompt_injection_block_suspicious",
                    "override_value": None,
                    "default_value": True,
                    "effective_value": True,
                    "is_overridden": False,
                }
            }

            response = admin_client.delete(
                "/api/admin/runtime-config/prompt_injection_block_suspicious"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_overridden"] is False
            assert data["effective_value"] is True

            # Step 5: Verify override is cleared
            response = admin_client.get("/api/admin/runtime-config")
            assert response.status_code == 200
            data = response.json()
            item = next(
                (i for i in data["items"] if i["key"] == "prompt_injection_block_suspicious"),
                None,
            )
            assert item is not None
            assert item["is_overridden"] is False
            assert item["effective_value"] is True


class TestRuntimeConfigSecurityE2E:
    """E2E tests for runtime config security controls."""

    def test_non_admin_cannot_list_config(self, non_admin_client: TestClient) -> None:
        """Test that non-admin users cannot list runtime config."""
        response = non_admin_client.get("/api/admin/runtime-config")
        assert response.status_code == 403

    def test_non_admin_cannot_set_override(self, non_admin_client: TestClient) -> None:
        """Test that non-admin users cannot set overrides."""
        response = non_admin_client.patch(
            "/api/admin/runtime-config/prompt_injection_block_suspicious",
            json={"value": False},
        )
        assert response.status_code == 403

    def test_non_admin_cannot_clear_override(self, non_admin_client: TestClient) -> None:
        """Test that non-admin users cannot clear overrides."""
        response = non_admin_client.delete(
            "/api/admin/runtime-config/prompt_injection_block_suspicious"
        )
        assert response.status_code == 403

    def test_cannot_set_non_whitelisted_key(self, admin_client: TestClient) -> None:
        """Test that non-whitelisted keys cannot be set."""
        with patch("backend.api.admin.runtime_config.runtime_config") as mock_config:
            mock_config.ALLOWED_OVERRIDES = {"prompt_injection_block_suspicious": bool}

            response = admin_client.patch(
                "/api/admin/runtime-config/not_allowed_key",
                json={"value": False},
            )

            assert response.status_code == 400
            assert "not configurable" in response.json()["detail"].lower()

    def test_cannot_clear_non_whitelisted_key(self, admin_client: TestClient) -> None:
        """Test that non-whitelisted keys cannot be cleared."""
        with patch("backend.api.admin.runtime_config.runtime_config") as mock_config:
            mock_config.ALLOWED_OVERRIDES = {"prompt_injection_block_suspicious": bool}

            response = admin_client.delete("/api/admin/runtime-config/not_allowed_key")

            assert response.status_code == 400
            assert "not configurable" in response.json()["detail"].lower()


class TestToggleBehaviorE2E:
    """E2E tests for verifying toggles affect system behavior."""

    def test_prompt_injection_toggle_default_enabled(self) -> None:
        """Test that prompt injection is blocked by default."""
        from backend.services.runtime_config import get_effective_value

        with (
            patch("backend.services.runtime_config.get_override") as mock_override,
            patch("backend.services.runtime_config.get_settings") as mock_settings,
        ):
            mock_override.return_value = None
            mock_settings.return_value.prompt_injection_block_suspicious = True

            result = get_effective_value("prompt_injection_block_suspicious")
            assert result is True

    def test_prompt_injection_toggle_override_disabled(self) -> None:
        """Test that prompt injection can be disabled via override."""
        from backend.services.runtime_config import get_effective_value

        with (
            patch("backend.services.runtime_config.get_override") as mock_override,
            patch("backend.services.runtime_config.get_settings") as mock_settings,
        ):
            mock_override.return_value = False  # Override is set
            mock_settings.return_value.prompt_injection_block_suspicious = True

            result = get_effective_value("prompt_injection_block_suspicious")
            assert result is False

    def test_llm_cache_toggle(self) -> None:
        """Test LLM response cache toggle."""
        from backend.services.runtime_config import get_effective_value

        with (
            patch("backend.services.runtime_config.get_override") as mock_override,
            patch("backend.services.runtime_config.get_settings") as mock_settings,
        ):
            # Default enabled
            mock_override.return_value = None
            mock_settings.return_value.enable_llm_response_cache = True
            assert get_effective_value("enable_llm_response_cache") is True

            # Override disabled
            mock_override.return_value = False
            assert get_effective_value("enable_llm_response_cache") is False

    def test_sse_streaming_toggle(self) -> None:
        """Test SSE streaming toggle."""
        from backend.services.runtime_config import get_effective_value

        with (
            patch("backend.services.runtime_config.get_override") as mock_override,
            patch("backend.services.runtime_config.get_settings") as mock_settings,
        ):
            # Default enabled
            mock_override.return_value = None
            mock_settings.return_value.enable_sse_streaming = True
            assert get_effective_value("enable_sse_streaming") is True

            # Override disabled
            mock_override.return_value = False
            assert get_effective_value("enable_sse_streaming") is False


class TestRuntimeConfigAuditE2E:
    """E2E tests for runtime config audit logging."""

    def test_set_override_logs_change(self, admin_client: TestClient) -> None:
        """Test that setting override creates audit log entry."""
        with (
            patch("backend.api.admin.runtime_config.runtime_config") as mock_config,
            patch("backend.api.admin.runtime_config.logger") as mock_logger,
        ):
            mock_config.ALLOWED_OVERRIDES = {"prompt_injection_block_suspicious": bool}
            mock_config.set_override.return_value = True
            mock_config.get_all_overrides.return_value = {
                "prompt_injection_block_suspicious": {
                    "key": "prompt_injection_block_suspicious",
                    "override_value": False,
                    "default_value": True,
                    "effective_value": False,
                    "is_overridden": True,
                }
            }

            response = admin_client.patch(
                "/api/admin/runtime-config/prompt_injection_block_suspicious",
                json={"value": False},
            )

            assert response.status_code == 200
            # Verify audit log was called
            mock_logger.warning.assert_called()
            call_args = str(mock_logger.warning.call_args)
            assert "ADMIN_RUNTIME_CONFIG_CHANGE" in call_args
            assert "prompt_injection_block_suspicious" in call_args

    def test_clear_override_logs_change(self, admin_client: TestClient) -> None:
        """Test that clearing override creates audit log entry."""
        with (
            patch("backend.api.admin.runtime_config.runtime_config") as mock_config,
            patch("backend.api.admin.runtime_config.logger") as mock_logger,
        ):
            mock_config.ALLOWED_OVERRIDES = {"prompt_injection_block_suspicious": bool}
            mock_config.clear_override.return_value = True
            mock_config.get_all_overrides.return_value = {
                "prompt_injection_block_suspicious": {
                    "key": "prompt_injection_block_suspicious",
                    "override_value": None,
                    "default_value": True,
                    "effective_value": True,
                    "is_overridden": False,
                }
            }

            response = admin_client.delete(
                "/api/admin/runtime-config/prompt_injection_block_suspicious"
            )

            assert response.status_code == 200
            # Verify audit log was called
            mock_logger.warning.assert_called()
            call_args = str(mock_logger.warning.call_args)
            assert "ADMIN_RUNTIME_CONFIG_CLEAR" in call_args
            assert "prompt_injection_block_suspicious" in call_args


class TestAllowedOverridesE2E:
    """E2E tests for verifying all allowed toggles are accessible."""

    def test_all_allowed_toggles_listed(self, admin_client: TestClient) -> None:
        """Test that all allowed toggles are returned in list."""
        from backend.services.runtime_config import ALLOWED_OVERRIDES

        with patch("backend.api.admin.runtime_config.runtime_config") as mock_config:
            mock_config.get_all_overrides.return_value = {
                key: {
                    "key": key,
                    "override_value": None,
                    "default_value": True,
                    "effective_value": True,
                    "is_overridden": False,
                }
                for key in ALLOWED_OVERRIDES
            }

            response = admin_client.get("/api/admin/runtime-config")

            assert response.status_code == 200
            data = response.json()
            returned_keys = {item["key"] for item in data["items"]}

            for expected_key in ALLOWED_OVERRIDES:
                assert expected_key in returned_keys, f"Missing key: {expected_key}"

    def test_expected_toggles_exist(self) -> None:
        """Test that all expected emergency toggles are whitelisted."""
        from backend.services.runtime_config import ALLOWED_OVERRIDES

        expected_toggles = {
            "prompt_injection_block_suspicious",
            "enable_llm_response_cache",
            "enable_prompt_cache",
            "enable_sse_streaming",
            "auto_generate_projects",
            "enable_context_collection",
        }

        for toggle in expected_toggles:
            assert toggle in ALLOWED_OVERRIDES, f"Expected toggle not in whitelist: {toggle}"
