"""Multi-dataset cross-dataset anomaly detection service.

Analyzes 2-5 datasets simultaneously to detect:
- Schema drift (columns present in only some datasets)
- Statistical outliers (metric variance > 2 std dev across datasets)
- Type mismatches across versions
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from backend.services.dataset_comparator import DatasetComparator

logger = logging.getLogger(__name__)


@dataclass
class MultiDatasetAnomaly:
    """A detected anomaly across datasets."""

    anomaly_type: str  # "schema_drift", "metric_outlier", "type_mismatch", "no_common_columns"
    severity: str  # "high", "medium", "low"
    description: str
    affected_datasets: list[str]  # Dataset names
    column: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "description": self.description,
            "affected_datasets": self.affected_datasets,
            "column": self.column,
            "details": self.details,
        }


@dataclass
class DatasetSummary:
    """Summary statistics for a single dataset."""

    name: str
    row_count: int
    column_count: int
    columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]
    column_types: dict[str, str]
    numeric_stats: dict[str, dict[str, float | None]]  # {col: {mean, std, min, max}}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": self.columns,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "column_types": self.column_types,
            "numeric_stats": self.numeric_stats,
        }


@dataclass
class CommonSchema:
    """Schema information common across all datasets."""

    common_columns: list[str]  # Columns present in ALL datasets
    partial_columns: dict[str, list[str]]  # {column: [datasets that have it]}
    type_consensus: dict[str, str]  # {column: most_common_type}
    type_conflicts: dict[str, dict[str, str]]  # {column: {dataset: type}}

    def to_dict(self) -> dict[str, Any]:
        return {
            "common_columns": self.common_columns,
            "partial_columns": self.partial_columns,
            "type_consensus": self.type_consensus,
            "type_conflicts": self.type_conflicts,
        }


@dataclass
class MultiDatasetAnalysisResult:
    """Full result of multi-dataset analysis."""

    dataset_names: list[str]
    common_schema: CommonSchema
    anomalies: list[MultiDatasetAnomaly]
    dataset_summaries: list[DatasetSummary]
    pairwise_comparisons: list[dict[str, Any]]  # From existing DatasetComparator

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_names": self.dataset_names,
            "common_schema": self.common_schema.to_dict(),
            "anomalies": [a.to_dict() for a in self.anomalies],
            "dataset_summaries": [s.to_dict() for s in self.dataset_summaries],
            "pairwise_comparisons": self.pairwise_comparisons,
        }


class MultiDatasetAnalyzer:
    """Analyze 2-5 datasets for cross-dataset anomalies."""

    def __init__(self, dataframes: list[pd.DataFrame], names: list[str]):
        """Initialize analyzer.

        Args:
            dataframes: List of 2-5 DataFrames to analyze
            names: Corresponding names for each DataFrame
        """
        if len(dataframes) < 2:
            raise ValueError("At least 2 datasets required for multi-dataset analysis")
        if len(dataframes) > 5:
            raise ValueError("Maximum 5 datasets allowed for multi-dataset analysis")
        if len(dataframes) != len(names):
            raise ValueError("Number of dataframes must match number of names")

        self.dataframes = dataframes
        self.names = names

    def _normalize_dtype(self, dtype: str) -> str:
        """Normalize dtype string for comparison."""
        dtype = dtype.lower()
        if "int" in dtype:
            return "integer"
        if "float" in dtype:
            return "float"
        if "object" in dtype or "string" in dtype:
            return "string"
        if "datetime" in dtype or "date" in dtype:
            return "datetime"
        if "bool" in dtype:
            return "boolean"
        return dtype

    def _safe_float(self, val: Any) -> float | None:
        """Safely convert to float, handling NaN and infinity."""
        if val is None:
            return None
        try:
            f = float(val)
            if np.isnan(f) or np.isinf(f):
                return None
            return round(f, 4)
        except (TypeError, ValueError):
            return None

    def _compute_dataset_summary(self, df: pd.DataFrame, name: str) -> DatasetSummary:
        """Compute summary statistics for a single dataset."""
        columns = list(df.columns)
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        categorical_cols = [
            col
            for col in columns
            if pd.api.types.is_object_dtype(df[col])
            or isinstance(df[col].dtype, pd.CategoricalDtype)
        ]

        column_types = {col: self._normalize_dtype(str(df[col].dtype)) for col in columns}

        # Compute numeric stats
        numeric_stats: dict[str, dict[str, float | None]] = {}
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                numeric_stats[col] = {
                    "mean": self._safe_float(col_data.mean()),
                    "std": self._safe_float(col_data.std()),
                    "min": self._safe_float(col_data.min()),
                    "max": self._safe_float(col_data.max()),
                }
            else:
                numeric_stats[col] = {"mean": None, "std": None, "min": None, "max": None}

        return DatasetSummary(
            name=name,
            row_count=len(df),
            column_count=len(columns),
            columns=columns,
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            column_types=column_types,
            numeric_stats=numeric_stats,
        )

    def _compute_common_schema(self, summaries: list[DatasetSummary]) -> CommonSchema:
        """Compute schema information across all datasets."""
        # Find columns in each dataset
        all_columns: set[str] = set()
        column_presence: dict[str, list[str]] = {}  # {column: [datasets]}

        for summary in summaries:
            for col in summary.columns:
                all_columns.add(col)
                if col not in column_presence:
                    column_presence[col] = []
                column_presence[col].append(summary.name)

        # Common columns (in ALL datasets)
        common_columns = [
            col for col, datasets in column_presence.items() if len(datasets) == len(summaries)
        ]

        # Partial columns (not in all)
        partial_columns = {
            col: datasets
            for col, datasets in column_presence.items()
            if len(datasets) < len(summaries)
        }

        # Type consensus (most common type for each column)
        type_consensus: dict[str, str] = {}
        type_conflicts: dict[str, dict[str, str]] = {}

        for col in all_columns:
            types_found: dict[str, list[str]] = {}  # {type: [datasets]}
            for summary in summaries:
                if col in summary.column_types:
                    col_type = summary.column_types[col]
                    if col_type not in types_found:
                        types_found[col_type] = []
                    types_found[col_type].append(summary.name)

            if types_found:
                # Most common type
                most_common = max(types_found.keys(), key=lambda t: len(types_found[t]))
                type_consensus[col] = most_common

                # Record conflicts if more than one type
                if len(types_found) > 1:
                    type_conflicts[col] = {ds: t for t, dss in types_found.items() for ds in dss}

        return CommonSchema(
            common_columns=sorted(common_columns),
            partial_columns={k: sorted(v) for k, v in partial_columns.items()},
            type_consensus=type_consensus,
            type_conflicts=type_conflicts,
        )

    def _detect_schema_drift_anomalies(
        self, schema: CommonSchema, summaries: list[DatasetSummary]
    ) -> list[MultiDatasetAnomaly]:
        """Detect schema drift anomalies."""
        anomalies = []

        # Check for columns only in some datasets
        for col, datasets in schema.partial_columns.items():
            missing_from = [s.name for s in summaries if s.name not in datasets]

            # High severity if column is in most datasets but missing from some
            if len(datasets) >= len(summaries) - 1:
                severity = "high"
            elif len(datasets) >= len(summaries) / 2:
                severity = "medium"
            else:
                severity = "low"

            anomalies.append(
                MultiDatasetAnomaly(
                    anomaly_type="schema_drift",
                    severity=severity,
                    description=f"Column '{col}' is missing from {len(missing_from)} dataset(s)",
                    affected_datasets=missing_from,
                    column=col,
                    details={"present_in": datasets, "missing_from": missing_from},
                )
            )

        # Check for type mismatches
        for col, type_map in schema.type_conflicts.items():
            types_present = list(set(type_map.values()))
            anomalies.append(
                MultiDatasetAnomaly(
                    anomaly_type="type_mismatch",
                    severity="high",
                    description=f"Column '{col}' has different types across datasets: {', '.join(types_present)}",
                    affected_datasets=list(type_map.keys()),
                    column=col,
                    details={"type_by_dataset": type_map},
                )
            )

        return anomalies

    def _detect_metric_outliers(
        self, summaries: list[DatasetSummary], common_cols: list[str]
    ) -> list[MultiDatasetAnomaly]:
        """Detect statistical outliers (values > 2 std dev from mean across datasets)."""
        if not summaries:
            return []

        anomalies = []

        # Find common numeric columns
        common_numeric = set(summaries[0].numeric_columns)
        for summary in summaries[1:]:
            common_numeric &= set(summary.numeric_columns)

        common_numeric = [c for c in common_numeric if c in common_cols]

        for col in common_numeric:
            # Gather means across datasets
            means = []
            dataset_means: dict[str, float] = {}

            for summary in summaries:
                if col in summary.numeric_stats and summary.numeric_stats[col]["mean"] is not None:
                    means.append(summary.numeric_stats[col]["mean"])
                    dataset_means[summary.name] = summary.numeric_stats[col]["mean"]

            if len(means) < 2:
                continue

            # Calculate cross-dataset mean and std
            overall_mean = np.mean(means)
            overall_std = np.std(means)

            if overall_std == 0:
                continue

            # Find outliers (>= 2 std dev)
            outliers = []
            for ds_name, ds_mean in dataset_means.items():
                z_score = abs((ds_mean - overall_mean) / overall_std)
                if z_score >= 2:
                    outliers.append((ds_name, ds_mean, z_score))

            if outliers:
                for ds_name, ds_mean, z_score in outliers:
                    severity = "high" if z_score > 3 else "medium"
                    direction = "above" if ds_mean > overall_mean else "below"

                    anomalies.append(
                        MultiDatasetAnomaly(
                            anomaly_type="metric_outlier",
                            severity=severity,
                            description=f"'{col}' in {ds_name} is {z_score:.1f} std dev {direction} cross-dataset mean",
                            affected_datasets=[ds_name],
                            column=col,
                            details={
                                "dataset_value": ds_mean,
                                "cross_dataset_mean": round(overall_mean, 4),
                                "cross_dataset_std": round(overall_std, 4),
                                "z_score": round(z_score, 2),
                            },
                        )
                    )

        return anomalies

    def _run_pairwise_comparisons(self) -> list[dict[str, Any]]:
        """Run pairwise comparisons using existing DatasetComparator."""
        comparisons = []

        for i in range(len(self.dataframes)):
            for j in range(i + 1, len(self.dataframes)):
                comparator = DatasetComparator(
                    self.dataframes[i],
                    self.dataframes[j],
                    self.names[i],
                    self.names[j],
                )
                result = comparator.run_full_comparison()
                comparisons.append(
                    {
                        "dataset_a": self.names[i],
                        "dataset_b": self.names[j],
                        "result": result.to_dict(),
                    }
                )

        return comparisons

    def run_analysis(self) -> MultiDatasetAnalysisResult:
        """Run full multi-dataset analysis."""
        # Compute summaries for each dataset
        summaries = [
            self._compute_dataset_summary(df, name)
            for df, name in zip(self.dataframes, self.names, strict=True)
        ]

        # Compute common schema
        schema = self._compute_common_schema(summaries)

        # Detect anomalies
        anomalies: list[MultiDatasetAnomaly] = []

        # Check for zero common columns
        if not schema.common_columns:
            anomalies.append(
                MultiDatasetAnomaly(
                    anomaly_type="no_common_columns",
                    severity="high",
                    description="No columns are common to all datasets",
                    affected_datasets=self.names,
                    details={"partial_columns": schema.partial_columns},
                )
            )
        else:
            # Schema drift anomalies
            anomalies.extend(self._detect_schema_drift_anomalies(schema, summaries))

            # Metric outliers
            anomalies.extend(self._detect_metric_outliers(summaries, schema.common_columns))

        # Run pairwise comparisons
        pairwise = self._run_pairwise_comparisons()

        # Sort anomalies by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        anomalies.sort(key=lambda a: severity_order.get(a.severity, 3))

        return MultiDatasetAnalysisResult(
            dataset_names=self.names,
            common_schema=schema,
            anomalies=anomalies,
            dataset_summaries=summaries,
            pairwise_comparisons=pairwise,
        )


def analyze_multiple_datasets(
    dataframes: list[pd.DataFrame],
    names: list[str],
) -> MultiDatasetAnalysisResult:
    """Convenience function to analyze multiple datasets.

    Args:
        dataframes: List of 2-5 DataFrames to analyze
        names: Corresponding names for each DataFrame

    Returns:
        MultiDatasetAnalysisResult with all analysis data
    """
    analyzer = MultiDatasetAnalyzer(dataframes, names)
    return analyzer.run_analysis()
