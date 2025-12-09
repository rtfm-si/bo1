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

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])

# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 0.5  # seconds
DEFAULT_MAX_DELAY = 10.0  # seconds

# Exceptions that trigger retry (transient DB errors)
RETRYABLE_EXCEPTIONS = (OperationalError, InterfaceError, PoolError)


def retry_db(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
) -> Callable[[F], F]:
    """Decorator for retrying database operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 0.5)
        max_delay: Maximum delay between retries in seconds (default: 10)
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry_db(max_attempts=3)
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

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
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
) -> Callable[[F], F]:
    """Async version of retry_db decorator.

    Same behavior as retry_db but uses asyncio.sleep for async functions.
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

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
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
