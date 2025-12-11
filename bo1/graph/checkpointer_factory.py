"""Checkpointer factory for creating backend-appropriate checkpoint savers.

Supports Redis (default) and PostgreSQL backends, configured via CHECKPOINT_BACKEND env var.
"""

import logging
import re
from typing import Any, Literal

from bo1.config import get_settings
from bo1.graph.checkpointer import LoggingCheckpointerWrapper

logger = logging.getLogger(__name__)

# Track if Postgres setup has been called (singleton pattern for setup)
_postgres_setup_complete = False

# Track fallback/degradation state
_using_fallback = False
_fallback_reason: str | None = None
_original_backend: str | None = None


def create_checkpointer(
    backend: Literal["redis", "postgres"] | None = None,
) -> Any:
    """Create a checkpointer for the specified backend.

    Args:
        backend: Checkpoint backend ('redis' or 'postgres').
                If None, uses CHECKPOINT_BACKEND env var (default: 'redis').

    Returns:
        Wrapped checkpointer with logging (LoggingCheckpointerWrapper)

    Raises:
        ValueError: If backend is not recognized

    Example:
        >>> checkpointer = create_checkpointer("postgres")
        >>> graph = create_deliberation_graph(checkpointer=checkpointer)
    """
    settings = get_settings()
    selected_backend = backend or settings.checkpoint_backend

    if selected_backend == "redis":
        return _create_redis_checkpointer()
    elif selected_backend == "postgres":
        return _create_postgres_checkpointer()
    else:
        raise ValueError(
            f"Unknown checkpoint backend: {selected_backend}. Valid options: 'redis', 'postgres'"
        )


def _create_redis_checkpointer() -> Any:
    """Create AsyncRedisSaver checkpointer with fallback to MemorySaver.

    Uses Redis configuration from environment variables.
    Falls back to in-memory checkpointing if Redis is unavailable.
    """
    global _using_fallback, _fallback_reason, _original_backend

    settings = get_settings()

    # Construct URL from individual env vars (Docker compatibility)
    redis_host = settings.redis_host
    redis_port = settings.redis_port
    redis_db = settings.redis_db
    redis_password = settings.redis_password

    if redis_password:
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    # Check Redis availability before creating checkpointer
    if settings.checkpoint_fallback_enabled:
        try:
            import redis

            client = redis.from_url(redis_url, socket_connect_timeout=2)
            client.ping()
            client.close()
        except Exception as e:
            _using_fallback = True
            _fallback_reason = f"Redis unavailable: {e}"
            _original_backend = "redis"
            logger.warning(
                f"Redis checkpoint backend unavailable ({e}), "
                "falling back to in-memory checkpointing. "
                "State will NOT persist across restarts."
            )
            return _create_memory_checkpointer()

    from langgraph.checkpoint.redis.aio import AsyncRedisSaver

    ttl_seconds = settings.checkpoint_ttl_seconds

    base_checkpointer = AsyncRedisSaver(redis_url)
    wrapped = LoggingCheckpointerWrapper(base_checkpointer)

    auth_status = " (with auth)" if redis_password else ""
    logger.info(
        f"Created Redis checkpointer: {redis_host}:{redis_port}/{redis_db}{auth_status} "
        f"(TTL: {ttl_seconds}s)"
    )

    return wrapped


def _create_memory_checkpointer() -> Any:
    """Create in-memory MemorySaver checkpointer.

    Used as fallback when Redis/Postgres are unavailable.
    WARNING: State is lost on process restart.
    """
    from langgraph.checkpoint.memory import MemorySaver

    base_checkpointer = MemorySaver()
    wrapped = LoggingCheckpointerWrapper(base_checkpointer)

    logger.info(
        "Created in-memory checkpointer (fallback mode). "
        "Checkpoint data will NOT persist across restarts."
    )

    return wrapped


def _create_postgres_checkpointer() -> Any:
    """Create AsyncPostgresSaver checkpointer using connection pool.

    Uses DATABASE_URL from environment with psycopg3 AsyncConnectionPool.
    The pool is managed by the checkpointer and handles connection lifecycle.

    Note: setup() must be called separately to create checkpoint tables.
    Use run_postgres_setup() or let it be called lazily on first checkpoint.
    """
    global _postgres_setup_complete

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg_pool import AsyncConnectionPool

    settings = get_settings()
    database_url = settings.database_url

    # Create connection pool with required settings for LangGraph
    # autocommit=True is required for checkpoint operations
    # prepare_threshold=0 disables prepared statements (better for pools)
    pool = AsyncConnectionPool(
        conninfo=database_url,
        max_size=10,  # Reasonable default for checkpoint operations
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
        },
    )

    base_checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]

    # Setup tables on first use (idempotent - safe to call multiple times)
    # Note: setup() requires a synchronous connection, so we run it separately
    if not _postgres_setup_complete:
        try:
            _run_postgres_setup_sync(database_url)
            _postgres_setup_complete = True
            logger.info("PostgreSQL checkpoint tables created/verified")
        except Exception as e:
            logger.warning(f"PostgreSQL checkpoint setup failed (tables may already exist): {e}")
            _postgres_setup_complete = True  # Don't retry on every call

    wrapped = LoggingCheckpointerWrapper(base_checkpointer)

    # Log without exposing password
    safe_url = _mask_password(database_url)
    logger.info(f"Created PostgreSQL checkpointer: {safe_url}")

    return wrapped


def _run_postgres_setup_sync(database_url: str) -> None:
    """Run synchronous PostgreSQL checkpoint table setup.

    Creates the checkpoint tables if they don't exist.
    Uses psycopg (sync) for the setup operation.
    """
    from langgraph.checkpoint.postgres import PostgresSaver

    # Use sync version for setup (creates tables)
    with PostgresSaver.from_conn_string(database_url) as saver:
        saver.setup()


def _mask_password(url: str) -> str:
    """Mask password in connection URL for safe logging."""
    # postgresql://user:password@host:port/db -> postgresql://user:***@host:port/db
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


def get_checkpointer_info() -> dict[str, Any]:
    """Get information about the current checkpointer configuration.

    Useful for health checks and debugging.

    Returns:
        Dict with backend type, connection info (password masked), and fallback status
    """
    settings = get_settings()
    backend = settings.checkpoint_backend

    # Base info varies by backend
    if _using_fallback:
        info = {
            "backend": "memory",
            "using_fallback": True,
            "original_backend": _original_backend,
            "fallback_reason": _fallback_reason,
        }
    elif backend == "redis":
        info = {
            "backend": "redis",
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "ttl_seconds": settings.checkpoint_ttl_seconds,
            "has_auth": bool(settings.redis_password),
            "using_fallback": False,
        }
    elif backend == "postgres":
        info = {
            "backend": "postgres",
            "url": _mask_password(settings.database_url),
            "setup_complete": _postgres_setup_complete,
            "using_fallback": False,
        }
    else:
        info = {"backend": backend, "error": "Unknown backend", "using_fallback": False}

    return info


def check_checkpoint_health() -> dict[str, Any]:
    """Check health of the checkpoint backend.

    Tests actual connectivity to Redis or Postgres checkpoint storage.
    Reports degraded state when using fallback.

    Returns:
        Dict with health status:
        {
            "healthy": bool,
            "degraded": bool,
            "backend": str,
            "message": str,
            "error": str | None,
            "fallback_reason": str | None,
            ...backend-specific info
        }
    """
    settings = get_settings()
    backend = settings.checkpoint_backend
    info = get_checkpointer_info()

    # If using fallback, report as degraded but healthy
    if _using_fallback:
        return {
            "healthy": True,
            "degraded": True,
            "backend": "memory",
            "original_backend": _original_backend,
            "message": "Operating in degraded mode with in-memory checkpointing",
            "fallback_reason": _fallback_reason,
            "error": None,
            **info,
        }

    try:
        if backend == "redis":
            result = _check_redis_health(info)
        elif backend == "postgres":
            result = _check_postgres_health(info)
        else:
            return {
                "healthy": False,
                "degraded": False,
                "backend": backend,
                "message": f"Unknown backend: {backend}",
                "error": "Invalid configuration",
                "fallback_reason": None,
            }
        # Add degraded=False to normal health responses
        result["degraded"] = False
        result["fallback_reason"] = None
        return result
    except Exception as e:
        logger.exception("Checkpoint health check failed")
        return {
            "healthy": False,
            "degraded": False,
            "backend": backend,
            "message": "Health check failed",
            "error": str(e),
            "fallback_reason": None,
            **info,
        }


def _check_redis_health(info: dict[str, Any]) -> dict[str, Any]:
    """Check Redis checkpoint backend health."""
    import redis

    settings = get_settings()
    redis_host = settings.redis_host
    redis_port = settings.redis_port
    redis_db = settings.redis_db
    redis_password = settings.redis_password

    if redis_password:
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    client = redis.from_url(redis_url)
    client.ping()
    client.close()

    return {
        "healthy": True,
        "backend": "redis",
        "message": "Redis checkpoint backend healthy",
        "error": None,
        **info,
    }


def _check_postgres_health(info: dict[str, Any]) -> dict[str, Any]:
    """Check Postgres checkpoint backend health."""
    import psycopg2

    settings = get_settings()
    database_url = settings.database_url

    conn = psycopg2.connect(database_url)
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
    conn.close()

    return {
        "healthy": True,
        "backend": "postgres",
        "message": "PostgreSQL checkpoint backend healthy",
        "error": None,
        **info,
    }
