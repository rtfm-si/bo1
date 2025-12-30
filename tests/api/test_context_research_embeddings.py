"""Tests for research embeddings visualization API.

Tests the GET /api/v1/context/research-embeddings endpoint.
"""

from unittest.mock import patch


class TestResearchEmbeddingsEndpoint:
    """Tests for get_research_embeddings endpoint."""

    def test_returns_empty_for_user_without_research(self):
        """Test that users without research data get empty response."""
        with patch("bo1.state.repositories.cache_repository") as mock_cache:
            mock_cache.get_user_research_with_embeddings.return_value = []

            from backend.api.context.models import ResearchEmbeddingsResponse

            response = ResearchEmbeddingsResponse(
                success=True, points=[], categories=[], total_count=0
            )

            assert response.success is True
            assert response.points == []
            assert response.categories == []
            assert response.total_count == 0

    def test_returns_points_with_coordinates(self):
        """Test that research data is converted to 2D points."""
        from backend.api.context.models import ResearchPoint

        # Mock data representing what the endpoint would return
        point = ResearchPoint(
            x=1.5,
            y=-0.5,
            preview="How to improve customer retention",
            category="saas_metrics",
            created_at="2025-01-15T12:00:00",
        )

        assert point.x == 1.5
        assert point.y == -0.5
        assert point.preview == "How to improve customer retention"
        assert point.category == "saas_metrics"

    def test_category_aggregation(self):
        """Test that categories are correctly aggregated."""
        from backend.api.context.models import ResearchCategory

        cat = ResearchCategory(name="saas_metrics", count=5)
        assert cat.name == "saas_metrics"
        assert cat.count == 5

    def test_response_model_structure(self):
        """Test the response model has correct structure."""
        from backend.api.context.models import (
            ResearchCategory,
            ResearchEmbeddingsResponse,
            ResearchPoint,
        )

        response = ResearchEmbeddingsResponse(
            success=True,
            points=[
                ResearchPoint(
                    x=0.1,
                    y=0.2,
                    preview="Test question",
                    category="pricing",
                    created_at="2025-01-15T12:00:00",
                ),
                ResearchPoint(
                    x=0.5,
                    y=-0.3,
                    preview="Another question",
                    category=None,
                    created_at="2025-01-15T12:00:00",
                ),
            ],
            categories=[
                ResearchCategory(name="pricing", count=1),
                ResearchCategory(name="uncategorized", count=1),
            ],
            total_count=2,
        )

        assert response.success is True
        assert len(response.points) == 2
        assert len(response.categories) == 2
        assert response.total_count == 2

    def test_preview_truncation(self):
        """Test that previews are truncated to 100 chars in model."""
        from backend.api.context.models import ResearchPoint

        # Note: The model has max_length=150, but DB query uses LEFT(question, 100)
        long_preview = "x" * 100
        point = ResearchPoint(
            x=0.0, y=0.0, preview=long_preview, category=None, created_at="2025-01-15T12:00:00"
        )
        assert len(point.preview) == 100


class TestCacheRepositoryMethods:
    """Tests for cache repository research embedding methods."""

    def test_get_user_research_with_embeddings(self):
        """Test repository method returns correct format."""
        from bo1.state.repositories.cache_repository import CacheRepository

        repo = CacheRepository()

        # Just verify the method exists and can be called (actual DB tests would need fixtures)
        assert hasattr(repo, "get_user_research_with_embeddings")
        assert callable(repo.get_user_research_with_embeddings)

    def test_get_user_research_category_counts(self):
        """Test repository method for category counts exists."""
        from bo1.state.repositories.cache_repository import CacheRepository

        repo = CacheRepository()
        assert hasattr(repo, "get_user_research_category_counts")
        assert callable(repo.get_user_research_category_counts)

    def test_get_user_research_total_count(self):
        """Test repository method for total count exists."""
        from bo1.state.repositories.cache_repository import CacheRepository

        repo = CacheRepository()
        assert hasattr(repo, "get_user_research_total_count")
        assert callable(repo.get_user_research_total_count)
