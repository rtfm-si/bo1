"""Tests for admin query performance API endpoints.

Tests:
- GET /api/admin/queries/slow
- POST /api/admin/queries/slow/reset
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.queries import router
from backend.api.middleware.admin import require_admin_any


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with queries router and admin auth override."""
    test_app = FastAPI()
    test_app.dependency_overrides[require_admin_any] = mock_admin_override
    test_app.include_router(router, prefix="/api/admin")
    return test_app


@pytest.fixture
def client(app):
    """Create test client with mocked admin auth (bypasses CSRF)."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def main_app_client():
    """Create test client using main app (for auth tests)."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_headers():
    """Admin API key headers."""
    return {"X-Admin-Key": "test-admin-key"}


class TestSlowQueriesEndpoint:
    """Tests for GET /api/admin/queries/slow."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/queries/slow")
        assert response.status_code == 403

    def test_returns_extension_not_available(self, client: TestClient):
        """Should handle extension not available gracefully."""
        with patch(
            "backend.api.admin.queries._check_extension_available",
            return_value=False,
        ):
            response = client.get("/api/admin/queries/slow")
            assert response.status_code == 200

            data = response.json()
            assert data["extension_available"] is False
            assert data["queries"] == []
            assert "not installed" in data["message"]

    def test_returns_slow_queries(self, client: TestClient):
        """Should return slow queries when extension is available."""
        mock_rows = [
            {
                "query": "SELECT * FROM users WHERE id = $1",
                "calls": 1000,
                "mean_time_ms": 5.5,
                "total_time_ms": 5500.0,
                "rows": 1000,
                "shared_blks_hit": 500,
                "shared_blks_read": 10,
            },
            {
                "query": "SELECT * FROM sessions WHERE user_id = $1",
                "calls": 500,
                "mean_time_ms": 3.2,
                "total_time_ms": 1600.0,
                "rows": 2000,
                "shared_blks_hit": 300,
                "shared_blks_read": 5,
            },
        ]

        with (
            patch(
                "backend.api.admin.queries._check_extension_available",
                return_value=True,
            ),
            patch(
                "backend.api.admin.queries.execute_query",
                return_value=mock_rows,
            ),
        ):
            response = client.get("/api/admin/queries/slow")
            assert response.status_code == 200

            data = response.json()
            assert data["extension_available"] is True
            assert data["message"] is None
            assert len(data["queries"]) == 2

            # Check first query
            q1 = data["queries"][0]
            assert q1["query"] == "SELECT * FROM users WHERE id = $1"
            assert q1["calls"] == 1000
            assert q1["mean_time_ms"] == 5.5
            assert q1["total_time_ms"] == 5500.0
            assert q1["rows"] == 1000

    def test_respects_limit_parameter(self, client: TestClient):
        """Should respect limit query parameter."""
        with (
            patch(
                "backend.api.admin.queries._check_extension_available",
                return_value=True,
            ),
            patch(
                "backend.api.admin.queries.execute_query",
                return_value=[],
            ) as mock_execute,
        ):
            response = client.get("/api/admin/queries/slow?limit=10&min_calls=5")
            assert response.status_code == 200

            # Check execute_query was called with correct params
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            # Params are (min_calls, limit)
            assert call_args[0][1] == (5, 10)

    def test_empty_result_when_no_queries(self, client: TestClient):
        """Should return empty list when no queries tracked."""
        with (
            patch(
                "backend.api.admin.queries._check_extension_available",
                return_value=True,
            ),
            patch(
                "backend.api.admin.queries.execute_query",
                return_value=[],
            ),
        ):
            response = client.get("/api/admin/queries/slow")
            assert response.status_code == 200

            data = response.json()
            assert data["extension_available"] is True
            assert data["queries"] == []


class TestResetQueryStatsEndpoint:
    """Tests for POST /api/admin/queries/slow/reset."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.post("/api/admin/queries/slow/reset")
        assert response.status_code == 403

    def test_skips_when_extension_not_available(self, client: TestClient):
        """Should skip reset when extension not available."""
        with patch(
            "backend.api.admin.queries._check_extension_available",
            return_value=False,
        ):
            response = client.post("/api/admin/queries/slow/reset")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "skipped"
            assert "not available" in data["message"]

    def test_resets_stats_successfully(self, client: TestClient):
        """Should reset stats when extension is available."""
        with (
            patch(
                "backend.api.admin.queries._check_extension_available",
                return_value=True,
            ),
            patch(
                "backend.api.admin.queries.execute_query",
                return_value=None,
            ) as mock_execute,
        ):
            response = client.post("/api/admin/queries/slow/reset")
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"

            # Verify pg_stat_statements_reset was called
            mock_execute.assert_called_once_with(
                "SELECT pg_stat_statements_reset()",
                fetch="none",
            )
