"""Tests for circuit breaker registry and per-service instances.

Validates:
- Per-service circuit breaker isolation
- Service-specific configurations
- Sync call methods for non-async code
- Registry management functions
"""

import pytest

from bo1.llm.circuit_breaker import (
    SERVICE_CONFIGS,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    _circuit_breakers,
    get_all_circuit_breaker_status,
    get_service_circuit_breaker,
    reset_service_circuit_breaker,
)


@pytest.fixture(autouse=True)
def reset_breakers():
    """Reset circuit breakers before each test."""
    _circuit_breakers.clear()
    yield
    _circuit_breakers.clear()


class TestServiceCircuitBreaker:
    """Test per-service circuit breaker registry."""

    def test_get_circuit_breaker_returns_same_instance(self):
        """Same service returns same instance."""
        breaker1 = get_service_circuit_breaker("voyage")
        breaker2 = get_service_circuit_breaker("voyage")

        assert breaker1 is breaker2

    def test_get_circuit_breaker_per_service_isolation(self):
        """Different services get different instances."""
        voyage_breaker = get_service_circuit_breaker("voyage")
        brave_breaker = get_service_circuit_breaker("brave")
        anthropic_breaker = get_service_circuit_breaker("anthropic")

        assert voyage_breaker is not brave_breaker
        assert voyage_breaker is not anthropic_breaker
        assert brave_breaker is not anthropic_breaker

    def test_service_configs_applied(self):
        """Service-specific configs are applied."""
        voyage_breaker = get_service_circuit_breaker("voyage")
        brave_breaker = get_service_circuit_breaker("brave")

        # Voyage has higher failure threshold (8 vs 5)
        assert (
            voyage_breaker.config.failure_threshold
            == SERVICE_CONFIGS["voyage"]["failure_threshold"]
        )
        assert (
            brave_breaker.config.failure_threshold == SERVICE_CONFIGS["brave"]["failure_threshold"]
        )

        # Voyage has shorter recovery timeout (30 vs 45)
        assert (
            voyage_breaker.config.recovery_timeout == SERVICE_CONFIGS["voyage"]["recovery_timeout"]
        )
        assert brave_breaker.config.recovery_timeout == SERVICE_CONFIGS["brave"]["recovery_timeout"]

    def test_unknown_service_uses_anthropic_defaults(self):
        """Unknown services use Anthropic config as default."""
        unknown_breaker = get_service_circuit_breaker("unknown_service")
        anthropic_breaker = get_service_circuit_breaker("anthropic")

        assert (
            unknown_breaker.config.failure_threshold == anthropic_breaker.config.failure_threshold
        )
        assert unknown_breaker.config.recovery_timeout == anthropic_breaker.config.recovery_timeout

    def test_get_all_circuit_breaker_status(self):
        """Get status of all initialized breakers."""
        # Initialize some breakers
        get_service_circuit_breaker("voyage")
        get_service_circuit_breaker("brave")

        statuses = get_all_circuit_breaker_status()

        assert "voyage" in statuses
        assert "brave" in statuses
        assert statuses["voyage"]["state"] == "closed"
        assert statuses["brave"]["state"] == "closed"

    def test_reset_service_circuit_breaker(self):
        """Reset removes breaker from registry."""
        breaker1 = get_service_circuit_breaker("voyage")
        reset_service_circuit_breaker("voyage")
        breaker2 = get_service_circuit_breaker("voyage")

        # Should be a new instance
        assert breaker1 is not breaker2


class TestSyncCallMethod:
    """Test synchronous circuit breaker call method."""

    def test_call_sync_success(self):
        """Sync call succeeds when circuit closed."""
        breaker = CircuitBreaker()

        def success_func():
            return "result"

        result = breaker.call_sync(success_func)

        assert result == "result"
        assert breaker.failure_count == 0

    def test_call_sync_failure_records(self):
        """Sync call records failures."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        def failing_func():
            raise ValueError("test error")

        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call_sync(failing_func)

        assert breaker.failure_count == 2
        assert breaker.state == CircuitState.CLOSED

    def test_call_sync_opens_circuit_after_threshold(self):
        """Circuit opens after failure threshold."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=3))

        def failing_func():
            raise ValueError("test error")

        for _ in range(3):
            with pytest.raises(ValueError):
                breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

    def test_call_sync_fast_fails_when_open(self):
        """Fast-fails when circuit is open."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        def failing_func():
            raise ValueError("test error")

        # Trip the circuit
        with pytest.raises(ValueError):
            breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Next call should fast-fail
        def should_not_run():
            raise AssertionError("Should not reach here")

        with pytest.raises(CircuitBreakerOpenError):
            breaker.call_sync(should_not_run)

    def test_call_sync_success_resets_failure_count(self):
        """Success in closed state resets failure count."""
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=5))

        def failing_func():
            raise ValueError("test error")

        def success_func():
            return "ok"

        # Accumulate some failures
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call_sync(failing_func)

        assert breaker.failure_count == 2

        # Success resets count
        breaker.call_sync(success_func)
        assert breaker.failure_count == 0


class TestCircuitBreakerStateTransitions:
    """Test circuit state transitions."""

    def test_half_open_to_closed_on_success(self):
        """Circuit closes after success_threshold successes in half-open."""
        import time

        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0,  # Immediate recovery for testing
                success_threshold=2,
            )
        )

        def failing_func():
            raise ValueError("test error")

        def success_func():
            return "ok"

        # Trip the circuit
        with pytest.raises(ValueError):
            breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait and trigger recovery check (recovery_timeout=0)
        time.sleep(0.01)

        # First success moves to half-open
        result = breaker.call_sync(success_func)
        assert result == "ok"
        # After first success in half-open, success_count=1

        # Second success should close circuit
        result = breaker.call_sync(success_func)
        assert result == "ok"
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self):
        """Circuit re-opens on failure in half-open state."""
        import time

        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=0,
                success_threshold=2,
            )
        )

        def failing_func():
            raise ValueError("test error")

        # Trip the circuit
        with pytest.raises(ValueError):
            breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery check
        time.sleep(0.01)
        breaker._check_recovery_sync()
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure in half-open re-opens circuit
        with pytest.raises(ValueError):
            breaker.call_sync(failing_func)

        assert breaker.state == CircuitState.OPEN


class TestVoyageCircuitBreakerIntegration:
    """Test Voyage AI circuit breaker integration."""

    def test_voyage_breaker_has_correct_config(self):
        """Voyage breaker uses specific config."""
        breaker = get_service_circuit_breaker("voyage")

        assert breaker.config.failure_threshold == 8
        assert breaker.config.recovery_timeout == 30
        assert breaker.config.success_threshold == 2

    def test_voyage_breaker_isolated_from_others(self):
        """Voyage failures don't affect other services."""
        voyage_breaker = get_service_circuit_breaker("voyage")
        brave_breaker = get_service_circuit_breaker("brave")

        # Record failures on voyage
        for _ in range(10):
            voyage_breaker._record_failure_sync(ValueError("test"))

        assert voyage_breaker.state == CircuitState.OPEN
        assert brave_breaker.state == CircuitState.CLOSED


class TestBraveCircuitBreakerIntegration:
    """Test Brave Search circuit breaker integration."""

    def test_brave_breaker_has_correct_config(self):
        """Brave breaker uses specific config."""
        breaker = get_service_circuit_breaker("brave")

        assert breaker.config.failure_threshold == 5
        assert breaker.config.recovery_timeout == 45
        assert breaker.config.success_threshold == 2

    def test_brave_breaker_opens_on_failures(self):
        """Brave circuit opens after threshold failures."""
        breaker = get_service_circuit_breaker("brave")

        for _ in range(5):
            breaker._record_failure_sync(Exception("Connection refused"))

        assert breaker.state == CircuitState.OPEN


class TestTavilyCircuitBreakerIntegration:
    """Test Tavily AI circuit breaker integration."""

    def test_tavily_breaker_has_correct_config(self):
        """Tavily breaker uses specific config."""
        breaker = get_service_circuit_breaker("tavily")

        assert breaker.config.failure_threshold == 5
        assert breaker.config.recovery_timeout == 45
        assert breaker.config.success_threshold == 2

    def test_tavily_breaker_opens_on_failures(self):
        """Tavily circuit opens after threshold failures."""
        breaker = get_service_circuit_breaker("tavily")

        for _ in range(5):
            breaker._record_failure_sync(Exception("Connection refused"))

        assert breaker.state == CircuitState.OPEN

    def test_tavily_breaker_isolated_from_brave(self):
        """Tavily failures don't affect Brave service."""
        tavily_breaker = get_service_circuit_breaker("tavily")
        brave_breaker = get_service_circuit_breaker("brave")

        # Record failures on tavily
        for _ in range(5):
            tavily_breaker._record_failure_sync(ValueError("test"))

        assert tavily_breaker.state == CircuitState.OPEN
        assert brave_breaker.state == CircuitState.CLOSED
