"""CSV validation and parsing utilities.

Provides validation and metadata extraction for CSV uploads.
"""

import csv
import io
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CSVValidationError(Exception):
    """Error during CSV validation."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize CSVValidationError."""
        self.field = field
        super().__init__(message)


@dataclass
class CSVMetadata:
    """Metadata extracted from CSV content."""

    headers: list[str]
    row_count: int
    column_count: int
    delimiter: str
    encoding: str
    warnings: list[str] | None = None


# CSV injection prefixes (Excel formula triggers)
_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# Pattern for safe minus: negative number like -123 or -12.5 (only digits/dots after minus)
_SAFE_MINUS_PATTERN = r"^-[\d.]+$"
# Pattern for safe plus: phone number like +1234567890 (only digits/spaces after plus)
_SAFE_PLUS_PATTERN = r"^\+[\d\s]+$"
# Max cell size (Excel limit is 32KB)
MAX_CELL_SIZE = 32 * 1024


def sanitize_csv_cell(value: str) -> str:
    """Sanitize a CSV cell value to prevent formula injection.

    Escapes dangerous prefixes (=, +, @, tab, CR) with a leading single quote,
    strips control characters, and truncates cells exceeding 32KB.

    Args:
        value: Raw cell value

    Returns:
        Sanitized cell value
    """
    import re

    if not value:
        return value

    # Strip null bytes and control characters (0x00-0x08, 0x0B-0x0C, 0x0E-0x1F)
    # Keep tab (0x09), newline (0x0A), carriage return (0x0D)
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)

    # Truncate cells exceeding max size
    if len(value) > MAX_CELL_SIZE:
        value = value[:MAX_CELL_SIZE]
        logger.warning(f"Truncated cell value exceeding {MAX_CELL_SIZE} bytes")

    # Check for injection prefixes
    if value.startswith(_INJECTION_PREFIXES):
        # Allow safe minus (negative numbers like -123)
        if value.startswith("-") and re.match(_SAFE_MINUS_PATTERN, value):
            return value
        # Allow safe plus (phone numbers like +1234567890)
        if value.startswith("+") and re.match(_SAFE_PLUS_PATTERN, value):
            return value
        # Escape with leading single quote
        return f"'{value}"

    return value


def detect_injection_patterns(content: bytes, max_rows: int = 100) -> list[str]:
    """Detect potential formula injection patterns in CSV content.

    Scans first N rows for cells starting with injection prefixes.
    Returns warnings (not errors) for security monitoring.

    Args:
        content: Raw CSV bytes
        max_rows: Max rows to scan (default 100 for performance)

    Returns:
        List of warning messages
    """
    import re

    warnings_list: list[str] = []
    encoding = detect_encoding(content)

    try:
        text = content.decode(encoding)
    except UnicodeDecodeError:
        return warnings_list

    lines = text.strip().split("\n")
    if len(lines) < 2:
        return warnings_list

    # Detect delimiter
    sample = "\n".join(lines[:5])
    delimiter = detect_delimiter(sample)

    # Skip header, scan data rows
    reader = csv.reader(io.StringIO("\n".join(lines[1:])), delimiter=delimiter)

    injection_cells = 0
    for row_idx, row in enumerate(reader):
        if row_idx >= max_rows:
            break
        for _col_idx, cell in enumerate(row):
            if not cell:
                continue
            # Check for injection prefixes (excluding safe patterns)
            if cell.startswith(_INJECTION_PREFIXES):
                # Skip safe negative numbers
                if cell.startswith("-") and re.match(_SAFE_MINUS_PATTERN, cell):
                    continue
                # Skip safe phone numbers
                if cell.startswith("+") and re.match(_SAFE_PLUS_PATTERN, cell):
                    continue
                injection_cells += 1

    if injection_cells > 0:
        warnings_list.append(
            f"Detected {injection_cells} cell(s) with formula injection prefixes "
            f"(=, +, @, tab, CR). Values will be sanitized when queried."
        )
        logger.info(
            f"CSV injection detection: {injection_cells} cells with "
            f"injection prefixes in first {min(max_rows, len(lines) - 1)} rows"
        )

    return warnings_list


def detect_encoding(content: bytes) -> str:
    """Detect encoding of CSV content.

    Args:
        content: Raw bytes content

    Returns:
        Encoding string (utf-8 or latin-1)
    """
    try:
        content.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        try:
            content.decode("latin-1")
            return "latin-1"
        except UnicodeDecodeError:
            return "utf-8"  # Default fallback


def detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter from sample content.

    Args:
        sample: First few lines of CSV as string

    Returns:
        Detected delimiter character
    """
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        # Default to comma if detection fails
        return ","


def validate_csv_headers(content: bytes) -> CSVMetadata:
    """Validate CSV content and extract headers.

    Args:
        content: Raw CSV bytes

    Returns:
        CSVMetadata with headers and metadata

    Raises:
        CSVValidationError: If CSV is invalid
    """
    if not content or len(content) == 0:
        raise CSVValidationError("Empty file", field="file")

    # Detect encoding
    encoding = detect_encoding(content)

    try:
        text = content.decode(encoding)
    except UnicodeDecodeError as e:
        raise CSVValidationError(f"Invalid encoding: {e}", field="file") from e

    # Need at least one line
    lines = text.strip().split("\n")
    if not lines:
        raise CSVValidationError("No data rows found", field="file")

    # Detect delimiter from first few lines
    sample = "\n".join(lines[:5])
    delimiter = detect_delimiter(sample)

    # Parse headers
    reader = csv.reader(io.StringIO(lines[0]), delimiter=delimiter)
    try:
        headers = next(reader)
    except StopIteration:
        raise CSVValidationError("No headers found", field="file") from None

    # Validate headers
    if not headers:
        raise CSVValidationError("No headers found", field="file")

    # Check for empty headers
    headers = [h.strip() for h in headers]
    if any(not h for h in headers):
        raise CSVValidationError("Empty column header detected", field="headers")

    # Check for duplicate headers
    if len(headers) != len(set(headers)):
        raise CSVValidationError("Duplicate column headers detected", field="headers")

    # Count rows (excluding header)
    row_count = len(lines) - 1

    return CSVMetadata(
        headers=headers,
        row_count=row_count,
        column_count=len(headers),
        delimiter=delimiter,
        encoding=encoding,
    )


def count_csv_rows(content: bytes) -> int:
    """Quick row count without full CSV parse.

    Args:
        content: Raw CSV bytes

    Returns:
        Number of data rows (excluding header)
    """
    encoding = detect_encoding(content)
    text = content.decode(encoding)
    lines = text.strip().split("\n")
    # Subtract 1 for header row
    return max(0, len(lines) - 1)


def validate_csv_structure(content: bytes, max_columns: int = 100) -> CSVMetadata:
    """Full CSV structure validation.

    Args:
        content: Raw CSV bytes
        max_columns: Maximum allowed columns

    Returns:
        CSVMetadata with full validation (includes injection warnings)

    Raises:
        CSVValidationError: If CSV structure is invalid
    """
    metadata = validate_csv_headers(content)

    if metadata.column_count > max_columns:
        raise CSVValidationError(
            f"Too many columns ({metadata.column_count}). Maximum is {max_columns}",
            field="columns",
        )

    # Validate a sample of rows have correct column count
    encoding = metadata.encoding
    text = content.decode(encoding)
    reader = csv.reader(io.StringIO(text), delimiter=metadata.delimiter)

    # Skip header
    next(reader, None)

    # Check first 100 rows for consistency
    for i, row in enumerate(reader):
        if i >= 100:
            break
        if len(row) != metadata.column_count:
            raise CSVValidationError(
                f"Row {i + 2} has {len(row)} columns, expected {metadata.column_count}",
                field="structure",
            )

    # Detect injection patterns and add warnings
    warnings_list = detect_injection_patterns(content)
    if warnings_list:
        metadata.warnings = warnings_list

    return metadata
