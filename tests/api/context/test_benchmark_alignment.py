"""Tests for benchmark_alignment module."""

from backend.api.context.benchmark_alignment import (
    OBJECTIVE_METRICS,
    STAGE_WEIGHTS,
    AlignedBenchmark,
    get_aligned_benchmarks,
    get_available_objectives,
    get_available_stages,
    score_benchmark_relevance,
)


class TestScoreBenchmarkRelevance:
    """Tests for score_benchmark_relevance function."""

    def test_no_objective_or_stage_returns_default(self):
        """Without objective/stage, returns default 0.5 score."""
        score, reason, is_aligned = score_benchmark_relevance("some_metric", None, None)
        assert score == 0.5
        assert reason is None
        assert is_aligned is False

    def test_objective_aligned_metric_scores_high(self):
        """Metrics aligned with objective get high relevance scores."""
        # customer_acquisition_cost is first in acquire_customers list
        score, reason, is_aligned = score_benchmark_relevance(
            "customer_acquisition_cost", "acquire_customers", None
        )
        assert score == 1.0  # First position = highest score
        assert reason == "Key for customer acquisition"
        assert is_aligned is True

    def test_objective_aligned_second_position(self):
        """Second position in objective list scores slightly lower."""
        # conversion_rate is second in acquire_customers list
        score, reason, is_aligned = score_benchmark_relevance(
            "conversion_rate", "acquire_customers", None
        )
        assert score == 0.85  # Second position = 1.0 - 0.15
        assert is_aligned is True

    def test_objective_aligned_third_position(self):
        """Third position in objective list scores even lower."""
        # ltv_cac_ratio is third in acquire_customers list
        score, reason, is_aligned = score_benchmark_relevance(
            "ltv_cac_ratio", "acquire_customers", None
        )
        assert score == 0.70  # Third position
        assert is_aligned is True

    def test_unaligned_metric_with_objective(self):
        """Metrics not in objective list stay at 0.5."""
        score, reason, is_aligned = score_benchmark_relevance(
            "random_metric", "acquire_customers", None
        )
        assert score == 0.5
        assert reason is None
        assert is_aligned is False

    def test_stage_modifier_increases_score(self):
        """Stage modifier can increase relevance score."""
        # customer_acquisition_cost has 1.3 weight in "early" stage
        score, _, _ = score_benchmark_relevance("customer_acquisition_cost", None, "early")
        # 0.5 * 1.3 = 0.65
        assert score == 0.65

    def test_stage_modifier_capped_at_1(self):
        """Score with stage modifier is capped at 1.0."""
        # conversion_rate in "idea" stage has 1.5 weight
        # Start with high objective score + stage boost
        score, _, _ = score_benchmark_relevance("conversion_rate", "acquire_customers", "idea")
        # 0.85 * 1.5 = 1.275, but capped at 1.0
        assert score == 1.0

    def test_stage_specific_reason_override(self):
        """Stage-specific reasons override objective reasons."""
        score, reason, _ = score_benchmark_relevance("churn_rate", "improve_retention", "early")
        assert reason == "Retention matters now"  # Stage reason, not objective

    def test_invalid_objective_ignored(self):
        """Invalid objective returns default score."""
        score, reason, is_aligned = score_benchmark_relevance(
            "churn_rate", "invalid_objective", None
        )
        assert score == 0.5
        assert reason is None
        assert is_aligned is False

    def test_invalid_stage_no_effect(self):
        """Invalid stage has no effect on score."""
        score, _, _ = score_benchmark_relevance("churn_rate", None, "invalid_stage")
        assert score == 0.5  # No stage modifier applied


class TestGetAlignedBenchmarks:
    """Tests for get_aligned_benchmarks function."""

    def test_returns_empty_for_unknown_industry(self):
        """Unknown industry returns empty list."""
        result = get_aligned_benchmarks("unknown_industry", None, None)
        assert result == []

    def test_returns_benchmarks_for_valid_industry(self):
        """Valid industry returns list of aligned benchmarks."""
        result = get_aligned_benchmarks("saas", None, None)
        assert len(result) > 0
        assert all(isinstance(b, AlignedBenchmark) for b in result)

    def test_sorted_by_relevance_descending(self):
        """Results are sorted by relevance score (highest first)."""
        result = get_aligned_benchmarks("saas", "acquire_customers", None)
        scores = [b.relevance_score for b in result]
        assert scores == sorted(scores, reverse=True)

    def test_aligned_metrics_marked_correctly(self):
        """Objective-aligned metrics have is_objective_aligned=True."""
        result = get_aligned_benchmarks("saas", "acquire_customers", None)
        aligned = [b for b in result if b.is_objective_aligned]
        # Should have some aligned metrics for valid objective
        assert len(aligned) > 0

    def test_normalized_industry_name(self):
        """Industry name is normalized (lowercase, underscores)."""
        result1 = get_aligned_benchmarks("SaaS", None, None)
        result2 = get_aligned_benchmarks("saas", None, None)
        # Note: "Sa-aS" normalizes to "sa_as" which doesn't match "saas"
        assert len(result1) == len(result2)
        assert len(result1) > 0


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_available_objectives(self):
        """Returns list of supported objectives."""
        objectives = get_available_objectives()
        assert isinstance(objectives, list)
        assert len(objectives) == len(OBJECTIVE_METRICS)
        assert "acquire_customers" in objectives
        assert "improve_retention" in objectives

    def test_get_available_stages(self):
        """Returns list of supported stages."""
        stages = get_available_stages()
        assert isinstance(stages, list)
        assert len(stages) == len(STAGE_WEIGHTS)
        assert "idea" in stages
        assert "scaling" in stages


# Integration tests moved to tests/api/test_industry_insights_alignment.py
# to use proper fixtures
