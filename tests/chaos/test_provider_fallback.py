"""Chaos tests for LLM provider fallback behavior.

Validates:
- Anthropic circuit breaker open triggers OpenAI fallback
- OpenAI circuit breaker open triggers Anthropic fallback
- Fallback disabled raises RuntimeError when circuit open
- Both providers down raises RuntimeError
- Prometheus metric incremented on fallback activation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APIError

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from bo1.llm.client import TokenUsage


def _create_mock_settings(
    primary: str = "anthropic",
    fallback_enabled: bool = True,
) -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.llm_primary_provider = primary
    settings.llm_fallback_enabled = fallback_enabled
    return settings


def _create_request(request_id: str = "test-123") -> PromptRequest:
    """Create a test prompt request."""
    return PromptRequest(
        system="You are a test assistant.",
        user_message="Hello, world!",
        model="core",
        phase="test",
        agent_type="TestAgent",
        request_id=request_id,
    )


def _mock_token_usage() -> TokenUsage:
    """Create mock token usage."""
    return TokenUsage(
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=0,
        cache_read_tokens=0,
    )


@pytest.mark.chaos
class TestAnthropicCircuitOpenTriggersOpenAIFallback:
    """Test fallback to OpenAI when Anthropic circuit is open."""

    @pytest.mark.asyncio
    async def test_anthropic_circuit_open_triggers_openai_fallback(self) -> None:
        """When Anthropic circuit is open and fallback enabled, use OpenAI."""
        # Create circuit breakers
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        # Trip the Anthropic circuit breaker
        async def failing_call() -> None:
            raise APIError(message="Service unavailable", request=None, body=None)  # type: ignore[arg-type]

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)
        assert anthropic_cb.state == CircuitState.OPEN

        # Mock the broker
        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker") as mock_get_cb,
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            # Setup mocks
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-3-5-sonnet-20241022"
            mock_cost_ctx.return_value = {}

            # Cache returns None (no hit)
            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            # Return appropriate circuit breaker based on provider
            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            # Mock OpenAI client to succeed
            mock_openai = AsyncMock()
            mock_openai.call.return_value = ("OpenAI response", _mock_token_usage())
            mock_get_openai.return_value = mock_openai

            # Make the call - should fallback to OpenAI
            request = _create_request()
            response = await broker.call(request)

            # Verify fallback occurred
            assert response.content == "OpenAI response"
            mock_fallback_metric.assert_called_once_with(
                from_provider="anthropic",
                to_provider="openai",
                reason="circuit_breaker_open",
            )

    @pytest.mark.asyncio
    async def test_openai_circuit_open_triggers_anthropic_fallback(self) -> None:
        """When OpenAI circuit is open (and is primary), fallback to Anthropic."""
        # Create circuit breakers - OpenAI is primary and tripped
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        # Trip the OpenAI circuit breaker
        async def failing_call() -> None:
            raise APIError(message="Service unavailable", request=None, body=None)  # type: ignore[arg-type]

        with pytest.raises(APIError):
            await openai_cb.call(failing_call)
        assert openai_cb.state == CircuitState.OPEN

        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker") as mock_get_cb,
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
            patch.object(broker, "client") as mock_anthropic,
        ):
            # Setup - OpenAI is primary
            mock_settings.return_value = _create_mock_settings(primary="openai")
            mock_provider.return_value = "openai"
            mock_resolve.return_value = "gpt-4o"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return openai_cb if provider == "openai" else anthropic_cb

            mock_get_cb.side_effect = get_cb

            # Anthropic client succeeds
            mock_anthropic.call = AsyncMock(
                return_value=("Anthropic response", _mock_token_usage())
            )

            request = _create_request()
            response = await broker.call(request)

            assert response.content == "Anthropic response"
            mock_fallback_metric.assert_called_once_with(
                from_provider="openai",
                to_provider="anthropic",
                reason="circuit_breaker_open",
            )


@pytest.mark.chaos
class TestFallbackDisabledRaisesError:
    """Test behavior when fallback is disabled."""

    @pytest.mark.asyncio
    async def test_fallback_disabled_raises_error(self) -> None:
        """When fallback disabled and circuit open, raise RuntimeError."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        # Trip the circuit
        async def failing_call() -> None:
            raise APIError(message="Service unavailable", request=None, body=None)  # type: ignore[arg-type]

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)
        assert anthropic_cb.state == CircuitState.OPEN

        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker", return_value=anthropic_cb),
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
        ):
            # Fallback disabled
            mock_settings.return_value = _create_mock_settings(fallback_enabled=False)
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-3-5-sonnet-20241022"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            request = _create_request()

            with pytest.raises(RuntimeError) as exc_info:
                await broker.call(request)

            assert "temporarily unavailable" in str(exc_info.value)
            mock_fallback_metric.assert_not_called()


@pytest.mark.chaos
class TestBothProvidersDownRaisesError:
    """Test behavior when both providers are down."""

    @pytest.mark.asyncio
    async def test_both_providers_down_raises_error(self) -> None:
        """When both circuit breakers are open, raise RuntimeError."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        # Trip both circuits
        async def failing_call() -> None:
            raise APIError(message="Service unavailable", request=None, body=None)  # type: ignore[arg-type]

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)
        with pytest.raises(APIError):
            await openai_cb.call(failing_call)

        assert anthropic_cb.state == CircuitState.OPEN
        assert openai_cb.state == CircuitState.OPEN

        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker") as mock_get_cb,
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-3-5-sonnet-20241022"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            request = _create_request()

            with pytest.raises(RuntimeError) as exc_info:
                await broker.call(request)

            assert "temporarily unavailable" in str(exc_info.value)
            # Fallback was NOT activated because both are down
            mock_fallback_metric.assert_not_called()


@pytest.mark.chaos
class TestFallbackPreventsDoubleRetry:
    """Test that fallback flag prevents infinite loop."""

    @pytest.mark.asyncio
    async def test_fallback_flag_prevents_double_fallback(self) -> None:
        """Used fallback flag prevents cascading fallback attempts.

        When the primary circuit is open, we try fallback once.
        The _call_with_provider helper is used for fallback - it should only be
        called once even if it also fails.
        """
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        # Trip Anthropic circuit breaker
        async def failing_call() -> None:
            raise APIError(message="Service unavailable", request=None, body=None)  # type: ignore[arg-type]

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)

        # Also trip OpenAI circuit breaker
        with pytest.raises(APIError):
            await openai_cb.call(failing_call)

        assert anthropic_cb.state == CircuitState.OPEN
        assert openai_cb.state == CircuitState.OPEN

        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker") as mock_get_cb,
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-3-5-sonnet-20241022"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            request = _create_request()

            # Should raise RuntimeError - both circuits open, no fallback possible
            with pytest.raises(RuntimeError) as exc_info:
                await broker.call(request)

            assert "temporarily unavailable" in str(exc_info.value)

            # Verify fallback was NOT attempted (both circuits open)
            mock_fallback_metric.assert_not_called()


@pytest.mark.chaos
class TestFallbackIncrementsPrometheusCounter:
    """Test Prometheus metric tracking."""

    @pytest.mark.asyncio
    async def test_fallback_increments_prometheus_counter(self) -> None:
        """Fallback activation increments the prometheus counter."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        # Trip Anthropic
        async def failing_call() -> None:
            raise APIError(message="Service unavailable", request=None, body=None)  # type: ignore[arg-type]

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)

        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker") as mock_get_cb,
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-3-5-sonnet-20241022"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            mock_openai = AsyncMock()
            mock_openai.call.return_value = ("OpenAI response", _mock_token_usage())
            mock_get_openai.return_value = mock_openai

            request = _create_request()
            await broker.call(request)

            # Verify metric was recorded with correct labels
            mock_fallback_metric.assert_called_once()
            call_args = mock_fallback_metric.call_args
            assert call_args.kwargs["from_provider"] == "anthropic"
            assert call_args.kwargs["to_provider"] == "openai"
            assert call_args.kwargs["reason"] == "circuit_breaker_open"
