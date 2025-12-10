"""Tests for profiler service module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from backend.services.profiler import (
    ColumnProfile,
    DatasetProfile,
    ProfileError,
    profile_dataset,
    save_profile,
)
from backend.services.statistics import ColumnStats
from backend.services.type_inference import ColumnType


class TestColumnProfile:
    """Tests for ColumnProfile class."""

    def test_to_dict(self):
        stats = ColumnStats(
            null_count=0,
            unique_count=10,
            sample_values=[1, 2, 3],
            min_value=1.0,
            max_value=10.0,
        )
        profile = ColumnProfile("test_col", ColumnType.INTEGER, stats)
        result = profile.to_dict()

        assert result["name"] == "test_col"
        assert result["inferred_type"] == "integer"
        assert result["stats"]["null_count"] == 0
        assert result["stats"]["min_value"] == 1.0


class TestDatasetProfile:
    """Tests for DatasetProfile class."""

    def test_to_dict(self):
        stats = ColumnStats(null_count=0, unique_count=5, sample_values=[])
        col = ColumnProfile("col1", ColumnType.TEXT, stats)
        profile = DatasetProfile("dataset-123", 100, 1, [col])

        result = profile.to_dict()

        assert result["dataset_id"] == "dataset-123"
        assert result["row_count"] == 100
        assert result["column_count"] == 1
        assert len(result["columns"]) == 1


class TestProfileDataset:
    """Tests for profile_dataset function."""

    @patch("backend.services.profiler.load_dataframe")
    def test_profile_success(self, mock_load):
        # Setup mock
        df = pd.DataFrame({"num": [1, 2, 3], "text": ["a", "b", "c"]})
        mock_load.return_value = df

        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {
            "id": "test-id",
            "file_key": "datasets/user/test.csv",
        }

        # Execute
        profile = profile_dataset("test-id", "user-1", mock_repo)

        # Verify
        assert profile.dataset_id == "test-id"
        assert profile.row_count == 3
        assert profile.column_count == 2
        assert len(profile.columns) == 2

    @patch("backend.services.profiler.load_dataframe")
    def test_profile_not_found(self, mock_load):
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = None

        with pytest.raises(ProfileError, match="not found"):
            profile_dataset("missing-id", "user-1", mock_repo)

    @patch("backend.services.profiler.load_dataframe")
    def test_profile_no_file_key(self, mock_load):
        mock_repo = MagicMock()
        mock_repo.get_by_id.return_value = {"id": "test-id", "file_key": None}

        with pytest.raises(ProfileError, match="no file_key"):
            profile_dataset("test-id", "user-1", mock_repo)


class TestSaveProfile:
    """Tests for save_profile function."""

    def test_save_clears_existing(self):
        stats = ColumnStats(
            null_count=0,
            unique_count=5,
            sample_values=["a", "b"],
            min_value=None,
            max_value=None,
        )
        col = ColumnProfile("col1", ColumnType.TEXT, stats)
        profile = DatasetProfile("dataset-123", 100, 1, [col])

        mock_repo = MagicMock()
        save_profile(profile, mock_repo)

        # Should delete existing profiles first
        mock_repo.delete_profiles.assert_called_once_with("dataset-123")
        # Should create new profile
        mock_repo.create_profile.assert_called_once()

    def test_save_multiple_columns(self):
        stats1 = ColumnStats(null_count=0, unique_count=5, sample_values=[])
        stats2 = ColumnStats(null_count=1, unique_count=3, sample_values=[])
        col1 = ColumnProfile("col1", ColumnType.INTEGER, stats1)
        col2 = ColumnProfile("col2", ColumnType.TEXT, stats2)
        profile = DatasetProfile("dataset-123", 100, 2, [col1, col2])

        mock_repo = MagicMock()
        save_profile(profile, mock_repo)

        assert mock_repo.create_profile.call_count == 2
