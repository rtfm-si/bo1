"""Tests for GDPR service."""

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.services.gdpr import (
    CONV_INDEX_PREFIX,
    GDPRError,
    _collect_conversations,
    _delete_user_conversations,
    _hash_text,
    _serialize_for_json,
    collect_user_data,
    delete_user_data,
)


class TestHashText:
    """Tests for text hashing utility."""

    def test_hash_text_returns_16_chars(self) -> None:
        """Test hash returns 16 character string."""
        result = _hash_text("test input")
        assert len(result) == 16
        assert isinstance(result, str)

    def test_hash_text_deterministic(self) -> None:
        """Test same input produces same hash."""
        input_text = "consistent input"
        hash1 = _hash_text(input_text)
        hash2 = _hash_text(input_text)
        assert hash1 == hash2

    def test_hash_text_different_inputs(self) -> None:
        """Test different inputs produce different hashes."""
        hash1 = _hash_text("input one")
        hash2 = _hash_text("input two")
        assert hash1 != hash2


class TestSerializeForJson:
    """Tests for JSON serialization utility."""

    def test_serialize_datetime(self) -> None:
        """Test datetime objects are converted to ISO strings."""
        from datetime import UTC, datetime

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = _serialize_for_json(dt)
        assert result == "2024-01-15T10:30:00+00:00"

    def test_serialize_nested_dict(self) -> None:
        """Test nested dicts with datetimes are serialized."""
        from datetime import UTC, datetime

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        data = {"outer": {"inner": dt, "string": "test"}}
        result = _serialize_for_json(data)

        assert result["outer"]["inner"] == "2024-01-15T10:30:00+00:00"
        assert result["outer"]["string"] == "test"

    def test_serialize_list_with_datetimes(self) -> None:
        """Test lists containing datetimes are serialized."""
        from datetime import UTC, datetime

        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
        data = [{"created_at": dt}, {"created_at": dt}]
        result = _serialize_for_json(data)

        assert result[0]["created_at"] == "2024-01-15T10:30:00+00:00"
        assert result[1]["created_at"] == "2024-01-15T10:30:00+00:00"

    def test_serialize_primitives_unchanged(self) -> None:
        """Test primitive types pass through unchanged."""
        assert _serialize_for_json("string") == "string"
        assert _serialize_for_json(123) == 123
        assert _serialize_for_json(True) is True
        assert _serialize_for_json(None) is None


class TestCollectUserData:
    """Tests for collect_user_data function."""

    @patch("backend.services.gdpr.db_session")
    def test_collect_user_data_structure(self, mock_db_session: MagicMock) -> None:
        """Test collected data has expected structure."""
        # Mock cursor and connection
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = collect_user_data("test-user-123")

        # Verify expected keys exist
        assert "export_date" in result
        assert "user_id" in result
        assert result["user_id"] == "test-user-123"
        assert "profile" in result
        assert "business_context" in result
        assert "sessions" in result
        assert "actions" in result
        assert "datasets" in result
        assert "projects" in result
        assert "gdpr_audit_log" in result

    @patch("backend.services.gdpr.db_session")
    def test_collect_user_data_db_error(self, mock_db_session: MagicMock) -> None:
        """Test GDPRError raised on database error."""
        mock_db_session.side_effect = Exception("Database connection failed")

        with pytest.raises(GDPRError) as exc_info:
            collect_user_data("test-user")

        assert "Data collection failed" in str(exc_info.value)


class TestDeleteUserData:
    """Tests for delete_user_data function."""

    @patch("backend.services.gdpr._delete_user_conversations")
    @patch("backend.services.spaces.SpacesClient")
    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_returns_summary(
        self, mock_db_session: MagicMock, mock_spaces: MagicMock, mock_del_conv: MagicMock
    ) -> None:
        """Test deletion returns summary with counts."""
        mock_del_conv.return_value = 0

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No datasets
        mock_cursor.rowcount = 0
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = delete_user_data("test-user-123")

        assert "user_id" in result
        assert "deleted_at" in result
        assert "sessions_anonymized" in result
        assert "actions_anonymized" in result
        assert "datasets_deleted" in result
        assert "files_deleted" in result
        assert "conversations_deleted" in result
        assert "errors" in result

    @patch("backend.services.gdpr._delete_user_conversations")
    @patch("backend.services.spaces.SpacesClient")
    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_deletes_files(
        self,
        mock_db_session: MagicMock,
        mock_spaces_class: MagicMock,
        mock_del_conv: MagicMock,
    ) -> None:
        """Test that dataset files are deleted from Spaces."""
        mock_del_conv.return_value = 0

        # Mock dataset with file
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"id": "ds-1", "file_path": "datasets/test.csv"}]
        mock_cursor.rowcount = 1
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        # Mock Spaces client
        mock_spaces = MagicMock()
        mock_spaces_class.return_value = mock_spaces

        result = delete_user_data("test-user-123")

        # Verify Spaces.delete was called
        mock_spaces.delete.assert_called_once_with("datasets/test.csv")
        assert result["files_deleted"] == 1

    @patch("backend.services.gdpr._delete_user_conversations")
    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_db_error(
        self, mock_db_session: MagicMock, mock_del_conv: MagicMock
    ) -> None:
        """Test GDPRError raised on database error."""
        mock_del_conv.return_value = 0
        mock_db_session.side_effect = Exception("Database error")

        with pytest.raises(GDPRError) as exc_info:
            delete_user_data("test-user")

        assert "Deletion failed" in str(exc_info.value)

    @patch("backend.services.gdpr._delete_user_conversations")
    @patch("backend.services.spaces.SpacesClient")
    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_deletes_conversations(
        self,
        mock_db_session: MagicMock,
        mock_spaces: MagicMock,
        mock_del_conv: MagicMock,
    ) -> None:
        """Test that Redis conversations are deleted."""
        mock_del_conv.return_value = 5

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.rowcount = 0
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = delete_user_data("test-user-123")

        mock_del_conv.assert_called_once_with("test-user-123")
        assert result["conversations_deleted"] == 5


class TestCollectConversations:
    """Tests for _collect_conversations function."""

    @patch("backend.services.gdpr.RedisManager")
    def test_collect_conversations_empty(self, mock_redis_class: MagicMock) -> None:
        """Test collecting conversations when none exist."""
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, [])
        mock_redis_class.return_value.client = mock_client

        result = _collect_conversations("test-user")

        assert result == []
        mock_client.scan.assert_called()

    @patch("backend.services.gdpr.RedisManager")
    def test_collect_conversations_with_data(self, mock_redis_class: MagicMock) -> None:
        """Test collecting conversations with existing data."""
        mock_client = MagicMock()

        # Mock scan returning one index key
        index_key = f"{CONV_INDEX_PREFIX}:test-user:dataset-1"
        mock_client.scan.return_value = (0, [index_key.encode()])

        # Mock zrange returning conversation IDs
        mock_client.zrange.return_value = [b"conv-123"]

        # Mock get returning conversation data
        conv_data = {
            "id": "conv-123",
            "dataset_id": "dataset-1",
            "user_id": "test-user",
            "messages": [{"role": "user", "content": "What is the total?"}],
        }
        mock_client.get.return_value = json.dumps(conv_data).encode()

        mock_redis_class.return_value.client = mock_client

        result = _collect_conversations("test-user")

        assert len(result) == 1
        assert result[0]["id"] == "conv-123"
        assert len(result[0]["messages"]) == 1

    @patch("backend.services.gdpr.RedisManager")
    def test_collect_conversations_handles_redis_error(self, mock_redis_class: MagicMock) -> None:
        """Test graceful handling of Redis errors."""
        mock_redis_class.side_effect = Exception("Redis connection failed")

        # Should not raise, just return empty list
        result = _collect_conversations("test-user")

        assert result == []


class TestDeleteUserConversations:
    """Tests for _delete_user_conversations function."""

    @patch("backend.services.gdpr.RedisManager")
    def test_delete_conversations_empty(self, mock_redis_class: MagicMock) -> None:
        """Test deleting conversations when none exist."""
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, [])
        mock_redis_class.return_value.client = mock_client

        result = _delete_user_conversations("test-user")

        assert result == 0

    @patch("backend.services.gdpr.RedisManager")
    def test_delete_conversations_with_data(self, mock_redis_class: MagicMock) -> None:
        """Test deleting existing conversations."""
        mock_client = MagicMock()

        # Mock scan returning one index key
        index_key = f"{CONV_INDEX_PREFIX}:test-user:dataset-1"
        mock_client.scan.return_value = (0, [index_key.encode()])

        # Mock zrange returning conversation IDs
        mock_client.zrange.return_value = [b"conv-123", b"conv-456"]

        # Mock delete returning 1 for each call (success)
        mock_client.delete.return_value = 1

        mock_redis_class.return_value.client = mock_client

        result = _delete_user_conversations("test-user")

        assert result == 2  # 2 conversations deleted
        # Should delete both conversation keys and the index key
        assert mock_client.delete.call_count == 3

    @patch("backend.services.gdpr.RedisManager")
    def test_delete_conversations_handles_redis_error(self, mock_redis_class: MagicMock) -> None:
        """Test graceful handling of Redis errors."""
        mock_redis_class.side_effect = Exception("Redis connection failed")

        # Should not raise, just return 0
        result = _delete_user_conversations("test-user")

        assert result == 0


class TestCollectUserDataClarifications:
    """Tests for collect_user_data dataset clarifications."""

    @patch("backend.services.gdpr._collect_conversations")
    @patch("backend.services.gdpr.db_session")
    def test_includes_dataset_clarifications(
        self, mock_db_session: MagicMock, mock_collect_conv: MagicMock
    ) -> None:
        """Test that dataset clarifications are included in export."""
        mock_collect_conv.return_value = []

        # Mock cursor with dataset that has clarifications
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            None,  # profile
            None,  # business_context
        ]
        clarifications = [
            {"question": "What is revenue?", "answer": "Total sales"},
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # sessions
            [],  # actions
            [
                {
                    "id": "ds-1",
                    "name": "Sales Data",
                    "source_type": "csv",
                    "file_path": "datasets/sales.csv",
                    "row_count": 100,
                    "column_count": 5,
                    "file_size_bytes": 1024,
                    "summary": "Sales data",
                    "clarifications": clarifications,
                    "created_at": None,
                    "updated_at": None,
                }
            ],  # datasets
            [],  # projects
            [],  # gdpr_audit_log
        ]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = collect_user_data("test-user")

        assert "dataset_clarifications" in result
        assert len(result["dataset_clarifications"]) == 1
        assert result["dataset_clarifications"][0]["dataset_name"] == "Sales Data"
        assert result["dataset_clarifications"][0]["clarifications"] == clarifications

    @patch("backend.services.gdpr._collect_conversations")
    @patch("backend.services.gdpr.db_session")
    def test_includes_dataset_conversations(
        self, mock_db_session: MagicMock, mock_collect_conv: MagicMock
    ) -> None:
        """Test that dataset conversations are included in export."""
        conversations = [
            {
                "id": "conv-123",
                "dataset_id": "ds-1",
                "messages": [{"role": "user", "content": "What is total?"}],
            }
        ]
        mock_collect_conv.return_value = conversations

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        mock_db_session.return_value = mock_conn

        result = collect_user_data("test-user")

        assert "dataset_conversations" in result
        assert result["dataset_conversations"] == conversations
        mock_collect_conv.assert_called_once_with("test-user")
