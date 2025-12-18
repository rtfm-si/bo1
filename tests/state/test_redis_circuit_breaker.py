"""Tests for Redis circuit breaker integration.

Tests that the redis circuit breaker:
- Trips after repeated failures
- Fast-fails when open
- Recovers through half-open state
"""

import pytest

from bo1.llm.circuit_breaker import (
    CircuitState,
    FaultType,
    classify_fault_redis,
    get_service_circuit_breaker,
    reset_service_circuit_breaker,
)
from bo1.state.circuit_breaker_wrappers import (
    get_redis_circuit_status,
    is_redis_circuit_open,
    record_redis_failure,
    record_redis_success,
)


@pytest.fixture(autouse=True)
def reset_redis_circuit():
    """Reset redis circuit breaker before each test."""
    reset_service_circuit_breaker("redis")
    yield
    reset_service_circuit_breaker("redis")


class TestClassifyFaultRedis:
    """Tests for classify_fault_redis function."""

    def test_connection_error_is_transient(self):
        """ConnectionError should be transient."""
        import redis

        error = redis.ConnectionError("Connection refused")
        assert classify_fault_redis(error) == FaultType.TRANSIENT

    def test_timeout_error_is_transient(self):
        """TimeoutError should be transient."""
        import redis

        error = redis.TimeoutError("Connection timed out")
        assert classify_fault_redis(error) == FaultType.TRANSIENT

    def test_auth_error_is_permanent(self):
        """AuthenticationError should be permanent."""
        import redis

        error = redis.AuthenticationError("NOAUTH Authentication required")
        assert classify_fault_redis(error) == FaultType.PERMANENT

    def test_response_error_is_permanent(self):
        """ResponseError (WRONGTYPE, etc.) should be permanent."""
        import redis

        error = redis.ResponseError("WRONGTYPE Operation against a key holding the wrong kind")
        assert classify_fault_redis(error) == FaultType.PERMANENT

    def test_connection_pattern_in_message(self):
        """Error message with 'connection' should be transient."""
        error = Exception("connection refused")
        assert classify_fault_redis(error) == FaultType.TRANSIENT

    def test_timeout_pattern_in_message(self):
        """Error message with 'timeout' should be transient."""
        error = Exception("read timeout")
        assert classify_fault_redis(error) == FaultType.TRANSIENT

    def test_unknown_error_returns_unknown(self):
        """Unknown errors should return UNKNOWN."""
        error = Exception("some random error")
        assert classify_fault_redis(error) == FaultType.UNKNOWN


class TestRedisCircuitBreaker:
    """Tests for Redis circuit breaker behavior."""

    def test_circuit_starts_closed(self):
        """Circuit should start in closed state."""
        breaker = get_service_circuit_breaker("redis")
        assert breaker.state == CircuitState.CLOSED

    def test_is_redis_circuit_open_initially_false(self):
        """is_redis_circuit_open should return False initially."""
        assert not is_redis_circuit_open()

    def test_record_redis_failure_increments_count(self):
        """Recording failure should increment failure count."""
        breaker = get_service_circuit_breaker("redis")
        initial_count = breaker.failure_count

        error = Exception("connection timeout")
        record_redis_failure(error)

        assert breaker.failure_count > initial_count

    def test_record_redis_success_resets_count(self):
        """Recording success should reset failure count in closed state."""
        breaker = get_service_circuit_breaker("redis")

        # Record some failures
        for _ in range(3):
            record_redis_failure(Exception("connection timeout"))

        assert breaker.failure_count > 0

        # Record success
        record_redis_success()

        assert breaker.failure_count == 0

    def test_circuit_trips_after_threshold(self):
        """Circuit should trip to OPEN after threshold failures."""
        breaker = get_service_circuit_breaker("redis")

        # Redis threshold is 5
        for _ in range(5):
            record_redis_failure(Exception("connection timeout"))

        assert breaker.state == CircuitState.OPEN
        assert is_redis_circuit_open()

    def test_get_redis_circuit_status(self):
        """get_redis_circuit_status should return status dict."""
        status = get_redis_circuit_status()

        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert status["state"] == "closed"

    def test_permanent_errors_dont_trip_circuit(self):
        """Permanent errors should not count toward tripping."""
        import redis

        breaker = get_service_circuit_breaker("redis")

        # Record permanent errors (auth errors)
        for _ in range(10):
            record_redis_failure(redis.AuthenticationError("NOAUTH"))

        # Circuit should still be closed (permanent errors filtered)
        assert breaker.state == CircuitState.CLOSED


class TestRedisCircuitBreakerConfig:
    """Tests for redis circuit breaker configuration."""

    def test_redis_config_exists(self):
        """Redis config should exist in SERVICE_CONFIGS."""
        from bo1.llm.circuit_breaker import SERVICE_CONFIGS

        assert "redis" in SERVICE_CONFIGS

    def test_redis_config_values(self):
        """Redis config should have expected values."""
        from bo1.llm.circuit_breaker import SERVICE_CONFIGS

        config = SERVICE_CONFIGS["redis"]
        assert config["failure_threshold"] == 5
        assert config["recovery_timeout"] == 15
        assert config["success_threshold"] == 2

    def test_breaker_uses_redis_config(self):
        """Circuit breaker should use redis-specific config."""
        breaker = get_service_circuit_breaker("redis")

        assert breaker.config.failure_threshold == 5
        assert breaker.config.recovery_timeout == 15


class TestRedisCircuitBreakerRecovery:
    """Tests for Redis circuit breaker recovery behavior."""

    def test_half_open_after_recovery_timeout(self):
        """Circuit should transition to half-open after recovery timeout."""
        import time

        breaker = get_service_circuit_breaker("redis")

        # Trip the circuit
        for _ in range(5):
            record_redis_failure(Exception("connection timeout"))

        assert breaker.state == CircuitState.OPEN

        # Manually set last_failure_time to past (simulate timeout passing)
        breaker.last_failure_time = time.time() - 20  # 20s ago (> 15s recovery)

        # Check recovery
        breaker._check_recovery_sync()

        assert breaker.state == CircuitState.HALF_OPEN

    def test_success_in_half_open_closes_circuit(self):
        """Success in half-open state should close circuit after threshold."""
        import time

        breaker = get_service_circuit_breaker("redis")

        # Trip the circuit
        for _ in range(5):
            record_redis_failure(Exception("connection timeout"))

        # Transition to half-open
        breaker.last_failure_time = time.time() - 20
        breaker._check_recovery_sync()
        assert breaker.state == CircuitState.HALF_OPEN

        # Record successes (threshold is 2)
        record_redis_success()
        record_redis_success()

        assert breaker.state == CircuitState.CLOSED
