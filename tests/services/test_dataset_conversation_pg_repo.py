"""Tests for DatasetConversationPgRepository.

Tests PostgreSQL storage for dataset Q&A conversations.
"""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest


class TestDatasetConversationPgRepository:
    """Tests for DatasetConversationPgRepository."""

    @pytest.fixture
    def user_id(self) -> str:
        """Create a test user ID."""
        return str(uuid4())

    @pytest.fixture
    def dataset_id(self) -> str:
        """Create a test dataset ID."""
        return str(uuid4())

    def test_create_conversation(self, user_id: str, dataset_id: str):
        """Test creating a new dataset conversation."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with patch.object(repo, "_execute_returning") as mock_exec:
            mock_exec.return_value = {
                "id": uuid4(),
                "dataset_id": dataset_id,
                "user_id": user_id,
                "label": None,
                "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
            }

            result = repo.create(dataset_id, user_id)

            assert result["dataset_id"] == dataset_id
            assert result["user_id"] == user_id
            assert result["messages"] == []
            mock_exec.assert_called_once()

    def test_get_conversation_not_found(self, user_id: str):
        """Test getting a non-existent conversation."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with patch.object(repo, "_execute_one") as mock_exec:
            mock_exec.return_value = None

            result = repo.get("nonexistent-id", user_id)

            assert result is None

    def test_get_conversation_with_messages(self, user_id: str, dataset_id: str):
        """Test getting a conversation with messages."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        conv_id = str(uuid4())

        with (
            patch.object(repo, "_execute_one") as mock_one,
            patch.object(repo, "_execute_query") as mock_query,
        ):
            mock_one.return_value = {
                "id": conv_id,
                "dataset_id": dataset_id,
                "user_id": user_id,
                "label": "Test conversation",
                "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                "updated_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
            }
            mock_query.return_value = [
                {
                    "id": str(uuid4()),
                    "role": "user",
                    "content": "What is the average sales?",
                    "query_spec": None,
                    "chart_spec": None,
                    "query_result": None,
                    "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                },
                {
                    "id": str(uuid4()),
                    "role": "assistant",
                    "content": "The average sales is $1,234",
                    "query_spec": {"columns": ["sales"], "aggregation": "avg"},
                    "chart_spec": {"type": "bar"},
                    "query_result": {"value": 1234},
                    "created_at": datetime(2026, 1, 2, 0, 0, 1, tzinfo=UTC),
                },
            ]

            result = repo.get(conv_id, user_id)

            assert result is not None
            assert result["id"] == conv_id
            assert len(result["messages"]) == 2
            assert result["messages"][0]["role"] == "user"
            assert result["messages"][1]["role"] == "assistant"
            assert result["messages"][1]["query_spec"] is not None

    def test_get_conversation_wrong_user(self, user_id: str, dataset_id: str):
        """Test that getting a conversation with wrong user returns None."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        conv_id = str(uuid4())
        other_user_id = str(uuid4())

        with patch.object(repo, "_execute_one") as mock_one:
            mock_one.return_value = {
                "id": conv_id,
                "dataset_id": dataset_id,
                "user_id": other_user_id,  # Different user
                "label": None,
                "created_at": "2026-01-02T00:00:00+00:00",
                "updated_at": "2026-01-02T00:00:00+00:00",
            }

            result = repo.get(conv_id, user_id)

            assert result is None

    def test_list_by_dataset(self, user_id: str, dataset_id: str):
        """Test listing conversations for a dataset."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with (
            patch.object(repo, "_execute_one") as mock_one,
            patch.object(repo, "_execute_query") as mock_query,
        ):
            mock_one.return_value = {"count": 2}
            mock_query.return_value = [
                {
                    "id": uuid4(),
                    "dataset_id": dataset_id,
                    "user_id": user_id,
                    "label": None,
                    "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                    "updated_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                    "message_count": 5,
                },
                {
                    "id": uuid4(),
                    "dataset_id": dataset_id,
                    "user_id": user_id,
                    "label": "Analysis chat",
                    "created_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                    "updated_at": datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
                    "message_count": 3,
                },
            ]

            conversations, total = repo.list_by_dataset(dataset_id, user_id, limit=20, offset=0)

            assert total == 2
            assert len(conversations) == 2
            assert conversations[0]["message_count"] == 5
            assert conversations[1]["message_count"] == 3

    def test_delete_conversation(self, user_id: str):
        """Test deleting a conversation."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        conv_id = str(uuid4())

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 1

            result = repo.delete(conv_id, user_id)

            assert result is True
            mock_count.assert_called_once()

    def test_delete_conversation_not_found(self, user_id: str):
        """Test deleting a non-existent conversation."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 0

            result = repo.delete("nonexistent-id", user_id)

            assert result is False

    def test_delete_all_for_user(self, user_id: str):
        """Test deleting all conversations for a user."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 5

            result = repo.delete_all_for_user(user_id)

            assert result == 5

    def test_delete_all_for_dataset(self, user_id: str, dataset_id: str):
        """Test deleting all conversations for a dataset."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 3

            result = repo.delete_all_for_dataset(dataset_id, user_id)

            assert result == 3

    def test_update_label(self, user_id: str):
        """Test updating conversation label."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        conv_id = str(uuid4())

        with patch.object(repo, "_execute_count") as mock_count:
            mock_count.return_value = 1

            result = repo.update_label(conv_id, "New Label", user_id)

            assert result is True

    def test_get_all_for_export(self, user_id: str, dataset_id: str):
        """Test getting all conversations for GDPR export."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()

        with patch.object(repo, "_execute_query") as mock_query:
            conv_id = uuid4()
            mock_query.side_effect = [
                # First call: get conversations
                [
                    {
                        "id": conv_id,
                        "dataset_id": dataset_id,
                        "user_id": user_id,
                        "label": None,
                        "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                        "updated_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                    }
                ],
                # Second call: get messages for conversation
                [
                    {
                        "id": uuid4(),
                        "role": "user",
                        "content": "Hello",
                        "query_spec": None,
                        "chart_spec": None,
                        "query_result": None,
                        "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
                    }
                ],
            ]

            result = repo.get_all_for_export(user_id)

            assert len(result) == 1
            assert len(result[0]["messages"]) == 1


class TestDatasetConversationPgRepositorySingleton:
    """Tests for singleton pattern."""

    def test_get_repo_singleton(self):
        """Test that get_dataset_conversation_pg_repo returns singleton."""
        import backend.services.dataset_conversation_pg_repo as module

        # Reset singleton
        module._dataset_conversation_pg_repo = None

        repo1 = module.get_dataset_conversation_pg_repo()
        repo2 = module.get_dataset_conversation_pg_repo()

        assert repo1 is repo2

        # Clean up
        module._dataset_conversation_pg_repo = None


class TestRowConversion:
    """Tests for row conversion methods."""

    def test_row_to_conversation(self):
        """Test converting a database row to conversation dict."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        row = {
            "id": uuid4(),
            "dataset_id": uuid4(),
            "user_id": "user-123",
            "label": "Test chat",
            "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
            "updated_at": datetime(2026, 1, 2, 1, 0, 0, tzinfo=UTC),
        }
        messages = [
            {
                "role": "user",
                "content": "Hi",
                "timestamp": "2026-01-02T00:00:00+00:00",
            }
        ]

        result = repo._row_to_conversation(row, messages)

        assert isinstance(result["id"], str)
        assert result["user_id"] == "user-123"
        assert result["label"] == "Test chat"
        assert result["messages"] == messages
        assert "2026-01-02" in result["created_at"]

    def test_row_to_message(self):
        """Test converting a database row to message dict."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        row = {
            "id": uuid4(),
            "role": "assistant",
            "content": "Here's the result",
            "query_spec": {"columns": ["sales"], "aggregation": "sum"},
            "chart_spec": {"type": "line"},
            "query_result": {"value": 5000},
            "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
        }

        result = repo._row_to_message(row)

        assert result["role"] == "assistant"
        assert result["content"] == "Here's the result"
        assert result["query_spec"]["aggregation"] == "sum"
        assert result["chart_spec"]["type"] == "line"
        assert "2026-01-02" in result["timestamp"]

    def test_row_to_message_without_specs(self):
        """Test converting a database row to message dict without optional fields."""
        from backend.services.dataset_conversation_pg_repo import (
            DatasetConversationPgRepository,
        )

        repo = DatasetConversationPgRepository()
        row = {
            "id": uuid4(),
            "role": "user",
            "content": "What's the total?",
            "query_spec": None,
            "chart_spec": None,
            "query_result": None,
            "created_at": datetime(2026, 1, 2, 0, 0, 0, tzinfo=UTC),
        }

        result = repo._row_to_message(row)

        assert result["role"] == "user"
        assert result["content"] == "What's the total?"
        assert "query_spec" not in result
        assert "chart_spec" not in result
        assert "query_result" not in result
