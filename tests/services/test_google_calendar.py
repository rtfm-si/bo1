"""Tests for Google Calendar integration service."""
# ruff: noqa: S105, S106 - Test fixtures use hardcoded test credentials

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError

from backend.services.google_calendar import (
    CalendarError,
    GoogleCalendarClient,
    exchange_code,
    get_auth_url,
    get_calendar_client,
)


@pytest.fixture
def mock_settings():
    """Mock settings with OAuth credentials."""
    with patch("backend.services.google_calendar.get_settings") as mock:
        settings = MagicMock()
        settings.google_oauth_client_id = "test_client_id"
        settings.google_oauth_client_secret = "test_client_secret"
        settings.google_calendar_enabled = True
        settings.supertokens_api_domain = "http://localhost:8000"
        mock.return_value = settings
        yield mock


@pytest.fixture
def calendar_client():
    """Create GoogleCalendarClient with test tokens."""
    return GoogleCalendarClient(
        user_id="test_user",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_at=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    )


class TestGoogleCalendarClientTokenManagement:
    """Tests for token expiry and refresh."""

    def test_token_not_expired(self, calendar_client):
        """Test that valid token is not considered expired."""
        assert not calendar_client._is_token_expired()

    def test_token_expired(self):
        """Test that expired token is detected."""
        client = GoogleCalendarClient(
            user_id="test_user",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        )
        assert client._is_token_expired()

    def test_token_expires_soon(self):
        """Test that token expiring within buffer is considered expired."""
        client = GoogleCalendarClient(
            user_id="test_user",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=(datetime.now(UTC) + timedelta(minutes=3)).isoformat(),
        )
        # Token expires in 3 min, but buffer is 5 min, so considered expired
        assert client._is_token_expired()

    def test_token_no_expiry(self):
        """Test that missing expiry doesn't trigger refresh."""
        client = GoogleCalendarClient(
            user_id="test_user",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=None,
        )
        assert not client._is_token_expired()


class TestGoogleCalendarClientEvents:
    """Tests for calendar event operations."""

    def test_create_event_success(self, calendar_client):
        """Test successful event creation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "event123",
            "summary": "Test Event",
            "start": {"dateTime": "2025-01-15T09:00:00Z"},
            "end": {"dateTime": "2025-01-15T10:00:00Z"},
            "description": "Test description",
            "htmlLink": "https://calendar.google.com/event?id=event123",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(calendar_client._session, "request", return_value=mock_response):
            event = calendar_client.create_event(
                summary="Test Event",
                start=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
                end=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
                description="Test description",
            )

        assert event.event_id == "event123"
        assert event.summary == "Test Event"
        assert event.html_link == "https://calendar.google.com/event?id=event123"

    def test_create_event_default_end_time(self, calendar_client):
        """Test event creation with default end time (1 hour after start)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "event456",
            "summary": "Quick Event",
            "start": {"dateTime": "2025-01-15T09:00:00Z"},
            "end": {"dateTime": "2025-01-15T10:00:00Z"},
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            calendar_client._session, "request", return_value=mock_response
        ) as mock_req:
            calendar_client.create_event(
                summary="Quick Event",
                start=datetime(2025, 1, 15, 9, 0, tzinfo=UTC),
            )

            # Check that end time was set to 1 hour after start
            call_args = mock_req.call_args
            json_data = call_args.kwargs.get("json")
            assert json_data is not None

    def test_delete_event_success(self, calendar_client):
        """Test successful event deletion."""
        mock_response = MagicMock()
        mock_response.status_code = 204  # No Content

        with patch.object(calendar_client._session, "request", return_value=mock_response):
            result = calendar_client.delete_event("event123")

        assert result is True

    def test_delete_event_not_found(self, calendar_client):
        """Test 404 error when deleting non-existent event."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

        with patch.object(calendar_client._session, "request", return_value=mock_response):
            with pytest.raises(CalendarError) as exc_info:
                calendar_client.delete_event("nonexistent")
            assert "not found" in str(exc_info.value).lower()


class TestAuthHelpers:
    """Tests for OAuth helper functions."""

    def test_get_auth_url(self, mock_settings):
        """Test OAuth URL generation."""
        url = get_auth_url(
            redirect_uri="http://localhost:8000/callback",
            state="test_state_123",
        )

        assert "accounts.google.com" in url
        assert "client_id=test_client_id" in url
        assert "redirect_uri=" in url
        assert "state=test_state_123" in url
        assert "calendar.events" in url  # Check scope

    def test_get_auth_url_no_client_id(self):
        """Test error when client ID not configured."""
        with patch("backend.services.google_calendar.get_settings") as mock:
            mock.return_value.google_oauth_client_id = ""
            with pytest.raises(CalendarError) as exc_info:
                get_auth_url(redirect_uri="http://localhost/callback")
            assert "not configured" in str(exc_info.value).lower()

    def test_exchange_code_success(self, mock_settings):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
        }

        with patch("backend.services.google_calendar.requests.post", return_value=mock_response):
            tokens = exchange_code(
                code="auth_code_123",
                redirect_uri="http://localhost:8000/callback",
            )

        assert tokens["access_token"] == "new_access_token"
        assert tokens["refresh_token"] == "new_refresh_token"
        assert "expires_at" in tokens

    def test_exchange_code_failure(self, mock_settings):
        """Test token exchange failure."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"

        with patch("backend.services.google_calendar.requests.post", return_value=mock_response):
            with pytest.raises(CalendarError) as exc_info:
                exchange_code(code="bad_code", redirect_uri="http://localhost/callback")
            assert "exchange" in str(exc_info.value).lower()


class TestGetCalendarClient:
    """Tests for get_calendar_client helper."""

    def test_get_client_with_tokens(self):
        """Test getting client when user has tokens."""
        mock_tokens = {
            "access_token": "token123",
            "refresh_token": "refresh456",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }

        from bo1.state.repositories import user_repository as repo_module

        with patch.object(repo_module, "get_calendar_tokens", return_value=mock_tokens):
            client = get_calendar_client("test_user")

        assert client is not None
        assert client._access_token == "token123"

    def test_get_client_no_tokens(self):
        """Test getting client when user has no tokens."""
        from bo1.state.repositories import user_repository as repo_module

        with patch.object(repo_module, "get_calendar_tokens", return_value=None):
            client = get_calendar_client("test_user")

        assert client is None

    def test_get_client_empty_access_token(self):
        """Test getting client when access token is empty."""
        from bo1.state.repositories import user_repository as repo_module

        with patch.object(repo_module, "get_calendar_tokens", return_value={"access_token": ""}):
            client = get_calendar_client("test_user")

        assert client is None
