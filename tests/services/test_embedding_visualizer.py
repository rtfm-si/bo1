"""Tests for embedding visualization service."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.embedding_visualizer import (
    compute_2d_coordinates,
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
            {"count": 0},  # contributions
            {"count": 0},  # research_cache
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
            {"count": 100},  # contributions
            {"count": 50},  # research_cache
            {"exists": True},  # context_chunks table exists
            {"count": 25},  # context_chunks
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
