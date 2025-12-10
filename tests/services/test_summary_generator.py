"""Tests for summary generator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.summary_generator import (
    _compute_profile_hash,
    _format_profile_for_prompt,
    generate_dataset_summary,
    invalidate_summary_cache,
)


class TestFormatProfileForPrompt:
    """Tests for _format_profile_for_prompt function."""

    def test_basic_format(self):
        profile = {
            "dataset_id": "test-123",
            "row_count": 100,
            "column_count": 2,
            "columns": [
                {
                    "name": "id",
                    "inferred_type": "integer",
                    "stats": {"null_count": 0, "unique_count": 100},
                },
                {
                    "name": "name",
                    "inferred_type": "text",
                    "stats": {"null_count": 5, "unique_count": 50},
                },
            ],
        }

        result = _format_profile_for_prompt(profile)

        assert "100 rows" in result
        assert "2 columns" in result
        assert "id (integer)" in result
        assert "name (text)" in result
        assert "5.0% null" in result

    def test_numeric_stats(self):
        profile = {
            "row_count": 100,
            "column_count": 1,
            "columns": [
                {
                    "name": "price",
                    "inferred_type": "float",
                    "stats": {
                        "null_count": 0,
                        "unique_count": 50,
                        "min_value": 10.0,
                        "max_value": 100.0,
                        "mean_value": 55.0,
                    },
                },
            ],
        }

        result = _format_profile_for_prompt(profile)

        assert "range: 10.0 to 100.0" in result
        assert "mean: 55.00" in result

    def test_categorical_stats(self):
        profile = {
            "row_count": 100,
            "column_count": 1,
            "columns": [
                {
                    "name": "status",
                    "inferred_type": "categorical",
                    "stats": {
                        "null_count": 0,
                        "unique_count": 3,
                        "top_values": [
                            {"value": "active", "count": 50},
                            {"value": "pending", "count": 30},
                            {"value": "inactive", "count": 20},
                        ],
                    },
                },
            ],
        }

        result = _format_profile_for_prompt(profile)

        assert "active (50)" in result
        assert "pending (30)" in result


class TestComputeProfileHash:
    """Tests for _compute_profile_hash function."""

    def test_consistent_hash(self):
        profile = {"dataset_id": "test", "row_count": 100}

        hash1 = _compute_profile_hash(profile)
        hash2 = _compute_profile_hash(profile)

        assert hash1 == hash2
        assert len(hash1) == 12

    def test_different_profiles_different_hash(self):
        profile1 = {"dataset_id": "test1", "row_count": 100}
        profile2 = {"dataset_id": "test2", "row_count": 100}

        hash1 = _compute_profile_hash(profile1)
        hash2 = _compute_profile_hash(profile2)

        assert hash1 != hash2


class TestGenerateDatasetSummary:
    """Tests for generate_dataset_summary function."""

    @pytest.mark.asyncio
    @patch("backend.services.summary_generator.ClaudeClient")
    @patch("backend.services.summary_generator.RedisManager")
    async def test_cache_hit(self, mock_redis_class, mock_client_class):
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = b"Cached summary"
        mock_redis_class.return_value = mock_redis

        profile = {"dataset_id": "test-123", "row_count": 100, "column_count": 2, "columns": []}

        result = await generate_dataset_summary(profile, redis_manager=mock_redis)

        assert result == "Cached summary"
        mock_client_class.assert_not_called()

    @pytest.mark.asyncio
    @patch("backend.services.summary_generator.ClaudeClient")
    @patch("backend.services.summary_generator.RedisManager")
    async def test_cache_miss_generates_summary(self, mock_redis_class, mock_client_class):
        mock_redis = MagicMock()
        mock_redis.client.get.return_value = None
        mock_redis_class.return_value = mock_redis

        mock_client = MagicMock()
        mock_client.call = AsyncMock(
            return_value=(
                "Generated summary",
                MagicMock(total_tokens=100, calculate_cost=MagicMock(return_value=0.001)),
            )
        )
        mock_client_class.return_value = mock_client

        profile = {"dataset_id": "test-123", "row_count": 100, "column_count": 2, "columns": []}

        result = await generate_dataset_summary(profile, redis_manager=mock_redis)

        assert result == "Generated summary"
        mock_client.call.assert_called_once()
        mock_redis.client.setex.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.services.summary_generator.ClaudeClient")
    @patch("backend.services.summary_generator.RedisManager")
    async def test_skip_cache(self, mock_redis_class, mock_client_class):
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis

        mock_client = MagicMock()
        mock_client.call = AsyncMock(
            return_value=(
                "Generated summary",
                MagicMock(total_tokens=100, calculate_cost=MagicMock(return_value=0.001)),
            )
        )
        mock_client_class.return_value = mock_client

        profile = {"dataset_id": "test-123", "row_count": 100, "column_count": 2, "columns": []}

        result = await generate_dataset_summary(profile, use_cache=False, redis_manager=mock_redis)

        assert result == "Generated summary"
        mock_redis.client.get.assert_not_called()


class TestInvalidateSummaryCache:
    """Tests for invalidate_summary_cache function."""

    def test_invalidate_existing_keys(self):
        mock_redis = MagicMock()
        mock_redis.client.scan_iter.return_value = [b"key1", b"key2"]
        mock_redis.client.delete.return_value = 2

        result = invalidate_summary_cache("test-123", redis_manager=mock_redis)

        assert result == 2
        mock_redis.client.delete.assert_called_once()

    def test_no_keys_to_invalidate(self):
        mock_redis = MagicMock()
        mock_redis.client.scan_iter.return_value = []

        result = invalidate_summary_cache("test-123", redis_manager=mock_redis)

        assert result == 0
        mock_redis.client.delete.assert_not_called()
