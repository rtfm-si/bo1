"""Database connection infrastructure.

Provides:
- Connection pool management
- db_session context manager with RLS support
- Pool health monitoring
- Connection timeout handling

This module provides the core database infrastructure
to enable the Repository Pattern implementation.
"""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from bo1.config import Settings


class ConnectionTimeoutError(Exception):
    """Raised when connection pool is exhausted and timeout exceeded."""

    pass


logger = logging.getLogger(__name__)

# Global connection pool (initialized once)
_connection_pool: pool.ThreadedConnectionPool | None = None


@lru_cache(maxsize=1)
def _get_settings() -> Settings:
    """Get cached Settings instance.

    Returns:
        Settings instance (cached)
    """
    return Settings(
        anthropic_api_key="dummy",  # Not needed for DB operations
        voyage_api_key="dummy",  # Not needed for DB operations
    )


def get_connection_pool() -> pool.ThreadedConnectionPool:
    """Get or create the global connection pool.

    Returns:
        ThreadedConnectionPool instance

    Raises:
        ValueError: If DATABASE_URL is not configured
    """
    global _connection_pool

    if _connection_pool is None:
        settings = _get_settings()

        if not settings.database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Import constants for pool configuration
        from bo1.constants import DatabaseConfig

        # Create connection pool with configurable limits
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=DatabaseConfig.POOL_MIN_CONNECTIONS,
            maxconn=DatabaseConfig.POOL_MAX_CONNECTIONS,
            dsn=settings.database_url,
            cursor_factory=RealDictCursor,
        )

    return _connection_pool


def get_pool_health() -> dict[str, Any]:
    """Get health status of the PostgreSQL connection pool.

    Returns:
        Dictionary with pool health metrics:
        - healthy: Whether pool is functioning correctly
        - pool_initialized: Whether pool exists
        - min_connections: Configured minimum connections
        - max_connections: Configured maximum connections
        - used_connections: Count of connections currently in use
        - free_connections: Count of connections available in pool
        - pool_utilization_pct: Percentage of pool in use (0-100)
        - test_query_success: Whether SELECT 1 succeeded
        - error: Error message if unhealthy
    """
    from bo1.constants import DatabaseConfig

    result: dict[str, Any] = {
        "healthy": False,
        "pool_initialized": _connection_pool is not None,
        "min_connections": DatabaseConfig.POOL_MIN_CONNECTIONS,
        "max_connections": DatabaseConfig.POOL_MAX_CONNECTIONS,
        "used_connections": 0,
        "free_connections": 0,
        "pool_utilization_pct": 0.0,
        "test_query_success": False,
        "error": None,
    }

    try:
        pool_instance = get_connection_pool()
        result["pool_initialized"] = True

        # Get pool utilization metrics (thread-safe access)
        # psycopg2 ThreadedConnectionPool uses _used dict and _pool list
        with pool_instance._lock:
            used_count = len(pool_instance._used)
            free_count = len(pool_instance._pool)
        result["used_connections"] = used_count
        result["free_connections"] = free_count
        total = used_count + free_count
        if total > 0:
            result["pool_utilization_pct"] = round((used_count / total) * 100, 1)

        conn = pool_instance.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 AS health_check")
                row = cur.fetchone()
                result["test_query_success"] = row is not None
                result["healthy"] = True
        finally:
            pool_instance.putconn(conn)

    except Exception as e:
        result["error"] = str(e)
        logger.warning(f"Pool health check failed: {e}")

    return result


def reset_connection_pool() -> None:
    """Reset the global connection pool.

    Closes all connections and clears the pool.
    Use after detecting unhealthy state to force reconnection.
    """
    global _connection_pool

    if _connection_pool is not None:
        try:
            _connection_pool.closeall()
            logger.info("Connection pool closed and reset")
        except Exception as e:
            logger.warning(f"Error closing connection pool: {e}")
        finally:
            _connection_pool = None


def check_pool_health_and_recover() -> bool:
    """Check pool health and attempt recovery if unhealthy.

    Returns:
        True if pool is healthy (or recovered), False otherwise
    """
    health = get_pool_health()

    if health["healthy"]:
        return True

    logger.warning(f"Pool unhealthy: {health.get('error')}. Attempting recovery...")

    try:
        reset_connection_pool()
        # Re-check after reset
        new_health = get_pool_health()
        if new_health["healthy"]:
            logger.info("Pool recovered successfully after reset")
            return True
        else:
            logger.error(f"Pool still unhealthy after reset: {new_health.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Pool recovery failed: {e}")
        return False


def _getconn_with_timeout(
    pool_instance: pool.ThreadedConnectionPool,
    timeout: float,
) -> Any:
    """Get connection from pool with timeout.

    Uses polling with short sleeps to implement timeout since psycopg2's
    ThreadedConnectionPool.getconn() blocks indefinitely.

    Args:
        pool_instance: The connection pool
        timeout: Maximum time to wait in seconds

    Returns:
        Database connection

    Raises:
        ConnectionTimeoutError: If timeout exceeded waiting for connection
    """
    start = time.monotonic()
    poll_interval = 0.1  # 100ms between attempts

    while True:
        try:
            # Try non-blocking getconn
            conn = pool_instance.getconn()
            return conn
        except pool.PoolError as e:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                raise ConnectionTimeoutError(
                    f"Connection pool exhausted after {timeout}s: {e}"
                ) from e

            # Wait and retry
            remaining = timeout - elapsed
            sleep_time = min(poll_interval, remaining)
            time.sleep(sleep_time)


# Default connection timeout in seconds
DEFAULT_CONNECTION_TIMEOUT = 5.0


@contextmanager
def db_session(
    user_id: str | None = None,
    timeout: float = DEFAULT_CONNECTION_TIMEOUT,
) -> Generator[Any, None, None]:
    """Context manager for database transactions with RLS support.

    Provides automatic connection pooling, commit/rollback, cleanup, and
    Row-Level Security (RLS) context setting.

    Args:
        user_id: Optional user ID for RLS policies. When provided, sets
                 app.current_user_id session variable for RLS enforcement.
        timeout: Maximum time to wait for a connection from the pool (default: 5s).
                 Raises ConnectionTimeoutError if exceeded.

    Yields:
        psycopg2.extensions.connection: PostgreSQL connection from pool

    Raises:
        ConnectionTimeoutError: If pool is exhausted and timeout exceeded
    """
    pool_instance = get_connection_pool()
    conn = _getconn_with_timeout(pool_instance, timeout)

    try:
        if user_id:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_user_id = %s", (user_id,))
                logger.debug(f"RLS context set for user: {user_id}")

        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool_instance.putconn(conn)
