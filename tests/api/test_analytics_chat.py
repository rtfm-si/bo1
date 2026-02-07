"""Integration tests for admin analytics chat API endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import limiter


@pytest.fixture
def client():
    """TestClient with admin auth overridden and rate limiter disabled."""
    app.dependency_overrides[require_admin_any] = lambda: "test_admin_user"
    original_enabled = limiter.enabled
    limiter.enabled = False
    yield TestClient(app)
    limiter.enabled = original_enabled
    app.dependency_overrides.clear()


@pytest.fixture
def mock_agent():
    """Mock the analytics agent."""
    with patch("backend.api.admin.analytics_chat.AdminAnalyticsAgent") as mock_agent_cls:
        instance = mock_agent_cls.return_value

        async def mock_run(*args, **kwargs):
            yield {"event": "thinking", "data": {"status": "planning"}}
            yield {"event": "step_start", "data": {"step": 0, "description": "Count users"}}
            yield {"event": "sql", "data": {"step": 0, "sql": "SELECT COUNT(*) FROM users"}}
            yield {
                "event": "data",
                "data": {"step": 0, "columns": ["count"], "row_count": 1, "rows": [{"count": 42}]},
            }
            yield {"event": "step_summary", "data": {"step": 0, "summary": "42 total users."}}
            yield {"event": "step_complete", "data": {"step": 0}}
            yield {"event": "suggestions", "data": {"suggestions": ["How many signed up today?"]}}
            yield {
                "event": "done",
                "data": {
                    "steps": [{"step": 0, "summary": "42 total users."}],
                    "total_cost": 0.001,
                    "elapsed_seconds": 1.5,
                    "suggestions": ["How many signed up today?"],
                },
            }

        instance.run = mock_run
        yield mock_agent_cls


@pytest.fixture
def mock_saved():
    """Mock saved analyses functions."""
    with (
        patch("backend.api.admin.analytics_chat.create_conversation") as mock_create,
        patch("backend.api.admin.analytics_chat.save_message") as mock_save_msg,
        patch("backend.api.admin.analytics_chat.get_conversation_messages") as mock_get_msgs,
        patch("backend.api.admin.analytics_chat.list_conversations") as mock_list,
    ):
        mock_create.return_value = {"id": "conv-123", "admin_user_id": "test", "title": "Test"}
        mock_save_msg.return_value = {"id": "msg-123", "created_at": "2026-01-01T00:00:00"}
        mock_get_msgs.return_value = []
        mock_list.return_value = []
        yield {
            "create": mock_create,
            "save_msg": mock_save_msg,
            "get_msgs": mock_get_msgs,
            "list": mock_list,
        }


class TestAnalyticsChatSSE:
    """Test the SSE streaming endpoint."""

    def test_ask_returns_sse_stream(self, client, mock_agent, mock_saved):
        """POST /ask should return SSE stream with correct events."""
        response = client.post(
            "/api/admin/analytics-chat/ask",
            json={"question": "How many users?", "model": "sonnet"},
            headers={"X-Admin-Key": "test"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_ask_validates_model(self, client, mock_agent, mock_saved):
        """Should reject invalid model values."""
        response = client.post(
            "/api/admin/analytics-chat/ask",
            json={"question": "test", "model": "gpt-4"},
            headers={"X-Admin-Key": "test"},
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_ask_requires_question(self, client, mock_agent, mock_saved):
        """Should reject empty question."""
        response = client.post(
            "/api/admin/analytics-chat/ask",
            json={"question": "", "model": "sonnet"},
            headers={"X-Admin-Key": "test"},
        )
        assert response.status_code == 422


class TestConversationHistory:
    """Test conversation history endpoints."""

    def test_list_history(self, client, mock_saved):
        """GET /history should return conversation list."""
        mock_saved["list"].return_value = [
            {"id": "conv-1", "title": "Test", "created_at": "2026-01-01"}
        ]

        response = client.get("/api/admin/analytics-chat/history")
        assert response.status_code == 200


class TestSavedAnalyses:
    """Test saved analyses CRUD."""

    def test_save_analysis(self, client):
        """POST /saved should create a saved analysis."""
        with patch("backend.api.admin.analytics_chat.save_analysis") as mock_save:
            mock_save.return_value = {"id": "saved-1", "title": "Test", "created_at": "2026-01-01"}

            response = client.post(
                "/api/admin/analytics-chat/saved",
                json={
                    "title": "Test Analysis",
                    "description": "A test",
                    "original_question": "How many users?",
                    "steps": [{"description": "Count", "sql": "SELECT 1"}],
                },
                headers={"X-Admin-Key": "test"},
            )
            assert response.status_code == 200

    def test_delete_saved(self, client):
        """DELETE /saved/{id} should delete."""
        with patch("backend.api.admin.analytics_chat.delete_saved_analysis") as mock_del:
            mock_del.return_value = True

            response = client.delete(
                "/api/admin/analytics-chat/saved/test-id",
                headers={"X-Admin-Key": "test"},
            )
            assert response.status_code == 200

    def test_delete_nonexistent(self, client):
        """DELETE /saved/{id} should 404 for unknown ID."""
        with patch("backend.api.admin.analytics_chat.delete_saved_analysis") as mock_del:
            mock_del.return_value = False

            response = client.delete(
                "/api/admin/analytics-chat/saved/nonexistent",
                headers={"X-Admin-Key": "test"},
            )
            assert response.status_code == 404
