"""Google Search Console integration service.

Manages OAuth flow and Search Analytics API operations.
Follows the pattern established by google_calendar.py.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import requests

from backend.services.encryption import EncryptionError, get_encryption_service, is_encrypted
from backend.services.google_oauth import GOOGLE_TOKEN_URL, refresh_google_token
from backend.services.http_utils import create_resilient_session
from bo1.config import get_settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
WEBMASTERS_API_BASE = "https://www.googleapis.com/webmasters/v3"
SEARCH_CONSOLE_API_BASE = "https://searchconsole.googleapis.com/v1"

# Required scopes for Search Console access
GSC_SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",  # Read search analytics
]


class GSCError(Exception):
    """Error during Google Search Console operation."""

    pass


@dataclass
class SearchAnalyticsRow:
    """A single row of search analytics data."""

    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GoogleSearchConsoleClient:
    """Client for Google Search Console API operations.

    Uses admin OAuth tokens for site-wide access.
    Handles token refresh automatically when expired.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> None:
        """Initialize GSC client.

        Args:
            access_token: Google OAuth access token (encrypted or plain)
            refresh_token: Google OAuth refresh token (encrypted or plain)
            expires_at: Timestamp when access token expires
        """
        self._access_token = self._decrypt_if_needed(access_token)
        self._refresh_token = self._decrypt_if_needed(refresh_token) if refresh_token else None
        self._expires_at = expires_at

        self._session = create_resilient_session()

    @staticmethod
    def _decrypt_if_needed(value: str | None) -> str | None:
        """Decrypt value if it's encrypted."""
        if not value:
            return None
        if is_encrypted(value):
            try:
                service = get_encryption_service()
                return service.decrypt(value)
            except EncryptionError:
                logger.warning("Failed to decrypt token, using as-is")
                return value
        return value

    def _is_token_expired(self) -> bool:
        """Check if access token is expired."""
        if not self._expires_at:
            return False
        # Add 5 minute buffer
        return datetime.now(UTC) >= (self._expires_at - timedelta(minutes=5))

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token.

        Returns:
            True if refresh succeeded
        """
        if not self._refresh_token:
            logger.warning("No refresh token available for GSC")
            return False

        settings = get_settings()
        client_id = settings.google_oauth_client_id
        client_secret = settings.google_oauth_client_secret

        if not client_id or not client_secret:
            logger.error("Google OAuth credentials not configured")
            return False

        tokens = refresh_google_token(self._refresh_token, client_id, client_secret)
        if tokens is None:
            return False

        self._access_token = tokens.get("access_token", "")
        expires_in = tokens.get("expires_in")

        if expires_in:
            self._expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))

        # Persist refreshed tokens (encrypted)
        from bo1.state.repositories.gsc_repository import gsc_repository

        try:
            service = get_encryption_service()
            encrypted_access = service.encrypt(self._access_token)
            encrypted_refresh = (
                service.encrypt(self._refresh_token) if self._refresh_token else None
            )
        except EncryptionError:
            encrypted_access = self._access_token
            encrypted_refresh = self._refresh_token

        gsc_repository.update_connection_tokens(
            access_token=encrypted_access,
            refresh_token=encrypted_refresh,
            expires_at=self._expires_at,
        )

        logger.info("Refreshed GSC token")
        return True

    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if needed."""
        if self._is_token_expired():
            if not self._refresh_access_token():
                raise GSCError(
                    "GSC access token expired and refresh failed. Please reconnect Search Console."
                )

    def _make_request(
        self,
        method: str,
        url: str,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        """Make authenticated request to GSC API.

        Args:
            method: HTTP method
            url: API URL
            params: Query parameters
            json_data: JSON body data

        Returns:
            JSON response

        Raises:
            GSCError: If request fails
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
                timeout=60,  # GSC queries can be slow
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
                        timeout=60,
                    )
                else:
                    raise GSCError("GSC access token invalid. Please reconnect Search Console.")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 403:
                raise GSCError(
                    "Access denied. Search Console permissions may have been revoked."
                ) from None
            elif status_code == 404:
                raise GSCError("Site not found in Search Console.") from None
            else:
                raise GSCError(f"Search Console API error: {e}") from e
        except requests.exceptions.RequestException as e:
            raise GSCError(f"Network error: {e}") from e

    def list_sites(self) -> list[dict[str, Any]]:
        """List all sites/properties accessible to the authenticated user.

        Returns:
            List of site entries with siteUrl, permissionLevel
        """
        url = f"{WEBMASTERS_API_BASE}/sites"
        result = self._make_request("GET", url)
        return result.get("siteEntry", [])

    def get_search_analytics(
        self,
        site_url: str,
        start_date: date,
        end_date: date,
        dimensions: list[str] | None = None,
        row_limit: int = 1000,
    ) -> list[SearchAnalyticsRow]:
        """Query search analytics data for a site.

        Args:
            site_url: The site URL (property) to query
            start_date: Start date for the query
            end_date: End date for the query
            dimensions: Dimensions to group by (default: ["page"])
            row_limit: Maximum rows to return (max 25000)

        Returns:
            List of SearchAnalyticsRow objects
        """
        if dimensions is None:
            dimensions = ["page"]

        # Use the Search Analytics API
        url = f"{SEARCH_CONSOLE_API_BASE}/urlInspection/index:inspect"

        # Actually use the searchanalytics query endpoint
        url = f"{WEBMASTERS_API_BASE}/sites/{requests.utils.quote(site_url, safe='')}/searchAnalytics/query"

        request_body = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dimensions,
            "rowLimit": min(row_limit, 25000),
        }

        result = self._make_request("POST", url, json_data=request_body)

        rows = result.get("rows", [])
        return [
            SearchAnalyticsRow(
                page=row["keys"][0] if dimensions == ["page"] else row["keys"][0],
                clicks=row.get("clicks", 0),
                impressions=row.get("impressions", 0),
                ctr=row.get("ctr", 0.0),
                position=row.get("position", 0.0),
            )
            for row in rows
        ]

    def get_search_analytics_by_page(
        self,
        site_url: str,
        start_date: date,
        end_date: date,
        page_filter: str | None = None,
        row_limit: int = 1000,
    ) -> list[SearchAnalyticsRow]:
        """Query search analytics grouped by page.

        Args:
            site_url: The site URL (property) to query
            start_date: Start date
            end_date: End date
            page_filter: Optional URL prefix filter
            row_limit: Maximum rows

        Returns:
            List of SearchAnalyticsRow objects
        """
        url = f"{WEBMASTERS_API_BASE}/sites/{requests.utils.quote(site_url, safe='')}/searchAnalytics/query"

        request_body: dict[str, Any] = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": ["page"],
            "rowLimit": min(row_limit, 25000),
        }

        if page_filter:
            request_body["dimensionFilterGroups"] = [
                {
                    "filters": [
                        {
                            "dimension": "page",
                            "operator": "contains",
                            "expression": page_filter,
                        }
                    ]
                }
            ]

        result = self._make_request("POST", url, json_data=request_body)

        rows = result.get("rows", [])
        return [
            SearchAnalyticsRow(
                page=row["keys"][0],
                clicks=row.get("clicks", 0),
                impressions=row.get("impressions", 0),
                ctr=row.get("ctr", 0.0),
                position=row.get("position", 0.0),
            )
            for row in rows
        ]


def get_auth_url(redirect_uri: str, state: str | None = None) -> str:
    """Generate Google OAuth authorization URL for GSC access.

    Args:
        redirect_uri: OAuth callback URL
        state: Optional state parameter for CSRF protection

    Returns:
        Authorization URL to redirect user to
    """
    settings = get_settings()

    if not settings.google_oauth_client_id:
        raise GSCError("Google OAuth client ID not configured")

    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GSC_SCOPES),
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent to get refresh token
        "include_granted_scopes": "true",  # Incremental authorization
    }

    if state:
        params["state"] = state

    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    """Exchange authorization code for tokens.

    Args:
        code: Authorization code from OAuth callback
        redirect_uri: OAuth callback URL (must match original)

    Returns:
        Dict with access_token, refresh_token, expires_at
    """
    settings = get_settings()

    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise GSCError("Google OAuth credentials not configured")

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
            logger.error(f"GSC token exchange failed: {response.text}")
            raise GSCError("Failed to exchange authorization code")

        tokens = response.json()

        # Calculate expiry time
        expires_in = tokens.get("expires_in", 3600)
        expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))

        return {
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": expires_at,
        }

    except requests.RequestException as e:
        raise GSCError(f"Network error during token exchange: {e}") from e


def get_gsc_client() -> GoogleSearchConsoleClient | None:
    """Get a GSC client if connected.

    Returns:
        GoogleSearchConsoleClient if connected, None otherwise
    """
    from bo1.state.repositories.gsc_repository import gsc_repository

    connection = gsc_repository.get_connection()
    if not connection:
        return None

    access_token = connection.get("access_token")
    if not access_token:
        return None

    return GoogleSearchConsoleClient(
        access_token=access_token,
        refresh_token=connection.get("refresh_token"),
        expires_at=connection.get("expires_at"),
    )
