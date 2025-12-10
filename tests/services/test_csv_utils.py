"""Tests for CSV validation utilities."""

import pytest

from backend.services.csv_utils import (
    CSVMetadata,
    CSVValidationError,
    count_csv_rows,
    detect_delimiter,
    detect_encoding,
    validate_csv_headers,
    validate_csv_structure,
)


class TestDetectEncoding:
    """Tests for encoding detection."""

    def test_detect_utf8(self):
        """Test UTF-8 detection."""
        content = b"name,value\nalice,100\nbob,200"
        assert detect_encoding(content) == "utf-8"

    def test_detect_utf8_with_bom(self):
        """Test UTF-8 with special characters."""
        content = "name,value\nälice,100\nbøb,200".encode()
        assert detect_encoding(content) == "utf-8"

    def test_detect_latin1(self):
        """Test Latin-1 detection for non-UTF8 content."""
        # Create content that's valid Latin-1 but invalid UTF-8
        content = b"name,value\nalice,\xe9100"  # \xe9 is é in Latin-1
        assert detect_encoding(content) == "latin-1"


class TestDetectDelimiter:
    """Tests for delimiter detection."""

    def test_detect_comma(self):
        """Test comma delimiter detection."""
        sample = "name,value,count\nalice,100,5"
        assert detect_delimiter(sample) == ","

    def test_detect_semicolon(self):
        """Test semicolon delimiter detection."""
        sample = "name;value;count\nalice;100;5"
        assert detect_delimiter(sample) == ";"

    def test_detect_tab(self):
        """Test tab delimiter detection."""
        sample = "name\tvalue\tcount\nalice\t100\t5"
        assert detect_delimiter(sample) == "\t"

    def test_default_to_comma(self):
        """Test default to comma when detection fails."""
        sample = "single_column\nvalue1\nvalue2"
        assert detect_delimiter(sample) == ","


class TestValidateCSVHeaders:
    """Tests for CSV header validation."""

    def test_valid_csv(self):
        """Test valid CSV with headers."""
        content = b"name,age,city\nalice,30,nyc\nbob,25,la"
        metadata = validate_csv_headers(content)

        assert metadata.headers == ["name", "age", "city"]
        assert metadata.row_count == 2
        assert metadata.column_count == 3
        assert metadata.delimiter == ","
        assert metadata.encoding == "utf-8"

    def test_empty_file(self):
        """Test empty file raises error."""
        with pytest.raises(CSVValidationError) as exc:
            validate_csv_headers(b"")
        assert "Empty file" in str(exc.value)

    def test_no_headers(self):
        """Test file with no content raises error."""
        with pytest.raises(CSVValidationError) as exc:
            validate_csv_headers(b"\n\n")
        assert "No headers found" in str(exc.value)

    def test_empty_header(self):
        """Test empty column header raises error."""
        content = b"name,,city\nalice,30,nyc"
        with pytest.raises(CSVValidationError) as exc:
            validate_csv_headers(content)
        assert "Empty column header" in str(exc.value)

    def test_duplicate_headers(self):
        """Test duplicate headers raises error."""
        content = b"name,age,name\nalice,30,bob"
        with pytest.raises(CSVValidationError) as exc:
            validate_csv_headers(content)
        assert "Duplicate column headers" in str(exc.value)

    def test_whitespace_trimmed(self):
        """Test whitespace is trimmed from headers."""
        content = b" name , age , city \nalice,30,nyc"
        metadata = validate_csv_headers(content)
        assert metadata.headers == ["name", "age", "city"]


class TestCountCSVRows:
    """Tests for row counting."""

    def test_count_rows(self):
        """Test basic row counting."""
        content = b"name,value\nrow1,1\nrow2,2\nrow3,3"
        assert count_csv_rows(content) == 3

    def test_count_empty(self):
        """Test counting empty file."""
        content = b""
        assert count_csv_rows(content) == 0

    def test_count_header_only(self):
        """Test counting file with header only."""
        content = b"name,value"
        assert count_csv_rows(content) == 0


class TestValidateCSVStructure:
    """Tests for full CSV structure validation."""

    def test_valid_structure(self):
        """Test valid CSV structure."""
        content = b"name,value\nrow1,1\nrow2,2"
        metadata = validate_csv_structure(content)

        assert metadata.headers == ["name", "value"]
        assert metadata.row_count == 2
        assert metadata.column_count == 2

    def test_too_many_columns(self):
        """Test CSV with too many columns."""
        # Create CSV with 101 columns
        headers = ",".join([f"col{i}" for i in range(101)])
        values = ",".join(["v" for _ in range(101)])
        content = f"{headers}\n{values}".encode()

        with pytest.raises(CSVValidationError) as exc:
            validate_csv_structure(content, max_columns=100)
        assert "Too many columns" in str(exc.value)

    def test_inconsistent_columns(self):
        """Test CSV with inconsistent column count."""
        content = b"name,value,extra\nrow1,1\nrow2,2,3"

        with pytest.raises(CSVValidationError) as exc:
            validate_csv_structure(content)
        assert "Row 2 has 2 columns, expected 3" in str(exc.value)

    def test_semicolon_delimiter(self):
        """Test CSV with semicolon delimiter."""
        content = b"name;value\nrow1;1\nrow2;2"
        metadata = validate_csv_structure(content)

        assert metadata.delimiter == ";"
        assert metadata.headers == ["name", "value"]


class TestCSVMetadataDataclass:
    """Tests for CSVMetadata dataclass."""

    def test_metadata_creation(self):
        """Test CSVMetadata dataclass."""
        metadata = CSVMetadata(
            headers=["a", "b"],
            row_count=10,
            column_count=2,
            delimiter=",",
            encoding="utf-8",
        )
        assert metadata.headers == ["a", "b"]
        assert metadata.row_count == 10
        assert metadata.column_count == 2


class TestCSVValidationError:
    """Tests for CSVValidationError."""

    def test_error_with_field(self):
        """Test error with field attribute."""
        error = CSVValidationError("Test error", field="headers")
        assert str(error) == "Test error"
        assert error.field == "headers"

    def test_error_without_field(self):
        """Test error without field attribute."""
        error = CSVValidationError("Test error")
        assert error.field is None
