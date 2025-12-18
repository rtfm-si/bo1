"""Tests for centralized model selection via get_model_for_role().

Validates:
- All task types in TASK_MODEL_DEFAULTS are resolvable
- Experiment override takes precedence when enabled
- Fallback when experiment disabled
- Unknown roles raise ValueError
"""

import json
import os
from unittest.mock import patch

import pytest

from bo1.config import (
    MODEL_ALIASES,
    TASK_MODEL_DEFAULTS,
    get_model_for_role,
    reset_settings,
    resolve_model_alias,
    resolve_tier_to_model,
)


class TestTaskModelDefaults:
    """Test that TASK_MODEL_DEFAULTS covers all expected task types."""

    def test_all_expected_task_types_exist(self):
        """Verify all expected task types are defined."""
        expected_tasks = [
            # Core agents
            "persona",
            "facilitator",
            "decomposer",
            "selector",
            # Fast agents
            "summarizer",
            "moderator",
            "researcher",
            "judge",
            # Synthesis and voting
            "synthesis",
            "meta_synthesis",
            "voting",
            "recommendation",
            # Quality and security
            "quality_check",
            "prompt_injection_check",
            # Auxiliary tasks
            "complexity_assessment",
            "enrichment",
            "research_detection",
        ]
        for task in expected_tasks:
            assert task in TASK_MODEL_DEFAULTS, f"Missing task type: {task}"

    def test_all_task_types_have_valid_tier(self):
        """All task types must map to 'core' or 'fast' tier."""
        valid_tiers = {"core", "fast"}
        for task, tier in TASK_MODEL_DEFAULTS.items():
            assert tier in valid_tiers, f"Task {task} has invalid tier: {tier}"


class TestGetModelForRole:
    """Test get_model_for_role() function."""

    def setup_method(self):
        """Reset settings and disable AI override before each test."""
        os.environ["AI_OVERRIDE"] = "false"
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_returns_full_model_id_for_all_task_types(self):
        """get_model_for_role() should return full model IDs for all task types."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            for task in TASK_MODEL_DEFAULTS:
                model_id = get_model_for_role(task)
                # Should be a full model ID (contains 'claude' or 'gpt')
                assert "claude" in model_id or "gpt" in model_id, (
                    f"Task {task} returned invalid model ID: {model_id}"
                )

    def test_case_insensitive_lookup(self):
        """Role lookup should be case-insensitive."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            assert get_model_for_role("persona") == get_model_for_role("PERSONA")
            assert get_model_for_role("synthesis") == get_model_for_role("Synthesis")

    def test_unknown_role_raises_error(self):
        """Unknown roles should raise ValueError."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            with pytest.raises(ValueError, match="Unknown role"):
                get_model_for_role("unknown_task_type")

    def test_core_tasks_resolve_to_sonnet(self):
        """Core tier tasks should resolve to Sonnet."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            core_tasks = ["persona", "facilitator", "decomposer", "selector", "voting"]
            for task in core_tasks:
                model_id = get_model_for_role(task)
                assert "sonnet" in model_id, f"Core task {task} should use Sonnet"

    def test_fast_tasks_resolve_to_haiku(self):
        """Fast tier tasks should resolve to Haiku."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            fast_tasks = [
                "summarizer",
                "moderator",
                "researcher",
                "judge",
                "quality_check",
                "complexity_assessment",
            ]
            for task in fast_tasks:
                model_id = get_model_for_role(task)
                assert "haiku" in model_id, f"Fast task {task} should use Haiku"


class TestExperimentOverride:
    """Test model experiment override functionality."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_experiment_override_takes_precedence(self):
        """When experiment enabled, mapping should override defaults."""
        experiment_mapping = json.dumps({"persona": "haiku", "synthesis": "sonnet"})

        with patch.dict(
            os.environ,
            {
                "AI_OVERRIDE": "false",
                "MODEL_EXPERIMENT_ENABLED": "true",
                "MODEL_EXPERIMENT_MAPPING": experiment_mapping,
            },
        ):
            reset_settings()

            # persona normally uses core (Sonnet), but experiment overrides to Haiku
            model_id = get_model_for_role("persona")
            assert "haiku" in model_id, f"Expected Haiku, got {model_id}"

            # synthesis normally uses fast (Haiku), but experiment overrides to Sonnet
            model_id = get_model_for_role("synthesis")
            assert "sonnet" in model_id, f"Expected Sonnet, got {model_id}"

    def test_experiment_disabled_uses_defaults(self):
        """When experiment disabled, defaults should be used."""
        experiment_mapping = json.dumps({"persona": "haiku"})

        with patch.dict(
            os.environ,
            {
                "AI_OVERRIDE": "false",
                "MODEL_EXPERIMENT_ENABLED": "false",
                "MODEL_EXPERIMENT_MAPPING": experiment_mapping,
            },
        ):
            reset_settings()

            # persona should use default (core = Sonnet)
            model_id = get_model_for_role("persona")
            assert "sonnet" in model_id, f"Expected Sonnet, got {model_id}"

    def test_experiment_with_invalid_json_falls_back(self):
        """Invalid JSON in mapping should fall back to defaults."""
        with patch.dict(
            os.environ,
            {
                "AI_OVERRIDE": "false",
                "MODEL_EXPERIMENT_ENABLED": "true",
                "MODEL_EXPERIMENT_MAPPING": "not valid json",
            },
        ):
            reset_settings()

            # Should fall back to default (core = Sonnet)
            model_id = get_model_for_role("persona")
            assert "sonnet" in model_id, f"Expected Sonnet, got {model_id}"

    def test_experiment_with_unmapped_role_uses_default(self):
        """Roles not in experiment mapping should use defaults."""
        experiment_mapping = json.dumps({"persona": "haiku"})

        with patch.dict(
            os.environ,
            {
                "AI_OVERRIDE": "false",
                "MODEL_EXPERIMENT_ENABLED": "true",
                "MODEL_EXPERIMENT_MAPPING": experiment_mapping,
            },
        ):
            reset_settings()

            # synthesis not in mapping, should use default (fast = Haiku)
            model_id = get_model_for_role("synthesis")
            assert "haiku" in model_id, f"Expected Haiku, got {model_id}"


class TestResolveTierToModel:
    """Test resolve_tier_to_model() function."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_core_tier_resolves_to_sonnet(self):
        """Core tier should resolve to Sonnet for Anthropic."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            model_id = resolve_tier_to_model("core", provider="anthropic")
            assert "sonnet" in model_id

    def test_fast_tier_resolves_to_haiku(self):
        """Fast tier should resolve to Haiku for Anthropic."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            model_id = resolve_tier_to_model("fast", provider="anthropic")
            assert "haiku" in model_id

    def test_direct_alias_passthrough(self):
        """Direct model aliases should pass through."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            model_id = resolve_tier_to_model("sonnet")
            assert "sonnet" in model_id

            model_id = resolve_tier_to_model("haiku")
            assert "haiku" in model_id


class TestResolveModelAlias:
    """Test resolve_model_alias() function."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_known_aliases_resolve(self):
        """Known aliases should resolve to full model IDs."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            for alias, expected_id in MODEL_ALIASES.items():
                result = resolve_model_alias(alias)
                assert result == expected_id, f"Alias {alias}: expected {expected_id}, got {result}"

    def test_unknown_alias_returns_as_is(self):
        """Unknown aliases should be returned as-is (assumed full model ID)."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            full_id = "claude-sonnet-4-5-20250929"
            assert resolve_model_alias(full_id) == full_id


class TestIntegration:
    """Integration tests verifying model selection works end-to-end."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    def teardown_method(self):
        """Reset settings after each test."""
        reset_settings()

    def test_all_tasks_produce_valid_anthropic_model_ids(self):
        """All tasks should produce valid Anthropic model IDs."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            for task in TASK_MODEL_DEFAULTS:
                model_id = get_model_for_role(task)
                # Check it's a valid Anthropic model ID format
                assert model_id.startswith("claude-"), (
                    f"Task {task} produced invalid model ID: {model_id}"
                )
                # Check it contains version date (YYYYMMDD pattern)
                assert any(c.isdigit() for c in model_id), (
                    f"Task {task} model ID missing version: {model_id}"
                )
