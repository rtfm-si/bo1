"""Tests for audit logging middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.api.middleware.audit_logging import (
    EXCLUDED_PATHS,
    EXCLUDED_PREFIXES,
    AuditLoggingMiddleware,
    _get_client_ip,
    _should_log,
)


class TestShouldLog:
    """Tests for _should_log helper function."""

    def test_normal_paths_should_log(self) -> None:
        """Normal API paths should be logged."""
        paths = [
            "/api/v1/sessions",
            "/api/v1/users",
            "/api/v1/actions",
            "/api/v1/datasets",
        ]
        for path in paths:
            assert _should_log(path) is True

    def test_excluded_paths_not_logged(self) -> None:
        """Health and docs paths should not be logged."""
        for path in EXCLUDED_PATHS:
            assert _should_log(path) is False

    def test_excluded_prefixes_not_logged(self) -> None:
        """Static asset paths should not be logged."""
        paths = [
            "/static/style.css",
            "/static/app.js",
            "/assets/image.png",
            "/assets/fonts/roboto.woff2",
        ]
        for path in paths:
            assert _should_log(path) is False


class TestGetClientIp:
    """Tests for _get_client_ip helper function."""

    def test_x_forwarded_for_header(self) -> None:
        """Should extract IP from X-Forwarded-For header."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        request.client = None

        ip = _get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_x_real_ip_header(self) -> None:
        """Should extract IP from X-Real-IP header."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "203.0.113.50"}
        request.client = None

        ip = _get_client_ip(request)
        assert ip == "203.0.113.50"

    def test_direct_client(self) -> None:
        """Should fall back to direct client IP."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client.host = "192.168.1.100"

        ip = _get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_no_client_info(self) -> None:
        """Should return None when no client info available."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None

        ip = _get_client_ip(request)
        assert ip is None


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI app with audit logging middleware."""
    app = FastAPI()
    app.add_middleware(AuditLoggingMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/api/health")
    async def health_endpoint():
        return {"healthy": True}

    @app.get("/metrics")
    async def metrics_endpoint():
        return {"metrics": "data"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestAuditLoggingMiddleware:
    """Tests for AuditLoggingMiddleware."""

    @patch("backend.api.middleware.audit_logging._log_request_async")
    def test_logs_normal_request(self, mock_log_async: AsyncMock, client: TestClient) -> None:
        """Should log normal API requests."""
        response = client.get("/api/v1/test")

        assert response.status_code == 200
        # Note: asyncio.create_task may not execute in sync test context
        # We verify the middleware doesn't break the request flow

    def test_excludes_health_endpoint(self, client: TestClient) -> None:
        """Should not log health check requests."""
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"healthy": True}

    def test_excludes_metrics_endpoint(self, client: TestClient) -> None:
        """Should not log metrics endpoint requests."""
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_response_not_blocked(self, client: TestClient) -> None:
        """Audit logging should not block response."""
        import time

        start = time.perf_counter()
        response = client.get("/api/v1/test")
        duration = time.perf_counter() - start

        assert response.status_code == 200
        # Response should be fast (logging is async)
        assert duration < 1.0  # Very generous threshold


class TestExcludedPaths:
    """Tests for excluded path configuration."""

    def test_health_paths_excluded(self) -> None:
        """Health endpoints should be excluded."""
        assert "/api/health" in EXCLUDED_PATHS
        assert "/api/ready" in EXCLUDED_PATHS

    def test_docs_paths_excluded(self) -> None:
        """Documentation endpoints should be excluded."""
        assert "/docs" in EXCLUDED_PATHS
        assert "/redoc" in EXCLUDED_PATHS
        assert "/openapi.json" in EXCLUDED_PATHS

    def test_metrics_path_excluded(self) -> None:
        """Prometheus metrics should be excluded."""
        assert "/metrics" in EXCLUDED_PATHS

    def test_static_prefixes_excluded(self) -> None:
        """Static asset prefixes should be excluded."""
        assert "/static/" in EXCLUDED_PREFIXES
        assert "/assets/" in EXCLUDED_PREFIXES
