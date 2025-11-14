"""Tests for session kill switches and graceful shutdown.

Tests:
- User can kill own session
- User CANNOT kill other users' sessions
- Admin can kill any session
- Admin can kill all sessions
- Graceful shutdown preserves checkpoints
- Audit trail logged for all kills
"""

import asyncio

import pytest

from bo1.graph.execution import PermissionError, SessionManager
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
    """Create session manager with test admin user."""
    manager = SessionManager(redis_manager=redis_manager, admin_user_ids={"admin_user_1"})
    return manager


async def dummy_task(duration: float = 10.0):
    """Dummy async task for testing."""
    try:
        await asyncio.sleep(duration)
        return "completed"
    except asyncio.CancelledError:
        return "cancelled"


@pytest.mark.asyncio
async def test_user_can_kill_own_session(session_manager):
    """Test: User can kill their own session."""
    # Start a session
    session_id = "test_session_1"
    user_id = "user_1"

    task = await session_manager.start_session(
        session_id=session_id, user_id=user_id, coro=dummy_task(10.0)
    )

    # Verify session is running
    assert session_id in session_manager.active_executions
    assert not task.done()

    # Kill the session (same user)
    result = await session_manager.kill_session(
        session_id=session_id, user_id=user_id, reason="User requested termination"
    )

    # Verify kill succeeded
    assert result is True
    assert session_id not in session_manager.active_executions

    # Wait a bit for task to be cancelled
    await asyncio.sleep(0.1)
    assert task.done()

    # Verify metadata updated
    metadata = session_manager._load_session_metadata(session_id)
    assert metadata is not None
    assert metadata["status"] == "killed"
    assert metadata["killed_by"] == user_id
    assert metadata["kill_reason"] == "User requested termination"
    assert metadata["admin_kill"] == "False"


@pytest.mark.asyncio
async def test_user_cannot_kill_other_users_sessions(session_manager):
    """Test: User CANNOT kill sessions owned by other users."""
    # Start a session for user_1
    session_id = "test_session_2"
    user_1 = "user_1"
    user_2 = "user_2"

    await session_manager.start_session(
        session_id=session_id, user_id=user_1, coro=dummy_task(10.0)
    )

    # Verify session is running
    assert session_id in session_manager.active_executions

    # Attempt to kill as user_2 (should fail)
    with pytest.raises(PermissionError, match="cannot kill session"):
        await session_manager.kill_session(
            session_id=session_id, user_id=user_2, reason="Unauthorized attempt"
        )

    # Verify session is still running
    assert session_id in session_manager.active_executions


@pytest.mark.asyncio
async def test_admin_can_kill_any_session(session_manager):
    """Test: Admin can kill any session (no ownership check)."""
    # Start a session for user_1
    session_id = "test_session_3"
    user_id = "user_1"
    admin_id = "admin_user_1"

    await session_manager.start_session(
        session_id=session_id, user_id=user_id, coro=dummy_task(10.0)
    )

    # Verify session is running
    assert session_id in session_manager.active_executions

    # Admin kills the session (no ownership check)
    result = await session_manager.admin_kill_session(
        session_id=session_id, admin_user_id=admin_id, reason="Admin intervention"
    )

    # Verify kill succeeded
    assert result is True
    assert session_id not in session_manager.active_executions

    # Verify metadata shows admin kill
    metadata = session_manager._load_session_metadata(session_id)
    assert metadata is not None
    assert metadata["status"] == "killed"
    assert metadata["killed_by"] == admin_id
    assert metadata["kill_reason"] == "Admin intervention"
    assert metadata["admin_kill"] == "True"


@pytest.mark.asyncio
async def test_non_admin_cannot_use_admin_kill(session_manager):
    """Test: Non-admin user cannot use admin kill switch."""
    # Start a session
    session_id = "test_session_4"
    user_id = "user_1"
    non_admin = "user_2"

    await session_manager.start_session(
        session_id=session_id, user_id=user_id, coro=dummy_task(10.0)
    )

    # Non-admin attempts admin kill
    with pytest.raises(PermissionError, match="is not an admin"):
        await session_manager.admin_kill_session(
            session_id=session_id, admin_user_id=non_admin, reason="Unauthorized admin attempt"
        )

    # Verify session is still running
    assert session_id in session_manager.active_executions


@pytest.mark.asyncio
async def test_admin_can_kill_all_sessions(session_manager):
    """Test: Admin can kill all active sessions."""
    admin_id = "admin_user_1"

    # Start 3 sessions for different users
    sessions = [
        ("session_1", "user_1"),
        ("session_2", "user_2"),
        ("session_3", "user_3"),
    ]

    for session_id, user_id in sessions:
        await session_manager.start_session(
            session_id=session_id, user_id=user_id, coro=dummy_task(10.0)
        )

    # Verify all 3 sessions are running
    assert len(session_manager.active_executions) == 3

    # Admin kills all sessions
    killed_count = await session_manager.admin_kill_all_sessions(
        admin_user_id=admin_id, reason="System maintenance"
    )

    # Verify all sessions killed
    assert killed_count == 3
    assert len(session_manager.active_executions) == 0

    # Verify metadata for each session
    for session_id, _ in sessions:
        metadata = session_manager._load_session_metadata(session_id)
        assert metadata is not None
        assert metadata["status"] == "killed"
        assert metadata["killed_by"] == admin_id
        assert metadata["kill_reason"] == "System maintenance"
        assert metadata["admin_kill"] == "True"


@pytest.mark.asyncio
async def test_non_admin_cannot_kill_all(session_manager):
    """Test: Non-admin user cannot kill all sessions."""
    non_admin = "user_1"

    # Start 2 sessions
    await session_manager.start_session("session_1", "user_1", dummy_task(10.0))
    await session_manager.start_session("session_2", "user_2", dummy_task(10.0))

    # Non-admin attempts kill all
    with pytest.raises(PermissionError, match="is not an admin"):
        await session_manager.admin_kill_all_sessions(
            admin_user_id=non_admin, reason="Unauthorized attempt"
        )

    # Verify sessions still running
    assert len(session_manager.active_executions) == 2


@pytest.mark.asyncio
async def test_graceful_shutdown_preserves_metadata(session_manager):
    """Test: Graceful shutdown saves metadata for all sessions."""
    # Start 2 sessions
    await session_manager.start_session("session_1", "user_1", dummy_task(10.0))
    await session_manager.start_session("session_2", "user_2", dummy_task(10.0))

    assert len(session_manager.active_executions) == 2

    # Graceful shutdown
    await session_manager.shutdown(grace_period=1.0)

    # Verify all sessions terminated
    assert len(session_manager.active_executions) == 0

    # Verify metadata saved
    for session_id in ["session_1", "session_2"]:
        metadata = session_manager._load_session_metadata(session_id)
        assert metadata is not None
        assert metadata["status"] == "shutdown"
        assert "shutdown_at" in metadata
        assert metadata["shutdown_reason"] == "System shutdown"


@pytest.mark.asyncio
async def test_kill_nonexistent_session_returns_false(session_manager):
    """Test: Killing non-existent session returns False."""
    result = await session_manager.kill_session(
        session_id="nonexistent", user_id="user_1", reason="Test"
    )
    assert result is False


@pytest.mark.asyncio
async def test_admin_kill_nonexistent_session_returns_false(session_manager):
    """Test: Admin killing non-existent session returns False."""
    result = await session_manager.admin_kill_session(
        session_id="nonexistent", admin_user_id="admin_user_1", reason="Test"
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_admin_check(session_manager):
    """Test: is_admin() correctly identifies admin users."""
    assert session_manager.is_admin("admin_user_1") is True
    assert session_manager.is_admin("regular_user") is False


@pytest.mark.asyncio
async def test_session_metadata_persistence(session_manager):
    """Test: Session metadata persists correctly in Redis."""
    session_id = "test_metadata_session"
    user_id = "user_1"

    # Start session
    await session_manager.start_session(
        session_id=session_id, user_id=user_id, coro=dummy_task(10.0)
    )

    # Load metadata
    metadata = session_manager._load_session_metadata(session_id)
    assert metadata is not None
    assert metadata["user_id"] == user_id
    assert metadata["status"] == "running"
    assert "started_at" in metadata

    # Update metadata
    session_manager._save_session_metadata(session_id, {"custom_field": "test_value"})

    # Verify merge
    metadata = session_manager._load_session_metadata(session_id)
    assert metadata["custom_field"] == "test_value"
    assert metadata["user_id"] == user_id  # Original field preserved


@pytest.mark.asyncio
async def test_concurrent_session_management(session_manager):
    """Test: Can manage multiple concurrent sessions."""
    # Start 5 sessions concurrently
    tasks = []
    for i in range(5):
        task = session_manager.start_session(
            session_id=f"concurrent_session_{i}", user_id=f"user_{i}", coro=dummy_task(10.0)
        )
        tasks.append(task)

    await asyncio.gather(*tasks)

    # Verify all sessions running
    assert len(session_manager.active_executions) == 5

    # Kill 3 sessions concurrently
    kill_tasks = []
    for i in range(3):
        task = session_manager.kill_session(
            session_id=f"concurrent_session_{i}", user_id=f"user_{i}", reason="Test"
        )
        kill_tasks.append(task)

    results = await asyncio.gather(*kill_tasks)
    assert all(results)

    # Verify 2 sessions still running
    assert len(session_manager.active_executions) == 2
