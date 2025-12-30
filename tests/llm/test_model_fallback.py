"""Unit tests for within-provider model fallback.

Tests:
- Fallback chain lookup
- Chain exhaustion behavior
- Model fallback eligibility
"""

from unittest.mock import MagicMock

import pytest

from bo1.llm.model_fallback import get_fallback_model, is_model_fallback_eligible


@pytest.fixture
def mock_settings():
    """Create mock settings with configurable model fallback options."""
    settings = MagicMock()
    settings.llm_model_fallback_enabled = True
    settings.llm_anthropic_fallback_chain = ["claude-sonnet-4-20250514", "claude-haiku-3.5"]
    settings.llm_openai_fallback_chain = ["gpt-4o-mini", "gpt-3.5-turbo"]
    return settings


class TestGetFallbackModel:
    """Tests for get_fallback_model function."""

    def test_returns_first_fallback_when_model_not_in_chain(self, monkeypatch, mock_settings):
        """When current model is not in chain, return first fallback."""
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("anthropic", "claude-opus-4-20250514")

        assert result == "claude-sonnet-4-20250514"

    def test_returns_next_in_chain_when_model_in_chain(self, monkeypatch, mock_settings):
        """When current model is in chain, return next model."""
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("anthropic", "claude-sonnet-4-20250514")

        assert result == "claude-haiku-3.5"

    def test_returns_none_when_chain_exhausted(self, monkeypatch, mock_settings):
        """When at end of chain, return None."""
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("anthropic", "claude-haiku-3.5")

        assert result is None

    def test_returns_none_when_disabled(self, monkeypatch, mock_settings):
        """When model fallback is disabled, return None."""
        mock_settings.llm_model_fallback_enabled = False
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("anthropic", "claude-opus-4-20250514")

        assert result is None

    def test_returns_none_for_empty_chain(self, monkeypatch, mock_settings):
        """When chain is empty, return None."""
        mock_settings.llm_anthropic_fallback_chain = []
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("anthropic", "claude-opus-4-20250514")

        assert result is None

    def test_returns_none_for_unknown_provider(self, monkeypatch, mock_settings):
        """When provider is unknown, return None."""
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("unknown_provider", "some-model")

        assert result is None

    def test_openai_fallback_chain(self, monkeypatch, mock_settings):
        """Test OpenAI provider uses its own fallback chain."""
        monkeypatch.setattr("bo1.llm.model_fallback.get_settings", lambda: mock_settings)

        result = get_fallback_model("openai", "gpt-4o")

        assert result == "gpt-4o-mini"


class TestIsModelFallbackEligible:
    """Tests for is_model_fallback_eligible function."""

    def test_529_is_eligible(self):
        """529 (overloaded) is eligible for model fallback."""
        assert is_model_fallback_eligible(529) is True

    def test_503_is_eligible(self):
        """503 (service unavailable) is eligible for model fallback."""
        assert is_model_fallback_eligible(503) is True

    def test_500_is_not_eligible(self):
        """500 (internal server error) is not eligible."""
        assert is_model_fallback_eligible(500) is False

    def test_429_is_not_eligible(self):
        """429 (rate limit) is not eligible for model fallback."""
        assert is_model_fallback_eligible(429) is False

    def test_none_is_not_eligible(self):
        """None status code is not eligible."""
        assert is_model_fallback_eligible(None) is False
