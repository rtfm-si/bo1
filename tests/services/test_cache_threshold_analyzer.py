"""Tests for cache_threshold_analyzer service."""

from unittest.mock import patch

from backend.services.cache_threshold_analyzer import (
    LOWER_THRESHOLD,
    RAISE_THRESHOLD,
    calculate_recommended_threshold,
    get_full_cache_metrics,
)
from bo1.constants import SimilarityCacheThresholds


class TestCalculateRecommendedThreshold:
    """Tests for calculate_recommended_threshold function."""

    def test_optimal_hit_rate_no_change(self):
        """When hit rate is within optimal range, no change recommended."""
        result = calculate_recommended_threshold(
            hit_rate_30d=35.0,
            avg_similarity_on_hit=0.90,
            near_miss_count=5,
        )

        assert result["current_threshold"] == SimilarityCacheThresholds.RESEARCH_CACHE
        assert result["recommended_threshold"] == SimilarityCacheThresholds.RESEARCH_CACHE
        assert result["change_needed"] is False
        assert result["confidence"] == "high"

    def test_low_hit_rate_with_near_misses_suggests_lower(self):
        """When hit rate is low with many near-misses, suggest lowering threshold."""
        result = calculate_recommended_threshold(
            hit_rate_30d=5.0,  # Below LOW_HIT_RATE_THRESHOLD (10%)
            avg_similarity_on_hit=0.88,
            near_miss_count=25,  # Many near-misses
        )

        assert result["recommended_threshold"] == LOWER_THRESHOLD  # 0.80
        assert result["change_needed"] is True
        assert "lowering" in result["reason"].lower() or "lower" in result["reason"].lower()

    def test_low_hit_rate_without_near_misses_no_change(self):
        """When hit rate is low but no near-misses, suggest monitoring."""
        result = calculate_recommended_threshold(
            hit_rate_30d=5.0,
            avg_similarity_on_hit=0.75,  # Below NEAR_MISS_SIMILARITY_THRESHOLD
            near_miss_count=3,  # Few near-misses
        )

        assert result["recommended_threshold"] == SimilarityCacheThresholds.RESEARCH_CACHE
        assert result["change_needed"] is False
        assert result["confidence"] == "low"
        assert "monitoring" in result["reason"].lower() or "continue" in result["reason"].lower()

    def test_high_hit_rate_with_low_similarity_suggests_raise(self):
        """When hit rate is high with low avg similarity, suggest raising threshold."""
        result = calculate_recommended_threshold(
            hit_rate_30d=70.0,  # Above HIGH_HIT_RATE_THRESHOLD (60%)
            avg_similarity_on_hit=0.87,  # Below 0.90
            near_miss_count=5,
        )

        assert result["recommended_threshold"] == RAISE_THRESHOLD  # 0.88
        assert result["change_needed"] is True
        assert "raising" in result["reason"].lower() or "raise" in result["reason"].lower()

    def test_high_hit_rate_with_strong_similarity_no_change(self):
        """When hit rate is high but similarity is strong, no change needed."""
        result = calculate_recommended_threshold(
            hit_rate_30d=70.0,
            avg_similarity_on_hit=0.95,  # Strong similarity
            near_miss_count=5,
        )

        assert result["recommended_threshold"] == SimilarityCacheThresholds.RESEARCH_CACHE
        assert result["change_needed"] is False

    def test_metrics_included_in_result(self):
        """Verify that input metrics are included in the result."""
        result = calculate_recommended_threshold(
            hit_rate_30d=35.0,
            avg_similarity_on_hit=0.90,
            near_miss_count=10,
        )

        assert result["metrics"]["hit_rate_30d"] == 35.0
        assert result["metrics"]["avg_similarity_on_hit"] == 0.90
        assert result["metrics"]["near_miss_count"] == 10


class TestGetFullCacheMetrics:
    """Tests for get_full_cache_metrics function."""

    @patch("backend.services.cache_threshold_analyzer.cache_repository")
    def test_returns_all_expected_fields(self, mock_repo):
        """Verify all expected fields are returned."""
        # Setup mocks
        mock_repo.get_hit_rate_metrics.side_effect = [
            {"hit_rate": 20.0, "total_queries": 50, "cache_hits": 10, "avg_savings_per_hit": 0.05},
            {"hit_rate": 25.0, "total_queries": 200, "cache_hits": 50, "avg_savings_per_hit": 0.05},
            {
                "hit_rate": 30.0,
                "total_queries": 500,
                "cache_hits": 150,
                "avg_savings_per_hit": 0.05,
            },
        ]
        mock_repo.get_avg_similarity_on_hit.return_value = 0.88
        mock_repo.get_miss_similarity_distribution.return_value = [
            {"bucket": 1, "range_start": 0.70, "range_end": 0.73, "count": 5},
            {"bucket": 2, "range_start": 0.73, "range_end": 0.76, "count": 8},
        ]
        mock_repo.get_stats.return_value = {
            "total_cached_results": 1000,
            "cost_savings_30d": 10.50,
            "cache_hit_rate_30d": 30.0,
            "top_cached_questions": [],
        }

        result = get_full_cache_metrics()

        # Verify all fields present
        assert "hit_rate_1d" in result
        assert "hit_rate_7d" in result
        assert "hit_rate_30d" in result
        assert "total_queries_1d" in result
        assert "cache_hits_30d" in result
        assert "avg_similarity_on_hit" in result
        assert "miss_distribution" in result
        assert "current_threshold" in result
        assert "recommended_threshold" in result
        assert "recommendation_reason" in result
        assert "recommendation_confidence" in result
        assert "total_cached_results" in result
        assert "cost_savings_30d" in result

    @patch("backend.services.cache_threshold_analyzer.cache_repository")
    def test_calls_repository_correctly(self, mock_repo):
        """Verify correct repository methods are called."""
        mock_repo.get_hit_rate_metrics.return_value = {
            "hit_rate": 30.0,
            "total_queries": 100,
            "cache_hits": 30,
            "avg_savings_per_hit": 0.05,
        }
        mock_repo.get_avg_similarity_on_hit.return_value = 0.88
        mock_repo.get_miss_similarity_distribution.return_value = []
        mock_repo.get_stats.return_value = {
            "total_cached_results": 100,
            "cost_savings_30d": 5.0,
            "cache_hit_rate_30d": 30.0,
            "top_cached_questions": [],
        }

        get_full_cache_metrics()

        # Verify calls
        assert mock_repo.get_hit_rate_metrics.call_count == 3
        mock_repo.get_hit_rate_metrics.assert_any_call(1)
        mock_repo.get_hit_rate_metrics.assert_any_call(7)
        mock_repo.get_hit_rate_metrics.assert_any_call(30)
        mock_repo.get_avg_similarity_on_hit.assert_called_once_with(30)
        mock_repo.get_miss_similarity_distribution.assert_called_once()
        mock_repo.get_stats.assert_called_once()

    @patch("backend.services.cache_threshold_analyzer.cache_repository")
    def test_recommendation_based_on_metrics(self, mock_repo):
        """Verify recommendation is calculated from metrics."""
        # Setup low hit rate scenario
        mock_repo.get_hit_rate_metrics.return_value = {
            "hit_rate": 5.0,
            "total_queries": 100,
            "cache_hits": 5,
            "avg_savings_per_hit": 0.05,
        }
        mock_repo.get_avg_similarity_on_hit.return_value = 0.82
        mock_repo.get_miss_similarity_distribution.return_value = [
            {"bucket": 1, "range_start": 0.70, "range_end": 0.73, "count": 30},
        ]
        mock_repo.get_stats.return_value = {
            "total_cached_results": 100,
            "cost_savings_30d": 1.0,
            "cache_hit_rate_30d": 5.0,
            "top_cached_questions": [],
        }

        result = get_full_cache_metrics()

        # Low hit rate with near-misses should recommend lowering
        assert result["recommended_threshold"] == LOWER_THRESHOLD
