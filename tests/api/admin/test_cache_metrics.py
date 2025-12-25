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
    return TestClient(app)


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
