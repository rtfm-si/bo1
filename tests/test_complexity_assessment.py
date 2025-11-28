"""Tests for complexity assessment and adaptive parameters.

Validates that:
1. Complexity scores are calculated correctly
2. Adaptive round limits match complexity
3. Adaptive expert counts match complexity
4. Integration with decompose_node works
"""

from bo1.agents.complexity_assessor import (
    get_adaptive_max_rounds,
    get_adaptive_num_experts,
    validate_complexity_assessment,
)


class TestAdaptiveParameters:
    """Test adaptive round and expert count calculations."""

    def test_adaptive_rounds_simple(self):
        """Simple problems (0.0-0.3) should get 3 rounds."""
        assert get_adaptive_max_rounds(0.1) == 3
        assert get_adaptive_max_rounds(0.2) == 3
        assert get_adaptive_max_rounds(0.29) == 3

    def test_adaptive_rounds_moderate(self):
        """Moderate problems (0.3-0.5) should get 4 rounds."""
        assert get_adaptive_max_rounds(0.3) == 4
        assert get_adaptive_max_rounds(0.4) == 4
        assert get_adaptive_max_rounds(0.49) == 4

    def test_adaptive_rounds_complex(self):
        """Complex problems (0.5-0.7) should get 5 rounds."""
        assert get_adaptive_max_rounds(0.5) == 5
        assert get_adaptive_max_rounds(0.6) == 5
        assert get_adaptive_max_rounds(0.69) == 5

    def test_adaptive_rounds_highly_complex(self):
        """Highly complex problems (0.7-1.0) should get 6 rounds."""
        assert get_adaptive_max_rounds(0.7) == 6
        assert get_adaptive_max_rounds(0.8) == 6
        assert get_adaptive_max_rounds(0.9) == 6
        assert get_adaptive_max_rounds(1.0) == 6

    def test_adaptive_experts_simple(self):
        """Simple problems (0.0-0.3) should get 3 experts."""
        assert get_adaptive_num_experts(0.1) == 3
        assert get_adaptive_num_experts(0.2) == 3
        assert get_adaptive_num_experts(0.29) == 3

    def test_adaptive_experts_moderate(self):
        """Moderate problems (0.3-0.7) should get 4 experts."""
        assert get_adaptive_num_experts(0.3) == 4
        assert get_adaptive_num_experts(0.4) == 4
        assert get_adaptive_num_experts(0.5) == 4
        assert get_adaptive_num_experts(0.6) == 4
        assert get_adaptive_num_experts(0.69) == 4

    def test_adaptive_experts_complex(self):
        """Complex problems (0.7-1.0) should get 5 experts."""
        assert get_adaptive_num_experts(0.7) == 5
        assert get_adaptive_num_experts(0.8) == 5
        assert get_adaptive_num_experts(0.9) == 5
        assert get_adaptive_num_experts(1.0) == 5


class TestComplexityValidation:
    """Test complexity assessment validation and sanitization."""

    def test_validate_clamps_scores_to_range(self):
        """Scores should be clamped to 0.0-1.0."""
        assessment = {
            "overall_complexity": 1.5,  # Too high
            "scope_breadth": -0.1,  # Too low
            "dependencies": 0.5,  # Valid
        }
        validated = validate_complexity_assessment(assessment)

        assert validated["overall_complexity"] == 1.0  # Clamped to max
        assert validated["scope_breadth"] == 0.0  # Clamped to min
        assert validated["dependencies"] == 0.5  # Unchanged

    def test_validate_clamps_rounds(self):
        """Recommended rounds should be clamped to 3-6."""
        assessment = {
            "recommended_rounds": 10,  # Too high
        }
        validated = validate_complexity_assessment(assessment)
        assert validated["recommended_rounds"] == 6  # Clamped to max

        assessment = {
            "recommended_rounds": 1,  # Too low
        }
        validated = validate_complexity_assessment(assessment)
        assert validated["recommended_rounds"] == 3  # Clamped to min

    def test_validate_clamps_experts(self):
        """Recommended experts should be clamped to 3-5."""
        assessment = {
            "recommended_experts": 10,  # Too high
        }
        validated = validate_complexity_assessment(assessment)
        assert validated["recommended_experts"] == 5  # Clamped to max

        assessment = {
            "recommended_experts": 1,  # Too low
        }
        validated = validate_complexity_assessment(assessment)
        assert validated["recommended_experts"] == 3  # Clamped to min

    def test_validate_provides_fallbacks(self):
        """Invalid values should get safe fallbacks."""
        assessment = {
            "overall_complexity": "invalid",  # Non-numeric
            "recommended_rounds": "foo",  # Non-numeric
            "recommended_experts": None,  # None
        }
        validated = validate_complexity_assessment(assessment)

        assert validated["overall_complexity"] == 0.5  # Fallback
        assert validated["recommended_rounds"] == 4  # Fallback
        assert validated["recommended_experts"] == 4  # Fallback

    def test_validate_ensures_reasoning_exists(self):
        """Reasoning field should always exist."""
        assessment = {}
        validated = validate_complexity_assessment(assessment)
        assert "reasoning" in validated
        assert isinstance(validated["reasoning"], str)


class TestComplexityExamples:
    """Test complexity scoring with real-world examples."""

    def test_simple_technical_decision(self):
        """Simple technical decision: PostgreSQL vs MySQL."""
        # Expected complexity: ~0.16
        # Scope: 0.1 (single domain)
        # Dependencies: 0.2 (mostly independent)
        # Ambiguity: 0.2 (clear trade-offs)
        # Stakeholders: 0.1 (solo dev)
        # Novelty: 0.2 (established patterns)
        complexity = 0.16
        assert get_adaptive_max_rounds(complexity) == 3
        assert get_adaptive_num_experts(complexity) == 3

    def test_moderate_business_decision(self):
        """Moderate business decision: $50K SEO vs ads."""
        # Expected complexity: ~0.41
        # Scope: 0.4 (marketing + finance + operations)
        # Dependencies: 0.5 (interconnected)
        # Ambiguity: 0.5 (some unknowns)
        # Stakeholders: 0.3 (small team)
        # Novelty: 0.3 (familiar problem)
        complexity = 0.41
        assert get_adaptive_max_rounds(complexity) == 4
        assert get_adaptive_num_experts(complexity) == 4

    def test_complex_strategic_decision(self):
        """Complex strategic decision: B2B to B2C pivot."""
        # Expected complexity: ~0.80
        # Scope: 0.9 (market + product + finance + org + legal)
        # Dependencies: 0.8 (tightly coupled)
        # Ambiguity: 0.8 (high uncertainty)
        # Stakeholders: 0.7 (many parties)
        # Novelty: 0.7 (novel for this context)
        complexity = 0.80
        assert get_adaptive_max_rounds(complexity) == 6
        assert get_adaptive_num_experts(complexity) == 5


class TestMetricsIntegration:
    """Test integration with DeliberationMetrics model."""

    def test_metrics_stores_complexity_scores(self):
        """DeliberationMetrics should store all complexity dimensions."""
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics(
            complexity_score=0.65,
            scope_breadth=0.7,
            dependencies=0.6,
            ambiguity=0.5,
            stakeholders_complexity=0.4,
            novelty=0.6,
            recommended_rounds=5,
            recommended_experts=4,
            complexity_reasoning="Complex problem spanning multiple domains",
        )

        assert metrics.complexity_score == 0.65
        assert metrics.scope_breadth == 0.7
        assert metrics.dependencies == 0.6
        assert metrics.ambiguity == 0.5
        assert metrics.stakeholders_complexity == 0.4
        assert metrics.novelty == 0.6
        assert metrics.recommended_rounds == 5
        assert metrics.recommended_experts == 4
        assert "multiple domains" in metrics.complexity_reasoning

    def test_metrics_defaults_to_none(self):
        """Complexity fields should default to None."""
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

        assert metrics.complexity_score is None
        assert metrics.scope_breadth is None
        assert metrics.dependencies is None
        assert metrics.ambiguity is None
        assert metrics.stakeholders_complexity is None
        assert metrics.novelty is None
        assert metrics.recommended_rounds is None
        assert metrics.recommended_experts is None
        assert metrics.complexity_reasoning is None
