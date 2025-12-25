"""Tests for admin drill-down API endpoints.

Tests:
- GET /api/admin/drilldown/users
- GET /api/admin/drilldown/costs
- GET /api/admin/drilldown/waitlist
- GET /api/admin/drilldown/whitelist
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin.drilldown import limiter, router
from backend.api.middleware.admin import require_admin_any


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "admin-user-id"


@pytest.fixture
def app():
    """Create test app with drilldown router and admin auth override."""
    # Disable rate limiter for tests
    original_enabled = limiter.enabled
    limiter.enabled = False

    test_app = FastAPI()
    test_app.dependency_overrides[require_admin_any] = mock_admin_override
    test_app.include_router(router, prefix="/api/admin")

    yield test_app

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


def _make_mock_db():
    """Create mock db_session context manager."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=None)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
    return mock_cursor, mock_conn


class TestUsersDrillDown:
    """Tests for GET /api/admin/drilldown/users."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/users")
        assert response.status_code == 403

    def test_returns_users_list(self, client: TestClient):
        """Admin should get paginated user list."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 2
            mock_query.return_value = [
                {
                    "id": "user_1",
                    "email": "user1@example.com",
                    "subscription_tier": "free",
                    "is_admin": False,
                    "created_at": datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
                },
                {
                    "id": "user_2",
                    "email": "user2@example.com",
                    "subscription_tier": "pro",
                    "is_admin": True,
                    "created_at": datetime(2025, 1, 14, 10, 0, 0, tzinfo=UTC),
                },
            ]

            response = client.get("/api/admin/drilldown/users?period=day&limit=10")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 2
            assert data["limit"] == 10
            assert data["offset"] == 0
            assert data["period"] == "day"
            assert len(data["items"]) == 2
            assert data["items"][0]["user_id"] == "user_1"
            assert data["items"][0]["email"] == "user1@example.com"

    def test_pagination_params(self, client: TestClient):
        """Should respect limit and offset params."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 50
            mock_query.return_value = []

            response = client.get("/api/admin/drilldown/users?limit=20&offset=10")
            assert response.status_code == 200

            data = response.json()
            assert data["limit"] == 20
            assert data["offset"] == 10
            assert data["has_more"] is True
            assert data["next_offset"] == 30

    def test_time_period_filter(self, client: TestClient):
        """Should support all time period values."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 0
            mock_query.return_value = []

            for period in ["hour", "day", "week", "month", "all"]:
                response = client.get(f"/api/admin/drilldown/users?period={period}")
                assert response.status_code == 200
                assert response.json()["period"] == period


class TestCostsDrillDown:
    """Tests for GET /api/admin/drilldown/costs."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/costs")
        assert response.status_code == 403

    def test_returns_costs_list(self, client: TestClient):
        """Admin should get paginated cost list."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            # First call for stats, second for items
            mock_query.side_effect = [
                {"count": 3, "total": 1.50},  # stats query
                [
                    {
                        "id": 1,
                        "user_id": "user_1",
                        "email": "user1@example.com",
                        "provider": "anthropic",
                        "model": "claude-3-haiku",
                        "cost_usd": 0.50,
                        "created_at": datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
                    },
                    {
                        "id": 2,
                        "user_id": "user_2",
                        "email": "user2@example.com",
                        "provider": "anthropic",
                        "model": "claude-3-sonnet",
                        "cost_usd": 1.00,
                        "created_at": datetime(2025, 1, 15, 11, 0, 0, tzinfo=UTC),
                    },
                ],
            ]

            response = client.get("/api/admin/drilldown/costs?period=day")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 3
            assert data["total_cost_usd"] == 1.50
            assert data["period"] == "day"
            assert len(data["items"]) == 2
            assert data["items"][0]["provider"] == "anthropic"
            assert data["items"][0]["amount_usd"] == 0.50

    def test_handles_null_user_id(self, client: TestClient):
        """Should handle costs without user_id."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.side_effect = [
                {"count": 1, "total": 0.10},
                [
                    {
                        "id": 1,
                        "user_id": None,
                        "email": None,
                        "provider": "openai",
                        "model": "gpt-4",
                        "cost_usd": 0.10,
                        "created_at": datetime(2025, 1, 15, tzinfo=UTC),
                    },
                ],
            ]

            response = client.get("/api/admin/drilldown/costs")
            assert response.status_code == 200

            data = response.json()
            assert data["items"][0]["user_id"] == "unknown"
            assert data["items"][0]["email"] is None


class TestWaitlistDrillDown:
    """Tests for GET /api/admin/drilldown/waitlist."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/waitlist")
        assert response.status_code == 403

    def test_returns_waitlist_entries(self, client: TestClient):
        """Admin should get paginated waitlist."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 2
            mock_query.return_value = [
                {
                    "id": "uuid-1",
                    "email": "wait1@example.com",
                    "status": "pending",
                    "source": "landing_page",
                    "created_at": datetime(2025, 1, 15, tzinfo=UTC),
                },
                {
                    "id": "uuid-2",
                    "email": "wait2@example.com",
                    "status": "invited",
                    "source": "referral",
                    "created_at": datetime(2025, 1, 14, tzinfo=UTC),
                },
            ]

            response = client.get("/api/admin/drilldown/waitlist?period=week")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 2
            assert data["period"] == "week"
            assert len(data["items"]) == 2
            assert data["items"][0]["email"] == "wait1@example.com"
            assert data["items"][0]["status"] == "pending"


class TestWhitelistDrillDown:
    """Tests for GET /api/admin/drilldown/whitelist."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/whitelist")
        assert response.status_code == 403

    def test_returns_whitelist_entries(self, client: TestClient):
        """Admin should get paginated whitelist."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 2
            mock_query.return_value = [
                {
                    "id": "uuid-1",
                    "email": "beta1@example.com",
                    "added_by": "admin@example.com",
                    "notes": "YC W25",
                    "created_at": datetime(2025, 1, 15, tzinfo=UTC),
                },
                {
                    "id": "uuid-2",
                    "email": "beta2@example.com",
                    "added_by": None,
                    "notes": None,
                    "created_at": datetime(2025, 1, 14, tzinfo=UTC),
                },
            ]

            response = client.get("/api/admin/drilldown/whitelist?period=month")
            assert response.status_code == 200

            data = response.json()
            assert data["total"] == 2
            assert data["period"] == "month"
            assert len(data["items"]) == 2
            assert data["items"][0]["email"] == "beta1@example.com"
            assert data["items"][0]["added_by"] == "admin@example.com"
            assert data["items"][0]["notes"] == "YC W25"


class TestTimePeriodFilter:
    """Tests for time period filter logic."""

    def test_get_time_filter_hour(self):
        """Hour filter should use 1 hour interval."""
        from backend.api.admin.drilldown import TimePeriod, _get_time_filter

        result = _get_time_filter(TimePeriod.HOUR)
        assert "1 hour" in result

    def test_get_time_filter_day(self):
        """Day filter should use 1 day interval."""
        from backend.api.admin.drilldown import TimePeriod, _get_time_filter

        result = _get_time_filter(TimePeriod.DAY)
        assert "1 day" in result

    def test_get_time_filter_week(self):
        """Week filter should use 7 days interval."""
        from backend.api.admin.drilldown import TimePeriod, _get_time_filter

        result = _get_time_filter(TimePeriod.WEEK)
        assert "7 days" in result

    def test_get_time_filter_month(self):
        """Month filter should use 30 days interval."""
        from backend.api.admin.drilldown import TimePeriod, _get_time_filter

        result = _get_time_filter(TimePeriod.MONTH)
        assert "30 days" in result

    def test_get_time_filter_all(self):
        """All filter should return TRUE (no filter)."""
        from backend.api.admin.drilldown import TimePeriod, _get_time_filter

        result = _get_time_filter(TimePeriod.ALL)
        assert result == "TRUE"


class TestPaginationHelpers:
    """Tests for pagination calculation."""

    def test_has_more_when_more_items(self, client: TestClient):
        """has_more should be true when more items exist."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 50
            mock_query.return_value = []

            response = client.get("/api/admin/drilldown/users?limit=10&offset=0")
            data = response.json()

            assert data["has_more"] is True
            assert data["next_offset"] == 10

    def test_no_more_when_end_reached(self, client: TestClient):
        """has_more should be false at end of list."""
        with (
            patch("backend.api.admin.drilldown.get_single_value") as mock_count,
            patch("backend.api.admin.drilldown.execute_query") as mock_query,
        ):
            mock_count.return_value = 5
            mock_query.return_value = []

            response = client.get("/api/admin/drilldown/users?limit=10&offset=0")
            data = response.json()

            assert data["has_more"] is False
            assert data["next_offset"] is None


class TestLimitValidation:
    """Tests for query param validation."""

    def test_limit_min(self, client: TestClient):
        """Limit below 1 should fail validation."""
        with (
            patch("backend.api.admin.drilldown.get_single_value"),
            patch("backend.api.admin.drilldown.execute_query"),
        ):
            response = client.get("/api/admin/drilldown/users?limit=0")
            assert response.status_code == 422

    def test_limit_max(self, client: TestClient):
        """Limit above 100 should fail validation."""
        with (
            patch("backend.api.admin.drilldown.get_single_value"),
            patch("backend.api.admin.drilldown.execute_query"),
        ):
            response = client.get("/api/admin/drilldown/users?limit=101")
            assert response.status_code == 422

    def test_offset_negative(self, client: TestClient):
        """Negative offset should fail validation."""
        with (
            patch("backend.api.admin.drilldown.get_single_value"),
            patch("backend.api.admin.drilldown.execute_query"),
        ):
            response = client.get("/api/admin/drilldown/users?offset=-1")
            assert response.status_code == 422
