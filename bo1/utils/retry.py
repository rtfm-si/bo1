"""Retry utilities for transient database errors.

Provides decorators and helpers for handling transient PostgreSQL errors
with exponential backoff.
"""

import functools
import logging
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from psycopg2 import InterfaceError, OperationalError
from psycopg2.pool import PoolError

from bo1.constants import RetryConfig

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Default retry configuration (aliased from RetryConfig for backward compat)
DEFAULT_MAX_ATTEMPTS = RetryConfig.MAX_ATTEMPTS
DEFAULT_BASE_DELAY = RetryConfig.BASE_DELAY
DEFAULT_MAX_DELAY = RetryConfig.MAX_DELAY
DEFAULT_TOTAL_TIMEOUT = RetryConfig.TOTAL_TIMEOUT

# Exceptions that trigger retry (transient DB errors)
RETRYABLE_EXCEPTIONS = (OperationalError, InterfaceError, PoolError)

# PostgreSQL SQLSTATE codes that are retryable
# 40P01 = deadlock_detected
# 40001 = serialization_failure
RETRYABLE_PGCODES: frozenset[str] = frozenset({"40P01", "40001"})


def is_retryable_error(exc: BaseException) -> bool:
    """Check if an exception is retryable.

    Returns True if:
    - Exception is an instance of RETRYABLE_EXCEPTIONS (OperationalError, InterfaceError, PoolError)
    - Exception has a pgcode attribute matching RETRYABLE_PGCODES (deadlock, serialization failure)

    Args:
        exc: The exception to check

    Returns:
        True if the exception should trigger a retry, False otherwise

    Example:
        try:
            cursor.execute(...)
        except Exception as e:
            if is_retryable_error(e):
                # retry logic
    """
    # Check base retryable exception types
    if isinstance(exc, RETRYABLE_EXCEPTIONS):
        return True

    # Check PostgreSQL error codes (psycopg2 errors have pgcode attribute)
    pgcode = getattr(exc, "pgcode", None)
    if pgcode is not None and pgcode in RETRYABLE_PGCODES:
        return True

    return False


def retry_db(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    total_timeout: float | None = DEFAULT_TOTAL_TIMEOUT,
) -> Callable[[F], F]:
    """Decorator for retrying database operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.5)
        max_delay: Maximum delay between retries in seconds (default: 10)
        exceptions: Tuple of exception types to catch and retry
        total_timeout: Total timeout across all retries in seconds (default: 30).
            None disables total timeout (backward compat).

    Returns:
        Decorated function with retry logic

    Raises:
        TimeoutError: If total elapsed time exceeds total_timeout

    Note:
        Always specify `total_timeout` explicitly for production callsites.
        Recommended values by operation type:
        - User-facing writes: 30.0 (default)
        - Background batch operations: 60.0
        - Health checks: 5.0

    Example:
        @retry_db(max_attempts=3, base_delay=0.5, total_timeout=30.0)
        def save_data(self, data):
            with db_session() as conn:
                ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Lazy import to avoid circular dependency
            from bo1.context import get_request_id

            last_exception = None
            request_id = get_request_id() or "unknown"
            func_name = getattr(func, "__name__", str(func))
            start_time = time.monotonic()

            for attempt in range(1, max_attempts + 1):
                # Check total timeout before attempt
                if total_timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed > total_timeout:
                        msg = (
                            f"[{request_id}] {func_name} total timeout exceeded: "
                            f"{elapsed:.2f}s > {total_timeout}s after {attempt - 1} attempts"
                        )
                        logger.error(msg)
                        raise TimeoutError(msg)

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Check if exception is retryable (type-based or pgcode-based)
                    if not (isinstance(e, exceptions) or is_retryable_error(e)):
                        raise

                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"[{request_id}] {func_name} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff + jitter
                    # S311: random.uniform is fine for jitter - not security-sensitive
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.1)  # noqa: S311
                    sleep_time = delay + jitter

                    logger.warning(
                        f"[{request_id}] {func_name} attempt {attempt}/{max_attempts} "
                        f"failed: {e}. Retrying in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)

            # Should never reach here, but just in case
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def retry_db_async(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    total_timeout: float | None = DEFAULT_TOTAL_TIMEOUT,
) -> Callable[[F], F]:
    """Async version of retry_db decorator.

    Same behavior as retry_db but uses asyncio.sleep for async functions.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.5)
        max_delay: Maximum delay between retries in seconds (default: 10)
        exceptions: Tuple of exception types to catch and retry
        total_timeout: Total timeout across all retries in seconds (default: 30).
            None disables total timeout (backward compat).

    Raises:
        asyncio.TimeoutError: If total elapsed time exceeds total_timeout
    """
    import asyncio

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Lazy import to avoid circular dependency
            from bo1.context import get_request_id

            last_exception = None
            request_id = get_request_id() or "unknown"
            func_name = getattr(func, "__name__", str(func))
            start_time = time.monotonic()

            for attempt in range(1, max_attempts + 1):
                # Check total timeout before attempt
                if total_timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed > total_timeout:
                        msg = (
                            f"[{request_id}] {func_name} total timeout exceeded: "
                            f"{elapsed:.2f}s > {total_timeout}s after {attempt - 1} attempts"
                        )
                        logger.error(msg)
                        raise TimeoutError(msg)

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Check if exception is retryable (type-based or pgcode-based)
                    if not (isinstance(e, exceptions) or is_retryable_error(e)):
                        raise

                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"[{request_id}] {func_name} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff + jitter
                    # S311: random.uniform is fine for jitter - not security-sensitive
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    jitter = random.uniform(0, delay * 0.1)  # noqa: S311
                    sleep_time = delay + jitter

                    logger.warning(
                        f"[{request_id}] {func_name} attempt {attempt}/{max_attempts} "
                        f"failed: {e}. Retrying in {sleep_time:.2f}s..."
                    )
                    await asyncio.sleep(sleep_time)

            # Should never reach here, but just in case
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
