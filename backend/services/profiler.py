"""Dataset profiler service using ydata-profiling.

Generates comprehensive dataset profiles using ydata-profiling,
extracting key statistics into a structured format for storage and analysis.

For large datasets (>100K rows), uses DuckDB SQL for basic statistics
instead of ydata-profiling for better performance.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pandas as pd
from ydata_profiling import ProfileReport

from backend.services.dataframe_loader import (
    LARGE_DATASET_THRESHOLD,
    DataFrameLoadError,
    get_dataframe_or_connection,
)
from backend.services.type_inference import ColumnType
from bo1.state.repositories.dataset_repository import DatasetRepository

if TYPE_CHECKING:
    import duckdb

logger = logging.getLogger(__name__)


class ProfileError(Exception):
    """Error during dataset profiling."""

    pass


# Map ydata-profiling types to our ColumnType enum
YDATA_TYPE_MAP = {
    "Numeric": ColumnType.FLOAT,
    "Categorical": ColumnType.CATEGORICAL,
    "Boolean": ColumnType.BOOLEAN,
    "DateTime": ColumnType.DATE,
    "Text": ColumnType.TEXT,
    "Unsupported": ColumnType.TEXT,
}


@dataclass
class ColumnStats:
    """Statistics for a single column extracted from ydata-profiling."""

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


@dataclass
class ColumnProfile:
    """Profile for a single column."""

    name: str
    inferred_type: ColumnType
    stats: ColumnStats

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        stats_dict = asdict(self.stats)
        return {
            "name": self.name,
            "inferred_type": self.inferred_type.value,
            "stats": stats_dict,
        }


@dataclass
class DatasetSummary:
    """High-level summary from ydata-profiling."""

    row_count: int
    column_count: int
    memory_size_bytes: int
    duplicate_rows: int
    duplicate_row_percent: float
    missing_cells: int
    missing_cells_percent: float
    # Correlation matrix (column_a -> column_b -> correlation)
    correlations: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class DatasetProfile:
    """Complete profile for a dataset."""

    dataset_id: str
    row_count: int
    column_count: int
    columns: list[ColumnProfile]
    summary: DatasetSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "dataset_id": self.dataset_id,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [c.to_dict() for c in self.columns],
        }
        if self.summary:
            result["summary"] = asdict(self.summary)
        return result


def _extract_column_profile(col_name: str, col_data: dict[str, Any]) -> ColumnProfile:
    """Extract column profile from ydata-profiling column analysis."""
    # Map type
    ydata_type = col_data.get("type", "Unsupported")
    col_type = YDATA_TYPE_MAP.get(ydata_type, ColumnType.TEXT)

    # Extract common stats
    null_count = int(col_data.get("n_missing", 0))
    unique_count = int(col_data.get("n_distinct", 0))

    # Get sample values from value_counts or histogram
    sample_values = []
    if "value_counts_without_nan" in col_data:
        vc = col_data["value_counts_without_nan"]
        if isinstance(vc, dict):
            sample_values = list(vc.keys())[:5]

    stats = ColumnStats(
        null_count=null_count,
        unique_count=unique_count,
        sample_values=sample_values,
    )

    # Numeric stats
    if ydata_type == "Numeric":
        stats.min_value = _safe_float(col_data.get("min"))
        stats.max_value = _safe_float(col_data.get("max"))
        stats.mean_value = _safe_float(col_data.get("mean"))
        stats.median_value = _safe_float(col_data.get("median"))
        stats.std_value = _safe_float(col_data.get("std"))
        stats.q25 = _safe_float(col_data.get("25%"))
        stats.q75 = _safe_float(col_data.get("75%"))
        col_type = _refine_numeric_type(col_data, col_type)

    # Categorical stats
    elif ydata_type in ("Categorical", "Boolean"):
        if "value_counts_without_nan" in col_data:
            vc = col_data["value_counts_without_nan"]
            if isinstance(vc, dict):
                stats.top_values = [{"value": k, "count": int(v)} for k, v in list(vc.items())[:10]]

    # DateTime stats
    elif ydata_type == "DateTime":
        stats.min_date = str(col_data.get("min")) if col_data.get("min") else None
        stats.max_date = str(col_data.get("max")) if col_data.get("max") else None
        if col_data.get("range"):
            # Range is typically in days
            try:
                stats.date_range_days = int(col_data["range"].days)
            except (AttributeError, TypeError):
                pass

    return ColumnProfile(name=col_name, inferred_type=col_type, stats=stats)


def _safe_float(value: Any) -> float | None:
    """Safely convert value to float."""
    if value is None:
        return None
    try:
        f = float(value)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _refine_numeric_type(col_data: dict[str, Any], default: ColumnType) -> ColumnType:
    """Refine numeric type to INTEGER if all values are whole numbers."""
    # Check if p_integer (percentage of integer values) is 1.0
    if col_data.get("p_infinite", 0) == 0:
        # Check if values appear to be integers
        n_distinct = col_data.get("n_distinct", 0)
        if n_distinct > 0 and col_data.get("is_unique", False) is False:
            # Heuristic: if min/max are both whole numbers and no decimals in samples
            min_val = col_data.get("min")
            max_val = col_data.get("max")
            if min_val is not None and max_val is not None:
                try:
                    if float(min_val) == int(min_val) and float(max_val) == int(max_val):
                        return ColumnType.INTEGER
                except (ValueError, TypeError):
                    pass
    return default


def _extract_correlations(report_json: dict[str, Any]) -> dict[str, dict[str, float]]:
    """Extract correlation matrix from ydata-profiling report."""
    correlations: dict[str, dict[str, float]] = {}
    try:
        corr_data = report_json.get("correlations", {})
        # ydata-profiling stores correlations under different keys
        pearson = corr_data.get("pearson", {})
        if isinstance(pearson, dict):
            correlations = {
                str(k): {str(k2): float(v2) for k2, v2 in v.items()}
                for k, v in pearson.items()
                if isinstance(v, dict)
            }
    except (KeyError, TypeError, ValueError):
        pass
    return correlations


def profile_dataset_ydata(
    df: pd.DataFrame,
    dataset_name: str,
    minimal: bool = True,
) -> tuple[list[ColumnProfile], DatasetSummary]:
    """Generate profile using ydata-profiling and extract key stats.

    Args:
        df: DataFrame to profile
        dataset_name: Name of the dataset
        minimal: Use minimal mode for faster profiling (default True)

    Returns:
        Tuple of (column_profiles, dataset_summary)
    """
    logger.info(f"Profiling dataset '{dataset_name}' with ydata-profiling (minimal={minimal})")

    # Generate profile report (suppress all output)
    import warnings

    warnings.filterwarnings("ignore", module="ydata_profiling")

    profile = ProfileReport(
        df,
        title=dataset_name,
        minimal=minimal,
        explorative=False,
        progress_bar=False,
        pool_size=1,  # Single-threaded to reduce overhead
        correlations={
            "pearson": {"calculate": True},
            "spearman": {"calculate": False},
            "kendall": {"calculate": False},
            "phi_k": {"calculate": False},
            "cramers": {"calculate": False},
        },
    )

    # Extract JSON representation
    report_json = json.loads(profile.to_json())

    # Extract dataset-level summary
    table_stats = report_json.get("table", {})
    summary = DatasetSummary(
        row_count=int(table_stats.get("n", len(df))),
        column_count=int(table_stats.get("n_var", len(df.columns))),
        memory_size_bytes=int(table_stats.get("memory_size", 0)),
        duplicate_rows=int(table_stats.get("n_duplicates", 0)),
        duplicate_row_percent=float(table_stats.get("p_duplicates", 0)) * 100,
        missing_cells=int(table_stats.get("n_cells_missing", 0)),
        missing_cells_percent=float(table_stats.get("p_cells_missing", 0)) * 100,
        correlations=_extract_correlations(report_json),
    )

    # Extract column profiles
    columns_data = report_json.get("variables", {})
    column_profiles: list[ColumnProfile] = []
    for col_name, col_data in columns_data.items():
        try:
            col_profile = _extract_column_profile(col_name, col_data)
            column_profiles.append(col_profile)
        except Exception as e:
            logger.warning(f"Failed to extract profile for column '{col_name}': {e}")
            # Create minimal profile on error
            column_profiles.append(
                ColumnProfile(
                    name=col_name,
                    inferred_type=ColumnType.TEXT,
                    stats=ColumnStats(null_count=0, unique_count=0, sample_values=[]),
                )
            )

    logger.info(f"Extracted {len(column_profiles)} column profiles from ydata-profiling")
    return column_profiles, summary


def profile_with_duckdb(
    conn: "duckdb.DuckDBPyConnection",
    dataset_name: str,
) -> tuple[list[ColumnProfile], DatasetSummary]:
    """Generate profile using DuckDB SQL for large datasets.

    More efficient than ydata-profiling for datasets >100K rows.

    Args:
        conn: DuckDB connection with 'dataset' table
        dataset_name: Name of the dataset

    Returns:
        Tuple of (column_profiles, dataset_summary)
    """
    logger.info(f"Profiling dataset '{dataset_name}' with DuckDB")

    # Get table statistics
    row_count = conn.execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    columns_info = conn.execute("DESCRIBE dataset").fetchall()
    column_count = len(columns_info)

    # Estimate memory (rough approximation)
    memory_size = row_count * column_count * 50  # ~50 bytes per cell average

    column_profiles: list[ColumnProfile] = []

    for col_info in columns_info:
        col_name = col_info[0]
        col_type_str = str(col_info[1]).upper()
        quoted_col = f'"{col_name}"'

        # Determine column type
        if "INT" in col_type_str or "BIGINT" in col_type_str:
            col_type = ColumnType.INTEGER
        elif "DOUBLE" in col_type_str or "FLOAT" in col_type_str or "DECIMAL" in col_type_str:
            col_type = ColumnType.FLOAT
        elif "BOOL" in col_type_str:
            col_type = ColumnType.BOOLEAN
        elif "DATE" in col_type_str or "TIMESTAMP" in col_type_str:
            col_type = ColumnType.DATE
        else:
            col_type = ColumnType.TEXT

        try:
            # Get basic stats for all columns
            stats_result = conn.execute(
                f"""
                SELECT
                    COUNT(*) - COUNT({quoted_col}) AS null_count,
                    COUNT(DISTINCT {quoted_col}) AS unique_count
                FROM dataset
                """
            ).fetchone()

            null_count = stats_result[0] or 0
            unique_count = stats_result[1] or 0

            # Get sample values
            sample_result = conn.execute(
                f"""
                SELECT DISTINCT {quoted_col}
                FROM dataset
                WHERE {quoted_col} IS NOT NULL
                LIMIT 5
                """
            ).fetchall()
            sample_values = [row[0] for row in sample_result]

            stats = ColumnStats(
                null_count=null_count,
                unique_count=unique_count,
                sample_values=sample_values,
            )

            # Get numeric stats for numeric columns
            if col_type in (ColumnType.INTEGER, ColumnType.FLOAT):
                numeric_result = conn.execute(
                    f"""
                    SELECT
                        MIN({quoted_col}),
                        MAX({quoted_col}),
                        AVG({quoted_col}),
                        MEDIAN({quoted_col}),
                        STDDEV({quoted_col}),
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {quoted_col}),
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {quoted_col})
                    FROM dataset
                    WHERE {quoted_col} IS NOT NULL
                    """
                ).fetchone()

                if numeric_result:
                    stats.min_value = _safe_float(numeric_result[0])
                    stats.max_value = _safe_float(numeric_result[1])
                    stats.mean_value = _safe_float(numeric_result[2])
                    stats.median_value = _safe_float(numeric_result[3])
                    stats.std_value = _safe_float(numeric_result[4])
                    stats.q25 = _safe_float(numeric_result[5])
                    stats.q75 = _safe_float(numeric_result[6])

            # Get top values for categorical/text columns
            elif col_type in (ColumnType.TEXT, ColumnType.CATEGORICAL, ColumnType.BOOLEAN):
                top_result = conn.execute(
                    f"""
                    SELECT {quoted_col}, COUNT(*) AS cnt
                    FROM dataset
                    WHERE {quoted_col} IS NOT NULL
                    GROUP BY {quoted_col}
                    ORDER BY cnt DESC
                    LIMIT 10
                    """
                ).fetchall()

                if top_result:
                    stats.top_values = [{"value": row[0], "count": row[1]} for row in top_result]

            # Get date stats for date columns
            elif col_type == ColumnType.DATE:
                date_result = conn.execute(
                    f"""
                    SELECT
                        MIN({quoted_col}),
                        MAX({quoted_col}),
                        DATEDIFF('day', MIN({quoted_col}), MAX({quoted_col}))
                    FROM dataset
                    WHERE {quoted_col} IS NOT NULL
                    """
                ).fetchone()

                if date_result:
                    stats.min_date = str(date_result[0]) if date_result[0] else None
                    stats.max_date = str(date_result[1]) if date_result[1] else None
                    stats.date_range_days = date_result[2]

            column_profiles.append(
                ColumnProfile(name=col_name, inferred_type=col_type, stats=stats)
            )

        except Exception as e:
            logger.warning(f"Failed to profile column '{col_name}' with DuckDB: {e}")
            column_profiles.append(
                ColumnProfile(
                    name=col_name,
                    inferred_type=ColumnType.TEXT,
                    stats=ColumnStats(null_count=0, unique_count=0, sample_values=[]),
                )
            )

    # Calculate duplicate rows
    try:
        dup_result = conn.execute(
            """
            SELECT COUNT(*) - COUNT(DISTINCT *)
            FROM dataset
            """
        ).fetchone()
        duplicate_rows = dup_result[0] if dup_result else 0
    except Exception:
        duplicate_rows = 0

    # Calculate missing cells
    total_cells = row_count * column_count
    total_nulls = sum(cp.stats.null_count for cp in column_profiles)

    summary = DatasetSummary(
        row_count=row_count,
        column_count=column_count,
        memory_size_bytes=memory_size,
        duplicate_rows=duplicate_rows,
        duplicate_row_percent=round(duplicate_rows / row_count * 100, 2) if row_count > 0 else 0,
        missing_cells=total_nulls,
        missing_cells_percent=round(total_nulls / total_cells * 100, 2) if total_cells > 0 else 0,
        correlations={},  # Skip correlations for large datasets (expensive)
    )

    logger.info(f"DuckDB profiled {column_count} columns, {row_count} rows")
    return column_profiles, summary


def profile_dataset(
    dataset_id: str | UUID,
    user_id: str,
    repository: DatasetRepository | None = None,
) -> DatasetProfile:
    """Profile a dataset using ydata-profiling or DuckDB.

    For large datasets (>100K rows), uses DuckDB for faster profiling.
    For smaller datasets, uses ydata-profiling for more detailed analysis.

    Args:
        dataset_id: Dataset UUID
        user_id: User ID for authorization
        repository: Optional repository instance

    Returns:
        DatasetProfile with all column profiles and summary

    Raises:
        ProfileError: If profiling fails
    """
    repo = repository or DatasetRepository()

    # Get dataset
    dataset = repo.get_by_id(str(dataset_id), user_id)
    if not dataset:
        raise ProfileError(f"Dataset {dataset_id} not found")

    file_key = dataset.get("file_key")
    if not file_key:
        raise ProfileError(f"Dataset {dataset_id} has no file_key")

    # Get data backend based on size
    try:
        df, conn, row_count = get_dataframe_or_connection(file_key)
    except DataFrameLoadError as e:
        raise ProfileError(f"Failed to load dataset: {e}") from e

    dataset_name = dataset.get("name", "Unknown")

    try:
        if conn is not None:
            # Use DuckDB profiling for large datasets
            logger.info(f"Using DuckDB profiler for {row_count} rows (>={LARGE_DATASET_THRESHOLD})")
            try:
                column_profiles, summary = profile_with_duckdb(conn, dataset_name)
            finally:
                conn.close()
        else:
            # Use ydata-profiling for smaller datasets
            assert df is not None
            minimal = len(df) > 10000 or len(df.columns) > 50
            column_profiles, summary = profile_dataset_ydata(df, dataset_name, minimal=minimal)
    except Exception as e:
        logger.error(f"Profiling failed for dataset {dataset_id}: {e}")
        raise ProfileError(f"Failed to profile dataset: {e}") from e

    profile = DatasetProfile(
        dataset_id=str(dataset_id),
        row_count=summary.row_count,
        column_count=summary.column_count,
        columns=column_profiles,
        summary=summary,
    )

    logger.info(
        f"Profiled dataset {dataset_id}: {profile.row_count} rows, {profile.column_count} columns"
    )

    return profile


def save_profile(
    profile: DatasetProfile,
    repository: DatasetRepository | None = None,
) -> None:
    """Save column profiles to database.

    Args:
        profile: DatasetProfile to save
        repository: Optional repository instance
    """
    repo = repository or DatasetRepository()

    # Clear existing profiles
    repo.delete_profiles(profile.dataset_id)

    # Save new profiles
    for col_profile in profile.columns:
        stats = col_profile.stats
        repo.create_profile(
            dataset_id=profile.dataset_id,
            column_name=col_profile.name,
            data_type=col_profile.inferred_type.value,
            null_count=stats.null_count,
            unique_count=stats.unique_count,
            min_value=str(stats.min_value) if stats.min_value is not None else stats.min_date,
            max_value=str(stats.max_value) if stats.max_value is not None else stats.max_date,
            mean_value=stats.mean_value,
            sample_values=stats.sample_values,
        )

    logger.info(f"Saved {len(profile.columns)} column profiles for dataset {profile.dataset_id}")
