"""Tests for public endpoint annotations.

Verifies:
- Public endpoints have summary="... (public, no auth required)"
- Public endpoints do not require authentication
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestPublicEndpointAnnotations:
    """Test public endpoints have proper summary annotations."""

    def test_health_endpoint_has_public_summary(self, client: TestClient):
        """Health endpoint should have public annotation in summary."""
        from backend.api.main import app

        # Find the route in the app
        route = next(
            (r for r in app.routes if hasattr(r, "path") and r.path == "/api/health"),
            None,
        )
        assert route is not None
        assert "public" in route.summary.lower()
        assert "no auth" in route.summary.lower()

    def test_ready_endpoint_has_public_summary(self, client: TestClient):
        """Ready endpoint should have public annotation in summary."""
        from backend.api.main import app

        route = next(
            (r for r in app.routes if hasattr(r, "path") and r.path == "/api/ready"),
            None,
        )
        assert route is not None
        assert "public" in route.summary.lower()

    def test_waitlist_endpoint_has_public_summary(self, client: TestClient):
        """Waitlist endpoint should have public annotation in summary."""
        from backend.api.main import app

        route = next(
            (r for r in app.routes if hasattr(r, "path") and r.path == "/api/v1/waitlist"),
            None,
        )
        assert route is not None
        assert "public" in route.summary.lower()

    def test_waitlist_check_endpoint_has_public_summary(self, client: TestClient):
        """Waitlist check endpoint should have public annotation in summary."""
        from backend.api.main import app

        route = next(
            (r for r in app.routes if hasattr(r, "path") and r.path == "/api/v1/waitlist/check"),
            None,
        )
        assert route is not None
        assert "public" in route.summary.lower()


class TestPublicEndpointsNoAuth:
    """Test public endpoints don't require authentication."""

    def test_health_no_auth_required(self, client: TestClient):
        """Health endpoint should work without auth header."""
        response = client.get("/api/health")
        # Should not be 401/403
        assert response.status_code == 200

    def test_ready_no_auth_required(self, client: TestClient):
        """Ready endpoint should work without auth header."""
        # May return 503 if deps unavailable, but not 401
        response = client.get("/api/ready")
        assert response.status_code != 401
        assert response.status_code != 403

    def test_share_token_no_auth_required(self, client: TestClient):
        """Share endpoint should work without auth header (returns 404 for invalid token)."""
        response = client.get("/api/v1/share/invalid-token")
        # Should be 404 (not found), not 401 (unauthorized)
        assert response.status_code == 404
