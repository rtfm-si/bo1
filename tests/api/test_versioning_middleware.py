"""Tests for API versioning middleware."""

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.testclient import TestClient

from backend.api.middleware.api_version import (
    API_VERSION,
    VERSION_PATTERN,
    ApiVersionMiddleware,
    parse_version_header,
)


class TestVersionPattern:
    """Test version string validation."""

    def test_valid_versions(self):
        assert VERSION_PATTERN.match("1.0")
        assert VERSION_PATTERN.match("2.1")
        assert VERSION_PATTERN.match("10.20")

    def test_invalid_versions(self):
        assert not VERSION_PATTERN.match("1")
        assert not VERSION_PATTERN.match("v1.0")
        assert not VERSION_PATTERN.match("1.0.0")
        assert not VERSION_PATTERN.match("abc")
        assert not VERSION_PATTERN.match("")


class TestParseVersionHeader:
    """Test version header extraction."""

    def test_accept_version_header(self):
        """Accept-Version header is preferred."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [(b"accept-version", b"1.0")],
        }
        request = Request(scope)
        assert parse_version_header(request) == "1.0"

    def test_x_api_version_header(self):
        """X-API-Version header works as fallback."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [(b"x-api-version", b"2.0")],
        }
        request = Request(scope)
        assert parse_version_header(request) == "2.0"

    def test_accept_version_takes_precedence(self):
        """Accept-Version preferred over X-API-Version."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [
                (b"accept-version", b"1.0"),
                (b"x-api-version", b"2.0"),
            ],
        }
        request = Request(scope)
        assert parse_version_header(request) == "1.0"

    def test_no_version_header(self):
        """Returns None when no version header present."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [],
        }
        request = Request(scope)
        assert parse_version_header(request) is None

    def test_invalid_version_format(self):
        """Returns None for invalid version format."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "headers": [(b"accept-version", b"invalid")],
        }
        request = Request(scope)
        assert parse_version_header(request) is None


class TestApiVersionMiddleware:
    """Test API version middleware."""

    @pytest.fixture
    def app(self):
        """Create test app with middleware."""
        app = FastAPI()
        app.add_middleware(ApiVersionMiddleware)

        @app.get("/api/v1/test")
        async def test_endpoint():
            return {"status": "ok"}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_adds_api_version_header(self, client):
        """Response includes API-Version header."""
        response = client.get("/api/v1/test")
        assert response.headers.get("API-Version") == API_VERSION

    def test_api_version_on_non_api_routes(self, client):
        """API-Version header added to all routes."""
        response = client.get("/health")
        assert response.headers.get("API-Version") == API_VERSION

    def test_stores_version_in_request_state(self, app):
        """Requested version is stored in request.state."""
        captured_version = None

        @app.get("/api/v1/capture")
        async def capture_endpoint(request: Request):
            nonlocal captured_version
            captured_version = getattr(request.state, "api_version", None)
            return {"status": "ok"}

        client = TestClient(app)
        client.get("/api/v1/capture", headers={"Accept-Version": "1.0"})
        assert captured_version == "1.0"

    def test_default_version_when_no_header(self, app):
        """Uses API_VERSION when no header provided."""
        captured_version = None

        @app.get("/api/v1/capture2")
        async def capture_endpoint(request: Request):
            nonlocal captured_version
            captured_version = getattr(request.state, "api_version", None)
            return {"status": "ok"}

        client = TestClient(app)
        client.get("/api/v1/capture2")
        assert captured_version == API_VERSION
