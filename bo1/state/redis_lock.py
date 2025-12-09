"""Redis-based distributed locking for session status updates.

Provides:
- acquire_lock: Acquire a distributed lock using SETNX
- release_lock: Release lock if still owned
- session_lock: Context manager for session status locks

Uses Redis SET with NX and EX options for atomic lock acquisition with TTL.
"""

import logging
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)


class LockTimeoutError(Exception):
    """Raised when lock acquisition times out."""

    pass


class LockNotAcquiredError(Exception):
    """Raised when lock could not be acquired."""

    pass


# Aliases for backward compatibility
LockTimeout = LockTimeoutError
LockNotAcquired = LockNotAcquiredError


def acquire_lock(
    redis_client: Any,
    key: str,
    ttl_seconds: int = 30,
) -> str | None:
    """Acquire a distributed lock using Redis SET NX EX.

    Args:
        redis_client: Redis client instance
        key: Lock key (e.g., "lock:session:123:status")
        ttl_seconds: Lock TTL in seconds (default 30)

    Returns:
        lock_id (UUID string) if acquired, None if lock already held

    Examples:
        >>> lock_id = acquire_lock(redis, "lock:session:abc:status")
        >>> if lock_id:
        ...     try:
        ...         # do work
        ...     finally:
        ...         release_lock(redis, "lock:session:abc:status", lock_id)
    """
    if redis_client is None:
        logger.debug("Redis unavailable, skipping lock acquisition")
        return None

    lock_id = str(uuid.uuid4())

    try:
        # SET key lock_id NX EX ttl - atomic acquire with TTL
        acquired = redis_client.set(key, lock_id, nx=True, ex=ttl_seconds)

        if acquired:
            logger.debug(f"[LOCK] Acquired lock: {key} (id={lock_id[:8]}..., ttl={ttl_seconds}s)")
            return lock_id
        else:
            logger.debug(f"[LOCK] Failed to acquire lock: {key} (already held)")
            return None

    except Exception as e:
        logger.warning(f"[LOCK] Error acquiring lock {key}: {e}")
        return None


def release_lock(redis_client: Any, key: str, lock_id: str) -> bool:
    """Release a distributed lock if still owned.

    Uses Lua script for atomic check-and-delete to prevent
    releasing locks owned by other processes.

    Args:
        redis_client: Redis client instance
        key: Lock key
        lock_id: Lock ID returned by acquire_lock

    Returns:
        True if lock was released, False if not owned or error
    """
    if redis_client is None:
        return True  # No Redis = no lock to release

    # Lua script: check ownership and delete atomically
    release_script = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    else
        return 0
    end
    """

    try:
        result = redis_client.eval(release_script, 1, key, lock_id)

        if result == 1:
            logger.debug(f"[LOCK] Released lock: {key} (id={lock_id[:8]}...)")
            return True
        else:
            logger.debug(f"[LOCK] Lock not owned or expired: {key}")
            return False

    except Exception as e:
        logger.warning(f"[LOCK] Error releasing lock {key}: {e}")
        return False


@contextmanager
def session_lock(
    redis_client: Any,
    session_id: str,
    timeout_seconds: float = 5.0,
    ttl_seconds: int = 30,
) -> Generator[str | None, None, None]:
    """Context manager for session status lock.

    Acquires lock on entry, releases on exit. Retries acquisition
    until timeout.

    Args:
        redis_client: Redis client instance
        session_id: Session identifier
        timeout_seconds: Max time to wait for lock (default 5s)
        ttl_seconds: Lock TTL in seconds (default 30s)

    Yields:
        lock_id if acquired, None if Redis unavailable

    Raises:
        LockTimeout: If lock cannot be acquired within timeout

    Examples:
        >>> with session_lock(redis, "bo1_abc123") as lock_id:
        ...     # session is locked, safe to update status
        ...     session_repository.update_status(session_id, "running")
    """
    key = f"lock:session:{session_id}:status"
    lock_id = None
    start_time = time.time()

    # Retry acquisition until timeout
    while time.time() - start_time < timeout_seconds:
        lock_id = acquire_lock(redis_client, key, ttl_seconds)

        if lock_id is not None:
            break

        # Redis unavailable - proceed without lock
        if redis_client is None:
            break

        # Wait before retry (exponential backoff capped at 0.5s)
        elapsed = time.time() - start_time
        wait_time = min(0.1 * (2 ** (elapsed / timeout_seconds)), 0.5)
        time.sleep(wait_time)

    if lock_id is None and redis_client is not None:
        raise LockTimeoutError(
            f"Could not acquire lock for session {session_id} within {timeout_seconds}s"
        )

    try:
        yield lock_id
    finally:
        if lock_id is not None:
            release_lock(redis_client, key, lock_id)
