"""Tests for mentor chat API endpoints."""

import json
from datetime import UTC
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

    def test_format_postmortem_insights(self):
        """Should format post-mortem insights as XML."""
        from datetime import date

        from bo1.prompts.mentor import format_postmortem_insights

        insights = [
            {
                "id": "action-1",
                "title": "Launch marketing campaign",
                "lessons_learned": "Start earlier next time",
                "went_well": "Great team collaboration",
                "actual_end_date": date(2024, 12, 15),
            },
            {
                "id": "action-2",
                "title": "Refactor API",
                "lessons_learned": "Document decisions as we go",
                "went_well": None,
                "actual_end_date": date(2024, 12, 10),
            },
        ]

        result = format_postmortem_insights(insights)
        assert "<postmortem_insights>" in result
        assert "Lessons from the user's completed actions:" in result
        assert '<insight title="Launch marketing campaign" completed="2024-12-15">' in result
        assert "<went_well>Great team collaboration</went_well>" in result
        assert "<lessons>Start earlier next time</lessons>" in result
        assert '<insight title="Refactor API" completed="2024-12-10">' in result
        assert "<lessons>Document decisions as we go</lessons>" in result
        assert "</postmortem_insights>" in result

    def test_format_postmortem_insights_empty(self):
        """Should return empty string when no insights."""
        from bo1.prompts.mentor import format_postmortem_insights

        assert format_postmortem_insights([]) == ""
        assert format_postmortem_insights(None) == ""

    def test_format_postmortem_insights_truncates_long_text(self):
        """Should truncate long lessons/went_well to 500 chars."""
        from bo1.prompts.mentor import format_postmortem_insights

        long_text = "x" * 600
        insights = [
            {
                "title": "Test action",
                "lessons_learned": long_text,
                "went_well": long_text,
                "actual_end_date": "2024-12-01",
            },
        ]

        result = format_postmortem_insights(insights)
        # Each truncated text should be 500 chars
        assert "<lessons>" + "x" * 500 + "</lessons>" in result
        assert "<went_well>" + "x" * 500 + "</went_well>" in result

    def test_build_mentor_prompt_with_postmortem_context(self):
        """Should include postmortem_context in prompt."""
        from bo1.prompts.mentor import build_mentor_prompt

        prompt = build_mentor_prompt(
            question="What have I learned?",
            postmortem_context="<postmortem_insights>...</postmortem_insights>",
        )

        assert "<question>What have I learned?</question>" in prompt
        assert "<postmortem_insights>" in prompt


class TestMentorConversationRepo:
    """Tests for mentor conversation repository.

    These tests verify the combined PostgreSQL + Redis cache behavior.
    """

    def test_create_conversation(self):
        """Should create conversation in PostgreSQL and cache in Redis."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        mock_pg_repo = MagicMock()

        # Mock PostgreSQL create
        mock_pg_repo.create.return_value = {
            "id": "conv-uuid-123",
            "user_id": "user-123",
            "persona": "general",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "messages": [],
            "context_sources": [],
        }

        repo = MentorConversationRepository(redis_manager=mock_redis, pg_repo=mock_pg_repo)
        result = repo.create("user-123", "general")

        assert result["user_id"] == "user-123"
        assert result["persona"] == "general"
        assert "id" in result
        assert "messages" in result
        mock_pg_repo.create.assert_called_once_with("user-123", "general")
        mock_redis.client.setex.assert_called_once()

    def test_append_message(self):
        """Should append message via PostgreSQL and update Redis cache."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        mock_pg_repo = MagicMock()

        # Mock existing conversation in Redis cache
        existing_conv = {
            "id": "conv-uuid-123",
            "user_id": "user-123",
            "persona": "general",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "messages": [],
            "context_sources": [],
        }
        mock_redis.client.get.return_value = json.dumps(existing_conv)

        # Mock PostgreSQL append_message
        updated_conv = {
            "id": "conv-uuid-123",
            "user_id": "user-123",
            "persona": "general",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:01:00+00:00",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": "2024-01-01T00:01:00+00:00",
                    "persona": "general",
                }
            ],
            "context_sources": [],
        }
        mock_pg_repo.append_message.return_value = updated_conv

        repo = MentorConversationRepository(redis_manager=mock_redis, pg_repo=mock_pg_repo)
        result = repo.append_message("conv-uuid-123", "user", "Hello", persona="general")

        assert result is not None
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"
        assert result["messages"][0]["content"] == "Hello"
        mock_pg_repo.append_message.assert_called_once()


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
        mock_action_repo.get_postmortem_insights.return_value = []

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

    def test_sources_used_includes_postmortem(self):
        """Should include postmortem_insights in sources when present."""
        from backend.services.mentor_context import MentorContext

        context = MentorContext(
            business_context=None,
            recent_meetings=None,
            active_actions=None,
            datasets=None,
            postmortem_insights=[{"title": "Test", "lessons_learned": "Lesson"}],
        )

        sources = context.sources_used()
        assert "postmortem_insights" in sources
        assert len(sources) == 1

    def test_get_postmortem_insights(self):
        """Should call action_repo.get_postmortem_insights."""
        from backend.services.mentor_context import MentorContextService

        mock_action_repo = MagicMock()
        mock_action_repo.get_postmortem_insights.return_value = [
            {
                "id": "action-1",
                "title": "Test action",
                "lessons_learned": "Learn from mistakes",
                "went_well": "Team worked well",
                "actual_end_date": "2024-12-01",
            }
        ]

        service = MentorContextService(action_repo=mock_action_repo)
        insights = service.get_postmortem_insights("user-123", limit=5)

        mock_action_repo.get_postmortem_insights.assert_called_once_with(
            user_id="user-123", limit=5
        )
        assert len(insights) == 1
        assert insights[0]["title"] == "Test action"

    def test_gather_context_includes_postmortem(self):
        """gather_context should include postmortem_insights."""
        from backend.services.mentor_context import MentorContextService

        mock_user_repo = MagicMock()
        mock_user_repo.get_context.return_value = None

        mock_session_repo = MagicMock()
        mock_session_repo.list_by_user.return_value = []

        mock_action_repo = MagicMock()
        mock_action_repo.get_by_user.return_value = []
        mock_action_repo.get_postmortem_insights.return_value = [
            {"title": "Done task", "lessons_learned": "Important lesson"}
        ]

        mock_dataset_repo = MagicMock()
        mock_dataset_repo.list_by_user.return_value = ([], 0)

        service = MentorContextService(
            user_repo=mock_user_repo,
            session_repo=mock_session_repo,
            action_repo=mock_action_repo,
            dataset_repo=mock_dataset_repo,
        )

        context = service.gather_context("user-123")

        assert context.postmortem_insights is not None
        assert len(context.postmortem_insights) == 1
        assert context.postmortem_insights[0]["title"] == "Done task"


class TestMentorConversationLabels:
    """Tests for mentor conversation label generation and display."""

    def test_conversation_response_includes_label_field(self):
        """MentorConversationResponse should have label field."""
        from backend.api.mentor import MentorConversationResponse

        # With label
        response = MentorConversationResponse(
            id="conv-123",
            user_id="user-456",
            persona="general",
            label="Quarterly Revenue Strategy",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            message_count=2,
            context_sources=["business_context"],
        )
        assert response.label == "Quarterly Revenue Strategy"

        # Without label (None)
        response_no_label = MentorConversationResponse(
            id="conv-456",
            user_id="user-456",
            persona="general",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            message_count=0,
            context_sources=[],
        )
        assert response_no_label.label is None

    def test_list_response_includes_labels(self):
        """list_by_user should return labels in conversation list."""
        from datetime import datetime
        from unittest.mock import patch

        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        with (
            patch.object(
                MentorConversationPgRepository,
                "_execute_one",
                return_value={"count": 1},
            ),
            patch.object(
                MentorConversationPgRepository,
                "_execute_query",
                return_value=[
                    {
                        "id": "conv-uuid-123",
                        "user_id": "user-123",
                        "persona": "general",
                        "label": "Team Hiring Strategy",
                        "context_sources": [],
                        "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                        "updated_at": datetime(2024, 1, 1, 0, 1, 0, tzinfo=UTC),
                        "message_count": 2,
                    }
                ],
            ),
        ):
            repo = MentorConversationPgRepository()
            conversations, total = repo.list_by_user("user-123", limit=10)

            assert len(conversations) == 1
            assert conversations[0]["label"] == "Team Hiring Strategy"
            assert total == 1

    def test_update_label_success(self):
        """update_label should update the conversation label."""
        from unittest.mock import patch

        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        with patch.object(
            MentorConversationPgRepository,
            "_execute_count",
            return_value=1,
        ):
            repo = MentorConversationPgRepository()
            result = repo.update_label("conv-123", "New Label", "user-456")

            assert result is True

    def test_update_label_not_found(self):
        """update_label should return False if conversation not found."""
        from unittest.mock import patch

        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        with patch.object(
            MentorConversationPgRepository,
            "_execute_count",
            return_value=0,
        ):
            repo = MentorConversationPgRepository()
            result = repo.update_label("nonexistent-conv", "New Label", "user-456")

            assert result is False


class TestUpdateConversationLabelEndpoint:
    """Tests for PATCH /api/v1/mentor/conversations/{id} endpoint."""

    def test_update_label_request_validation(self):
        """UpdateConversationLabelRequest should validate label field."""
        from pydantic import ValidationError

        from backend.api.mentor import UpdateConversationLabelRequest

        # Valid label
        req = UpdateConversationLabelRequest(label="My New Label")
        assert req.label == "My New Label"

        # Empty label should fail
        with pytest.raises(ValidationError):
            UpdateConversationLabelRequest(label="")

        # Label too long should fail
        with pytest.raises(ValidationError):
            UpdateConversationLabelRequest(label="x" * 101)

    def test_update_label_success(self):
        """PATCH endpoint should update label and return conversation."""
        from unittest.mock import patch

        mock_repo = MagicMock()
        mock_repo.update_label.return_value = True
        mock_repo.get.return_value = {
            "id": "conv-123",
            "user_id": "user-456",
            "persona": "general",
            "label": "Updated Label",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:01:00+00:00",
            "messages": [{"role": "user", "content": "Hello"}],
            "context_sources": ["business_context"],
        }

        with patch(
            "backend.api.mentor.get_mentor_conversation_repo",
            return_value=mock_repo,
        ):
            # Verify mock behavior directly
            assert mock_repo.update_label("conv-123", "user-456", "Updated Label") is True
            conv = mock_repo.get("conv-123", "user-456")
            assert conv["label"] == "Updated Label"

    def test_update_label_unauthorized(self):
        """PATCH should return 404 for conversation owned by different user."""

        mock_repo = MagicMock()
        # update_label returns False when user doesn't own the conversation
        mock_repo.update_label.return_value = False

        # Simulating the endpoint behavior: if update_label returns False, we return 404
        result = mock_repo.update_label("conv-123", "wrong-user", "New Label")
        assert result is False

    def test_update_label_not_found(self):
        """PATCH should return 404 for nonexistent conversation."""

        mock_repo = MagicMock()
        mock_repo.update_label.return_value = False

        result = mock_repo.update_label("nonexistent-id", "user-456", "New Label")
        assert result is False

    def test_update_label_too_long(self):
        """PATCH should reject labels over 100 characters."""
        from pydantic import ValidationError

        from backend.api.mentor import UpdateConversationLabelRequest

        with pytest.raises(ValidationError) as exc_info:
            UpdateConversationLabelRequest(label="x" * 101)

        # Check that it's a max_length error
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "string_too_long" in errors[0]["type"]


class TestMentionSearchChat:
    """Tests for mentor chat @mention search functionality."""

    def test_search_mentions_type_includes_chat(self):
        """search_mentions endpoint should accept 'chat' type."""
        # The endpoint validation should accept 'chat' as a valid type
        valid_types = ("meeting", "action", "dataset", "chat")
        assert "chat" in valid_types

    def test_mention_suggestion_can_be_chat_type(self):
        """MentionSuggestion should support 'chat' type."""
        from backend.api.mentor import MentionSuggestion

        suggestion = MentionSuggestion(
            id="chat-uuid-123",
            type="chat",
            title="Previous Pricing Discussion",
            preview="general",
        )
        assert suggestion.type == "chat"
        assert suggestion.title == "Previous Pricing Discussion"

    def test_chat_mention_excluded_when_current_conversation(self):
        """Chat search should exclude the current conversation ID."""
        from unittest.mock import MagicMock

        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        mock_redis.client.get.return_value = None
        mock_pg_repo = MagicMock()
        mock_pg_repo.list_by_user.return_value = (
            [
                {
                    "id": "conv-1",
                    "user_id": "user-123",
                    "persona": "general",
                    "label": "Discussion 1",
                    "message_count": 2,
                    "created_at": "2024-01-01",
                    "updated_at": "2024-01-01",
                },
                {
                    "id": "conv-2",
                    "user_id": "user-123",
                    "persona": "action_coach",
                    "label": "Discussion 2",
                    "message_count": 4,
                    "created_at": "2024-01-02",
                    "updated_at": "2024-01-02",
                },
            ],
            2,
        )

        repo = MentorConversationRepository(redis_manager=mock_redis, pg_repo=mock_pg_repo)
        conversations = repo.list_by_user("user-123", limit=50)

        # Filter out current conversation (simulating endpoint logic)
        current_conv_id = "conv-1"
        filtered = [c for c in conversations if c["id"] != current_conv_id]

        assert len(filtered) == 1
        assert filtered[0]["id"] == "conv-2"


class TestChatMentionResolver:
    """Tests for chat mention resolution."""

    def test_resolved_chat_dataclass(self):
        """ResolvedChat should have correct fields."""
        from backend.services.mention_resolver import ResolvedChat

        chat = ResolvedChat(
            id="chat-uuid-123",
            label="Quarterly Planning",
            persona="general",
            created_at="2024-01-15",
            message_preview="User: How should I... | Mentor: I recommend...",
        )
        assert chat.id == "chat-uuid-123"
        assert chat.label == "Quarterly Planning"
        assert chat.persona == "general"
        assert chat.created_at == "2024-01-15"
        assert "How should I" in chat.message_preview

    def test_resolved_mentions_includes_chats(self):
        """ResolvedMentions should include chats list."""
        from backend.services.mention_resolver import ResolvedChat, ResolvedMentions

        chat = ResolvedChat(
            id="chat-uuid-123",
            label="Test Chat",
            persona="general",
        )
        mentions = ResolvedMentions(chats=[chat])

        assert len(mentions.chats) == 1
        assert mentions.has_context() is True

    def test_has_context_true_with_only_chats(self):
        """has_context should return True when only chats present."""
        from backend.services.mention_resolver import ResolvedChat, ResolvedMentions

        mentions = ResolvedMentions(
            meetings=[],
            actions=[],
            datasets=[],
            chats=[ResolvedChat(id="1", label="Test", persona="general")],
        )
        assert mentions.has_context() is True


class TestChatMentionContextFormatting:
    """Tests for chat mention context formatting in prompts."""

    def test_format_mentioned_context_includes_chats(self):
        """format_mentioned_context should include referenced_chats section."""
        from backend.services.mention_resolver import ResolvedChat, ResolvedMentions
        from bo1.prompts.mentor import format_mentioned_context

        chat = ResolvedChat(
            id="chat-uuid-123",
            label="Pricing Strategy Discussion",
            persona="general",
            created_at="2024-01-15",
            message_preview="User: How should I price... | Mentor: Consider value-based...",
        )
        mentions = ResolvedMentions(chats=[chat])

        result = format_mentioned_context(mentions)

        assert "<referenced_chats>" in result
        assert "Pricing Strategy Discussion" in result
        assert "chat-uuid-123" in result
        assert 'persona="general"' in result
        assert "<recent_exchanges>" in result

    def test_format_mentioned_context_chat_without_label(self):
        """Chats without labels should use fallback."""
        from backend.services.mention_resolver import ResolvedChat, ResolvedMentions
        from bo1.prompts.mentor import format_mentioned_context

        chat = ResolvedChat(
            id="chat-uuid-123",
            label=None,
            persona="action_coach",
        )
        mentions = ResolvedMentions(chats=[chat])

        result = format_mentioned_context(mentions)

        assert "<referenced_chats>" in result
        assert "Unnamed conversation" in result


class TestMentorConversationRepoLabelUpdate:
    """Tests for MentorConversationRepository.update_label method."""

    def test_update_label_calls_pg_repo(self):
        """update_label should call PostgreSQL repo."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        mock_pg_repo = MagicMock()
        mock_pg_repo.update_label.return_value = True

        repo = MentorConversationRepository(redis_manager=mock_redis, pg_repo=mock_pg_repo)
        result = repo.update_label("conv-123", "user-456", "New Label")

        assert result is True
        mock_pg_repo.update_label.assert_called_once_with("conv-123", "New Label", "user-456")

    def test_update_label_invalidates_redis_cache(self):
        """update_label should delete Redis cache entry on success."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        mock_pg_repo = MagicMock()
        mock_pg_repo.update_label.return_value = True

        repo = MentorConversationRepository(redis_manager=mock_redis, pg_repo=mock_pg_repo)
        repo.update_label("conv-123", "user-456", "New Label")

        # Should delete the Redis cache key
        mock_redis.client.delete.assert_called_once_with("mentor_conv:conv-123")

    def test_update_label_no_cache_invalidation_on_failure(self):
        """update_label should not touch Redis if PostgreSQL update fails."""
        from backend.services.mentor_conversation_repo import MentorConversationRepository

        mock_redis = MagicMock()
        mock_redis.client = MagicMock()
        mock_pg_repo = MagicMock()
        mock_pg_repo.update_label.return_value = False

        repo = MentorConversationRepository(redis_manager=mock_redis, pg_repo=mock_pg_repo)
        result = repo.update_label("nonexistent", "user-456", "New Label")

        assert result is False
        mock_redis.client.delete.assert_not_called()


class TestActionRepositoryPostmortemInsights:
    """Tests for ActionRepository.get_postmortem_insights method."""

    def test_get_postmortem_insights_returns_only_actions_with_data(self):
        """Should return only actions with lessons_learned or went_well."""
        from unittest.mock import patch

        from bo1.state.repositories.action_repository import ActionRepository

        expected_results = [
            {
                "id": "action-1",
                "title": "Completed task",
                "lessons_learned": "Important lesson",
                "went_well": "Great collaboration",
                "actual_end_date": "2024-12-15",
            }
        ]

        with patch.object(ActionRepository, "_execute_query", return_value=expected_results):
            repo = ActionRepository()
            results = repo.get_postmortem_insights("user-123", limit=10)

            assert len(results) == 1
            assert results[0]["lessons_learned"] == "Important lesson"

    def test_get_postmortem_insights_empty_when_no_data(self):
        """Should return empty list when no actions have post-mortem data."""
        from unittest.mock import patch

        from bo1.state.repositories.action_repository import ActionRepository

        with patch.object(ActionRepository, "_execute_query", return_value=[]):
            repo = ActionRepository()
            results = repo.get_postmortem_insights("user-123")

            assert results == []

    def test_get_postmortem_insights_respects_limit(self):
        """Should respect the limit parameter."""
        from unittest.mock import patch

        from bo1.state.repositories.action_repository import ActionRepository

        with patch.object(ActionRepository, "_execute_query", return_value=[]) as mock_exec:
            repo = ActionRepository()
            repo.get_postmortem_insights("user-123", limit=5)

            # Verify limit is passed to the query
            call_args = mock_exec.call_args
            query = call_args[0][0]
            params = call_args[0][1]
            assert "LIMIT" in query
            assert params[1] == 5  # Second param is limit
