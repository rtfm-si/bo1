"""Tests for Kanban columns preference API endpoints.

Tests:
- GET /api/v1/user/preferences/kanban-columns (returns defaults for new users)
- PATCH /api/v1/user/preferences/kanban-columns (create/update)
- Validation: min 1, max 8 columns, unique IDs, valid statuses
- Color validation (optional hex format)
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_db_session():
    """Mock db_session context manager."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


class TestGetKanbanColumns:
    """Test GET /api/v1/user/preferences/kanban-columns."""

    def test_returns_default_columns_when_null(self, mock_db_session, mock_user):
        """New users get default 3-column layout."""
        mock_conn, mock_cursor = mock_db_session
        # User exists but has no kanban_columns set
        mock_cursor.fetchone.return_value = {"kanban_columns": None}

        with patch("backend.api.utils.db_helpers.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            with patch("backend.api.user.get_current_user", return_value=mock_user):
                import asyncio

                from backend.api.user import get_kanban_columns

                result = asyncio.get_event_loop().run_until_complete(get_kanban_columns(mock_user))

        assert len(result.columns) == 3
        assert result.columns[0].id == "todo"
        assert result.columns[0].title == "To Do"
        assert result.columns[1].id == "in_progress"
        assert result.columns[2].id == "done"

    def test_returns_stored_columns(self, mock_db_session, mock_user):
        """Returns user's stored columns when set."""
        mock_conn, mock_cursor = mock_db_session
        stored_columns = [
            {"id": "todo", "title": "Backlog", "color": "#FF5733"},
            {"id": "in_progress", "title": "Working"},
            {"id": "in_review", "title": "Review"},
            {"id": "done", "title": "Complete"},
        ]
        mock_cursor.fetchone.return_value = {"kanban_columns": stored_columns}

        with patch("backend.api.utils.db_helpers.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            with patch("backend.api.user.get_current_user", return_value=mock_user):
                import asyncio

                from backend.api.user import get_kanban_columns

                result = asyncio.get_event_loop().run_until_complete(get_kanban_columns(mock_user))

        assert len(result.columns) == 4
        assert result.columns[0].id == "todo"
        assert result.columns[0].title == "Backlog"
        assert result.columns[0].color == "#FF5733"
        assert result.columns[2].id == "in_review"


class TestUpdateKanbanColumns:
    """Test PATCH /api/v1/user/preferences/kanban-columns."""

    def test_update_valid_columns(self, mock_db_session, mock_user):
        """Valid column configuration is saved."""
        mock_conn, mock_cursor = mock_db_session
        mock_cursor.fetchone.return_value = {"kanban_columns": []}

        from backend.api.models import KanbanColumn, KanbanColumnsUpdate

        update = KanbanColumnsUpdate(
            columns=[
                KanbanColumn(id="todo", title="To Do"),
                KanbanColumn(id="done", title="Done"),
            ]
        )

        with patch("backend.api.utils.db_helpers.db_session") as mock_db:
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            with patch("backend.api.user.get_current_user", return_value=mock_user):
                import asyncio

                from backend.api.user import update_kanban_columns

                result = asyncio.get_event_loop().run_until_complete(
                    update_kanban_columns(update, mock_user)
                )

        assert len(result.columns) == 2
        # Verify SQL was called
        mock_cursor.execute.assert_called()


class TestKanbanColumnsValidation:
    """Test validation rules for kanban columns."""

    def test_rejects_empty_columns(self):
        """At least 1 column required."""
        from pydantic import ValidationError

        from backend.api.models import KanbanColumnsUpdate

        with pytest.raises(ValidationError) as exc_info:
            KanbanColumnsUpdate(columns=[])

        assert "too_short" in str(exc_info.value).lower()

    def test_rejects_too_many_columns(self):
        """Max 8 columns allowed."""
        from pydantic import ValidationError

        from backend.api.models import KanbanColumn, KanbanColumnsUpdate

        columns = [KanbanColumn(id=f"col_{i}", title=f"Column {i}") for i in range(9)]

        with pytest.raises(ValidationError) as exc_info:
            KanbanColumnsUpdate(columns=columns)

        assert "too_long" in str(exc_info.value).lower()

    def test_rejects_duplicate_ids(self, mock_user):
        """Column IDs must be unique."""
        from fastapi import HTTPException

        from backend.api.models import KanbanColumn
        from backend.api.user import _validate_kanban_columns

        columns = [
            KanbanColumn(id="todo", title="To Do 1"),
            KanbanColumn(id="todo", title="To Do 2"),  # Duplicate
        ]

        with pytest.raises(HTTPException) as exc_info:
            _validate_kanban_columns(columns)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        detail_str = (
            detail.get("message", detail.get("detail", ""))
            if isinstance(detail, dict)
            else str(detail)
        )
        assert "unique" in detail_str.lower()

    def test_rejects_invalid_status_id(self, mock_user):
        """Column IDs must be valid ActionStatus values."""
        from fastapi import HTTPException

        from backend.api.models import KanbanColumn
        from backend.api.user import _validate_kanban_columns

        columns = [
            KanbanColumn(id="invalid_status", title="Invalid"),
        ]

        with pytest.raises(HTTPException) as exc_info:
            _validate_kanban_columns(columns)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        detail_str = (
            detail.get("message", detail.get("detail", ""))
            if isinstance(detail, dict)
            else str(detail)
        )
        assert "invalid" in detail_str.lower()

    def test_accepts_all_valid_statuses(self, mock_user):
        """All ActionStatus values are valid column IDs."""
        from backend.api.models import ActionStatus, KanbanColumn
        from backend.api.user import _validate_kanban_columns

        valid_statuses = [
            ActionStatus.TODO,
            ActionStatus.IN_PROGRESS,
            ActionStatus.BLOCKED,
            ActionStatus.IN_REVIEW,
            ActionStatus.DONE,
            ActionStatus.CANCELLED,
            ActionStatus.FAILED,
            ActionStatus.ABANDONED,
        ]

        columns = [
            KanbanColumn(id=status, title=f"Column for {status}")
            for status in valid_statuses[:8]  # Max 8
        ]

        # Should not raise
        _validate_kanban_columns(columns)

    def test_accepts_valid_hex_color(self):
        """Valid hex colors are accepted."""
        from backend.api.models import KanbanColumn

        col = KanbanColumn(id="todo", title="To Do", color="#FF5733")
        assert col.color == "#FF5733"

    def test_rejects_invalid_hex_color(self):
        """Invalid hex colors are rejected."""
        from pydantic import ValidationError

        from backend.api.models import KanbanColumn

        with pytest.raises(ValidationError):
            KanbanColumn(id="todo", title="To Do", color="invalid")

        with pytest.raises(ValidationError):
            KanbanColumn(id="todo", title="To Do", color="#GGG")

        with pytest.raises(ValidationError):
            KanbanColumn(id="todo", title="To Do", color="rgb(255,0,0)")

    def test_accepts_null_color(self):
        """Null/missing color is valid (uses default)."""
        from backend.api.models import KanbanColumn

        col = KanbanColumn(id="todo", title="To Do")
        assert col.color is None

        col2 = KanbanColumn(id="todo", title="To Do", color=None)
        assert col2.color is None

    def test_title_length_validation(self):
        """Title must be 1-50 characters."""
        from pydantic import ValidationError

        from backend.api.models import KanbanColumn

        # Empty title
        with pytest.raises(ValidationError):
            KanbanColumn(id="todo", title="")

        # Too long title
        with pytest.raises(ValidationError):
            KanbanColumn(id="todo", title="x" * 51)

        # Valid titles
        col = KanbanColumn(id="todo", title="X")
        assert col.title == "X"

        col2 = KanbanColumn(id="todo", title="x" * 50)
        assert len(col2.title) == 50


class TestKanbanColumnModels:
    """Test Pydantic model definitions."""

    def test_kanban_column_serialization(self):
        """KanbanColumn serializes correctly."""
        from backend.api.models import KanbanColumn

        col = KanbanColumn(id="todo", title="To Do", color="#FF5733")
        data = col.model_dump()

        assert data == {"id": "todo", "title": "To Do", "color": "#FF5733"}

    def test_kanban_columns_response(self):
        """KanbanColumnsResponse contains columns list."""
        from backend.api.models import KanbanColumn, KanbanColumnsResponse

        response = KanbanColumnsResponse(
            columns=[
                KanbanColumn(id="todo", title="To Do"),
                KanbanColumn(id="done", title="Done"),
            ]
        )

        assert len(response.columns) == 2
        data = response.model_dump()
        assert "columns" in data
        assert len(data["columns"]) == 2

    def test_valid_kanban_statuses_set(self):
        """VALID_KANBAN_STATUSES contains all expected statuses."""
        from backend.api.models import VALID_KANBAN_STATUSES, ActionStatus

        assert ActionStatus.TODO in VALID_KANBAN_STATUSES
        assert ActionStatus.IN_PROGRESS in VALID_KANBAN_STATUSES
        assert ActionStatus.BLOCKED in VALID_KANBAN_STATUSES
        assert ActionStatus.IN_REVIEW in VALID_KANBAN_STATUSES
        assert ActionStatus.DONE in VALID_KANBAN_STATUSES
        assert ActionStatus.CANCELLED in VALID_KANBAN_STATUSES
        assert ActionStatus.FAILED in VALID_KANBAN_STATUSES
        assert ActionStatus.ABANDONED in VALID_KANBAN_STATUSES
        assert ActionStatus.REPLANNED in VALID_KANBAN_STATUSES
