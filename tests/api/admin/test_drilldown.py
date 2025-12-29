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
                        "model_name": "claude-3-haiku",
                        "total_cost": 0.50,
                        "created_at": datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
                    },
                    {
                        "id": 2,
                        "user_id": "user_2",
                        "email": "user2@example.com",
                        "provider": "anthropic",
                        "model_name": "claude-3-sonnet",
                        "total_cost": 1.00,
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
                        "model_name": "gpt-4",
                        "total_cost": 0.10,
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


# =============================================================================
# Insight Drill-Down Tests
# =============================================================================


class TestCacheEffectivenessDrillDown:
    """Tests for GET /api/admin/drilldown/cache-effectiveness."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/cache-effectiveness")
        assert response.status_code == 403

    def test_returns_cache_effectiveness_data(self, client: TestClient):
        """Admin should get cache effectiveness buckets."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            # First call: bucket aggregation, second call: overall stats
            mock_query.side_effect = [
                [
                    {
                        "bucket": 1,
                        "session_count": 10,
                        "avg_cost": 0.25,
                        "total_cost": 2.50,
                        "total_saved": 0.50,
                        "avg_savings": 0.05,
                        "bucket_hit_rate": 0.15,
                    },
                    {
                        "bucket": 4,
                        "session_count": 20,
                        "avg_cost": 0.10,
                        "total_cost": 2.00,
                        "total_saved": 1.50,
                        "avg_savings": 0.075,
                        "bucket_hit_rate": 0.85,
                    },
                ],
                {"hit_rate": 0.55},  # overall stats
            ]

            response = client.get("/api/admin/drilldown/cache-effectiveness?period=week")
            assert response.status_code == 200

            data = response.json()
            assert data["period"] == "week"
            assert data["total_sessions"] == 30
            assert len(data["buckets"]) == 2
            assert data["buckets"][0]["bucket_label"] == "0-25%"
            assert data["buckets"][0]["session_count"] == 10
            assert data["overall_hit_rate"] == 0.55

    def test_handles_empty_data(self, client: TestClient):
        """Should handle empty cache data gracefully."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.side_effect = [[], {"hit_rate": None}]

            response = client.get("/api/admin/drilldown/cache-effectiveness")
            assert response.status_code == 200

            data = response.json()
            assert data["total_sessions"] == 0
            assert data["buckets"] == []
            assert data["overall_hit_rate"] == 0


class TestModelImpactDrillDown:
    """Tests for GET /api/admin/drilldown/model-impact."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/model-impact")
        assert response.status_code == 403

    def test_returns_model_impact_data(self, client: TestClient):
        """Admin should get model impact analysis."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.return_value = [
                {
                    "model_name": "claude-3-5-sonnet",
                    "request_count": 100,
                    "total_cost": 5.00,
                    "avg_cost": 0.05,
                    "cache_hit_rate": 0.40,
                    "total_tokens": 500000,
                },
                {
                    "model_name": "claude-3-haiku",
                    "request_count": 50,
                    "total_cost": 0.50,
                    "avg_cost": 0.01,
                    "cache_hit_rate": 0.60,
                    "total_tokens": 100000,
                },
            ]

            response = client.get("/api/admin/drilldown/model-impact?period=week")
            assert response.status_code == 200

            data = response.json()
            assert data["period"] == "week"
            assert data["total_requests"] == 150
            assert data["total_cost"] == 5.50
            assert len(data["models"]) == 2
            assert data["models"][0]["model_display"] == "Claude Sonnet"
            assert data["cost_if_all_opus"] > data["cost_if_all_haiku"]
            assert data["savings_from_model_mix"] > 0

    def test_handles_empty_model_data(self, client: TestClient):
        """Should handle empty model data gracefully."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.return_value = []

            response = client.get("/api/admin/drilldown/model-impact")
            assert response.status_code == 200

            data = response.json()
            assert data["total_requests"] == 0
            assert data["models"] == []


class TestFeatureEfficiencyDrillDown:
    """Tests for GET /api/admin/drilldown/feature-efficiency."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/feature-efficiency")
        assert response.status_code == 403

    def test_returns_feature_efficiency_data(self, client: TestClient):
        """Admin should get feature efficiency stats."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.return_value = [
                {
                    "feature": "deliberation",
                    "request_count": 200,
                    "total_cost": 10.00,
                    "avg_cost": 0.05,
                    "cache_hit_rate": 0.35,
                    "unique_sessions": 50,
                },
                {
                    "feature": "research",
                    "request_count": 100,
                    "total_cost": 2.00,
                    "avg_cost": 0.02,
                    "cache_hit_rate": 0.70,
                    "unique_sessions": 30,
                },
            ]

            response = client.get("/api/admin/drilldown/feature-efficiency?period=month")
            assert response.status_code == 200

            data = response.json()
            assert data["period"] == "month"
            assert data["total_requests"] == 300
            assert data["total_cost"] == 12.00
            assert len(data["features"]) == 2
            assert data["features"][0]["feature"] == "deliberation"
            assert data["features"][0]["cost_per_session"] == 0.20


class TestTuningRecommendations:
    """Tests for GET /api/admin/drilldown/tuning-recommendations."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/tuning-recommendations")
        assert response.status_code == 403

    def test_returns_recommendations(self, client: TestClient):
        """Admin should get tuning recommendations."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            # Stats query, model stats query, feature stats query
            mock_query.side_effect = [
                {
                    "total_requests": 1000,
                    "total_sessions": 100,
                    "cache_hit_rate": 0.25,
                    "total_cost": 50.00,
                    "total_saved": 5.00,
                },
                [
                    {"model_tier": "opus", "count": 600, "cost": 45.00},
                    {"model_tier": "sonnet", "count": 300, "cost": 4.50},
                    {"model_tier": "haiku", "count": 100, "cost": 0.50},
                ],
                [],
            ]

            response = client.get("/api/admin/drilldown/tuning-recommendations")
            assert response.status_code == 200

            data = response.json()
            assert data["analysis_period_days"] == 30
            assert data["data_quality"] == "sufficient"
            assert len(data["recommendations"]) >= 1
            # Should recommend improving cache hit rate since it's 25%
            cache_recs = [r for r in data["recommendations"] if r["area"] == "cache"]
            assert len(cache_recs) >= 1

    def test_insufficient_data_quality(self, client: TestClient):
        """Should indicate insufficient data when sample size is low."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.side_effect = [
                {
                    "total_requests": 50,
                    "total_sessions": 10,
                    "cache_hit_rate": 0.50,
                    "total_cost": 1.00,
                    "total_saved": 0.10,
                },
                [],
                [],
            ]

            response = client.get("/api/admin/drilldown/tuning-recommendations")
            assert response.status_code == 200

            data = response.json()
            assert data["data_quality"] == "insufficient"


class TestQualityIndicators:
    """Tests for GET /api/admin/drilldown/quality-indicators."""

    def test_returns_403_without_admin(self, main_app_client: TestClient):
        """Non-admin users should get 403."""
        response = main_app_client.get("/api/admin/drilldown/quality-indicators")
        assert response.status_code == 403

    def test_returns_quality_indicators(self, client: TestClient):
        """Admin should get quality indicator stats."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.return_value = {
                "total_sessions": 100,
                "avg_hit_rate": 0.45,
                "continuation_rate": 0.60,
                "cached_continuation": 0.65,
                "uncached_continuation": 0.55,
            }

            response = client.get("/api/admin/drilldown/quality-indicators?period=month")
            assert response.status_code == 200

            data = response.json()
            assert data["period"] == "month"
            assert data["sample_size"] == 100
            assert data["overall_cache_hit_rate"] == 0.45
            assert data["session_continuation_rate"] == 0.60
            assert data["cached_continuation_rate"] == 0.65
            assert data["uncached_continuation_rate"] == 0.55
            # Correlation should be positive since cached > uncached
            assert abs(data["correlation_score"] - 0.10) < 0.001
            assert "quality_assessment" in data

    def test_handles_insufficient_data(self, client: TestClient):
        """Should indicate insufficient data for quality assessment."""
        with patch("backend.api.admin.drilldown.execute_query") as mock_query:
            mock_query.return_value = {
                "total_sessions": 20,
                "avg_hit_rate": 0.50,
                "continuation_rate": 0.50,
                "cached_continuation": None,
                "uncached_continuation": None,
            }

            response = client.get("/api/admin/drilldown/quality-indicators")
            assert response.status_code == 200

            data = response.json()
            assert data["sample_size"] == 20
            assert "Insufficient data" in data["quality_assessment"]
