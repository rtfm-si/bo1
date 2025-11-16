"""Tests for deliberation control API endpoints.

Tests:
- POST /api/v1/sessions/{session_id}/start
- POST /api/v1/sessions/{session_id}/pause
- POST /api/v1/sessions/{session_id}/resume
- POST /api/v1/sessions/{session_id}/kill
- POST /api/v1/sessions/{session_id}/clarify
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.graph.execution import PermissionError

client = TestClient(app)


@pytest.fixture
def mock_redis_manager():
    """Mock RedisManager."""
    with patch("backend.api.control.RedisManager") as mock:
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
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager."""
    with patch("backend.api.control._get_session_manager") as mock:
        manager = MagicMock()
        manager.active_executions = {}
        manager.start_session = AsyncMock(return_value=MagicMock())
        manager.kill_session = AsyncMock(return_value=True)
        mock.return_value = manager
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
        # load_personas returns a tuple of dicts, not objects
        mock.return_value = (
            {"code": "maria", "name": "Maria", "system_prompt": "Test"},
            {"code": "zara", "name": "Zara", "system_prompt": "Test"},
            {"code": "tariq", "name": "Tariq", "system_prompt": "Test"},
        )
        yield mock


def test_start_deliberation_success(
    mock_redis_manager, mock_session_manager, mock_graph, mock_personas
):
    """Test starting a deliberation successfully."""
    response = client.post("/api/v1/sessions/test-session-123/start")

    assert response.status_code == 202
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["action"] == "start"
    assert data["status"] == "success"
    assert "background" in data["message"].lower()

    # Verify session manager was called
    mock_session_manager.start_session.assert_called_once()


def test_start_deliberation_session_not_found(mock_redis_manager, mock_session_manager):
    """Test starting a non-existent session."""
    mock_redis_manager.load_metadata.return_value = None

    response = client.post("/api/v1/sessions/nonexistent/start")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_start_deliberation_already_running(mock_redis_manager, mock_session_manager):
    """Test starting a session that's already running."""
    mock_session_manager.active_executions["test-session-123"] = MagicMock()

    response = client.post("/api/v1/sessions/test-session-123/start")

    assert response.status_code == 409
    data = response.json()
    assert "already running" in data["detail"].lower()


def test_start_deliberation_invalid_status(mock_redis_manager, mock_session_manager):
    """Test starting a session with invalid status."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "completed",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = client.post("/api/v1/sessions/test-session-123/start")

    assert response.status_code == 400
    data = response.json()
    assert "cannot start" in data["detail"].lower()


def test_pause_deliberation_success(mock_redis_manager):
    """Test pausing a deliberation successfully."""
    response = client.post("/api/v1/sessions/test-session-123/pause")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["action"] == "pause"
    assert data["status"] == "success"
    assert "paused" in data["message"].lower()

    # Verify metadata was updated
    mock_redis_manager.save_metadata.assert_called_once()
    saved_metadata = mock_redis_manager.save_metadata.call_args[0][1]
    assert saved_metadata["status"] == "paused"
    assert "paused_at" in saved_metadata


def test_pause_deliberation_session_not_found(mock_redis_manager):
    """Test pausing a non-existent session."""
    mock_redis_manager.load_metadata.return_value = None

    response = client.post("/api/v1/sessions/nonexistent/pause")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_resume_deliberation_success(mock_redis_manager, mock_session_manager, mock_graph):
    """Test resuming a paused deliberation."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "paused",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "user_id": "test_user_1",
    }

    response = client.post("/api/v1/sessions/test-session-123/resume")

    assert response.status_code == 202
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["action"] == "resume"
    assert data["status"] == "success"
    assert "resumed" in data["message"].lower()

    # Verify session manager was called
    mock_session_manager.start_session.assert_called_once()


def test_resume_deliberation_invalid_status(mock_redis_manager, mock_session_manager):
    """Test resuming a session that's not paused."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "running",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = client.post("/api/v1/sessions/test-session-123/resume")

    assert response.status_code == 400
    data = response.json()
    assert "must be paused" in data["detail"].lower()


def test_resume_deliberation_already_running(mock_redis_manager, mock_session_manager):
    """Test resuming a session that's already running."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "paused",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    mock_session_manager.active_executions["test-session-123"] = MagicMock()

    response = client.post("/api/v1/sessions/test-session-123/resume")

    assert response.status_code == 409
    data = response.json()
    assert "already running" in data["detail"].lower()


def test_kill_deliberation_success(mock_redis_manager, mock_session_manager):
    """Test killing a deliberation successfully."""
    response = client.post(
        "/api/v1/sessions/test-session-123/kill",
        json={"reason": "Test kill"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["action"] == "kill"
    assert data["status"] == "success"
    assert "killed" in data["message"].lower()

    # Verify session manager was called with reason
    mock_session_manager.kill_session.assert_called_once_with(
        "test-session-123", "test_user_1", "Test kill"
    )


def test_kill_deliberation_no_reason(mock_redis_manager, mock_session_manager):
    """Test killing a deliberation without providing a reason."""
    response = client.post("/api/v1/sessions/test-session-123/kill")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify default reason was used
    mock_session_manager.kill_session.assert_called_once()
    call_args = mock_session_manager.kill_session.call_args[0]
    assert "User requested stop" in call_args[2]


def test_kill_deliberation_permission_denied(mock_redis_manager, mock_session_manager):
    """Test killing a session owned by another user."""
    mock_session_manager.kill_session.side_effect = PermissionError(
        "User test_user_1 cannot kill session owned by test_user_2"
    )

    response = client.post("/api/v1/sessions/test-session-123/kill")

    assert response.status_code == 403
    data = response.json()
    assert "cannot kill session" in data["detail"].lower()


def test_kill_deliberation_not_found(mock_redis_manager, mock_session_manager):
    """Test killing a non-existent session."""
    mock_session_manager.kill_session.return_value = False

    response = client.post("/api/v1/sessions/nonexistent/kill")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_submit_clarification_success(mock_redis_manager):
    """Test submitting a clarification successfully."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "waiting_for_clarification",
        "user_id": "test_user_1",
        "pending_clarification": {
            "question_id": "q1",
            "question": "What is your churn rate?",
        },
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = client.post(
        "/api/v1/sessions/test-session-123/clarify",
        json={"answer": "3.5% monthly"},
    )

    assert response.status_code == 202
    data = response.json()
    assert data["session_id"] == "test-session-123"
    assert data["action"] == "clarify"
    assert data["status"] == "success"
    assert "submitted" in data["message"].lower()

    # Verify state was updated with answer
    mock_redis_manager.save_state.assert_called_once()
    saved_state = mock_redis_manager.save_state.call_args[0][1]
    assert "clarification_q1" in saved_state["problem"]["context"]
    assert saved_state["problem"]["context"]["clarification_q1"] == "3.5% monthly"

    # Verify pending clarification was cleared
    mock_redis_manager.save_metadata.assert_called_once()
    saved_metadata = mock_redis_manager.save_metadata.call_args[0][1]
    assert saved_metadata["pending_clarification"] is None
    assert saved_metadata["status"] == "paused"


def test_submit_clarification_no_pending(mock_redis_manager):
    """Test submitting a clarification when none is pending."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "running",
        "user_id": "test_user_1",
        "pending_clarification": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = client.post(
        "/api/v1/sessions/test-session-123/clarify",
        json={"answer": "Some answer"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "no pending clarification" in data["detail"].lower()


def test_submit_clarification_permission_denied(mock_redis_manager):
    """Test submitting a clarification for non-owned session."""
    mock_redis_manager.load_metadata.return_value = {
        "status": "waiting_for_clarification",
        "user_id": "test_user_2",  # Different user
        "pending_clarification": {
            "question_id": "q1",
            "question": "What is your churn rate?",
        },
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = client.post(
        "/api/v1/sessions/test-session-123/clarify",
        json={"answer": "3.5% monthly"},
    )

    assert response.status_code == 403
    data = response.json()
    assert "does not own" in data["detail"].lower()


def test_submit_clarification_session_not_found(mock_redis_manager):
    """Test submitting a clarification for non-existent session."""
    mock_redis_manager.load_metadata.return_value = None

    response = client.post(
        "/api/v1/sessions/nonexistent/clarify",
        json={"answer": "Some answer"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_submit_clarification_invalid_answer(mock_redis_manager):
    """Test submitting an invalid clarification answer."""
    response = client.post(
        "/api/v1/sessions/test-session-123/clarify",
        json={"answer": ""},  # Empty answer
    )

    assert response.status_code == 422  # Validation error
    data = response.json()
    # Check for string_too_short error type from pydantic
    assert any("string_too_short" in str(error["type"]) for error in data["detail"])
