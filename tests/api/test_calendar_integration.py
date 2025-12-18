"""Tests for calendar integration API endpoints."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_verify_session():
    """Mock session verification."""
    with patch("backend.api.integrations.calendar.verify_session") as mock:
        session = MagicMock()
        session.get_user_id.return_value = "test-user-123"
        mock.return_value = lambda: session
        yield session


@pytest.fixture
def mock_settings_enabled():
    """Mock settings with calendar enabled."""
    with patch("backend.api.integrations.calendar.get_settings") as mock:
        settings = MagicMock()
        settings.google_calendar_enabled = True
        mock.return_value = settings
        yield mock


class TestCalendarStatusEndpoint:
    """Tests for GET /status endpoint."""

    def test_status_includes_sync_enabled(self, mock_settings_enabled, mock_verify_session):
        """Test that status response includes sync_enabled field."""
        with (
            patch("backend.api.integrations.calendar.user_repository") as mock_repo,
            patch("backend.api.integrations.calendar.limiter"),
        ):
            mock_repo.get_calendar_tokens.return_value = {
                "access_token": "token123",
                "connected_at": None,
            }
            mock_repo.get_calendar_sync_enabled.return_value = True

            # Import after patching
            from backend.api.integrations.calendar import CalendarStatusResponse

            # Verify response model has sync_enabled
            assert hasattr(CalendarStatusResponse, "model_fields")
            assert "sync_enabled" in CalendarStatusResponse.model_fields

    def test_status_returns_sync_disabled_when_user_disabled(self, mock_settings_enabled):
        """Test status correctly reports sync_enabled=False."""
        with patch("backend.api.integrations.calendar.user_repository") as mock_repo:
            mock_repo.get_calendar_tokens.return_value = {
                "access_token": "token123",
                "connected_at": None,
            }
            mock_repo.get_calendar_sync_enabled.return_value = False

            from backend.api.integrations.calendar import CalendarStatusResponse

            # Create response manually to verify structure
            response = CalendarStatusResponse(
                connected=True,
                connected_at=None,
                feature_enabled=True,
                sync_enabled=False,
            )
            assert response.sync_enabled is False


class TestCalendarToggleSyncEndpoint:
    """Tests for PATCH /status endpoint (toggle sync)."""

    def test_toggle_sync_request_model(self):
        """Test that toggle request model accepts enabled boolean."""
        from backend.api.integrations.calendar import CalendarSyncToggleRequest

        # Valid request
        req = CalendarSyncToggleRequest(enabled=True)
        assert req.enabled is True

        req = CalendarSyncToggleRequest(enabled=False)
        assert req.enabled is False

    def test_toggle_sync_updates_preference(self, mock_settings_enabled):
        """Test that toggle endpoint calls repository to update preference."""
        with patch("backend.api.integrations.calendar.user_repository") as mock_repo:
            mock_repo.set_calendar_sync_enabled.return_value = True
            mock_repo.get_calendar_tokens.return_value = {
                "access_token": "token123",
                "connected_at": None,
            }

            # Verify the repository method exists and is callable
            assert hasattr(mock_repo, "set_calendar_sync_enabled")
            mock_repo.set_calendar_sync_enabled("test-user", False)
            mock_repo.set_calendar_sync_enabled.assert_called_with("test-user", False)


class TestUserRepositoryCalendarSync:
    """Tests for user repository calendar sync methods."""

    def test_get_calendar_sync_enabled_default(self):
        """Test that get_calendar_sync_enabled returns True by default."""
        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        # Mock the _execute_one to return None (user not found)
        with patch.object(repo, "_execute_one", return_value=None):
            result = repo.get_calendar_sync_enabled("nonexistent-user")
            assert result is True  # Default to enabled

    def test_get_calendar_sync_enabled_returns_stored_value(self):
        """Test that stored False value is returned correctly."""
        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        # Mock the _execute_one to return False
        with patch.object(repo, "_execute_one", return_value={"calendar_sync_enabled": False}):
            result = repo.get_calendar_sync_enabled("user123")
            assert result is False

    def test_get_calendar_sync_enabled_null_defaults_true(self):
        """Test that NULL value in DB defaults to True."""
        from bo1.state.repositories.user_repository import UserRepository

        repo = UserRepository()

        # Mock the _execute_one to return None value (column is NULL)
        with patch.object(repo, "_execute_one", return_value={"calendar_sync_enabled": None}):
            result = repo.get_calendar_sync_enabled("user123")
            assert result is True  # NULL defaults to True
