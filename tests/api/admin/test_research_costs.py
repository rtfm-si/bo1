"""Tests for admin research costs API endpoints.

Tests:
- GET /api/admin/costs/research
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.costs import limiter, router
from backend.api.middleware.admin import require_admin_any


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with costs router and admin auth override."""
    # Disable rate limiter for tests (to avoid Redis connection)
    original_enabled = limiter.enabled
    limiter.enabled = False

    test_app = FastAPI()
    test_app.dependency_overrides[require_admin_any] = mock_admin_override
    # Router already has prefix="/costs", so mount at /api/admin
    test_app.include_router(router, prefix="/api/admin")

    yield test_app

    # Restore original limiter state
    limiter.enabled = original_enabled


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def main_app_client():
    """Create test client using main app (for auth tests)."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestResearchCostsEndpoint:
    """Tests for GET /api/admin/costs/research."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/costs/research")
        assert response.status_code == 403

    def test_returns_research_costs(self, client: TestClient):
        """Admin users should get research costs breakdown."""
        with patch("backend.api.admin.costs.db_session") as mock_db_session:
            # Set up mock cursor
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Mock query results
            mock_cursor.fetchall.side_effect = [
                # Provider totals
                [
                    {"provider": "brave", "amount": 1.50, "query_count": 100},
                    {"provider": "tavily", "amount": 3.00, "query_count": 50},
                ],
                # Daily breakdown
                [
                    {"day": date.today() - timedelta(days=1), "provider": "brave", "amount": 0.20},
                    {"day": date.today() - timedelta(days=1), "provider": "tavily", "amount": 0.40},
                    {"day": date.today(), "provider": "brave", "amount": 0.10},
                ],
            ]
            mock_cursor.fetchone.return_value = {
                "today": 0.10,
                "week": 1.50,
                "month": 4.50,
                "all_time": 4.50,
            }

            response = client.get("/api/admin/costs/research")
            assert response.status_code == 200

            data = response.json()

            # Verify brave breakdown
            assert data["brave"]["provider"] == "brave"
            assert data["brave"]["amount_usd"] == 1.50
            assert data["brave"]["query_count"] == 100

            # Verify tavily breakdown
            assert data["tavily"]["provider"] == "tavily"
            assert data["tavily"]["amount_usd"] == 3.00
            assert data["tavily"]["query_count"] == 50

            # Verify totals
            assert data["total_usd"] == 4.50
            assert data["total_queries"] == 150

            # Verify period breakdown
            assert data["by_period"]["today"] == 0.10
            assert data["by_period"]["week"] == 1.50
            assert data["by_period"]["month"] == 4.50
            assert data["by_period"]["all_time"] == 4.50

            # Verify daily trend has entries
            assert "daily_trend" in data
            assert len(data["daily_trend"]) == 7  # 7 days

    def test_handles_empty_data(self, client: TestClient):
        """Should handle empty costs gracefully."""
        with patch("backend.api.admin.costs.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Empty results
            mock_cursor.fetchall.side_effect = [
                [],  # No provider totals
                [],  # No daily data
            ]
            mock_cursor.fetchone.return_value = {
                "today": 0,
                "week": 0,
                "month": 0,
                "all_time": 0,
            }

            response = client.get("/api/admin/costs/research")
            assert response.status_code == 200

            data = response.json()
            assert data["brave"]["amount_usd"] == 0
            assert data["brave"]["query_count"] == 0
            assert data["tavily"]["amount_usd"] == 0
            assert data["tavily"]["query_count"] == 0
            assert data["total_usd"] == 0
            assert data["total_queries"] == 0
            assert data["by_period"]["today"] == 0
            assert data["by_period"]["week"] == 0
            assert data["by_period"]["month"] == 0
            assert data["by_period"]["all_time"] == 0

    def test_handles_brave_only_data(self, client: TestClient):
        """Should handle case where only Brave has data."""
        with patch("backend.api.admin.costs.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            # Only Brave data
            mock_cursor.fetchall.side_effect = [
                [{"provider": "brave", "amount": 2.00, "query_count": 150}],
                [],
            ]
            mock_cursor.fetchone.return_value = {
                "today": 0.25,
                "week": 0.75,
                "month": 2.00,
                "all_time": 2.00,
            }

            response = client.get("/api/admin/costs/research")
            assert response.status_code == 200

            data = response.json()
            assert data["brave"]["amount_usd"] == 2.00
            assert data["brave"]["query_count"] == 150
            assert data["tavily"]["amount_usd"] == 0
            assert data["tavily"]["query_count"] == 0
            assert data["total_usd"] == 2.00
            assert data["total_queries"] == 150


class TestResearchCostsResponseShape:
    """Tests for response model shape validation."""

    def test_response_model_fields(self, client: TestClient):
        """Response should include all required fields."""
        with patch("backend.api.admin.costs.db_session") as mock_db_session:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
            mock_db_session.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db_session.return_value.__exit__ = MagicMock(return_value=None)

            mock_cursor.fetchall.side_effect = [[], []]
            mock_cursor.fetchone.return_value = {
                "today": 0,
                "week": 0,
                "month": 0,
                "all_time": 0,
            }

            response = client.get("/api/admin/costs/research")
            assert response.status_code == 200

            data = response.json()

            # Verify top-level fields
            assert "brave" in data
            assert "tavily" in data
            assert "total_usd" in data
            assert "total_queries" in data
            assert "by_period" in data
            assert "daily_trend" in data

            # Verify provider item fields
            for provider in ["brave", "tavily"]:
                assert "provider" in data[provider]
                assert "amount_usd" in data[provider]
                assert "query_count" in data[provider]

            # Verify period fields
            assert "today" in data["by_period"]
            assert "week" in data["by_period"]
            assert "month" in data["by_period"]
            assert "all_time" in data["by_period"]

            # Verify daily trend item fields
            for day in data["daily_trend"]:
                assert "date" in day
                assert "brave" in day
                assert "tavily" in day
                assert "total" in day
