"""Tests for research cache metrics admin endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import limiter
from bo1.constants import SimilarityCacheThresholds


def mock_admin_override():
    """Override for admin dependency."""
    return "admin-user-id"


@pytest.fixture
def client():
    """Create test client with admin auth override and disabled rate limiting."""
    test_app = app
    test_app.dependency_overrides[require_admin_any] = mock_admin_override

    # Disable rate limiter for tests (to avoid Redis connection)
    original_enabled = limiter.enabled
    limiter.enabled = False

    with TestClient(test_app) as client:
        yield client

    # Restore original limiter state
    limiter.enabled = original_enabled
    test_app.dependency_overrides.clear()


@pytest.fixture
def mock_cache_metrics():
    """Mock cache metrics data."""
    return {
        "hit_rate_1d": 25.0,
        "hit_rate_7d": 30.0,
        "hit_rate_30d": 35.0,
        "total_queries_1d": 100,
        "total_queries_7d": 500,
        "total_queries_30d": 1500,
        "cache_hits_1d": 25,
        "cache_hits_7d": 150,
        "cache_hits_30d": 525,
        "avg_similarity_on_hit": 0.88,
        "miss_distribution": [
            {"bucket": 1, "range_start": 0.70, "range_end": 0.73, "count": 10},
            {"bucket": 2, "range_start": 0.73, "range_end": 0.76, "count": 15},
        ],
        "current_threshold": SimilarityCacheThresholds.RESEARCH_CACHE,
        "recommended_threshold": SimilarityCacheThresholds.RESEARCH_CACHE,
        "recommendation_reason": "Current threshold performing optimally",
        "recommendation_confidence": "high",
        "total_cached_results": 5000,
        "cost_savings_30d": 35.50,
    }


@pytest.fixture
def unauthenticated_client():
    """Create test client without admin auth override."""
    from fastapi import HTTPException

    from backend.api.middleware.auth import get_current_user

    async def _reject():
        raise HTTPException(status_code=401, detail="Not authenticated")

    app.dependency_overrides[get_current_user] = _reject
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


class TestGetResearchCacheMetrics:
    """Tests for GET /api/admin/research-cache/metrics endpoint."""

    def test_returns_metrics_successfully(self, client, mock_cache_metrics):
        """Test successful metrics retrieval."""
        with patch("backend.services.cache_threshold_analyzer.get_full_cache_metrics") as mock_get:
            mock_get.return_value = mock_cache_metrics

            response = client.get("/api/admin/research-cache/metrics")

            assert response.status_code == 200
            data = response.json()

            # Verify all expected fields
            assert data["hit_rate_1d"] == 25.0
            assert data["hit_rate_7d"] == 30.0
            assert data["hit_rate_30d"] == 35.0
            assert data["total_queries_30d"] == 1500
            assert data["cache_hits_30d"] == 525
            assert data["avg_similarity_on_hit"] == 0.88
            assert data["current_threshold"] == SimilarityCacheThresholds.RESEARCH_CACHE
            assert data["recommendation_confidence"] == "high"
            assert len(data["miss_distribution"]) == 2

    def test_requires_admin_auth(self, unauthenticated_client):
        """Test that endpoint requires admin authentication."""
        response = unauthenticated_client.get("/api/admin/research-cache/metrics")
        assert response.status_code in [401, 403]

    def test_miss_distribution_structure(self, client, mock_cache_metrics):
        """Test miss distribution has correct structure."""
        with patch("backend.services.cache_threshold_analyzer.get_full_cache_metrics") as mock_get:
            mock_get.return_value = mock_cache_metrics

            response = client.get("/api/admin/research-cache/metrics")

            data = response.json()
            for bucket in data["miss_distribution"]:
                assert "bucket" in bucket
                assert "range_start" in bucket
                assert "range_end" in bucket
                assert "count" in bucket

    def test_recommendation_fields_present(self, client, mock_cache_metrics):
        """Test all recommendation fields are present."""
        with patch("backend.services.cache_threshold_analyzer.get_full_cache_metrics") as mock_get:
            mock_get.return_value = mock_cache_metrics

            response = client.get("/api/admin/research-cache/metrics")

            data = response.json()
            assert "current_threshold" in data
            assert "recommended_threshold" in data
            assert "recommendation_reason" in data
            assert "recommendation_confidence" in data
            assert data["recommendation_confidence"] in ["low", "medium", "high"]

    def test_handles_service_error(self, client):
        """Test graceful handling of service errors."""
        with patch("backend.services.cache_threshold_analyzer.get_full_cache_metrics") as mock_get:
            mock_get.side_effect = Exception("Database connection failed")

            response = client.get("/api/admin/research-cache/metrics")

            # Should return 500 on service error
            assert response.status_code == 500


class TestGetPromptCacheByType:
    """Tests for GET /api/admin/costs/prompt-cache-by-type endpoint."""

    def test_returns_metrics_successfully(self, client):
        """Test successful metrics retrieval."""
        mock_metrics = [
            {
                "prompt_type": "persona_contribution",
                "cache_hits": 80,
                "cache_misses": 20,
                "cache_hit_rate": 0.8,
                "total_requests": 100,
                "cache_read_tokens": 50000,
                "total_input_tokens": 100000,
                "cache_token_rate": 0.5,
            },
            {
                "prompt_type": "synthesis",
                "cache_hits": 30,
                "cache_misses": 70,
                "cache_hit_rate": 0.3,
                "total_requests": 100,
                "cache_read_tokens": 10000,
                "total_input_tokens": 50000,
                "cache_token_rate": 0.2,
            },
        ]

        with patch("bo1.llm.cost_tracker.CostTracker.get_prompt_type_cache_metrics") as mock_get:
            mock_get.return_value = mock_metrics

            response = client.get("/api/admin/costs/prompt-cache-by-type?days=7")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "items" in data
            assert "total_requests" in data
            assert "overall_cache_hit_rate" in data
            assert "overall_cache_token_rate" in data
            assert "days" in data

            # Verify aggregations
            assert data["total_requests"] == 200
            assert data["overall_cache_hit_rate"] == 0.55  # 110/200
            assert data["days"] == 7
            assert len(data["items"]) == 2

    def test_requires_admin_auth(self, unauthenticated_client):
        """Test that endpoint requires admin authentication."""
        response = unauthenticated_client.get("/api/admin/costs/prompt-cache-by-type")
        assert response.status_code in [401, 403]

    def test_validates_days_parameter(self, client):
        """Test days parameter validation."""
        # Days too high
        response = client.get("/api/admin/costs/prompt-cache-by-type?days=100")
        assert response.status_code == 422  # Validation error

        # Days too low
        response = client.get("/api/admin/costs/prompt-cache-by-type?days=0")
        assert response.status_code == 422

    def test_returns_empty_list_when_no_data(self, client):
        """Test empty response when no cache data exists."""
        with patch("bo1.llm.cost_tracker.CostTracker.get_prompt_type_cache_metrics") as mock_get:
            mock_get.return_value = []

            response = client.get("/api/admin/costs/prompt-cache-by-type")

            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            assert data["total_requests"] == 0
            assert data["overall_cache_hit_rate"] == 0.0

    def test_item_structure(self, client):
        """Test each item has correct structure."""
        mock_metrics = [
            {
                "prompt_type": "decomposition",
                "cache_hits": 50,
                "cache_misses": 50,
                "cache_hit_rate": 0.5,
                "total_requests": 100,
                "cache_read_tokens": 25000,
                "total_input_tokens": 50000,
                "cache_token_rate": 0.5,
            }
        ]

        with patch("bo1.llm.cost_tracker.CostTracker.get_prompt_type_cache_metrics") as mock_get:
            mock_get.return_value = mock_metrics

            response = client.get("/api/admin/costs/prompt-cache-by-type")

            assert response.status_code == 200
            item = response.json()["items"][0]

            # Verify all fields present
            assert item["prompt_type"] == "decomposition"
            assert item["cache_hits"] == 50
            assert item["cache_misses"] == 50
            assert item["cache_hit_rate"] == 0.5
            assert item["total_requests"] == 100
            assert item["cache_read_tokens"] == 25000
            assert item["total_input_tokens"] == 50000
            assert item["cache_token_rate"] == 0.5


class TestGetUnifiedCacheMetrics:
    """Tests for GET /api/admin/costs/cache-metrics endpoint."""

    def test_returns_all_cache_types(self, client):
        """Test unified cache metrics includes all 4 cache types."""
        mock_metrics = {
            "prompt": {"hit_rate": 0.6, "hits": 60, "misses": 40, "total": 100},
            "research": {"hit_rate": 0.7, "hits": 70, "misses": 30, "total": 100},
            "llm": {"hit_rate": 0.5, "hits": 50, "misses": 50, "total": 100},
            "session_metadata": {"hit_rate": 0.8, "hits": 80, "misses": 20, "total": 100},
            "aggregate": {"hit_rate": 0.65, "total_hits": 260, "total_requests": 400},
        }

        with patch("bo1.llm.cost_tracker.CostTracker.get_cache_metrics") as mock_get:
            mock_get.return_value = mock_metrics

            response = client.get("/api/admin/costs/cache-metrics")

            assert response.status_code == 200
            data = response.json()

            # Verify all cache types present
            assert "prompt" in data
            assert "research" in data
            assert "llm" in data
            assert "session_metadata" in data
            assert "aggregate" in data

            # Verify session_metadata structure
            assert data["session_metadata"]["hit_rate"] == 0.8
            assert data["session_metadata"]["hits"] == 80
            assert data["session_metadata"]["misses"] == 20
            assert data["session_metadata"]["total"] == 100

    def test_requires_admin_auth(self, unauthenticated_client):
        """Test that endpoint requires admin authentication."""
        response = unauthenticated_client.get("/api/admin/costs/cache-metrics")
        assert response.status_code in [401, 403]
