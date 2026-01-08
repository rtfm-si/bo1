"""Tests for CSV validation utilities."""

import pytest

from backend.services.csv_utils import (
    MAX_CELL_SIZE,
    CSVMetadata,
    CSVValidationError,
    count_csv_rows,
    detect_delimiter,
    detect_encoding,
    detect_injection_patterns,
    sanitize_csv_cell,
    skip_leading_empty_rows,
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


class TestSanitizeCSVCell:
    """Tests for cell sanitization."""

    def test_sanitize_cell_formula_prefix(self):
        """Test =SUM() gets escaped."""
        assert sanitize_csv_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"

    def test_sanitize_cell_hyperlink_formula(self):
        """Test HYPERLINK formula gets escaped."""
        result = sanitize_csv_cell('=HYPERLINK("http://evil.com","Click")')
        assert result.startswith("'=")

    def test_sanitize_cell_plus_prefix_formula(self):
        """Test +1+2 formula gets escaped."""
        assert sanitize_csv_cell("+1+2") == "'+1+2"

    def test_sanitize_cell_at_prefix(self):
        """Test @mention gets escaped."""
        assert sanitize_csv_cell("@mention") == "'@mention"

    def test_sanitize_cell_tab_prefix(self):
        """Test tab prefix gets escaped."""
        assert sanitize_csv_cell("\tvalue") == "'\tvalue"

    def test_sanitize_cell_cr_prefix(self):
        """Test carriage return prefix gets escaped."""
        assert sanitize_csv_cell("\rvalue") == "'\rvalue"

    def test_sanitize_cell_safe_negative_number(self):
        """Test negative number is preserved."""
        assert sanitize_csv_cell("-123.45") == "-123.45"
        assert sanitize_csv_cell("-1") == "-1"

    def test_sanitize_cell_unsafe_minus(self):
        """Test minus not followed by digit is escaped."""
        assert sanitize_csv_cell("-@SUM()") == "'-@SUM()"

    def test_sanitize_cell_safe_phone_number(self):
        """Test phone number with + is preserved."""
        assert sanitize_csv_cell("+1234567890") == "+1234567890"
        assert sanitize_csv_cell("+44 123 456 7890") == "+44 123 456 7890"

    def test_sanitize_cell_unsafe_plus(self):
        """Test plus not followed by digit is escaped."""
        assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"

    def test_sanitize_cell_null_bytes(self):
        """Test null bytes are stripped."""
        assert sanitize_csv_cell("hello\x00world") == "helloworld"

    def test_sanitize_cell_control_characters(self):
        """Test control characters are stripped."""
        # 0x01-0x08, 0x0B-0x0C, 0x0E-0x1F
        assert sanitize_csv_cell("hello\x01\x02\x03world") == "helloworld"
        assert sanitize_csv_cell("test\x0b\x0cvalue") == "testvalue"

    def test_sanitize_cell_preserves_tab_newline_cr_in_content(self):
        """Test tab/newline/CR in middle of string are kept."""
        # Note: Only the prefix is escaped; tabs inside are kept
        assert sanitize_csv_cell("hello\tworld") == "hello\tworld"
        assert sanitize_csv_cell("hello\nworld") == "hello\nworld"

    def test_sanitize_cell_length_limit(self):
        """Test cells exceeding 32KB are truncated."""
        long_value = "x" * (MAX_CELL_SIZE + 1000)
        result = sanitize_csv_cell(long_value)
        assert len(result) == MAX_CELL_SIZE

    def test_sanitize_cell_empty(self):
        """Test empty values pass through."""
        assert sanitize_csv_cell("") == ""

    def test_sanitize_cell_normal_text(self):
        """Test normal text is unchanged."""
        assert sanitize_csv_cell("Hello World") == "Hello World"
        assert sanitize_csv_cell("Product Name") == "Product Name"

    def test_sanitize_cell_unicode(self):
        """Test unicode characters pass through."""
        assert sanitize_csv_cell("Café Münch ñoño") == "Café Münch ñoño"


class TestDetectInjectionPatterns:
    """Tests for injection pattern detection."""

    def test_detect_formula_injection(self):
        """Test detection of formula cells."""
        content = b"name,value\n=SUM(A1),100\ntest,200"
        warnings = detect_injection_patterns(content)
        assert len(warnings) == 1
        assert "1 cell(s)" in warnings[0]
        assert "formula injection" in warnings[0]

    def test_detect_multiple_injection_cells(self):
        """Test detection of multiple injection cells."""
        content = b"name,value\n=SUM(A1),@mention\n+cmd,test"
        warnings = detect_injection_patterns(content)
        assert len(warnings) == 1
        assert "3 cell(s)" in warnings[0]

    def test_no_injection_in_clean_csv(self):
        """Test no warnings for clean CSV."""
        content = b"name,value,amount\nAlice,100,-50\nBob,200,+44123456"
        warnings = detect_injection_patterns(content)
        assert warnings == []

    def test_safe_negative_numbers_ignored(self):
        """Test negative numbers don't trigger warnings."""
        content = b"name,amount\nProduct,-123.45\nService,-1"
        warnings = detect_injection_patterns(content)
        assert warnings == []

    def test_safe_phone_numbers_ignored(self):
        """Test phone numbers don't trigger warnings."""
        content = b"name,phone\nAlice,+1234567890\nBob,+44 123"
        warnings = detect_injection_patterns(content)
        assert warnings == []

    def test_max_rows_limit(self):
        """Test only scans max_rows."""
        # Create CSV with injection in row 150 (beyond default 100)
        rows = ["name,value"] + ["test,normal"] * 149 + ["=EVIL,injected"]
        content = "\n".join(rows).encode()
        warnings = detect_injection_patterns(content, max_rows=100)
        # Should not detect the injection at row 151
        assert warnings == []


class TestValidateCSVStructureWithWarnings:
    """Tests for validate_csv_structure with injection warnings."""

    def test_validate_csv_structure_with_injection_warning(self):
        """Test warnings are populated for injection patterns."""
        content = b"name,value\n=SUM(A1),100\ntest,200"
        metadata = validate_csv_structure(content)
        assert metadata.warnings is not None
        assert len(metadata.warnings) == 1
        assert "formula injection" in metadata.warnings[0]

    def test_validate_csv_structure_no_warnings_for_clean(self):
        """Test no warnings for clean CSV."""
        content = b"name,value\nAlice,100\nBob,-200"
        metadata = validate_csv_structure(content)
        assert metadata.warnings is None


class TestSkipLeadingEmptyRows:
    """Tests for skip_leading_empty_rows function."""

    def test_skip_leading_empty_rows_basic(self):
        """Test skipping 3 empty rows before header."""
        text = "\n\n\nname,value\nrow1,1\nrow2,2"
        cleaned, skipped = skip_leading_empty_rows(text)
        assert skipped == 3
        assert cleaned == "name,value\nrow1,1\nrow2,2"

    def test_skip_leading_empty_rows_whitespace(self):
        """Test skipping whitespace-only rows (tabs/spaces)."""
        text = "   \n\t\n  \t  \nname,value\nrow1,1"
        cleaned, skipped = skip_leading_empty_rows(text)
        assert skipped == 3
        assert cleaned == "name,value\nrow1,1"

    def test_skip_leading_empty_rows_mixed(self):
        """Test skipping mixed empty and whitespace rows."""
        text = "\n   \n\t\n\nname,value\nrow1,1"
        cleaned, skipped = skip_leading_empty_rows(text)
        assert skipped == 4
        assert cleaned == "name,value\nrow1,1"

    def test_skip_leading_empty_rows_none(self):
        """Test no skipping when header is first row."""
        text = "name,value\nrow1,1\nrow2,2"
        cleaned, skipped = skip_leading_empty_rows(text)
        assert skipped == 0
        assert cleaned == text

    def test_skip_leading_empty_rows_preserves_middle_empty(self):
        """Test empty rows in middle of data are preserved."""
        text = "\nname,value\n\nrow1,1\n\nrow2,2"
        cleaned, skipped = skip_leading_empty_rows(text)
        assert skipped == 1
        assert cleaned == "name,value\n\nrow1,1\n\nrow2,2"

    def test_skip_leading_empty_rows_all_empty(self):
        """Test file that's entirely empty rows."""
        text = "\n\n   \n\t"
        cleaned, skipped = skip_leading_empty_rows(text)
        assert skipped == 4
        assert cleaned == ""


class TestValidateCSVHeadersWithEmptyRows:
    """Tests for validate_csv_headers with leading empty rows."""

    def test_validate_csv_headers_with_leading_empty(self):
        """Test headers detected correctly after empty rows."""
        content = b"\n\n\nname,age,city\nalice,30,nyc\nbob,25,la"
        metadata = validate_csv_headers(content)
        assert metadata.headers == ["name", "age", "city"]
        assert metadata.row_count == 2
        assert metadata.column_count == 3

    def test_validate_csv_headers_with_whitespace_rows(self):
        """Test headers detected after whitespace-only rows."""
        content = b"   \n\t\nname,value\nrow1,1"
        metadata = validate_csv_headers(content)
        assert metadata.headers == ["name", "value"]
        assert metadata.row_count == 1

    def test_validate_csv_headers_all_empty_raises_error(self):
        """Test file with only empty rows raises error."""
        content = b"\n\n   \n\t\n"
        with pytest.raises(CSVValidationError) as exc:
            validate_csv_headers(content)
        assert "No headers found" in str(exc.value)


class TestValidateCSVStructureWithEmptyRows:
    """Tests for validate_csv_structure with leading empty rows."""

    def test_validate_csv_structure_with_leading_empty(self):
        """Test full validation works after empty rows."""
        content = b"\n\nname,value\nrow1,1\nrow2,2"
        metadata = validate_csv_structure(content)
        assert metadata.headers == ["name", "value"]
        assert metadata.row_count == 2
        assert metadata.column_count == 2

    def test_validate_csv_structure_with_empty_rows_and_injection(self):
        """Test injection detection works after skipping empty rows."""
        content = b"\n\nname,value\n=SUM(A1),100"
        metadata = validate_csv_structure(content)
        assert metadata.headers == ["name", "value"]
        assert metadata.warnings is not None
        assert "formula injection" in metadata.warnings[0]


class TestDetectInjectionWithEmptyRows:
    """Tests for detect_injection_patterns with leading empty rows."""

    def test_detect_injection_after_empty_rows(self):
        """Test injection detection works after empty rows."""
        content = b"\n\nname,value\n=SUM(A1),100"
        warnings = detect_injection_patterns(content)
        assert len(warnings) == 1
        assert "1 cell(s)" in warnings[0]
