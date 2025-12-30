"""Admin routes health tests.

Tests that all admin API endpoints return valid responses (not 500s).
This serves as a regression test to ensure admin endpoints remain functional.

Each endpoint is tested with admin authentication and basic valid parameters.
Some endpoints may return 404 (no data) or other expected error codes,
but should never return 500 (internal server error).

Note: These tests use real database connections and are integration tests.
They require a running database with the schema initialized.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.admin import router as admin_router
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.auth import get_current_user


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "test-admin-user-id"


def mock_get_current_user():
    """Override get_current_user to return admin user dict."""
    return {"user_id": "test-admin-user-id", "is_admin": True}


@pytest.fixture
def app():
    """Create test app with all admin routes and mocked auth."""
    app = FastAPI()

    # Set up rate limiter with memory storage for tests
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    app.state.limiter = limiter

    # Mock admin auth - let DB and Redis work normally
    app.dependency_overrides[require_admin_any] = mock_admin_override
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Include the full admin router
    app.include_router(admin_router, prefix="/api")

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


def make_route_id(route):
    """Generate a descriptive test ID for each route."""
    method, path, _, _ = route
    return f"{method}_{path.replace('/api/admin/', '').replace('/', '_')}"


# Admin routes that should work correctly
# Format: (method, path, params/body, expected_status_codes)
ADMIN_ROUTES_WORKING = [
    # Users - /api/admin/* (prefix="")
    ("GET", "/api/admin/users", None, [200]),
    ("GET", "/api/admin/stats", None, [200]),
    ("GET", "/api/admin/users/test-user-id", None, [200, 404]),
    # Sessions - /api/admin/* (prefix="")
    ("GET", "/api/admin/sessions/active", None, [200]),
    ("GET", "/api/admin/sessions/test-session-id", None, [200, 404]),
    # Research Cache - /api/admin/* (prefix="")
    ("GET", "/api/admin/research-cache/stats", None, [200]),
    ("GET", "/api/admin/research-cache/stale", None, [200]),
    # Waitlist - /api/admin/* (prefix="")
    ("GET", "/api/admin/waitlist", None, [200]),
    # Metrics - /api/admin/* (prefix="")
    ("GET", "/api/admin/metrics", None, [200]),
    # User Metrics - /api/admin/metrics/* (prefix="/metrics")
    ("GET", "/api/admin/metrics/users", None, [200]),
    ("GET", "/api/admin/metrics/usage", None, [200]),
    ("GET", "/api/admin/metrics/onboarding", None, [200]),
    # Costs - /api/admin/costs/* (prefix="/costs")
    ("GET", "/api/admin/costs/by-provider", None, [200]),
    ("GET", "/api/admin/costs/per-user", None, [200]),
    ("GET", "/api/admin/costs/cache-metrics", None, [200]),
    ("GET", "/api/admin/costs/fair-usage/heavy-users", None, [200]),
    ("GET", "/api/admin/costs/fair-usage/by-feature", None, [200]),
    # Observability - /api/admin/* (prefix="")
    ("GET", "/api/admin/observability-links", None, [200]),
    # Alerts - /api/admin/alerts/*
    ("GET", "/api/admin/alerts/history", None, [200]),
    ("GET", "/api/admin/alerts/settings", None, [200]),
    # Email Stats - /api/admin/email-stats/*
    ("GET", "/api/admin/email-stats", None, [200]),
    # Impersonation - /api/admin/* (prefix="")
    ("GET", "/api/admin/impersonate/status", None, [200]),
    # Partitions - /api/admin/partitions/*
    ("GET", "/api/admin/partitions", None, [200]),
    # Promotions - /api/admin/promotions/*
    ("GET", "/api/admin/promotions", None, [200]),
    # Feedback - /api/admin/feedback/*
    ("GET", "/api/admin/feedback", None, [200]),
    ("GET", "/api/admin/feedback/analysis-summary", None, [200]),
    ("GET", "/api/admin/feedback/by-theme/usability", None, [200]),
    ("GET", "/api/admin/feedback/test-feedback-id", None, [200, 404]),
    # Blog - /api/admin/blog/*
    ("GET", "/api/admin/blog/posts", None, [200]),
    # Note: /api/admin/blog/topics requires LLM API - tested separately
    # SEO - /api/admin/seo/*
    ("GET", "/api/admin/seo/analytics", None, [200]),
    # Dashboard - /api/admin/dashboard/*
    ("GET", "/api/admin/dashboard/costs", None, [200]),
    # Drilldown - /api/admin/drilldown/*
    ("GET", "/api/admin/drilldown/users", None, [200]),
    ("GET", "/api/admin/drilldown/whitelist", None, [200]),
    ("GET", "/api/admin/drilldown/costs", None, [200]),
    # Extended KPIs - /api/admin/* (prefix="")
    ("GET", "/api/admin/extended-kpis", None, [200]),
    # Embeddings - /api/admin/* (prefix="")
    ("GET", "/api/admin/embeddings/stats", None, [200]),
    # Templates - /api/admin/templates/*
    ("GET", "/api/admin/templates", None, [200]),
    # Feature Flags - /api/admin/feature-flags
    ("GET", "/api/admin/feature-flags", None, [200]),
    # Runtime Config - /api/admin/runtime-config
    ("GET", "/api/admin/runtime-config", None, [200]),
    # Cost Analytics - /api/admin/analytics/costs/*
    ("GET", "/api/admin/analytics/costs", None, [200]),
    ("GET", "/api/admin/analytics/costs/users", None, [200]),
    ("GET", "/api/admin/analytics/costs/daily", None, [200]),
    ("GET", "/api/admin/analytics/costs/top-users", None, [200]),
    # Ops - /api/admin/ops/*
    ("GET", "/api/admin/ops/patterns", None, [200]),
    ("GET", "/api/admin/ops/remediations", None, [200]),
    ("GET", "/api/admin/ops/health", None, [200]),
    ("GET", "/api/admin/ops/client-errors", None, [200]),
    ("GET", "/api/admin/ops/api-errors", None, [200]),
    ("GET", "/api/admin/ops/error-summary", None, [200]),
    # Performance Monitoring - /api/admin/ops/*
    ("GET", "/api/admin/ops/performance-metrics", None, [200]),
    ("GET", "/api/admin/ops/performance-trends", None, [200]),
    ("GET", "/api/admin/ops/performance-thresholds", None, [200]),
]


class TestAdminRoutesHealth:
    """Test all admin routes return valid responses (no 500s)."""

    @pytest.mark.parametrize(
        "method,path,params,expected_statuses",
        ADMIN_ROUTES_WORKING,
        ids=[make_route_id(r) for r in ADMIN_ROUTES_WORKING],
    )
    def test_admin_route_returns_valid_response(
        self, client, method, path, params, expected_statuses
    ):
        """Each admin route should return a valid response (not 500)."""
        # Make request
        if method == "GET":
            response = client.get(path, params=params)
        elif method == "POST":
            response = client.post(path, json=params or {})
        elif method == "PUT":
            response = client.put(path, json=params or {})
        elif method == "PATCH":
            response = client.patch(path, json=params or {})
        elif method == "DELETE":
            response = client.delete(path, params=params)
        else:
            pytest.fail(f"Unknown HTTP method: {method}")

        # Assert no 500 error
        assert response.status_code != 500, (
            f"{method} {path} returned 500 Internal Server Error: "
            f"{response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}"
        )

        # If we have expected statuses, verify against them
        if expected_statuses:
            assert response.status_code in expected_statuses, (
                f"{method} {path} returned {response.status_code}, "
                f"expected one of {expected_statuses}. "
                f"Response: {response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}"
            )
