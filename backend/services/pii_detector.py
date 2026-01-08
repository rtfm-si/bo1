"""PII (Personally Identifiable Information) detection service.

Scans dataset columns to detect potential PII such as:
- Email addresses
- Social Security Numbers (SSN)
- Phone numbers
- Credit card numbers
- IP addresses
- Names (first/last)
- Physical addresses
- Dates of birth

Returns warnings for user confirmation before final upload.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

import pandas as pd

logger = logging.getLogger(__name__)

# Maximum rows to sample for PII detection (performance optimization)
PII_SAMPLE_SIZE = 1000


class PiiType(str, Enum):
    """Types of PII that can be detected."""

    EMAIL = "email"
    SSN = "ssn"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class PiiWarning:
    """Warning about potential PII detected in a column."""

    column_name: str
    pii_type: PiiType
    confidence: float  # 0.0 - 1.0
    sample_values: list[str]  # Up to 3 sample matches (masked)
    match_count: int  # Number of matches found in sample


# PII detection patterns
PII_PATTERNS = {
    PiiType.EMAIL: re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        re.IGNORECASE,
    ),
    PiiType.SSN: re.compile(
        r"^\d{3}-\d{2}-\d{4}$|^\d{9}$",
    ),
    PiiType.PHONE: re.compile(
        # US phone formats: (123) 456-7890, 123-456-7890, 1234567890, +1-123-456-7890
        r"^(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}$",
    ),
    PiiType.CREDIT_CARD: re.compile(
        # 13-19 digits, optionally with spaces/dashes
        r"^(?:\d{4}[-\s]?){3,4}\d{1,4}$",
    ),
    PiiType.IP_ADDRESS: re.compile(
        r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$",
    ),
    PiiType.DATE_OF_BIRTH: re.compile(
        # Common date formats that could be DOB
        r"^(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})$",
    ),
}

# Column name patterns that suggest PII (increases confidence)
PII_COLUMN_HINTS = {
    PiiType.EMAIL: re.compile(r"(?:e[-_]?mail|email_?addr)", re.IGNORECASE),
    PiiType.SSN: re.compile(r"(?:ssn|social|tax_?id|sin)", re.IGNORECASE),
    PiiType.PHONE: re.compile(r"(?:phone|mobile|cell|tel|fax)", re.IGNORECASE),
    PiiType.CREDIT_CARD: re.compile(r"(?:card|cc|credit|payment)", re.IGNORECASE),
    PiiType.IP_ADDRESS: re.compile(r"(?:ip|ip_?addr|client_?ip)", re.IGNORECASE),
    PiiType.NAME: re.compile(
        r"(?:^name$|first_?name|last_?name|full_?name|customer_?name|user_?name$)",
        re.IGNORECASE,
    ),
    PiiType.ADDRESS: re.compile(
        r"(?:address|street|city|zip|postal|state|country)",
        re.IGNORECASE,
    ),
    PiiType.DATE_OF_BIRTH: re.compile(r"(?:dob|birth|birthday|born)", re.IGNORECASE),
}

# Minimum match ratio for pattern detection (reduces false positives)
MIN_MATCH_RATIO = 0.1  # At least 10% of non-null values must match
MIN_MATCHES = 3  # Need at least 3 matches regardless of ratio


def _mask_value(value: str, pii_type: PiiType) -> str:
    """Mask a PII value for display, showing pattern but not full data."""
    if not value:
        return ""

    if pii_type == PiiType.EMAIL:
        # Show first char + domain: j***@example.com
        if "@" in value:
            local, domain = value.split("@", 1)
            return f"{local[0]}***@{domain}" if local else f"***@{domain}"

    elif pii_type == PiiType.SSN:
        # Show last 4: ***-**-1234
        digits = re.sub(r"[^\d]", "", value)
        if len(digits) >= 4:
            return f"***-**-{digits[-4:]}"

    elif pii_type == PiiType.PHONE:
        # Show last 4: (***) ***-1234
        digits = re.sub(r"[^\d]", "", value)
        if len(digits) >= 4:
            return f"(***) ***-{digits[-4:]}"

    elif pii_type == PiiType.CREDIT_CARD:
        # Show last 4: ****-****-****-1234
        digits = re.sub(r"[^\d]", "", value)
        if len(digits) >= 4:
            return f"****-****-****-{digits[-4:]}"

    elif pii_type == PiiType.IP_ADDRESS:
        # Show first octet: 192.***.***.**
        parts = value.split(".")
        if parts:
            return f"{parts[0]}.***.***.**"

    # Default: show first 2 chars + asterisks
    if len(value) > 2:
        return f"{value[:2]}{'*' * min(len(value) - 2, 10)}"
    return "*" * len(value)


def _detect_names(column: pd.Series) -> tuple[int, list[str]]:
    """Detect potential name columns using heuristics.

    Names are tricky - we look for:
    - Mostly alphabetic with spaces (full names)
    - Title case or mixed case
    - Reasonable length (2-50 chars)
    - High uniqueness (names are usually unique)
    """
    matches = []
    match_count = 0

    # Sample non-null values
    sample = column.dropna().head(PII_SAMPLE_SIZE)
    if len(sample) == 0:
        return 0, []

    for val in sample:
        str_val = str(val).strip()
        if not str_val:
            continue

        # Check name-like characteristics
        is_name_like = (
            2 <= len(str_val) <= 50
            and bool(re.match(r"^[A-Za-z][a-zA-Z\s\'-]+$", str_val))
            and str_val != str_val.upper()  # Not all uppercase (likely code)
            and " " not in str_val
            or (  # Single word OR
                " " in str_val and len(str_val.split()) <= 4
            )  # Multi-word, max 4 parts
        )

        if is_name_like:
            match_count += 1
            if len(matches) < 3:
                # Mask: show first letter of each word
                masked = " ".join(
                    f"{word[0]}***" if len(word) > 1 else word for word in str_val.split()
                )
                matches.append(masked)

    return match_count, matches


def _detect_addresses(column: pd.Series) -> tuple[int, list[str]]:
    """Detect potential address columns using heuristics.

    Addresses typically contain:
    - Numbers followed by street names
    - Common street suffixes (St, Ave, Rd, etc.)
    - City, state, zip patterns
    """
    street_pattern = re.compile(
        r"\d+\s+[A-Za-z]+(?:\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Ct|Court|Pl|Place))?",
        re.IGNORECASE,
    )
    zip_pattern = re.compile(r"\b\d{5}(?:-\d{4})?\b")

    matches = []
    match_count = 0

    sample = column.dropna().head(PII_SAMPLE_SIZE)
    for val in sample:
        str_val = str(val).strip()
        if not str_val:
            continue

        has_street = bool(street_pattern.search(str_val))
        has_zip = bool(zip_pattern.search(str_val))

        if has_street or has_zip:
            match_count += 1
            if len(matches) < 3:
                # Mask: show first word + asterisks
                words = str_val.split()
                if words:
                    masked = f"{words[0]} ***" + (" ***" if len(words) > 2 else "")
                    matches.append(masked[:30])

    return match_count, matches


def detect_pii_columns(df: pd.DataFrame) -> list[PiiWarning]:
    """Detect potential PII in dataframe columns.

    Args:
        df: DataFrame to scan

    Returns:
        List of PII warnings for columns with detected PII
    """
    warnings: list[PiiWarning] = []

    # Sample rows for performance
    if len(df) > PII_SAMPLE_SIZE:
        sample_df = df.head(PII_SAMPLE_SIZE)
    else:
        sample_df = df

    for col_name in df.columns:
        column = sample_df[col_name]

        # Skip numeric-only columns (unlikely PII in raw form)
        if pd.api.types.is_numeric_dtype(column) and not column.dtype == object:
            continue

        # Get non-null string values
        non_null = column.dropna()
        if len(non_null) == 0:
            continue

        total_values = len(non_null)

        # Check each PII pattern
        for pii_type, pattern in PII_PATTERNS.items():
            match_count = 0
            sample_matches: list[str] = []

            for val in non_null:
                str_val = str(val).strip()
                if not str_val:
                    continue

                if pattern.match(str_val):
                    match_count += 1
                    if len(sample_matches) < 3:
                        sample_matches.append(_mask_value(str_val, pii_type))

            # Check if enough matches to be suspicious
            if match_count >= MIN_MATCHES and match_count / total_values >= MIN_MATCH_RATIO:
                # Calculate confidence
                match_ratio = match_count / total_values
                base_confidence = min(match_ratio * 1.2, 0.9)  # Cap at 0.9

                # Boost confidence if column name hints at PII
                hint_pattern = PII_COLUMN_HINTS.get(pii_type)
                if hint_pattern and hint_pattern.search(col_name):
                    base_confidence = min(base_confidence + 0.2, 0.95)

                warnings.append(
                    PiiWarning(
                        column_name=col_name,
                        pii_type=pii_type,
                        confidence=round(base_confidence, 2),
                        sample_values=sample_matches,
                        match_count=match_count,
                    )
                )

        # Check for names (heuristic-based)
        hint_pattern = PII_COLUMN_HINTS.get(PiiType.NAME)
        if hint_pattern and hint_pattern.search(col_name):
            match_count, sample_matches = _detect_names(non_null)
            if match_count >= MIN_MATCHES and match_count / total_values >= MIN_MATCH_RATIO:
                warnings.append(
                    PiiWarning(
                        column_name=col_name,
                        pii_type=PiiType.NAME,
                        confidence=round(min(match_count / total_values + 0.3, 0.85), 2),
                        sample_values=sample_matches,
                        match_count=match_count,
                    )
                )

        # Check for addresses (heuristic-based)
        hint_pattern = PII_COLUMN_HINTS.get(PiiType.ADDRESS)
        if hint_pattern and hint_pattern.search(col_name):
            match_count, sample_matches = _detect_addresses(non_null)
            if match_count >= MIN_MATCHES and match_count / total_values >= MIN_MATCH_RATIO:
                warnings.append(
                    PiiWarning(
                        column_name=col_name,
                        pii_type=PiiType.ADDRESS,
                        confidence=round(min(match_count / total_values + 0.2, 0.8), 2),
                        sample_values=sample_matches,
                        match_count=match_count,
                    )
                )

    # Sort by confidence descending
    warnings.sort(key=lambda w: w.confidence, reverse=True)

    logger.info(f"PII detection found {len(warnings)} potential PII columns")
    return warnings


def detect_pii_in_csv(content: bytes) -> list[PiiWarning]:
    """Convenience function to detect PII in CSV content.

    Args:
        content: CSV file content as bytes

    Returns:
        List of PII warnings
    """
    import io

    try:
        df = pd.read_csv(io.BytesIO(content), nrows=PII_SAMPLE_SIZE)
        return detect_pii_columns(df)
    except Exception as e:
        logger.warning(f"Failed to detect PII in CSV: {e}")
        return []
