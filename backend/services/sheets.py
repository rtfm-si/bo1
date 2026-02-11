"""Google Drive integration service for data file imports.

Fetches data from Google Drive using Drive API v3 (drive.file scope).
- Google Sheets: Exported as CSV via Drive API
- Uploaded files (CSV, XLSX, etc.): Downloaded directly

No Sheets API required - only Drive API with drive.file scope.
"""

import io
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import pandas as pd
import requests

from backend.services.google_oauth import refresh_google_token
from backend.services.http_utils import create_resilient_session
from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Google Drive API base URL
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files"

# URL patterns for Google Drive files
DRIVE_URL_PATTERNS = [
    # Google Sheets: https://docs.google.com/spreadsheets/d/{fileId}/edit
    r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)",
    # Google Drive file: https://drive.google.com/file/d/{fileId}/view
    r"drive\.google\.com/file/d/([a-zA-Z0-9_-]+)",
    # Google Drive open: https://drive.google.com/open?id={fileId}
    r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)",
]

# MIME types
GOOGLE_SHEETS_MIME = "application/vnd.google-apps.spreadsheet"
CSV_MIME = "text/csv"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLS_MIME = "application/vnd.ms-excel"
TSV_MIME = "text/tab-separated-values"
TEXT_MIME = "text/plain"

# Limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max download


class SheetsError(Exception):
    """Error during Google Drive/Sheets operation."""

    def __init__(self, message: str, spreadsheet_id: str | None = None) -> None:
        """Initialize SheetsError."""
        self.spreadsheet_id = spreadsheet_id
        super().__init__(message)


@dataclass
class SheetMetadata:
    """Metadata about a fetched file."""

    spreadsheet_id: str
    title: str
    sheet_name: str  # For compatibility - will be "Sheet1" for non-Sheets files
    row_count: int
    column_count: int


class SheetsClient:
    """DEPRECATED: Use OAuthSheetsClient instead.

    Client for fetching data from Google Drive using API key.
    Only supports public files. OAuth-based access is now required.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Drive client.

        Args:
            api_key: Google API key (defaults to settings)
        """
        settings = get_settings()
        self._api_key = api_key or settings.google_api_key

        if not self._api_key:
            raise SheetsError(
                "Google API key not configured. Set GOOGLE_API_KEY environment variable."
            )

        self._session = create_resilient_session(
            status_forcelist=[429, 500, 502, 503, 504],
        )

    def parse_sheets_url(self, url: str) -> str:
        """Extract file ID from a Google Drive/Sheets URL.

        Args:
            url: Google Drive or Sheets URL

        Returns:
            File ID

        Raises:
            SheetsError: If URL is not a valid Google Drive URL
        """
        for pattern in DRIVE_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise SheetsError(f"Invalid Google Drive/Sheets URL: {url}")

    def _get_file_metadata(self, file_id: str) -> dict:
        """Get file metadata from Drive API.

        Args:
            file_id: Google Drive file ID

        Returns:
            File metadata dict with name, mimeType, size

        Raises:
            SheetsError: If API request fails
        """
        url = f"{DRIVE_API_BASE}/{file_id}"
        params = {
            "key": self._api_key,
            "fields": "id,name,mimeType,size",
        }

        try:
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 404:
                raise SheetsError(
                    "File not found. Make sure the URL is correct and the file is publicly accessible.",
                    file_id,
                ) from None
            elif status_code == 403:
                raise SheetsError(
                    "Access denied. Make sure the file is set to 'Anyone with the link can view'.",
                    file_id,
                ) from None
            else:
                raise SheetsError(f"Failed to fetch file info: {e}", file_id) from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error fetching file: {e}", file_id) from e

    def _export_google_sheet(self, file_id: str) -> bytes:
        """Export a Google Sheet as CSV using Drive API.

        Args:
            file_id: Google Drive file ID

        Returns:
            CSV content as bytes

        Raises:
            SheetsError: If export fails
        """
        url = f"{DRIVE_API_BASE}/{file_id}/export"
        params = {
            "key": self._api_key,
            "mimeType": CSV_MIME,
        }

        try:
            response = self._session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 403:
                raise SheetsError(
                    "Access denied. Make sure the file is set to 'Anyone with the link can view'.",
                    file_id,
                ) from None
            else:
                raise SheetsError(f"Failed to export file: {e}", file_id) from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error exporting file: {e}", file_id) from e

    def _download_file(self, file_id: str) -> bytes:
        """Download a file directly from Drive.

        Args:
            file_id: Google Drive file ID

        Returns:
            File content as bytes

        Raises:
            SheetsError: If download fails
        """
        url = f"{DRIVE_API_BASE}/{file_id}"
        params = {
            "key": self._api_key,
            "alt": "media",
        }

        try:
            response = self._session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 403:
                raise SheetsError(
                    "Access denied. Make sure the file is set to 'Anyone with the link can view'.",
                    file_id,
                ) from None
            else:
                raise SheetsError(f"Failed to download file: {e}", file_id) from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error downloading file: {e}", file_id) from e

    def _convert_to_csv(self, content: bytes, mime_type: str, filename: str) -> bytes:
        """Convert file content to CSV format.

        Args:
            content: Raw file bytes
            mime_type: MIME type of the file
            filename: Original filename

        Returns:
            CSV content as bytes

        Raises:
            SheetsError: If conversion fails
        """
        try:
            if mime_type in (CSV_MIME, TEXT_MIME, TSV_MIME):
                # Already text-based, just return (handle TSV)
                if mime_type == TSV_MIME:
                    df = pd.read_csv(io.BytesIO(content), sep="\t")
                    buffer = io.BytesIO()
                    df.to_csv(buffer, index=False, encoding="utf-8")
                    return buffer.getvalue()
                return content

            elif mime_type in (XLSX_MIME, XLS_MIME):
                # Excel file - convert with pandas
                df = pd.read_excel(io.BytesIO(content))
                buffer = io.BytesIO()
                df.to_csv(buffer, index=False, encoding="utf-8")
                return buffer.getvalue()

            else:
                raise SheetsError(f"Unsupported file type: {mime_type}")

        except Exception as e:
            if isinstance(e, SheetsError):
                raise
            raise SheetsError(f"Failed to convert file to CSV: {e}") from e

    def fetch_as_csv(
        self,
        file_id: str,
        sheet_name: str | None = None,  # Ignored for Drive API (exports first sheet)
        max_rows: int = 50_000,  # Applied after download
    ) -> tuple[bytes, SheetMetadata]:
        """Fetch file data as CSV bytes.

        For Google Sheets: exports as CSV via Drive API
        For other files: downloads and converts to CSV

        Args:
            file_id: Google Drive file ID
            sheet_name: Ignored (Drive API exports first sheet only)
            max_rows: Maximum rows to keep (applied after download)

        Returns:
            Tuple of (CSV bytes, SheetMetadata)
        """
        # Get file metadata
        metadata = self._get_file_metadata(file_id)
        name = metadata.get("name", "Untitled")
        mime_type = metadata.get("mimeType", "")
        file_size = int(metadata.get("size", 0) or 0)

        # Check file size for non-Google-native files
        if mime_type != GOOGLE_SHEETS_MIME and file_size > MAX_FILE_SIZE:
            raise SheetsError(
                f"File too large ({file_size} bytes). Maximum is {MAX_FILE_SIZE} bytes."
            )

        # Fetch content based on type
        if mime_type == GOOGLE_SHEETS_MIME:
            # Google Sheets - export as CSV
            csv_content = self._export_google_sheet(file_id)
            logger.info(f"Exported Google Sheet '{name}' as CSV ({len(csv_content)} bytes)")
        else:
            # Regular file - download and convert
            content = self._download_file(file_id)
            csv_content = self._convert_to_csv(content, mime_type, name)
            logger.info(
                f"Downloaded and converted '{name}' ({mime_type}) to CSV ({len(csv_content)} bytes)"
            )

        # Parse CSV to get row/column counts and apply max_rows
        df = pd.read_csv(io.BytesIO(csv_content))
        if len(df) > max_rows:
            df = df.head(max_rows)
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False, encoding="utf-8")
            csv_content = buffer.getvalue()
            logger.info(f"Truncated to {max_rows} rows")

        sheet_metadata = SheetMetadata(
            spreadsheet_id=file_id,
            title=name,
            sheet_name="Sheet1",  # Drive API exports first sheet
            row_count=len(df),
            column_count=len(df.columns),
        )

        return csv_content, sheet_metadata

    # Compatibility aliases
    def get_spreadsheet_info(self, spreadsheet_id: str) -> dict:
        """Get file metadata (compatibility method)."""
        return self._get_file_metadata(spreadsheet_id)


# Singleton instance


@lru_cache(maxsize=1)
def get_sheets_client() -> SheetsClient:
    """DEPRECATED: Use get_oauth_sheets_client instead.

    Get or create the singleton SheetsClient instance.
    """
    import warnings

    warnings.warn(
        "get_sheets_client is deprecated. Use get_oauth_sheets_client for OAuth-based access.",
        DeprecationWarning,
        stacklevel=2,
    )
    return SheetsClient()


def reset_sheets_client() -> None:
    """Reset the singleton client (for testing)."""
    get_sheets_client.cache_clear()


class OAuthSheetsClient:
    """Client for fetching data from Google Drive using OAuth tokens.

    Uses user's OAuth access token for private file access.
    Handles token refresh automatically when expired.
    """

    def __init__(
        self, user_id: str, access_token: str, refresh_token: str | None, expires_at: str | None
    ) -> None:
        """Initialize OAuth Drive client.

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

        self._session = create_resilient_session()

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

        tokens = refresh_google_token(self._refresh_token, client_id, client_secret)
        if tokens is None:
            return False

        self._access_token = tokens.get("access_token", "")
        expires_in = tokens.get("expires_in")

        if expires_in:
            self._expires_at = (datetime.now(UTC) + timedelta(seconds=int(expires_in))).isoformat()

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

    def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if needed."""
        if self._is_token_expired():
            if not self._refresh_access_token():
                raise SheetsError(
                    "Google access token expired and refresh failed. Please reconnect Google Drive."
                )

    def _make_request(
        self, url: str, params: dict | None = None, stream: bool = False
    ) -> requests.Response:
        """Make authenticated request to Drive API.

        Args:
            url: API URL
            params: Query parameters
            stream: Whether to stream response

        Returns:
            Response object

        Raises:
            SheetsError: If request fails
        """
        self._ensure_valid_token()

        headers = {"Authorization": f"Bearer {self._access_token}"}

        try:
            response = self._session.get(
                url, headers=headers, params=params, timeout=60, stream=stream
            )

            # Handle 401 - try refresh once
            if response.status_code == 401:
                if self._refresh_access_token():
                    headers = {"Authorization": f"Bearer {self._access_token}"}
                    response = self._session.get(
                        url, headers=headers, params=params, timeout=60, stream=stream
                    )
                else:
                    raise SheetsError("Google access token invalid. Please reconnect Google Drive.")

            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 404:
                raise SheetsError("File not found. Make sure the URL is correct.") from None
            elif status_code == 403:
                raise SheetsError(
                    "Access denied. You don't have permission to view this file."
                ) from None
            else:
                raise SheetsError(f"Failed to fetch file: {e}") from e
        except requests.exceptions.RequestException as e:
            raise SheetsError(f"Network error: {e}") from e

    def parse_sheets_url(self, url: str) -> str:
        """Extract file ID from a Google Drive/Sheets URL."""
        for pattern in DRIVE_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        raise SheetsError(f"Invalid Google Drive/Sheets URL: {url}")

    def _get_file_metadata(self, file_id: str) -> dict:
        """Get file metadata from Drive API."""
        url = f"{DRIVE_API_BASE}/{file_id}"
        params = {"fields": "id,name,mimeType,size"}
        response = self._make_request(url, params)
        return response.json()

    def _export_google_sheet(self, file_id: str) -> bytes:
        """Export a Google Sheet as CSV."""
        url = f"{DRIVE_API_BASE}/{file_id}/export"
        params = {"mimeType": CSV_MIME}
        response = self._make_request(url, params)
        return response.content

    def _download_file(self, file_id: str) -> bytes:
        """Download a file directly from Drive."""
        url = f"{DRIVE_API_BASE}/{file_id}"
        params = {"alt": "media"}
        response = self._make_request(url, params)
        return response.content

    def _convert_to_csv(self, content: bytes, mime_type: str, filename: str) -> bytes:
        """Convert file content to CSV format."""
        try:
            if mime_type in (CSV_MIME, TEXT_MIME, TSV_MIME):
                if mime_type == TSV_MIME:
                    df = pd.read_csv(io.BytesIO(content), sep="\t")
                    buffer = io.BytesIO()
                    df.to_csv(buffer, index=False, encoding="utf-8")
                    return buffer.getvalue()
                return content

            elif mime_type in (XLSX_MIME, XLS_MIME):
                df = pd.read_excel(io.BytesIO(content))
                buffer = io.BytesIO()
                df.to_csv(buffer, index=False, encoding="utf-8")
                return buffer.getvalue()

            else:
                raise SheetsError(f"Unsupported file type: {mime_type}")

        except Exception as e:
            if isinstance(e, SheetsError):
                raise
            raise SheetsError(f"Failed to convert file to CSV: {e}") from e

    def fetch_as_csv(
        self,
        file_id: str,
        sheet_name: str | None = None,
        max_rows: int = 50_000,
    ) -> tuple[bytes, SheetMetadata]:
        """Fetch file data as CSV bytes using OAuth.

        For Google Sheets: exports as CSV via Drive API
        For other files: downloads and converts to CSV

        Args:
            file_id: Google Drive file ID
            sheet_name: Ignored (Drive API exports first sheet only)
            max_rows: Maximum rows to keep

        Returns:
            Tuple of (CSV bytes, SheetMetadata)
        """
        # Get file metadata
        metadata = self._get_file_metadata(file_id)
        name = metadata.get("name", "Untitled")
        mime_type = metadata.get("mimeType", "")
        file_size = int(metadata.get("size", 0) or 0)

        # Check file size for non-Google-native files
        if mime_type != GOOGLE_SHEETS_MIME and file_size > MAX_FILE_SIZE:
            raise SheetsError(
                f"File too large ({file_size} bytes). Maximum is {MAX_FILE_SIZE} bytes."
            )

        # Fetch content based on type
        if mime_type == GOOGLE_SHEETS_MIME:
            csv_content = self._export_google_sheet(file_id)
            logger.info(f"[OAuth] Exported Google Sheet '{name}' as CSV ({len(csv_content)} bytes)")
        else:
            content = self._download_file(file_id)
            csv_content = self._convert_to_csv(content, mime_type, name)
            logger.info(
                f"[OAuth] Downloaded '{name}' ({mime_type}) to CSV ({len(csv_content)} bytes)"
            )

        # Parse CSV to get row/column counts and apply max_rows
        df = pd.read_csv(io.BytesIO(csv_content))
        if len(df) > max_rows:
            df = df.head(max_rows)
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False, encoding="utf-8")
            csv_content = buffer.getvalue()
            logger.info(f"[OAuth] Truncated to {max_rows} rows")

        sheet_metadata = SheetMetadata(
            spreadsheet_id=file_id,
            title=name,
            sheet_name="Sheet1",
            row_count=len(df),
            column_count=len(df.columns),
        )

        return csv_content, sheet_metadata

    # Compatibility alias
    def get_spreadsheet_info(self, spreadsheet_id: str) -> dict:
        """Get file metadata (compatibility method)."""
        return self._get_file_metadata(spreadsheet_id)


def get_oauth_sheets_client(user_id: str) -> OAuthSheetsClient | None:
    """Get an OAuth Drive client for a user if they have tokens.

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
