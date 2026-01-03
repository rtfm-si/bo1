"""Unit tests for challenge phase validation.

Tests marker detection accuracy, threshold logic, and edge cases.
"""

from bo1.prompts.validation import (
    ChallengeValidationResult,
    detect_challenge_markers,
    generate_challenge_reprompt,
    has_sufficient_challenge_engagement,
    validate_challenge_phase_contribution,
)


class TestDetectChallengeMarkers:
    """Tests for detect_challenge_markers function."""

    def test_detects_however(self):
        """Test detection of 'however' marker."""
        text = "This is a good idea. However, there are some risks to consider."
        markers = detect_challenge_markers(text)
        assert "however" in markers

    def test_detects_multiple_markers(self):
        """Test detection of multiple distinct markers."""
        text = (
            "However, I disagree with this approach. "
            "The main risk is that it fails to account for edge cases. "
            "What if the user provides invalid input?"
        )
        markers = detect_challenge_markers(text)
        assert "however" in markers
        assert "disagree" in markers
        assert "risk" in markers
        assert "fails_to" in markers
        assert "what_if" in markers

    def test_detects_risk_variations(self):
        """Test detection of risk word variations."""
        assert "risk" in detect_challenge_markers("This is risky")
        assert "risk" in detect_challenge_markers("There are risks involved")
        assert "risk" in detect_challenge_markers("The main risk is...")

    def test_detects_counterargument(self):
        """Test detection of counterargument variations."""
        assert "counterargument" in detect_challenge_markers("A counterargument would be...")
        assert "counterargument" in detect_challenge_markers("The counter-argument is that...")

    def test_detects_limitation_weakness(self):
        """Test detection of limitation and weakness markers."""
        text = "The limitation of this approach is its weakness in handling large datasets."
        markers = detect_challenge_markers(text)
        assert "limitation" in markers
        assert "weakness" in markers

    def test_detects_challenge_disagree(self):
        """Test detection of challenge and disagreement markers."""
        text = "I must challenge this assumption. I disagree with the conclusion."
        markers = detect_challenge_markers(text)
        assert "challenge" in markers
        assert "disagree" in markers

    def test_detects_overlooked_missing(self):
        """Test detection of overlooked/missing markers."""
        text = "This analysis has overlooked a key factor. Missing from the discussion is..."
        markers = detect_challenge_markers(text)
        assert "overlooked" in markers
        assert "missing" in markers

    def test_detects_critique_skeptic(self):
        """Test detection of critique and skeptic markers."""
        text = "My critique is that... I'm skeptical about this claim."
        markers = detect_challenge_markers(text)
        assert "critique" in markers
        assert "skeptic" in markers

    def test_detects_devils_advocate(self):
        """Test detection of devil's advocate marker."""
        text = "Playing devil's advocate, what if this assumption is wrong?"
        markers = detect_challenge_markers(text)
        assert "devil_advocate" in markers
        assert "what_if" in markers

    def test_empty_string_returns_empty_list(self):
        """Test that empty string returns no markers."""
        assert detect_challenge_markers("") == []

    def test_none_text_returns_empty_list(self):
        """Test that None-like empty text returns no markers."""
        assert detect_challenge_markers("") == []

    def test_agreeable_text_finds_few_markers(self):
        """Test that agreeable text without challenge finds few/no markers."""
        text = (
            "I completely agree with this analysis. "
            "The proposed solution is excellent and well-thought-out. "
            "This is exactly what we need."
        )
        markers = detect_challenge_markers(text)
        # Should find very few or no markers
        assert len(markers) < 2

    def test_case_insensitive(self):
        """Test that marker detection is case-insensitive."""
        assert "however" in detect_challenge_markers("HOWEVER, this is important")
        assert "however" in detect_challenge_markers("HoWeVeR, this is mixed case")
        assert "risk" in detect_challenge_markers("The RISKS are significant")


class TestHasSufficientChallengeEngagement:
    """Tests for has_sufficient_challenge_engagement function."""

    def test_passes_with_sufficient_markers(self):
        """Test that text with sufficient markers passes."""
        text = "However, there are risks to consider. The limitation is clear."
        result = has_sufficient_challenge_engagement(text, min_markers=2)
        assert result.passes_threshold is True
        assert result.marker_count >= 2

    def test_fails_with_insufficient_markers(self):
        """Test that text with insufficient markers fails."""
        text = "This is a great idea that I fully support."
        result = has_sufficient_challenge_engagement(text, min_markers=2)
        assert result.passes_threshold is False
        assert result.marker_count < 2

    def test_threshold_customizable(self):
        """Test that threshold can be customized."""
        text = "However, this has risks."  # 2 markers

        result_low = has_sufficient_challenge_engagement(text, min_markers=1)
        assert result_low.passes_threshold is True

        result_high = has_sufficient_challenge_engagement(text, min_markers=3)
        assert result_high.passes_threshold is False

    def test_returns_validation_result_dataclass(self):
        """Test that function returns ChallengeValidationResult."""
        text = "However, the risk is significant."
        result = has_sufficient_challenge_engagement(text)

        assert isinstance(result, ChallengeValidationResult)
        assert isinstance(result.detected_markers, list)
        assert isinstance(result.marker_count, int)
        assert isinstance(result.passes_threshold, bool)
        assert isinstance(result.threshold, int)

    def test_detected_markers_populated(self):
        """Test that detected_markers list is populated correctly."""
        text = "However, I must challenge this risky assumption."
        result = has_sufficient_challenge_engagement(text)

        assert "however" in result.detected_markers
        assert "challenge" in result.detected_markers
        assert "risk" in result.detected_markers  # "risky"
        assert "assumptions" in result.detected_markers


class TestValidateChallengePhaseContribution:
    """Tests for validate_challenge_phase_contribution function."""

    def test_skips_non_challenge_rounds(self):
        """Test that validation passes for non-challenge rounds (1, 2, 5, 6)."""
        agreeable_text = "I agree with everything said so far."

        # Round 1 (exploration) - should pass
        passed, result = validate_challenge_phase_contribution(
            content=agreeable_text,
            round_number=1,
            expert_name="TestExpert",
        )
        assert passed is True

        # Round 2 (exploration) - should pass
        passed, result = validate_challenge_phase_contribution(
            content=agreeable_text,
            round_number=2,
            expert_name="TestExpert",
        )
        assert passed is True

        # Round 5 (convergence) - should pass
        passed, result = validate_challenge_phase_contribution(
            content=agreeable_text,
            round_number=5,
            expert_name="TestExpert",
        )
        assert passed is True

    def test_validates_round_3(self):
        """Test that round 3 contributions are validated."""
        # Good challenge contribution
        challenge_text = "However, I disagree with this approach. The risks are significant."
        passed, result = validate_challenge_phase_contribution(
            content=challenge_text,
            round_number=3,
            expert_name="TestExpert",
        )
        assert passed is True
        assert result.marker_count >= 2

        # Agreeable contribution should fail
        agreeable_text = "I completely agree with this analysis."
        passed, result = validate_challenge_phase_contribution(
            content=agreeable_text,
            round_number=3,
            expert_name="TestExpert",
        )
        assert passed is False

    def test_validates_round_4(self):
        """Test that round 4 contributions are validated."""
        # Good challenge contribution
        challenge_text = "What if we're overlooking a key flaw? The limitation is clear."
        passed, result = validate_challenge_phase_contribution(
            content=challenge_text,
            round_number=4,
            expert_name="TestExpert",
        )
        assert passed is True

        # Weak challenge contribution should fail
        weak_text = "This seems reasonable to me."
        passed, result = validate_challenge_phase_contribution(
            content=weak_text,
            round_number=4,
            expert_name="TestExpert",
        )
        assert passed is False

    def test_returns_tuple(self):
        """Test that function returns (bool, ChallengeValidationResult) tuple."""
        passed, result = validate_challenge_phase_contribution(
            content="However, the risk is clear.",
            round_number=3,
            expert_name="TestExpert",
        )

        assert isinstance(passed, bool)
        assert isinstance(result, ChallengeValidationResult)

    def test_expert_type_parameter(self):
        """Test that expert_type parameter is accepted."""
        passed, result = validate_challenge_phase_contribution(
            content="However, I must challenge this risky assumption.",
            round_number=3,
            expert_name="TestExpert",
            expert_type="researcher",
        )
        assert passed is True

    def test_custom_threshold(self):
        """Test custom min_markers threshold."""
        text = "However, this seems risky."  # 2 markers

        # Default threshold (2) - should pass
        passed, _ = validate_challenge_phase_contribution(
            content=text,
            round_number=3,
            expert_name="TestExpert",
            min_markers=2,
        )
        assert passed is True

        # Higher threshold - should fail
        passed, _ = validate_challenge_phase_contribution(
            content=text,
            round_number=3,
            expert_name="TestExpert",
            min_markers=4,
        )
        assert passed is False


class TestEdgeCases:
    """Edge case tests for challenge validation."""

    def test_very_short_text(self):
        """Test with very short text."""
        markers = detect_challenge_markers("but")
        assert "but" in markers

        result = has_sufficient_challenge_engagement("but", min_markers=2)
        assert result.passes_threshold is False

    def test_very_long_text(self):
        """Test with very long text containing multiple markers."""
        long_text = (
            "However, I must strongly disagree with the proposed approach. "
            "There are significant risks that have been overlooked. "
            "The main limitation is that it fails to account for edge cases. "
            "What if the user provides malicious input? "
            "I am skeptical about the security assumptions. "
            "Playing devil's advocate, this could be a major flaw. "
            "The weakness in the design is concerning. "
        ) * 3  # Repeat to make it longer

        markers = detect_challenge_markers(long_text)
        assert len(markers) >= 5  # Should find many markers

        result = has_sufficient_challenge_engagement(long_text)
        assert result.passes_threshold is True

    def test_markers_in_quotes_still_detected(self):
        """Test that markers inside quotes are still detected.

        Note: This is expected behavior - quoted text still counts.
        Future enhancement could exclude quoted markers.
        """
        text = 'The expert said "however, there are risks" and I agree.'
        markers = detect_challenge_markers(text)
        # Currently, quoted markers are detected
        assert "however" in markers
        assert "risk" in markers

    def test_partial_word_not_matched(self):
        """Test that partial words are not matched."""
        # "shower" contains "however" substring but should not match
        # Our regex uses word boundaries so this should work correctly
        text = "I took a shower this morning."
        markers = detect_challenge_markers(text)
        assert "however" not in markers

    def test_punctuation_adjacent(self):
        """Test markers adjacent to punctuation."""
        text = "However, risks! Weakness... Flaw?"
        markers = detect_challenge_markers(text)
        assert "however" in markers
        assert "risk" in markers
        assert "weakness" in markers
        assert "flaw" in markers

    def test_newlines_in_text(self):
        """Test text with newlines."""
        text = "However,\nthe risks\nare significant."
        markers = detect_challenge_markers(text)
        assert "however" in markers
        assert "risk" in markers

    def test_unicode_text(self):
        """Test with unicode characters in text."""
        text = "However, the risks are significant. émoji: 🤔"
        markers = detect_challenge_markers(text)
        assert "however" in markers
        assert "risk" in markers


class TestGenerateChallengeReprompt:
    """Tests for generate_challenge_reprompt function."""

    def test_basic_reprompt_generation(self):
        """Test that reprompt is generated with required elements."""
        reprompt = generate_challenge_reprompt(
            expert_name="TestExpert",
            detected_markers=["but"],
            required_markers=2,
            original_contribution="I think this is a good idea but we should consider it carefully.",
        )

        assert "lacked sufficient critical engagement" in reprompt
        assert "1 marker(s)" in reprompt
        assert "but" in reprompt
        assert "At least 2 distinct challenge markers" in reprompt
        assert "I think this is a good idea" in reprompt

    def test_reprompt_with_no_markers(self):
        """Test reprompt when no markers were detected."""
        reprompt = generate_challenge_reprompt(
            expert_name="TestExpert",
            detected_markers=[],
            required_markers=2,
            original_contribution="I completely agree with this approach.",
        )

        assert "0 marker(s) - none" in reprompt
        assert "At least 2 distinct challenge markers" in reprompt

    def test_reprompt_truncates_long_contribution(self):
        """Test that long contributions are truncated in reprompt."""
        long_content = "A" * 300

        reprompt = generate_challenge_reprompt(
            expert_name="TestExpert",
            detected_markers=[],
            required_markers=2,
            original_contribution=long_content,
        )

        # Should truncate to 200 chars + "..."
        assert "..." in reprompt
        assert "A" * 200 in reprompt
        assert "A" * 201 not in reprompt.replace("...", "")

    def test_reprompt_includes_challenge_guidance(self):
        """Test that reprompt includes guidance on challenge markers."""
        reprompt = generate_challenge_reprompt(
            expert_name="TestExpert",
            detected_markers=["risk"],
            required_markers=2,
            original_contribution="This is risky.",
        )

        # Check for category guidance
        assert "Counterarguments" in reprompt
        assert "Risk identification" in reprompt
        assert "Disagreement" in reprompt
        assert "Missing considerations" in reprompt
        assert "Critical analysis" in reprompt

    def test_reprompt_with_multiple_markers(self):
        """Test reprompt correctly shows multiple detected markers."""
        reprompt = generate_challenge_reprompt(
            expert_name="TestExpert",
            detected_markers=["however", "but"],
            required_markers=3,
            original_contribution="However, but I still agree.",
        )

        assert "2 marker(s) - however, but" in reprompt
        assert "At least 3 distinct challenge markers" in reprompt

    def test_reprompt_includes_instructions(self):
        """Test that reprompt includes actionable instructions."""
        reprompt = generate_challenge_reprompt(
            expert_name="TestExpert",
            detected_markers=[],
            required_markers=2,
            original_contribution="Good idea.",
        )

        assert "actively challenges" in reprompt
        assert "questions assumptions" in reprompt
        assert "DO NOT simply agree" in reprompt
