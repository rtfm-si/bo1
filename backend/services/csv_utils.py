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
        CSVMetadata with full validation

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

    return metadata
