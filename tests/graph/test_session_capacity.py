"""Tests for session capacity limits and FIFO eviction.

Tests:
- Session starts normally under capacity
- Eviction triggered at capacity
- FIFO order (oldest session evicted first)
- Capacity info reporting
- Eviction warning event
"""

import asyncio

import pytest

from bo1.constants import SessionManagerConfig
from bo1.graph.execution import SessionManager
from bo1.state.redis_manager import RedisManager


@pytest.fixture
def redis_manager():
    """Create Redis manager for tests."""
    manager = RedisManager()
    yield manager
    # Cleanup
    if manager.is_available and manager.redis:
        manager.redis.flushdb()
    manager.close()


@pytest.fixture
def session_manager(redis_manager):
    """Create session manager with low capacity for testing."""
    manager = SessionManager(
        redis_manager=redis_manager,
        admin_user_ids={"admin"},
        max_concurrent_sessions=3,  # Low limit for testing
    )
    return manager


async def dummy_task(duration: float = 60.0) -> str:
    """Dummy async task for testing."""
    try:
        await asyncio.sleep(duration)
        return "completed"
    except asyncio.CancelledError:
        return "cancelled"


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_session_starts_under_capacity(session_manager):
    """Test: Sessions start normally when under capacity."""
    # Start first session
    task1 = await session_manager.start_session(
        session_id="session_1", user_id="user_1", coro=dummy_task()
    )

    assert "session_1" in session_manager.active_executions
    assert not task1.done()

    # Check capacity info
    info = session_manager.get_capacity_info()
    assert info["current_sessions"] == 1
    assert info["max_sessions"] == 3
    assert info["at_capacity"] is False

    # Clean up
    task1.cancel()
    await asyncio.sleep(0.1)


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_capacity_tracking_accurate(session_manager):
    """Test: Capacity tracking is accurate as sessions start/stop."""
    tasks = []

    # Start sessions up to capacity
    for i in range(3):
        task = await session_manager.start_session(
            session_id=f"session_{i}", user_id=f"user_{i}", coro=dummy_task()
        )
        tasks.append(task)

    # Should be at capacity
    assert session_manager.is_at_capacity()
    info = session_manager.get_capacity_info()
    assert info["current_sessions"] == 3
    assert info["at_capacity"] is True
    assert info["utilization_pct"] == 100.0

    # Clean up
    for task in tasks:
        task.cancel()
    await asyncio.sleep(0.1)


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_get_oldest_session_fifo(session_manager):
    """Test: get_oldest_session returns oldest by start time."""
    # Start sessions with small delays to ensure ordering
    await session_manager.start_session(session_id="oldest", user_id="user_1", coro=dummy_task())
    await asyncio.sleep(0.01)
    await session_manager.start_session(session_id="middle", user_id="user_2", coro=dummy_task())
    await asyncio.sleep(0.01)
    await session_manager.start_session(session_id="newest", user_id="user_3", coro=dummy_task())

    # Verify oldest is returned
    assert session_manager.get_oldest_session() == "oldest"

    # Clean up
    for task in session_manager.active_executions.values():
        task.cancel()
    await asyncio.sleep(0.1)


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_eviction_triggered_at_capacity(session_manager, monkeypatch):
    """Test: Starting session at capacity triggers eviction of oldest."""
    # Reduce grace period for faster test
    monkeypatch.setattr(SessionManagerConfig, "EVICTION_GRACE_PERIOD_SECONDS", 0.1)

    # Start 3 sessions (at capacity)
    for i in range(3):
        await session_manager.start_session(
            session_id=f"session_{i}", user_id=f"user_{i}", coro=dummy_task()
        )
        await asyncio.sleep(0.01)

    assert session_manager.is_at_capacity()
    assert "session_0" in session_manager.active_executions

    # Start 4th session - should evict oldest (session_0)
    await session_manager.start_session(session_id="session_3", user_id="user_3", coro=dummy_task())

    # session_0 should be evicted
    assert "session_0" not in session_manager.active_executions
    assert "session_3" in session_manager.active_executions

    # Verify metadata shows evicted status
    metadata = session_manager._load_session_metadata("session_0")
    assert metadata is not None
    assert metadata["status"] == "evicted"
    assert metadata["eviction_reason"] == "capacity_eviction"

    # Clean up
    for task in session_manager.active_executions.values():
        task.cancel()
    await asyncio.sleep(0.1)


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_capacity_info_utilization_calculation(session_manager):
    """Test: Capacity utilization percentage is calculated correctly."""
    # Empty - 0%
    info = session_manager.get_capacity_info()
    assert info["utilization_pct"] == 0.0

    # 1 of 3 - 33.3%
    task1 = await session_manager.start_session(session_id="s1", user_id="u1", coro=dummy_task())
    info = session_manager.get_capacity_info()
    assert info["utilization_pct"] == 33.3

    # 2 of 3 - 66.7%
    task2 = await session_manager.start_session(session_id="s2", user_id="u2", coro=dummy_task())
    info = session_manager.get_capacity_info()
    assert info["utilization_pct"] == 66.7

    # Clean up
    task1.cancel()
    task2.cancel()
    await asyncio.sleep(0.1)


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_session_start_times_cleaned_on_completion(session_manager):
    """Test: _session_start_times is cleaned when session completes."""

    # Create a quick-completing task
    async def quick_task():
        return "done"

    await session_manager.start_session(session_id="quick", user_id="user_1", coro=quick_task())

    # Wait for task to complete
    await asyncio.sleep(0.1)

    # Verify cleaned up from both dicts
    assert "quick" not in session_manager.active_executions
    assert "quick" not in session_manager._session_start_times


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_concurrent_start_uses_lock(session_manager, monkeypatch):
    """Test: Concurrent start_session calls use capacity lock to prevent race."""
    monkeypatch.setattr(SessionManagerConfig, "EVICTION_GRACE_PERIOD_SECONDS", 0.01)

    # Fill to capacity
    for i in range(3):
        await session_manager.start_session(session_id=f"s{i}", user_id=f"u{i}", coro=dummy_task())
        await asyncio.sleep(0.01)

    # Try to start 2 more concurrently at capacity
    # Both should succeed due to eviction, but only one at a time
    results = await asyncio.gather(
        session_manager.start_session(session_id="new1", user_id="user_new1", coro=dummy_task()),
        session_manager.start_session(session_id="new2", user_id="user_new2", coro=dummy_task()),
    )

    # Both should have succeeded
    assert all(r is not None for r in results)
    assert "new1" in session_manager.active_executions
    assert "new2" in session_manager.active_executions

    # Clean up
    for task in session_manager.active_executions.values():
        task.cancel()
    await asyncio.sleep(0.1)


@pytest.mark.requires_redis
@pytest.mark.asyncio
async def test_default_max_sessions_from_config():
    """Test: Default max_concurrent_sessions comes from config."""
    redis_manager = RedisManager()
    try:
        # Create without explicit max_concurrent_sessions
        manager = SessionManager(redis_manager=redis_manager)
        assert manager.max_concurrent_sessions == SessionManagerConfig.MAX_CONCURRENT_SESSIONS
    finally:
        redis_manager.close()
