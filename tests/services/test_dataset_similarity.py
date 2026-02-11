"""Tests for dataset similarity service."""

from unittest.mock import MagicMock, patch

from backend.services.dataset_similarity import (
    EMBEDDING_CACHE_PREFIX,
    EMBEDDING_CACHE_TTL,
    MAX_COLUMNS_FOR_EMBEDDING,
    DatasetSimilarityService,
    SimilarDataset,
    get_similarity_service,
)


class TestBuildDatasetText:
    """Tests for _build_dataset_text method."""

    def test_builds_text_from_name_only(self):
        """Should include dataset name."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        dataset = {"name": "Sales Data 2024"}

        result = service._build_dataset_text(dataset)

        assert "Dataset: Sales Data 2024" in result

    def test_includes_description_when_present(self):
        """Should include description if provided."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        dataset = {
            "name": "Sales Data",
            "description": "Monthly sales metrics for Q4",
        }

        result = service._build_dataset_text(dataset)

        assert "Description: Monthly sales metrics for Q4" in result

    def test_includes_summary_when_present(self):
        """Should include summary if provided."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        dataset = {
            "name": "Sales Data",
            "summary": "Contains 1000 transactions across 5 regions",
        }

        result = service._build_dataset_text(dataset)

        assert "Summary: Contains 1000 transactions across 5 regions" in result

    def test_includes_column_names_from_profiles(self):
        """Should include column names from profiles."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        dataset = {"name": "Sales Data"}
        profiles = [
            {"column_name": "revenue"},
            {"column_name": "date"},
            {"column_name": "region"},
        ]

        result = service._build_dataset_text(dataset, profiles=profiles)

        assert "Columns: revenue, date, region" in result

    def test_truncates_columns_to_max_limit(self):
        """Should truncate column list to MAX_COLUMNS_FOR_EMBEDDING."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        dataset = {"name": "Wide Data"}
        profiles = [{"column_name": f"col_{i}"} for i in range(100)]

        result = service._build_dataset_text(dataset, profiles=profiles)

        # Should have exactly MAX_COLUMNS_FOR_EMBEDDING columns
        columns_line = [line for line in result.split("\n") if line.startswith("Columns:")]
        assert len(columns_line) == 1
        column_count = len(columns_line[0].split(": ")[1].split(", "))
        assert column_count == MAX_COLUMNS_FOR_EMBEDDING

    def test_includes_insights_preview(self):
        """Should include first 5 insights."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        dataset = {"name": "Sales Data"}
        insights = [
            {"text": "Revenue grew 15% YoY"},
            {"title": "Seasonal pattern detected"},
            {"insight": "Top region is West"},
        ]

        result = service._build_dataset_text(dataset, insights=insights)

        assert "Revenue grew 15% YoY" in result
        assert "Seasonal pattern detected" in result
        assert "Top region is West" in result


class TestEmbeddingCache:
    """Tests for embedding caching behavior."""

    def test_generates_correct_cache_key(self):
        """Should generate cache key with prefix and dataset_id."""
        service = DatasetSimilarityService(redis_manager=MagicMock())

        key = service._embedding_cache_key("dataset-123")

        assert key == f"{EMBEDDING_CACHE_PREFIX}:dataset-123"

    def test_returns_cached_embedding_when_available(self):
        """Should return cached embedding without regenerating."""
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = "[0.1, 0.2, 0.3]"
        service = DatasetSimilarityService(redis_manager=mock_redis)

        result = service._get_cached_embedding("dataset-123")

        assert result == [0.1, 0.2, 0.3]
        mock_redis.client.get.assert_called_once()

    def test_returns_none_when_not_cached(self):
        """Should return None if no cached embedding exists."""
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = None
        service = DatasetSimilarityService(redis_manager=mock_redis)

        result = service._get_cached_embedding("dataset-123")

        assert result is None

    def test_caches_embedding_with_correct_ttl(self):
        """Should cache embedding with 7-day TTL."""
        mock_redis = MagicMock()
        service = DatasetSimilarityService(redis_manager=mock_redis)

        service._cache_embedding("dataset-123", [0.1, 0.2, 0.3])

        mock_redis.client.setex.assert_called_once()
        call_args = mock_redis.client.setex.call_args
        assert call_args[0][1] == EMBEDDING_CACHE_TTL  # 7 days


class TestGetSharedColumns:
    """Tests for _get_shared_columns method."""

    def test_finds_exact_column_matches(self):
        """Should find columns with matching names."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        source_profiles = [
            {"column_name": "revenue"},
            {"column_name": "date"},
            {"column_name": "region"},
        ]
        target_profiles = [
            {"column_name": "revenue"},
            {"column_name": "region"},
            {"column_name": "product"},
        ]

        result = service._get_shared_columns(source_profiles, target_profiles)

        assert "revenue" in result
        assert "region" in result
        assert "date" not in result
        assert "product" not in result

    def test_case_insensitive_matching(self):
        """Should match columns regardless of case."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        source_profiles = [{"column_name": "Revenue"}]
        target_profiles = [{"column_name": "revenue"}]

        result = service._get_shared_columns(source_profiles, target_profiles)

        assert len(result) == 1

    def test_returns_empty_when_no_matches(self):
        """Should return empty list when no columns match."""
        service = DatasetSimilarityService(redis_manager=MagicMock())
        source_profiles = [{"column_name": "revenue"}]
        target_profiles = [{"column_name": "product"}]

        result = service._get_shared_columns(source_profiles, target_profiles)

        assert result == []


class TestFindSimilarDatasets:
    """Tests for find_similar_datasets method."""

    @patch("backend.services.dataset_similarity.generate_embeddings_batch")
    def test_excludes_source_dataset(self, mock_embed):
        """Should not include the source dataset in results."""
        mock_embed.return_value = [[0.1] * 1024]
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = None
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {"id": "ds-1", "name": "Test"}
        mock_repo.get_profiles.return_value = []
        mock_repo.list_by_user.return_value = (
            [
                {"id": "ds-1", "name": "Test"},  # Same as source
                {"id": "ds-2", "name": "Other"},
            ],
            2,
        )

        service = DatasetSimilarityService(
            redis_manager=mock_redis,
            dataset_repo=mock_repo,
        )
        result = service.find_similar_datasets("user-1", "ds-1", threshold=0.0)

        # ds-1 should not be in results
        result_ids = [r.dataset_id for r in result]
        assert "ds-1" not in result_ids

    @patch("backend.services.dataset_similarity.generate_embeddings_batch")
    def test_filters_by_threshold(self, mock_embed):
        """Should only return datasets above threshold."""
        # Embeddings: source=[1,0], ds-2=[0.9,0.1], ds-3=[0.1,0.9]
        # ds-2 is similar (high cosine), ds-3 is dissimilar
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = None
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {"id": "ds-1", "name": "Source"}
        mock_repo.get_profiles.return_value = []
        mock_repo.list_by_user.return_value = (
            [
                {"id": "ds-1", "name": "Source"},
                {"id": "ds-2", "name": "Similar"},
                {"id": "ds-3", "name": "Different"},
            ],
            3,
        )

        # Return different embeddings for each call
        embeddings = [
            [[1.0, 0.0] + [0.0] * 1022],  # Source
            [[0.99, 0.1] + [0.0] * 1022],  # Similar - high cosine sim
            [[0.1, 0.99] + [0.0] * 1022],  # Different - low cosine sim
        ]
        call_count = [0]

        def mock_generate(*args, **kwargs):
            result = embeddings[call_count[0]]
            call_count[0] += 1
            return result

        mock_embed.side_effect = mock_generate

        service = DatasetSimilarityService(
            redis_manager=mock_redis,
            dataset_repo=mock_repo,
        )
        result = service.find_similar_datasets("user-1", "ds-1", threshold=0.8)

        # Only ds-2 should be above threshold
        result_ids = [r.dataset_id for r in result]
        assert "ds-2" in result_ids
        assert "ds-3" not in result_ids

    @patch("backend.services.dataset_similarity.generate_embeddings_batch")
    def test_respects_limit(self, mock_embed):
        """Should limit number of results."""
        mock_embed.return_value = [[0.1] * 1024]
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = None
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {"id": "ds-1", "name": "Source"}
        mock_repo.get_profiles.return_value = []
        # Return 10 similar datasets
        mock_repo.list_by_user.return_value = (
            [{"id": f"ds-{i}", "name": f"Dataset {i}"} for i in range(10)],
            10,
        )

        service = DatasetSimilarityService(
            redis_manager=mock_redis,
            dataset_repo=mock_repo,
        )
        result = service.find_similar_datasets("user-1", "ds-1", threshold=0.0, limit=3)

        assert len(result) <= 3

    @patch("backend.services.dataset_similarity.generate_embeddings_batch")
    def test_sorts_by_similarity_descending(self, mock_embed):
        """Should return results sorted by similarity, highest first."""
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = None
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {"id": "ds-1", "name": "Source"}
        mock_repo.get_profiles.return_value = []
        mock_repo.list_by_user.return_value = (
            [
                {"id": "ds-1", "name": "Source"},
                {"id": "ds-2", "name": "Less Similar"},
                {"id": "ds-3", "name": "Most Similar"},
            ],
            3,
        )

        # Return different similarity levels
        embeddings = [
            [[1.0, 0.0] + [0.0] * 1022],  # Source
            [[0.7, 0.3] + [0.0] * 1022],  # Less similar
            [[0.95, 0.05] + [0.0] * 1022],  # Most similar
        ]
        call_count = [0]

        def mock_generate(*args, **kwargs):
            result = embeddings[call_count[0]]
            call_count[0] += 1
            return result

        mock_embed.side_effect = mock_generate

        service = DatasetSimilarityService(
            redis_manager=mock_redis,
            dataset_repo=mock_repo,
        )
        result = service.find_similar_datasets("user-1", "ds-1", threshold=0.0)

        # Should be sorted by similarity descending
        similarities = [r.similarity for r in result]
        assert similarities == sorted(similarities, reverse=True)

    def test_returns_empty_when_dataset_not_found(self):
        """Should return empty list if source dataset not found."""
        mock_redis = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        service = DatasetSimilarityService(
            redis_manager=mock_redis,
            dataset_repo=mock_repo,
        )
        result = service.find_similar_datasets("user-1", "nonexistent")

        assert result == []


class TestInvalidateCache:
    """Tests for cache invalidation."""

    def test_deletes_cache_key(self):
        """Should delete the cached embedding."""
        mock_redis = MagicMock()
        mock_redis.client.delete.return_value = 1
        service = DatasetSimilarityService(redis_manager=mock_redis)

        result = service.invalidate_cache("dataset-123")

        assert result is True
        mock_redis.client.delete.assert_called_once()

    def test_returns_false_when_not_cached(self):
        """Should return False if no cache to invalidate."""
        mock_redis = MagicMock()
        mock_redis.client.delete.return_value = 0
        service = DatasetSimilarityService(redis_manager=mock_redis)

        result = service.invalidate_cache("nonexistent")

        assert result is False


class TestSimilarDatasetDataclass:
    """Tests for SimilarDataset dataclass."""

    def test_creates_with_all_fields(self):
        """Should create instance with all fields."""
        similar = SimilarDataset(
            dataset_id="ds-123",
            name="Similar Dataset",
            similarity=0.85,
            shared_columns=["revenue", "date"],
            insight_preview="Contains sales data",
        )

        assert similar.dataset_id == "ds-123"
        assert similar.name == "Similar Dataset"
        assert similar.similarity == 0.85
        assert similar.shared_columns == ["revenue", "date"]
        assert similar.insight_preview == "Contains sales data"

    def test_allows_none_insight_preview(self):
        """Should allow None for insight_preview."""
        similar = SimilarDataset(
            dataset_id="ds-123",
            name="Similar Dataset",
            similarity=0.85,
            shared_columns=[],
            insight_preview=None,
        )

        assert similar.insight_preview is None


class TestGetSimilarityService:
    """Tests for singleton getter."""

    def test_returns_singleton_instance(self):
        """Should return same instance on repeated calls."""
        # Reset singleton for test
        get_similarity_service.cache_clear()

        with patch.object(DatasetSimilarityService, "__init__", return_value=None):
            service1 = get_similarity_service()
            service2 = get_similarity_service()

            assert service1 is service2
