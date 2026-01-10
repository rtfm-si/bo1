"""Data cleaning utilities for dataset quality actions.

Provides transformations to fix common data quality issues:
- Duplicate row removal
- Null value handling (fill or drop)
- Whitespace trimming

Each function returns a tuple of (cleaned_df, stats_dict) for tracking changes.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class CleaningError(Exception):
    """Error during data cleaning operation."""

    pass


def remove_duplicates(
    df: pd.DataFrame,
    keep: str = "first",
    subset: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove duplicate rows from DataFrame.

    Args:
        df: Input DataFrame
        keep: Which duplicate to keep: 'first', 'last', or False (drop all)
        subset: Column names to consider for identifying duplicates (None = all)

    Returns:
        Tuple of (cleaned DataFrame, stats dict with rows_removed and new_count)

    Raises:
        CleaningError: If operation fails
    """
    try:
        original_count = len(df)

        # Validate keep parameter
        if keep not in ("first", "last", False):
            keep = "first"

        # Validate subset columns exist
        if subset:
            missing = [c for c in subset if c not in df.columns]
            if missing:
                raise CleaningError(f"Columns not found: {', '.join(missing)}")

        df_clean = df.drop_duplicates(keep=keep, subset=subset)
        removed = original_count - len(df_clean)

        logger.info(f"Removed {removed} duplicate rows ({removed / original_count * 100:.1f}%)")

        return df_clean, {
            "rows_removed": removed,
            "new_count": len(df_clean),
            "original_count": original_count,
        }
    except CleaningError:
        raise
    except Exception as e:
        raise CleaningError(f"Failed to remove duplicates: {e}") from e


def fill_nulls(
    df: pd.DataFrame,
    column: str,
    strategy: str = "mean",
    fill_value: str | int | float | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fill null values in a column using specified strategy.

    Args:
        df: Input DataFrame
        column: Column name to fill nulls in
        strategy: Fill strategy - 'mean', 'median', 'mode', 'zero', 'value', 'forward', 'backward'
        fill_value: Custom value when strategy='value'

    Returns:
        Tuple of (cleaned DataFrame, stats dict with nulls_filled)

    Raises:
        CleaningError: If column not found or operation fails
    """
    try:
        if column not in df.columns:
            raise CleaningError(f"Column '{column}' not found")

        null_count = int(df[column].isna().sum())
        if null_count == 0:
            return df.copy(), {"nulls_filled": 0, "column": column, "strategy": strategy}

        df_clean = df.copy()

        if strategy == "mean":
            if not pd.api.types.is_numeric_dtype(df[column]):
                raise CleaningError(f"Cannot use 'mean' on non-numeric column '{column}'")
            df_clean[column] = df_clean[column].fillna(df_clean[column].mean())

        elif strategy == "median":
            if not pd.api.types.is_numeric_dtype(df[column]):
                raise CleaningError(f"Cannot use 'median' on non-numeric column '{column}'")
            df_clean[column] = df_clean[column].fillna(df_clean[column].median())

        elif strategy == "mode":
            mode_val = df_clean[column].mode()
            if len(mode_val) > 0:
                df_clean[column] = df_clean[column].fillna(mode_val.iloc[0])

        elif strategy == "zero":
            df_clean[column] = df_clean[column].fillna(0)

        elif strategy == "value":
            if fill_value is None:
                raise CleaningError("fill_value required when strategy='value'")
            df_clean[column] = df_clean[column].fillna(fill_value)

        elif strategy == "forward":
            df_clean[column] = df_clean[column].ffill()

        elif strategy == "backward":
            df_clean[column] = df_clean[column].bfill()

        else:
            raise CleaningError(f"Unknown strategy: {strategy}")

        actual_filled = null_count - int(df_clean[column].isna().sum())
        logger.info(f"Filled {actual_filled} nulls in '{column}' using {strategy}")

        return df_clean, {
            "nulls_filled": actual_filled,
            "column": column,
            "strategy": strategy,
        }
    except CleaningError:
        raise
    except Exception as e:
        raise CleaningError(f"Failed to fill nulls: {e}") from e


def remove_null_rows(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    how: str = "any",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Remove rows containing null values.

    Args:
        df: Input DataFrame
        columns: Columns to check for nulls (None = all columns)
        how: 'any' removes rows with any null, 'all' removes rows where all specified are null

    Returns:
        Tuple of (cleaned DataFrame, stats dict with rows_removed and new_count)

    Raises:
        CleaningError: If operation fails
    """
    try:
        original_count = len(df)

        # Validate columns exist
        if columns:
            missing = [c for c in columns if c not in df.columns]
            if missing:
                raise CleaningError(f"Columns not found: {', '.join(missing)}")

        if how not in ("any", "all"):
            how = "any"

        df_clean = df.dropna(subset=columns, how=how)
        removed = original_count - len(df_clean)

        logger.info(f"Removed {removed} rows with null values")

        return df_clean, {
            "rows_removed": removed,
            "new_count": len(df_clean),
            "original_count": original_count,
            "columns_checked": columns or list(df.columns),
        }
    except CleaningError:
        raise
    except Exception as e:
        raise CleaningError(f"Failed to remove null rows: {e}") from e


def trim_whitespace(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Trim leading/trailing whitespace from all string columns.

    Args:
        df: Input DataFrame

    Returns:
        Tuple of (cleaned DataFrame, stats dict with cells_trimmed and columns_affected)

    Raises:
        CleaningError: If operation fails
    """
    try:
        df_clean = df.copy()
        string_cols = df_clean.select_dtypes(include=["object"]).columns.tolist()

        if not string_cols:
            return df_clean, {"cells_trimmed": 0, "columns_affected": []}

        cells_trimmed = 0
        columns_affected = []

        for col in string_cols:
            # Get non-null string values
            mask = df_clean[col].notna()
            if not mask.any():
                continue

            # Convert to string and strip
            original = df_clean.loc[mask, col].astype(str)
            stripped = original.str.strip()

            # Count changes
            changed = (original != stripped).sum()
            if changed > 0:
                cells_trimmed += changed
                columns_affected.append(col)
                df_clean.loc[mask, col] = stripped

        logger.info(
            f"Trimmed whitespace in {cells_trimmed} cells across {len(columns_affected)} columns"
        )

        return df_clean, {
            "cells_trimmed": int(cells_trimmed),
            "columns_affected": columns_affected,
        }
    except Exception as e:
        raise CleaningError(f"Failed to trim whitespace: {e}") from e
