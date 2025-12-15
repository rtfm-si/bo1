"""Tests for circuit breaker status and metrics."""

from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_service_circuit_breaker,
    reset_circuit_breaker,
)


class TestCircuitBreakerStatusClosed:
    """Test circuit breaker status when closed."""

    def test_status_closed_by_default(self) -> None:
        """Initial state is closed."""
        breaker = CircuitBreaker(service_name="test_service")

        status = breaker.get_status()
        assert status["state"] == "closed"
        assert status["is_open"] is False
        assert status["is_half_open"] is False
        assert status["failure_count"] == 0

    def test_status_includes_service_name(self) -> None:
        """Circuit breaker tracks its service name."""
        breaker = CircuitBreaker(service_name="anthropic")
        assert breaker.service_name == "anthropic"


class TestCircuitBreakerStatusTransitions:
    """Test circuit breaker status after state transitions."""

    def test_status_after_failures(self) -> None:
        """State transitions to open after failures."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config, service_name="test")

        # Record failures
        for _ in range(3):
            breaker._record_failure_sync(Exception("test error"))

        status = breaker.get_status()
        assert status["state"] == "open"
        assert status["is_open"] is True
        assert status["failure_count"] == 3

    def test_status_reset_on_success(self) -> None:
        """Circuit closes after successes in half-open state."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0, success_threshold=1)
        breaker = CircuitBreaker(config, service_name="test")

        # Open the circuit
        breaker._record_failure_sync(Exception("error"))
        breaker._record_failure_sync(Exception("error"))
        assert breaker.state == CircuitState.OPEN

        # Transition to half-open
        breaker._check_recovery_sync()
        assert breaker.state == CircuitState.HALF_OPEN

        # Record success to close
        breaker._record_success_sync()
        status = breaker.get_status()
        assert status["state"] == "closed"
        assert status["failure_count"] == 0


class TestServiceCircuitBreakerCreation:
    """Test service-specific circuit breaker creation."""

    def setup_method(self) -> None:
        """Reset circuit breakers before each test."""
        reset_circuit_breaker()

    def test_service_breaker_has_service_name(self) -> None:
        """Service circuit breakers have correct service names."""
        breaker = get_service_circuit_breaker("voyage")
        assert breaker.service_name == "voyage"

    def test_anthropic_breaker_has_service_name(self) -> None:
        """Anthropic circuit breaker has correct service name."""
        breaker = get_service_circuit_breaker("anthropic")
        assert breaker.service_name == "anthropic"


class TestCircuitBreakerUptimeTracking:
    """Test uptime tracking in status."""

    def test_status_uptime_seconds(self) -> None:
        """Status includes uptime since last state change."""
        breaker = CircuitBreaker(service_name="test")

        status = breaker.get_status()
        assert "uptime_seconds" in status
        assert status["uptime_seconds"] >= 0
