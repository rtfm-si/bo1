"""DataFrame loader for CSV files from DO Spaces.

Loads CSV files from Spaces storage into pandas DataFrames with:
- Encoding detection (UTF-8 with latin-1 fallback)
- Row sampling for large files (>10K rows)
- Cell sanitization to prevent formula injection
- DuckDB backend support for large datasets (>100K rows)
"""

import io
import logging
from typing import TYPE_CHECKING

import pandas as pd

from backend.services.csv_utils import sanitize_csv_cell
from backend.services.spaces import SpacesError, get_spaces_client

if TYPE_CHECKING:
    import duckdb

logger = logging.getLogger(__name__)

# Maximum rows to load for profiling (sample large files)
MAX_PROFILE_ROWS = 10_000

# Threshold for large datasets (use DuckDB backend)
LARGE_DATASET_THRESHOLD = 100_000


class DataFrameLoadError(Exception):
    """Error loading DataFrame from Spaces."""

    pass


def load_dataframe(
    file_key: str,
    max_rows: int | None = MAX_PROFILE_ROWS,
    sanitize: bool = True,
) -> pd.DataFrame:
    """Load CSV from Spaces into DataFrame.

    Args:
        file_key: Spaces object key
        max_rows: Max rows to load (None for all)
        sanitize: If True, sanitize cell values to prevent formula injection

    Returns:
        pandas DataFrame (with sanitized string values if sanitize=True)

    Raises:
        DataFrameLoadError: If loading fails
    """
    try:
        spaces_client = get_spaces_client()
        content = spaces_client.download_file(file_key)
    except SpacesError as e:
        raise DataFrameLoadError(f"Failed to download {file_key}: {e}") from e

    # Try UTF-8 first, fallback to latin-1
    for encoding in ["utf-8", "latin-1"]:
        try:
            df = pd.read_csv(
                io.BytesIO(content),
                encoding=encoding,
                nrows=max_rows,
                low_memory=False,
            )
            logger.info(f"Loaded {file_key}: {len(df)} rows, {len(df.columns)} cols ({encoding})")

            # Sanitize string columns to prevent formula injection
            if sanitize:
                for col in df.select_dtypes(include=["object"]).columns:
                    df[col] = df[col].apply(
                        lambda x: sanitize_csv_cell(str(x)) if pd.notna(x) else x
                    )
                logger.debug(f"Sanitized string columns in {file_key}")

            return df
        except UnicodeDecodeError:
            continue
        except pd.errors.ParserError as e:
            raise DataFrameLoadError(f"CSV parse error: {e}") from e

    raise DataFrameLoadError(f"Failed to decode {file_key} with any encoding")


def get_row_count(file_key: str) -> int:
    """Get row count for a CSV file efficiently.

    Uses DuckDB for fast row counting without loading entire file into memory.

    Args:
        file_key: Spaces object key

    Returns:
        Number of rows in the CSV file

    Raises:
        DataFrameLoadError: If counting fails
    """
    from backend.services.duckdb_engine import DuckDBError
    from backend.services.duckdb_engine import get_row_count as duckdb_row_count

    try:
        return duckdb_row_count(file_key)
    except DuckDBError as e:
        raise DataFrameLoadError(f"Failed to count rows: {e}") from e


def load_to_duckdb_table(file_key: str, sanitize: bool = True) -> "duckdb.DuckDBPyConnection":
    """Load CSV from Spaces into a DuckDB in-memory table.

    For large datasets (>100K rows), this is more efficient than pandas.

    Args:
        file_key: Spaces object key
        sanitize: If True, sanitize cell values

    Returns:
        DuckDB connection with 'dataset' table

    Raises:
        DataFrameLoadError: If loading fails
    """
    from backend.services.duckdb_engine import DuckDBError, load_csv_to_duckdb

    try:
        return load_csv_to_duckdb(file_key, sanitize=sanitize)
    except DuckDBError as e:
        raise DataFrameLoadError(f"Failed to load into DuckDB: {e}") from e


def get_dataframe_or_connection(
    file_key: str,
    max_rows: int | None = MAX_PROFILE_ROWS,
    sanitize: bool = True,
    row_count: int | None = None,
) -> tuple[pd.DataFrame | None, "duckdb.DuckDBPyConnection | None", int]:
    """Get appropriate data backend based on dataset size.

    Args:
        file_key: Spaces object key
        max_rows: Max rows for DataFrame (only used for small datasets)
        sanitize: If True, sanitize cell values
        row_count: Pre-computed row count (optional)

    Returns:
        Tuple of (DataFrame or None, DuckDB connection or None, row_count)
        - For small datasets: (DataFrame, None, count)
        - For large datasets: (None, DuckDB connection, count)

    Raises:
        DataFrameLoadError: If loading fails
    """
    # Get row count if not provided
    if row_count is None:
        row_count = get_row_count(file_key)

    if row_count >= LARGE_DATASET_THRESHOLD:
        logger.info(f"Using DuckDB for {row_count} rows (>={LARGE_DATASET_THRESHOLD})")
        conn = load_to_duckdb_table(file_key, sanitize=sanitize)
        return None, conn, row_count
    else:
        logger.info(f"Using pandas for {row_count} rows (<{LARGE_DATASET_THRESHOLD})")
        df = load_dataframe(file_key, max_rows=max_rows, sanitize=sanitize)
        return df, None, row_count
