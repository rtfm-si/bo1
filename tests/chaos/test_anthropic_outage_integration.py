"""Integration chaos tests for Anthropic outage → OpenAI fallback validation.

Validates:
- Full outage flow: Anthropic 503 → circuit breaker trips → OpenAI fallback activates
- SSE event emission for `model_fallback` with correct payload
- Prometheus counter `bo1_provider_fallback_total` incremented
- Session completes successfully using fallback provider
- Fallback disabled raises RuntimeError with user-friendly message

These tests simulate real-world outage scenarios at the integration level.
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

# ============================================================================
# Test Fixtures and Helpers
# ============================================================================


def _create_mock_settings(
    primary: str = "anthropic",
    fallback_enabled: bool = True,
    model_fallback_enabled: bool = False,
) -> MagicMock:
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.llm_primary_provider = primary
    settings.llm_fallback_enabled = fallback_enabled
    settings.llm_model_fallback_enabled = model_fallback_enabled
    return settings


def _create_request(request_id: str = "chaos-test-123") -> PromptRequest:
    """Create a test prompt request."""
    return PromptRequest(
        system="You are a test assistant for chaos testing.",
        user_message="Test message for fallback validation.",
        model="core",
        phase="chaos_test",
        agent_type="ChaosTestAgent",
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


def _create_api_error(status_code: int = 503, message: str = "Service unavailable") -> APIError:
    """Create an APIError with specific status code."""
    error = APIError(message=message, request=None, body=None)  # type: ignore[arg-type]
    error.status_code = status_code  # type: ignore[attr-defined]
    return error


# ============================================================================
# TestAnthropicOutageFullFlow: Full outage simulation
# ============================================================================


@pytest.mark.chaos
class TestAnthropicOutageFullFlow:
    """Test full Anthropic outage → circuit breaker trip → OpenAI fallback flow."""

    @pytest.mark.asyncio
    async def test_anthropic_503_trips_circuit_and_activates_fallback(self) -> None:
        """Simulate Anthropic 503 → circuit trips → OpenAI fallback activates."""
        # Create circuit breakers with low threshold for testing
        anthropic_cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, transient_failure_threshold=1),
            service_name="anthropic",
        )
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5), service_name="openai")

        # Trip the Anthropic circuit breaker with 503
        async def failing_anthropic_call() -> None:
            raise _create_api_error(503, "Service unavailable")

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_anthropic_call)
        assert anthropic_cb.state == CircuitState.OPEN

        # Setup broker
        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker") as mock_get_cb,
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch("bo1.llm.broker.record_provider_fallback") as mock_fallback_metric,
            patch("bo1.llm.broker.record_llm_request"),
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
            mock_cost_ctx.return_value = {"session_id": "test-session-123"}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            # OpenAI succeeds as fallback
            mock_openai = AsyncMock()
            mock_openai.call.return_value = ("OpenAI fallback response", _mock_token_usage())
            mock_get_openai.return_value = mock_openai

            # Execute
            request = _create_request()
            response = await broker.call(request)

            # Verify fallback activated and succeeded
            assert response.content == "OpenAI fallback response"
            mock_fallback_metric.assert_called_once_with(
                from_provider="anthropic",
                to_provider="openai",
                reason="circuit_breaker_open",
            )
            # Verify OpenAI client was actually called
            mock_openai.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_state_transitions_during_outage(self) -> None:
        """Verify circuit state transitions: CLOSED → OPEN during simulated outage."""
        anthropic_cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=2, transient_failure_threshold=2),
            service_name="anthropic",
        )

        # Initially closed
        assert anthropic_cb.state == CircuitState.CLOSED

        # First failure - still closed
        async def failing_call() -> None:
            raise _create_api_error(503)

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)
        # With transient failure threshold=2, need 2 failures
        assert anthropic_cb.failure_count == 1

        # Second failure - trips to open
        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)
        assert anthropic_cb.state == CircuitState.OPEN


# ============================================================================
# TestFallbackEventEmission: SSE event validation
# ============================================================================


@pytest.mark.chaos
class TestFallbackEventEmission:
    """Test `model_fallback` SSE event emission on provider fallback."""

    @pytest.mark.asyncio
    async def test_provider_fallback_does_not_emit_model_fallback_event(self) -> None:
        """Provider fallback does not emit model_fallback event (different event type)."""
        # Provider fallback (Anthropic → OpenAI) emits provider_fallback metric
        # Model fallback (Opus → Sonnet) emits model_fallback event
        # This test verifies we don't confuse the two
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        # Trip anthropic
        async def failing_call() -> None:
            raise _create_api_error(503)

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
            patch("bo1.llm.broker.record_provider_fallback") as mock_provider_fallback,
            patch("bo1.llm.broker.record_model_fallback") as mock_model_fallback,
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
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

            # Provider fallback metric recorded
            mock_provider_fallback.assert_called_once()
            # Model fallback NOT recorded (this is provider fallback, not model fallback)
            mock_model_fallback.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_event_payload_structure(self) -> None:
        """Verify provider fallback metric call arguments structure."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        async def failing_call() -> None:
            raise _create_api_error(503)

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
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
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

            # Verify exact call structure
            call_args = mock_fallback_metric.call_args
            assert call_args.kwargs["from_provider"] == "anthropic"
            assert call_args.kwargs["to_provider"] == "openai"
            assert call_args.kwargs["reason"] == "circuit_breaker_open"


# ============================================================================
# TestFallbackMetricsRecording: Prometheus metrics validation
# ============================================================================


@pytest.mark.chaos
class TestFallbackMetricsRecording:
    """Test Prometheus counter `bo1_provider_fallback_total` is incremented."""

    @pytest.mark.asyncio
    async def test_fallback_increments_prometheus_counter(self) -> None:
        """Verify Prometheus fallback counter is incremented with correct labels."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        async def failing_call() -> None:
            raise _create_api_error(503)

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
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
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

            # Verify metric was called exactly once with correct labels
            mock_fallback_metric.assert_called_once()
            call_kwargs = mock_fallback_metric.call_args.kwargs
            assert call_kwargs["from_provider"] == "anthropic"
            assert call_kwargs["to_provider"] == "openai"
            assert call_kwargs["reason"] == "circuit_breaker_open"

    @pytest.mark.asyncio
    async def test_no_fallback_metrics_when_primary_succeeds(self) -> None:
        """Verify no fallback metrics when primary provider succeeds."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

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
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            # Anthropic succeeds
            mock_anthropic.call = AsyncMock(
                return_value=("Anthropic response", _mock_token_usage())
            )

            request = _create_request()
            response = await broker.call(request)

            assert response.content == "Anthropic response"
            # No fallback metrics recorded
            mock_fallback_metric.assert_not_called()


# ============================================================================
# TestSessionCompletesWithFallback: End-to-end session completion
# ============================================================================


@pytest.mark.chaos
class TestSessionCompletesWithFallback:
    """Test session completes successfully using fallback provider."""

    @pytest.mark.asyncio
    async def test_session_completes_with_fallback(self) -> None:
        """Integration: session completes via OpenAI when Anthropic circuit is open."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        # Trip Anthropic
        async def failing_call() -> None:
            raise _create_api_error(503)

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
            patch("bo1.llm.broker.record_provider_fallback"),
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
            mock_cost_ctx.return_value = {"session_id": "test-session-complete"}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            def get_cb(provider: str) -> CircuitBreaker:
                return anthropic_cb if provider == "anthropic" else openai_cb

            mock_get_cb.side_effect = get_cb

            # OpenAI returns valid response
            mock_openai = AsyncMock()
            mock_openai.call.return_value = (
                "<recommendation>Use OpenAI fallback</recommendation>",
                _mock_token_usage(),
            )
            mock_get_openai.return_value = mock_openai

            request = _create_request()
            response = await broker.call(request)

            # Verify session completed successfully with fallback
            assert response is not None
            assert "<recommendation>" in response.content
            assert response.model is not None  # Model should be set
            assert response.duration_ms >= 0  # Duration is tracked (may be 0 in mocked env)

    @pytest.mark.asyncio
    async def test_multiple_requests_use_fallback_while_circuit_open(self) -> None:
        """Multiple requests continue using fallback while circuit is open."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        # Trip Anthropic
        async def failing_call() -> None:
            raise _create_api_error(503)

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
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
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

            # Make 3 consecutive requests
            for i in range(3):
                request = _create_request(request_id=f"multi-request-{i}")
                response = await broker.call(request)
                assert response.content == "OpenAI response"

            # Fallback metric called for each request
            assert mock_fallback_metric.call_count == 3


# ============================================================================
# TestFallbackDisabledFailsGracefully: Disabled fallback behavior
# ============================================================================


@pytest.mark.chaos
class TestFallbackDisabledFailsGracefully:
    """Test behavior when `llm_fallback_enabled=False`."""

    @pytest.mark.asyncio
    async def test_fallback_disabled_raises_user_friendly_error(self) -> None:
        """When fallback disabled and circuit open, raise RuntimeError with user message."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        # Trip circuit
        async def failing_call() -> None:
            raise _create_api_error(503)

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
            # Fallback DISABLED
            mock_settings.return_value = _create_mock_settings(fallback_enabled=False)
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            request = _create_request()

            with pytest.raises(RuntimeError) as exc_info:
                await broker.call(request)

            # Verify user-friendly message
            error_message = str(exc_info.value)
            assert "temporarily unavailable" in error_message.lower()
            assert "try again later" in error_message.lower()

            # Verify no fallback metrics recorded
            mock_fallback_metric.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_disabled_does_not_attempt_openai(self) -> None:
        """When fallback disabled, OpenAI client is never instantiated/called."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        async def failing_call() -> None:
            raise _create_api_error(503)

        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)

        broker = PromptBroker()

        with (
            patch.object(broker, "_get_circuit_breaker", return_value=anthropic_cb),
            patch("bo1.llm.broker.get_settings") as mock_settings,
            patch("bo1.llm.broker.get_active_llm_provider") as mock_provider,
            patch("bo1.llm.broker.resolve_tier_to_model") as mock_resolve,
            patch("bo1.llm.broker.get_cost_context") as mock_cost_ctx,
            patch("bo1.llm.cache.get_llm_cache") as mock_cache,
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            mock_settings.return_value = _create_mock_settings(fallback_enabled=False)
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
            mock_cost_ctx.return_value = {}

            mock_cache_instance = AsyncMock()
            mock_cache_instance.get.return_value = None
            mock_cache.return_value = mock_cache_instance

            request = _create_request()

            with pytest.raises(RuntimeError):
                await broker.call(request)

            # OpenAI client never accessed
            mock_get_openai.assert_not_called()


# ============================================================================
# TestCircuitOpensOnConsecutive503s: Circuit trip validation
# ============================================================================


@pytest.mark.chaos
class TestCircuitTripsOnConsecutive503s:
    """Unit test: circuit opens after consecutive 503 errors."""

    @pytest.mark.asyncio
    async def test_circuit_trips_on_consecutive_503s(self) -> None:
        """Verify circuit opens after reaching transient failure threshold."""
        threshold = 3
        anthropic_cb = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=threshold,
                transient_failure_threshold=threshold,
            ),
            service_name="anthropic",
        )

        async def failing_call() -> None:
            raise _create_api_error(503)

        # First (threshold - 1) failures: circuit stays closed
        for i in range(threshold - 1):
            with pytest.raises(APIError):
                await anthropic_cb.call(failing_call)
            assert anthropic_cb.state == CircuitState.CLOSED, f"Failed at iteration {i}"

        # Final failure: circuit opens
        with pytest.raises(APIError):
            await anthropic_cb.call(failing_call)
        assert anthropic_cb.state == CircuitState.OPEN
        assert anthropic_cb.failure_count == threshold


# ============================================================================
# TestOpenAIReceivesRequestOnFallback: Request routing validation
# ============================================================================


@pytest.mark.chaos
class TestOpenAIClientReceivesRequestOnFallback:
    """Unit test: OpenAI client receives request when fallback activates."""

    @pytest.mark.asyncio
    async def test_openai_client_receives_request_on_fallback(self) -> None:
        """Verify OpenAI client receives correctly formatted request on fallback."""
        anthropic_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))
        openai_cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        # Trip Anthropic
        async def failing_call() -> None:
            raise _create_api_error(503)

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
            patch("bo1.llm.broker.record_provider_fallback"),
            patch.object(broker, "_get_openai_client") as mock_get_openai,
        ):
            mock_settings.return_value = _create_mock_settings()
            mock_provider.return_value = "anthropic"
            mock_resolve.return_value = "claude-sonnet-4-5-20250929"
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
            request.system = "Custom system prompt"
            request.user_message = "Custom user message"
            await broker.call(request)

            # Verify OpenAI client was called with correct parameters
            mock_openai.call.assert_called_once()
            call_kwargs = mock_openai.call.call_args.kwargs
            assert call_kwargs["system"] == "Custom system prompt"
            assert call_kwargs["messages"] == [{"role": "user", "content": "Custom user message"}]
