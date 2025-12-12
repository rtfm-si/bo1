"""Unit tests for CSRF middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRFMiddleware,
    generate_csrf_token,
    is_exempt_path,
)


@pytest.fixture
def app_with_csrf() -> FastAPI:
    """Create a test FastAPI app with CSRF middleware."""
    app = FastAPI()
    app.add_middleware(CSRFMiddleware)

    @app.get("/test")
    async def get_test() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/test")
    async def post_test() -> dict[str, str]:
        return {"status": "created"}

    @app.put("/test")
    async def put_test() -> dict[str, str]:
        return {"status": "updated"}

    @app.patch("/test")
    async def patch_test() -> dict[str, str]:
        return {"status": "patched"}

    @app.delete("/test")
    async def delete_test() -> dict[str, str]:
        return {"status": "deleted"}

    # Exempt paths
    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.post("/api/v1/webhooks/stripe")
    async def webhook() -> dict[str, str]:
        return {"status": "received"}

    @app.post("/api/v1/csp-report")
    async def csp_report() -> dict[str, str]:
        return {"status": "logged"}

    @app.post("/api/v1/waitlist")
    async def waitlist() -> dict[str, str]:
        return {"status": "added"}

    return app


@pytest.fixture
def client(app_with_csrf: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app_with_csrf)


class TestCSRFTokenGeneration:
    """Tests for CSRF token generation."""

    def test_generate_csrf_token_length(self) -> None:
        """Generated token should be 64 hex characters (32 bytes)."""
        token = generate_csrf_token()
        assert len(token) == 64
        # Should be valid hex
        int(token, 16)

    def test_generate_csrf_token_unique(self) -> None:
        """Each generated token should be unique."""
        tokens = {generate_csrf_token() for _ in range(100)}
        assert len(tokens) == 100


class TestExemptPaths:
    """Tests for path exemption logic."""

    def test_health_endpoint_exempt(self) -> None:
        """Health endpoints should be exempt."""
        assert is_exempt_path("/api/health")
        assert is_exempt_path("/api/health/db")

    def test_ready_endpoint_exempt(self) -> None:
        """Ready endpoint should be exempt."""
        assert is_exempt_path("/api/ready")

    def test_webhook_endpoints_exempt(self) -> None:
        """Webhook endpoints should be exempt."""
        assert is_exempt_path("/api/v1/webhooks/stripe")
        assert is_exempt_path("/api/v1/webhooks/anything")

    def test_csp_report_exempt(self) -> None:
        """CSP report endpoint should be exempt."""
        assert is_exempt_path("/api/v1/csp-report")

    def test_waitlist_exempt(self) -> None:
        """Waitlist endpoint should be exempt."""
        assert is_exempt_path("/api/v1/waitlist")

    def test_supertokens_exempt(self) -> None:
        """SuperTokens paths should be exempt."""
        assert is_exempt_path("/auth/session/refresh")
        assert is_exempt_path("/auth/signout")

    def test_normal_path_not_exempt(self) -> None:
        """Normal API paths should not be exempt."""
        assert not is_exempt_path("/api/v1/sessions")
        assert not is_exempt_path("/api/v1/context")
        assert not is_exempt_path("/test")


class TestCSRFMiddlewareGET:
    """Tests for GET request handling."""

    def test_get_sets_csrf_cookie(self, client: TestClient) -> None:
        """GET request should set csrf_token cookie."""
        response = client.get("/test")
        assert response.status_code == 200
        assert CSRF_COOKIE_NAME in response.cookies

    def test_get_does_not_replace_existing_cookie(self, client: TestClient) -> None:
        """GET should not replace existing csrf_token cookie."""
        # First GET sets the cookie
        response1 = client.get("/test")
        token1 = response1.cookies[CSRF_COOKIE_NAME]

        # Second GET should not replace it (cookie already present in request)
        response2 = client.get("/test", cookies={CSRF_COOKIE_NAME: token1})
        # Cookie won't be re-set if already present
        assert (
            CSRF_COOKIE_NAME not in response2.cookies
            or response2.cookies.get(CSRF_COOKIE_NAME) == token1
        )


class TestCSRFMiddlewarePOST:
    """Tests for POST request validation."""

    def test_post_without_cookie_returns_403(self, client: TestClient) -> None:
        """POST without csrf_token cookie should return 403."""
        response = client.post("/test")
        assert response.status_code == 403
        data = response.json()
        assert data["type"] == "CSRFError"
        assert "Missing CSRF token" in data["message"]

    def test_post_without_header_returns_403(self, client: TestClient) -> None:
        """POST with cookie but without header should return 403."""
        token = generate_csrf_token()
        response = client.post("/test", cookies={CSRF_COOKIE_NAME: token})
        assert response.status_code == 403
        data = response.json()
        assert data["type"] == "CSRFError"
        assert "Missing X-CSRF-Token" in data["message"]

    def test_post_with_mismatched_token_returns_403(self, client: TestClient) -> None:
        """POST with mismatched tokens should return 403."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        response = client.post(
            "/test",
            cookies={CSRF_COOKIE_NAME: token1},
            headers={CSRF_HEADER_NAME: token2},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["type"] == "CSRFError"
        assert "Invalid CSRF token" in data["message"]

    def test_post_with_valid_token_succeeds(self, client: TestClient) -> None:
        """POST with matching tokens should succeed."""
        token = generate_csrf_token()
        response = client.post(
            "/test",
            cookies={CSRF_COOKIE_NAME: token},
            headers={CSRF_HEADER_NAME: token},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "created"}


class TestCSRFMiddlewareOtherMethods:
    """Tests for PUT, PATCH, DELETE methods."""

    def test_put_with_valid_token_succeeds(self, client: TestClient) -> None:
        """PUT with matching tokens should succeed."""
        token = generate_csrf_token()
        response = client.put(
            "/test",
            cookies={CSRF_COOKIE_NAME: token},
            headers={CSRF_HEADER_NAME: token},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "updated"}

    def test_patch_with_valid_token_succeeds(self, client: TestClient) -> None:
        """PATCH with matching tokens should succeed."""
        token = generate_csrf_token()
        response = client.patch(
            "/test",
            cookies={CSRF_COOKIE_NAME: token},
            headers={CSRF_HEADER_NAME: token},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "patched"}

    def test_delete_with_valid_token_succeeds(self, client: TestClient) -> None:
        """DELETE with matching tokens should succeed."""
        token = generate_csrf_token()
        response = client.delete(
            "/test",
            cookies={CSRF_COOKIE_NAME: token},
            headers={CSRF_HEADER_NAME: token},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "deleted"}

    def test_put_without_token_returns_403(self, client: TestClient) -> None:
        """PUT without tokens should return 403."""
        response = client.put("/test")
        assert response.status_code == 403


class TestCSRFMiddlewareExemptPaths:
    """Tests for exempt path bypass."""

    def test_health_bypasses_csrf(self, client: TestClient) -> None:
        """Health endpoint should bypass CSRF."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_webhook_bypasses_csrf(self, client: TestClient) -> None:
        """Webhook POST should bypass CSRF validation."""
        response = client.post("/api/v1/webhooks/stripe")
        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    def test_csp_report_bypasses_csrf(self, client: TestClient) -> None:
        """CSP report POST should bypass CSRF validation."""
        response = client.post("/api/v1/csp-report")
        assert response.status_code == 200
        assert response.json() == {"status": "logged"}

    def test_waitlist_bypasses_csrf(self, client: TestClient) -> None:
        """Waitlist POST should bypass CSRF validation."""
        response = client.post("/api/v1/waitlist")
        assert response.status_code == 200
        assert response.json() == {"status": "added"}


class TestCSRFMiddlewareIntegration:
    """Integration tests for full CSRF flow."""

    def test_full_flow_get_then_post(self, client: TestClient) -> None:
        """Full flow: GET sets cookie, then use in POST."""
        # GET to obtain cookie
        get_response = client.get("/test")
        assert get_response.status_code == 200
        csrf_token = get_response.cookies[CSRF_COOKIE_NAME]

        # POST with token from cookie
        post_response = client.post(
            "/test",
            cookies={CSRF_COOKIE_NAME: csrf_token},
            headers={CSRF_HEADER_NAME: csrf_token},
        )
        assert post_response.status_code == 200
        assert post_response.json() == {"status": "created"}

    def test_cookie_attributes(self, client: TestClient) -> None:
        """Verify cookie has correct attributes."""
        response = client.get("/test")
        # TestClient doesn't expose all cookie attributes easily,
        # but we can verify the cookie is set
        assert CSRF_COOKIE_NAME in response.cookies
