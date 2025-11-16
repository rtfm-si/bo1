"""Tests for admin API endpoints.

Tests:
- GET /api/admin/sessions/active
- GET /api/admin/sessions/{session_id}/full
- POST /api/admin/sessions/{session_id}/kill
- POST /api/admin/sessions/kill-all
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)

# Valid admin API key for testing
ADMIN_API_KEY = "test-admin-key-123"
INVALID_API_KEY = "invalid-key"


@pytest.fixture(autouse=True)
def mock_admin_key():
    """Mock ADMIN_API_KEY environment variable."""
    with patch("backend.api.middleware.admin.ADMIN_API_KEY", ADMIN_API_KEY):
        yield ADMIN_API_KEY


@pytest.fixture
def mock_redis_manager():
    """Mock RedisManager."""
    with patch("backend.api.admin.RedisManager") as mock:
        manager = MagicMock()
        manager.is_available = True
        manager.load_metadata.return_value = {
            "status": "running",
            "user_id": "test_user_1",
            "started_at": datetime.now(UTC).isoformat(),
            "cost": 0.15,
            "phase": "discussion",
        }
        manager.load_state.return_value = {
            "round_number": 2,
            "contributions": [],
        }
        mock.return_value = manager
        yield manager


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager."""
    with patch("backend.api.admin._get_session_manager") as mock:
        manager = MagicMock()
        manager.active_executions = {
            "session-1": MagicMock(),
            "session-2": MagicMock(),
            "session-3": MagicMock(),
        }
        manager.admin_kill_session = AsyncMock(return_value=True)
        manager.admin_kill_all_sessions = AsyncMock(return_value=3)
        mock.return_value = manager
        yield manager


def test_list_active_sessions_success(mock_redis_manager, mock_session_manager):
    """Test listing active sessions as admin."""
    response = client.get(
        "/api/admin/sessions/active",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active_count"] == 3
    assert len(data["sessions"]) == 3
    assert len(data["longest_running"]) <= 10
    assert len(data["most_expensive"]) <= 10

    # Check session info structure
    session = data["sessions"][0]
    assert "session_id" in session
    assert "user_id" in session
    assert "status" in session
    assert "duration_seconds" in session


def test_list_active_sessions_no_admin_key(mock_redis_manager, mock_session_manager):
    """Test listing active sessions without admin key."""
    response = client.get("/api/admin/sessions/active")

    assert response.status_code == 422  # Missing required header


def test_list_active_sessions_invalid_admin_key(mock_redis_manager, mock_session_manager):
    """Test listing active sessions with invalid admin key."""
    response = client.get(
        "/api/admin/sessions/active",
        headers={"X-Admin-Key": INVALID_API_KEY},
    )

    assert response.status_code == 403
    data = response.json()
    assert "invalid" in data["detail"].lower()


def test_list_active_sessions_with_top_n(mock_redis_manager, mock_session_manager):
    """Test listing active sessions with custom top_n parameter."""
    response = client.get(
        "/api/admin/sessions/active?top_n=5",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["longest_running"]) <= 5
    assert len(data["most_expensive"]) <= 5


def test_get_full_session_success(mock_redis_manager, mock_session_manager):
    """Test getting full session details as admin."""
    response = client.get(
        "/api/admin/sessions/session-1/full",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session-1"
    assert "metadata" in data
    assert "state" in data
    assert data["is_active"] is True

    # Check metadata structure
    assert data["metadata"]["status"] == "running"
    assert data["metadata"]["user_id"] == "test_user_1"


def test_get_full_session_not_found(mock_redis_manager, mock_session_manager):
    """Test getting full session details for non-existent session."""
    mock_redis_manager.load_metadata.return_value = None

    response = client.get(
        "/api/admin/sessions/nonexistent/full",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_full_session_no_admin_key(mock_redis_manager, mock_session_manager):
    """Test getting full session details without admin key."""
    response = client.get("/api/admin/sessions/session-1/full")

    assert response.status_code == 422  # Missing required header


def test_admin_kill_session_success(mock_redis_manager, mock_session_manager):
    """Test admin killing a session."""
    response = client.post(
        "/api/admin/sessions/session-1/kill",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session-1"
    assert data["action"] == "admin_kill"
    assert data["status"] == "success"

    # Verify admin_kill_session was called
    mock_session_manager.admin_kill_session.assert_called_once()


def test_admin_kill_session_with_reason(mock_redis_manager, mock_session_manager):
    """Test admin killing a session with custom reason."""
    response = client.post(
        "/api/admin/sessions/session-1/kill?reason=Runaway+session",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert "runaway session" in data["message"].lower()

    # Verify reason was passed
    call_args = mock_session_manager.admin_kill_session.call_args[0]
    assert "Runaway session" in call_args[2]


def test_admin_kill_session_not_found(mock_redis_manager, mock_session_manager):
    """Test admin killing a non-existent session."""
    mock_session_manager.admin_kill_session.return_value = False

    response = client.post(
        "/api/admin/sessions/nonexistent/kill",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_admin_kill_session_no_admin_key(mock_redis_manager, mock_session_manager):
    """Test admin killing a session without admin key."""
    response = client.post("/api/admin/sessions/session-1/kill")

    assert response.status_code == 422  # Missing required header


def test_admin_kill_all_sessions_success(mock_redis_manager, mock_session_manager):
    """Test admin killing all sessions."""
    response = client.post(
        "/api/admin/sessions/kill-all?confirm=true",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["killed_count"] == 3
    assert "3" in data["message"]

    # Verify admin_kill_all_sessions was called
    mock_session_manager.admin_kill_all_sessions.assert_called_once()


def test_admin_kill_all_sessions_with_reason(mock_redis_manager, mock_session_manager):
    """Test admin killing all sessions with custom reason."""
    response = client.post(
        "/api/admin/sessions/kill-all?confirm=true&reason=Emergency+maintenance",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 200
    data = response.json()
    assert "emergency maintenance" in data["message"].lower()

    # Verify reason was passed
    call_args = mock_session_manager.admin_kill_all_sessions.call_args[0]
    assert "Emergency maintenance" in call_args[1]


def test_admin_kill_all_sessions_no_confirmation(mock_redis_manager, mock_session_manager):
    """Test admin killing all sessions without confirmation."""
    response = client.post(
        "/api/admin/sessions/kill-all",
        headers={"X-Admin-Key": ADMIN_API_KEY},
    )

    assert response.status_code == 400
    data = response.json()
    assert "confirm" in data["detail"].lower()

    # Verify kill_all was NOT called
    mock_session_manager.admin_kill_all_sessions.assert_not_called()


def test_admin_kill_all_sessions_no_admin_key(mock_redis_manager, mock_session_manager):
    """Test admin killing all sessions without admin key."""
    response = client.post("/api/admin/sessions/kill-all?confirm=true")

    assert response.status_code == 422  # Missing required header


def test_admin_kill_all_sessions_invalid_admin_key(mock_redis_manager, mock_session_manager):
    """Test admin killing all sessions with invalid admin key."""
    response = client.post(
        "/api/admin/sessions/kill-all?confirm=true",
        headers={"X-Admin-Key": INVALID_API_KEY},
    )

    assert response.status_code == 403
    data = response.json()
    assert "invalid" in data["detail"].lower()


def test_admin_key_not_configured():
    """Test admin endpoints when ADMIN_API_KEY is not configured."""
    with patch("backend.api.middleware.admin.ADMIN_API_KEY", ""):
        response = client.get(
            "/api/admin/sessions/active",
            headers={"X-Admin-Key": "any-key"},
        )

        assert response.status_code == 500
        data = response.json()
        assert "not configured" in data["detail"].lower()
