"""Integration tests for challenge phase validation in round context.

Tests that challenge phase validation is correctly integrated with
the deliberation round processing.
"""

from unittest.mock import MagicMock, patch

from bo1.prompts.validation import validate_challenge_phase_contribution


class TestChallengePhaseInRoundContext:
    """Tests for challenge validation in deliberation round context."""

    def test_round_3_triggers_validation(self):
        """Test that round 3 contributions trigger validation."""
        challenge_content = "However, I disagree with this. The risks are significant."

        passed, result = validate_challenge_phase_contribution(
            content=challenge_content,
            round_number=3,
            expert_name="TestExpert",
        )

        # Round 3 should validate and this content should pass
        assert passed is True
        assert result.marker_count >= 2

    def test_round_4_triggers_validation(self):
        """Test that round 4 contributions trigger validation."""
        weak_content = "I agree completely with the proposed solution."

        passed, result = validate_challenge_phase_contribution(
            content=weak_content,
            round_number=4,
            expert_name="TestExpert",
        )

        # Round 4 should validate and this weak content should fail
        assert passed is False
        assert result.marker_count < 2

    def test_round_2_skips_validation(self):
        """Test that round 2 (exploration phase) skips validation."""
        weak_content = "I agree completely with the proposed solution."

        passed, result = validate_challenge_phase_contribution(
            content=weak_content,
            round_number=2,
            expert_name="TestExpert",
        )

        # Round 2 should skip validation, so even weak content passes
        assert passed is True

    def test_round_5_skips_validation(self):
        """Test that round 5 (convergence phase) skips validation."""
        weak_content = "I agree completely with the proposed solution."

        passed, result = validate_challenge_phase_contribution(
            content=weak_content,
            round_number=5,
            expert_name="TestExpert",
        )

        # Round 5 should skip validation
        assert passed is True

    def test_validation_result_contains_all_fields(self):
        """Test that validation result contains all expected fields."""
        challenge_content = "However, the risks here are significant. What if this fails?"

        passed, result = validate_challenge_phase_contribution(
            content=challenge_content,
            round_number=3,
            expert_name="TestExpert",
        )

        assert hasattr(result, "detected_markers")
        assert hasattr(result, "marker_count")
        assert hasattr(result, "passes_threshold")
        assert hasattr(result, "threshold")


class TestChallengeValidationMetrics:
    """Tests for challenge validation metric recording."""

    @patch("backend.api.middleware.metrics.record_challenge_validation")
    def test_metric_recorded_for_passing_contribution(self, mock_record):
        """Test that metric is recorded for passing contributions."""
        from bo1.graph.nodes.rounds import _validate_challenge_contributions

        # Create mock contribution
        contribution = MagicMock()
        contribution.persona_name = "TestExpert"
        contribution.persona_type = "persona"
        contribution.content = "However, I disagree. The risks are clear."

        _validate_challenge_contributions([contribution], round_number=3)

        mock_record.assert_called_once()
        call_args = mock_record.call_args
        assert call_args[1]["passed"] is True
        assert call_args[1]["round_number"] == 3
        assert call_args[1]["expert_type"] == "persona"

    @patch("backend.api.middleware.metrics.record_challenge_validation")
    def test_metric_recorded_for_failing_contribution(self, mock_record):
        """Test that metric is recorded for failing contributions."""
        from bo1.graph.nodes.rounds import _validate_challenge_contributions

        # Create mock contribution with weak content
        contribution = MagicMock()
        contribution.persona_name = "TestExpert"
        contribution.persona_type = "persona"
        contribution.content = "I agree with everything proposed."

        _validate_challenge_contributions([contribution], round_number=3)

        mock_record.assert_called_once()
        call_args = mock_record.call_args
        assert call_args[1]["passed"] is False
        assert call_args[1]["round_number"] == 3

    @patch("backend.api.middleware.metrics.record_challenge_validation")
    def test_metrics_recorded_for_multiple_contributions(self, mock_record):
        """Test that metrics are recorded for all contributions in a round."""
        from bo1.graph.nodes.rounds import _validate_challenge_contributions

        contributions = [
            MagicMock(
                persona_name="Expert1",
                persona_type="persona",
                content="However, I disagree. The risks are clear.",
            ),
            MagicMock(
                persona_name="Expert2",
                persona_type="researcher",
                content="I completely agree with this approach.",
            ),
            MagicMock(
                persona_name="Expert3",
                persona_type="persona",
                content="What if we're overlooking a flaw? The limitation is obvious.",
            ),
        ]

        _validate_challenge_contributions(contributions, round_number=4)

        # Should be called once per contribution
        assert mock_record.call_count == 3


class TestChallengePhaseIntegration:
    """Integration tests for challenge phase in full round flow."""

    def test_phase_determination_for_challenge_rounds(self):
        """Test that rounds 3-4 are correctly identified as challenge phase."""
        from bo1.graph.nodes.rounds import _determine_phase

        # Rounds 3-4 should be challenge phase (assuming 6 max rounds)
        assert _determine_phase(3, 6) == "challenge"
        assert _determine_phase(4, 6) == "challenge"

        # Other rounds should not be challenge
        assert _determine_phase(1, 6) != "challenge"
        assert _determine_phase(2, 6) != "challenge"
        assert _determine_phase(5, 6) != "challenge"

    def test_validation_with_real_contribution_patterns(self):
        """Test validation with realistic contribution patterns."""
        # Strong challenge contribution
        strong_challenge = """
        I must respectfully push back on this recommendation. While the proposed
        approach has merit, there are significant risks that haven't been adequately
        addressed. Specifically, the assumption that users will adopt this feature
        quickly is questionable - historical data suggests otherwise.

        What if adoption rates are lower than projected? The limitation of this
        model is that it doesn't account for competitive responses. I'm skeptical
        about the timeline presented.
        """

        passed, result = validate_challenge_phase_contribution(
            content=strong_challenge,
            round_number=3,
            expert_name="CriticalAnalyst",
        )

        assert passed is True
        assert result.marker_count >= 4  # Multiple strong markers

        # Weak challenge contribution
        weak_challenge = """
        I think this is a reasonable approach. The team has done good work
        identifying the key considerations. I particularly appreciate the
        attention to detail in the implementation plan. This aligns well
        with our strategic objectives.
        """

        passed, result = validate_challenge_phase_contribution(
            content=weak_challenge,
            round_number=3,
            expert_name="AgreeableExpert",
        )

        assert passed is False
        assert result.marker_count < 2

    def test_validation_boundary_conditions(self):
        """Test validation at exact threshold boundaries."""
        # Exactly 2 markers (should pass with default threshold of 2)
        two_marker_text = "However, there are risks to consider."

        passed, result = validate_challenge_phase_contribution(
            content=two_marker_text,
            round_number=3,
            expert_name="TestExpert",
        )

        assert result.marker_count == 2
        assert passed is True

        # Exactly 1 marker (should fail)
        one_marker_text = "However, this is a good approach."

        passed, result = validate_challenge_phase_contribution(
            content=one_marker_text,
            round_number=3,
            expert_name="TestExpert",
        )

        assert result.marker_count == 1
        assert passed is False
