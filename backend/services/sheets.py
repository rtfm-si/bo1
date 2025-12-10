"""Google Sheets integration service.

Fetches data from Google Sheets using the Sheets API v4.
- Public sheets: Uses GOOGLE_API_KEY
- Private sheets: Uses user's OAuth tokens
"""

import io
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Google Sheets API base URL
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105

# URL patterns for Google Sheets
SHEETS_URL_PATTERNS = [
    # https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid=0
    r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)",
    # https://docs.google.com/spreadsheets/d/{spreadsheet_id}
    r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)",
]

# Limits
MAX_ROWS = 50_000  # Max rows to fetch
MAX_CELLS = 500_000  # Max total cells (API limit is 10M but we're conservative)


class SheetsError(Exception):
    """Error during Google Sheets operation."""

    def __init__(self, message: str, spreadsheet_id: str | None = None) -> None:
        """Initialize SheetsError."""
        self.spreadsheet_id = spreadsheet_id
        super().__init__(message)


@dataclass
class SheetMetadata:
    """Metadata about a fetched sheet."""

    spreadsheet_id: str
    title: str
    sheet_name: str
    row_count: int
    column_count: int


class SheetsClient:
    """Client for fetching data from Google Sheets.

    Uses Google Sheets API v4 with API key authentication.
    Only supports public sheets (anyone with link can view).
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Sheets client.

        Args:
            api_key: Google API key (defaults to settings)
        """
        settings = get_settings()
        self._api_key = api_key or settings.google_api_key

        if not self._api_key:
            raise SheetsError(
                "Google API key not configured. Set GOOGLE_API_KEY environment variable."
            )

        # Configure session with retry logic
        self._session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)

    def parse_sheets_url(self, url: str) -> str:
        """Extract spreadsheet ID from a Google Sheets URL.

        Args:
            url: Google Sheets URL

        Returns:
            Spreadsheet ID

        Raises:
            SheetsError: If URL is not a valid Google Sheets URL
        """
        for pattern in SHEETS_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise SheetsError(f"Invalid Google Sheets URL: {url}")

    def get_spreadsheet_info(self, spreadsheet_id: str) -> dict:
        """Get spreadsheet metadata.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID

        Returns:
            Spreadsheet metadata dict

        Raises:
            SheetsError: If API request fails
        """
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}"
        params = {
            "key": self._api_key,
            "fields": "properties.title,sheets.properties",
        }

        try:
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 404:
                raise SheetsError(
                    "Spreadsheet not found. Make sure the URL is correct and the sheet is publicly accessible.",
                    spreadsheet_id,
                ) from None
            elif status_code == 403:
                raise SheetsError(
                    "Access denied. Make sure the sheet is set to 'Anyone with the link can view'.",
                    spreadsheet_id,
                ) from None
            else:
                raise SheetsError(f"Failed to fetch spreadsheet info: {e}", spreadsheet_id) from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error fetching spreadsheet: {e}", spreadsheet_id) from e

    def fetch_sheet_data(
        self,
        spreadsheet_id: str,
        sheet_name: str | None = None,
        max_rows: int = MAX_ROWS,
    ) -> tuple[pd.DataFrame, SheetMetadata]:
        """Fetch data from a Google Sheet as a DataFrame.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of specific sheet (defaults to first sheet)
            max_rows: Maximum rows to fetch (default: 50,000)

        Returns:
            Tuple of (DataFrame, SheetMetadata)

        Raises:
            SheetsError: If API request fails or sheet is empty
        """
        # Get spreadsheet info to find sheet names
        info = self.get_spreadsheet_info(spreadsheet_id)
        title = info.get("properties", {}).get("title", "Untitled")
        sheets = info.get("sheets", [])

        if not sheets:
            raise SheetsError("Spreadsheet has no sheets", spreadsheet_id)

        # Find target sheet
        if sheet_name:
            target_sheet = None
            for sheet in sheets:
                props = sheet.get("properties", {})
                if props.get("title") == sheet_name:
                    target_sheet = props
                    break
            if not target_sheet:
                available = [s.get("properties", {}).get("title") for s in sheets]
                raise SheetsError(
                    f"Sheet '{sheet_name}' not found. Available sheets: {available}",
                    spreadsheet_id,
                )
        else:
            target_sheet = sheets[0].get("properties", {})
            sheet_name = target_sheet.get("title", "Sheet1")

        # Fetch sheet data
        range_notation = f"'{sheet_name}'!A1:ZZ{max_rows}"
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}"
        params = {
            "key": self._api_key,
            "valueRenderOption": "UNFORMATTED_VALUE",
            "dateTimeRenderOption": "FORMATTED_STRING",
        }

        try:
            response = self._session.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 403:
                raise SheetsError(
                    "Access denied. Make sure the sheet is set to 'Anyone with the link can view'.",
                    spreadsheet_id,
                ) from None
            else:
                raise SheetsError(f"Failed to fetch sheet data: {e}", spreadsheet_id) from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error fetching sheet data: {e}", spreadsheet_id) from e

        values = data.get("values", [])
        if not values:
            raise SheetsError("Sheet is empty", spreadsheet_id)

        # Convert to DataFrame
        # First row is header
        headers = values[0] if values else []
        rows = values[1:] if len(values) > 1 else []

        # Normalize row lengths (pad short rows)
        max_cols = len(headers)
        normalized_rows = []
        for row in rows:
            if len(row) < max_cols:
                row = row + [""] * (max_cols - len(row))
            elif len(row) > max_cols:
                row = row[:max_cols]
            normalized_rows.append(row)

        df = pd.DataFrame(normalized_rows, columns=headers)

        # Create metadata
        metadata = SheetMetadata(
            spreadsheet_id=spreadsheet_id,
            title=title,
            sheet_name=sheet_name,
            row_count=len(df),
            column_count=len(df.columns),
        )

        logger.info(
            f"Fetched sheet '{sheet_name}' from '{title}': "
            f"{metadata.row_count} rows x {metadata.column_count} cols"
        )

        return df, metadata

    def fetch_as_csv(
        self,
        spreadsheet_id: str,
        sheet_name: str | None = None,
        max_rows: int = MAX_ROWS,
    ) -> tuple[bytes, SheetMetadata]:
        """Fetch sheet data and convert to CSV bytes.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of specific sheet (defaults to first sheet)
            max_rows: Maximum rows to fetch

        Returns:
            Tuple of (CSV bytes, SheetMetadata)
        """
        df, metadata = self.fetch_sheet_data(spreadsheet_id, sheet_name, max_rows)

        # Convert to CSV
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        csv_bytes = buffer.getvalue()

        return csv_bytes, metadata


# Singleton instance
_sheets_client: SheetsClient | None = None


def get_sheets_client() -> SheetsClient:
    """Get or create the singleton SheetsClient instance."""
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient()
    return _sheets_client


def reset_sheets_client() -> None:
    """Reset the singleton client (for testing)."""
    global _sheets_client
    _sheets_client = None


class OAuthSheetsClient:
    """Client for fetching data from Google Sheets using OAuth tokens.

    Uses user's OAuth access token for private sheets access.
    Handles token refresh automatically when expired.
    """

    def __init__(
        self, user_id: str, access_token: str, refresh_token: str | None, expires_at: str | None
    ) -> None:
        """Initialize OAuth Sheets client.

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

        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")

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

            user_repository.save_google_tokens(
                user_id=self._user_id,
                access_token=self._access_token,
                refresh_token=self._refresh_token,
                expires_at=self._expires_at,
                scopes=tokens.get("scope"),
            )

            logger.info(f"Refreshed Google access token for user {self._user_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"Token refresh request failed: {e}")
            return False

    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if needed."""
        if self._is_token_expired():
            if not self._refresh_access_token():
                raise SheetsError(
                    "Google access token expired and refresh failed. Please reconnect Google Sheets."
                )

    def _make_request(self, url: str, params: dict | None = None) -> dict:
        """Make authenticated request to Sheets API.

        Args:
            url: API URL
            params: Query parameters

        Returns:
            JSON response

        Raises:
            SheetsError: If request fails
        """
        self._ensure_valid_token()

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = self._session.get(url, headers=headers, params=params, timeout=60)

            # Handle 401 - try refresh once
            if response.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self._access_token}"}
                    response = self._session.get(url, headers=headers, params=params, timeout=60)
                else:
                    raise SheetsError(
                        "Google access token invalid. Please reconnect Google Sheets."
                    )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 404:
                raise SheetsError("Spreadsheet not found. Make sure the URL is correct.") from None
            elif status_code == 403:
                raise SheetsError(
                    "Access denied. You don't have permission to view this spreadsheet."
                ) from None
            else:
                raise SheetsError(f"Failed to fetch spreadsheet: {e}") from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error: {e}") from e

    def parse_sheets_url(self, url: str) -> str:
        """Extract spreadsheet ID from a Google Sheets URL."""
        for pattern in SHEETS_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise SheetsError(f"Invalid Google Sheets URL: {url}")

    def get_spreadsheet_info(self, spreadsheet_id: str) -> dict:
        """Get spreadsheet metadata."""
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}"
        params = {"fields": "properties.title,sheets.properties"}
        return self._make_request(url, params)

    def fetch_sheet_data(
        self,
        spreadsheet_id: str,
        sheet_name: str | None = None,
        max_rows: int = MAX_ROWS,
    ) -> tuple[pd.DataFrame, SheetMetadata]:
        """Fetch data from a Google Sheet as a DataFrame.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Name of specific sheet (defaults to first sheet)
            max_rows: Maximum rows to fetch

        Returns:
            Tuple of (DataFrame, SheetMetadata)
        """
        # Get spreadsheet info
        info = self.get_spreadsheet_info(spreadsheet_id)
        title = info.get("properties", {}).get("title", "Untitled")
        sheets = info.get("sheets", [])

        if not sheets:
            raise SheetsError("Spreadsheet has no sheets", spreadsheet_id)

        # Find target sheet
        if sheet_name:
            target_sheet = None
            for sheet in sheets:
                props = sheet.get("properties", {})
                if props.get("title") == sheet_name:
                    target_sheet = props
                    break
            if not target_sheet:
                available = [s.get("properties", {}).get("title") for s in sheets]
                raise SheetsError(
                    f"Sheet '{sheet_name}' not found. Available: {available}", spreadsheet_id
                )
        else:
            target_sheet = sheets[0].get("properties", {})
            sheet_name = target_sheet.get("title", "Sheet1")

        # Fetch sheet data
        range_notation = f"'{sheet_name}'!A1:ZZ{max_rows}"
        url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_notation}"
        params = {
            "valueRenderOption": "UNFORMATTED_VALUE",
            "dateTimeRenderOption": "FORMATTED_STRING",
        }

        data = self._make_request(url, params)
        values = data.get("values", [])

        if not values:
            raise SheetsError("Sheet is empty", spreadsheet_id)

        # Convert to DataFrame
        headers = values[0] if values else []
        rows = values[1:] if len(values) > 1 else []

        # Normalize row lengths
        max_cols = len(headers)
        normalized_rows = []
        for row in rows:
            if len(row) < max_cols:
                row = row + [""] * (max_cols - len(row))
            elif len(row) > max_cols:
                row = row[:max_cols]
            normalized_rows.append(row)

        df = pd.DataFrame(normalized_rows, columns=headers)

        metadata = SheetMetadata(
            spreadsheet_id=spreadsheet_id,
            title=title,
            sheet_name=sheet_name,
            row_count=len(df),
            column_count=len(df.columns),
        )

        logger.info(
            f"[OAuth] Fetched sheet '{sheet_name}' from '{title}': {metadata.row_count}x{metadata.column_count}"
        )
        return df, metadata

    def fetch_as_csv(
        self,
        spreadsheet_id: str,
        sheet_name: str | None = None,
        max_rows: int = MAX_ROWS,
    ) -> tuple[bytes, SheetMetadata]:
        """Fetch sheet data and convert to CSV bytes."""
        df, metadata = self.fetch_sheet_data(spreadsheet_id, sheet_name, max_rows)

        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        csv_bytes = buffer.getvalue()

        return csv_bytes, metadata


def get_oauth_sheets_client(user_id: str) -> OAuthSheetsClient | None:
    """Get an OAuth Sheets client for a user if they have tokens.

    Args:
        user_id: User ID

    Returns:
        OAuthSheetsClient if user has valid tokens, None otherwise
    """
    from bo1.state.repositories import user_repository

    tokens = user_repository.get_google_tokens(user_id)
    if not tokens:
        return None

    access_token = tokens.get("access_token")
    if not access_token:
        return None

    return OAuthSheetsClient(
        user_id=user_id,
        access_token=access_token,
        refresh_token=tokens.get("refresh_token"),
        expires_at=tokens.get("expires_at"),
    )
