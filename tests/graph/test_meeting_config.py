"""Tests for meeting configuration and critical aspects.

Tests:
- Config schema validation
- Preset configs (tactical, strategic, default)
- Config selection logic
- Weight normalization
"""

import pytest

from bo1.graph.meeting_config import (
    CRITICAL_ASPECTS,
    DEFAULT_CONFIG,
    STRATEGIC_CONFIG,
    TACTICAL_CONFIG,
    MeetingConfig,
    get_aspect_description,
    get_meeting_config,
)


class TestCriticalAspects:
    """Tests for critical aspects definitions."""

    def test_critical_aspects_list(self):
        """Test that all 8 critical aspects are defined."""
        assert len(CRITICAL_ASPECTS) == 8
        assert "problem_clarity" in CRITICAL_ASPECTS
        assert "objectives" in CRITICAL_ASPECTS
        assert "options_alternatives" in CRITICAL_ASPECTS
        assert "key_assumptions" in CRITICAL_ASPECTS
        assert "risks_failure_modes" in CRITICAL_ASPECTS
        assert "constraints" in CRITICAL_ASPECTS
        assert "stakeholders_impact" in CRITICAL_ASPECTS
        assert "dependencies_unknowns" in CRITICAL_ASPECTS

    def test_aspect_descriptions(self):
        """Test that descriptions exist for all aspects."""
        for aspect in CRITICAL_ASPECTS:
            description = get_aspect_description(aspect)
            assert "description" in description
            assert "examples" in description
            assert "none" in description["examples"]
            assert "shallow" in description["examples"]
            assert "deep" in description["examples"]

    def test_invalid_aspect_raises_error(self):
        """Test that invalid aspect name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown aspect"):
            get_aspect_description("invalid_aspect")


class TestMeetingConfig:
    """Tests for MeetingConfig schema and validation."""

    def test_config_schema_validation(self):
        """Test that config schema validates correctly."""
        config = MeetingConfig(
            meeting_type="default",
            weights={"exploration": 0.35, "convergence": 0.35, "focus": 0.20, "low_novelty": 0.10},
            thresholds={
                "exploration": {"min_to_allow_end": 0.6, "target_good": 0.75},
                "convergence": {"min_to_allow_end": 0.6, "target_good": 0.75},
                "focus": {"min_acceptable": 0.6, "target_good": 0.8},
                "novelty": {"novelty_floor_recent": 0.25},
                "composite": {"min_index_to_recommend_end": 0.7},
            },
            round_limits={"min_rounds": 3, "max_rounds": 10},
        )

        assert config.meeting_type == "default"
        assert config.weights["exploration"] == 0.35
        assert config.thresholds["exploration"]["min_to_allow_end"] == 0.6

    def test_weights_must_sum_to_one(self):
        """Test that weights are validated to sum to 1.0."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            MeetingConfig(
                meeting_type="default",
                weights={
                    "exploration": 0.5,
                    "convergence": 0.5,
                    "focus": 0.2,
                    "low_novelty": 0.2,  # Sum = 1.4, invalid
                },
                thresholds={},
                round_limits={"min_rounds": 3, "max_rounds": 10},
            )

    def test_thresholds_in_range(self):
        """Test that thresholds are validated to be in 0-1 range."""
        with pytest.raises(ValueError, match="must be in"):
            MeetingConfig(
                meeting_type="default",
                weights={
                    "exploration": 0.35,
                    "convergence": 0.35,
                    "focus": 0.20,
                    "low_novelty": 0.10,
                },
                thresholds={
                    "exploration": {"min_to_allow_end": 1.5}  # Invalid: > 1.0
                },
                round_limits={"min_rounds": 3, "max_rounds": 10},
            )


class TestPresetConfigs:
    """Tests for preset configurations."""

    def test_tactical_config(self):
        """Test tactical configuration settings."""
        assert TACTICAL_CONFIG.meeting_type == "tactical"
        assert TACTICAL_CONFIG.weights["convergence"] == 0.40  # Higher weight on convergence
        assert TACTICAL_CONFIG.round_limits["max_rounds"] == 7  # Shorter max
        assert TACTICAL_CONFIG.thresholds["exploration"]["min_to_allow_end"] == 0.5  # Lower bar

    def test_strategic_config(self):
        """Test strategic configuration settings."""
        assert STRATEGIC_CONFIG.meeting_type == "strategic"
        assert STRATEGIC_CONFIG.weights["exploration"] == 0.40  # Higher weight on exploration
        assert STRATEGIC_CONFIG.round_limits["max_rounds"] == 10  # Longer max
        assert STRATEGIC_CONFIG.thresholds["exploration"]["min_to_allow_end"] == 0.65  # Higher bar

    def test_default_config(self):
        """Test default configuration settings."""
        assert DEFAULT_CONFIG.meeting_type == "default"
        assert DEFAULT_CONFIG.weights["exploration"] == 0.35  # Balanced
        assert DEFAULT_CONFIG.weights["convergence"] == 0.35  # Balanced
        assert DEFAULT_CONFIG.round_limits["min_rounds"] == 3

    def test_all_configs_have_valid_weights(self):
        """Test that all preset configs have weights summing to 1.0."""
        for config in [TACTICAL_CONFIG, STRATEGIC_CONFIG, DEFAULT_CONFIG]:
            total = sum(config.weights.values())
            assert 0.99 <= total <= 1.01, f"{config.meeting_type} weights sum to {total}"


class TestConfigSelection:
    """Tests for config selection logic."""

    def test_explicit_meeting_type(self):
        """Test that explicit meeting_type is respected."""
        state = {"meeting_type": "tactical"}
        config = get_meeting_config(state)
        assert config.meeting_type == "tactical"

        state = {"meeting_type": "strategic"}
        config = get_meeting_config(state)
        assert config.meeting_type == "strategic"

    def test_strategic_keywords_heuristic(self):
        """Test that strategic keywords trigger strategic config."""
        state = {
            "problem": {
                "description": "Should we develop a long-term expansion strategy for European markets?"
            }
        }
        config = get_meeting_config(state)
        assert config.meeting_type == "strategic"

    def test_tactical_keywords_heuristic(self):
        """Test that tactical keywords trigger tactical config."""
        state = {"problem": {"description": "Should we build this new feature for our product?"}}
        config = get_meeting_config(state)
        assert config.meeting_type == "tactical"

    def test_high_stakes_triggers_strategic(self):
        """Test that high financial stakes trigger strategic config."""
        state = {"problem": {"description": "Should we invest $1 million in Series A funding?"}}
        config = get_meeting_config(state)
        assert config.meeting_type == "strategic"

    def test_default_fallback(self):
        """Test that default config is used when no clear heuristic."""
        state = {"problem": {"description": "Some neutral question without keywords"}}
        config = get_meeting_config(state)
        assert config.meeting_type == "default"

    def test_empty_state_returns_default(self):
        """Test that empty state returns default config."""
        state = {}
        config = get_meeting_config(state)
        assert config.meeting_type == "default"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
