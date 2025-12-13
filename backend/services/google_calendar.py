"""Google Calendar integration service.

Manages OAuth flow and calendar event operations for action due date sync.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bo1.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

# Required scopes for calendar access
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",  # Create/update/delete events
]


class CalendarError(Exception):
    """Error during Google Calendar operation."""

    pass


@dataclass
class CalendarEvent:
    """Represents a Google Calendar event."""

    event_id: str
    summary: str
    start: datetime
    end: datetime
    description: str | None = None
    html_link: str | None = None


class GoogleCalendarClient:
    """Client for Google Calendar API operations.

    Uses user's OAuth access token for calendar access.
    Handles token refresh automatically when expired.
    """

    def __init__(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str | None,
    ) -> None:
        """Initialize Google Calendar client.

        Args:
            user_id: User ID for token refresh persistence
            access_token: Google OAuth access token
            refresh_token: Google OAuth refresh token (for refresh)
            expires_at: ISO timestamp when access token expires
        """
        self._user_id = user_id
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expires_at = expires_at

        # Configure session with retry logic
        self._session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],  # Don't retry 401/403
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)

    def _is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self._expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self._expires_at.replace("Z", "+00:00"))
            # Add 5 minute buffer
            return datetime.now(UTC) >= (expires - timedelta(minutes=5))
        except (ValueError, TypeError):
            return False

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token.

        Returns:
            True if refresh succeeded
        """
        if not self._refresh_token:
            logger.warning(f"No refresh token available for user {self._user_id}")
            return False

        settings = get_settings()
        client_id = settings.google_oauth_client_id
        client_secret = settings.google_oauth_client_secret

        if not client_id or not client_secret:
            logger.error("Google OAuth credentials not configured")
            return False

        try:
            response = requests.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.text}")
                return False

            tokens = response.json()
            self._access_token = tokens.get("access_token", "")
            expires_in = tokens.get("expires_in")

            if expires_in:
                self._expires_at = (
                    datetime.now(UTC) + timedelta(seconds=int(expires_in))
                ).isoformat()

            # Persist refreshed tokens
            from bo1.state.repositories import user_repository

            user_repository.save_calendar_tokens(
                user_id=self._user_id,
                access_token=self._access_token,
                refresh_token=self._refresh_token,
                expires_at=self._expires_at,
            )

            logger.info(f"Refreshed Google Calendar token for user {self._user_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            return False

    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if needed."""
        if self._is_token_expired():
            if not self._refresh_access_token():
                raise CalendarError(
                    "Google access token expired and refresh failed. Please reconnect Google Calendar."
                )

    def _make_request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        """Make authenticated request to Calendar API.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            url: API URL
            params: Query parameters
            json_data: JSON body data

        Returns:
            JSON response (empty dict for DELETE)

        Raises:
            CalendarError: If request fails
        """
        self._ensure_valid_token()

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = self._session.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30,
            )

            # Handle 401 - try refresh once
            if response.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self._access_token}"}
                    response = self._session.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=json_data,
                        timeout=30,
                    )
                else:
                    raise CalendarError(
                        "Google access token invalid. Please reconnect Google Calendar."
                    )

            # DELETE returns 204 No Content
            if response.status_code == 204:
                return {}

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 404:
                raise CalendarError("Calendar event not found.") from None
            elif status_code == 403:
                raise CalendarError(
                    "Access denied. Calendar permissions may have been revoked."
                ) from None
            else:
                raise CalendarError(f"Calendar API error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise CalendarError(f"Network error: {e}") from e

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> CalendarEvent:
        """Create a calendar event.

        Args:
            summary: Event title
            start: Event start time (UTC)
            end: Event end time (UTC), defaults to 1 hour after start
            description: Event description
            calendar_id: Calendar ID (default: primary)

        Returns:
            Created CalendarEvent
        """
        if end is None:
            end = start + timedelta(hours=1)

        event_data: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }

        if description:
            event_data["description"] = description

        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events"
        result = self._make_request("POST", url, json_data=event_data)

        return CalendarEvent(
            event_id=result.get("id", ""),
            summary=result.get("summary", ""),
            start=datetime.fromisoformat(
                result.get("start", {}).get("dateTime", "").replace("Z", "+00:00")
            ),
            end=datetime.fromisoformat(
                result.get("end", {}).get("dateTime", "").replace("Z", "+00:00")
            ),
            description=result.get("description"),
            html_link=result.get("htmlLink"),
        )

    def update_event(
        self,
        event_id: str,
        summary: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        description: str | None = None,
        calendar_id: str = "primary",
    ) -> CalendarEvent:
        """Update a calendar event.

        Args:
            event_id: Google Calendar event ID
            summary: New event title (optional)
            start: New start time (optional)
            end: New end time (optional)
            description: New description (optional)
            calendar_id: Calendar ID (default: primary)

        Returns:
            Updated CalendarEvent
        """
        # Get current event first
        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
        current = self._make_request("GET", url)

        # Build update payload
        event_data: dict[str, Any] = {}

        if summary is not None:
            event_data["summary"] = summary
        else:
            event_data["summary"] = current.get("summary", "")

        if start is not None:
            event_data["start"] = {"dateTime": start.isoformat(), "timeZone": "UTC"}
        else:
            event_data["start"] = current.get("start", {})

        if end is not None:
            event_data["end"] = {"dateTime": end.isoformat(), "timeZone": "UTC"}
        else:
            event_data["end"] = current.get("end", {})

        if description is not None:
            event_data["description"] = description
        elif "description" in current:
            event_data["description"] = current["description"]

        result = self._make_request("PUT", url, json_data=event_data)

        return CalendarEvent(
            event_id=result.get("id", ""),
            summary=result.get("summary", ""),
            start=datetime.fromisoformat(
                result.get("start", {}).get("dateTime", "").replace("Z", "+00:00")
            ),
            end=datetime.fromisoformat(
                result.get("end", {}).get("dateTime", "").replace("Z", "+00:00")
            ),
            description=result.get("description"),
            html_link=result.get("htmlLink"),
        )

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        """Delete a calendar event.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Calendar ID (default: primary)

        Returns:
            True if deleted successfully
        """
        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
        self._make_request("DELETE", url)
        return True

    def get_event(self, event_id: str, calendar_id: str = "primary") -> CalendarEvent:
        """Get a calendar event by ID.

        Args:
            event_id: Google Calendar event ID
            calendar_id: Calendar ID (default: primary)

        Returns:
            CalendarEvent
        """
        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
        result = self._make_request("GET", url)

        return CalendarEvent(
            event_id=result.get("id", ""),
            summary=result.get("summary", ""),
            start=datetime.fromisoformat(
                result.get("start", {}).get("dateTime", "").replace("Z", "+00:00")
            ),
            end=datetime.fromisoformat(
                result.get("end", {}).get("dateTime", "").replace("Z", "+00:00")
            ),
            description=result.get("description"),
            html_link=result.get("htmlLink"),
        )


def get_auth_url(redirect_uri: str, state: str | None = None) -> str:
    """Generate Google OAuth authorization URL for Calendar access.

    Args:
        redirect_uri: OAuth callback URL
        state: Optional state parameter for CSRF protection

    Returns:
        Authorization URL to redirect user to
    """
    settings = get_settings()

    if not settings.google_oauth_client_id:
        raise CalendarError("Google OAuth client ID not configured")

    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(CALENDAR_SCOPES),
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent to get refresh token
    }

    if state:
        params["state"] = state

    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


def exchange_code(code: str, redirect_uri: str) -> dict[str, str]:
    """Exchange authorization code for tokens.

    Args:
        code: Authorization code from OAuth callback
        redirect_uri: OAuth callback URL (must match original)

    Returns:
        Dict with access_token, refresh_token, expires_at
    """
    settings = get_settings()

    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise CalendarError("Google OAuth credentials not configured")

    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise CalendarError("Failed to exchange authorization code")

        tokens = response.json()

        # Calculate expiry time
        expires_in = tokens.get("expires_in", 3600)
        expires_at = (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()

        return {
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": expires_at,
        }

    except requests.RequestException as e:
        raise CalendarError(f"Network error during token exchange: {e}") from e


def get_calendar_client(user_id: str) -> GoogleCalendarClient | None:
    """Get a Calendar client for a user if they have tokens.

    Args:
        user_id: User ID

    Returns:
        GoogleCalendarClient if user has valid tokens, None otherwise
    """
    from bo1.state.repositories import user_repository

    tokens = user_repository.get_calendar_tokens(user_id)
    if not tokens:
        return None

    access_token = tokens.get("access_token")
    if not access_token:
        return None

    return GoogleCalendarClient(
        user_id=user_id,
        access_token=access_token,
        refresh_token=tokens.get("refresh_token"),
        expires_at=tokens.get("expires_at"),
    )
