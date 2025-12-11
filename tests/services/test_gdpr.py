"""Tests for GDPR service."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.gdpr import (
    GDPRError,
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

    @patch("backend.services.spaces.SpacesClient")
    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_returns_summary(
        self, mock_db_session: MagicMock, mock_spaces: MagicMock
    ) -> None:
        """Test deletion returns summary with counts."""
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
        assert "errors" in result

    @patch("backend.services.spaces.SpacesClient")
    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_deletes_files(
        self, mock_db_session: MagicMock, mock_spaces_class: MagicMock
    ) -> None:
        """Test that dataset files are deleted from Spaces."""
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

    @patch("backend.services.gdpr.db_session")
    def test_delete_user_data_db_error(self, mock_db_session: MagicMock) -> None:
        """Test GDPRError raised on database error."""
        mock_db_session.side_effect = Exception("Database error")

        with pytest.raises(GDPRError) as exc_info:
            delete_user_data("test-user")

        assert "Deletion failed" in str(exc_info.value)
