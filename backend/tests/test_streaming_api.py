"""Tests for SSE streaming API endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.api.events import (
    contribution_event,
    format_sse_event,
    node_end_event,
    node_start_event,
)
from backend.api.main import app
from bo1.state.redis_manager import RedisManager


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


def test_format_sse_event() -> None:
    """Test SSE event formatting."""
    event = format_sse_event("test", {"message": "hello"})

    assert "event: test" in event
    assert 'data: {"message": "hello"}' in event
    assert event.endswith("\n\n")


def test_node_start_event() -> None:
    """Test node start event creation."""
    event = node_start_event("decompose", "session_123")

    assert "event: node_start" in event
    assert '"node": "decompose"' in event
    assert '"session_id": "session_123"' in event
    assert "timestamp" in event


def test_node_end_event() -> None:
    """Test node end event creation."""
    event = node_end_event("decompose", "session_123", duration_ms=150.5)

    assert "event: node_end" in event
    assert '"node": "decompose"' in event
    assert '"duration_ms": 150.5' in event


def test_contribution_event() -> None:
    """Test contribution event creation."""
    event = contribution_event(
        session_id="session_123",
        persona_code="CFO",
        persona_name="Maria Gonzalez",
        contribution="We should focus on profitability",
        round_number=2,
    )

    assert "event: contribution" in event
    assert '"persona_code": "CFO"' in event
    assert '"round": 2' in event


def test_stream_endpoint_session_not_found(client: TestClient, redis_manager: RedisManager) -> None:
    """Test streaming endpoint with non-existent session.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    response = client.get("/api/v1/sessions/bo1_nonexistent/stream")

    assert response.status_code == 404


def test_stream_endpoint_session_exists(client: TestClient, redis_manager: RedisManager) -> None:
    """Test streaming endpoint with existing session.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create a session first
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest in AI?" + " " * 100,
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Test streaming endpoint (basic check - don't read full stream)
    try:
        with client.stream("GET", f"/api/v1/sessions/{session_id}/stream") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Read first line to verify SSE format
            lines_read = 0
            for chunk in response.iter_lines():
                if chunk:
                    # chunk is already a string in TestClient
                    first_line = chunk if isinstance(chunk, str) else chunk.decode()
                    assert "event:" in first_line or "data:" in first_line
                    break
                lines_read += 1
                if lines_read > 10:  # Prevent infinite loop
                    break
    finally:
        # Cleanup
        redis_manager.delete_state(session_id)
        if redis_manager.redis:
            redis_manager.redis.delete(f"metadata:{session_id}")
