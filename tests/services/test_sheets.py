"""Tests for Google Drive integration service (sheets.py).

Tests the Drive API-based data import functionality.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from requests.exceptions import HTTPError

from backend.services.sheets import (
    SheetMetadata,
    SheetsClient,
    SheetsError,
    get_sheets_client,
    reset_sheets_client,
)


@pytest.fixture
def mock_settings():
    """Mock settings with API key."""
    with patch("backend.services.sheets.get_settings") as mock:
        mock.return_value.google_api_key = "test_api_key"
        yield mock


@pytest.fixture
def sheets_client(mock_settings):
    """Create SheetsClient with mocked settings."""
    reset_sheets_client()
    return SheetsClient(api_key="test_api_key")


class TestSheetsClientUrlParsing:
    """Tests for URL parsing."""

    def test_parse_standard_sheets_url(self, sheets_client):
        """Test parsing standard Google Sheets URL."""
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0"
        result = sheets_client.parse_sheets_url(url)
        assert result == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_parse_url_without_edit(self, sheets_client):
        """Test parsing URL without edit fragment."""
        url = "https://docs.google.com/spreadsheets/d/abc123_xyz-ABC"
        result = sheets_client.parse_sheets_url(url)
        assert result == "abc123_xyz-ABC"

    def test_parse_drive_file_url(self, sheets_client):
        """Test parsing Google Drive file URL."""
        url = "https://drive.google.com/file/d/1abc123xyz/view"
        result = sheets_client.parse_sheets_url(url)
        assert result == "1abc123xyz"

    def test_parse_drive_open_url(self, sheets_client):
        """Test parsing Google Drive open URL."""
        url = "https://drive.google.com/open?id=1abc123xyz"
        result = sheets_client.parse_sheets_url(url)
        assert result == "1abc123xyz"

    def test_parse_invalid_url_raises_error(self, sheets_client):
        """Test that invalid URL raises SheetsError."""
        with pytest.raises(SheetsError) as exc_info:
            sheets_client.parse_sheets_url("https://example.com/not-a-sheet")
        assert "Invalid Google Drive/Sheets URL" in str(exc_info.value)

    def test_parse_partial_url_raises_error(self, sheets_client):
        """Test that partial URL raises SheetsError."""
        with pytest.raises(SheetsError):
            sheets_client.parse_sheets_url("docs.google.com/spreadsheets")


class TestSheetsClientGetInfo:
    """Tests for getting file info via Drive API."""

    def test_get_file_metadata_success(self, sheets_client):
        """Test successful file metadata retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test_id",
            "name": "Test Sheet",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "size": "1234",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(sheets_client._session, "get", return_value=mock_response):
            result = sheets_client.get_spreadsheet_info("test_id")

        assert result["name"] == "Test Sheet"
        assert result["mimeType"] == "application/vnd.google-apps.spreadsheet"

    def test_get_file_metadata_not_found(self, sheets_client):
        """Test 404 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

        with patch.object(sheets_client._session, "get", return_value=mock_response):
            with pytest.raises(SheetsError) as exc_info:
                sheets_client.get_spreadsheet_info("nonexistent_id")
            assert "not found" in str(exc_info.value).lower()

    def test_get_file_metadata_access_denied(self, sheets_client):
        """Test 403 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

        with patch.object(sheets_client._session, "get", return_value=mock_response):
            with pytest.raises(SheetsError) as exc_info:
                sheets_client.get_spreadsheet_info("private_id")
            assert "access denied" in str(exc_info.value).lower()


class TestSheetsClientFetchAsCsv:
    """Tests for fetch_as_csv method."""

    def test_fetch_google_sheet_as_csv(self, sheets_client):
        """Test fetching a Google Sheet exports as CSV."""
        # Mock metadata response
        metadata_response = MagicMock()
        metadata_response.json.return_value = {
            "id": "test_id",
            "name": "Test Sheet",
            "mimeType": "application/vnd.google-apps.spreadsheet",
        }
        metadata_response.raise_for_status = MagicMock()

        # Mock export response
        export_response = MagicMock()
        export_response.content = b"Name,Age\nAlice,30\nBob,25\n"
        export_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if "/export" in url:
                return export_response
            return metadata_response

        with patch.object(sheets_client._session, "get", side_effect=mock_get):
            csv_bytes, metadata = sheets_client.fetch_as_csv("test_id")

        assert isinstance(csv_bytes, bytes)
        assert b"Name,Age" in csv_bytes
        assert metadata.title == "Test Sheet"
        assert metadata.row_count == 2
        assert metadata.column_count == 2

    def test_fetch_csv_file_directly(self, sheets_client):
        """Test downloading a CSV file directly."""
        # Mock metadata response
        metadata_response = MagicMock()
        metadata_response.json.return_value = {
            "id": "test_id",
            "name": "data.csv",
            "mimeType": "text/csv",
            "size": "100",
        }
        metadata_response.raise_for_status = MagicMock()

        # Mock download response
        download_response = MagicMock()
        download_response.content = b"Col1,Col2\nA,B\nC,D\n"
        download_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if kwargs.get("params", {}).get("alt") == "media":
                return download_response
            return metadata_response

        with patch.object(sheets_client._session, "get", side_effect=mock_get):
            csv_bytes, metadata = sheets_client.fetch_as_csv("test_id")

        assert isinstance(csv_bytes, bytes)
        assert b"Col1,Col2" in csv_bytes
        assert metadata.title == "data.csv"

    def test_fetch_file_too_large(self, sheets_client):
        """Test error when file exceeds size limit."""
        metadata_response = MagicMock()
        metadata_response.json.return_value = {
            "id": "test_id",
            "name": "huge.csv",
            "mimeType": "text/csv",
            "size": str(100 * 1024 * 1024),  # 100MB
        }
        metadata_response.raise_for_status = MagicMock()

        with patch.object(sheets_client._session, "get", return_value=metadata_response):
            with pytest.raises(SheetsError) as exc_info:
                sheets_client.fetch_as_csv("test_id")
            assert "too large" in str(exc_info.value).lower()

    def test_fetch_unsupported_mime_type(self, sheets_client):
        """Test error on unsupported file type."""
        metadata_response = MagicMock()
        metadata_response.json.return_value = {
            "id": "test_id",
            "name": "image.png",
            "mimeType": "image/png",
            "size": "1000",
        }
        metadata_response.raise_for_status = MagicMock()

        download_response = MagicMock()
        download_response.content = b"PNG binary data"
        download_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if kwargs.get("params", {}).get("alt") == "media":
                return download_response
            return metadata_response

        with patch.object(sheets_client._session, "get", side_effect=mock_get):
            with pytest.raises(SheetsError) as exc_info:
                sheets_client.fetch_as_csv("test_id")
            assert "unsupported" in str(exc_info.value).lower()


class TestSheetsClientSingleton:
    """Tests for singleton pattern."""

    def test_get_sheets_client_creates_singleton(self, mock_settings):
        """Test that get_sheets_client returns singleton."""
        reset_sheets_client()
        client1 = get_sheets_client()
        client2 = get_sheets_client()
        assert client1 is client2

    def test_reset_clears_singleton(self, mock_settings):
        """Test that reset_sheets_client clears singleton."""
        reset_sheets_client()
        client1 = get_sheets_client()
        reset_sheets_client()
        client2 = get_sheets_client()
        assert client1 is not client2


class TestSheetsClientNoApiKey:
    """Tests for missing API key."""

    def test_no_api_key_raises_error(self):
        """Test that missing API key raises SheetsError."""
        with patch("backend.services.sheets.get_settings") as mock:
            mock.return_value.google_api_key = ""
            reset_sheets_client()
            with pytest.raises(SheetsError) as exc_info:
                SheetsClient()
            assert "API key not configured" in str(exc_info.value)
