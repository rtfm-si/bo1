"""Column statistics calculator for dataset profiling.

Computes per-column statistics based on inferred type:
- Common: null_count, unique_count, sample_values
- Numeric: min, max, mean, median, std, quartiles
- Categorical: top_values with counts
- Date: min_date, max_date, date_range_days
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from backend.services.type_inference import ColumnType


@dataclass
class ColumnStats:
    """Statistics for a single column."""

    null_count: int
    unique_count: int
    sample_values: list[Any]
    # Numeric stats
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    median_value: float | None = None
    std_value: float | None = None
    q25: float | None = None
    q75: float | None = None
    # Categorical stats
    top_values: list[dict[str, Any]] | None = None
    # Date stats
    min_date: str | None = None
    max_date: str | None = None
    date_range_days: int | None = None


def compute_column_stats(series: pd.Series, col_type: ColumnType) -> ColumnStats:
    """Compute statistics for a column based on its type.

    Args:
        series: Column data as pandas Series
        col_type: Inferred column type

    Returns:
        ColumnStats with computed statistics
    """
    non_null = series.dropna()

    # Common stats
    null_count = int(series.isna().sum())
    unique_count = int(non_null.nunique())
    sample_values = _get_sample_values(non_null, limit=5)

    stats = ColumnStats(
        null_count=null_count,
        unique_count=unique_count,
        sample_values=sample_values,
    )

    # Type-specific stats
    if col_type in (ColumnType.INTEGER, ColumnType.FLOAT):
        _compute_numeric_stats(series, stats)
    elif col_type == ColumnType.CURRENCY:
        _compute_currency_stats(series, stats)
    elif col_type == ColumnType.PERCENTAGE:
        _compute_percentage_stats(series, stats)
    elif col_type == ColumnType.DATE:
        _compute_date_stats(series, stats)
    elif col_type == ColumnType.CATEGORICAL:
        _compute_categorical_stats(series, stats)
    elif col_type == ColumnType.BOOLEAN:
        _compute_categorical_stats(series, stats)

    return stats


def _get_sample_values(series: pd.Series, limit: int = 5) -> list[Any]:
    """Get sample unique values from series."""
    unique = series.unique()[:limit]
    return [_safe_value(v) for v in unique]


def _safe_value(v: Any) -> Any:
    """Convert value to JSON-safe type."""
    if pd.isna(v):
        return None
    if hasattr(v, "item"):  # numpy types
        return v.item()
    if hasattr(v, "isoformat"):  # datetime
        return v.isoformat()
    return v


def _compute_numeric_stats(series: pd.Series, stats: ColumnStats) -> None:
    """Compute numeric statistics."""
    try:
        numeric = pd.to_numeric(series, errors="coerce")
        stats.min_value = float(numeric.min()) if not pd.isna(numeric.min()) else None
        stats.max_value = float(numeric.max()) if not pd.isna(numeric.max()) else None
        stats.mean_value = float(numeric.mean()) if not pd.isna(numeric.mean()) else None
        stats.median_value = float(numeric.median()) if not pd.isna(numeric.median()) else None
        stats.std_value = float(numeric.std()) if not pd.isna(numeric.std()) else None
        quantiles = numeric.quantile([0.25, 0.75])
        stats.q25 = float(quantiles[0.25]) if not pd.isna(quantiles[0.25]) else None
        stats.q75 = float(quantiles[0.75]) if not pd.isna(quantiles[0.75]) else None
    except (ValueError, TypeError):
        pass


def _compute_currency_stats(series: pd.Series, stats: ColumnStats) -> None:
    """Compute currency statistics (strip symbols, treat as numeric)."""
    import re

    def parse_currency(v: Any) -> float | None:
        if pd.isna(v):
            return None
        s = re.sub(r"[^\d.,\-]", "", str(v))
        s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None

    numeric = series.apply(parse_currency)
    _compute_numeric_stats(numeric, stats)


def _compute_percentage_stats(series: pd.Series, stats: ColumnStats) -> None:
    """Compute percentage statistics (strip %, treat as numeric)."""

    def parse_percentage(v: Any) -> float | None:
        if pd.isna(v):
            return None
        s = str(v).replace("%", "").strip()
        try:
            return float(s)
        except ValueError:
            return None

    numeric = series.apply(parse_percentage)
    _compute_numeric_stats(numeric, stats)


def _compute_date_stats(series: pd.Series, stats: ColumnStats) -> None:
    """Compute date statistics."""
    try:
        dates = pd.to_datetime(series, errors="coerce", format="mixed")
        valid_dates = dates.dropna()
        if len(valid_dates) > 0:
            min_date = valid_dates.min()
            max_date = valid_dates.max()
            stats.min_date = min_date.isoformat() if pd.notna(min_date) else None
            stats.max_date = max_date.isoformat() if pd.notna(max_date) else None
            if pd.notna(min_date) and pd.notna(max_date):
                stats.date_range_days = (max_date - min_date).days
    except (ValueError, TypeError):
        pass


def _compute_categorical_stats(series: pd.Series, stats: ColumnStats, top_n: int = 10) -> None:
    """Compute categorical statistics (value counts)."""
    counts = series.value_counts().head(top_n)
    stats.top_values = [
        {"value": _safe_value(value), "count": int(count)} for value, count in counts.items()
    ]
