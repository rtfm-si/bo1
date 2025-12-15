"""Tests for admin embeddings API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def admin_headers():
    """Admin API key headers."""
    return {"X-Admin-Key": "test-admin-key"}


class TestEmbeddingsStats:
    """Tests for GET /api/admin/embeddings/stats."""

    def test_get_stats_success(self, client: TestClient, admin_headers: dict):
        """Returns embedding statistics."""
        with (
            patch("backend.api.admin.embeddings.get_embedding_stats") as mock_stats,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_stats.return_value = {
                "total_embeddings": 500,
                "by_type": {
                    "contributions": 300,
                    "research_cache": 150,
                    "context_chunks": 50,
                },
                "dimensions": 1024,
                "storage_estimate_mb": 1.95,
                "umap_available": True,
            }

            response = client.get("/api/admin/embeddings/stats", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["total_embeddings"] == 500
            assert data["by_type"]["contributions"] == 300
            assert data["dimensions"] == 1024
            assert data["umap_available"] is True

    def test_get_stats_requires_admin(self, client: TestClient):
        """Rejects non-admin requests."""
        response = client.get("/api/admin/embeddings/stats")
        assert response.status_code == 403


class TestEmbeddingsSample:
    """Tests for GET /api/admin/embeddings/sample."""

    def test_get_sample_success(self, client: TestClient, admin_headers: dict):
        """Returns 2D embedding sample."""
        with (
            patch("backend.api.admin.embeddings.get_redis_manager") as mock_redis_mgr,
            patch("backend.api.admin.embeddings.compute_2d_coordinates") as mock_compute,
            patch("backend.api.admin.embeddings.get_sample_embeddings") as mock_samples,
            patch("backend.api.admin.embeddings.get_embedding_stats") as mock_stats,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_redis_mgr.return_value.is_available = False  # No cache
            mock_stats.return_value = {"total_embeddings": 1000}
            mock_samples.return_value = [
                {
                    "embedding": [0.1] * 1024,
                    "type": "contribution",
                    "preview": "Test content",
                    "metadata": {"persona": "test"},
                    "created_at": "2025-01-01T00:00:00",
                }
            ]
            mock_compute.return_value = [
                {
                    "x": 0.5,
                    "y": -0.3,
                    "type": "contribution",
                    "preview": "Test content",
                    "metadata": {"persona": "test"},
                    "created_at": "2025-01-01T00:00:00",
                }
            ]

            response = client.get("/api/admin/embeddings/sample", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["method"] == "pca"
            assert data["total_available"] == 1000
            assert len(data["points"]) == 1
            assert data["points"][0]["x"] == 0.5
            assert data["points"][0]["type"] == "contribution"

    def test_get_sample_with_type_filter(self, client: TestClient, admin_headers: dict):
        """Filters by embedding type."""
        with (
            patch("backend.api.admin.embeddings.get_redis_manager") as mock_redis_mgr,
            patch("backend.api.admin.embeddings.compute_2d_coordinates") as mock_compute,
            patch("backend.api.admin.embeddings.get_sample_embeddings") as mock_samples,
            patch("backend.api.admin.embeddings.get_embedding_stats") as mock_stats,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_redis_mgr.return_value.is_available = False
            mock_stats.return_value = {"total_embeddings": 500}
            mock_samples.return_value = []
            mock_compute.return_value = []

            response = client.get(
                "/api/admin/embeddings/sample?embedding_type=contributions",
                headers=admin_headers,
            )

            assert response.status_code == 200
            mock_samples.assert_called_once_with(embedding_type="contributions", limit=500)

    def test_get_sample_with_method_param(self, client: TestClient, admin_headers: dict):
        """Uses requested reduction method."""
        with (
            patch("backend.api.admin.embeddings.get_redis_manager") as mock_redis_mgr,
            patch("backend.api.admin.embeddings.compute_2d_coordinates") as mock_compute,
            patch("backend.api.admin.embeddings.get_sample_embeddings") as mock_samples,
            patch("backend.api.admin.embeddings.get_embedding_stats") as mock_stats,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_redis_mgr.return_value.is_available = False
            mock_stats.return_value = {"total_embeddings": 100}
            mock_samples.return_value = []
            mock_compute.return_value = []

            response = client.get("/api/admin/embeddings/sample?method=umap", headers=admin_headers)

            assert response.status_code == 200
            mock_compute.assert_called_once_with([], method="umap")

    def test_get_sample_cached(self, client: TestClient, admin_headers: dict):
        """Returns cached response when available."""
        import json

        with (
            patch("backend.api.admin.embeddings.get_redis_manager") as mock_redis_mgr,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            cached_data = {
                "points": [
                    {
                        "x": 1.0,
                        "y": 2.0,
                        "type": "research",
                        "preview": "Cached",
                        "metadata": {},
                        "created_at": "2025-01-01T00:00:00",
                    }
                ],
                "method": "pca",
                "total_available": 50,
            }
            mock_redis_client = MagicMock()
            mock_redis_client.get.return_value = json.dumps(cached_data)
            mock_redis_mgr.return_value.is_available = True
            mock_redis_mgr.return_value.redis = mock_redis_client

            response = client.get("/api/admin/embeddings/sample", headers=admin_headers)

            assert response.status_code == 200
            data = response.json()
            assert data["points"][0]["preview"] == "Cached"
            assert data["total_available"] == 50

    def test_get_sample_requires_admin(self, client: TestClient):
        """Rejects non-admin requests."""
        response = client.get("/api/admin/embeddings/sample")
        assert response.status_code == 403

    def test_get_sample_limit_validation(self, client: TestClient, admin_headers: dict):
        """Validates limit parameter bounds."""
        with (
            patch("backend.api.admin.embeddings.get_redis_manager") as mock_redis_mgr,
            patch("backend.api.admin.embeddings.compute_2d_coordinates") as mock_compute,
            patch("backend.api.admin.embeddings.get_sample_embeddings") as mock_samples,
            patch("backend.api.admin.embeddings.get_embedding_stats") as mock_stats,
            patch("backend.api.middleware.admin.verify_admin_key_secure", return_value=True),
            patch("backend.api.middleware.admin.ADMIN_API_KEY", "test-admin-key"),
        ):
            mock_redis_mgr.return_value.is_available = False
            mock_stats.return_value = {"total_embeddings": 100}
            mock_samples.return_value = []
            mock_compute.return_value = []

            # Valid limit
            response = client.get("/api/admin/embeddings/sample?limit=250", headers=admin_headers)
            assert response.status_code == 200

            # Invalid limit (too low)
            response = client.get("/api/admin/embeddings/sample?limit=5", headers=admin_headers)
            assert response.status_code == 422

            # Invalid limit (too high)
            response = client.get("/api/admin/embeddings/sample?limit=2000", headers=admin_headers)
            assert response.status_code == 422
