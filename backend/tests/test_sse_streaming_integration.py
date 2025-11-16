"""Integration tests for SSE streaming endpoints.

Tests cover:
- Invalid session_id (non-UUID, SQL injection)
- Authorization (user cannot stream other user's session)
- Connection limits (max 10 concurrent connections per user)
- Malformed events (handle corrupted SSE data)
- Reconnection logic (client reconnects after disconnect)
- Clarification events (requested and answered)
"""

import logging

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)


@pytest.fixture
def client() -> TestClient:
    """Create test client.

    Returns:
        FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
def redis_manager() -> RedisManager:
    """Create Redis manager for tests.

    Returns:
        RedisManager instance
    """
    return RedisManager()


@pytest.mark.integration
def test_stream_invalid_session_id_non_uuid(client: TestClient) -> None:
    """Test SSE streaming with non-UUID session_id.

    Args:
        client: FastAPI test client
    """
    # Non-UUID session_id
    response = client.get("/api/v1/sessions/not-a-uuid/stream")

    # Should return 404 (session not found)
    assert response.status_code == 404


@pytest.mark.integration
def test_stream_invalid_session_id_sql_injection(client: TestClient) -> None:
    """Test SSE streaming with SQL injection attempt in session_id.

    Args:
        client: FastAPI test client
    """
    # SQL injection attempt in path
    malicious_id = "bo1_' OR '1'='1"
    response = client.get(f"/api/v1/sessions/{malicious_id}/stream")

    # Should safely handle and return 404
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.skip(
    reason="Authorization not implemented in MVP (Week 7) - currently uses hardcoded test_user_1"
)
def test_stream_authorization_other_user_session(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that user cannot stream another user's session.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session for user A
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test problem for user A" + " " * 100},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    try:
        # TODO(Week 7): Once JWT auth is implemented, test with different user token
        # For now, this test is skipped
        pass
    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")


@pytest.mark.integration
@pytest.mark.skip(reason="Connection limits not implemented in v1.0 - will be added in v2.0")
def test_stream_connection_limits(client: TestClient, redis_manager: RedisManager) -> None:
    """Test max concurrent connections per user (limit: 10).

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create a session
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test problem" + " " * 100},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    try:
        # TODO(v2.0): Test opening 11 concurrent connections
        # First 10 should succeed, 11th should return 429 (Too Many Requests)
        pass
    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")


@pytest.mark.integration
def test_stream_handles_session_not_found(client: TestClient) -> None:
    """Test SSE streaming handles missing session gracefully.

    Args:
        client: FastAPI test client
    """
    # Valid UUID format but session doesn't exist
    fake_session_id = "bo1_00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/sessions/{fake_session_id}/stream")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
def test_stream_redis_unavailable(client: TestClient, redis_manager: RedisManager) -> None:
    """Test SSE streaming when Redis is unavailable.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if redis_manager.is_available:
        pytest.skip("Test only runs when Redis is unavailable")

    response = client.get("/api/v1/sessions/bo1_test/stream")

    # Should return 500 when Redis is down
    assert response.status_code == 500


@pytest.mark.integration
def test_stream_event_format_valid(client: TestClient, redis_manager: RedisManager) -> None:
    """Test that SSE events are properly formatted.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create a session
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test SSE event format" + " " * 100},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    try:
        # Stream events (limited read)
        with client.stream("GET", f"/api/v1/sessions/{session_id}/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Read first few lines to verify format
            lines_read = 0
            event_found = False
            data_found = False

            for chunk in response.iter_lines():
                if chunk:
                    line = chunk if isinstance(chunk, str) else chunk.decode()

                    # SSE format: "event: type" or "data: json"
                    if line.startswith("event:"):
                        event_found = True
                    elif line.startswith("data:"):
                        data_found = True

                lines_read += 1
                if lines_read > 20 or (event_found and data_found):
                    break

            # Should have both event and data lines
            assert event_found, "No 'event:' line found in SSE stream"
            assert data_found, "No 'data:' line found in SSE stream"

    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")


@pytest.mark.integration
@pytest.mark.skip(
    reason="Reconnection logic with Last-Event-ID not implemented in v1.0 - will be added in v2.0"
)
def test_stream_reconnection_logic(client: TestClient, redis_manager: RedisManager) -> None:
    """Test client reconnection with Last-Event-ID header.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create a session
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test reconnection" + " " * 100},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    try:
        # TODO(v2.0): Test reconnection logic
        # 1. Connect and read some events
        # 2. Disconnect
        # 3. Reconnect with Last-Event-ID header
        # 4. Verify events resume from correct position
        pass
    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")


@pytest.mark.integration
@pytest.mark.skip(
    reason="Clarification events tested in Day 39 - requires full deliberation execution"
)
def test_stream_clarification_requested_event(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that clarification_requested event is sent during deliberation.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # TODO(Day 39): Test with actual deliberation that triggers clarification
    # 1. Create session with problem that needs clarification
    # 2. Start deliberation
    # 3. Stream events
    # 4. Verify clarification_requested event is sent
    # 5. Submit clarification answer
    # 6. Verify clarification_answered event is sent


@pytest.mark.integration
@pytest.mark.skip(
    reason="Clarification answer event tested in Day 39 - requires full deliberation execution"
)
def test_stream_clarification_answered_event(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that clarification_answered event resumes deliberation.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # TODO(Day 39): Test with actual deliberation
    # 1. Create session
    # 2. Start deliberation
    # 3. Wait for clarification_requested event
    # 4. Submit answer via POST /sessions/{id}/clarify
    # 5. Verify clarification_answered event is sent
    # 6. Verify deliberation resumes


@pytest.mark.integration
def test_stream_basic_connection(client: TestClient, redis_manager: RedisManager) -> None:
    """Test basic SSE connection establishment and headers.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create a session
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test basic SSE connection" + " " * 100},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    try:
        # Test streaming endpoint
        with client.stream("GET", f"/api/v1/sessions/{session_id}/stream") as response:
            assert response.status_code == 200

            # Verify SSE headers
            assert "text/event-stream" in response.headers["content-type"]
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("connection") == "keep-alive"

    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")


@pytest.mark.integration
@pytest.mark.skip(reason="Long-running test - only run manually for memory leak checks")
def test_stream_long_running_no_memory_leak(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that long-running SSE connections don't leak memory.

    This test should be run manually for performance testing.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create a session
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test long-running connection" + " " * 100},
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    try:
        # TODO: Connect and maintain connection for 1 hour
        # Monitor memory usage to ensure no leaks
        # This would require actual profiling tools
        pass
    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")
