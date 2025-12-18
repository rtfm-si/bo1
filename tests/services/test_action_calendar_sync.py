"""Tests for action-to-calendar sync service."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from backend.services.action_calendar_sync import (
    remove_action_from_calendar,
    set_action_calendar_sync,
    sync_action_to_calendar,
)


@pytest.fixture
def mock_settings_enabled():
    """Mock settings with calendar enabled."""
    with patch("backend.services.action_calendar_sync.get_settings") as mock:
        settings = MagicMock()
        settings.google_calendar_enabled = True
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_settings_disabled():
    """Mock settings with calendar disabled."""
    with patch("backend.services.action_calendar_sync.get_settings") as mock:
        settings = MagicMock()
        settings.google_calendar_enabled = False
        mock.return_value = settings
        yield mock


@pytest.fixture
def mock_action_with_due_date():
    """Sample action with a due date."""
    return {
        "id": "action123",
        "title": "Test Action",
        "description": "Test description",
        "status": "in_progress",
        "priority": "high",
        "target_end_date": date(2025, 1, 20),
        "estimated_end_date": None,
        "calendar_event_id": None,
        "calendar_event_link": None,
        "calendar_sync_enabled": True,
    }


@pytest.fixture
def mock_action_with_event():
    """Sample action with existing calendar event."""
    return {
        "id": "action456",
        "title": "Existing Event Action",
        "description": "Has calendar event",
        "status": "in_progress",
        "priority": "medium",
        "target_end_date": date(2025, 1, 25),
        "calendar_event_id": "cal_event_123",
        "calendar_event_link": "https://calendar.google.com/event?id=123",
        "calendar_sync_enabled": True,
    }


class TestSyncActionToCalendar:
    """Tests for sync_action_to_calendar function."""

    def test_skips_when_feature_disabled(self, mock_settings_disabled):
        """Test that sync is skipped when feature is disabled."""
        result = sync_action_to_calendar("action123", "user1")
        assert result is None

    def test_skips_when_user_sync_disabled(self, mock_settings_enabled):
        """Test that sync is skipped when user has disabled sync at user level."""
        from bo1.state.repositories import user_repository

        with patch.object(
            user_repository, "get_calendar_sync_enabled", return_value=False
        ) as mock_sync:
            result = sync_action_to_calendar("action123", "user1")

        assert result is None
        mock_sync.assert_called_once_with("user1")

    def test_skips_when_action_not_found(self, mock_settings_enabled):
        """Test that sync is skipped when action doesn't exist."""
        from bo1.state.repositories import user_repository

        with (
            patch.object(user_repository, "get_calendar_sync_enabled", return_value=True),
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
        ):
            mock_get.return_value = None
            result = sync_action_to_calendar("nonexistent", "user1")

        assert result is None

    def test_skips_when_sync_disabled_on_action(
        self, mock_settings_enabled, mock_action_with_due_date
    ):
        """Test that sync is skipped when action has sync disabled."""
        from bo1.state.repositories import user_repository

        mock_action_with_due_date["calendar_sync_enabled"] = False

        with (
            patch.object(user_repository, "get_calendar_sync_enabled", return_value=True),
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
        ):
            mock_get.return_value = mock_action_with_due_date
            result = sync_action_to_calendar("action123", "user1")

        assert result is None

    def test_skips_when_no_due_date(self, mock_settings_enabled):
        """Test that sync is skipped when action has no due date."""
        from bo1.state.repositories import user_repository

        action_no_date = {
            "id": "action789",
            "title": "No Date Action",
            "target_end_date": None,
            "estimated_end_date": None,
            "calendar_sync_enabled": True,
        }

        with (
            patch.object(user_repository, "get_calendar_sync_enabled", return_value=True),
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
        ):
            mock_get.return_value = action_no_date
            result = sync_action_to_calendar("action789", "user1")

        assert result is None

    def test_skips_when_calendar_not_connected(
        self, mock_settings_enabled, mock_action_with_due_date
    ):
        """Test that sync is skipped when user hasn't connected calendar."""
        from bo1.state.repositories import user_repository

        with (
            patch.object(user_repository, "get_calendar_sync_enabled", return_value=True),
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
            patch("backend.services.google_calendar.get_calendar_client") as mock_client,
        ):
            mock_get.return_value = mock_action_with_due_date
            mock_client.return_value = None

            result = sync_action_to_calendar("action123", "user1")

        assert result is None

    def test_creates_new_event(self, mock_settings_enabled, mock_action_with_due_date):
        """Test that new calendar event is created."""
        from bo1.state.repositories import user_repository

        mock_event = MagicMock()
        mock_event.event_id = "new_event_id"
        mock_event.html_link = "https://calendar.google.com/event?id=new"

        mock_client = MagicMock()
        mock_client.create_event.return_value = mock_event

        with (
            patch.object(user_repository, "get_calendar_sync_enabled", return_value=True),
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
            patch("backend.services.google_calendar.get_calendar_client") as mock_get_client,
            patch(
                "backend.services.action_calendar_sync._update_action_calendar_fields"
            ) as mock_update,
        ):
            mock_get.return_value = mock_action_with_due_date
            mock_get_client.return_value = mock_client

            result = sync_action_to_calendar("action123", "user1")

        assert result is not None
        assert result["event_id"] == "new_event_id"
        mock_client.create_event.assert_called_once()
        mock_update.assert_called_once()

    def test_updates_existing_event(self, mock_settings_enabled, mock_action_with_event):
        """Test that existing calendar event is updated."""
        from bo1.state.repositories import user_repository

        mock_event = MagicMock()
        mock_event.event_id = "cal_event_123"
        mock_event.html_link = "https://calendar.google.com/event?id=123"

        mock_client = MagicMock()
        mock_client.update_event.return_value = mock_event

        with (
            patch.object(user_repository, "get_calendar_sync_enabled", return_value=True),
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
            patch("backend.services.google_calendar.get_calendar_client") as mock_get_client,
            patch("backend.services.action_calendar_sync._update_action_calendar_fields"),
        ):
            mock_get.return_value = mock_action_with_event
            mock_get_client.return_value = mock_client

            result = sync_action_to_calendar("action456", "user1")

        assert result is not None
        mock_client.update_event.assert_called_once()
        mock_client.create_event.assert_not_called()


class TestRemoveActionFromCalendar:
    """Tests for remove_action_from_calendar function."""

    def test_skips_when_feature_disabled(self, mock_settings_disabled):
        """Test removal is skipped when feature disabled."""
        result = remove_action_from_calendar("action123", "user1")
        assert result is False

    def test_skips_when_no_event(self, mock_settings_enabled, mock_action_with_due_date):
        """Test removal is skipped when action has no calendar event."""
        with patch("backend.services.action_calendar_sync._get_action_details") as mock_get:
            mock_get.return_value = mock_action_with_due_date  # Has no event

            result = remove_action_from_calendar("action123", "user1")

        assert result is False

    def test_deletes_event_successfully(self, mock_settings_enabled, mock_action_with_event):
        """Test successful event deletion."""
        mock_client = MagicMock()
        mock_client.delete_event.return_value = True

        with (
            patch("backend.services.action_calendar_sync._get_action_details") as mock_get,
            patch("backend.services.google_calendar.get_calendar_client") as mock_get_client,
            patch(
                "backend.services.action_calendar_sync._update_action_calendar_fields"
            ) as mock_update,
        ):
            mock_get.return_value = mock_action_with_event
            mock_get_client.return_value = mock_client

            result = remove_action_from_calendar("action456", "user1")

        assert result is True
        mock_client.delete_event.assert_called_once_with("cal_event_123")
        mock_update.assert_called_once_with(action_id="action456", event_id=None, event_link=None)


class TestSetActionCalendarSync:
    """Tests for set_action_calendar_sync function."""

    def test_enable_sync_triggers_sync(self):
        """Test that enabling sync triggers immediate sync."""
        with (
            patch("backend.services.action_calendar_sync.db_session"),
            patch("backend.services.action_calendar_sync.sync_action_to_calendar") as mock_sync,
        ):
            # Mock the update returning success
            with patch("backend.services.action_calendar_sync.db_session") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.rowcount = 1
                mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

                set_action_calendar_sync("action123", "user1", enabled=True)

            mock_sync.assert_called_once_with("action123", "user1", force=True)

    def test_disable_sync_removes_event(self):
        """Test that disabling sync removes calendar event."""
        with (
            patch("backend.services.action_calendar_sync.db_session"),
            patch(
                "backend.services.action_calendar_sync.remove_action_from_calendar"
            ) as mock_remove,
        ):
            with patch("backend.services.action_calendar_sync.db_session") as mock_db:
                mock_cursor = MagicMock()
                mock_cursor.rowcount = 1
                mock_db.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value = mock_cursor

                set_action_calendar_sync("action123", "user1", enabled=False)

            mock_remove.assert_called_once_with("action123", "user1")
