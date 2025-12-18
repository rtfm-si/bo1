"""Circuit breaker pattern for external API resilience.

Implements the circuit breaker pattern to prevent cascading failures
when external APIs (Anthropic, Voyage, Brave) are experiencing issues.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests fail immediately (fast-fail)
- HALF_OPEN: Testing if service recovered, limited requests allowed

Example:
    >>> from bo1.llm.circuit_breaker import call_with_circuit_breaker
    >>> response = await call_with_circuit_breaker(
    ...     client.messages.create,
    ...     model="claude-opus",
    ...     messages=[...],
    ... )
"""

import asyncio
import logging
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from bo1.constants import CircuitBreakerConfig as CBConstants

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal: requests pass through
    OPEN = "open"  # Failing: fast-fail, no requests
    HALF_OPEN = "half_open"  # Testing: limited requests allowed


class FaultType(str, Enum):
    """Fault classification for circuit breaker behavior.

    TRANSIENT: Temporary failures that may recover (retry-worthy)
    PERMANENT: Deterministic failures that won't recover (fail-fast)
    UNKNOWN: Unclassified errors (treated as transient for safety)
    """

    TRANSIENT = "transient"  # Rate limits, timeouts, 5xx - retry-worthy
    PERMANENT = "permanent"  # 400, 401, 403, 404 - fail-fast
    UNKNOWN = "unknown"  # Unclassified - treat as transient


def classify_fault(error: Exception) -> FaultType:
    """Classify an exception as transient or permanent.

    Args:
        error: The exception to classify

    Returns:
        FaultType indicating whether error is transient (retry-worthy) or permanent
    """
    # Anthropic SDK exceptions
    try:
        from anthropic import (
            APIConnectionError,
            APIStatusError,
            APITimeoutError,
            RateLimitError,
        )

        # Rate limits are transient
        if isinstance(error, RateLimitError):
            return FaultType.TRANSIENT

        # Timeouts and connection errors are transient
        if isinstance(error, (APITimeoutError, APIConnectionError)):
            return FaultType.TRANSIENT

        # API status errors - check HTTP status code
        if isinstance(error, APIStatusError):
            status = getattr(error, "status_code", None)
            if status is None:
                return FaultType.UNKNOWN
            # 5xx errors are transient (server issues)
            if 500 <= status < 600:
                return FaultType.TRANSIENT
            # 429 is rate limit (transient)
            if status == 429:
                return FaultType.TRANSIENT
            # 4xx errors (except 429) are permanent (client errors)
            if 400 <= status < 500:
                return FaultType.PERMANENT
            return FaultType.UNKNOWN
    except ImportError:
        pass

    # httpx exceptions (used by Anthropic SDK internally)
    try:
        from httpx import ConnectError, TimeoutException

        if isinstance(error, (TimeoutException, ConnectError)):
            return FaultType.TRANSIENT
    except ImportError:
        pass

    # Generic HTTP status code extraction
    status = getattr(error, "status_code", None) or getattr(error, "status", None)
    if status is not None:
        if 500 <= status < 600 or status == 429:
            return FaultType.TRANSIENT
        if 400 <= status < 500:
            return FaultType.PERMANENT

    # Connection/timeout patterns in error message
    error_str = str(error).lower()
    transient_patterns = ["timeout", "connection", "rate limit", "503", "502", "504"]
    if any(p in error_str for p in transient_patterns):
        return FaultType.TRANSIENT

    # Default to unknown (treated as transient for safety)
    return FaultType.UNKNOWN


def classify_fault_db(error: Exception) -> FaultType:
    """Classify a database exception as transient or permanent.

    Args:
        error: The database exception to classify

    Returns:
        FaultType indicating whether error is transient (retry-worthy) or permanent
    """
    try:
        import psycopg2
        from psycopg2 import pool as psycopg2_pool

        # Pool exhaustion is transient - will recover
        if isinstance(error, psycopg2_pool.PoolError):
            return FaultType.TRANSIENT

        # Connection errors are transient
        if isinstance(error, psycopg2.OperationalError):
            return FaultType.TRANSIENT

        # Interface errors (bad cursor state) are permanent
        if isinstance(error, psycopg2.InterfaceError):
            return FaultType.PERMANENT

        # Programming errors (SQL syntax) are permanent
        if isinstance(error, psycopg2.ProgrammingError):
            return FaultType.PERMANENT

        # Integrity errors (constraints) are permanent
        if isinstance(error, psycopg2.IntegrityError):
            return FaultType.PERMANENT

        # Data errors (type mismatches) are permanent
        if isinstance(error, psycopg2.DataError):
            return FaultType.PERMANENT

    except ImportError:
        pass

    # Check error message patterns
    error_str = str(error).lower()
    transient_patterns = [
        "connection",
        "timeout",
        "pool exhausted",
        "too many connections",
        "server closed",
        "connection reset",
    ]
    if any(p in error_str for p in transient_patterns):
        return FaultType.TRANSIENT

    return FaultType.UNKNOWN


def classify_fault_redis(error: Exception) -> FaultType:
    """Classify a Redis exception as transient or permanent.

    Args:
        error: The Redis exception to classify

    Returns:
        FaultType indicating whether error is transient (retry-worthy) or permanent
    """
    try:
        import redis as redis_lib

        # Auth errors are permanent (check before ConnectionError - it inherits from it)
        if isinstance(error, redis_lib.AuthenticationError):
            return FaultType.PERMANENT

        # Response errors (WRONGTYPE, etc.) are permanent
        if isinstance(error, redis_lib.ResponseError):
            return FaultType.PERMANENT

        # Connection errors are transient
        if isinstance(error, redis_lib.ConnectionError):
            return FaultType.TRANSIENT

        # Timeout errors are transient
        if isinstance(error, redis_lib.TimeoutError):
            return FaultType.TRANSIENT

    except ImportError:
        pass

    # Check error message patterns
    error_str = str(error).lower()
    transient_patterns = ["connection", "timeout", "refused", "reset", "closed"]
    if any(p in error_str for p in transient_patterns):
        return FaultType.TRANSIENT

    return FaultType.UNKNOWN


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    def __init__(
        self,
        failure_threshold: int = CBConstants.FAILURE_THRESHOLD,
        recovery_timeout: int = CBConstants.RECOVERY_TIMEOUT,
        success_threshold: int = CBConstants.SUCCESS_THRESHOLD,
        excluded_exceptions: tuple[type[Exception], ...] | None = None,
        # Per-fault-type settings (REL-P2)
        transient_failure_threshold: int | None = None,
        permanent_failure_threshold: int | None = None,
        transient_recovery_timeout: int | None = None,
        permanent_recovery_timeout: int | None = None,
    ) -> None:
        """Initialize circuit breaker config.

        Args:
            failure_threshold: Number of failures before circuit opens (legacy)
            recovery_timeout: Seconds to wait before transitioning to half-open (legacy)
            success_threshold: Number of successes in half-open to close circuit
            excluded_exceptions: Exception types that don't count as failures
            transient_failure_threshold: Failures before opening for transient faults (default: 5)
            permanent_failure_threshold: Failures before opening for permanent faults (default: 3)
            transient_recovery_timeout: Recovery timeout for transient faults in seconds (default: 60)
            permanent_recovery_timeout: Recovery timeout for permanent faults in seconds (default: 300)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions or ()
        # Per-fault-type thresholds (use legacy values as fallback)
        self.transient_failure_threshold = transient_failure_threshold or failure_threshold
        self.permanent_failure_threshold = permanent_failure_threshold or max(
            3, failure_threshold - 2
        )
        self.transient_recovery_timeout = transient_recovery_timeout or recovery_timeout
        self.permanent_recovery_timeout = permanent_recovery_timeout or recovery_timeout * 5


class CircuitBreaker:
    """Circuit breaker for Anthropic API calls.

    Implements the circuit breaker pattern to prevent cascading failures:

    CLOSED (normal):
    - Requests pass through normally
    - Failures increment counter
    - After N failures -> OPEN

    OPEN (failing):
    - Requests fail immediately without hitting API
    - Fast-fail prevents overload
    - After timeout -> HALF_OPEN

    HALF_OPEN (testing recovery):
    - Limited requests allowed to test if service recovered
    - If succeeds -> CLOSED
    - If fails -> OPEN (with longer timeout)

    Example:
        >>> breaker = CircuitBreaker()
        >>> response = await breaker.call(
        ...     client.messages.create,
        ...     model="claude-opus",
        ...     messages=[...],
        ... )
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        service_name: str = "unknown",
    ) -> None:
        """Initialize circuit breaker.

        Args:
            config: CircuitBreakerConfig (uses defaults if None)
            service_name: Name of the service (for metrics/logging)
        """
        self.config = config or CircuitBreakerConfig()
        self.service_name = service_name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()
        self._lock = asyncio.Lock()
        # Fault classification tracking (REL-P2)
        self.transient_failure_count = 0
        self.permanent_failure_count = 0
        self.last_fault_type: FaultType | None = None

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call (e.g., client.messages.create)
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result from successful function call

        Raises:
            CircuitBreakerOpenError: If circuit is open (fast-fail)
            APIError: If function raises (after retries exhausted)

        Example:
            >>> breaker = CircuitBreaker()
            >>> response = await breaker.call(
            ...     client.messages.create,
            ...     model="claude-opus",
            ...     messages=[{"role": "user", "content": "Hello"}],
            ... )
        """
        async with self._lock:
            # Check if we should transition to half-open
            await self._check_recovery()

            # If circuit is open, fail immediately
            if self.state == CircuitState.OPEN:
                logger.error(
                    f"Circuit breaker OPEN: Fast-fail without calling API. "
                    f"Failed {self.failure_count}x, will retry in "
                    f"{self.config.recovery_timeout}s"
                )
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Service unavailable. "
                    f"(Failed {self.failure_count} times)"
                )

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Success: record it
            async with self._lock:
                await self._record_success()

            return result

        except Exception as e:
            # Failure: record it
            async with self._lock:
                await self._record_failure(e)

            # Re-raise the original error
            raise

    async def _record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"Circuit breaker: Success {self.success_count}/{self.config.success_threshold} "
                f"in HALF_OPEN state"
            )

            # If enough successes, close circuit
            if self.success_count >= self.config.success_threshold:
                await self._set_state(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
            logger.debug("Circuit breaker: Success in CLOSED state")

    async def _record_failure(self, error: Exception) -> None:
        """Record a failed call with fault classification.

        Args:
            error: The exception that occurred
        """
        # Check if this is an excluded exception (shouldn't count)
        if isinstance(error, self.config.excluded_exceptions):
            logger.debug(f"Excluded exception (doesn't count): {type(error).__name__}")
            return

        # Only count API-related errors as circuit-breaker failures
        # Import here to avoid circular imports
        try:
            from anthropic import APIError, RateLimitError

            if not isinstance(error, (APIError, RateLimitError)):
                logger.debug(f"Non-API error (doesn't affect circuit): {type(error).__name__}")
                return
        except ImportError:
            # If anthropic not available, count all exceptions
            pass

        # Classify the fault (REL-P2)
        fault_type = classify_fault(error)
        self.last_fault_type = fault_type
        self.last_failure_time = time.time()

        # Track per-fault-type counters
        if fault_type == FaultType.PERMANENT:
            self.permanent_failure_count += 1
            # Permanent faults don't trigger circuit open (deterministic failures)
            logger.warning(
                f"Circuit breaker: Permanent fault {self.permanent_failure_count} - "
                f"{type(error).__name__}: {str(error)[:100]} (not triggering circuit)"
            )
            self._emit_fault_metric(fault_type)
            return
        else:
            # Transient or unknown faults trigger circuit breaker
            self.transient_failure_count += 1
            self.failure_count += 1

        logger.warning(
            f"Circuit breaker: {fault_type.value} fault {self.failure_count}/"
            f"{self.config.transient_failure_threshold} - "
            f"{type(error).__name__}: {str(error)[:100]}"
        )

        self._emit_fault_metric(fault_type)

        # Only transient faults open circuit
        if self.failure_count >= self.config.transient_failure_threshold:
            await self._set_state(CircuitState.OPEN)

    def _emit_fault_metric(self, fault_type: FaultType) -> None:
        """Emit Prometheus metric for fault classification."""
        try:
            from backend.api.middleware.metrics import record_circuit_breaker_fault

            record_circuit_breaker_fault(self.service_name, fault_type.value)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Failed to emit fault metric: {e}")

    async def _check_recovery(self) -> None:
        """Check if we should transition from OPEN to HALF_OPEN.

        This is called before each request when in OPEN state.
        If recovery timeout has elapsed, transition to HALF_OPEN.
        Recovery timeout varies by last fault type (REL-P2).
        """
        if self.state != CircuitState.OPEN:
            return

        elapsed = time.time() - self.last_failure_time
        # Use fault-type-specific recovery timeout
        recovery_timeout = self._get_recovery_timeout()
        if elapsed >= recovery_timeout:
            await self._set_state(CircuitState.HALF_OPEN)

    def _get_recovery_timeout(self) -> int:
        """Get recovery timeout based on last fault type."""
        if self.last_fault_type == FaultType.PERMANENT:
            return self.config.permanent_recovery_timeout
        return self.config.transient_recovery_timeout

    async def _set_state(self, new_state: CircuitState) -> None:
        """Transition to a new state.

        Args:
            new_state: The new circuit state
        """
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()

        # Reset counters based on new state
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
            self.transient_failure_count = 0
            self.permanent_failure_count = 0
            self.last_fault_type = None
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        elif new_state == CircuitState.OPEN:
            pass  # Keep failure count for logging

        logger.warning(
            f"Circuit breaker: {old_state.value.upper()} -> {new_state.value.upper()} "
            f"(failures={self.failure_count}, transient={self.transient_failure_count}, "
            f"permanent={self.permanent_failure_count}, successes={self.success_count})"
        )

        # Emit Prometheus metrics
        self._emit_state_metrics(new_state, old_state)

    def call_sync(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute sync function with circuit breaker protection.

        Args:
            func: Sync function to call
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result from successful function call

        Raises:
            CircuitBreakerOpenError: If circuit is open (fast-fail)
        """
        # Check recovery (sync version)
        self._check_recovery_sync()

        # If circuit is open, fail immediately
        if self.state == CircuitState.OPEN:
            logger.error(
                f"Circuit breaker OPEN: Fast-fail without calling API. "
                f"Failed {self.failure_count}x, will retry in "
                f"{self.config.recovery_timeout}s"
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Service unavailable. (Failed {self.failure_count} times)"
            )

        try:
            result = func(*args, **kwargs)
            self._record_success_sync()
            return result
        except Exception as e:
            self._record_failure_sync(e)
            raise

    def _check_recovery_sync(self) -> None:
        """Sync version of recovery check."""
        if self.state != CircuitState.OPEN:
            return
        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.config.recovery_timeout:
            self._set_state_sync(CircuitState.HALF_OPEN)

    def _record_success_sync(self) -> None:
        """Sync version of success recording."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._set_state_sync(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def _record_failure_sync(self, error: Exception) -> None:
        """Sync version of failure recording."""
        if isinstance(error, self.config.excluded_exceptions):
            return

        # Count all errors for non-Anthropic services
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker: Failure {self.failure_count}/{self.config.failure_threshold} - "
            f"{type(error).__name__}: {str(error)[:100]}"
        )

        if self.failure_count >= self.config.failure_threshold:
            self._set_state_sync(CircuitState.OPEN)

    def _set_state_sync(self, new_state: CircuitState) -> None:
        """Sync version of state transition."""
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
            self.transient_failure_count = 0
            self.permanent_failure_count = 0
            self.last_fault_type = None
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0

        logger.warning(
            f"Circuit breaker: {old_state.value.upper()} -> {new_state.value.upper()} "
            f"(failures={self.failure_count}, transient={self.transient_failure_count}, "
            f"permanent={self.permanent_failure_count}, successes={self.success_count})"
        )

        # Emit Prometheus metrics
        self._emit_state_metrics(new_state, old_state)

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status.

        Returns:
            Dict with status info (state, failure count, uptime since last change)
        """
        uptime = time.time() - self.last_state_change
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "uptime_seconds": uptime,
            "is_open": self.state == CircuitState.OPEN,
            "is_half_open": self.state == CircuitState.HALF_OPEN,
            # Fault classification stats (REL-P2)
            "transient_failure_count": self.transient_failure_count,
            "permanent_failure_count": self.permanent_failure_count,
            "last_fault_type": self.last_fault_type.value if self.last_fault_type else None,
        }

    def _emit_state_metrics(self, new_state: CircuitState, old_state: CircuitState) -> None:
        """Emit Prometheus metrics for state changes.

        Args:
            new_state: The new circuit state
            old_state: The previous circuit state
        """
        try:
            from backend.api.middleware.metrics import (
                record_circuit_breaker_state,
                record_circuit_breaker_trip,
            )

            # Record current state
            record_circuit_breaker_state(self.service_name, new_state.value)

            # Record trip if transitioning to OPEN
            if new_state == CircuitState.OPEN and old_state != CircuitState.OPEN:
                record_circuit_breaker_trip(self.service_name)
        except ImportError:
            # Metrics module not available (e.g., during tests)
            pass
        except Exception as e:
            logger.debug(f"Failed to emit circuit breaker metrics: {e}")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""

    pass


# Global circuit breaker registry for per-service instances
_circuit_breakers: dict[str, CircuitBreaker] = {}


# Service-specific configurations with fault-type settings (REL-P2)
SERVICE_CONFIGS: dict[str, dict[str, int]] = {
    "anthropic": {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "success_threshold": 2,
        # Transient-focused (API reliability)
        "transient_failure_threshold": 5,
        "permanent_failure_threshold": 3,
        "transient_recovery_timeout": 60,
        "permanent_recovery_timeout": 300,
    },
    "openai": {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "success_threshold": 2,
        # Transient-focused (API reliability)
        "transient_failure_threshold": 5,
        "permanent_failure_threshold": 3,
        "transient_recovery_timeout": 60,
        "permanent_recovery_timeout": 300,
    },
    "voyage": {
        "failure_threshold": 8,  # Higher threshold - embeddings have retries
        "recovery_timeout": 30,  # Shorter recovery - embeddings are fast
        "success_threshold": 2,
        # Transient-focused (embeddings)
        "transient_failure_threshold": 8,
        "permanent_failure_threshold": 5,
        "transient_recovery_timeout": 30,
        "permanent_recovery_timeout": 120,
    },
    "brave": {
        "failure_threshold": 5,
        "recovery_timeout": 45,  # Rate limit sensitive
        "success_threshold": 2,
        # Rate-limit-focused (search API)
        "transient_failure_threshold": 5,
        "permanent_failure_threshold": 3,
        "transient_recovery_timeout": 45,
        "permanent_recovery_timeout": 180,
    },
    "tavily": {
        "failure_threshold": 5,
        "recovery_timeout": 45,  # Similar to Brave - rate limit sensitive
        "success_threshold": 2,
        # Rate-limit-focused (search API)
        "transient_failure_threshold": 5,
        "permanent_failure_threshold": 3,
        "transient_recovery_timeout": 45,
        "permanent_recovery_timeout": 180,
    },
    "postgres": {
        "failure_threshold": 8,  # Higher threshold - transient failures rare
        "recovery_timeout": 30,  # Shorter recovery - Postgres recovers fast
        "success_threshold": 2,
        "transient_failure_threshold": 8,
        "permanent_failure_threshold": 5,
        "transient_recovery_timeout": 30,
        "permanent_recovery_timeout": 120,
    },
    "redis": {
        "failure_threshold": 5,  # Moderate threshold
        "recovery_timeout": 15,  # Short recovery - Redis is fast
        "success_threshold": 2,
        "transient_failure_threshold": 5,
        "permanent_failure_threshold": 3,
        "transient_recovery_timeout": 15,
        "permanent_recovery_timeout": 60,
    },
}


def get_service_circuit_breaker(service: str) -> CircuitBreaker:
    """Get or create circuit breaker for a specific service.

    Args:
        service: Service name ("anthropic", "voyage", "brave")

    Returns:
        CircuitBreaker instance for the service

    Example:
        >>> breaker = get_service_circuit_breaker("voyage")
        >>> result = await breaker.call(voyage_api_func, ...)
    """
    if service not in _circuit_breakers:
        config_params = SERVICE_CONFIGS.get(service, SERVICE_CONFIGS["anthropic"])
        config = CircuitBreakerConfig(
            failure_threshold=config_params["failure_threshold"],
            recovery_timeout=config_params["recovery_timeout"],
            success_threshold=config_params["success_threshold"],
            transient_failure_threshold=config_params.get("transient_failure_threshold"),
            permanent_failure_threshold=config_params.get("permanent_failure_threshold"),
            transient_recovery_timeout=config_params.get("transient_recovery_timeout"),
            permanent_recovery_timeout=config_params.get("permanent_recovery_timeout"),
        )
        _circuit_breakers[service] = CircuitBreaker(config, service_name=service)
        logger.debug(f"Created circuit breaker for service: {service}")
    return _circuit_breakers[service]


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create the global circuit breaker instance (Anthropic).

    Returns:
        Global CircuitBreaker instance for Anthropic
    """
    return get_service_circuit_breaker("anthropic")


async def call_with_circuit_breaker(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Convenience function to use global circuit breaker.

    Args:
        func: Async function to call
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result from function call

    Example:
        >>> from bo1.llm.circuit_breaker import call_with_circuit_breaker
        >>> response = await call_with_circuit_breaker(
        ...     client.messages.create,
        ...     model="claude-opus",
        ...     messages=[...],
        ... )
    """
    breaker = get_circuit_breaker()
    return await breaker.call(func, *args, **kwargs)


def get_circuit_breaker_status() -> dict[str, Any]:
    """Get global circuit breaker status (Anthropic).

    Returns:
        Status dict from circuit breaker
    """
    breaker = get_circuit_breaker()
    return breaker.get_status()


def get_all_circuit_breaker_status() -> dict[str, dict[str, Any]]:
    """Get status of all circuit breakers.

    Returns:
        Dict mapping service name to status dict
    """
    return {service: breaker.get_status() for service, breaker in _circuit_breakers.items()}


def reset_circuit_breaker() -> None:
    """Reset the global circuit breaker (Anthropic) to initial state.

    Useful for testing or manual recovery.
    """
    reset_service_circuit_breaker("anthropic")


def reset_service_circuit_breaker(service: str) -> None:
    """Reset a specific service's circuit breaker.

    Args:
        service: Service name to reset
    """
    if service in _circuit_breakers:
        del _circuit_breakers[service]
    logger.info(f"Circuit breaker reset for service: {service}")


def get_active_llm_provider(
    primary: str = "anthropic",
    fallback: str = "openai",
    fallback_enabled: bool = True,
) -> str:
    """Get the currently active (healthy) LLM provider.

    Checks circuit breaker states and returns the provider to use.
    If primary provider's circuit is open and fallback is enabled,
    returns the fallback provider.

    Args:
        primary: Primary provider name (default: "anthropic")
        fallback: Fallback provider name (default: "openai")
        fallback_enabled: Whether to allow fallback (default: True)

    Returns:
        Provider name to use ("anthropic" or "openai")

    Examples:
        >>> get_active_llm_provider()  # Primary healthy
        "anthropic"
        >>> # After Anthropic failures...
        >>> get_active_llm_provider()  # Primary circuit open
        "openai"
    """
    primary_breaker = get_service_circuit_breaker(primary)

    # If primary is healthy (closed or half-open), use it
    if primary_breaker.state != CircuitState.OPEN:
        return primary

    # Primary is open - check if we should fall back
    if not fallback_enabled:
        logger.warning(f"Primary provider {primary} circuit OPEN, fallback disabled")
        return primary  # Will raise CircuitBreakerOpenError on call

    # Check fallback provider health
    fallback_breaker = get_service_circuit_breaker(fallback)
    if fallback_breaker.state == CircuitState.OPEN:
        logger.error(f"Both {primary} and {fallback} circuits OPEN - no healthy provider")
        return primary  # Return primary, will fail but at least tries

    logger.warning(f"Primary provider {primary} circuit OPEN, falling back to {fallback}")
    return fallback


def is_provider_healthy(provider: str) -> bool:
    """Check if a provider's circuit breaker is healthy.

    Args:
        provider: Provider name to check

    Returns:
        True if provider is healthy (circuit closed or half-open)
    """
    breaker = get_service_circuit_breaker(provider)
    return breaker.state != CircuitState.OPEN


def get_provider_health(provider: str) -> dict[str, Any]:
    """Get detailed health info for a provider.

    Args:
        provider: Provider name

    Returns:
        Dict with health metrics for vendor health tracking
    """
    breaker = get_service_circuit_breaker(provider)
    status = breaker.get_status()
    return {
        "provider": provider,
        "circuit_state": status["state"],
        "failure_count": status["failure_count"],
        "success_count": status["success_count"],
        "is_healthy": breaker.state != CircuitState.OPEN,
        "last_state_change": breaker.last_state_change,
        "last_failure_time": breaker.last_failure_time,
        "uptime_seconds": status["uptime_seconds"],
    }
