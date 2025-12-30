"""Tests for circuit breaker fault classification (REL-P2).

Tests the FaultType enum, classify_fault() function, and fault-type-based
circuit breaker behavior.
"""

import pytest

from bo1.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    FaultType,
    classify_fault,
)


class TestClassifyFault:
    """Tests for classify_fault() function."""

    def test_rate_limit_error_is_transient(self) -> None:
        """RateLimitError should be classified as transient."""
        try:
            from anthropic import RateLimitError

            # Create mock RateLimitError
            error = RateLimitError.__new__(RateLimitError)
            error.status_code = 429
            error.message = "Rate limit exceeded"
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_timeout_error_is_transient(self) -> None:
        """APITimeoutError should be classified as transient."""
        try:
            from anthropic import APITimeoutError

            error = APITimeoutError.__new__(APITimeoutError)
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_connection_error_is_transient(self) -> None:
        """APIConnectionError should be classified as transient."""
        try:
            from anthropic import APIConnectionError

            error = APIConnectionError.__new__(APIConnectionError)
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_status_404_is_permanent(self) -> None:
        """404 Not Found should be classified as permanent."""
        try:
            from anthropic import NotFoundError

            error = NotFoundError.__new__(NotFoundError)
            error.status_code = 404
            result = classify_fault(error)
            assert result == FaultType.PERMANENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_status_400_is_permanent(self) -> None:
        """400 Bad Request should be classified as permanent."""
        try:
            from anthropic import BadRequestError

            error = BadRequestError.__new__(BadRequestError)
            error.status_code = 400
            result = classify_fault(error)
            assert result == FaultType.PERMANENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_status_401_is_permanent(self) -> None:
        """401 Unauthorized should be classified as permanent."""
        try:
            from anthropic import AuthenticationError

            error = AuthenticationError.__new__(AuthenticationError)
            error.status_code = 401
            result = classify_fault(error)
            assert result == FaultType.PERMANENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_status_500_is_transient(self) -> None:
        """500 Internal Server Error should be classified as transient."""
        try:
            from anthropic import InternalServerError

            error = InternalServerError.__new__(InternalServerError)
            error.status_code = 500
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_status_503_is_transient(self) -> None:
        """503 Service Unavailable should be classified as transient."""
        try:
            from anthropic import APIStatusError

            error = APIStatusError.__new__(APIStatusError)
            error.status_code = 503
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_unknown_exception_is_unknown(self) -> None:
        """Unknown exceptions should be classified as UNKNOWN."""
        error = ValueError("Some random error")
        result = classify_fault(error)
        assert result == FaultType.UNKNOWN

    def test_generic_status_code_attribute(self) -> None:
        """Generic exceptions with status_code attribute should be classified."""

        class GenericError(Exception):
            status_code = 500

        error = GenericError("Server error")
        result = classify_fault(error)
        assert result == FaultType.TRANSIENT

    def test_generic_permanent_status_code(self) -> None:
        """Generic exceptions with 4xx status_code should be permanent."""

        class GenericError(Exception):
            status_code = 403

        error = GenericError("Forbidden")
        result = classify_fault(error)
        assert result == FaultType.PERMANENT

    def test_timeout_in_message_is_transient(self) -> None:
        """Errors with 'timeout' in message should be transient."""
        error = Exception("Connection timeout occurred")
        result = classify_fault(error)
        assert result == FaultType.TRANSIENT

    def test_connection_in_message_is_transient(self) -> None:
        """Errors with 'connection' in message should be transient."""
        error = Exception("Connection refused")
        result = classify_fault(error)
        assert result == FaultType.TRANSIENT

    def test_httpx_timeout_is_transient(self) -> None:
        """httpx TimeoutException should be transient."""
        try:
            from httpx import TimeoutException

            error = TimeoutException("Request timed out")
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("httpx not installed")

    def test_httpx_connect_error_is_transient(self) -> None:
        """httpx ConnectError should be transient."""
        try:
            from httpx import ConnectError

            error = ConnectError("Failed to connect")
            result = classify_fault(error)
            assert result == FaultType.TRANSIENT
        except ImportError:
            pytest.skip("httpx not installed")


class TestCircuitBreakerFaultTracking:
    """Tests for circuit breaker fault classification behavior."""

    @pytest.fixture
    def config(self) -> CircuitBreakerConfig:
        """Create test config with low thresholds."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=10,
            success_threshold=1,
            transient_failure_threshold=3,
            permanent_failure_threshold=2,
            transient_recovery_timeout=10,
            permanent_recovery_timeout=60,
        )

    @pytest.fixture
    def breaker(self, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create test circuit breaker."""
        return CircuitBreaker(config, service_name="test")

    @pytest.mark.asyncio
    async def test_transient_fault_increments_transient_counter(
        self, breaker: CircuitBreaker
    ) -> None:
        """Transient faults should increment transient_failure_count."""
        try:
            from anthropic import RateLimitError

            error = RateLimitError.__new__(RateLimitError)
            error.status_code = 429
            error.message = "Rate limit"

            await breaker._record_failure(error)

            assert breaker.transient_failure_count == 1
            assert breaker.permanent_failure_count == 0
            assert breaker.failure_count == 1
        except ImportError:
            pytest.skip("anthropic not installed")

    @pytest.mark.asyncio
    async def test_permanent_fault_increments_permanent_counter(
        self, breaker: CircuitBreaker
    ) -> None:
        """Permanent faults should increment permanent_failure_count but not failure_count."""
        try:
            from anthropic import NotFoundError

            error = NotFoundError.__new__(NotFoundError)
            error.status_code = 404
            error.message = "Not found"

            await breaker._record_failure(error)

            assert breaker.permanent_failure_count == 1
            assert breaker.transient_failure_count == 0
            assert breaker.failure_count == 0  # Permanent faults don't trigger circuit
        except ImportError:
            pytest.skip("anthropic not installed")

    @pytest.mark.asyncio
    async def test_permanent_faults_dont_open_circuit(self, breaker: CircuitBreaker) -> None:
        """Multiple permanent faults should not open the circuit."""
        try:
            from anthropic import NotFoundError

            error = NotFoundError.__new__(NotFoundError)
            error.status_code = 404
            error.message = "Not found"

            # Record many permanent faults
            for _ in range(10):
                await breaker._record_failure(error)

            assert breaker.state == CircuitState.CLOSED
            assert breaker.permanent_failure_count == 10
            assert breaker.failure_count == 0
        except ImportError:
            pytest.skip("anthropic not installed")

    @pytest.mark.asyncio
    async def test_transient_faults_open_circuit_at_threshold(
        self, breaker: CircuitBreaker
    ) -> None:
        """Transient faults should open circuit after threshold reached."""
        try:
            from anthropic import RateLimitError

            error = RateLimitError.__new__(RateLimitError)
            error.status_code = 429
            error.message = "Rate limit"

            # Record transient faults up to threshold
            for _ in range(3):
                await breaker._record_failure(error)

            assert breaker.state == CircuitState.OPEN
            assert breaker.transient_failure_count == 3
        except ImportError:
            pytest.skip("anthropic not installed")

    @pytest.mark.asyncio
    async def test_get_status_includes_fault_stats(self, breaker: CircuitBreaker) -> None:
        """get_status() should include fault classification stats."""
        try:
            from anthropic import NotFoundError, RateLimitError

            # Record one of each type
            transient_error = RateLimitError.__new__(RateLimitError)
            transient_error.status_code = 429
            transient_error.message = "Rate limit"

            permanent_error = NotFoundError.__new__(NotFoundError)
            permanent_error.status_code = 404
            permanent_error.message = "Not found"

            await breaker._record_failure(transient_error)
            await breaker._record_failure(permanent_error)

            status = breaker.get_status()

            assert status["transient_failure_count"] == 1
            assert status["permanent_failure_count"] == 1
            assert status["last_fault_type"] == "permanent"
        except ImportError:
            pytest.skip("anthropic not installed")

    @pytest.mark.asyncio
    async def test_unknown_fault_treated_as_transient(self, breaker: CircuitBreaker) -> None:
        """Unknown faults should be treated as transient (safe default)."""
        # Use generic exception that won't be classified as API error
        # For this test, we need to bypass the API error check
        breaker.config.excluded_exceptions = ()

        # Mock an error that passes the API check but isn't classified
        try:
            from anthropic import APIError

            class UnknownAPIError(APIError):
                """API error without status code."""

                def __init__(self) -> None:
                    pass

            error = UnknownAPIError()

            await breaker._record_failure(error)

            # Unknown should be treated as transient
            assert breaker.transient_failure_count == 1
            assert breaker.last_fault_type == FaultType.UNKNOWN
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_closed_state_resets_fault_counters(self, breaker: CircuitBreaker) -> None:
        """Transitioning to CLOSED should reset fault counters."""
        breaker.transient_failure_count = 5
        breaker.permanent_failure_count = 3
        breaker.last_fault_type = FaultType.TRANSIENT

        breaker._set_state_sync(CircuitState.CLOSED)

        assert breaker.transient_failure_count == 0
        assert breaker.permanent_failure_count == 0
        assert breaker.last_fault_type is None


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig fault-type settings."""

    def test_default_fault_thresholds(self) -> None:
        """Config should have sensible defaults for fault thresholds."""
        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)

        assert config.transient_failure_threshold == 5
        assert config.permanent_failure_threshold == 3  # max(3, 5-2)
        assert config.transient_recovery_timeout == 60
        assert config.permanent_recovery_timeout == 300  # 60 * 5

    def test_explicit_fault_thresholds(self) -> None:
        """Config should use explicit fault thresholds when provided."""
        config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60,
            transient_failure_threshold=10,
            permanent_failure_threshold=5,
            transient_recovery_timeout=30,
            permanent_recovery_timeout=120,
        )

        assert config.transient_failure_threshold == 10
        assert config.permanent_failure_threshold == 5
        assert config.transient_recovery_timeout == 30
        assert config.permanent_recovery_timeout == 120


class TestRecoveryTimeout:
    """Tests for fault-type-based recovery timeouts."""

    def test_transient_fault_uses_transient_timeout(self) -> None:
        """Recovery timeout should use transient timeout after transient fault."""
        config = CircuitBreakerConfig(
            transient_recovery_timeout=30,
            permanent_recovery_timeout=300,
        )
        breaker = CircuitBreaker(config, service_name="test")
        breaker.last_fault_type = FaultType.TRANSIENT

        assert breaker._get_recovery_timeout() == 30

    def test_permanent_fault_uses_permanent_timeout(self) -> None:
        """Recovery timeout should use permanent timeout after permanent fault."""
        config = CircuitBreakerConfig(
            transient_recovery_timeout=30,
            permanent_recovery_timeout=300,
        )
        breaker = CircuitBreaker(config, service_name="test")
        breaker.last_fault_type = FaultType.PERMANENT

        assert breaker._get_recovery_timeout() == 300

    def test_no_fault_uses_transient_timeout(self) -> None:
        """Recovery timeout should default to transient when no fault type set."""
        config = CircuitBreakerConfig(
            transient_recovery_timeout=30,
            permanent_recovery_timeout=300,
        )
        breaker = CircuitBreaker(config, service_name="test")
        breaker.last_fault_type = None

        assert breaker._get_recovery_timeout() == 30

    def test_unknown_fault_uses_transient_timeout(self) -> None:
        """Recovery timeout should use transient timeout for unknown faults."""
        config = CircuitBreakerConfig(
            transient_recovery_timeout=30,
            permanent_recovery_timeout=300,
        )
        breaker = CircuitBreaker(config, service_name="test")
        breaker.last_fault_type = FaultType.UNKNOWN

        assert breaker._get_recovery_timeout() == 30


class TestModelSpecificFaultType:
    """Tests for MODEL_SPECIFIC fault classification (529 overloaded)."""

    def test_status_529_is_model_specific(self) -> None:
        """529 (overloaded) should be classified as MODEL_SPECIFIC."""
        try:
            from anthropic import APIStatusError

            error = APIStatusError.__new__(APIStatusError)
            error.status_code = 529
            result = classify_fault(error)
            assert result == FaultType.MODEL_SPECIFIC
        except ImportError:
            pytest.skip("anthropic not installed")

    def test_generic_529_is_model_specific(self) -> None:
        """Generic exceptions with 529 status_code should be MODEL_SPECIFIC."""

        class GenericError(Exception):
            status_code = 529

        error = GenericError("Model overloaded")
        result = classify_fault(error)
        assert result == FaultType.MODEL_SPECIFIC

    def test_model_specific_fault_type_exists(self) -> None:
        """FaultType should have MODEL_SPECIFIC value."""
        assert hasattr(FaultType, "MODEL_SPECIFIC")
        assert FaultType.MODEL_SPECIFIC.value == "model_specific"
