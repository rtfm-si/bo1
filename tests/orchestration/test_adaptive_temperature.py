"""Tests for phase-adaptive temperature in persona executor."""

from bo1.constants import LLMConfig


class TestTemperatureAdjustmentsConstant:
    """Tests for TEMPERATURE_ADJUSTMENTS configuration."""

    def test_temperature_adjustments_exists(self) -> None:
        """TEMPERATURE_ADJUSTMENTS dict should exist in LLMConfig."""
        assert hasattr(LLMConfig, "TEMPERATURE_ADJUSTMENTS")
        assert isinstance(LLMConfig.TEMPERATURE_ADJUSTMENTS, dict)

    def test_temperature_adjustments_has_all_phases(self) -> None:
        """TEMPERATURE_ADJUSTMENTS should have entries for all deliberation phases."""
        expected_phases = {"initial", "early", "middle", "late"}
        actual_phases = set(LLMConfig.TEMPERATURE_ADJUSTMENTS.keys())
        assert expected_phases == actual_phases

    def test_initial_phase_no_adjustment(self) -> None:
        """Initial phase (round 1) should have no temperature adjustment."""
        assert LLMConfig.TEMPERATURE_ADJUSTMENTS["initial"] == 0.0

    def test_early_phase_positive_adjustment(self) -> None:
        """Early phase (challenge rounds) should have positive temperature adjustment."""
        adjustment = LLMConfig.TEMPERATURE_ADJUSTMENTS["early"]
        assert adjustment > 0.0, "Early/challenge phase should increase temperature"
        assert adjustment == 0.15, "Expected +0.15 for challenge phase"

    def test_middle_phase_no_adjustment(self) -> None:
        """Middle phase should have no temperature adjustment."""
        assert LLMConfig.TEMPERATURE_ADJUSTMENTS["middle"] == 0.0

    def test_late_phase_negative_adjustment(self) -> None:
        """Late phase (convergence) should have negative temperature adjustment."""
        adjustment = LLMConfig.TEMPERATURE_ADJUSTMENTS["late"]
        assert adjustment < 0.0, "Late/convergence phase should decrease temperature"
        assert adjustment == -0.10, "Expected -0.10 for convergence phase"


class TestTemperatureClamping:
    """Tests for temperature clamping bounds."""

    def test_temperature_min_exists(self) -> None:
        """TEMPERATURE_MIN should be defined."""
        assert hasattr(LLMConfig, "TEMPERATURE_MIN")
        assert LLMConfig.TEMPERATURE_MIN == 0.0

    def test_temperature_max_exists(self) -> None:
        """TEMPERATURE_MAX should be defined (1.0 for Anthropic API)."""
        assert hasattr(LLMConfig, "TEMPERATURE_MAX")
        assert LLMConfig.TEMPERATURE_MAX == 1.0

    def test_clamping_logic(self) -> None:
        """Test temperature clamping at boundaries."""
        # Test lower bound clamping
        base_temp = 0.05
        adjustment = -0.10  # late phase
        result = base_temp + adjustment
        clamped = max(LLMConfig.TEMPERATURE_MIN, min(LLMConfig.TEMPERATURE_MAX, result))
        assert clamped == 0.0, "Should clamp to minimum"

        # Test upper bound clamping (now 1.0 for Anthropic API)
        base_temp = 0.95
        adjustment = 0.15  # early phase
        result = base_temp + adjustment
        clamped = max(LLMConfig.TEMPERATURE_MIN, min(LLMConfig.TEMPERATURE_MAX, result))
        assert clamped == 1.0, "Should clamp to maximum"

        # Test no clamping needed
        base_temp = 0.7
        adjustment = 0.15
        result = base_temp + adjustment
        clamped = max(LLMConfig.TEMPERATURE_MIN, min(LLMConfig.TEMPERATURE_MAX, result))
        assert clamped == 0.85, "Should not clamp when in range"


class TestPhaseToTemperatureMapping:
    """Integration tests for phase-to-temperature mapping."""

    def test_early_rounds_get_challenge_adjustment(self) -> None:
        """Rounds 2-4 (early phase) should get +0.15 adjustment."""
        from bo1.prompts.utils import get_round_phase_config

        # Rounds 2-4 of 10 = early phase (<=40% progress)
        config = get_round_phase_config(round_number=3, max_rounds=10)
        assert config["phase"] == "early"

        adjustment = LLMConfig.TEMPERATURE_ADJUSTMENTS[config["phase"]]
        assert adjustment == 0.15

    def test_convergence_rounds_get_late_adjustment(self) -> None:
        """Rounds 8+ (late phase) should get -0.10 adjustment."""
        from bo1.prompts.utils import get_round_phase_config

        # Round 9 of 10 = late phase (>70% progress)
        config = get_round_phase_config(round_number=9, max_rounds=10)
        assert config["phase"] == "late"

        adjustment = LLMConfig.TEMPERATURE_ADJUSTMENTS[config["phase"]]
        assert adjustment == -0.10

    def test_initial_round_no_adjustment(self) -> None:
        """Round 1 (initial phase) should have no adjustment."""
        from bo1.prompts.utils import get_round_phase_config

        config = get_round_phase_config(round_number=1, max_rounds=10)
        assert config["phase"] == "initial"

        adjustment = LLMConfig.TEMPERATURE_ADJUSTMENTS[config["phase"]]
        assert adjustment == 0.0
