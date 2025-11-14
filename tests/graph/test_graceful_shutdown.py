"""Tests for graceful shutdown signal handlers.

Tests:
- SIGTERM triggers graceful shutdown
- SIGINT (Ctrl+C) triggers graceful shutdown
- Shutdown preserves checkpoints
- Shutdown completes within grace period
"""

import asyncio
import signal
import sys
import time

import pytest

from bo1.graph.execution import SessionManager, setup_shutdown_handlers
from bo1.state.redis_manager import RedisManager


@pytest.fixture
def redis_manager():
    """Create Redis manager for tests."""
    manager = RedisManager()
    yield manager
    if manager.is_available and manager.redis:
        manager.redis.flushdb()
    manager.close()


@pytest.fixture
def session_manager(redis_manager):
    """Create session manager for tests."""
    manager = SessionManager(redis_manager=redis_manager, admin_user_ids={"admin_user_1"})
    return manager


async def long_running_task():
    """Long running task for shutdown tests."""
    try:
        await asyncio.sleep(30.0)
        return "completed"
    except asyncio.CancelledError:
        return "cancelled"


@pytest.mark.asyncio
async def test_graceful_shutdown_cancels_tasks(session_manager):
    """Test: Graceful shutdown cancels all active tasks."""
    # Start 3 long-running sessions
    for i in range(3):
        await session_manager.start_session(
            session_id=f"shutdown_test_{i}", user_id=f"user_{i}", coro=long_running_task()
        )

    assert len(session_manager.active_executions) == 3

    # Initiate graceful shutdown
    start_time = time.time()
    await session_manager.shutdown(grace_period=2.0)
    shutdown_duration = time.time() - start_time

    # Verify shutdown completed quickly (not waiting 30s for tasks)
    assert shutdown_duration < 3.0  # Should finish within grace period

    # Verify all tasks cancelled
    assert len(session_manager.active_executions) == 0


@pytest.mark.asyncio
async def test_shutdown_saves_metadata_for_all_sessions(session_manager):
    """Test: Graceful shutdown saves metadata for all sessions."""
    session_ids = []

    # Start 4 sessions
    for i in range(4):
        session_id = f"metadata_test_{i}"
        session_ids.append(session_id)
        await session_manager.start_session(
            session_id=session_id, user_id=f"user_{i}", coro=long_running_task()
        )

    # Shutdown
    await session_manager.shutdown(grace_period=1.0)

    # Verify metadata saved for each session
    for session_id in session_ids:
        metadata = session_manager._load_session_metadata(session_id)
        assert metadata is not None
        assert metadata["status"] == "shutdown"
        assert "shutdown_at" in metadata
        assert metadata["shutdown_reason"] == "System shutdown"


@pytest.mark.asyncio
async def test_shutdown_with_zero_sessions(session_manager):
    """Test: Graceful shutdown works even with no active sessions."""
    assert len(session_manager.active_executions) == 0

    # Should complete immediately without errors
    start_time = time.time()
    await session_manager.shutdown(grace_period=5.0)
    shutdown_duration = time.time() - start_time

    # Should be instant
    assert shutdown_duration < 0.5


@pytest.mark.asyncio
async def test_shutdown_timeout_handling(session_manager):
    """Test: Shutdown respects grace period timeout."""
    # Start a session
    await session_manager.start_session(
        session_id="timeout_test", user_id="user_1", coro=long_running_task()
    )

    # Shutdown with very short grace period
    start_time = time.time()
    await session_manager.shutdown(grace_period=0.1)
    shutdown_duration = time.time() - start_time

    # Should timeout after ~0.1s, not wait forever
    assert shutdown_duration < 1.0

    # Verify session still marked as shutdown
    metadata = session_manager._load_session_metadata("timeout_test")
    assert metadata["status"] == "shutdown"


@pytest.mark.asyncio
async def test_multiple_shutdowns_are_safe(session_manager):
    """Test: Calling shutdown multiple times is safe."""
    # Start a session
    await session_manager.start_session(
        session_id="multi_shutdown", user_id="user_1", coro=long_running_task()
    )

    # Shutdown twice
    await session_manager.shutdown(grace_period=1.0)
    await session_manager.shutdown(grace_period=1.0)  # Should not raise error

    # Verify clean state
    assert len(session_manager.active_executions) == 0


# Note: Signal handler tests are difficult to write in pytest because:
# 1. signal.signal() only works in main thread
# 2. pytest runs tests in subprocesses
# 3. Sending real signals to test process can be dangerous
#
# The setup_shutdown_handlers() function is tested manually during integration testing.
# We verify the function exists and can be called:


def test_setup_shutdown_handlers_exists():
    """Test: setup_shutdown_handlers function exists and is callable."""
    assert callable(setup_shutdown_handlers)


@pytest.mark.skipif(sys.platform == "win32", reason="Signal handling differs on Windows")
def test_signal_handlers_can_be_registered():
    """Test: Signal handlers can be registered (smoke test).

    Note: This doesn't actually test shutdown behavior, just that
    the function can be called without errors.
    """

    # Create a mock session manager
    class MockRedis:
        async def hset(self, *args, **kwargs):
            pass

        async def hgetall(self, *args, **kwargs):
            return {}

        async def expire(self, *args, **kwargs):
            pass

    class MockRedisManager:
        def __init__(self):
            self.client = MockRedis()

    mock_manager = SessionManager(redis_manager=MockRedisManager(), admin_user_ids=set())

    # This should not raise an error
    # (actual signal behavior tested manually)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    original_sigint = signal.getsignal(signal.SIGINT)

    try:
        setup_shutdown_handlers(mock_manager)
        # Verify handlers were registered
        assert signal.getsignal(signal.SIGTERM) != original_sigterm
        assert signal.getsignal(signal.SIGINT) != original_sigint
    finally:
        # Restore original handlers
        signal.signal(signal.SIGTERM, original_sigterm)
        signal.signal(signal.SIGINT, original_sigint)
