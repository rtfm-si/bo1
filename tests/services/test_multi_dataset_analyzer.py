"""Tests for multi-dataset analysis service."""

import numpy as np
import pandas as pd
import pytest

from backend.services.multi_dataset_analyzer import (
    MultiDatasetAnalysisResult,
    MultiDatasetAnalyzer,
    analyze_multiple_datasets,
)


class TestMultiDatasetAnalyzer:
    """Tests for MultiDatasetAnalyzer class."""

    def test_init_requires_minimum_two_datasets(self):
        """Should raise ValueError if less than 2 datasets provided."""
        df = pd.DataFrame({"a": [1, 2, 3]})

        with pytest.raises(ValueError, match="At least 2 datasets"):
            MultiDatasetAnalyzer([df], ["ds1"])

    def test_init_requires_maximum_five_datasets(self):
        """Should raise ValueError if more than 5 datasets provided."""
        dfs = [pd.DataFrame({"a": [i]}) for i in range(6)]
        names = [f"ds{i}" for i in range(6)]

        with pytest.raises(ValueError, match="Maximum 5 datasets"):
            MultiDatasetAnalyzer(dfs, names)

    def test_init_requires_matching_names(self):
        """Should raise ValueError if names don't match dataframes."""
        dfs = [pd.DataFrame({"a": [1]}), pd.DataFrame({"a": [2]})]
        names = ["ds1"]

        with pytest.raises(ValueError, match="must match"):
            MultiDatasetAnalyzer(dfs, names)

    def test_detects_common_columns(self):
        """Should detect columns present in all datasets."""
        df1 = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        df2 = pd.DataFrame({"a": [4], "b": [5], "c": [6]})
        df3 = pd.DataFrame({"a": [7], "b": [8], "c": [9]})

        analyzer = MultiDatasetAnalyzer([df1, df2, df3], ["ds1", "ds2", "ds3"])
        result = analyzer.run_analysis()

        assert set(result.common_schema.common_columns) == {"a", "b", "c"}
        assert len(result.common_schema.partial_columns) == 0

    def test_detects_partial_columns(self):
        """Should detect columns present in only some datasets."""
        df1 = pd.DataFrame({"a": [1], "b": [2]})
        df2 = pd.DataFrame({"a": [3], "c": [4]})
        df3 = pd.DataFrame({"a": [5], "b": [6]})

        analyzer = MultiDatasetAnalyzer([df1, df2, df3], ["ds1", "ds2", "ds3"])
        result = analyzer.run_analysis()

        assert result.common_schema.common_columns == ["a"]
        assert "b" in result.common_schema.partial_columns
        assert "c" in result.common_schema.partial_columns

    def test_detects_schema_drift_anomaly(self):
        """Should detect schema drift when columns are missing from datasets."""
        df1 = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        df2 = pd.DataFrame({"a": [4], "b": [5]})  # Missing column c

        analyzer = MultiDatasetAnalyzer([df1, df2], ["ds1", "ds2"])
        result = analyzer.run_analysis()

        schema_drift_anomalies = [a for a in result.anomalies if a.anomaly_type == "schema_drift"]
        assert len(schema_drift_anomalies) >= 1
        assert any(a.column == "c" for a in schema_drift_anomalies)

    def test_detects_type_mismatch(self):
        """Should detect type mismatches for same column across datasets."""
        df1 = pd.DataFrame({"a": [1, 2, 3]})  # int
        df2 = pd.DataFrame({"a": ["x", "y", "z"]})  # string

        analyzer = MultiDatasetAnalyzer([df1, df2], ["ds1", "ds2"])
        result = analyzer.run_analysis()

        type_mismatch_anomalies = [a for a in result.anomalies if a.anomaly_type == "type_mismatch"]
        assert len(type_mismatch_anomalies) >= 1
        assert type_mismatch_anomalies[0].column == "a"

    def test_detects_metric_outlier(self):
        """Should detect metric outliers (>2 std dev from cross-dataset mean)."""
        # Create 5 datasets where one has a very different mean for column 'x'
        # Use slightly varied values to avoid exact z=2.0 threshold edge case
        df1 = pd.DataFrame({"x": [10, 11, 9, 10, 10]})  # mean ~10
        df2 = pd.DataFrame({"x": [10, 10, 10, 11, 9]})  # mean ~10
        df3 = pd.DataFrame({"x": [9, 10, 11, 10, 10]})  # mean ~10
        df4 = pd.DataFrame({"x": [11, 10, 9, 10, 10]})  # mean ~10
        df5 = pd.DataFrame({"x": [1000, 1001, 999, 1000, 1000]})  # mean ~1000 - extreme outlier

        analyzer = MultiDatasetAnalyzer(
            [df1, df2, df3, df4, df5], ["ds1", "ds2", "ds3", "ds4", "ds5"]
        )
        result = analyzer.run_analysis()

        metric_outliers = [a for a in result.anomalies if a.anomaly_type == "metric_outlier"]
        assert len(metric_outliers) >= 1
        assert any("ds5" in a.affected_datasets for a in metric_outliers)

    def test_handles_no_common_columns(self):
        """Should detect when datasets have no common columns."""
        df1 = pd.DataFrame({"a": [1], "b": [2]})
        df2 = pd.DataFrame({"c": [3], "d": [4]})

        analyzer = MultiDatasetAnalyzer([df1, df2], ["ds1", "ds2"])
        result = analyzer.run_analysis()

        no_common = [a for a in result.anomalies if a.anomaly_type == "no_common_columns"]
        assert len(no_common) == 1
        assert no_common[0].severity == "high"

    def test_computes_dataset_summaries(self):
        """Should compute summary statistics for each dataset."""
        df1 = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        df2 = pd.DataFrame({"a": [4, 5, 6], "c": [7.0, 8.0, 9.0]})

        analyzer = MultiDatasetAnalyzer([df1, df2], ["ds1", "ds2"])
        result = analyzer.run_analysis()

        assert len(result.dataset_summaries) == 2
        ds1_summary = result.dataset_summaries[0]
        assert ds1_summary.name == "ds1"
        assert ds1_summary.row_count == 3
        assert ds1_summary.column_count == 2
        assert "a" in ds1_summary.numeric_columns

    def test_runs_pairwise_comparisons(self):
        """Should run pairwise comparisons for all dataset pairs."""
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [4, 5, 6]})
        df3 = pd.DataFrame({"a": [7, 8, 9]})

        analyzer = MultiDatasetAnalyzer([df1, df2, df3], ["ds1", "ds2", "ds3"])
        result = analyzer.run_analysis()

        # 3 datasets = 3 pairs: (ds1,ds2), (ds1,ds3), (ds2,ds3)
        assert len(result.pairwise_comparisons) == 3

    def test_result_to_dict(self):
        """Should convert result to serializable dict."""
        df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df2 = pd.DataFrame({"a": [5, 6], "b": [7, 8]})

        analyzer = MultiDatasetAnalyzer([df1, df2], ["ds1", "ds2"])
        result = analyzer.run_analysis()
        result_dict = result.to_dict()

        assert "dataset_names" in result_dict
        assert "common_schema" in result_dict
        assert "anomalies" in result_dict
        assert "dataset_summaries" in result_dict
        assert "pairwise_comparisons" in result_dict

    def test_anomaly_severity_ordering(self):
        """Should sort anomalies by severity (high first)."""
        # Create scenarios that will produce anomalies of different severities
        df1 = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        df2 = pd.DataFrame({"a": ["x"], "d": [4]})  # Type mismatch (high), schema drift

        analyzer = MultiDatasetAnalyzer([df1, df2], ["ds1", "ds2"])
        result = analyzer.run_analysis()

        if len(result.anomalies) >= 2:
            severities = [a.severity for a in result.anomalies]
            severity_order = {"high": 0, "medium": 1, "low": 2}
            for i in range(len(severities) - 1):
                assert severity_order[severities[i]] <= severity_order[severities[i + 1]]


class TestConvenienceFunction:
    """Tests for the analyze_multiple_datasets convenience function."""

    def test_analyze_multiple_datasets(self):
        """Should run analysis via convenience function."""
        df1 = pd.DataFrame({"x": [1, 2, 3]})
        df2 = pd.DataFrame({"x": [4, 5, 6]})

        result = analyze_multiple_datasets([df1, df2], ["ds1", "ds2"])

        assert isinstance(result, MultiDatasetAnalysisResult)
        assert result.dataset_names == ["ds1", "ds2"]

    def test_handles_empty_dataframes(self):
        """Should handle empty dataframes gracefully."""
        df1 = pd.DataFrame({"a": []})
        df2 = pd.DataFrame({"a": []})

        result = analyze_multiple_datasets([df1, df2], ["empty1", "empty2"])

        assert result.dataset_summaries[0].row_count == 0
        assert result.dataset_summaries[1].row_count == 0

    def test_handles_nan_values(self):
        """Should handle NaN values in numeric columns."""
        df1 = pd.DataFrame({"a": [1, 2, np.nan, 4]})
        df2 = pd.DataFrame({"a": [np.nan, np.nan, np.nan, np.nan]})

        result = analyze_multiple_datasets([df1, df2], ["ds1", "ds2"])

        # Should not raise errors and should produce valid summaries
        assert len(result.dataset_summaries) == 2
