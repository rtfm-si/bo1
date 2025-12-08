"""Database connection infrastructure.

Provides:
- Connection pool management
- db_session context manager with RLS support
- Pool health monitoring

This module provides the core database infrastructure
to enable the Repository Pattern implementation.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from bo1.config import Settings

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
        - test_query_success: Whether SELECT 1 succeeded
        - error: Error message if unhealthy
    """
    from bo1.constants import DatabaseConfig

    result: dict[str, Any] = {
        "healthy": False,
        "pool_initialized": _connection_pool is not None,
        "min_connections": DatabaseConfig.POOL_MIN_CONNECTIONS,
        "max_connections": DatabaseConfig.POOL_MAX_CONNECTIONS,
        "test_query_success": False,
        "error": None,
    }

    try:
        pool_instance = get_connection_pool()
        result["pool_initialized"] = True

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


@contextmanager
def db_session(
    user_id: str | None = None,
) -> Generator[Any, None, None]:
    """Context manager for database transactions with RLS support.

    Provides automatic connection pooling, commit/rollback, cleanup, and
    Row-Level Security (RLS) context setting.

    Args:
        user_id: Optional user ID for RLS policies. When provided, sets
                 app.current_user_id session variable for RLS enforcement.

    Yields:
        psycopg2.extensions.connection: PostgreSQL connection from pool
    """
    pool_instance = get_connection_pool()
    conn = pool_instance.getconn()

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
