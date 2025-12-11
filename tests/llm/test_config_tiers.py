"""Tests for provider-agnostic tier system in config.py."""

import os
from unittest.mock import patch

import pytest

from bo1.config import (
    MODEL_ALIASES,
    OPENAI_PRICING,
    TASK_MODEL_DEFAULTS,
    TIER_ALIASES,
    get_model_for_role,
    get_service_pricing,
    reset_settings,
    resolve_model_alias,
    resolve_tier_to_model,
)


@pytest.fixture(autouse=True)
def reset_settings_fixture() -> None:
    """Reset settings before each test to avoid test pollution."""
    reset_settings()


class TestTierAliases:
    """Test tier alias configuration."""

    def test_tier_aliases_exist(self) -> None:
        """Test that core and fast tiers are defined."""
        assert "core" in TIER_ALIASES
        assert "fast" in TIER_ALIASES

    def test_tier_aliases_have_both_providers(self) -> None:
        """Test that both providers are defined for each tier."""
        for tier in ["core", "fast"]:
            assert "anthropic" in TIER_ALIASES[tier]
            assert "openai" in TIER_ALIASES[tier]

    def test_tier_aliases_map_to_valid_model_aliases(self) -> None:
        """Test that tier aliases resolve to valid model aliases."""
        for tier, providers in TIER_ALIASES.items():
            for provider, model_alias in providers.items():
                assert model_alias in MODEL_ALIASES, (
                    f"Tier '{tier}' provider '{provider}' maps to unknown alias '{model_alias}'"
                )


class TestTaskModelDefaults:
    """Test task-to-tier mapping."""

    def test_task_defaults_use_tiers(self) -> None:
        """Test that task defaults use tier aliases."""
        valid_tiers = {"core", "fast"}
        for task, tier in TASK_MODEL_DEFAULTS.items():
            assert tier in valid_tiers, f"Task '{task}' uses invalid tier '{tier}'"

    def test_expected_tasks_defined(self) -> None:
        """Test that expected tasks are defined."""
        expected = ["persona", "facilitator", "summarizer", "decomposer", "selector"]
        for task in expected:
            assert task in TASK_MODEL_DEFAULTS


class TestResolveTierToModel:
    """Test resolve_tier_to_model function."""

    def test_resolve_core_anthropic(self) -> None:
        """Test resolving 'core' tier with Anthropic provider."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            result = resolve_tier_to_model("core", provider="anthropic")
            assert result == MODEL_ALIASES["sonnet"]

    def test_resolve_core_openai(self) -> None:
        """Test resolving 'core' tier with OpenAI provider."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            result = resolve_tier_to_model("core", provider="openai")
            assert result == MODEL_ALIASES["gpt-5.1"]

    def test_resolve_fast_anthropic(self) -> None:
        """Test resolving 'fast' tier with Anthropic provider."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            result = resolve_tier_to_model("fast", provider="anthropic")
            assert result == MODEL_ALIASES["haiku"]

    def test_resolve_fast_openai(self) -> None:
        """Test resolving 'fast' tier with OpenAI provider."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            result = resolve_tier_to_model("fast", provider="openai")
            assert result == MODEL_ALIASES["gpt-5.1-mini"]

    def test_resolve_direct_alias_still_works(self) -> None:
        """Test that direct model aliases still resolve correctly."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            result = resolve_tier_to_model("sonnet", provider="anthropic")
            assert result == MODEL_ALIASES["sonnet"]

    def test_resolve_uses_primary_provider_by_default(self) -> None:
        """Test that primary provider is used when not specified."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false", "LLM_PRIMARY_PROVIDER": "anthropic"}):
            reset_settings()
            result = resolve_tier_to_model("core")
            assert result == MODEL_ALIASES["sonnet"]

    def test_resolve_invalid_provider_raises(self) -> None:
        """Test that invalid provider raises ValueError."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            with pytest.raises(ValueError, match="not configured for tier"):
                resolve_tier_to_model("core", provider="invalid_provider")


class TestGetModelForRole:
    """Test get_model_for_role function."""

    def test_persona_uses_core_tier(self) -> None:
        """Test that persona role uses core tier."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false", "LLM_PRIMARY_PROVIDER": "anthropic"}):
            reset_settings()
            result = get_model_for_role("persona")
            assert result == MODEL_ALIASES["sonnet"]

    def test_summarizer_uses_fast_tier(self) -> None:
        """Test that summarizer role uses fast tier."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false", "LLM_PRIMARY_PROVIDER": "anthropic"}):
            reset_settings()
            result = get_model_for_role("summarizer")
            assert result == MODEL_ALIASES["haiku"]

    def test_get_model_for_role_with_openai_provider(self) -> None:
        """Test get_model_for_role with OpenAI provider."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false", "LLM_PRIMARY_PROVIDER": "openai"}):
            reset_settings()
            result = get_model_for_role("persona", provider="openai")
            assert result == MODEL_ALIASES["gpt-5.1"]

    def test_unknown_role_raises(self) -> None:
        """Test that unknown role raises ValueError."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            with pytest.raises(ValueError, match="Unknown role"):
                get_model_for_role("unknown_role")


class TestOpenAIPricing:
    """Test OpenAI pricing configuration."""

    def test_openai_pricing_defined(self) -> None:
        """Test that OpenAI pricing is defined."""
        assert "gpt-5.1-2025-04-14" in OPENAI_PRICING
        assert "gpt-5.1-mini-2025-07-18" in OPENAI_PRICING

    def test_openai_pricing_has_required_fields(self) -> None:
        """Test that OpenAI pricing has required fields."""
        for model, pricing in OPENAI_PRICING.items():
            assert "input" in pricing, f"{model} missing 'input' pricing"
            assert "output" in pricing, f"{model} missing 'output' pricing"

    def test_get_service_pricing_openai(self) -> None:
        """Test get_service_pricing for OpenAI."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            price = get_service_pricing("openai", "gpt-5.1", "input")
            assert price == 2.50

    def test_get_service_pricing_openai_invalid_model(self) -> None:
        """Test get_service_pricing raises for invalid OpenAI model."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            with pytest.raises(ValueError, match="Unknown OpenAI model"):
                get_service_pricing("openai", "invalid-model", "input")


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_resolve_model_alias_still_works(self) -> None:
        """Test that resolve_model_alias still works for direct aliases."""
        with patch.dict(os.environ, {"AI_OVERRIDE": "false"}):
            reset_settings()
            assert resolve_model_alias("sonnet") == MODEL_ALIASES["sonnet"]
            assert resolve_model_alias("haiku") == MODEL_ALIASES["haiku"]

    def test_model_by_role_fallback(self) -> None:
        """Test that MODEL_BY_ROLE fallback works in get_model_for_role."""
        # This tests that existing code using old role names still works
        with patch.dict(os.environ, {"AI_OVERRIDE": "false", "LLM_PRIMARY_PROVIDER": "anthropic"}):
            reset_settings()
            result = get_model_for_role("PERSONA")  # uppercase
            assert result == MODEL_ALIASES["sonnet"]
