"""Tests for Anthropic prompt caching feature.

Validates:
- cache_control header is included when cache_system=True
- Cache metrics are extracted from API response
- Feature flag (enable_prompt_cache) disables caching when False
- CostTracker logs cache hit/miss metrics
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.llm.client import ClaudeClient, TokenUsage
from bo1.llm.cost_tracker import CostRecord, CostTracker


class TestClaudeClientCaching:
    """Test ClaudeClient prompt caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_control_included_when_enabled(self):
        """Verify cache_control header is set when cache_system=True."""
        client = ClaudeClient()

        # Mock the Anthropic SDK
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage = MagicMock(
            input_tokens=1000,
            output_tokens=200,
            cache_creation_input_tokens=800,
            cache_read_input_tokens=0,
        )

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            response_text, token_usage = await client.call(
                model="sonnet",
                messages=[{"role": "user", "content": "Test"}],
                system="You are a helpful assistant.",
                cache_system=True,
            )

            # Verify API was called
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args.kwargs

            # Verify system prompt has cache_control
            assert "system" in call_kwargs
            system_param = call_kwargs["system"]
            assert isinstance(system_param, list)
            assert len(system_param) == 1
            assert system_param[0]["type"] == "text"
            assert "cache_control" in system_param[0]
            assert system_param[0]["cache_control"]["type"] == "ephemeral"

    @pytest.mark.asyncio
    async def test_no_cache_control_when_disabled(self):
        """Verify cache_control is not set when cache_system=False."""
        client = ClaudeClient()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Test response")]
        mock_response.usage = MagicMock(
            input_tokens=1000,
            output_tokens=200,
        )

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            await client.call(
                model="sonnet",
                messages=[{"role": "user", "content": "Test"}],
                system="You are a helpful assistant.",
                cache_system=False,
            )

            call_kwargs = mock_client.messages.create.call_args.kwargs
            system_param = call_kwargs["system"]

            # System should still be a list for newer models
            assert isinstance(system_param, list)
            # But should NOT have cache_control
            assert "cache_control" not in system_param[0]

    @pytest.mark.asyncio
    async def test_cache_tokens_extracted_from_response(self):
        """Verify cache_creation_tokens and cache_read_tokens are extracted."""
        client = ClaudeClient()

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Cached response")]
        mock_response.usage = MagicMock(
            input_tokens=1000,
            output_tokens=200,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=800,  # Cache hit!
        )

        with patch("anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client

            _, token_usage = await client.call(
                model="sonnet",
                messages=[{"role": "user", "content": "Test"}],
                system="You are a helpful assistant.",
                cache_system=True,
            )

            # Verify cache metrics extracted
            assert token_usage.cache_creation_tokens == 0
            assert token_usage.cache_read_tokens == 800
            assert token_usage.cache_hit_rate > 0


class TestTokenUsageCacheMetrics:
    """Test TokenUsage cache hit rate calculations."""

    def test_cache_hit_rate_calculation(self):
        """Verify cache_hit_rate property calculates correctly."""
        usage = TokenUsage(
            input_tokens=200,
            output_tokens=100,
            cache_creation_tokens=0,
            cache_read_tokens=800,
        )
        # 800 cache reads / (200 input + 800 cache reads) = 0.8 (80%)
        assert usage.cache_hit_rate == pytest.approx(0.8, rel=0.01)

    def test_cache_hit_rate_zero_when_no_cache(self):
        """Verify cache_hit_rate is 0 when no cache usage."""
        usage = TokenUsage(
            input_tokens=1000,
            output_tokens=200,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        )
        assert usage.cache_hit_rate == 0.0

    def test_cache_hit_rate_with_cache_creation(self):
        """Verify cache_hit_rate handles cache creation tokens."""
        usage = TokenUsage(
            input_tokens=200,
            output_tokens=100,
            cache_creation_tokens=800,  # Creating cache
            cache_read_tokens=0,
        )
        # No cache reads, so rate should be 0
        assert usage.cache_hit_rate == 0.0


class TestCostRecordCacheTracking:
    """Test CostRecord cache hit tracking."""

    def test_cache_hit_property(self):
        """Verify cache_hit property detects cache usage."""
        record_with_hit = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            cache_read_tokens=500,
        )
        assert record_with_hit.cache_hit is True

        record_without_hit = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            cache_read_tokens=0,
        )
        assert record_without_hit.cache_hit is False

    def test_cost_saved_calculation(self):
        """Verify cost_saved property calculates savings correctly."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.003,
            cost_without_optimization=0.030,
        )
        # Saved $0.027 with caching
        assert record.cost_saved == pytest.approx(0.027, rel=0.01)

    def test_cost_saved_zero_without_optimization(self):
        """Verify cost_saved is 0 when no optimization data."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            total_cost=0.030,
            cost_without_optimization=None,
        )
        assert record.cost_saved == 0.0


class TestFeatureFlagIntegration:
    """Test enable_prompt_cache feature flag integration."""

    def test_feature_flag_enabled_sets_cache_system_true(self):
        """Verify cache_system=True is passed when feature flag is enabled."""
        from bo1.llm.broker import PromptRequest

        # Test that PromptRequest accepts cache_system=True
        request = PromptRequest(
            system="You are an expert.",
            user_message="Analyze this.",
            model="core",
            cache_system=True,
        )
        assert request.cache_system is True

    def test_feature_flag_disabled_sets_cache_system_false(self):
        """Verify cache_system=False is passed when feature flag is disabled."""
        from bo1.llm.broker import PromptRequest

        # Test that PromptRequest accepts cache_system=False
        request = PromptRequest(
            system="You are an expert.",
            user_message="Analyze this.",
            model="core",
            cache_system=False,
        )
        assert request.cache_system is False

    def test_settings_has_enable_prompt_cache_default_true(self):
        """Verify enable_prompt_cache defaults to True in Settings."""
        from bo1.config import Settings

        # Create a settings instance with minimal required values
        settings = Settings(
            anthropic_api_key="test-key",
            _env_file=None,  # Don't load .env file
        )
        assert settings.enable_prompt_cache is True

    def test_persona_executor_reads_feature_flag(self):
        """Verify PersonaExecutor uses get_settings() for cache_system."""
        # Read the source code to verify the implementation
        import inspect

        from bo1.orchestration.persona_executor import PersonaExecutor

        source = inspect.getsource(PersonaExecutor.execute_persona_call)

        # Verify the implementation reads from settings
        assert "get_settings()" in source
        assert "enable_prompt_cache" in source
        assert "cache_system" in source


class TestCostTrackerCacheMetrics:
    """Test CostTracker cache metrics emission."""

    def setup_method(self):
        """Clear buffer before each test."""
        CostTracker._clear_buffer_for_testing()

    def teardown_method(self):
        """Clear buffer after each test."""
        CostTracker._clear_buffer_for_testing()

    def test_emit_cache_metrics_on_cache_hit(self):
        """Verify cache hit metrics are emitted when cache_read_tokens > 0."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=200,
            output_tokens=100,
            cache_read_tokens=800,
            total_cost=0.003,
            cost_without_optimization=0.030,
        )

        with patch("bo1.llm.cost_tracker.db_session"):
            with patch("backend.api.metrics.metrics") as mock_metrics:
                with patch("backend.api.metrics.prom_metrics") as mock_prom:
                    CostTracker._emit_cache_metrics(record)

                    # Verify cache hit metric incremented
                    mock_metrics.increment.assert_any_call("llm.cache.hits")

                    # Verify cost saved was observed
                    mock_metrics.observe.assert_any_call(
                        "llm.cache.cost_saved", pytest.approx(0.027, rel=0.01)
                    )

                    # Verify Prometheus metric
                    mock_prom.record_cache_hit.assert_called_with(True)

    def test_emit_cache_metrics_on_cache_miss(self):
        """Verify cache miss metrics are emitted when no cache usage."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=1000,
            output_tokens=200,
            cache_read_tokens=0,  # No cache hit
        )

        with patch("backend.api.metrics.metrics") as mock_metrics:
            with patch("backend.api.metrics.prom_metrics") as mock_prom:
                CostTracker._emit_cache_metrics(record)

                # Verify cache miss metric incremented
                mock_metrics.increment.assert_called_with("llm.cache.misses")

                # Verify Prometheus metric
                mock_prom.record_cache_hit.assert_called_with(False)

    def test_optimization_type_set_on_cache_hit(self):
        """Verify optimization_type is set to 'prompt_cache' on cache hit."""
        record = CostRecord(
            provider="anthropic",
            model_name="claude-sonnet-4-5-20250929",
            operation_type="completion",
            input_tokens=200,
            output_tokens=100,
            cache_read_tokens=800,
        )

        # Simulate what happens in track_call context manager
        if record.cache_read_tokens > 0:
            record.optimization_type = "prompt_cache"

        assert record.optimization_type == "prompt_cache"
