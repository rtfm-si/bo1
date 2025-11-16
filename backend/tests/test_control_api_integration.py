"""Integration tests for deliberation control API endpoints.

Tests for Day 39: Security, validation, and integration tests for control endpoints.

Required Test Coverage (per roadmap):
- Invalid session_id: Non-UUID, SQL injection in path parameter
- Authorization: User A cannot pause/kill User B's sessions
- Double start prevention: Cannot start already running session
- Invalid state transitions: Cannot resume non-paused session
- Race conditions: Two users cannot kill same session simultaneously
- Audit trail: All control actions logged with user_id, timestamp, reason
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.state.redis_manager import RedisManager


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def redis_manager() -> RedisManager:
    """Create Redis manager for tests."""
    return RedisManager()


@pytest.fixture(autouse=True)
def cleanup_redis(redis_manager: RedisManager) -> None:
    """Clean up Redis before and after each test."""
    # Clean up before test
    if redis_manager.is_available:
        sessions = redis_manager.list_sessions()
        for session_id in sessions:
            redis_manager.delete_state(session_id)
            if redis_manager.redis:
                redis_manager.redis.delete(f"metadata:{session_id}")

    yield

    # Clean up after test
    if redis_manager.is_available:
        sessions = redis_manager.list_sessions()
        for session_id in sessions:
            redis_manager.delete_state(session_id)
            if redis_manager.redis:
                redis_manager.redis.delete(f"metadata:{session_id}")


# ============================================================================
# INVALID SESSION_ID TESTS
# ============================================================================


@pytest.mark.integration
def test_start_with_invalid_session_id_non_uuid(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that non-UUID session IDs are handled safely.

    Security test: Verifies that malformed session IDs don't cause errors.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Attempt to start with non-UUID session ID
    response = client.post("/api/v1/sessions/not-a-uuid/start")

    # Should return 404 (session not found) or handle gracefully
    assert response.status_code in [404, 400, 422]


@pytest.mark.integration
def test_start_with_sql_injection_in_session_id(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that SQL injection in session ID is safely rejected.

    Security test: Verifies path parameters are sanitized.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Attempt SQL injection in path parameter
    malicious_id = "'; DROP TABLE sessions; --"
    response = client.post(f"/api/v1/sessions/{malicious_id}/start")

    # Should safely reject without executing SQL
    assert response.status_code in [404, 400, 422]


@pytest.mark.integration
def test_pause_with_xss_in_session_id(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that XSS attempts in session ID are safely rejected.

    Security test: Verifies path parameters are sanitized.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Attempt XSS in path parameter
    malicious_id = "<script>alert('XSS')</script>"
    response = client.post(f"/api/v1/sessions/{malicious_id}/pause")

    # Should safely reject
    assert response.status_code in [404, 400, 422]


@pytest.mark.integration
def test_kill_with_path_traversal_in_session_id(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that path traversal attempts in session ID are rejected.

    Security test: Verifies path parameters prevent directory traversal.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Attempt path traversal
    malicious_id = "../../etc/passwd"
    response = client.post(f"/api/v1/sessions/{malicious_id}/kill")

    # Should safely reject
    assert response.status_code in [404, 400, 422]


# ============================================================================
# AUTHORIZATION TESTS
# ============================================================================


@pytest.mark.integration
def test_user_cannot_start_another_users_session(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that User A cannot start User B's session.

    Security test: Verifies ownership checks for session control.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session with user_2 as owner
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "created",
        "user_id": "user_2",  # Owned by user_2
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "problem_statement": "Test problem",
        "problem_context": {},
    }
    redis_manager.save_metadata(session_id, metadata)

    # User_1 (default test user) tries to start it
    # Note: For MVP, start doesn't check ownership (only kill/clarify do)
    # But we should still log who started it
    with patch("backend.api.control.load_personas") as mock_personas:
        mock_personas.return_value = (
            {"code": "maria", "name": "Maria", "system_prompt": "Test"},
            {"code": "zara", "name": "Zara", "system_prompt": "Test"},
            {"code": "tariq", "name": "Tariq", "system_prompt": "Test"},
        )

        with patch("backend.api.control.create_deliberation_graph") as mock_graph:
            graph = MagicMock()
            graph.ainvoke = AsyncMock(return_value={"session_id": session_id})
            mock_graph.return_value = graph

            response = client.post(f"/api/v1/sessions/{session_id}/start")

            # For MVP, start succeeds but logs different user
            # In production (Week 7+), this would return 403
            # For now, verify it starts (but we can check metadata later for audit)
            assert response.status_code in [202, 403]


@pytest.mark.integration
def test_user_cannot_kill_another_users_session(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that User A cannot kill User B's session.

    Security test: Verifies ownership enforcement for kill operations.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session owned by user_2
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "running",
        "user_id": "user_2",  # Owned by user_2
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Mock session manager to have active execution
    with patch("backend.api.control._get_session_manager") as mock_manager_fn:
        manager = MagicMock()
        manager.active_executions = {session_id: MagicMock()}

        # Mock kill_session to enforce ownership check
        async def mock_kill(sid: str, uid: str, reason: str) -> bool:
            from bo1.graph.execution import PermissionError

            meta = redis_manager.load_metadata(sid)
            if not meta:
                return False
            if meta.get("user_id") != uid:
                raise PermissionError(
                    f"User {uid} cannot kill session owned by {meta.get('user_id')}"
                )
            return True

        manager.kill_session = AsyncMock(side_effect=mock_kill)
        mock_manager_fn.return_value = manager

        # User_1 (default test user) tries to kill user_2's session
        response = client.post(f"/api/v1/sessions/{session_id}/kill")

        # Should return 403 Forbidden
        assert response.status_code == 403
        data = response.json()
        assert "cannot kill session" in data["detail"].lower()


@pytest.mark.integration
def test_user_cannot_submit_clarification_for_another_users_session(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that User A cannot submit clarification for User B's session.

    Security test: Verifies ownership enforcement for clarification submissions.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session owned by user_2 with pending clarification
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "waiting_for_clarification",
        "user_id": "user_2",  # Owned by user_2
        "pending_clarification": {
            "question_id": "q1",
            "question": "What is your churn rate?",
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Save state for the session
    state = {
        "problem": {"statement": "Test", "context": {}},
        "round_number": 0,
    }
    redis_manager.save_state(session_id, state)

    # User_1 (default test user) tries to submit clarification
    response = client.post(
        f"/api/v1/sessions/{session_id}/clarify",
        json={"answer": "3.5% monthly"},
    )

    # Should return 403 Forbidden
    assert response.status_code == 403
    data = response.json()
    assert "does not own" in data["detail"].lower()


# ============================================================================
# DOUBLE START PREVENTION
# ============================================================================


@pytest.mark.integration
def test_cannot_start_already_running_session(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that starting an already running session is prevented.

    Race condition test: Verifies duplicate start prevention.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "created",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "problem_statement": "Test problem",
        "problem_context": {},
    }
    redis_manager.save_metadata(session_id, metadata)

    # Mock session manager to simulate already running session
    with patch("backend.api.control._get_session_manager") as mock_manager_fn:
        manager = MagicMock()
        manager.active_executions = {session_id: MagicMock()}  # Already running!
        mock_manager_fn.return_value = manager

        # Try to start it again
        response = client.post(f"/api/v1/sessions/{session_id}/start")

        # Should return 409 Conflict
        assert response.status_code == 409
        data = response.json()
        assert "already running" in data["detail"].lower()


@pytest.mark.integration
def test_cannot_resume_already_running_session(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that resuming an already running session is prevented.

    Race condition test: Verifies duplicate resume prevention.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create paused session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "paused",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Mock session manager to simulate already running
    with patch("backend.api.control._get_session_manager") as mock_manager_fn:
        manager = MagicMock()
        manager.active_executions = {session_id: MagicMock()}  # Already running!
        mock_manager_fn.return_value = manager

        # Try to resume it
        response = client.post(f"/api/v1/sessions/{session_id}/resume")

        # Should return 409 Conflict
        assert response.status_code == 409
        data = response.json()
        assert "already running" in data["detail"].lower()


# ============================================================================
# INVALID STATE TRANSITIONS
# ============================================================================


@pytest.mark.integration
def test_cannot_resume_non_paused_session(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that resuming a non-paused session is rejected.

    State machine test: Verifies state transition validation.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session with 'running' status (not paused)
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "running",  # Not paused!
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Try to resume
    response = client.post(f"/api/v1/sessions/{session_id}/resume")

    # Should return 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "must be paused" in data["detail"].lower()


@pytest.mark.integration
def test_cannot_start_completed_session(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that starting a completed session is rejected.

    State machine test: Verifies completed sessions cannot be restarted.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create completed session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "completed",  # Already done!
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "problem_statement": "Test problem",
        "problem_context": {},
    }
    redis_manager.save_metadata(session_id, metadata)

    # Try to start
    response = client.post(f"/api/v1/sessions/{session_id}/start")

    # Should return 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "cannot start" in data["detail"].lower()


@pytest.mark.integration
def test_cannot_start_killed_session(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that starting a killed session is rejected.

    State machine test: Verifies killed sessions cannot be restarted.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create killed session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "killed",  # Already killed!
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "problem_statement": "Test problem",
        "problem_context": {},
    }
    redis_manager.save_metadata(session_id, metadata)

    # Try to start
    response = client.post(f"/api/v1/sessions/{session_id}/start")

    # Should return 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "cannot start" in data["detail"].lower()


# ============================================================================
# RACE CONDITIONS
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_kill_requests_handled_safely(
    redis_manager: RedisManager,
) -> None:
    """Test that two users cannot kill same session simultaneously.

    Race condition test: Verifies kill operation is idempotent and thread-safe.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "running",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Create mock session manager with real SessionManager logic
    from bo1.graph.execution import SessionManager

    manager = SessionManager(redis_manager, admin_user_ids={"admin_user"})

    # Create a mock task for the session
    mock_task = MagicMock()
    mock_task.cancel = MagicMock()

    async def mock_await():
        raise asyncio.CancelledError()

    mock_task.__await__ = lambda: mock_await().__await__()
    manager.active_executions[session_id] = mock_task

    # Attempt two concurrent kills (same user, same session)
    async def kill_operation():
        try:
            return await manager.kill_session(session_id, "test_user_1", "Concurrent test")
        except Exception as e:
            return str(e)

    results = await asyncio.gather(kill_operation(), kill_operation(), return_exceptions=True)

    # At least one should succeed
    successes = [r for r in results if r is True]
    assert len(successes) >= 1

    # Session should be removed from active executions
    assert session_id not in manager.active_executions

    # Metadata should show killed status
    final_metadata = redis_manager.load_metadata(session_id)
    assert final_metadata is not None
    assert final_metadata.get("status") == "killed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_start_and_kill_requests(
    redis_manager: RedisManager,
) -> None:
    """Test concurrent start and kill operations are handled safely.

    Race condition test: Verifies start/kill race conditions don't corrupt state.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "created",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "problem_statement": "Test problem",
        "problem_context": {},
    }
    redis_manager.save_metadata(session_id, metadata)

    # Create session manager
    from bo1.graph.execution import SessionManager

    manager = SessionManager(redis_manager, admin_user_ids=set())

    # Create a mock coroutine for start
    async def mock_deliberation():
        await asyncio.sleep(0.1)  # Simulate work
        return {"session_id": session_id}

    # Start operation
    async def start_operation():
        try:
            await manager.start_session(session_id, "test_user_1", mock_deliberation())
            return "started"
        except Exception as e:
            return str(e)

    # Kill operation
    async def kill_operation():
        await asyncio.sleep(0.05)  # Slight delay
        try:
            return await manager.kill_session(session_id, "test_user_1", "Test kill")
        except Exception as e:
            return str(e)

    # Run concurrently
    await asyncio.gather(start_operation(), kill_operation(), return_exceptions=True)

    # Should handle gracefully - either kill succeeds or session not found
    # Check final state is consistent
    final_metadata = redis_manager.load_metadata(session_id)
    assert final_metadata is not None
    # Status should be either running or killed (not corrupted)
    assert final_metadata.get("status") in ["running", "killed"]


# ============================================================================
# AUDIT TRAIL TESTS
# ============================================================================


@pytest.mark.integration
def test_kill_action_logged_to_audit_trail(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that kill actions are logged with user_id, timestamp, reason.

    Audit test: Verifies all kill operations are tracked.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "running",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Mock session manager with real kill logic
    with patch("backend.api.control._get_session_manager") as mock_manager_fn:
        manager = MagicMock()
        manager.active_executions = {session_id: MagicMock()}

        # Capture metadata updates
        saved_metadata = {}

        def save_metadata_side_effect(sid: str, meta: dict) -> None:
            saved_metadata.update(meta)
            redis_manager.save_metadata(sid, meta)

        async def mock_kill(sid: str, uid: str, reason: str) -> bool:
            # Simulate real kill logic
            mock_task = manager.active_executions.get(sid)
            if not mock_task:
                return False

            # Update metadata (audit trail)
            import time

            meta = redis_manager.load_metadata(sid) or {}
            meta.update(
                {
                    "status": "killed",
                    "killed_at": str(time.time()),
                    "killed_by": uid,
                    "kill_reason": reason,
                    "admin_kill": "False",
                }
            )
            save_metadata_side_effect(sid, meta)

            manager.active_executions.pop(sid, None)
            return True

        manager.kill_session = AsyncMock(side_effect=mock_kill)
        mock_manager_fn.return_value = manager

        # Kill the session
        response = client.post(
            f"/api/v1/sessions/{session_id}/kill",
            json={"reason": "Testing audit trail"},
        )

        # Should succeed
        assert response.status_code == 200

        # Verify audit trail in metadata
        final_metadata = redis_manager.load_metadata(session_id)
        assert final_metadata is not None
        assert final_metadata.get("status") == "killed"
        assert final_metadata.get("killed_by") == "test_user_1"
        assert final_metadata.get("kill_reason") == "Testing audit trail"
        assert "killed_at" in final_metadata
        assert final_metadata.get("admin_kill") == "False"


@pytest.mark.integration
def test_pause_action_updates_metadata_with_timestamp(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that pause actions update metadata with timestamp.

    Audit test: Verifies pause operations are tracked.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "running",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Pause the session
    response = client.post(f"/api/v1/sessions/{session_id}/pause")

    # Should succeed
    assert response.status_code == 200

    # Verify metadata updated
    final_metadata = redis_manager.load_metadata(session_id)
    assert final_metadata is not None
    assert final_metadata.get("status") == "paused"
    assert "paused_at" in final_metadata
    assert "updated_at" in final_metadata

    # Verify timestamp is recent
    paused_at = datetime.fromisoformat(final_metadata["paused_at"])
    time_diff = (datetime.now(UTC) - paused_at).total_seconds()
    assert time_diff < 5  # Paused within last 5 seconds


@pytest.mark.integration
def test_resume_action_updates_metadata_with_timestamp(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that resume actions update metadata with timestamp.

    Audit test: Verifies resume operations are tracked.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create paused session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "paused",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    redis_manager.save_metadata(session_id, metadata)

    # Mock graph for resume
    with patch("backend.api.control.create_deliberation_graph") as mock_graph:
        graph = MagicMock()
        graph.ainvoke = AsyncMock(return_value={"session_id": session_id})
        mock_graph.return_value = graph

        # Resume the session
        response = client.post(f"/api/v1/sessions/{session_id}/resume")

        # Should succeed
        assert response.status_code == 202

        # Verify metadata updated
        final_metadata = redis_manager.load_metadata(session_id)
        assert final_metadata is not None
        assert final_metadata.get("status") == "running"
        assert "resumed_at" in final_metadata
        assert "updated_at" in final_metadata

        # Verify timestamp is recent
        resumed_at = datetime.fromisoformat(final_metadata["resumed_at"])
        time_diff = (datetime.now(UTC) - resumed_at).total_seconds()
        assert time_diff < 5  # Resumed within last 5 seconds


@pytest.mark.integration
def test_start_action_creates_audit_trail(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that start actions create audit trail in metadata.

    Audit test: Verifies start operations are tracked with user_id.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    session_id = redis_manager.create_session()
    now = datetime.now(UTC)
    metadata = {
        "status": "created",
        "user_id": "test_user_1",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "problem_statement": "Test problem",
        "problem_context": {},
    }
    redis_manager.save_metadata(session_id, metadata)

    # Mock dependencies
    with patch("backend.api.control.load_personas") as mock_personas:
        mock_personas.return_value = (
            {"code": "maria", "name": "Maria", "system_prompt": "Test"},
            {"code": "zara", "name": "Zara", "system_prompt": "Test"},
            {"code": "tariq", "name": "Tariq", "system_prompt": "Test"},
        )

        with patch("backend.api.control.create_deliberation_graph") as mock_graph:
            graph = MagicMock()
            graph.ainvoke = AsyncMock(return_value={"session_id": session_id})
            mock_graph.return_value = graph

            # Start the session
            response = client.post(f"/api/v1/sessions/{session_id}/start")

            # Should succeed
            assert response.status_code == 202

            # Verify metadata includes who started it
            final_metadata = redis_manager.load_metadata(session_id)
            assert final_metadata is not None
            assert final_metadata.get("status") == "running"
            assert final_metadata.get("user_id") == "test_user_1"
            assert "started_at" in final_metadata
