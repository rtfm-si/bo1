"""Integration tests for Board of One API.

Tests complete end-to-end flows:
- Create session → Start deliberation → Get session details
- Create session → Start → Pause → Resume → Get details
- Create session → Start → Kill
- Admin: List active sessions → Kill specific session
- Error cases: Invalid session IDs, unauthorized access
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)

ADMIN_API_KEY = "test-admin-key-123"


@pytest.fixture(autouse=True)
def mock_admin_key():
    """Mock ADMIN_API_KEY environment variable."""
    with patch("backend.api.middleware.admin.ADMIN_API_KEY", ADMIN_API_KEY):
        yield ADMIN_API_KEY


@pytest.fixture
def mock_redis_manager():
    """Mock RedisManager for all tests."""
    with (
        patch("backend.api.sessions.RedisManager") as mock_sessions,
        patch("backend.api.control.RedisManager") as mock_control,
        patch("backend.api.admin.RedisManager") as mock_admin,
    ):
        manager = MagicMock()
        manager.is_available = True
        manager.create_session.return_value = "test-session-123"
        manager.load_metadata.return_value = {
            "status": "created",
            "phase": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "problem_statement": "Test problem",
            "problem_context": {},
            "user_id": "test_user_1",
        }
        manager.save_metadata.return_value = True
        manager.load_state.return_value = {
            "problem": {"statement": "Test", "context": {}},
            "round_number": 0,
        }
        manager.save_state.return_value = True
        manager.list_sessions.return_value = ["test-session-123"]

        # Apply to all patches
        mock_sessions.return_value = manager
        mock_control.return_value = manager
        mock_admin.return_value = manager

        yield manager


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for all tests."""
    with (
        patch("backend.api.control._get_session_manager") as mock_control,
        patch("backend.api.admin._get_session_manager") as mock_admin,
    ):
        manager = MagicMock()
        manager.active_executions = {}
        manager.start_session = AsyncMock(return_value=MagicMock())
        manager.kill_session = AsyncMock(return_value=True)
        manager.admin_kill_session = AsyncMock(return_value=True)
        manager.admin_kill_all_sessions = AsyncMock(return_value=0)

        # Apply to both patches
        mock_control.return_value = manager
        mock_admin.return_value = manager

        yield manager


@pytest.fixture
def mock_graph():
    """Mock deliberation graph."""
    with patch("backend.api.control.create_deliberation_graph") as mock:
        graph = MagicMock()
        graph.ainvoke = AsyncMock(return_value={"session_id": "test-session-123"})
        mock.return_value = graph
        yield graph


@pytest.fixture
def mock_personas():
    """Mock persona loader."""
    with patch("backend.api.control.load_personas") as mock:
        mock.return_value = (
            {"code": "maria", "name": "Maria", "system_prompt": "Test"},
            {"code": "zara", "name": "Zara", "system_prompt": "Test"},
            {"code": "tariq", "name": "Tariq", "system_prompt": "Test"},
        )
        yield mock


def test_integration_create_and_get_session(mock_redis_manager):
    """Integration test: Create session and retrieve it."""
    # Create session
    create_response = client.post(
        "/api/v1/sessions",
        json={
            "problem_statement": "Should we invest $500K in expanding to the European market?",
            "problem_context": {"budget": 500000},
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Get session details
    get_response = client.get(f"/api/v1/sessions/{session_id}")
    assert get_response.status_code == 200
    session_data = get_response.json()
    assert session_data["id"] == session_id
    assert session_data["status"] == "created"


def test_integration_create_start_pause_session(
    mock_redis_manager, mock_session_manager, mock_graph, mock_personas
):
    """Integration test: Create → Start → Pause flow."""
    # Create session
    create_response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "What pricing strategy should we use?"},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Start deliberation
    start_response = client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_response.status_code == 202
    assert start_response.json()["action"] == "start"

    # Pause deliberation
    pause_response = client.post(f"/api/v1/sessions/{session_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["action"] == "pause"


def test_integration_create_start_kill_session(
    mock_redis_manager, mock_session_manager, mock_graph, mock_personas
):
    """Integration test: Create → Start → Kill flow."""
    # Create session
    create_response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Should we pivot our business model?"},
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Start deliberation
    start_response = client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_response.status_code == 202

    # Kill deliberation
    kill_response = client.post(
        f"/api/v1/sessions/{session_id}/kill",
        json={"reason": "Testing kill functionality"},
    )
    assert kill_response.status_code == 200
    assert kill_response.json()["action"] == "kill"
    assert "testing kill" in kill_response.json()["message"].lower()


def test_integration_pause_resume_flow(
    mock_redis_manager, mock_session_manager, mock_graph, mock_personas
):
    """Integration test: Pause → Resume flow."""
    session_id = "test-session-123"

    # Update metadata to paused state
    mock_redis_manager.load_metadata.return_value = {
        "status": "paused",
        "user_id": "test_user_1",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    # Resume deliberation
    resume_response = client.post(f"/api/v1/sessions/{session_id}/resume")
    assert resume_response.status_code == 202
    assert resume_response.json()["action"] == "resume"


def test_integration_admin_list_and_kill(mock_redis_manager, mock_session_manager):
    """Integration test: Admin list active sessions → Admin kill."""
    # Simulate active sessions
    mock_session_manager.active_executions = {
        "session-1": MagicMock(),
        "session-2": MagicMock(),
    }

    # List active sessions as admin
    list_response = client.get(
        "/api/admin/sessions/active",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )
    assert list_response.status_code == 200
    assert list_response.json()["active_count"] == 2

    # Admin kill specific session
    kill_response = client.post(
        "/api/admin/sessions/session-1/kill",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )
    assert kill_response.status_code == 200
    assert kill_response.json()["action"] == "admin_kill"


def test_integration_admin_get_full_session(mock_redis_manager, mock_session_manager):
    """Integration test: Admin get full session details."""
    mock_session_manager.active_executions = {"test-session-123": MagicMock()}

    response = client.get(
        "/api/admin/sessions/test-session-123/full",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["is_active"] is True
    assert "metadata" in data
    assert "state" in data


def test_integration_list_sessions_pagination(mock_redis_manager):
    """Integration test: List sessions with pagination."""
    # List sessions with pagination
    response = client.get("/api/v1/sessions?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert "total" in data
    assert data["limit"] == 5
    assert data["offset"] == 0


def test_integration_invalid_session_id_handling(mock_redis_manager):
    """Integration test: Error handling for invalid session IDs."""
    mock_redis_manager.load_metadata.return_value = None

    # Try to get non-existent session
    response = client.get("/api/v1/sessions/nonexistent-session")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # Try to start non-existent session
    response = client.post("/api/v1/sessions/nonexistent-session/start")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_integration_session_status_validation(mock_redis_manager, mock_session_manager):
    """Integration test: Session status validation for control operations."""
    # Try to start already-running session
    mock_session_manager.active_executions["test-session-123"] = MagicMock()

    response = client.post("/api/v1/sessions/test-session-123/start")
    assert response.status_code == 409
    assert "already running" in response.json()["detail"].lower()

    # Try to resume non-paused session
    mock_redis_manager.load_metadata.return_value = {
        "status": "running",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    mock_session_manager.active_executions = {}  # Not running

    response = client.post("/api/v1/sessions/test-session-123/resume")
    assert response.status_code == 400
    assert "must be paused" in response.json()["detail"].lower()


def test_integration_admin_without_key(mock_redis_manager):
    """Integration test: Admin endpoints require API key."""
    # Try to list active sessions without key
    response = client.get("/api/admin/sessions/active")
    assert response.status_code == 422  # Missing required header

    # Try to admin kill without key
    response = client.post("/api/admin/sessions/session-1/kill")
    assert response.status_code == 422


def test_integration_admin_with_invalid_key(mock_redis_manager):
    """Integration test: Admin endpoints reject invalid API key."""
    response = client.get(
        "/api/admin/sessions/active",
        headers={"X-Admin-Key": "invalid-key"},
    )
    assert response.status_code == 403
    assert "invalid" in response.json()["detail"].lower()


def test_integration_clarification_flow(mock_redis_manager):
    """Integration test: Clarification submission flow."""
    # Set up session with pending clarification
    mock_redis_manager.load_metadata.return_value = {
        "status": "waiting_for_clarification",
        "user_id": "test_user_1",
        "pending_clarification": {
            "question_id": "q1",
            "question": "What is your monthly churn rate?",
        },
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    # Submit clarification
    response = client.post(
        "/api/v1/sessions/test-session-123/clarify",
        json={"answer": "3.5% monthly"},
    )

    assert response.status_code == 202
    assert response.json()["action"] == "clarify"
    assert response.json()["status"] == "success"

    # Verify state was updated
    mock_redis_manager.save_state.assert_called_once()


def test_integration_create_session_validation(mock_redis_manager):
    """Integration test: Request validation for session creation."""
    # Test with too short problem statement
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Short"},
    )
    assert response.status_code == 422

    # Test with malicious content (script tag)
    response = client.post(
        "/api/v1/sessions",
        json={"problem_statement": "Test <script>alert('xss')</script> problem statement here"},
    )
    assert response.status_code == 422


def test_integration_concurrent_sessions(
    mock_redis_manager, mock_session_manager, mock_graph, mock_personas
):
    """Integration test: Multiple sessions can be created and managed."""
    # Mock to return different session IDs
    session_counter = [0]

    def create_unique_session():
        session_counter[0] += 1
        return f"test-session-{session_counter[0]}"

    mock_redis_manager.create_session.side_effect = create_unique_session

    # Create multiple sessions
    sessions = []
    for i in range(3):
        response = client.post(
            "/api/v1/sessions",
            json={"problem_statement": f"Test problem {i} for concurrent testing"},
        )
        assert response.status_code == 201
        sessions.append(response.json()["id"])

    # Verify all sessions created
    assert len(sessions) == 3
    assert len(set(sessions)) == 3  # All unique

    # List sessions
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1  # At least one session in list
