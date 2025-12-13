"""Integration tests for user data retention endpoints.

Tests:
- GET /v1/user/retention returns current retention setting
- PATCH /v1/user/retention updates retention setting
- Boundary value validation (365-3650 days)
- NULL handling for legacy users
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.api.user import (
    RetentionSettingResponse,
    RetentionSettingUpdate,
    get_retention_setting,
    update_retention_setting,
)


@pytest.mark.unit
class TestGetRetentionSettingEndpoint:
    """Tests for get_retention_setting endpoint logic."""

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_returns_valid_setting(self, mock_db: MagicMock) -> None:
        """GET returns user's configured retention days."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 730}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await get_retention_setting(user={"user_id": "test-user"})

        assert isinstance(result, RetentionSettingResponse)
        assert result.data_retention_days == 730

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_handles_null_with_default(self, mock_db: MagicMock) -> None:
        """GET returns default 365 when column is NULL (legacy users)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # Simulate NULL value from database
        mock_cursor.fetchone.return_value = {"data_retention_days": None}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await get_retention_setting(user={"user_id": "legacy-user"})

        assert isinstance(result, RetentionSettingResponse)
        assert result.data_retention_days == 365

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_returns_minimum_boundary(self, mock_db: MagicMock) -> None:
        """GET returns minimum valid value (365 days / 1 year)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 365}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await get_retention_setting(user={"user_id": "test-user"})

        assert result.data_retention_days == 365

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_returns_maximum_boundary(self, mock_db: MagicMock) -> None:
        """GET returns maximum valid value (3650 days / 10 years)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 3650}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await get_retention_setting(user={"user_id": "test-user"})

        assert result.data_retention_days == 3650

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_raises_404_for_missing_user(self, mock_db: MagicMock) -> None:
        """GET raises 404 when user not found."""
        from fastapi import HTTPException

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await get_retention_setting(user={"user_id": "nonexistent"})

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestUpdateRetentionSettingEndpoint:
    """Tests for update_retention_setting endpoint logic."""

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_updates_and_returns_value(self, mock_db: MagicMock) -> None:
        """PATCH persists and returns updated retention days."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 730}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await update_retention_setting(
            body=RetentionSettingUpdate(days=730),
            user={"user_id": "test-user"},
        )

        assert isinstance(result, RetentionSettingResponse)
        assert result.data_retention_days == 730

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_updates_minimum_boundary(self, mock_db: MagicMock) -> None:
        """PATCH with minimum value (365 / 1 year) succeeds."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 365}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await update_retention_setting(
            body=RetentionSettingUpdate(days=365),
            user={"user_id": "test-user"},
        )

        assert result.data_retention_days == 365

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_updates_maximum_boundary(self, mock_db: MagicMock) -> None:
        """PATCH with maximum value (3650 / 10 years) succeeds."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 3650}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = await update_retention_setting(
            body=RetentionSettingUpdate(days=3650),
            user={"user_id": "test-user"},
        )

        assert result.data_retention_days == 3650

    @pytest.mark.asyncio
    @patch("backend.api.user.db_session")
    async def test_raises_404_for_missing_user(self, mock_db: MagicMock) -> None:
        """PATCH raises 404 when user not found."""
        from fastapi import HTTPException

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            await update_retention_setting(
                body=RetentionSettingUpdate(days=730),
                user={"user_id": "nonexistent"},
            )

        assert exc_info.value.status_code == 404
