"""Tests for session management API endpoints."""

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture(autouse=True)
def cleanup_redis(redis_manager: RedisManager) -> None:
    """Clean up Redis before and after each test.

    Args:
        redis_manager: Redis manager instance
    """
    # Clean up before test
    if redis_manager.is_available:
        sessions = redis_manager.list_sessions()
        for session_id in sessions:
            redis_manager.delete_state(session_id)
            # Also delete metadata
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


def test_create_session_success(client: TestClient, redis_manager: RedisManager) -> None:
    """Test creating a session successfully.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest $500K in expanding to the European market?",
            "problem_context": {"budget": 500000, "timeline": "Q2 2025"},
        },
    )

    # Verify response
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "created"
    assert data["phase"] is None
    assert "created_at" in data
    assert "updated_at" in data
    assert len(data["problem_statement"]) <= 100  # Truncated

    # Verify session saved to Redis
    session_id = data["id"]
    metadata = redis_manager.load_metadata(session_id)
    assert metadata is not None
    assert metadata["status"] == "created"
    assert (
        metadata["problem_statement"]
        == "Should we invest $500K in expanding to the European market?"
    )


def test_create_session_validation_errors(client: TestClient) -> None:
    """Test session creation with invalid input.

    Args:
        client: FastAPI test client
    """
    # Too short problem statement
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Short"},
    )
    assert response.status_code == 422  # Validation error

    # XSS attempt
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "<script>alert('xss')</script>" + "x" * 100},
    )
    assert response.status_code == 422  # Validation error

    # SQL injection attempt
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "'; DROP TABLE sessions; -- What should we do?"},
    )
    assert response.status_code == 422  # Validation error


def test_list_sessions_empty(client: TestClient, redis_manager: RedisManager) -> None:
    """Test listing sessions when none exist.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    response = client.get("/api/v1/sessions")

    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_list_sessions_with_data(client: TestClient, redis_manager: RedisManager) -> None:
    """Test listing sessions with multiple sessions.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create 3 sessions
    session_ids = []
    for i in range(3):
        response = client.post(
            "/api/v1/sessions",
            json={
                "problem_statement": f"Problem statement {i}"
                + " with more text to meet minimum length",
            },
        )
        assert response.status_code == 201
        session_ids.append(response.json()["id"])

    # List sessions
    response = client.get("/api/v1/sessions")

    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 3
    assert data["total"] == 3

    # Verify all session IDs present
    returned_ids = [s["id"] for s in data["sessions"]]
    assert set(returned_ids) == set(session_ids)


def test_list_sessions_pagination(client: TestClient, redis_manager: RedisManager) -> None:
    """Test session listing pagination.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create 5 sessions
    for i in range(5):
        response = client.post(
            "/api/v1/sessions",
            json={
                "problem_statement": f"Problem {i}" + " with more text to meet minimum length",
            },
        )
        assert response.status_code == 201

    # Get first page (limit=2)
    response = client.get("/api/v1/sessions?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0

    # Get second page
    response = client.get("/api/v1/sessions?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2
    assert data["total"] == 5


def test_get_session_details(client: TestClient, redis_manager: RedisManager) -> None:
    """Test getting session details.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create session
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we pivot our business model?",
            "problem_context": {"current_model": "subscription"},
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Get session details
    response = client.get(f"/api/v1/sessions/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == session_id
    assert data["status"] == "created"
    assert data["problem"]["statement"] == "Should we pivot our business model?"
    assert data["problem"]["context"]["current_model"] == "subscription"


def test_get_session_not_found(client: TestClient, redis_manager: RedisManager) -> None:
    """Test getting non-existent session.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    response = client.get("/api/v1/sessions/bo1_nonexistent")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_session_list_filter_by_status(client: TestClient, redis_manager: RedisManager) -> None:
    """Test filtering sessions by status.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create sessions with different statuses
    session1_response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Problem 1 with enough text to meet minimum"},
    )
    session1_id = session1_response.json()["id"]

    session2_response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Problem 2 with enough text to meet minimum"},
    )
    session2_id = session2_response.json()["id"]

    # Manually update one session status to "completed"
    metadata = redis_manager.load_metadata(session2_id)
    if metadata:
        metadata["status"] = "completed"
        redis_manager.save_metadata(session2_id, metadata)

    # Filter by "created" status
    response = client.get("/api/v1/sessions?status=created")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["id"] == session1_id

    # Filter by "completed" status
    response = client.get("/api/v1/sessions?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["id"] == session2_id


def test_malicious_input_boundary_tests(client: TestClient) -> None:
    """Test malicious and boundary inputs.

    Args:
        client: FastAPI test client
    """
    # Empty string (after strip)
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "   "},
    )
    assert response.status_code == 422

    # Max length + 1
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "x" * 10001},
    )
    assert response.status_code == 422

    # Null value
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": None},
    )
    assert response.status_code == 422


def test_pagination_boundary_tests(client: TestClient, redis_manager: RedisManager) -> None:
    """Test pagination boundary cases.

    Args:
        client: FastAPI test client
        redis_manager: Redis manager instance
    """
    # Skip if Redis not available
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Negative offset (should fail validation)
    response = client.get("/api/v1/sessions?offset=-1")
    assert response.status_code == 422

    # Limit > 100 (should fail validation)
    response = client.get("/api/v1/sessions?limit=101")
    assert response.status_code == 422

    # Very large offset (should return empty)
    response = client.get("/api/v1/sessions?offset=999999")
    assert response.status_code == 200
    assert response.json()["sessions"] == []
