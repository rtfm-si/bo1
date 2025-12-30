"""Tests for rate limit headers middleware.

Tests that X-RateLimit-* headers are properly added to API responses.
"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from backend.api.middleware.rate_limit_headers import (
    SKIP_PATHS,
    RateLimitHeadersMiddleware,
)
from bo1.constants import RateLimits


class TestRateLimitHeadersMiddleware:
    """Tests for RateLimitHeadersMiddleware class."""

    @pytest.fixture
    def app_with_middleware(self):
        """Create test app with rate limit headers middleware."""
        app = FastAPI()
        app.add_middleware(RateLimitHeadersMiddleware)

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/api/v1/sessions")
        async def sessions_endpoint():
            return {"sessions": []}

        @app.post("/api/v1/sessions")
        async def create_session():
            return {"session_id": "123"}

        @app.get("/api/admin/dashboard")
        async def admin_dashboard():
            return {"data": "admin"}

        @app.get("/api/v1/auth/me")
        async def auth_me():
            return {"user": "test"}

        @app.get("/api/v1/stream/123")
        async def stream_endpoint():
            return {"streaming": True}

        @app.post("/api/v1/datasets")
        async def upload_dataset():
            return {"uploaded": True}

        @app.get("/api/v1/context/profile")
        async def context_profile():
            return {"context": {}}

        @app.post("/api/v1/sessions/123/control/start")
        async def control_start():
            return {"started": True}

        @app.get("/health")
        async def health():
            return {"health": "ok"}

        @app.get("/metrics")
        async def metrics():
            return {"metrics": "data"}

        return app

    @pytest.fixture
    def client(self, app_with_middleware):
        """Create test client."""
        return TestClient(app_with_middleware)

    def test_headers_present_on_success_response(self, client):
        """Rate limit headers are present on 200 responses."""
        response = client.get("/api/v1/test")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_headers_contain_valid_integers(self, client):
        """Headers contain valid integer values."""
        response = client.get("/api/v1/test")

        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        reset = int(response.headers["X-RateLimit-Reset"])

        assert limit > 0
        assert remaining >= 0
        assert reset > 0

    def test_headers_absent_for_health_endpoint(self, client):
        """Health endpoints don't have rate limit headers."""
        response = client.get("/health")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers
        assert "X-RateLimit-Remaining" not in response.headers

    def test_headers_absent_for_metrics_endpoint(self, client):
        """Metrics endpoints don't have rate limit headers."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    def test_admin_endpoint_uses_admin_limit(self, client):
        """Admin endpoints use higher rate limit."""
        response = client.get("/api/admin/dashboard")

        limit = int(response.headers["X-RateLimit-Limit"])
        admin_limit, _ = _parse_limit(RateLimits.ADMIN)

        assert limit == admin_limit

    def test_auth_endpoint_uses_auth_limit(self, client):
        """Auth endpoints use auth rate limit."""
        response = client.get("/api/v1/auth/me")

        limit = int(response.headers["X-RateLimit-Limit"])
        auth_limit, _ = _parse_limit(RateLimits.AUTH)

        assert limit == auth_limit

    def test_streaming_endpoint_uses_streaming_limit(self, client):
        """Streaming endpoints use streaming rate limit."""
        response = client.get("/api/v1/stream/123")

        limit = int(response.headers["X-RateLimit-Limit"])
        streaming_limit, _ = _parse_limit(RateLimits.STREAMING)

        assert limit == streaming_limit

    def test_session_create_uses_session_limit(self, client):
        """Session creation uses session rate limit."""
        response = client.post("/api/v1/sessions")

        limit = int(response.headers["X-RateLimit-Limit"])
        session_limit, _ = _parse_limit(RateLimits.SESSION)

        assert limit == session_limit

    def test_upload_endpoint_uses_upload_limit(self, client):
        """Dataset upload uses upload rate limit."""
        response = client.post("/api/v1/datasets")

        limit = int(response.headers["X-RateLimit-Limit"])
        upload_limit, _ = _parse_limit(RateLimits.UPLOAD)

        assert limit == upload_limit

    def test_context_endpoint_uses_context_limit(self, client):
        """Context endpoints use context rate limit."""
        response = client.get("/api/v1/context/profile")

        limit = int(response.headers["X-RateLimit-Limit"])
        context_limit, _ = _parse_limit(RateLimits.CONTEXT)

        assert limit == context_limit

    def test_control_endpoint_uses_control_limit(self, client):
        """Control endpoints use control rate limit."""
        response = client.post("/api/v1/sessions/123/control/start")

        limit = int(response.headers["X-RateLimit-Limit"])
        control_limit, _ = _parse_limit(RateLimits.CONTROL)

        assert limit == control_limit

    def test_general_endpoint_uses_general_limit(self, client):
        """General endpoints use general rate limit."""
        response = client.get("/api/v1/sessions")

        limit = int(response.headers["X-RateLimit-Limit"])
        general_limit, _ = _parse_limit(RateLimits.GENERAL)

        assert limit == general_limit


class TestSkipPaths:
    """Tests for SKIP_PATHS constant."""

    def test_health_endpoints_skipped(self):
        """Health endpoints are in skip list."""
        assert "/health" in SKIP_PATHS
        assert "/api/health" in SKIP_PATHS
        assert "/ready" in SKIP_PATHS
        assert "/api/ready" in SKIP_PATHS

    def test_metrics_endpoints_skipped(self):
        """Metrics endpoints are in skip list."""
        assert "/metrics" in SKIP_PATHS
        assert "/api/metrics" in SKIP_PATHS


class TestEndpointLimitMapping:
    """Tests for endpoint limit mapping logic."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""

        async def dummy_app(scope, receive, send):
            pass

        return RateLimitHeadersMiddleware(dummy_app)

    def test_admin_path_detected(self, middleware):
        """Admin paths return admin limit."""
        limit, window = middleware._get_endpoint_limit("/api/admin/users", "GET")
        expected_limit, expected_window = _parse_limit(RateLimits.ADMIN)

        assert limit == expected_limit
        assert window == expected_window

    def test_auth_path_detected(self, middleware):
        """Auth paths return auth limit."""
        limit, window = middleware._get_endpoint_limit("/api/v1/auth/login", "POST")
        expected_limit, expected_window = _parse_limit(RateLimits.AUTH)

        assert limit == expected_limit

    def test_control_path_detected(self, middleware):
        """Control paths return control limit."""
        limit, _ = middleware._get_endpoint_limit("/api/v1/control/kill", "POST")
        expected_limit, _ = _parse_limit(RateLimits.CONTROL)

        assert limit == expected_limit

    def test_stream_path_detected(self, middleware):
        """Stream paths return streaming limit."""
        limit, _ = middleware._get_endpoint_limit("/api/v1/sessions/123/stream", "GET")
        expected_limit, _ = _parse_limit(RateLimits.STREAMING)

        assert limit == expected_limit

    def test_unknown_path_uses_general(self, middleware):
        """Unknown paths return general limit."""
        limit, _ = middleware._get_endpoint_limit("/api/v1/unknown/path", "GET")
        expected_limit, _ = _parse_limit(RateLimits.GENERAL)

        assert limit == expected_limit


def _parse_limit(limit_str: str) -> tuple[int, int]:
    """Parse limit string like '60/minute' into (count, window_seconds)."""
    parts = limit_str.split("/")
    count = int(parts[0])
    unit = parts[1]
    window_map = {"second": 1, "minute": 60, "hour": 3600}
    return count, window_map.get(unit, 60)
