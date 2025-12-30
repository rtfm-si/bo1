"""DataFrame loader for CSV files from DO Spaces.

Loads CSV files from Spaces storage into pandas DataFrames with:
- Encoding detection (UTF-8 with latin-1 fallback)
- Row sampling for large files (>10K rows)
- Cell sanitization to prevent formula injection
"""

import io
import logging

import pandas as pd

from backend.services.csv_utils import sanitize_csv_cell
from backend.services.spaces import SpacesError, get_spaces_client

logger = logging.getLogger(__name__)

# Maximum rows to load for profiling (sample large files)
MAX_PROFILE_ROWS = 10_000


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
