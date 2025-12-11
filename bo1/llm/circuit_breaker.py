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


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    def __init__(
        self,
        failure_threshold: int = CBConstants.FAILURE_THRESHOLD,
        recovery_timeout: int = CBConstants.RECOVERY_TIMEOUT,
        success_threshold: int = CBConstants.SUCCESS_THRESHOLD,
        excluded_exceptions: tuple[type[Exception], ...] | None = None,
    ) -> None:
        """Initialize circuit breaker config.

        Args:
            failure_threshold: Number of failures before circuit opens
            recovery_timeout: Seconds to wait before transitioning to half-open
            success_threshold: Number of successes in half-open to close circuit
            excluded_exceptions: Exception types that don't count as failures
                (e.g., validation errors shouldn't trigger circuit)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions or ()


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

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        """Initialize circuit breaker.

        Args:
            config: CircuitBreakerConfig (uses defaults if None)
        """
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()
        self._lock = asyncio.Lock()

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
        """Record a failed call.

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

        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"Circuit breaker: Failure {self.failure_count}/{self.config.failure_threshold} - "
            f"{type(error).__name__}: {str(error)[:100]}"
        )

        # If enough failures, open circuit
        if self.failure_count >= self.config.failure_threshold:
            await self._set_state(CircuitState.OPEN)

    async def _check_recovery(self) -> None:
        """Check if we should transition from OPEN to HALF_OPEN.

        This is called before each request when in OPEN state.
        If recovery timeout has elapsed, transition to HALF_OPEN.
        """
        if self.state != CircuitState.OPEN:
            return

        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.config.recovery_timeout:
            await self._set_state(CircuitState.HALF_OPEN)

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
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        elif new_state == CircuitState.OPEN:
            pass  # Keep failure count for logging

        logger.warning(
            f"Circuit breaker: {old_state.value.upper()} -> {new_state.value.upper()} "
            f"(failures={self.failure_count}, successes={self.success_count})"
        )

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
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0

        logger.warning(
            f"Circuit breaker: {old_state.value.upper()} -> {new_state.value.upper()} "
            f"(failures={self.failure_count}, successes={self.success_count})"
        )

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
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""

    pass


# Global circuit breaker registry for per-service instances
_circuit_breakers: dict[str, CircuitBreaker] = {}


# Service-specific configurations
SERVICE_CONFIGS: dict[str, dict[str, int]] = {
    "anthropic": {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "success_threshold": 2,
    },
    "openai": {
        "failure_threshold": 5,
        "recovery_timeout": 60,
        "success_threshold": 2,
    },
    "voyage": {
        "failure_threshold": 8,  # Higher threshold - embeddings have retries
        "recovery_timeout": 30,  # Shorter recovery - embeddings are fast
        "success_threshold": 2,
    },
    "brave": {
        "failure_threshold": 5,
        "recovery_timeout": 45,  # Rate limit sensitive
        "success_threshold": 2,
    },
    "tavily": {
        "failure_threshold": 5,
        "recovery_timeout": 45,  # Similar to Brave - rate limit sensitive
        "success_threshold": 2,
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
        )
        _circuit_breakers[service] = CircuitBreaker(config)
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
