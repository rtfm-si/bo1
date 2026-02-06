"""Tests for embedding visualization service."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.embedding_visualizer import (
    compute_2d_coordinates,
    compute_clusters,
    generate_cluster_labels,
    get_distinct_categories,
    get_embedding_stats,
    get_sample_embeddings,
    reduce_dimensions,
)


class TestReduceDimensions:
    """Tests for dimensionality reduction."""

    def test_reduce_empty_embeddings(self):
        """Empty input returns empty output."""
        result = reduce_dimensions([])
        assert result == []

    def test_reduce_single_embedding(self):
        """Single embedding returns single 2D point."""
        embedding = [0.1] * 1024
        result = reduce_dimensions([embedding])
        assert len(result) == 1
        assert len(result[0]) == 2  # 2D output

    def test_reduce_multiple_embeddings_pca(self):
        """Multiple embeddings reduced to 2D with PCA."""
        embeddings = [[float(i) + j * 0.1 for j in range(1024)] for i in range(10)]
        result = reduce_dimensions(embeddings, method="pca")
        assert len(result) == 10
        for point in result:
            assert len(point) == 2

    def test_reduce_dimensions_deterministic(self):
        """PCA reduction is deterministic."""
        embeddings = [[float(i) + j * 0.1 for j in range(1024)] for i in range(5)]
        result1 = reduce_dimensions(embeddings, method="pca")
        result2 = reduce_dimensions(embeddings, method="pca")
        assert result1 == result2

    def test_umap_fallback_to_pca(self):
        """UMAP falls back to PCA when unavailable."""
        embeddings = [[float(i) + j * 0.1 for j in range(1024)] for i in range(5)]
        # Even if we request UMAP, should work (falls back or uses UMAP)
        result = reduce_dimensions(embeddings, method="umap")
        assert len(result) == 5
        for point in result:
            assert len(point) == 2


class TestGetEmbeddingStats:
    """Tests for embedding statistics retrieval."""

    @patch("backend.services.embedding_visualizer.db_session")
    def test_get_stats_empty_database(self, mock_db):
        """Returns zeros when no embeddings exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"contributions": 0, "research": 0},  # single combined query
            {"exists": False},  # context_chunks table check
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        stats = get_embedding_stats()

        assert stats["total_embeddings"] == 0
        assert stats["by_type"]["contributions"] == 0
        assert stats["by_type"]["research_cache"] == 0
        assert stats["dimensions"] == 1024
        assert stats["storage_estimate_mb"] == 0.0

    @patch("backend.services.embedding_visualizer.db_session")
    def test_get_stats_with_embeddings(self, mock_db):
        """Returns correct counts and storage estimates."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"contributions": 100, "research": 50},  # single combined query
            {"exists": True},  # context_chunks table exists
            {"c": 25},  # context_chunks count
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        stats = get_embedding_stats()

        assert stats["total_embeddings"] == 175
        assert stats["by_type"]["contributions"] == 100
        assert stats["by_type"]["research_cache"] == 50
        assert stats["by_type"]["context_chunks"] == 25
        assert stats["dimensions"] == 1024
        # 175 * 1024 * 4 bytes / (1024 * 1024) = ~0.68 MB
        assert stats["storage_estimate_mb"] == pytest.approx(0.68, rel=0.1)


class TestGetSampleEmbeddings:
    """Tests for sample embedding retrieval."""

    @patch("backend.services.embedding_visualizer.db_session")
    def test_get_sample_empty_database(self, mock_db):
        """Returns empty list when no embeddings exist."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = {"exists": False}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        samples = get_sample_embeddings(limit=100)
        assert samples == []

    @patch("backend.services.embedding_visualizer.db_session")
    def test_get_sample_contributions(self, mock_db):
        """Retrieves contribution embeddings with metadata."""
        # Create a mock embedding string
        emb_str = "[" + ",".join(["0.1"] * 1024) + "]"

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "embedding": emb_str,
                "type": "contribution",
                "preview": "Test contribution content",
                "persona_code": "growth_hacker",
                "session_id": "sess123",
                "created_at": "2025-01-01T00:00:00",
            }
        ]
        mock_cursor.fetchone.return_value = {"exists": False}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        samples = get_sample_embeddings(embedding_type="contributions", limit=10)

        assert len(samples) == 1
        assert samples[0]["type"] == "contribution"
        assert samples[0]["preview"] == "Test contribution content"
        assert samples[0]["metadata"]["persona"] == "growth_hacker"
        assert len(samples[0]["embedding"]) == 1024


class TestCompute2DCoordinates:
    """Tests for computing 2D coordinates from samples."""

    def test_empty_samples(self):
        """Empty input returns empty output."""
        result = compute_2d_coordinates([])
        assert result == []

    def test_compute_coordinates(self):
        """Computes 2D coordinates for samples."""
        samples = [
            {
                "embedding": [0.1] * 1024,
                "type": "contribution",
                "preview": "Test 1",
                "metadata": {"persona": "test"},
                "created_at": "2025-01-01T00:00:00",
            },
            {
                "embedding": [0.2] * 1024,
                "type": "research",
                "preview": "Test 2",
                "metadata": {"category": "tech"},
                "created_at": "2025-01-02T00:00:00",
            },
        ]

        result = compute_2d_coordinates(samples, method="pca")

        assert len(result) == 2
        for point in result:
            assert "x" in point
            assert "y" in point
            assert "type" in point
            assert "preview" in point
            assert "metadata" in point
            assert isinstance(point["x"], float)
            assert isinstance(point["y"], float)

    def test_preserves_metadata(self):
        """2D computation preserves original metadata."""
        samples = [
            {
                "embedding": [0.1] * 1024,
                "type": "contribution",
                "preview": "Important content",
                "metadata": {"persona": "strategist", "session_id": "abc123"},
                "created_at": "2025-01-01T12:00:00",
            }
        ]

        result = compute_2d_coordinates(samples)

        assert result[0]["type"] == "contribution"
        assert result[0]["preview"] == "Important content"
        assert result[0]["metadata"]["persona"] == "strategist"
        assert result[0]["created_at"] == "2025-01-01T12:00:00"


class TestComputeClusters:
    """Tests for K-means clustering."""

    def test_too_few_points_returns_single_cluster(self):
        """Less than 20 points returns all points in cluster 0."""
        coords = [(float(i), float(i * 2)) for i in range(10)]
        assignments, centroids = compute_clusters(coords)
        assert len(assignments) == 10
        assert all(a == 0 for a in assignments)
        assert len(centroids) == 1

    def test_clusters_with_sufficient_points(self):
        """20+ points produces multiple clusters."""
        # Create two distinct clusters
        coords = [(0.0, 0.0)] * 15 + [(100.0, 100.0)] * 15
        assignments, centroids = compute_clusters(coords)
        assert len(assignments) == 30
        assert len(centroids) >= 2
        # Should have exactly 2 cluster IDs
        unique_clusters = set(assignments)
        assert len(unique_clusters) >= 2

    def test_cluster_assignments_match_centroid_count(self):
        """Each cluster ID maps to a centroid."""
        coords = [(float(i % 3), float(i // 3)) for i in range(30)]
        assignments, centroids = compute_clusters(coords)
        unique_clusters = set(assignments)
        # Every cluster ID should be < len(centroids)
        for cluster_id in unique_clusters:
            assert 0 <= cluster_id < len(centroids)


class TestGenerateClusterLabels:
    """Tests for cluster label generation."""

    def test_generates_labels_for_each_cluster(self):
        """Returns a label for every cluster."""
        assignments = [0, 0, 0, 1, 1, 1]
        previews = [
            "saas metrics growth",
            "saas metrics revenue",
            "saas metrics churn",
            "pricing strategy tier",
            "pricing strategy plan",
            "pricing model",
        ]
        centroids = [(0.0, 0.0), (10.0, 10.0)]
        coords = [(0.0, 0.0), (0.1, 0.1), (0.2, 0.2), (10.0, 10.0), (10.1, 10.1), (10.2, 10.2)]

        labels = generate_cluster_labels(assignments, previews, centroids, coords)

        assert len(labels) == 2
        assert 0 in labels
        assert 1 in labels
        assert isinstance(labels[0], str)
        assert isinstance(labels[1], str)

    def test_fallback_label_for_empty_cluster(self):
        """Falls back to 'Cluster N' when no pattern found."""
        assignments = [0]
        previews = ["x"]
        centroids = [(0.0, 0.0), (10.0, 10.0)]  # Second cluster empty
        coords = [(0.0, 0.0)]

        labels = generate_cluster_labels(assignments, previews, centroids, coords)

        assert 1 in labels
        assert "Cluster" in labels[1]

    def test_extracts_common_ngrams(self):
        """Picks label from repeated 2-word patterns."""
        assignments = [0, 0, 0, 0, 0]
        previews = [
            "market trends analysis for saas",
            "market trends overview today",
            "market trends report 2025",
            "market trends prediction model",
            "market trends forecast quarterly",
        ]
        centroids = [(0.0, 0.0)]
        coords = [(0.0, 0.0), (0.1, 0.1), (0.2, 0.2), (0.3, 0.3), (0.4, 0.4)]

        labels = generate_cluster_labels(assignments, previews, centroids, coords)

        # Should find "market trends" as common pattern
        assert "Market Trends" in labels[0]


class TestGetDistinctCategories:
    """Tests for category retrieval."""

    @patch("backend.services.embedding_visualizer.db_session")
    def test_returns_categories_with_counts(self, mock_db):
        """Returns category list sorted by count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"category": "saas_metrics", "count": 50},
            {"category": "pricing", "count": 30},
            {"category": "competitors", "count": 10},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        categories = get_distinct_categories()

        assert len(categories) == 3
        assert categories[0]["category"] == "saas_metrics"
        assert categories[0]["count"] == 50

    @patch("backend.services.embedding_visualizer.db_session")
    def test_returns_empty_when_no_categories(self, mock_db):
        """Returns empty list when no embeddings with categories."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        categories = get_distinct_categories()

        assert categories == []


class TestGetSampleEmbeddingsWithCategory:
    """Tests for category filtering in sample retrieval."""

    @patch("backend.services.embedding_visualizer.db_session")
    def test_filters_by_category(self, mock_db):
        """Passes category to SQL query when provided."""
        emb_str = "[" + ",".join(["0.1"] * 1024) + "]"
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "embedding": emb_str,
                "type": "research",
                "preview": "Filtered research",
                "category": "saas_metrics",
                "industry": "tech",
                "created_at": "2025-01-01T00:00:00",
            }
        ]
        mock_cursor.fetchone.return_value = {"exists": False}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        samples = get_sample_embeddings(
            embedding_type="research", limit=10, category="saas_metrics"
        )

        # Verify SQL was called with category parameter
        call_args = mock_cursor.execute.call_args_list
        # Find the research cache query call
        research_call = [c for c in call_args if "saas_metrics" in str(c)]
        assert len(research_call) > 0
        assert len(samples) == 1
        assert samples[0]["metadata"]["category"] == "saas_metrics"
