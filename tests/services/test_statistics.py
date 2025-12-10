"""Tests for statistics calculator module."""

import pandas as pd

from backend.services.statistics import compute_column_stats
from backend.services.type_inference import ColumnType


class TestComputeColumnStats:
    """Tests for compute_column_stats function."""

    def test_numeric_stats(self):
        series = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        stats = compute_column_stats(series, ColumnType.INTEGER)

        assert stats.null_count == 0
        assert stats.unique_count == 10
        assert stats.min_value == 1.0
        assert stats.max_value == 10.0
        assert stats.mean_value == 5.5
        assert stats.median_value == 5.5
        assert len(stats.sample_values) == 5

    def test_float_stats(self):
        series = pd.Series([1.5, 2.5, 3.5, 4.5, 5.5])
        stats = compute_column_stats(series, ColumnType.FLOAT)

        assert stats.min_value == 1.5
        assert stats.max_value == 5.5
        assert stats.mean_value == 3.5

    def test_null_count(self):
        series = pd.Series([1, 2, None, 4, None])
        stats = compute_column_stats(series, ColumnType.FLOAT)

        assert stats.null_count == 2
        assert stats.unique_count == 3

    def test_categorical_stats(self):
        series = pd.Series(["red", "blue", "red", "green", "blue", "blue"])
        stats = compute_column_stats(series, ColumnType.CATEGORICAL)

        assert stats.null_count == 0
        assert stats.unique_count == 3
        assert stats.top_values is not None
        assert len(stats.top_values) == 3
        # blue should be most frequent
        assert stats.top_values[0]["value"] == "blue"
        assert stats.top_values[0]["count"] == 3

    def test_date_stats(self):
        series = pd.Series(["2024-01-01", "2024-01-15", "2024-02-01"])
        stats = compute_column_stats(series, ColumnType.DATE)

        assert stats.min_date is not None
        assert stats.max_date is not None
        assert stats.date_range_days == 31  # Jan 1 to Feb 1

    def test_currency_stats(self):
        series = pd.Series(["$100.00", "$200.00", "$300.00"])
        stats = compute_column_stats(series, ColumnType.CURRENCY)

        assert stats.min_value == 100.0
        assert stats.max_value == 300.0
        assert stats.mean_value == 200.0

    def test_percentage_stats(self):
        series = pd.Series(["10%", "20%", "30%", "40%"])
        stats = compute_column_stats(series, ColumnType.PERCENTAGE)

        assert stats.min_value == 10.0
        assert stats.max_value == 40.0
        assert stats.mean_value == 25.0

    def test_boolean_stats(self):
        series = pd.Series(["yes", "no", "yes", "yes", "no"])
        stats = compute_column_stats(series, ColumnType.BOOLEAN)

        assert stats.unique_count == 2
        assert stats.top_values is not None
        assert stats.top_values[0]["value"] == "yes"
        assert stats.top_values[0]["count"] == 3

    def test_sample_values_limit(self):
        series = pd.Series([f"value_{i}" for i in range(100)])
        stats = compute_column_stats(series, ColumnType.TEXT)

        assert len(stats.sample_values) == 5

    def test_empty_series(self):
        series = pd.Series([], dtype=object)
        stats = compute_column_stats(series, ColumnType.TEXT)

        assert stats.null_count == 0
        assert stats.unique_count == 0
        assert stats.sample_values == []

    def test_quartiles(self):
        series = pd.Series(list(range(1, 101)))  # 1 to 100
        stats = compute_column_stats(series, ColumnType.INTEGER)

        assert stats.q25 == 25.75
        assert stats.q75 == 75.25
