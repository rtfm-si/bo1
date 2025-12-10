"""Dataset profiler service.

Orchestrates: load DataFrame → infer types → compute stats → store profiles.
"""

import logging
from dataclasses import asdict
from typing import Any
from uuid import UUID

from backend.services.dataframe_loader import DataFrameLoadError, load_dataframe
from backend.services.statistics import ColumnStats, compute_column_stats
from backend.services.type_inference import ColumnType, infer_column_type
from bo1.state.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)


class ProfileError(Exception):
    """Error during dataset profiling."""

    pass


class ColumnProfile:
    """Profile for a single column."""

    def __init__(
        self,
        name: str,
        inferred_type: ColumnType,
        stats: ColumnStats,
    ) -> None:
        """Initialize ColumnProfile."""
        self.name = name
        self.inferred_type = inferred_type
        self.stats = stats

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        stats_dict = asdict(self.stats)
        return {
            "name": self.name,
            "inferred_type": self.inferred_type.value,
            "stats": stats_dict,
        }


class DatasetProfile:
    """Complete profile for a dataset."""

    def __init__(
        self,
        dataset_id: str,
        row_count: int,
        column_count: int,
        columns: list[ColumnProfile],
    ) -> None:
        """Initialize DatasetProfile."""
        self.dataset_id = dataset_id
        self.row_count = row_count
        self.column_count = column_count
        self.columns = columns

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "dataset_id": self.dataset_id,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [c.to_dict() for c in self.columns],
        }


def profile_dataset(
    dataset_id: str | UUID,
    user_id: str,
    repository: DatasetRepository | None = None,
) -> DatasetProfile:
    """Profile a dataset by loading, inferring types, and computing stats.

    Args:
        dataset_id: Dataset UUID
        user_id: User ID for authorization
        repository: Optional repository instance

    Returns:
        DatasetProfile with all column profiles

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

    # Load DataFrame
    try:
        df = load_dataframe(file_key)
    except DataFrameLoadError as e:
        raise ProfileError(f"Failed to load dataset: {e}") from e

    # Profile each column
    column_profiles: list[ColumnProfile] = []
    for col_name in df.columns:
        series = df[col_name]
        col_type = infer_column_type(series)
        stats = compute_column_stats(series, col_type)
        column_profiles.append(ColumnProfile(col_name, col_type, stats))

    profile = DatasetProfile(
        dataset_id=str(dataset_id),
        row_count=len(df),
        column_count=len(df.columns),
        columns=column_profiles,
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
