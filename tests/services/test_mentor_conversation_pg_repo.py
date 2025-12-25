"""Tests for MentorConversationPgRepository.

Tests PostgreSQL storage for mentor chat conversations.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


class TestMentorConversationPgRepository:
    """Tests for MentorConversationPgRepository."""

    @pytest.fixture
    def user_id(self) -> str:
        """Create a test user ID."""
        return str(uuid4())

    @pytest.fixture
    def mock_db_session(self):
        """Mock db_session context manager."""
        with patch("backend.services.mentor_conversation_pg_repo.db_session") as mock:
            conn_mock = MagicMock()
            cursor_mock = MagicMock()
            conn_mock.cursor.return_value.__enter__ = MagicMock(return_value=cursor_mock)
            conn_mock.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock.return_value.__enter__ = MagicMock(return_value=conn_mock)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield mock, conn_mock, cursor_mock

    def test_create_conversation(self, user_id: str):
        """Test creating a new conversation."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()

        with patch.object(repo, "_execute_returning") as mock_exec:
            mock_exec.return_value = {
                "id": uuid4(),
                "user_id": user_id,
                "persona": "general",
                "label": None,
                "context_sources": [],
                "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                "updated_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
            }

            result = repo.create(user_id, "general")

            assert result["user_id"] == user_id
            assert result["persona"] == "general"
            assert result["messages"] == []
            mock_exec.assert_called_once()

    def test_get_conversation_not_found(self, user_id: str):
        """Test getting a non-existent conversation."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()

        with patch.object(repo, "_execute_one") as mock_exec:
            mock_exec.return_value = None

            result = repo.get("nonexistent-id", user_id)

            assert result is None

    def test_get_conversation_with_messages(self, user_id: str):
        """Test getting a conversation with messages."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()
        conv_id = str(uuid4())

        with (
            patch.object(repo, "_execute_one") as mock_one,
            patch.object(repo, "_execute_query") as mock_query,
        ):
            mock_one.return_value = {
                "id": conv_id,
                "user_id": user_id,
                "persona": "action_coach",
                "label": "Test conversation",
                "context_sources": ["business_context"],
                "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                "updated_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
            }
            mock_query.return_value = [
                {
                    "id": str(uuid4()),
                    "role": "user",
                    "content": "Hello",
                    "persona": None,
                    "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                },
                {
                    "id": str(uuid4()),
                    "role": "assistant",
                    "content": "Hi there!",
                    "persona": "action_coach",
                    "created_at": datetime(2025, 12, 25, 0, 0, 1, tzinfo=UTC),
                },
            ]

            result = repo.get(conv_id, user_id)

            assert result is not None
            assert result["id"] == conv_id
            assert result["persona"] == "action_coach"
            assert len(result["messages"]) == 2
            assert result["messages"][0]["role"] == "user"
            assert result["messages"][1]["role"] == "assistant"

    def test_get_conversation_wrong_user(self, user_id: str):
        """Test that getting a conversation with wrong user returns None."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()
        conv_id = str(uuid4())
        other_user_id = str(uuid4())

        with patch.object(repo, "_execute_one") as mock_one:
            mock_one.return_value = {
                "id": conv_id,
                "user_id": other_user_id,  # Different user
                "persona": "general",
                "label": None,
                "context_sources": [],
                "created_at": "2025-12-25T00:00:00+00:00",
                "updated_at": "2025-12-25T00:00:00+00:00",
            }

            result = repo.get(conv_id, user_id)

            assert result is None

    def test_list_by_user(self, user_id: str):
        """Test listing conversations for a user."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()

        with (
            patch.object(repo, "_execute_one") as mock_one,
            patch.object(repo, "_execute_query") as mock_query,
        ):
            mock_one.return_value = {"count": 2}
            mock_query.return_value = [
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "persona": "general",
                    "label": None,
                    "context_sources": [],
                    "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                    "updated_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                    "message_count": 5,
                },
                {
                    "id": uuid4(),
                    "user_id": user_id,
                    "persona": "data_analyst",
                    "label": "Analysis chat",
                    "context_sources": ["datasets"],
                    "created_at": datetime(2025, 12, 24, 0, 0, 0, tzinfo=UTC),
                    "updated_at": datetime(2025, 12, 24, 0, 0, 0, tzinfo=UTC),
                    "message_count": 3,
                },
            ]

            conversations, total = repo.list_by_user(user_id, limit=20, offset=0)

            assert total == 2
            assert len(conversations) == 2
            assert conversations[0]["message_count"] == 5
            assert conversations[1]["persona"] == "data_analyst"

    def test_delete_conversation(self, user_id: str):
        """Test deleting a conversation."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()
        conv_id = str(uuid4())

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 1

            result = repo.delete(conv_id, user_id)

            assert result is True
            mock_count.assert_called_once()

    def test_delete_conversation_not_found(self, user_id: str):
        """Test deleting a non-existent conversation."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 0

            result = repo.delete("nonexistent-id", user_id)

            assert result is False

    def test_delete_all_for_user(self, user_id: str):
        """Test deleting all conversations for a user."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 5

            result = repo.delete_all_for_user(user_id)

            assert result == 5

    def test_update_label(self, user_id: str):
        """Test updating conversation label."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()
        conv_id = str(uuid4())

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 1

            result = repo.update_label(conv_id, "New Label", user_id)

            assert result is True

    def test_get_all_for_export(self, user_id: str):
        """Test getting all conversations for GDPR export."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()

        with patch.object(repo, "_execute_query") as mock_query:
            conv_id = uuid4()
            mock_query.side_effect = [
                # First call: get conversations
                [
                    {
                        "id": conv_id,
                        "user_id": user_id,
                        "persona": "general",
                        "label": None,
                        "context_sources": [],
                        "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                        "updated_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                    }
                ],
                # Second call: get messages for conversation
                [
                    {
                        "id": uuid4(),
                        "role": "user",
                        "content": "Hello",
                        "persona": None,
                        "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
                    }
                ],
            ]

            result = repo.get_all_for_export(user_id)

            assert len(result) == 1
            assert len(result[0]["messages"]) == 1


class TestMentorConversationPgRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repo_singleton(self):
        """Test that get_mentor_conversation_pg_repo returns singleton."""
        import backend.services.mentor_conversation_pg_repo as module

        # Reset singleton
        module._mentor_conversation_pg_repo = None

        repo1 = module.get_mentor_conversation_pg_repo()
        repo2 = module.get_mentor_conversation_pg_repo()

        assert repo1 is repo2

        # Clean up
        module._mentor_conversation_pg_repo = None


class TestRowConversion:
    """Tests for row conversion methods."""

    def test_row_to_conversation(self):
        """Test converting a database row to conversation dict."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()
        row = {
            "id": uuid4(),
            "user_id": "user-123",
            "persona": "action_coach",
            "label": "Test chat",
            "context_sources": ["business_context", "actions"],
            "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2025, 12, 25, 1, 0, 0, tzinfo=UTC),
        }
        messages = [
            {
                "role": "user",
                "content": "Hi",
                "timestamp": "2025-12-25T00:00:00+00:00",
                "persona": None,
            }
        ]

        result = repo._row_to_conversation(row, messages)

        assert isinstance(result["id"], str)
        assert result["user_id"] == "user-123"
        assert result["persona"] == "action_coach"
        assert result["label"] == "Test chat"
        assert result["context_sources"] == ["business_context", "actions"]
        assert result["messages"] == messages
        assert "2025-12-25" in result["created_at"]

    def test_row_to_message(self):
        """Test converting a database row to message dict."""
        from backend.services.mentor_conversation_pg_repo import (
            MentorConversationPgRepository,
        )

        repo = MentorConversationPgRepository()
        row = {
            "id": uuid4(),
            "role": "assistant",
            "content": "Here's my response",
            "persona": "data_analyst",
            "created_at": datetime(2025, 12, 25, 0, 0, 0, tzinfo=UTC),
        }

        result = repo._row_to_message(row)

        assert result["role"] == "assistant"
        assert result["content"] == "Here's my response"
        assert result["persona"] == "data_analyst"
        assert "2025-12-25" in result["timestamp"]
