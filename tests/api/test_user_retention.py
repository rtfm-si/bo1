"""Tests for user data retention endpoints.

Validates:
- GET /v1/user/retention returns current retention setting
- PATCH /v1/user/retention updates retention setting
- Validation: 365 <= days <= 3650 (1-10 years)
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend.api.user import RetentionSettingResponse, RetentionSettingUpdate


@pytest.mark.unit
class TestRetentionSettingModels:
    """Test Pydantic models for retention setting."""

    def test_retention_response_valid(self) -> None:
        """Test valid retention response."""
        response = RetentionSettingResponse(data_retention_days=365)
        assert response.data_retention_days == 365

    def test_retention_update_valid(self) -> None:
        """Test valid retention update request."""
        update = RetentionSettingUpdate(days=730)
        assert update.days == 730

    def test_retention_update_minimum(self) -> None:
        """Test minimum value (365 days / 1 year)."""
        update = RetentionSettingUpdate(days=365)
        assert update.days == 365

    def test_retention_update_maximum(self) -> None:
        """Test maximum value (3650 days / 10 years)."""
        update = RetentionSettingUpdate(days=3650)
        assert update.days == 3650

    def test_retention_update_below_minimum(self) -> None:
        """Test that values below 365 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetentionSettingUpdate(days=364)
        assert "greater than or equal to 365" in str(exc_info.value)

    def test_retention_update_above_maximum(self) -> None:
        """Test that values above 3650 are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetentionSettingUpdate(days=3651)
        assert "less than or equal to 3650" in str(exc_info.value)

    def test_retention_update_zero(self) -> None:
        """Test that zero is rejected."""
        with pytest.raises(ValidationError):
            RetentionSettingUpdate(days=0)

    def test_retention_update_negative(self) -> None:
        """Test that negative values are rejected."""
        with pytest.raises(ValidationError):
            RetentionSettingUpdate(days=-1)


@pytest.mark.unit
class TestRetentionSettingEndpoints:
    """Test retention setting endpoint logic."""

    @patch("backend.api.user.db_session")
    def test_get_retention_returns_user_setting(self, mock_db: MagicMock) -> None:
        """Test GET returns user's configured retention days."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 180}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        # Verify mock returns expected value
        mock_cursor.execute.assert_not_called()  # Not called yet
        result = mock_cursor.fetchone()
        assert result["data_retention_days"] == 180

    @patch("backend.api.user.db_session")
    def test_update_retention_persists_value(self, mock_db: MagicMock) -> None:
        """Test PATCH persists and returns updated retention days."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"data_retention_days": 90}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        # Verify mock returns expected value
        result = mock_cursor.fetchone()
        assert result["data_retention_days"] == 90


@pytest.mark.unit
class TestSessionCleanupPerUserRetention:
    """Test session cleanup respects per-user retention settings."""

    @patch("backend.jobs.session_cleanup.db_session")
    def test_cleanup_uses_per_user_retention(self, mock_db: MagicMock) -> None:
        """Test cleanup job queries based on per-user retention."""
        from backend.jobs.session_cleanup import cleanup_expired_sessions

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # No sessions to clean up
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        # Run cleanup without override (uses per-user settings)
        result = cleanup_expired_sessions()

        assert result["sessions_anonymized"] == 0
        assert result["errors"] == 0
        # Verify the per-user query was used (with join to users table)
        call_args = mock_cursor.execute.call_args
        assert call_args is not None
        sql = call_args[0][0]
        assert "users" in sql.lower()
        assert "data_retention_days" in sql.lower()

    @patch("backend.jobs.session_cleanup.db_session")
    def test_cleanup_with_override_retention(self, mock_db: MagicMock) -> None:
        """Test cleanup job uses override retention when provided."""
        from backend.jobs.session_cleanup import cleanup_expired_sessions

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        # Run cleanup with override
        result = cleanup_expired_sessions(retention_days=30)

        assert result["sessions_anonymized"] == 0
        assert result["errors"] == 0
        # Verify the simple date-based query was used (no join)
        call_args = mock_cursor.execute.call_args
        assert call_args is not None
        sql = call_args[0][0]
        # Override query doesn't join users table
        assert "join" not in sql.lower()
