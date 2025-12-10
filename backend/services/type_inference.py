"""Column type inference for dataset profiling.

Detects column types: date, currency, percentage, integer, float, boolean, categorical, text.
"""

import re
from enum import Enum

import pandas as pd

# Patterns for type detection
CURRENCY_PATTERN = re.compile(r"^[\$\u00a3\u20ac\u00a5]\s*[\d,]+\.?\d*$")  # $, £, €, ¥
PERCENTAGE_PATTERN = re.compile(r"^[\d.]+\s*%$")
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
]


class ColumnType(str, Enum):
    """Inferred column data types."""

    DATE = "date"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    TEXT = "text"


def _is_boolean(series: pd.Series) -> bool:
    """Check if series contains boolean-like values."""
    unique = series.dropna().unique()
    if len(unique) > 3:
        return False
    bool_values = {"true", "false", "yes", "no", "1", "0", "y", "n", "t", "f"}
    return all(str(v).lower().strip() in bool_values for v in unique)


def _is_date(series: pd.Series) -> bool:
    """Check if series contains date values."""
    sample = series.dropna().head(100)
    if len(sample) == 0:
        return False

    # Try pandas date parsing
    try:
        pd.to_datetime(sample, format="mixed", dayfirst=False)
        return True
    except (ValueError, TypeError):
        pass

    # Try specific formats
    for fmt in DATE_FORMATS:
        try:
            pd.to_datetime(sample, format=fmt)
            return True
        except (ValueError, TypeError):
            continue

    return False


def _is_currency(series: pd.Series) -> bool:
    """Check if series contains currency values."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    match_count = sum(1 for v in sample if CURRENCY_PATTERN.match(v.strip()))
    return match_count / len(sample) > 0.8


def _is_percentage(series: pd.Series) -> bool:
    """Check if series contains percentage values."""
    sample = series.dropna().astype(str).head(100)
    if len(sample) == 0:
        return False
    match_count = sum(1 for v in sample if PERCENTAGE_PATTERN.match(v.strip()))
    return match_count / len(sample) > 0.8


def infer_column_type(series: pd.Series) -> ColumnType:
    """Infer the data type of a pandas Series.

    Args:
        series: Column data as pandas Series

    Returns:
        ColumnType enum value
    """
    # Handle empty or all-null columns
    non_null = series.dropna()
    if len(non_null) == 0:
        return ColumnType.TEXT

    # Check pandas dtype first
    dtype = series.dtype

    # Already numeric
    if pd.api.types.is_integer_dtype(dtype):
        return ColumnType.INTEGER
    if pd.api.types.is_float_dtype(dtype):
        return ColumnType.FLOAT
    if pd.api.types.is_bool_dtype(dtype):
        return ColumnType.BOOLEAN
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return ColumnType.DATE

    # String-based detection (object dtype)
    if pd.api.types.is_object_dtype(dtype):
        # Check specific patterns
        if _is_boolean(series):
            return ColumnType.BOOLEAN
        if _is_currency(series):
            return ColumnType.CURRENCY
        if _is_percentage(series):
            return ColumnType.PERCENTAGE
        if _is_date(series):
            return ColumnType.DATE

        # Try numeric conversion
        try:
            numeric = pd.to_numeric(non_null, errors="raise")
            if (numeric == numeric.astype(int)).all():
                return ColumnType.INTEGER
            return ColumnType.FLOAT
        except (ValueError, TypeError):
            pass

        # Categorical vs text heuristic
        unique_ratio = len(non_null.unique()) / len(non_null)
        if unique_ratio < 0.5 and len(non_null.unique()) <= 50:
            return ColumnType.CATEGORICAL

    return ColumnType.TEXT
