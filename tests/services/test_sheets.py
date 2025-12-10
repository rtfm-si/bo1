"""Tests for Google Sheets integration service."""

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

    def test_parse_standard_url(self, sheets_client):
        """Test parsing standard Google Sheets URL."""
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0"
        result = sheets_client.parse_sheets_url(url)
        assert result == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

    def test_parse_url_without_edit(self, sheets_client):
        """Test parsing URL without edit fragment."""
        url = "https://docs.google.com/spreadsheets/d/abc123_xyz-ABC"
        result = sheets_client.parse_sheets_url(url)
        assert result == "abc123_xyz-ABC"

    def test_parse_invalid_url_raises_error(self, sheets_client):
        """Test that invalid URL raises SheetsError."""
        with pytest.raises(SheetsError) as exc_info:
            sheets_client.parse_sheets_url("https://example.com/not-a-sheet")
        assert "Invalid Google Sheets URL" in str(exc_info.value)

    def test_parse_partial_url_raises_error(self, sheets_client):
        """Test that partial URL raises SheetsError."""
        with pytest.raises(SheetsError):
            sheets_client.parse_sheets_url("docs.google.com/spreadsheets")


class TestSheetsClientGetInfo:
    """Tests for getting spreadsheet info."""

    def test_get_spreadsheet_info_success(self, sheets_client):
        """Test successful spreadsheet info retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "properties": {"title": "Test Sheet"},
            "sheets": [{"properties": {"title": "Sheet1"}}],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(sheets_client._session, "get", return_value=mock_response):
            result = sheets_client.get_spreadsheet_info("test_id")

        assert result["properties"]["title"] == "Test Sheet"

    def test_get_spreadsheet_info_not_found(self, sheets_client):
        """Test 404 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

        with patch.object(sheets_client._session, "get", return_value=mock_response):
            with pytest.raises(SheetsError) as exc_info:
                sheets_client.get_spreadsheet_info("nonexistent_id")
            assert "not found" in str(exc_info.value).lower()

    def test_get_spreadsheet_info_access_denied(self, sheets_client):
        """Test 403 error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)

        with patch.object(sheets_client._session, "get", return_value=mock_response):
            with pytest.raises(SheetsError) as exc_info:
                sheets_client.get_spreadsheet_info("private_id")
            assert "access denied" in str(exc_info.value).lower()


class TestSheetsClientFetchData:
    """Tests for fetching sheet data."""

    def test_fetch_sheet_data_success(self, sheets_client):
        """Test successful data fetch."""
        # Mock get_spreadsheet_info
        with patch.object(
            sheets_client,
            "get_spreadsheet_info",
            return_value={
                "properties": {"title": "Test Data"},
                "sheets": [{"properties": {"title": "Data"}}],
            },
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "values": [
                    ["Name", "Age", "City"],
                    ["Alice", 30, "NYC"],
                    ["Bob", 25, "LA"],
                ]
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(sheets_client._session, "get", return_value=mock_response):
                df, metadata = sheets_client.fetch_sheet_data("test_id")

        assert len(df) == 2
        assert list(df.columns) == ["Name", "Age", "City"]
        assert metadata.title == "Test Data"
        assert metadata.row_count == 2
        assert metadata.column_count == 3

    def test_fetch_sheet_data_empty_sheet(self, sheets_client):
        """Test error on empty sheet."""
        with patch.object(
            sheets_client,
            "get_spreadsheet_info",
            return_value={
                "properties": {"title": "Empty"},
                "sheets": [{"properties": {"title": "Sheet1"}}],
            },
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {"values": []}
            mock_response.raise_for_status = MagicMock()

            with patch.object(sheets_client._session, "get", return_value=mock_response):
                with pytest.raises(SheetsError) as exc_info:
                    sheets_client.fetch_sheet_data("test_id")
                assert "empty" in str(exc_info.value).lower()

    def test_fetch_sheet_data_normalizes_row_lengths(self, sheets_client):
        """Test that short rows are padded."""
        with patch.object(
            sheets_client,
            "get_spreadsheet_info",
            return_value={
                "properties": {"title": "Sparse"},
                "sheets": [{"properties": {"title": "Sheet1"}}],
            },
        ):
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "values": [
                    ["A", "B", "C"],
                    ["1"],  # Short row
                    ["2", "3"],  # Short row
                    ["4", "5", "6"],  # Full row
                ]
            }
            mock_response.raise_for_status = MagicMock()

            with patch.object(sheets_client._session, "get", return_value=mock_response):
                df, _ = sheets_client.fetch_sheet_data("test_id")

        assert len(df) == 3
        assert df.iloc[0, 2] == ""  # Padded value
        assert df.iloc[1, 2] == ""  # Padded value
        assert df.iloc[2, 2] == "6"


class TestSheetsClientFetchAsCsv:
    """Tests for fetch_as_csv method."""

    def test_fetch_as_csv_returns_bytes(self, sheets_client):
        """Test that fetch_as_csv returns CSV bytes."""
        with patch.object(
            sheets_client,
            "fetch_sheet_data",
            return_value=(
                pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [30, 25]}),
                SheetMetadata(
                    spreadsheet_id="test",
                    title="Test",
                    sheet_name="Sheet1",
                    row_count=2,
                    column_count=2,
                ),
            ),
        ):
            csv_bytes, metadata = sheets_client.fetch_as_csv("test_id")

        assert isinstance(csv_bytes, bytes)
        assert b"Name,Age" in csv_bytes
        assert b"Alice,30" in csv_bytes
        assert metadata.row_count == 2


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
