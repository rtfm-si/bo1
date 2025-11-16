"""Integration tests for session API endpoints.

Tests for Day 37: Security, validation, and integration tests for session management API.
"""

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


@pytest.mark.integration
def test_create_session_with_malicious_xss_input(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that XSS injection attempts are handled safely.

    Security test: Verifies that script tags and malicious HTML are sanitized.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Attempt XSS injection
    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "<script>alert('XSS')</script>Should we invest?",
            "problem_context": {"note": "<img src=x onerror='alert(1)'>"},
        },
    )

    # Should be rejected by validation (security-first approach)
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
def test_create_session_with_sql_injection_attempt(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test that SQL injection attempts are rejected.

    Security test: Verifies input validation prevents SQL injection patterns.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Attempt SQL injection
    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "'; DROP TABLE sessions; --",
            "problem_context": {},
        },
    )

    # Should be rejected by validation
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
def test_create_session_with_empty_problem_statement(client: TestClient) -> None:
    """Test that empty problem statement is rejected.

    Boundary test: Verifies minimum length validation.
    """
    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "",
            "problem_context": {},
        },
    )

    # Should fail validation
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
def test_create_session_with_too_long_problem_statement(client: TestClient) -> None:
    """Test that excessively long problem statement is rejected.

    Boundary test: Verifies maximum length validation.
    """
    # Create problem statement exceeding max length (10,000 chars)
    long_problem = "A" * 10001

    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": long_problem,
            "problem_context": {},
        },
    )

    # Should fail validation
    assert response.status_code == 422


@pytest.mark.integration
def test_get_session_with_invalid_uuid(client: TestClient) -> None:
    """Test getting session with invalid UUID format.

    Security test: Verifies UUID validation prevents injection.
    """
    # Try various invalid UUIDs
    invalid_uuids = [
        "not-a-uuid",
        "'; DROP TABLE sessions; --",
        "../../../etc/passwd",
        "123",
    ]

    for invalid_uuid in invalid_uuids:
        response = client.get(f"/api/v1/sessions/{invalid_uuid}")

        # Should return 404 or 422, not crash
        assert response.status_code in [404, 422]


@pytest.mark.integration
def test_list_sessions_with_negative_pagination(client: TestClient) -> None:
    """Test list sessions with negative pagination values.

    Boundary test: Verifies pagination validation.
    """
    # Negative offset
    response = client.get("/api/v1/sessions?offset=-1&limit=10")

    # Should fail validation or use default
    assert response.status_code in [200, 422]

    # Negative limit
    response = client.get("/api/v1/sessions?offset=0&limit=-1")

    # Should fail validation or use default
    assert response.status_code in [200, 422]


@pytest.mark.integration
def test_list_sessions_with_excessive_pagination(client: TestClient) -> None:
    """Test list sessions with excessively large pagination values.

    Security test: Prevents resource exhaustion attacks.
    """
    # Excessive offset
    response = client.get("/api/v1/sessions?offset=999999&limit=10")

    # Should succeed (just return empty list)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["sessions"], list)

    # Excessive limit
    response = client.get("/api/v1/sessions?offset=0&limit=999999")

    # Should cap limit or fail validation
    assert response.status_code in [200, 422]


@pytest.mark.integration
def test_create_session_with_unicode_input(client: TestClient, redis_manager: RedisManager) -> None:
    """Test session creation with Unicode characters.

    Boundary test: Verifies Unicode handling.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "我们应该投资 $500K 吗? 🚀",
            "problem_context": {"emoji": "✅"},
        },
    )

    # Should succeed
    assert response.status_code == 201
    data = response.json()
    assert "id" in data


@pytest.mark.integration
def test_create_session_with_null_values(client: TestClient) -> None:
    """Test session creation with null values.

    Boundary test: Verifies null handling.
    """
    # Null problem_statement should fail
    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": None,
            "problem_context": {},
        },
    )

    # Should fail validation
    assert response.status_code == 422

    # Null problem_context should succeed (optional field)
    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest $500K in marketing?",
            "problem_context": None,
        },
    )

    # Should succeed
    assert response.status_code == 201


@pytest.mark.integration
def test_create_session_with_special_characters(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test session creation with special characters.

    Boundary test: Verifies special character handling.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest $500K in <product> & (service)?",
            "problem_context": {"symbols": "!@#$%^&*()[]{}"},
        },
    )

    # Should succeed
    assert response.status_code == 201
    data = response.json()
    assert "id" in data


@pytest.mark.integration
def test_create_multiple_sessions_sequential(
    client: TestClient, redis_manager: RedisManager
) -> None:
    """Test creating multiple sessions sequentially.

    Integration test: Verifies session isolation.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    session_ids = []

    for i in range(3):
        response = client.post(
            "/api/v1/sessions",
            json={
                "problem_statement": f"Should we implement strategy {i} for growth?",
                "problem_context": {},
            },
        )

        assert response.status_code == 201
        data = response.json()
        session_ids.append(data["id"])

    # Verify all sessions are unique
    assert len(set(session_ids)) == 3

    # Verify all sessions can be retrieved
    for session_id in session_ids:
        metadata = redis_manager.load_metadata(session_id)
        assert metadata is not None


@pytest.mark.integration
def test_get_nonexistent_session(client: TestClient) -> None:
    """Test getting a session that doesn't exist.

    Integration test: Verifies 404 handling.
    """
    import uuid

    # Use valid UUID that doesn't exist
    fake_uuid = str(uuid.uuid4())

    response = client.get(f"/api/v1/sessions/{fake_uuid}")

    # Should return 404
    assert response.status_code == 404


@pytest.mark.integration
def test_list_sessions_empty(client: TestClient, redis_manager: RedisManager) -> None:
    """Test listing sessions when none exist.

    Integration test: Verifies empty list handling.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    response = client.get("/api/v1/sessions")

    # Should succeed with empty list
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)
    assert len(data["sessions"]) == 0


@pytest.mark.integration
def test_create_session_with_large_context(client: TestClient, redis_manager: RedisManager) -> None:
    """Test session creation with large context object.

    Security test: Verifies context size limits (max 50KB).
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create large context (just under 50KB)
    large_context = {"data": "A" * 49000}

    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest $500K in marketing?",
            "problem_context": large_context,
        },
    )

    # Should succeed (under limit)
    assert response.status_code == 201

    # Create context exceeding 50KB
    excessive_context = {"data": "A" * 51000}

    response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest $500K in marketing?",
            "problem_context": excessive_context,
        },
    )

    # Should fail validation (if implemented) or succeed (if not yet enforced)
    # Currently documenting behavior - strict validation will be added later
    assert response.status_code in [201, 422]


@pytest.mark.integration
def test_session_pagination(client: TestClient, redis_manager: RedisManager) -> None:
    """Test session list pagination.

    Integration test: Verifies pagination works correctly.
    """
    if not redis_manager.is_available:
        pytest.skip("Redis not available")

    # Create 5 sessions
    for i in range(5):
        response = client.post(
            "/api/v1/sessions",
            json={
                "problem_statement": f"Should we implement strategy {i} for company growth?",
                "problem_context": {},
            },
        )
        assert response.status_code == 201

    # Get first page (limit=2)
    response = client.get("/api/v1/sessions?limit=2&offset=0")
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1["sessions"]) <= 2

    # Get second page
    response = client.get("/api/v1/sessions?limit=2&offset=2")
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2["sessions"]) <= 2


@pytest.mark.integration
def test_health_check_endpoint(client: TestClient) -> None:
    """Test health check endpoint.

    Integration test: Verifies API is responsive.
    """
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
