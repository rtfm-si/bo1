"""Tests for validate_trait_consistency() in bo1/agents/base.py.

Tests persona output validation against declared traits using heuristic analysis.
"""

from bo1.agents.base import validate_trait_consistency


class TestTraitValidationAnalytical:
    """Tests for high analytical trait validation."""

    def test_high_analytical_with_data_language_passes(self) -> None:
        """High analytical persona using data language should pass."""
        contribution = """
        Based on the data from our Q3 report, the evidence suggests a 15% increase
        in conversion rates. The metrics indicate strong performance, with our
        benchmark analysis showing we're outperforming the industry average.
        """
        traits = {"analytical": 0.9, "creative": 0.5}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Maria")

        assert is_valid is True
        assert reason is None

    def test_high_analytical_without_data_language_warns(self) -> None:
        """High analytical persona without data/evidence language should warn."""
        contribution = (
            """
        I think we should consider expanding our team. The market seems favorable
        and there are many opportunities ahead. We could explore new territories
        and build stronger relationships with customers. The timing feels right.
        """
            * 2
        )  # Make it long enough to trigger check
        traits = {"analytical": 0.8, "creative": 0.5}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Maria")

        # Non-strict mode: still valid but with warning
        assert is_valid is True
        assert reason is not None
        assert "analytical" in reason.lower()

    def test_high_analytical_strict_mode_fails(self) -> None:
        """High analytical in strict mode should fail without data language."""
        contribution = (
            """
        I believe we should move forward with this initiative. The team is
        enthusiastic and we have the resources to make it happen. Let's proceed
        with optimism and confidence in our collective abilities.
        """
            * 2
        )
        traits = {"analytical": 0.9}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Maria", strict=True)

        assert is_valid is False
        assert reason is not None

    def test_short_contribution_skips_analytical_check(self) -> None:
        """Short contributions should skip the analytical check."""
        contribution = "I agree with this approach."
        traits = {"analytical": 0.9}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Maria")

        assert is_valid is True
        assert reason is None


class TestTraitValidationRiskAverse:
    """Tests for high risk_averse trait validation."""

    def test_high_risk_averse_with_risk_language_passes(self) -> None:
        """High risk_averse persona mentioning risks should pass."""
        contribution = """
        Before we proceed, I have some concerns about this approach. The potential
        risks include market volatility and regulatory challenges. We should be
        careful about overcommitting resources before validating our assumptions.
        """
        traits = {"risk_averse": 0.8, "analytical": 0.5}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Tariq")

        assert is_valid is True
        assert reason is None

    def test_high_risk_averse_without_risk_language_warns(self) -> None:
        """High risk_averse persona without risk language should warn."""
        contribution = (
            """
        This is a great opportunity that we should pursue immediately. The market
        conditions are favorable and our team is ready. I recommend we allocate
        maximum resources to capture this window of opportunity.
        """
            * 2
        )
        traits = {"risk_averse": 0.8}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Tariq")

        assert is_valid is True
        assert reason is not None
        assert "risk_averse" in reason.lower()


class TestTraitValidationCreative:
    """Tests for low creative trait validation."""

    def test_low_creative_with_creative_language_warns(self) -> None:
        """Low creative persona using highly creative language should warn."""
        contribution = """
        Imagine a revolutionary approach where we completely disrupt the market
        with a wild idea. Let's brainstorm some blue sky thinking that could
        transform how customers interact with our product.
        """
        traits = {"creative": 0.2, "analytical": 0.8}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Sarah")

        assert is_valid is True
        assert reason is not None
        assert "creative" in reason.lower()

    def test_low_creative_without_creative_language_passes(self) -> None:
        """Low creative persona with measured language should pass."""
        contribution = """
        Based on our established processes, I recommend we follow the proven
        methodology we've used before. The systematic approach minimizes variables
        and provides predictable outcomes aligned with our objectives.
        """
        traits = {"creative": 0.2}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Sarah")

        assert is_valid is True
        assert reason is None


class TestTraitValidationOptimistic:
    """Tests for high optimistic trait validation."""

    def test_high_optimistic_with_positive_framing_passes(self) -> None:
        """High optimistic persona with positive framing should pass."""
        contribution = """
        This represents a significant growth opportunity for our organization.
        The potential benefits include market expansion and improved customer
        satisfaction. I see promising indicators that suggest we can succeed.
        """
        traits = {"optimistic": 0.8}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Zara")

        assert is_valid is True
        assert reason is None

    def test_high_optimistic_with_pessimistic_framing_warns(self) -> None:
        """High optimistic persona with pessimistic framing should warn."""
        contribution = (
            """
        This initiative is doomed from the start. The approach will fail because
        it's fundamentally flawed. The situation is impossible to recover from
        and will likely end in disaster for everyone involved.
        """
            * 2
        )
        traits = {"optimistic": 0.9}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Zara")

        assert is_valid is True
        assert reason is not None
        assert "optimistic" in reason.lower()

    def test_balanced_sentiment_passes(self) -> None:
        """High optimistic with both positive and negative terms should pass."""
        contribution = (
            """
        While the project may fail in certain areas, overall I see tremendous
        opportunity for growth. The potential benefits outweigh the risks, and
        I believe we can succeed with the right approach.
        """
            * 2
        )
        traits = {"optimistic": 0.8}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Zara")

        assert is_valid is True


class TestTraitValidationMultipleTraits:
    """Tests for multiple trait interactions."""

    def test_multiple_trait_issues_combined(self) -> None:
        """Multiple trait mismatches should all be reported."""
        contribution = (
            """
        Imagine we could disrupt the entire market with this wild idea! Everything
        is going to work perfectly without any challenges. We don't need to look
        at the numbers because it just feels right. This revolutionary approach
        will transform everything without any possible downsides. The whole concept
        is based on intuition and creative thinking rather than systematic analysis
        or careful evaluation of potential problems. Let's move forward boldly!
        """
            * 3
        )  # Make it long enough (>200 chars) to trigger analytical check
        traits = {
            "analytical": 0.9,  # Missing data language
            "creative": 0.2,  # Using creative language
            "risk_averse": 0.8,  # Missing risk language
        }

        is_valid, reason = validate_trait_consistency(contribution, traits, "Multi")

        assert is_valid is True  # Non-strict mode
        assert reason is not None
        # Should contain at least one trait warning (creative at minimum)
        assert "trait" in reason.lower()

    def test_all_traits_consistent_passes(self) -> None:
        """Contribution consistent with all traits should pass cleanly."""
        contribution = """
        Looking at the data, I see both significant opportunities and potential
        risks we need to consider carefully. The evidence suggests a measured
        approach would be optimal. My recommendation is based on benchmark analysis
        showing favorable metrics for growth, though we should be cautious about
        the challenges ahead.
        """
        traits = {
            "analytical": 0.8,
            "optimistic": 0.6,
            "risk_averse": 0.7,
            "creative": 0.5,
        }

        is_valid, reason = validate_trait_consistency(contribution, traits, "Balanced")

        assert is_valid is True
        assert reason is None


class TestTraitValidationEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_traits_passes(self) -> None:
        """Empty traits dict should pass without checks."""
        contribution = "This is a contribution."
        traits: dict[str, float] = {}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Test")

        assert is_valid is True
        assert reason is None

    def test_empty_contribution_passes(self) -> None:
        """Empty contribution should pass (too short for checks)."""
        contribution = ""
        traits = {"analytical": 0.9}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Test")

        assert is_valid is True
        assert reason is None

    def test_default_trait_scores(self) -> None:
        """Missing trait keys should use default 0.5 score."""
        contribution = "A normal contribution without any special markers." * 5
        traits = {"detail_oriented": 0.8}  # Other traits not specified

        is_valid, reason = validate_trait_consistency(contribution, traits, "Test")

        # Should pass because missing traits default to 0.5 (below thresholds)
        assert is_valid is True

    def test_threshold_boundary_analytical(self) -> None:
        """Analytical score exactly at 0.7 threshold should trigger check."""
        # Ensure contribution is >200 chars and contains NO analytical markers
        contribution = """
        This is a standard business contribution that discusses general concepts
        and ideas. The approach is based on intuition and general business sense
        rather than systematic planning or empirical observation of outcomes.
        I think we should move forward with confidence in our collective abilities.
        """
        # Verify no analytical markers present
        analytical_markers = [
            "data",
            "evidence",
            "analysis",
            "metric",
            "number",
            "percentage",
            "statistic",
            "research",
            "benchmark",
            "measure",
        ]
        assert not any(m in contribution.lower() for m in analytical_markers)
        assert len(contribution) > 200  # Verify length requirement

        # At threshold
        traits_at = {"analytical": 0.7}
        is_valid_at, reason_at = validate_trait_consistency(contribution, traits_at, "Test")
        assert reason_at is not None  # Should warn

        # Below threshold
        traits_below = {"analytical": 0.69}
        is_valid_below, reason_below = validate_trait_consistency(
            contribution, traits_below, "Test"
        )
        assert reason_below is None  # Should not warn

    def test_case_insensitive_matching(self) -> None:
        """Marker matching should be case-insensitive."""
        contribution = "Based on our DATA and EVIDENCE, the ANALYSIS shows clear METRICS."
        traits = {"analytical": 0.9}

        is_valid, reason = validate_trait_consistency(contribution, traits, "Test")

        assert is_valid is True
        assert reason is None
