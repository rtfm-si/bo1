"""Tests for dataset Q&A API (EPIC 5)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.api.datasets import (
    _parse_spec_from_response,
    _strip_specs_from_response,
)
from backend.api.models import (
    AskRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessage,
    ConversationResponse,
)
from backend.services.conversation_repo import ConversationRepository


class TestSpecParsing:
    """Test XML spec extraction from LLM responses."""

    def test_parse_query_spec(self):
        """Test extracting query_spec from response."""
        response = """Based on the data, here's the analysis.

<query_spec>
{"query_type": "aggregate", "group_by": {"fields": ["category"], "aggregates": [{"field": "revenue", "function": "sum"}]}}
</query_spec>

This shows revenue by category."""

        spec = _parse_spec_from_response(response, "query_spec")
        assert spec is not None
        assert spec["query_type"] == "aggregate"
        assert spec["group_by"]["fields"] == ["category"]

    def test_parse_chart_spec(self):
        """Test extracting chart_spec from response."""
        response = """Let me visualize this for you.

<chart_spec>
{"chart_type": "bar", "x_field": "month", "y_field": "sales", "title": "Monthly Sales"}
</chart_spec>"""

        spec = _parse_spec_from_response(response, "chart_spec")
        assert spec is not None
        assert spec["chart_type"] == "bar"
        assert spec["title"] == "Monthly Sales"

    def test_parse_missing_spec(self):
        """Test missing spec returns None."""
        response = "Just a plain text response without any specs."
        spec = _parse_spec_from_response(response, "query_spec")
        assert spec is None

    def test_parse_invalid_json(self):
        """Test invalid JSON returns None."""
        response = "<query_spec>not valid json</query_spec>"
        spec = _parse_spec_from_response(response, "query_spec")
        assert spec is None

    def test_strip_specs_from_response(self):
        """Test stripping spec blocks from response."""
        response = """Here's the analysis.

<query_spec>
{"query_type": "filter"}
</query_spec>

And a chart:

<chart_spec>
{"chart_type": "line"}
</chart_spec>

Final thoughts."""

        stripped = _strip_specs_from_response(response)
        assert "<query_spec>" not in stripped
        assert "<chart_spec>" not in stripped
        assert "Here's the analysis." in stripped
        assert "Final thoughts." in stripped


class TestConversationRepository:
    """Test conversation repository operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = MagicMock()
        mock.get.return_value = None
        mock.setex.return_value = True
        mock.zadd.return_value = 1
        mock.zrevrange.return_value = []
        mock.expire.return_value = True
        mock.zrem.return_value = 1
        mock.delete.return_value = 1
        return mock

    @pytest.fixture
    def repo(self, mock_redis):
        """Create repository with mocked Redis."""
        with patch("backend.services.conversation_repo.RedisManager") as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.client = mock_redis
            mock_manager_class.return_value = mock_manager
            return ConversationRepository(mock_manager)

    def test_create_conversation(self, repo, mock_redis):
        """Test creating a new conversation."""
        conv = repo.create("dataset-123", "user-456")

        assert conv["id"] is not None
        assert conv["dataset_id"] == "dataset-123"
        assert conv["user_id"] == "user-456"
        assert conv["messages"] == []
        assert mock_redis.setex.called
        assert mock_redis.zadd.called

    def test_get_conversation_not_found(self, repo, mock_redis):
        """Test getting non-existent conversation."""
        mock_redis.get.return_value = None
        conv = repo.get("nonexistent", "user-1")
        assert conv is None

    def test_get_conversation_wrong_user(self, repo, mock_redis):
        """Test user isolation - can't access other user's conversation."""
        mock_redis.get.return_value = json.dumps(
            {
                "id": "conv-1",
                "dataset_id": "ds-1",
                "user_id": "user-owner",
                "messages": [],
            }
        ).encode()

        conv = repo.get("conv-1", "user-attacker")
        assert conv is None

    def test_append_message(self, repo, mock_redis):
        """Test appending a message to conversation."""
        existing = {
            "id": "conv-1",
            "dataset_id": "ds-1",
            "user_id": "user-1",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "messages": [],
        }
        mock_redis.get.return_value = json.dumps(existing).encode()

        result = repo.append_message(
            "conv-1",
            "user",
            "What are the top products?",
        )

        assert result is not None
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "What are the top products?"

    def test_append_message_with_specs(self, repo, mock_redis):
        """Test appending message with query/chart specs."""
        existing = {
            "id": "conv-1",
            "dataset_id": "ds-1",
            "user_id": "user-1",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
            "messages": [{"role": "user", "content": "q", "timestamp": "t"}],
        }
        mock_redis.get.return_value = json.dumps(existing).encode()

        result = repo.append_message(
            "conv-1",
            "assistant",
            "Here's the analysis.",
            query_spec={"query_type": "aggregate"},
            chart_spec={"chart_type": "bar"},
            query_result={"rows": [], "columns": []},
        )

        assert result is not None
        assert len(result["messages"]) == 2
        assert result["messages"][1]["query_spec"] == {"query_type": "aggregate"}
        assert result["messages"][1]["chart_spec"] == {"chart_type": "bar"}


class TestAskRequestModel:
    """Test AskRequest model validation."""

    def test_valid_request(self):
        """Test valid ask request."""
        req = AskRequest(question="What are the top 5 products by revenue?")
        assert req.question == "What are the top 5 products by revenue?"
        assert req.conversation_id is None

    def test_request_with_conversation_id(self):
        """Test request with existing conversation."""
        req = AskRequest(
            question="And how did that change over time?",
            conversation_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert req.conversation_id == "550e8400-e29b-41d4-a716-446655440000"

    def test_question_too_short(self):
        """Test question minimum length validation."""
        with pytest.raises(ValueError):
            AskRequest(question="Hi")

    def test_question_too_long(self):
        """Test question maximum length validation."""
        with pytest.raises(ValueError):
            AskRequest(question="x" * 2001)


class TestConversationResponseModels:
    """Test conversation response models."""

    def test_conversation_response(self):
        """Test ConversationResponse model."""
        resp = ConversationResponse(
            id="conv-1",
            dataset_id="ds-1",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T01:00:00Z",
            message_count=5,
        )
        assert resp.id == "conv-1"
        assert resp.message_count == 5

    def test_conversation_detail_response(self):
        """Test ConversationDetailResponse with messages."""
        resp = ConversationDetailResponse(
            id="conv-1",
            dataset_id="ds-1",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T01:00:00Z",
            message_count=2,
            messages=[
                ConversationMessage(
                    role="user",
                    content="What's the total revenue?",
                    timestamp="2025-01-01T00:00:00Z",
                ),
                ConversationMessage(
                    role="assistant",
                    content="The total revenue is $1.2M.",
                    timestamp="2025-01-01T00:01:00Z",
                    query_spec={"query_type": "aggregate"},
                ),
            ],
        )
        assert len(resp.messages) == 2
        assert resp.messages[0].role == "user"
        assert resp.messages[1].query_spec is not None


class TestConversationListResponse:
    """Test conversation list response."""

    def test_empty_list(self):
        """Test empty conversation list."""
        resp = ConversationListResponse(conversations=[], total=0)
        assert resp.total == 0

    def test_populated_list(self):
        """Test list with conversations."""
        resp = ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id="conv-1",
                    dataset_id="ds-1",
                    created_at="2025-01-01T00:00:00Z",
                    updated_at="2025-01-01T00:00:00Z",
                    message_count=3,
                ),
                ConversationResponse(
                    id="conv-2",
                    dataset_id="ds-1",
                    created_at="2025-01-02T00:00:00Z",
                    updated_at="2025-01-02T00:00:00Z",
                    message_count=1,
                ),
            ],
            total=2,
        )
        assert resp.total == 2
        assert len(resp.conversations) == 2
