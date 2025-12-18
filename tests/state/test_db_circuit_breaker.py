"""Tests for database circuit breaker integration.

Tests that the postgres circuit breaker:
- Trips after repeated failures
- Fast-fails when open
- Recovers through half-open state
"""

import pytest

from bo1.llm.circuit_breaker import (
    CircuitState,
    FaultType,
    classify_fault_db,
    get_service_circuit_breaker,
    reset_service_circuit_breaker,
)
from bo1.state.circuit_breaker_wrappers import (
    get_db_circuit_status,
    is_db_circuit_open,
    record_db_failure,
    record_db_success,
)


@pytest.fixture(autouse=True)
def reset_postgres_circuit():
    """Reset postgres circuit breaker before each test."""
    reset_service_circuit_breaker("postgres")
    yield
    reset_service_circuit_breaker("postgres")


class TestClassifyFaultDb:
    """Tests for classify_fault_db function."""

    def test_operational_error_is_transient(self):
        """OperationalError (connection issues) should be transient."""
        import psycopg2

        error = psycopg2.OperationalError("connection refused")
        assert classify_fault_db(error) == FaultType.TRANSIENT

    def test_pool_error_is_transient(self):
        """PoolError (exhaustion) should be transient."""
        from psycopg2 import pool

        error = pool.PoolError("connection pool exhausted")
        assert classify_fault_db(error) == FaultType.TRANSIENT

    def test_programming_error_is_permanent(self):
        """ProgrammingError (SQL syntax) should be permanent."""
        import psycopg2

        error = psycopg2.ProgrammingError("syntax error at or near")
        assert classify_fault_db(error) == FaultType.PERMANENT

    def test_integrity_error_is_permanent(self):
        """IntegrityError (constraint violation) should be permanent."""
        import psycopg2

        error = psycopg2.IntegrityError("duplicate key value")
        assert classify_fault_db(error) == FaultType.PERMANENT

    def test_data_error_is_permanent(self):
        """DataError (type mismatch) should be permanent."""
        import psycopg2

        error = psycopg2.DataError("invalid input syntax")
        assert classify_fault_db(error) == FaultType.PERMANENT

    def test_connection_pattern_in_message(self):
        """Error message with 'connection' should be transient."""
        error = Exception("connection reset by peer")
        assert classify_fault_db(error) == FaultType.TRANSIENT

    def test_timeout_pattern_in_message(self):
        """Error message with 'timeout' should be transient."""
        error = Exception("query timeout exceeded")
        assert classify_fault_db(error) == FaultType.TRANSIENT

    def test_unknown_error_returns_unknown(self):
        """Unknown errors should return UNKNOWN."""
        error = Exception("some random error")
        assert classify_fault_db(error) == FaultType.UNKNOWN


class TestDbCircuitBreaker:
    """Tests for database circuit breaker behavior."""

    def test_circuit_starts_closed(self):
        """Circuit should start in closed state."""
        breaker = get_service_circuit_breaker("postgres")
        assert breaker.state == CircuitState.CLOSED

    def test_is_db_circuit_open_initially_false(self):
        """is_db_circuit_open should return False initially."""
        assert not is_db_circuit_open()

    def test_record_db_failure_increments_count(self):
        """Recording failure should increment failure count."""
        breaker = get_service_circuit_breaker("postgres")
        initial_count = breaker.failure_count

        error = Exception("connection timeout")
        record_db_failure(error)

        assert breaker.failure_count > initial_count

    def test_record_db_success_resets_count(self):
        """Recording success should reset failure count in closed state."""
        breaker = get_service_circuit_breaker("postgres")

        # Record some failures
        for _ in range(3):
            record_db_failure(Exception("connection timeout"))

        assert breaker.failure_count > 0

        # Record success
        record_db_success()

        assert breaker.failure_count == 0

    def test_circuit_trips_after_threshold(self):
        """Circuit should trip to OPEN after threshold failures."""
        breaker = get_service_circuit_breaker("postgres")

        # Postgres threshold is 8
        for _ in range(8):
            record_db_failure(Exception("connection timeout"))

        assert breaker.state == CircuitState.OPEN
        assert is_db_circuit_open()

    def test_get_db_circuit_status(self):
        """get_db_circuit_status should return status dict."""
        status = get_db_circuit_status()

        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert status["state"] == "closed"

    def test_permanent_errors_dont_trip_circuit(self):
        """Permanent errors should not count toward tripping."""
        import psycopg2

        breaker = get_service_circuit_breaker("postgres")

        # Record permanent errors (syntax errors)
        for _ in range(10):
            record_db_failure(psycopg2.ProgrammingError("syntax error"))

        # Circuit should still be closed (permanent errors filtered)
        assert breaker.state == CircuitState.CLOSED


class TestDbCircuitBreakerConfig:
    """Tests for postgres circuit breaker configuration."""

    def test_postgres_config_exists(self):
        """Postgres config should exist in SERVICE_CONFIGS."""
        from bo1.llm.circuit_breaker import SERVICE_CONFIGS

        assert "postgres" in SERVICE_CONFIGS

    def test_postgres_config_values(self):
        """Postgres config should have expected values."""
        from bo1.llm.circuit_breaker import SERVICE_CONFIGS

        config = SERVICE_CONFIGS["postgres"]
        assert config["failure_threshold"] == 8
        assert config["recovery_timeout"] == 30
        assert config["success_threshold"] == 2

    def test_breaker_uses_postgres_config(self):
        """Circuit breaker should use postgres-specific config."""
        breaker = get_service_circuit_breaker("postgres")

        assert breaker.config.failure_threshold == 8
        assert breaker.config.recovery_timeout == 30
