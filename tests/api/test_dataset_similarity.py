"""Tests for dataset similarity endpoint."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.api.datasets as datasets_module
from backend.services.dataset_similarity import SimilarDataset


def mock_user_override():
    """Override auth to return test user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def mock_repo():
    """Create mock dataset repository."""
    return MagicMock()


@pytest.fixture
def mock_similar_datasets():
    """Create mock similar dataset results."""
    return [
        SimilarDataset(
            dataset_id="ds-similar-1",
            name="Sales Data Q1",
            similarity=0.85,
            shared_columns=["revenue", "date", "region"],
            insight_preview="Monthly sales breakdown by region",
        ),
        SimilarDataset(
            dataset_id="ds-similar-2",
            name="Revenue Report",
            similarity=0.72,
            shared_columns=["revenue", "date"],
            insight_preview=None,
        ),
    ]


@pytest.fixture
def test_client(mock_repo):
    """Create test client with mocked dependencies."""
    from backend.api.datasets import router
    from backend.api.middleware.auth import get_current_user

    # Store original repo
    original_repo = datasets_module.dataset_repository

    # Replace with mock
    datasets_module.dataset_repository = mock_repo

    app = FastAPI()
    app.dependency_overrides[get_current_user] = mock_user_override
    # Router already has /v1/datasets prefix, only add /api
    app.include_router(router, prefix="/api")

    yield TestClient(app)

    # Restore original
    datasets_module.dataset_repository = original_repo


class TestSimilarDatasetsEndpoint:
    """Tests for GET /api/v1/datasets/{dataset_id}/similar."""

    def test_returns_similar_datasets(self, test_client, mock_repo, mock_similar_datasets):
        """Should return list of similar datasets."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source Dataset"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = mock_similar_datasets

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar")

        assert response.status_code == 200
        data = response.json()
        assert "similar" in data
        assert len(data["similar"]) == 2
        assert data["query_dataset_id"] == "ds-source"
        assert data["threshold"] == 0.6

    def test_similar_dataset_structure(self, test_client, mock_repo, mock_similar_datasets):
        """Should return properly structured similar dataset items."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source Dataset"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = mock_similar_datasets

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar")

        data = response.json()
        first = data["similar"][0]
        assert first["dataset_id"] == "ds-similar-1"
        assert first["name"] == "Sales Data Q1"
        assert first["similarity"] == 0.85
        assert first["shared_columns"] == ["revenue", "date", "region"]
        assert first["insight_preview"] == "Monthly sales breakdown by region"

    def test_returns_404_for_nonexistent_dataset(self, test_client, mock_repo):
        """Should return 404 if source dataset not found."""
        mock_repo.get_by_id.return_value = None

        response = test_client.get("/api/v1/datasets/nonexistent/similar")

        assert response.status_code == 404
        detail = response.json()["detail"]
        # Handle both string and dict error formats
        if isinstance(detail, dict):
            assert "not found" in detail.get("message", "").lower()
        else:
            assert "not found" in detail.lower()

    def test_respects_threshold_parameter(self, test_client, mock_repo):
        """Should pass threshold parameter to service."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = []

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar?threshold=0.8")

        assert response.status_code == 200
        mock_service.find_similar_datasets.assert_called_once()
        call_kwargs = mock_service.find_similar_datasets.call_args[1]
        assert call_kwargs["threshold"] == 0.8
        assert response.json()["threshold"] == 0.8

    def test_respects_limit_parameter(self, test_client, mock_repo):
        """Should pass limit parameter to service."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = []

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar?limit=3")

        assert response.status_code == 200
        mock_service.find_similar_datasets.assert_called_once()
        call_kwargs = mock_service.find_similar_datasets.call_args[1]
        assert call_kwargs["limit"] == 3

    def test_validates_threshold_lower_bound(self, test_client, mock_repo):
        """Should reject threshold below 0.4."""
        response = test_client.get("/api/v1/datasets/ds-source/similar?threshold=0.3")
        assert response.status_code == 422

    def test_validates_threshold_upper_bound(self, test_client, mock_repo):
        """Should reject threshold above 0.9."""
        response = test_client.get("/api/v1/datasets/ds-source/similar?threshold=0.95")
        assert response.status_code == 422

    def test_validates_limit_lower_bound(self, test_client, mock_repo):
        """Should reject limit below 1."""
        response = test_client.get("/api/v1/datasets/ds-source/similar?limit=0")
        assert response.status_code == 422

    def test_validates_limit_upper_bound(self, test_client, mock_repo):
        """Should reject limit above 10."""
        response = test_client.get("/api/v1/datasets/ds-source/similar?limit=15")
        assert response.status_code == 422

    def test_returns_empty_when_no_similar_datasets(self, test_client, mock_repo):
        """Should return empty list when no similar datasets found."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = []

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar")

        assert response.status_code == 200
        data = response.json()
        assert data["similar"] == []
        assert data["query_dataset_id"] == "ds-source"

    def test_passes_user_id_to_service(self, test_client, mock_repo):
        """Should pass authenticated user ID to service."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = []

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar")

        assert response.status_code == 200
        mock_service.find_similar_datasets.assert_called_once()
        call_kwargs = mock_service.find_similar_datasets.call_args[1]
        assert call_kwargs["user_id"] == "test-user-123"

    def test_handles_null_insight_preview(self, test_client, mock_repo):
        """Should correctly serialize null insight_preview."""
        mock_repo.get_by_id.return_value = {"id": "ds-source", "name": "Source"}
        mock_service = MagicMock()
        mock_service.find_similar_datasets.return_value = [
            SimilarDataset(
                dataset_id="ds-1",
                name="Dataset 1",
                similarity=0.8,
                shared_columns=[],
                insight_preview=None,
            )
        ]

        with patch(
            "backend.services.dataset_similarity.get_similarity_service",
            return_value=mock_service,
        ):
            response = test_client.get("/api/v1/datasets/ds-source/similar")

        assert response.status_code == 200
        data = response.json()
        assert data["similar"][0]["insight_preview"] is None
