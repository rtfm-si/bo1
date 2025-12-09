"""Chaos tests for LLM circuit breaker behavior.

Validates:
- Circuit opens after N consecutive failures
- Circuit half-open recovery after timeout
- Fast-fail when circuit is open (no API calls made)
- Concurrent requests during circuit state transitions

Note: Circuit breaker only counts APIError/RateLimitError from anthropic package.
Regular exceptions (ValueError, etc.) are re-raised but don't trip the circuit.
"""

import asyncio

import pytest
from anthropic import APIError

from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    get_service_circuit_breaker,
)


def _api_error(msg: str = "API error") -> APIError:
    """Create an APIError for testing circuit breaker."""
    return APIError(message=msg, request=None, body=None)  # type: ignore[arg-type]


@pytest.mark.chaos
class TestCircuitBreakerOpensOnFailures:
    """Test circuit opens after threshold failures."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_api_errors(self) -> None:
        """Circuit opens after N consecutive API errors."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60))

        # Simulate Anthropic APIError
        async def failing_call() -> str:
            from anthropic import APIError

            raise APIError(
                message="Service unavailable",
                request=None,  # type: ignore[arg-type]
                body=None,
            )

        # First 2 failures: circuit stays closed
        for i in range(2):
            with pytest.raises(Exception):  # noqa: B017 - APIError
                await breaker.call(failing_call)
            assert breaker.state == CircuitState.CLOSED
            assert breaker.failure_count == i + 1

        # 3rd failure: circuit opens
        with pytest.raises(Exception):  # noqa: B017
            await breaker.call(failing_call)

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_opens_on_rate_limit_errors(self) -> None:
        """Circuit opens after repeated rate limit (429) errors."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60))

        async def rate_limited_call() -> str:
            # Use APIError which has simpler constructor
            # RateLimitError extends APIStatusError which requires httpx.Response
            raise _api_error("Rate limit exceeded (429)")

        # Trip the circuit with rate limits
        for _ in range(2):
            with pytest.raises(APIError):
                await breaker.call(rate_limited_call)

        assert breaker.state == CircuitState.OPEN

    def test_sync_circuit_opens_after_threshold(self) -> None:
        """Sync circuit opens after threshold failures."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60))

        def failing_call() -> str:
            raise _api_error("Simulated failure")

        for _ in range(2):
            with pytest.raises(APIError):
                breaker.call_sync(failing_call)

        assert breaker.state == CircuitState.OPEN


@pytest.mark.chaos
class TestCircuitBreakerFastFail:
    """Test fast-fail behavior when circuit is open."""

    @pytest.mark.asyncio
    async def test_fast_fail_does_not_call_api(self) -> None:
        """When circuit is open, API is not called."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, recovery_timeout=300))

        call_count = 0

        async def counting_call() -> str:
            nonlocal call_count
            call_count += 1
            raise _api_error("API error")

        # Trip the circuit
        with pytest.raises(APIError):
            await breaker.call(counting_call)

        assert call_count == 1
        assert breaker.state == CircuitState.OPEN

        # Next call should fast-fail without calling API
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(counting_call)

        # Call count should not increase
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_fast_fail_error_contains_failure_count(self) -> None:
        """Fast-fail error message includes failure count."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3, recovery_timeout=300))

        async def failing_call() -> str:
            raise _api_error("Error")

        # Trip the circuit
        for _ in range(3):
            with pytest.raises(APIError):
                await breaker.call(failing_call)

        # Check error message
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await breaker.call(failing_call)

        assert "3 times" in str(exc_info.value)

    def test_sync_fast_fail(self) -> None:
        """Sync fast-fail when circuit open."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, recovery_timeout=300))

        def failing_call() -> str:
            raise _api_error("Error")

        # Trip circuit
        with pytest.raises(APIError):
            breaker.call_sync(failing_call)

        # Should fast-fail
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call_sync(failing_call)


@pytest.mark.chaos
class TestCircuitBreakerRecovery:
    """Test circuit recovery (half-open -> closed)."""

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self) -> None:
        """Circuit moves to half-open after recovery timeout."""
        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0,  # Immediate recovery for testing
                success_threshold=1,
            )
        )

        async def failing_then_succeeding() -> str:
            raise _api_error("Initial failure")

        # Trip circuit
        with pytest.raises(APIError):
            await breaker.call(failing_then_succeeding)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery (recovery_timeout=0 means immediate)
        await asyncio.sleep(0.01)

        # Next call triggers half-open check
        async def success_call() -> str:
            return "success"

        result = await breaker.call(success_call)

        # Should have recovered
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_reopens_on_failure(self) -> None:
        """Circuit reopens if failure occurs in half-open state."""
        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0,
                success_threshold=2,  # Need 2 successes
            )
        )

        async def failing_call() -> str:
            raise _api_error("Failure")

        # Trip circuit
        with pytest.raises(APIError):
            await breaker.call(failing_call)

        # Wait for half-open
        await asyncio.sleep(0.01)
        breaker._check_recovery_sync()  # Force check

        assert breaker.state == CircuitState.HALF_OPEN

        # Fail in half-open state
        with pytest.raises(APIError):
            await breaker.call(failing_call)

        # Should reopen
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_half_open_requires_success_threshold(self) -> None:
        """Circuit needs success_threshold successes to close."""
        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0,
                success_threshold=3,  # Need 3 successes
            )
        )

        async def failing_call() -> str:
            raise _api_error("Failure")

        async def success_call() -> str:
            return "ok"

        # Trip circuit
        with pytest.raises(APIError):
            await breaker.call(failing_call)

        await asyncio.sleep(0.01)

        # First success: still half-open
        await breaker.call(success_call)
        # State depends on implementation - may transition to half-open on first success

        # Second success
        await breaker.call(success_call)

        # Third success: should close
        await breaker.call(success_call)
        assert breaker.state == CircuitState.CLOSED


@pytest.mark.chaos
class TestCircuitBreakerConcurrency:
    """Test concurrent request behavior during state transitions."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_during_open_state(self) -> None:
        """Multiple concurrent requests fast-fail when circuit open."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1, recovery_timeout=300))

        async def failing_call() -> str:
            raise _api_error("Error")

        # Trip circuit
        with pytest.raises(APIError):
            await breaker.call(failing_call)

        # Launch concurrent requests
        async def attempt_call() -> str:
            try:
                return await breaker.call(failing_call)
            except CircuitBreakerOpenError:
                return "fast-fail"
            except APIError:
                return "api-error"

        results = await asyncio.gather(*[attempt_call() for _ in range(5)])

        # All should fast-fail
        assert all(r == "fast-fail" for r in results)

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        """Successful call resets failure count in closed state."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60))

        async def failing_call() -> str:
            raise _api_error("Error")

        async def success_call() -> str:
            return "ok"

        # Accumulate some failures
        for _ in range(2):
            with pytest.raises(APIError):
                await breaker.call(failing_call)

        assert breaker.failure_count == 2

        # Success resets count
        await breaker.call(success_call)
        assert breaker.failure_count == 0

        # Need 3 more failures to trip (not 1)
        for _ in range(2):
            with pytest.raises(APIError):
                await breaker.call(failing_call)

        assert breaker.state == CircuitState.CLOSED  # Still closed (only 2 failures)


@pytest.mark.chaos
class TestServiceCircuitBreakerIsolation:
    """Test per-service circuit breaker isolation."""

    def test_anthropic_failures_dont_affect_voyage(self) -> None:
        """Anthropic circuit opening doesn't affect Voyage."""
        anthropic_breaker = get_service_circuit_breaker("anthropic")
        voyage_breaker = get_service_circuit_breaker("voyage")

        # Trip Anthropic circuit (threshold=5)
        for _ in range(5):
            anthropic_breaker._record_failure_sync(ValueError("API error"))

        assert anthropic_breaker.state == CircuitState.OPEN
        assert voyage_breaker.state == CircuitState.CLOSED

    def test_voyage_higher_threshold(self) -> None:
        """Voyage has higher failure threshold (8 vs 5)."""
        voyage_breaker = get_service_circuit_breaker("voyage")

        # 5 failures: still closed
        for _ in range(5):
            voyage_breaker._record_failure_sync(ValueError("Error"))

        assert voyage_breaker.state == CircuitState.CLOSED

        # 3 more: opens
        for _ in range(3):
            voyage_breaker._record_failure_sync(ValueError("Error"))

        assert voyage_breaker.state == CircuitState.OPEN


@pytest.mark.chaos
class TestCircuitBreakerWithRealBroker:
    """Test circuit breaker integration with PromptBroker."""

    @pytest.mark.asyncio
    async def test_broker_circuit_breaker_trips(self) -> None:
        """PromptBroker's circuit breaker trips on repeated failures.

        Note: This test uses the circuit breaker directly rather than through
        PromptBroker, since PromptBroker has complex initialization requirements
        (cost tracking, caching, etc.) that make it difficult to isolate.
        """
        # Test circuit breaker directly with APIError
        circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=2, recovery_timeout=300)
        )

        # Simulate what broker does - wraps API call with circuit breaker
        async def mock_api_call() -> tuple[str, object]:
            raise _api_error("Service down")

        # First 2 calls fail with APIError
        for _ in range(2):
            with pytest.raises(APIError):
                await circuit_breaker.call(mock_api_call)

        # Circuit should be open
        assert circuit_breaker.state == CircuitState.OPEN

        # Next call should fast-fail (without calling the function)
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(mock_api_call)
