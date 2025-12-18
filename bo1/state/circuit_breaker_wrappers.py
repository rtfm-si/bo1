"""Circuit breaker wrappers for database and Redis operations.

Provides decorators and utilities to protect DB and Redis calls with
circuit breaker pattern, preventing cascading failures.

Example:
    >>> from bo1.state.circuit_breaker_wrappers import with_db_circuit_breaker
    >>> @with_db_circuit_breaker
    ... def my_db_operation():
    ...     # DB operation here
    ...     pass
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, cast

from bo1.llm.circuit_breaker import (
    CircuitBreakerOpenError,
    classify_fault_db,
    classify_fault_redis,
    get_service_circuit_breaker,
)

logger = logging.getLogger(__name__)


def with_db_circuit_breaker[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to wrap sync DB calls with circuit breaker protection.

    Uses the 'postgres' circuit breaker configuration. Records failures
    for transient DB errors (connection, timeout, pool exhaustion).

    Args:
        func: Sync function to wrap

    Returns:
        Wrapped function with circuit breaker protection

    Raises:
        CircuitBreakerOpenError: If circuit is open (fast-fail)

    Example:
        >>> @with_db_circuit_breaker
        ... def get_user(user_id: str):
        ...     with db_session() as conn:
        ...         # DB operation
        ...         pass
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        breaker = get_service_circuit_breaker("postgres")

        # Custom fault classifier for DB errors
        def execute_with_db_fault_classification() -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Classify DB-specific faults
                fault_type = classify_fault_db(e)
                # Only record transient faults (avoid tripping on app errors)
                if fault_type.value != "permanent":
                    breaker._record_failure_sync(e)
                raise

        return cast(T, breaker.call_sync(execute_with_db_fault_classification))

    return wrapper


def with_redis_circuit_breaker[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to wrap sync Redis calls with circuit breaker protection.

    Uses the 'redis' circuit breaker configuration. Records failures
    for transient Redis errors (connection, timeout).

    Args:
        func: Sync function to wrap

    Returns:
        Wrapped function with circuit breaker protection

    Raises:
        CircuitBreakerOpenError: If circuit is open (fast-fail)

    Example:
        >>> @with_redis_circuit_breaker
        ... def get_cached_data(key: str):
        ...     return redis_client.get(key)
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        breaker = get_service_circuit_breaker("redis")

        # Custom fault classifier for Redis errors
        def execute_with_redis_fault_classification() -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Classify Redis-specific faults
                fault_type = classify_fault_redis(e)
                # Only record transient faults
                if fault_type.value != "permanent":
                    breaker._record_failure_sync(e)
                raise

        return cast(T, breaker.call_sync(execute_with_redis_fault_classification))

    return wrapper


def record_db_failure(error: Exception) -> None:
    """Manually record a database failure in the circuit breaker.

    Use this when you have custom error handling and need to record
    failures without using the decorator.

    Args:
        error: The database exception that occurred
    """
    breaker = get_service_circuit_breaker("postgres")
    fault_type = classify_fault_db(error)
    if fault_type.value != "permanent":
        breaker._record_failure_sync(error)
        logger.debug(f"[DB_CIRCUIT] Recorded failure: {type(error).__name__}")


def record_db_success() -> None:
    """Manually record a database success in the circuit breaker.

    Use this when you have custom success handling and need to record
    successes without using the decorator.
    """
    breaker = get_service_circuit_breaker("postgres")
    breaker._record_success_sync()


def record_redis_failure(error: Exception) -> None:
    """Manually record a Redis failure in the circuit breaker.

    Use this when you have custom error handling and need to record
    failures without using the decorator.

    Args:
        error: The Redis exception that occurred
    """
    breaker = get_service_circuit_breaker("redis")
    fault_type = classify_fault_redis(error)
    if fault_type.value != "permanent":
        breaker._record_failure_sync(error)
        logger.debug(f"[REDIS_CIRCUIT] Recorded failure: {type(error).__name__}")


def record_redis_success() -> None:
    """Manually record a Redis success in the circuit breaker.

    Use this when you have custom success handling and need to record
    successes without using the decorator.
    """
    breaker = get_service_circuit_breaker("redis")
    breaker._record_success_sync()


def is_db_circuit_open() -> bool:
    """Check if the database circuit breaker is open.

    Returns:
        True if the circuit is open (rejecting requests)
    """
    breaker = get_service_circuit_breaker("postgres")
    return breaker.state.value == "open"


def is_redis_circuit_open() -> bool:
    """Check if the Redis circuit breaker is open.

    Returns:
        True if the circuit is open (rejecting requests)
    """
    breaker = get_service_circuit_breaker("redis")
    return breaker.state.value == "open"


def get_db_circuit_status() -> dict[str, Any]:
    """Get the current database circuit breaker status.

    Returns:
        Dict with circuit breaker state and metrics
    """
    breaker = get_service_circuit_breaker("postgres")
    return breaker.get_status()


def get_redis_circuit_status() -> dict[str, Any]:
    """Get the current Redis circuit breaker status.

    Returns:
        Dict with circuit breaker state and metrics
    """
    breaker = get_service_circuit_breaker("redis")
    return breaker.get_status()


__all__ = [
    "CircuitBreakerOpenError",
    "with_db_circuit_breaker",
    "with_redis_circuit_breaker",
    "record_db_failure",
    "record_db_success",
    "record_redis_failure",
    "record_redis_success",
    "is_db_circuit_open",
    "is_redis_circuit_open",
    "get_db_circuit_status",
    "get_redis_circuit_status",
]
