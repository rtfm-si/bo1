"""Tests for service status API endpoints."""

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

# Load .env to ensure ADMIN_API_KEY is available
load_dotenv()


@pytest.fixture
def client():
    """Create test client with mocked dependencies."""
    import backend.api.main as main_module

    main_module._shutdown_event = None
    main_module._in_flight_requests = 0

    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestPublicStatusEndpoint:
    """Tests for GET /api/v1/status (no auth required)."""

    def test_status_returns_200(self, client: TestClient) -> None:
        """Public status endpoint returns 200."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_status_response_structure(self, client: TestClient) -> None:
        """Response has expected structure."""
        response = client.get("/api/v1/status")
        data = response.json()

        assert "status" in data
        assert "message" in data
        assert "timestamp" in data
        assert data["status"] in ("operational", "degraded", "outage")

    def test_status_no_auth_required(self, client: TestClient) -> None:
        """Endpoint works without authentication."""
        # No auth headers
        response = client.get("/api/v1/status")
        assert response.status_code == 200

    def test_operational_status_has_no_message(self, client: TestClient) -> None:
        """Operational status has null message."""
        response = client.get("/api/v1/status")
        data = response.json()

        if data["status"] == "operational":
            assert data["message"] is None
            assert data["services"] is None


class TestAdminStatusEndpoint:
    """Tests for GET /api/admin/services/status (admin auth required)."""

    def test_admin_status_requires_auth(self, client: TestClient) -> None:
        """Admin endpoint requires authentication."""
        response = client.get("/api/admin/services/status")
        # Should fail without admin key
        assert response.status_code in (401, 403)

    @pytest.mark.skip(reason="Requires full SuperTokens integration - tested via E2E")
    def test_admin_status_with_auth(self, client: TestClient) -> None:
        """Admin endpoint works with valid auth."""
        admin_key = os.getenv("ADMIN_API_KEY")
        response = client.get("/api/admin/services/status", headers={"X-Admin-Key": admin_key})
        assert response.status_code == 200

    @pytest.mark.skip(reason="Requires full SuperTokens integration - tested via E2E")
    def test_admin_status_response_structure(self, client: TestClient) -> None:
        """Admin response has detailed structure."""
        admin_key = os.getenv("ADMIN_API_KEY")
        response = client.get("/api/admin/services/status", headers={"X-Admin-Key": admin_key})
        data = response.json()

        assert "status" in data
        assert "services" in data
        assert "circuit_breakers" in data
        assert "vendor_health" in data
        assert "incidents_24h" in data
        assert "timestamp" in data

    @pytest.mark.skip(reason="Requires full SuperTokens integration - tested via E2E")
    def test_admin_status_services_format(self, client: TestClient) -> None:
        """Admin services have detailed format."""
        admin_key = os.getenv("ADMIN_API_KEY")
        response = client.get("/api/admin/services/status", headers={"X-Admin-Key": admin_key})
        data = response.json()

        services = data["services"]
        assert isinstance(services, dict)

        # Check at least one service exists
        if services:
            service = next(iter(services.values()))
            assert "name" in service
            assert "status" in service
            assert "error_rate" in service
            assert "is_critical" in service


class TestReadinessEndpointServiceStatus:
    """Tests for /api/ready endpoint service status extension."""

    def test_ready_includes_services(self, client: TestClient) -> None:
        """Readiness endpoint includes service status."""
        response = client.get("/api/ready")
        # May be 200 or 503 depending on dependencies
        if response.status_code == 200:
            data = response.json()
            # Services field should be present (may be None if error getting status)
            assert "services" in data or "detail" in data

    def test_ready_includes_vendor_status(self, client: TestClient) -> None:
        """Readiness endpoint includes vendor status."""
        response = client.get("/api/ready")
        if response.status_code == 200:
            data = response.json()
            assert "vendor_status" in data or "detail" in data
