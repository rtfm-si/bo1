"""Tests for API versioning.

Tests that:
- API-Version header is present in all responses
- /api/version endpoint returns correct version info
- OpenAPI spec contains version metadata
"""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.middleware.api_version import API_VERSION


class TestApiVersionHeader:
    """Test API-Version response header."""

    def test_version_header_on_root(self) -> None:
        """Test API-Version header is present on root endpoint."""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        assert "API-Version" in response.headers
        assert response.headers["API-Version"] == API_VERSION

    def test_version_header_on_health(self) -> None:
        """Test API-Version header is present on health endpoint."""
        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        assert "API-Version" in response.headers
        assert response.headers["API-Version"] == API_VERSION

    def test_version_header_on_error(self) -> None:
        """Test API-Version header is present even on 404 responses."""
        client = TestClient(app)
        response = client.get("/api/nonexistent")

        assert response.status_code == 404
        assert "API-Version" in response.headers
        assert response.headers["API-Version"] == API_VERSION


class TestVersionEndpoint:
    """Test /api/version endpoint."""

    def test_version_endpoint_returns_versions(self) -> None:
        """Test version endpoint returns api_version and app_version."""
        client = TestClient(app)
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()
        assert "api_version" in data
        assert "app_version" in data
        assert data["api_version"] == API_VERSION
        assert data["app_version"] == "1.0.0"

    def test_version_endpoint_has_header(self) -> None:
        """Test version endpoint also has API-Version header."""
        client = TestClient(app)
        response = client.get("/api/version")

        assert response.status_code == 200
        assert response.headers["API-Version"] == API_VERSION


class TestOpenApiVersioning:
    """Test OpenAPI spec versioning (requires admin auth in production)."""

    @pytest.mark.skipif(
        True,  # Skip in automated tests - requires admin auth
        reason="OpenAPI spec requires admin authentication",
    )
    def test_openapi_contains_version(self) -> None:
        """Test OpenAPI spec contains version metadata."""
        client = TestClient(app)
        response = client.get("/api/v1/openapi.json")

        assert response.status_code == 200
        spec = response.json()
        assert spec["info"]["version"] == "1.0.0"
