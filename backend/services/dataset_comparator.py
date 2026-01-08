"""Dataset comparison service.

Compares two datasets (e.g., Jan vs Feb sales, Cohort A vs B) and generates
insights about their differences.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ColumnComparison:
    """Comparison result for a single column."""

    column: str
    in_a: bool
    in_b: bool
    type_a: str | None
    type_b: str | None
    type_match: bool


@dataclass
class SchemaComparison:
    """Schema comparison between two datasets."""

    common_columns: list[str]
    only_in_a: list[str]
    only_in_b: list[str]
    type_mismatches: list[dict[str, Any]]  # [{column, type_a, type_b}]
    column_count_a: int
    column_count_b: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "common_columns": self.common_columns,
            "only_in_a": self.only_in_a,
            "only_in_b": self.only_in_b,
            "type_mismatches": self.type_mismatches,
            "column_count_a": self.column_count_a,
            "column_count_b": self.column_count_b,
        }


@dataclass
class ColumnStatsDelta:
    """Statistics delta for a numeric column."""

    column: str
    mean_a: float | None
    mean_b: float | None
    mean_delta: float | None
    mean_pct_change: float | None
    median_a: float | None
    median_b: float | None
    median_delta: float | None
    std_a: float | None
    std_b: float | None
    min_a: float | None
    min_b: float | None
    max_a: float | None
    max_b: float | None
    null_count_a: int
    null_count_b: int
    null_delta: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "mean_a": self.mean_a,
            "mean_b": self.mean_b,
            "mean_delta": self.mean_delta,
            "mean_pct_change": self.mean_pct_change,
            "median_a": self.median_a,
            "median_b": self.median_b,
            "median_delta": self.median_delta,
            "std_a": self.std_a,
            "std_b": self.std_b,
            "min_a": self.min_a,
            "min_b": self.min_b,
            "max_a": self.max_a,
            "max_b": self.max_b,
            "null_count_a": self.null_count_a,
            "null_count_b": self.null_count_b,
            "null_delta": self.null_delta,
        }


@dataclass
class CategoricalDelta:
    """Distribution delta for a categorical column."""

    column: str
    unique_a: int
    unique_b: int
    top_values_a: list[dict[str, Any]]  # [{value, count, percent}]
    top_values_b: list[dict[str, Any]]
    new_values_in_b: list[str]  # Values present in B but not in A
    missing_in_b: list[str]  # Values present in A but not in B

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "unique_a": self.unique_a,
            "unique_b": self.unique_b,
            "top_values_a": self.top_values_a,
            "top_values_b": self.top_values_b,
            "new_values_in_b": self.new_values_in_b,
            "missing_in_b": self.missing_in_b,
        }


@dataclass
class StatisticsComparison:
    """Statistics comparison between datasets."""

    row_count_a: int
    row_count_b: int
    row_delta: int
    row_pct_change: float | None
    numeric_deltas: list[ColumnStatsDelta]
    categorical_deltas: list[CategoricalDelta]

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count_a": self.row_count_a,
            "row_count_b": self.row_count_b,
            "row_delta": self.row_delta,
            "row_pct_change": self.row_pct_change,
            "numeric_deltas": [d.to_dict() for d in self.numeric_deltas],
            "categorical_deltas": [d.to_dict() for d in self.categorical_deltas],
        }


@dataclass
class MetricComparison:
    """Key metric comparison with significance."""

    metric_name: str
    value_a: float
    value_b: float
    delta: float
    pct_change: float | None
    direction: str  # "up", "down", "flat"
    significance: str  # "high", "medium", "low"
    is_improvement: bool | None  # None if we can't determine

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_name": self.metric_name,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "delta": self.delta,
            "pct_change": self.pct_change,
            "direction": self.direction,
            "significance": self.significance,
            "is_improvement": self.is_improvement,
        }


@dataclass
class KeyMetricsComparison:
    """Key metrics comparison between datasets."""

    metrics: list[MetricComparison]
    summary: str  # Brief summary of key changes

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "summary": self.summary,
        }


@dataclass
class DatasetComparisonResult:
    """Full comparison result between two datasets."""

    dataset_a_name: str
    dataset_b_name: str
    schema_comparison: SchemaComparison
    statistics_comparison: StatisticsComparison
    key_metrics_comparison: KeyMetricsComparison
    insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_a_name": self.dataset_a_name,
            "dataset_b_name": self.dataset_b_name,
            "schema_comparison": self.schema_comparison.to_dict(),
            "statistics_comparison": self.statistics_comparison.to_dict(),
            "key_metrics_comparison": self.key_metrics_comparison.to_dict(),
            "insights": self.insights,
        }


class DatasetComparator:
    """Compare two pandas DataFrames and generate comparison insights."""

    def __init__(
        self,
        df_a: pd.DataFrame,
        df_b: pd.DataFrame,
        name_a: str = "Dataset A",
        name_b: str = "Dataset B",
    ):
        self.df_a = df_a
        self.df_b = df_b
        self.name_a = name_a
        self.name_b = name_b

    def compare_schemas(self) -> SchemaComparison:
        """Compare column schemas between datasets."""
        cols_a = set(self.df_a.columns)
        cols_b = set(self.df_b.columns)

        common = cols_a & cols_b
        only_a = cols_a - cols_b
        only_b = cols_b - cols_a

        # Check type mismatches in common columns
        type_mismatches = []
        for col in common:
            type_a = str(self.df_a[col].dtype)
            type_b = str(self.df_b[col].dtype)
            # Normalize types for comparison
            type_a_norm = self._normalize_dtype(type_a)
            type_b_norm = self._normalize_dtype(type_b)
            if type_a_norm != type_b_norm:
                type_mismatches.append(
                    {
                        "column": col,
                        "type_a": type_a,
                        "type_b": type_b,
                    }
                )

        return SchemaComparison(
            common_columns=sorted(common),
            only_in_a=sorted(only_a),
            only_in_b=sorted(only_b),
            type_mismatches=type_mismatches,
            column_count_a=len(cols_a),
            column_count_b=len(cols_b),
        )

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

    def compare_statistics(self, common_columns: list[str] | None = None) -> StatisticsComparison:
        """Compare statistics for common columns."""
        if common_columns is None:
            schema = self.compare_schemas()
            common_columns = schema.common_columns

        numeric_deltas = []
        categorical_deltas = []

        for col in common_columns:
            if col not in self.df_a.columns or col not in self.df_b.columns:
                continue

            col_a = self.df_a[col]
            col_b = self.df_b[col]

            # Determine if numeric
            if pd.api.types.is_numeric_dtype(col_a) and pd.api.types.is_numeric_dtype(col_b):
                numeric_deltas.append(self._compare_numeric_column(col, col_a, col_b))
            elif pd.api.types.is_object_dtype(col_a) or pd.api.types.is_categorical_dtype(col_a):
                categorical_deltas.append(self._compare_categorical_column(col, col_a, col_b))

        # Row count comparison
        row_a = len(self.df_a)
        row_b = len(self.df_b)
        row_delta = row_b - row_a
        row_pct = (row_delta / row_a * 100) if row_a > 0 else None

        return StatisticsComparison(
            row_count_a=row_a,
            row_count_b=row_b,
            row_delta=row_delta,
            row_pct_change=round(row_pct, 2) if row_pct is not None else None,
            numeric_deltas=numeric_deltas,
            categorical_deltas=categorical_deltas,
        )

    def _compare_numeric_column(
        self, col: str, col_a: pd.Series, col_b: pd.Series
    ) -> ColumnStatsDelta:
        """Compare statistics for a numeric column."""
        mean_a = col_a.mean() if not col_a.isna().all() else None
        mean_b = col_b.mean() if not col_b.isna().all() else None

        mean_delta = None
        mean_pct = None
        if mean_a is not None and mean_b is not None:
            mean_delta = mean_b - mean_a
            if mean_a != 0:
                mean_pct = round((mean_delta / mean_a) * 100, 2)

        median_a = col_a.median() if not col_a.isna().all() else None
        median_b = col_b.median() if not col_b.isna().all() else None
        median_delta = None
        if median_a is not None and median_b is not None:
            median_delta = median_b - median_a

        return ColumnStatsDelta(
            column=col,
            mean_a=self._safe_float(mean_a),
            mean_b=self._safe_float(mean_b),
            mean_delta=self._safe_float(mean_delta),
            mean_pct_change=mean_pct,
            median_a=self._safe_float(median_a),
            median_b=self._safe_float(median_b),
            median_delta=self._safe_float(median_delta),
            std_a=self._safe_float(col_a.std()),
            std_b=self._safe_float(col_b.std()),
            min_a=self._safe_float(col_a.min()),
            min_b=self._safe_float(col_b.min()),
            max_a=self._safe_float(col_a.max()),
            max_b=self._safe_float(col_b.max()),
            null_count_a=int(col_a.isna().sum()),
            null_count_b=int(col_b.isna().sum()),
            null_delta=int(col_b.isna().sum()) - int(col_a.isna().sum()),
        )

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

    def _compare_categorical_column(
        self, col: str, col_a: pd.Series, col_b: pd.Series
    ) -> CategoricalDelta:
        """Compare distribution for a categorical column."""
        values_a = set(col_a.dropna().unique())
        values_b = set(col_b.dropna().unique())

        # Top values
        top_a = col_a.value_counts().head(5)
        top_b = col_b.value_counts().head(5)

        def format_top(vc: pd.Series, total: int) -> list[dict[str, Any]]:
            return [
                {"value": str(v), "count": int(c), "percent": round(c / total * 100, 1)}
                for v, c in vc.items()
            ]

        return CategoricalDelta(
            column=col,
            unique_a=len(values_a),
            unique_b=len(values_b),
            top_values_a=format_top(top_a, len(col_a)),
            top_values_b=format_top(top_b, len(col_b)),
            new_values_in_b=sorted([str(v) for v in (values_b - values_a)])[:10],
            missing_in_b=sorted([str(v) for v in (values_a - values_b)])[:10],
        )

    def compare_key_metrics(self, common_columns: list[str] | None = None) -> KeyMetricsComparison:
        """Identify and compare key metrics."""
        if common_columns is None:
            schema = self.compare_schemas()
            common_columns = schema.common_columns

        metrics = []

        # Identify likely metric columns (numeric with revenue/amount/value/count keywords)
        metric_keywords = [
            "revenue",
            "amount",
            "value",
            "total",
            "count",
            "sales",
            "cost",
            "price",
            "profit",
        ]

        for col in common_columns:
            if col not in self.df_a.columns:
                continue

            col_lower = col.lower()
            is_metric = any(kw in col_lower for kw in metric_keywords)

            if is_metric and pd.api.types.is_numeric_dtype(self.df_a[col]):
                val_a = self.df_a[col].sum()
                val_b = self.df_b[col].sum()

                if pd.isna(val_a) or pd.isna(val_b):
                    continue

                delta = val_b - val_a
                pct_change = (delta / val_a * 100) if val_a != 0 else None

                # Determine direction and significance
                direction = "flat"
                if pct_change is not None:
                    if pct_change > 1:
                        direction = "up"
                    elif pct_change < -1:
                        direction = "down"

                significance = "low"
                if pct_change is not None:
                    abs_pct = abs(pct_change)
                    if abs_pct > 20:
                        significance = "high"
                    elif abs_pct > 5:
                        significance = "medium"

                # Determine if improvement (higher is typically better for revenue/sales/profit)
                positive_metrics = ["revenue", "sales", "profit", "value"]
                negative_metrics = ["cost", "churn", "loss"]

                is_improvement = None
                if any(kw in col_lower for kw in positive_metrics):
                    is_improvement = delta > 0
                elif any(kw in col_lower for kw in negative_metrics):
                    is_improvement = delta < 0

                metrics.append(
                    MetricComparison(
                        metric_name=col,
                        value_a=self._safe_float(val_a) or 0,
                        value_b=self._safe_float(val_b) or 0,
                        delta=self._safe_float(delta) or 0,
                        pct_change=round(pct_change, 2) if pct_change is not None else None,
                        direction=direction,
                        significance=significance,
                        is_improvement=is_improvement,
                    )
                )

        # Generate summary
        if not metrics:
            summary = "No key metrics identified for comparison."
        else:
            improving = [m for m in metrics if m.is_improvement is True]
            declining = [m for m in metrics if m.is_improvement is False]
            if improving and not declining:
                summary = f"All {len(improving)} key metrics improved."
            elif declining and not improving:
                summary = f"All {len(declining)} key metrics declined."
            elif improving and declining:
                summary = f"{len(improving)} metrics improved, {len(declining)} declined."
            else:
                summary = f"{len(metrics)} metrics compared."

        return KeyMetricsComparison(metrics=metrics, summary=summary)

    def generate_insights(
        self,
        schema: SchemaComparison,
        stats: StatisticsComparison,
        metrics: KeyMetricsComparison,
    ) -> list[str]:
        """Generate human-readable insights from comparison."""
        insights = []

        # Row count insight
        if stats.row_pct_change is not None:
            if stats.row_pct_change > 10:
                insights.append(
                    f"Dataset B has {stats.row_pct_change:.1f}% more rows than Dataset A (+{stats.row_delta:,} records)"
                )
            elif stats.row_pct_change < -10:
                insights.append(
                    f"Dataset B has {abs(stats.row_pct_change):.1f}% fewer rows than Dataset A ({stats.row_delta:,} records)"
                )

        # Schema differences
        if schema.only_in_a:
            insights.append(
                f"Columns only in {self.name_a}: {', '.join(schema.only_in_a[:5])}"
                + (f" (+{len(schema.only_in_a) - 5} more)" if len(schema.only_in_a) > 5 else "")
            )
        if schema.only_in_b:
            insights.append(
                f"New columns in {self.name_b}: {', '.join(schema.only_in_b[:5])}"
                + (f" (+{len(schema.only_in_b) - 5} more)" if len(schema.only_in_b) > 5 else "")
            )
        if schema.type_mismatches:
            insights.append(
                f"{len(schema.type_mismatches)} column(s) have type mismatches between datasets"
            )

        # Key metric insights
        for m in metrics.metrics:
            if m.significance == "high" and m.pct_change is not None:
                direction_word = "increased" if m.direction == "up" else "decreased"
                insights.append(f"{m.metric_name} {direction_word} by {abs(m.pct_change):.1f}%")

        # Numeric column insights (significant changes)
        for nd in stats.numeric_deltas:
            if nd.mean_pct_change is not None and abs(nd.mean_pct_change) > 20:
                direction = "increased" if nd.mean_pct_change > 0 else "decreased"
                insights.append(
                    f"Average {nd.column} {direction} by {abs(nd.mean_pct_change):.1f}%"
                )

        # Null count changes
        for nd in stats.numeric_deltas:
            if nd.null_delta != 0 and abs(nd.null_delta) > 100:
                direction = "more" if nd.null_delta > 0 else "fewer"
                insights.append(f"{abs(nd.null_delta)} {direction} null values in {nd.column}")

        return insights[:10]  # Limit to 10 insights

    def run_full_comparison(self) -> DatasetComparisonResult:
        """Run full comparison and return results."""
        schema = self.compare_schemas()
        stats = self.compare_statistics(schema.common_columns)
        metrics = self.compare_key_metrics(schema.common_columns)
        insights = self.generate_insights(schema, stats, metrics)

        return DatasetComparisonResult(
            dataset_a_name=self.name_a,
            dataset_b_name=self.name_b,
            schema_comparison=schema,
            statistics_comparison=stats,
            key_metrics_comparison=metrics,
            insights=insights,
        )


def compare_datasets(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    name_a: str = "Dataset A",
    name_b: str = "Dataset B",
) -> DatasetComparisonResult:
    """Convenience function to compare two datasets.

    Args:
        df_a: First DataFrame (baseline/older)
        df_b: Second DataFrame (comparison/newer)
        name_a: Name for first dataset
        name_b: Name for second dataset

    Returns:
        DatasetComparisonResult with all comparison data
    """
    comparator = DatasetComparator(df_a, df_b, name_a, name_b)
    return comparator.run_full_comparison()
