"""Tests for mentor chat API endpoints."""

import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


class TestMentorPersonaListing:
    """Tests for mentor persona listing."""

    def test_list_all_personas(self):
        """Should return all available personas with metadata."""
        from backend.services.mentor_persona import list_all_personas

        personas = list_all_personas()

        assert len(personas) == 3
        persona_ids = [p.id for p in personas]
        assert "general" in persona_ids
        assert "action_coach" in persona_ids
        assert "data_analyst" in persona_ids

        # Check each persona has required fields
        for persona in personas:
            assert persona.id
            assert persona.name
            assert persona.description
            assert isinstance(persona.expertise, list)
            assert persona.icon

    def test_get_persona_by_id(self):
        """Should return persona by ID or None."""
        from backend.services.mentor_persona import get_persona_by_id

        general = get_persona_by_id("general")
        assert general is not None
        assert general.id == "general"
        assert general.name == "General Business Advisor"

        action = get_persona_by_id("action_coach")
        assert action is not None
        assert "task" in action.description.lower() or "execution" in action.description.lower()

        invalid = get_persona_by_id("invalid_persona")
        assert invalid is None

    def test_persona_to_dict(self):
        """Persona should serialize to dict correctly."""
        from backend.services.mentor_persona import MentorPersona

        persona = MentorPersona(
            id="test",
            name="Test Persona",
            description="A test persona",
            expertise=["testing", "mocking"],
            icon="flask",
        )

        result = persona.to_dict()
        assert result["id"] == "test"
        assert result["name"] == "Test Persona"
        assert result["description"] == "A test persona"
        assert result["expertise"] == ["testing", "mocking"]
        assert result["icon"] == "flask"


class TestMentorPersonaSelection:
    """Tests for mentor persona auto-selection."""

    def test_auto_select_action_coach(self):
        """Action keywords should select action_coach persona."""
        from backend.services.mentor_persona import auto_select_persona

        # Task-related questions (need 2+ keywords to trigger)
        assert auto_select_persona("Help me prioritize my tasks and actions") == "action_coach"
        assert auto_select_persona("I'm stuck on a task, need to focus") == "action_coach"
        assert auto_select_persona("What's blocking my progress on the deadline?") == "action_coach"

    def test_auto_select_data_analyst(self):
        """Data keywords should select data_analyst persona."""
        from backend.services.mentor_persona import auto_select_persona

        assert auto_select_persona("Can you analyze my sales data?") == "data_analyst"
        assert auto_select_persona("What metrics should I track?") == "data_analyst"
        assert auto_select_persona("Help me understand this trend in revenue") == "data_analyst"

    def test_auto_select_general(self):
        """Ambiguous or general questions should select general persona."""
        from backend.services.mentor_persona import auto_select_persona

        assert auto_select_persona("How should I grow my business?") == "general"
        assert auto_select_persona("What's your advice?") == "general"
        assert auto_select_persona("Hello") == "general"

    def test_validate_persona(self):
        """validate_persona should return valid personas or default to general."""
        from backend.services.mentor_persona import validate_persona

        assert validate_persona("general") == "general"
        assert validate_persona("action_coach") == "action_coach"
        assert validate_persona("data_analyst") == "data_analyst"
        assert validate_persona("invalid") == "general"
        assert validate_persona(None) == "general"


class TestMentorPrompts:
    """Tests for mentor prompt formatting."""

    def test_get_mentor_system_prompt(self):
        """Should return correct system prompt for each persona."""
        from bo1.prompts.mentor import get_mentor_system_prompt

        general = get_mentor_system_prompt("general")
        assert "business mentor" in general.lower()

        action = get_mentor_system_prompt("action_coach")
        assert "action" in action.lower() or "execution" in action.lower()

        data = get_mentor_system_prompt("data_analyst")
        assert "data" in data.lower() or "analyst" in data.lower()

    def test_format_business_context(self):
        """Should format business context as XML."""
        from bo1.prompts.mentor import format_business_context

        context = {
            "company_name": "Test Corp",
            "business_model": "SaaS",
            "revenue": "$100k MRR",
        }

        result = format_business_context(context)
        assert "<business_context>" in result
        assert "Test Corp" in result
        assert "SaaS" in result

    def test_format_business_context_empty(self):
        """Should return empty string for empty context."""
        from bo1.prompts.mentor import format_business_context

        assert format_business_context(None) == ""
        assert format_business_context({}) == ""

    def test_format_active_actions(self):
        """Should format actions grouped by status."""
        from bo1.prompts.mentor import format_active_actions

        actions = [
            {"title": "Task 1", "status": "in_progress", "priority": "high"},
            {"title": "Task 2", "status": "todo", "priority": "medium"},
        ]

        result = format_active_actions(actions)
        assert "<active_actions>" in result
        assert "Task 1" in result
        assert "<in_progress>" in result

    def test_build_mentor_prompt(self):
        """Should combine all context into user prompt."""
        from bo1.prompts.mentor import build_mentor_prompt

        prompt = build_mentor_prompt(
            question="How do I grow?",
            business_context="<business_context>...</business_context>",
            actions_context="<active_actions>...</active_actions>",
        )

        assert "<question>How do I grow?</question>" in prompt
        assert "<business_context>" in prompt
        assert "<active_actions>" in prompt


class TestMentorConversationRepo:
    """Tests for mentor conversation repository."""

    def test_create_conversation(self):
        """Should create a new conversation."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        repo = MentorConversationRepository(redis_manager=mock_redis)

        result = repo.create("user-123", "general")

        assert result["user_id"] == "user-123"
        assert result["persona"] == "general"
        assert "id" in result
        assert "messages" in result
        mock_redis.client.setex.assert_called_once()

    def test_append_message(self):
        """Should append message to conversation."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()

        # Mock existing conversation
        existing_conv = {
            "id": "conv-123",
            "user_id": "user-123",
            "persona": "general",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "messages": [],
            "context_sources": [],
        }
        mock_redis.client.get.return_value = json.dumps(existing_conv)

        repo = MentorConversationRepository(redis_manager=mock_redis)
        result = repo.append_message("conv-123", "user", "Hello", persona="general")

        assert result is not None
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"


class TestMentorContextService:
    """Tests for mentor context service."""

    def test_gather_context(self):
        """Should gather context from all sources."""
        from backend.services.mentor_context import MentorContext, MentorContextService

        # Mock repositories
        mock_user_repo = MagicMock()
        mock_user_repo.get_context.return_value = {"company_name": "Test"}

        mock_session_repo = MagicMock()
        mock_session_repo.list_by_user.return_value = []

        mock_action_repo = MagicMock()
        mock_action_repo.get_by_user.return_value = []

        mock_dataset_repo = MagicMock()
        mock_dataset_repo.list_by_user.return_value = ([], 0)

        service = MentorContextService(
            user_repo=mock_user_repo,
            session_repo=mock_session_repo,
            action_repo=mock_action_repo,
            dataset_repo=mock_dataset_repo,
        )

        context = service.gather_context("user-123")

        assert isinstance(context, MentorContext)
        assert context.business_context == {"company_name": "Test"}

    def test_sources_used(self):
        """Should correctly report which sources have data."""
        from backend.services.mentor_context import MentorContext

        context = MentorContext(
            business_context={"company": "Test"},
            recent_meetings=None,
            active_actions=[{"title": "Task"}],
            datasets=None,
        )

        sources = context.sources_used()
        assert "business_context" in sources
        assert "active_actions" in sources
        assert "recent_meetings" not in sources
        assert "datasets" not in sources
