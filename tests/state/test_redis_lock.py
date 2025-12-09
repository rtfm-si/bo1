"""Tests for Redis-based distributed locking.

Validates:
- acquire_lock success and conflict scenarios
- release_lock ownership verification
- session_lock context manager with timeout
- Graceful handling when Redis unavailable
"""

from unittest.mock import MagicMock

import pytest

from bo1.state.redis_lock import (
    LockNotAcquired,
    LockTimeout,
    acquire_lock,
    release_lock,
    session_lock,
)


class TestAcquireLock:
    """Test acquire_lock function."""

    def test_acquire_lock_success(self):
        """Lock acquired when key not held."""
        redis_client = MagicMock()
        redis_client.set.return_value = True

        lock_id = acquire_lock(redis_client, "lock:test:key", ttl_seconds=30)

        assert lock_id is not None
        assert len(lock_id) == 36  # UUID format
        redis_client.set.assert_called_once()
        call_args = redis_client.set.call_args
        assert call_args[0][0] == "lock:test:key"
        assert call_args[1]["nx"] is True
        assert call_args[1]["ex"] == 30

    def test_acquire_lock_conflict(self):
        """Lock not acquired when key already held."""
        redis_client = MagicMock()
        redis_client.set.return_value = False  # Already held

        lock_id = acquire_lock(redis_client, "lock:test:key")

        assert lock_id is None
        redis_client.set.assert_called_once()

    def test_acquire_lock_redis_unavailable(self):
        """Returns None when Redis client is None."""
        lock_id = acquire_lock(None, "lock:test:key")

        assert lock_id is None

    def test_acquire_lock_redis_error(self):
        """Returns None on Redis error."""
        redis_client = MagicMock()
        redis_client.set.side_effect = Exception("Connection refused")

        lock_id = acquire_lock(redis_client, "lock:test:key")

        assert lock_id is None

    def test_acquire_lock_custom_ttl(self):
        """Custom TTL is passed to Redis."""
        redis_client = MagicMock()
        redis_client.set.return_value = True

        acquire_lock(redis_client, "lock:test:key", ttl_seconds=60)

        call_args = redis_client.set.call_args
        assert call_args[1]["ex"] == 60


class TestReleaseLock:
    """Test release_lock function."""

    def test_release_lock_success(self):
        """Lock released when still owned."""
        redis_client = MagicMock()
        redis_client.eval.return_value = 1  # Successfully deleted

        result = release_lock(redis_client, "lock:test:key", "lock-id-123")

        assert result is True
        redis_client.eval.assert_called_once()

    def test_release_lock_not_owned(self):
        """Lock not released when not owned."""
        redis_client = MagicMock()
        redis_client.eval.return_value = 0  # Not owned

        result = release_lock(redis_client, "lock:test:key", "wrong-lock-id")

        assert result is False

    def test_release_lock_redis_unavailable(self):
        """Returns True when Redis client is None (no lock to release)."""
        result = release_lock(None, "lock:test:key", "lock-id-123")

        assert result is True

    def test_release_lock_redis_error(self):
        """Returns False on Redis error."""
        redis_client = MagicMock()
        redis_client.eval.side_effect = Exception("Connection refused")

        result = release_lock(redis_client, "lock:test:key", "lock-id-123")

        assert result is False

    def test_release_lock_uses_lua_script(self):
        """Verify Lua script is used for atomic check-and-delete."""
        redis_client = MagicMock()
        redis_client.eval.return_value = 1

        release_lock(redis_client, "lock:test:key", "lock-id-123")

        call_args = redis_client.eval.call_args
        lua_script = call_args[0][0]
        assert "GET" in lua_script
        assert "DEL" in lua_script
        assert call_args[0][1] == 1  # Number of keys
        assert call_args[0][2] == "lock:test:key"
        assert call_args[0][3] == "lock-id-123"


class TestSessionLock:
    """Test session_lock context manager."""

    def test_session_lock_acquires_and_releases(self):
        """Lock acquired on enter, released on exit."""
        redis_client = MagicMock()
        redis_client.set.return_value = True
        redis_client.eval.return_value = 1

        with session_lock(redis_client, "session-123") as lock_id:
            assert lock_id is not None

        # Verify release was called
        redis_client.eval.assert_called_once()

    def test_session_lock_key_format(self):
        """Lock key follows expected format."""
        redis_client = MagicMock()
        redis_client.set.return_value = True
        redis_client.eval.return_value = 1

        with session_lock(redis_client, "bo1_abc123"):
            pass

        call_args = redis_client.set.call_args
        assert call_args[0][0] == "lock:session:bo1_abc123:status"

    def test_session_lock_timeout_raises(self):
        """Raises LockTimeout when cannot acquire within timeout."""
        redis_client = MagicMock()
        redis_client.set.return_value = False  # Always fails

        with pytest.raises(LockTimeout) as exc_info:
            with session_lock(redis_client, "session-123", timeout_seconds=0.2):
                pass

        assert "session-123" in str(exc_info.value)

    def test_session_lock_redis_unavailable_proceeds(self):
        """Proceeds without lock when Redis unavailable."""
        with session_lock(None, "session-123") as lock_id:
            assert lock_id is None
        # Should not raise, just proceed without lock

    def test_session_lock_releases_on_exception(self):
        """Lock released even when exception raised in context."""
        redis_client = MagicMock()
        redis_client.set.return_value = True
        redis_client.eval.return_value = 1

        with pytest.raises(ValueError):
            with session_lock(redis_client, "session-123"):
                raise ValueError("Test error")

        # Verify release was still called
        redis_client.eval.assert_called_once()

    def test_session_lock_custom_ttl(self):
        """Custom TTL is passed through."""
        redis_client = MagicMock()
        redis_client.set.return_value = True
        redis_client.eval.return_value = 1

        with session_lock(redis_client, "session-123", ttl_seconds=60):
            pass

        call_args = redis_client.set.call_args
        assert call_args[1]["ex"] == 60

    def test_session_lock_retries_until_acquired(self):
        """Retries lock acquisition until success."""
        redis_client = MagicMock()
        # Fail twice, succeed on third attempt
        redis_client.set.side_effect = [False, False, True]
        redis_client.eval.return_value = 1

        with session_lock(redis_client, "session-123", timeout_seconds=2.0) as lock_id:
            assert lock_id is not None

        assert redis_client.set.call_count == 3


class TestLockExceptions:
    """Test lock exception classes."""

    def test_lock_timeout_message(self):
        """LockTimeout has descriptive message."""
        exc = LockTimeout("Could not acquire lock for session abc")
        assert "session abc" in str(exc)

    def test_lock_not_acquired_exists(self):
        """LockNotAcquired exception exists and can be raised."""
        with pytest.raises(LockNotAcquired):
            raise LockNotAcquired("Lock unavailable")
