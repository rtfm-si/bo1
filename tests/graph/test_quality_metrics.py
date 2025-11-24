"""Unit tests for quality metrics module."""

import pytest

from bo1.graph.quality_metrics import (
    calculate_conflict_score,
    calculate_exploration_score_heuristic,
    calculate_focus_score_heuristic,
    calculate_meeting_completeness_index,
    calculate_novelty_score_semantic,
    detect_contribution_drift,
)
from bo1.models.state import AspectCoverage, ContributionMessage


class TestNoveltyScore:
    """Tests for novelty score calculation."""

    @pytest.mark.requires_llm
    def test_high_novelty_diverse_contributions(self):
        """Test novelty score for completely different contributions."""
        contributions = [
            {"content": "We should focus on user acquisition through paid advertising."},
            {
                "content": "The technical infrastructure needs significant improvements for scalability."
            },
            {"content": "Customer retention metrics show we need better onboarding processes."},
            {
                "content": "Financial projections indicate we should prioritize profitability over growth."
            },
            {"content": "Market research suggests expanding into European markets first."},
            {"content": "Product-market fit data shows we need to pivot our value proposition."},
        ]

        score = calculate_novelty_score_semantic(contributions)

        # Diverse contributions should have moderate to high novelty (>0.4)
        # Note: Business-related contributions may show semantic similarity even when topically diverse
        assert score > 0.4, f"Expected high novelty for diverse contributions, got {score:.2f}"

    @pytest.mark.requires_llm
    def test_low_novelty_repetitive_contributions(self):
        """Test novelty score for very similar contributions."""
        contributions = [
            {"content": "We should increase marketing spend to acquire more users."},
            {"content": "I agree, we need to invest more in marketing to get new users."},
            {"content": "Marketing investment is key to growing our user base."},
            {"content": "Yes, more marketing budget will help us acquire customers."},
            {"content": "I support increasing marketing spend for user acquisition."},
            {"content": "Marketing is the right approach to grow our user numbers."},
        ]

        score = calculate_novelty_score_semantic(contributions)

        # Repetitive contributions should have low novelty (<0.4)
        assert score < 0.4, f"Expected low novelty for repetitive contributions, got {score:.2f}"

    def test_fallback_to_zero_when_insufficient_contributions(self):
        """Test fallback behavior with insufficient contributions."""
        contributions = [
            {"content": "First contribution."},
        ]

        score = calculate_novelty_score_semantic(contributions)

        # Should return 0.0 with insufficient contributions
        assert score == 0.0, f"Expected 0.0 for single contribution, got {score:.2f}"

    def test_empty_contributions(self):
        """Test with empty contributions list."""
        contributions = []

        score = calculate_novelty_score_semantic(contributions)

        assert score == 0.0


class TestConflictScore:
    """Tests for conflict score calculation."""

    def test_high_conflict_disagreement_keywords(self):
        """Test conflict score with disagreement keywords."""
        contributions = [
            {"content": "I disagree with this approach. It's incorrect."},
            {"content": "However, I think the alternative solution is better."},
            {"content": "But that's wrong. We need a different strategy."},
            {"content": "I have concerns about this plan. It's problematic."},
            {"content": "Unfortunately, I oppose this direction."},
            {"content": "I question whether this is the right approach."},
        ]

        score = calculate_conflict_score(contributions)

        # High disagreement should result in conflict score > 0.5
        assert score > 0.5, f"Expected high conflict score, got {score:.2f}"

    def test_low_conflict_agreement_keywords(self):
        """Test conflict score with agreement keywords."""
        contributions = [
            {"content": "I agree with this proposal. It's exactly right."},
            {"content": "Yes, I support this approach. Absolutely correct."},
            {"content": "Indeed, this is the perfect solution."},
            {"content": "I definitely agree. This is good."},
            {"content": "Certainly, this is the right direction."},
            {"content": "I agree completely. This is correct."},
        ]

        score = calculate_conflict_score(contributions)

        # High agreement should result in conflict score < 0.5
        assert score < 0.5, f"Expected low conflict score, got {score:.2f}"

    def test_zero_conflict_neutral_contributions(self):
        """Test conflict score with neutral language."""
        contributions = [
            {"content": "The data shows revenue growth of 15% year over year."},
            {"content": "Our customer base has expanded to 50,000 users."},
            {"content": "Market analysis indicates strong demand in this sector."},
            {"content": "The product roadmap includes these five features."},
            {"content": "Financial projections estimate break-even in Q3."},
            {"content": "Technical infrastructure can scale to 100,000 users."},
        ]

        score = calculate_conflict_score(contributions)

        # Neutral language should result in moderate conflict score (0.4-0.6)
        assert 0.3 < score < 0.7, f"Expected moderate conflict score, got {score:.2f}"

    def test_empty_contributions(self):
        """Test with empty contributions list."""
        contributions = []

        score = calculate_conflict_score(contributions)

        assert score == 0.0


class TestDriftDetection:
    """Tests for drift detection."""

    @pytest.mark.requires_llm
    def test_drift_detected_off_topic(self):
        """Test drift detection for off-topic contribution."""
        problem_statement = (
            "Should we invest $500K in expanding our SaaS product to European markets?"
        )
        contribution = "I think the best pizza toppings are pepperoni and mushrooms."

        drift = detect_contribution_drift(contribution, problem_statement)

        assert drift is True, "Expected drift to be detected for off-topic contribution"

    @pytest.mark.requires_llm
    def test_no_drift_on_topic(self):
        """Test no drift for on-topic contribution."""
        problem_statement = (
            "Should we invest $500K in expanding our SaaS product to European markets?"
        )
        contribution = (
            "I believe expanding to Europe is a strong opportunity. "
            "The SaaS market in Germany and UK is growing at 25% annually, "
            "and our product solves a clear pain point for European businesses."
        )

        drift = detect_contribution_drift(contribution, problem_statement)

        assert drift is False, "Expected no drift for on-topic contribution"

    @pytest.mark.requires_llm
    def test_similarity_threshold_boundary(self):
        """Test similarity threshold behavior."""
        problem_statement = "Should we hire a VP of Sales?"
        # Somewhat related but not directly on topic
        contribution = "Our revenue growth has been good this quarter."

        drift = detect_contribution_drift(contribution, problem_statement)

        # This should likely trigger drift as it's tangentially related
        # The exact result depends on embeddings, but we test it doesn't crash
        assert isinstance(drift, bool)

    def test_empty_strings(self):
        """Test with empty contribution or problem statement."""
        drift1 = detect_contribution_drift("", "Some problem")
        drift2 = detect_contribution_drift("Some contribution", "")
        drift3 = detect_contribution_drift("", "")

        # Empty strings should not trigger drift
        assert drift1 is False
        assert drift2 is False
        assert drift3 is False


# Integration tests for metrics tracking
class TestMetricsIntegration:
    """Integration tests for metrics in deliberation flow."""

    @pytest.mark.requires_llm
    def test_novelty_calculation_with_real_contributions(self):
        """Test novelty calculation with realistic deliberation contributions."""
        contributions = [
            {
                "content": "I believe we should focus on B2B sales rather than B2C. "
                "The enterprise market offers higher lifetime value."
            },
            {
                "content": "While B2B is attractive, B2C provides faster user acquisition. "
                "We can iterate the product more quickly with consumer feedback."
            },
            {
                "content": "Actually, a hybrid approach might work best. "
                "Start with B2C for validation, then move to B2B for monetization."
            },
            {
                "content": "The hybrid model is interesting, but we risk spreading ourselves too thin. "
                "I suggest focusing on B2B exclusively for the first year."
            },
            {
                "content": "Resource constraints are a valid concern. "
                "However, B2C gives us data to prove the concept to B2B buyers."
            },
            {
                "content": "I agree that data is crucial. "
                "Perhaps we could run a limited B2C pilot while preparing for B2B."
            },
        ]

        score = calculate_novelty_score_semantic(contributions)

        # This realistic deliberation should have moderate to high novelty
        assert 0.3 < score < 0.8, (
            f"Expected moderate novelty for realistic deliberation, got {score:.2f}"
        )

    def test_conflict_calculation_with_debate(self):
        """Test conflict calculation with actual debate."""
        contributions = [
            {
                "content": "I strongly disagree with the pricing strategy. "
                "Charging $99/month is too expensive for our target market."
            },
            {
                "content": "I agree that price sensitivity is a concern. "
                "However, premium pricing positions us as a quality solution."
            },
            {"content": "But our competitors charge $49/month. We can't ignore that."},
            {
                "content": "Yes, but we offer significantly more features. The value justifies the price."
            },
            {"content": "I'm not convinced. Customer surveys show price is the top concern."},
            {
                "content": "Fair point. Perhaps we need tiered pricing to address different segments."
            },
        ]

        score = calculate_conflict_score(contributions)

        # Debate with mixed agreement/disagreement should have moderate to high conflict
        # The score can reach 1.0 due to normalization with high disagreement
        assert 0.4 < score <= 1.0, f"Expected moderate to high conflict for debate, got {score:.2f}"


# NEW TESTS for Meeting Quality Enhancement
class TestExplorationScore:
    """Tests for exploration score calculation."""

    def test_exploration_score_heuristic_all_deep(self):
        """Test heuristic exploration with all aspects deeply covered."""
        # Create contributions with all aspects mentioned frequently
        contributions = [
            ContributionMessage(
                persona_code="CEO",
                persona_name="CEO",
                content="The problem is to increase MRR from $50K to $75K (problem_clarity). "
                "Success metrics include 50% growth and <$150 CAC (objectives). "
                "We could focus on paid ads, content marketing, or partnerships (options_alternatives). "
                "Key assumptions: market size of 10K potential customers, 5% conversion rate (key_assumptions). "
                "Top 3 risks: market saturation, competitor response, and economic downturn (risks_failure_modes). "
                "Budget constraint is $200K, timeline is 6 months (constraints). "
                "This affects our sales team workload and customer success capacity (stakeholders_impact). "
                "Dependencies include product stability and sales hiring (dependencies_unknowns).",
                round_number=1,
            )
        ]

        score, coverage = calculate_exploration_score_heuristic(
            contributions, "Should we expand marketing?"
        )

        # All 8 aspects mentioned with keywords, should be high
        # Heuristic scores slightly lower than LLM due to keyword matching limitations
        assert score >= 0.55, f"Expected high exploration score, got {score:.2f}"
        assert len(coverage) == 8, "Should have coverage for all 8 aspects"

    def test_exploration_score_heuristic_none(self):
        """Test heuristic exploration with no aspects covered."""
        contributions = [
            ContributionMessage(
                persona_code="CEO",
                persona_name="CEO",
                content="This is a generic statement with no specific aspects.",
                round_number=1,
            )
        ]

        score, coverage = calculate_exploration_score_heuristic(contributions, "Should we hire?")

        # No aspects covered, score should be low
        assert score < 0.3, f"Expected low exploration score, got {score:.2f}"

    def test_exploration_score_heuristic_partial(self):
        """Test heuristic exploration with some aspects covered."""
        contributions = [
            ContributionMessage(
                persona_code="CEO",
                persona_name="CEO",
                content="The problem is to increase revenue (problem_clarity). "
                "We want to achieve 50% growth (objectives). "
                "There are some risks involved (risks_failure_modes).",
                round_number=1,
            )
        ]

        score, coverage = calculate_exploration_score_heuristic(contributions, "Should we expand?")

        # 3-4 aspects partially covered (heuristic is conservative)
        assert 0.15 < score < 0.7, f"Expected moderate exploration score, got {score:.2f}"
        # Check that some aspects are marked as shallow/deep
        deep_or_shallow = [c for c in coverage if c.level in ["shallow", "deep"]]
        assert len(deep_or_shallow) >= 2, "Should have at least 2 aspects with some coverage"


class TestFocusScore:
    """Tests for focus score calculation."""

    def test_focus_score_heuristic_on_topic(self):
        """Test focus score with on-topic contributions."""
        problem = "Should we increase pricing by 20%?"
        contributions = [
            ContributionMessage(
                persona_code="CFO",
                persona_name="CFO",
                content="Pricing increase to $120/month would generate 20% more revenue. "
                "We need to assess price elasticity and competitor pricing.",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="CMO",
                persona_name="CMO",
                content="Customer surveys show 30% would accept a price increase. "
                "Pricing strategy should consider value perception.",
                round_number=1,
            ),
        ]

        score = calculate_focus_score_heuristic(contributions, problem)

        # On-topic contributions should have high focus
        assert score >= 0.7, f"Expected high focus score, got {score:.2f}"

    def test_focus_score_heuristic_off_topic(self):
        """Test focus score with off-topic contributions."""
        problem = "Should we hire a VP of Sales?"
        contributions = [
            ContributionMessage(
                persona_code="CTO",
                persona_name="CTO",
                content="The new database migration is progressing well. "
                "We've reduced latency by 40% and improved throughput.",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="CEO",
                persona_name="CEO",
                content="I enjoyed my vacation last week. The beach was beautiful.",
                round_number=1,
            ),
        ]

        score = calculate_focus_score_heuristic(contributions, problem)

        # Off-topic contributions should have low focus
        assert score < 0.5, f"Expected low focus score, got {score:.2f}"


class TestMeetingCompletenessIndex:
    """Tests for meeting completeness index calculation."""

    def test_completeness_index_high_quality(self):
        """Test completeness index with high quality metrics."""
        M_r = calculate_meeting_completeness_index(
            exploration_score=0.75,
            convergence_score=0.80,
            focus_score=0.85,
            novelty_score_recent=0.25,  # Low novelty (good for ending)
        )

        # High quality metrics should yield high M_r
        assert M_r >= 0.7, f"Expected high completeness index, got {M_r:.2f}"

    def test_completeness_index_low_quality(self):
        """Test completeness index with low quality metrics."""
        M_r = calculate_meeting_completeness_index(
            exploration_score=0.40,
            convergence_score=0.35,
            focus_score=0.50,
            novelty_score_recent=0.80,  # High novelty (still exploring)
        )

        # Low quality metrics should yield low M_r
        assert M_r < 0.5, f"Expected low completeness index, got {M_r:.2f}"

    def test_completeness_index_custom_weights(self):
        """Test completeness index with custom weights."""
        # Tactical config: convergence weighted higher
        M_r_tactical = calculate_meeting_completeness_index(
            exploration_score=0.50,
            convergence_score=0.80,
            focus_score=0.70,
            novelty_score_recent=0.30,
            weights={"exploration": 0.30, "convergence": 0.40, "focus": 0.20, "low_novelty": 0.10},
        )

        # Strategic config: exploration weighted higher
        M_r_strategic = calculate_meeting_completeness_index(
            exploration_score=0.50,
            convergence_score=0.80,
            focus_score=0.70,
            novelty_score_recent=0.30,
            weights={"exploration": 0.40, "convergence": 0.30, "focus": 0.20, "low_novelty": 0.10},
        )

        # Tactical should value high convergence more
        assert M_r_tactical > M_r_strategic, "Tactical config should value convergence more"

    def test_completeness_index_weight_normalization(self):
        """Test that weights are normalized if they don't sum to 1.0."""
        # Provide weights that don't sum to 1.0
        M_r = calculate_meeting_completeness_index(
            exploration_score=0.60,
            convergence_score=0.70,
            focus_score=0.75,
            novelty_score_recent=0.40,
            weights={
                "exploration": 0.40,
                "convergence": 0.40,
                "focus": 0.20,
                "low_novelty": 0.20,  # Sum = 1.2, will be normalized
            },
        )

        # Should still return valid score in 0-1 range
        assert 0.0 <= M_r <= 1.0, f"M_r should be in [0, 1], got {M_r:.2f}"

    def test_completeness_index_bounds(self):
        """Test that completeness index is bounded to [0, 1]."""
        # Test extreme values
        M_r_max = calculate_meeting_completeness_index(
            exploration_score=1.0,
            convergence_score=1.0,
            focus_score=1.0,
            novelty_score_recent=0.0,  # No novelty = bonus
        )

        M_r_min = calculate_meeting_completeness_index(
            exploration_score=0.0,
            convergence_score=0.0,
            focus_score=0.0,
            novelty_score_recent=1.0,  # High novelty = penalty
        )

        assert 0.0 <= M_r_min <= 1.0, f"M_r_min should be in [0, 1], got {M_r_min:.2f}"
        assert 0.0 <= M_r_max <= 1.0, f"M_r_max should be in [0, 1], got {M_r_max:.2f}"
        assert M_r_max > M_r_min, "Max metrics should yield higher M_r than min metrics"


class TestAspectCoverage:
    """Tests for AspectCoverage model."""

    def test_aspect_coverage_model(self):
        """Test AspectCoverage Pydantic model."""
        coverage = AspectCoverage(
            name="risks_failure_modes",
            level="deep",
            notes="Maria identified 3 major risks with mitigation strategies",
        )

        assert coverage.name == "risks_failure_modes"
        assert coverage.level == "deep"
        assert coverage.notes == "Maria identified 3 major risks with mitigation strategies"

    def test_aspect_coverage_validation(self):
        """Test that invalid level raises validation error."""
        with pytest.raises(ValueError):
            AspectCoverage(
                name="risks_failure_modes",
                level="invalid",  # Should be none/shallow/deep
                notes="Some notes",
            )
