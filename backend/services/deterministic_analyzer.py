"""Deterministic dataset analyses - computed locally without LLM.

Provides 8 pre-computed analyses that serve dual purposes:
1. Displayed to user as "Key Insights" immediately after dataset loads
2. Fed to LLM along with business context for smarter "Next Steps"
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Analysis Result Models
# =============================================================================


@dataclass
class ColumnRole:
    """Inferred semantic role for a column."""

    column_name: str
    inferred_role: str  # "identifier", "timestamp", "metric", "dimension", "unknown"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    suggested_type_fix: str | None = None


@dataclass
class ColumnRolesAnalysis:
    """Analysis 1: Column role inference."""

    columns: list[ColumnRole]
    primary_key_candidate: str | None = None
    time_column: str | None = None
    metric_columns: list[str] = field(default_factory=list)
    dimension_columns: list[str] = field(default_factory=list)


@dataclass
class ColumnMissingness:
    """Missingness stats for a column."""

    column_name: str
    null_count: int
    null_percent: float
    unique_count: int
    unique_percent: float
    cardinality_class: str  # "low" (<10), "medium" (10-100), "high" (>100)
    is_complete: bool


@dataclass
class MissingnessAnalysis:
    """Analysis 2: Missingness + uniqueness + cardinality."""

    columns: list[ColumnMissingness]
    overall_completeness: float
    columns_with_nulls: list[str]
    high_cardinality_columns: list[str]
    potential_id_columns: list[str]  # High uniqueness


@dataclass
class HeavyHitter:
    """A value that dominates a column's distribution."""

    value: str
    count: int
    percent: float


@dataclass
class ColumnDescriptiveStats:
    """Descriptive stats for a column."""

    column_name: str
    data_type: str
    # Numeric stats
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    skewness: float | None = None
    # Categorical stats
    heavy_hitters: list[HeavyHitter] | None = None
    has_dominant_value: bool = False  # >30% of values


@dataclass
class DescriptiveStatsAnalysis:
    """Analysis 3: Descriptive stats + heavy hitters."""

    columns: list[ColumnDescriptiveStats]
    skewed_columns: list[str]  # |skewness| > 1
    columns_with_dominant_values: list[str]


@dataclass
class ColumnOutliers:
    """Outlier info for a numeric column."""

    column_name: str
    outlier_count: int
    outlier_percent: float
    lower_bound: float
    upper_bound: float
    sample_outliers: list[float]  # Up to 5 examples
    method: str = "IQR"


@dataclass
class OutlierAnalysis:
    """Analysis 4: Outlier detection."""

    columns: list[ColumnOutliers]
    total_outlier_rows: int
    columns_with_outliers: list[str]


@dataclass
class CorrelationPair:
    """A notable correlation between two columns."""

    column_a: str
    column_b: str
    correlation: float
    is_leakage_risk: bool  # |corr| > 0.95
    is_highly_correlated: bool  # |corr| > 0.8


@dataclass
class CorrelationAnalysis:
    """Analysis 5: Correlation matrix + leakage hints."""

    notable_pairs: list[CorrelationPair]
    leakage_warnings: list[str]
    highly_correlated_pairs: list[str]  # "colA <-> colB"


@dataclass
class TimeSeriesAnalysis:
    """Analysis 6: Time-series readiness."""

    date_column: str | None
    is_time_series_ready: bool
    cadence: str | None  # "daily", "weekly", "monthly", "irregular"
    date_range_days: int | None
    min_date: str | None
    max_date: str | None
    gap_count: int = 0
    gaps: list[str] = field(default_factory=list)  # Gap descriptions
    seasonality_hint: str | None = None


@dataclass
class SegmentationSuggestion:
    """A suggested metric + dimension combination."""

    metric_column: str
    dimension_column: str
    rationale: str
    priority: int  # 1 = highest


@dataclass
class SegmentationAnalysis:
    """Analysis 7: Segmentation suggestions."""

    suggestions: list[SegmentationSuggestion]
    best_metric: str | None = None
    best_dimensions: list[str] = field(default_factory=list)


@dataclass
class QualityIssue:
    """A data quality issue."""

    column_name: str
    issue_type: str  # "mixed_types", "inconsistent_format", "high_nulls", "suspicious_values"
    description: str
    severity: str  # "high", "medium", "low"
    affected_count: int


@dataclass
class DataQualityAnalysis:
    """Analysis 8: Data quality assessment."""

    overall_score: int  # 0-100
    issues: list[QualityIssue]
    recommendations: list[str]


@dataclass
class DatasetInvestigation:
    """Combined result of all 8 analyses."""

    column_roles: ColumnRolesAnalysis
    missingness: MissingnessAnalysis
    descriptive_stats: DescriptiveStatsAnalysis
    outliers: OutlierAnalysis
    correlations: CorrelationAnalysis
    time_series_readiness: TimeSeriesAnalysis
    segmentation_suggestions: SegmentationAnalysis
    data_quality: DataQualityAnalysis

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage.

        Transforms field names to match frontend KeyInsightsPanel expectations.
        """

        def convert_numpy(obj: Any) -> Any:
            """Recursively convert numpy types to native Python types."""
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(v) for v in obj]
            elif isinstance(obj, (np.bool_, np.generic)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        # Transform column_roles: columns -> roles, column_name -> column, inferred_role -> role
        column_roles = {
            "roles": [
                {
                    "column": col.column_name,
                    "role": col.inferred_role,
                    "confidence": col.confidence,
                    "reasoning": col.reasoning,
                }
                for col in self.column_roles.columns
            ],
            "metric_columns": self.column_roles.metric_columns,
            "dimension_columns": self.column_roles.dimension_columns,
            "primary_key_candidate": self.column_roles.primary_key_candidate,
            "time_column": self.column_roles.time_column,
        }

        # Transform missingness: column_name -> column, cardinality_class -> cardinality_category
        # columns_with_nulls -> high_null_columns
        missingness = {
            "columns": [
                {
                    "column": col.column_name,
                    "null_count": col.null_count,
                    "null_percent": col.null_percent,
                    "unique_count": col.unique_count,
                    "unique_percent": col.unique_percent,
                    "cardinality_category": col.cardinality_class,
                    "is_complete": col.is_complete,
                }
                for col in self.missingness.columns
            ],
            "overall_completeness": self.missingness.overall_completeness,
            "columns_with_nulls": len(self.missingness.columns_with_nulls),
            "high_null_columns": self.missingness.columns_with_nulls,
            "high_cardinality_columns": self.missingness.high_cardinality_columns,
        }

        # Transform descriptive_stats: split into numeric_columns and categorical_columns
        numeric_cols = []
        categorical_cols = []
        for col in self.descriptive_stats.columns:
            if col.data_type == "numeric":
                numeric_cols.append(
                    {
                        "column": col.column_name,
                        "mean": col.mean,
                        "median": col.median,
                        "std": col.std,
                        "min": col.min_val,
                        "max": col.max_val,
                        "skewness": col.skewness,
                    }
                )
            else:
                top_values = None
                if col.heavy_hitters:
                    top_values = [
                        {"value": hh.value, "count": hh.count, "percent": hh.percent}
                        for hh in col.heavy_hitters
                    ]
                categorical_cols.append(
                    {
                        "column": col.column_name,
                        "top_values": top_values,
                        "has_dominant_value": col.has_dominant_value,
                    }
                )

        descriptive_stats = {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "skewed_columns": self.descriptive_stats.skewed_columns,
            "columns_with_dominant_values": self.descriptive_stats.columns_with_dominant_values,
        }

        # Transform outliers: columns -> outliers, column_name -> column
        outliers = {
            "outliers": [
                {
                    "column": col.column_name,
                    "outlier_count": col.outlier_count,
                    "outlier_percent": col.outlier_percent,
                    "lower_bound": col.lower_bound,
                    "upper_bound": col.upper_bound,
                    "sample_outliers": col.sample_outliers,
                    "method": col.method,
                }
                for col in self.outliers.columns
            ],
            "total_outlier_rows": self.outliers.total_outlier_rows,
            "columns_with_outliers": len(self.outliers.columns_with_outliers),
        }

        # Transform correlations: split notable_pairs into potential_leakage, top_positive, top_negative
        potential_leakage = []
        top_positive = []
        top_negative = []
        for pair in self.correlations.notable_pairs:
            pair_dict = {
                "column_a": pair.column_a,
                "column_b": pair.column_b,
                "correlation": pair.correlation,
            }
            if pair.is_leakage_risk:
                potential_leakage.append(pair_dict)
            elif pair.correlation > 0:
                top_positive.append(pair_dict)
            else:
                top_negative.append(pair_dict)

        # Sort by absolute correlation
        top_positive.sort(key=lambda x: x["correlation"], reverse=True)
        top_negative.sort(key=lambda x: x["correlation"])

        correlations = {
            "potential_leakage": potential_leakage,
            "top_positive": top_positive[:10],
            "top_negative": top_negative[:10],
            "leakage_warnings": self.correlations.leakage_warnings,
        }

        # Transform time_series_readiness
        ts = self.time_series_readiness
        date_range = None
        if ts.min_date and ts.max_date:
            date_range = {"start": ts.min_date, "end": ts.max_date}

        time_series_readiness = {
            "is_ready": ts.is_time_series_ready,
            "timestamp_column": ts.date_column,
            "detected_frequency": ts.cadence,
            "date_range": date_range,
            "date_range_days": ts.date_range_days,
            "gap_count": ts.gap_count,
            "recommendations": ts.gaps if ts.gaps else [],
            "seasonality_hint": ts.seasonality_hint,
        }

        # Transform segmentation_suggestions: suggestions -> opportunities
        segmentation_suggestions = {
            "opportunities": [
                {
                    "metric": s.metric_column,
                    "dimension": s.dimension_column,
                    "recommendation": s.rationale,
                    "priority": s.priority,
                }
                for s in self.segmentation_suggestions.suggestions
            ],
            "best_metric": self.segmentation_suggestions.best_metric,
            "best_dimensions": self.segmentation_suggestions.best_dimensions,
        }

        # Transform data_quality: column_name -> column, add score breakdown
        # Calculate completeness/consistency/validity from issues
        completeness_issues = sum(
            1 for i in self.data_quality.issues if i.issue_type == "high_nulls"
        )
        consistency_issues = sum(
            1
            for i in self.data_quality.issues
            if i.issue_type in ("mixed_types", "inconsistent_format")
        )
        validity_issues = sum(
            1 for i in self.data_quality.issues if i.issue_type == "suspicious_values"
        )

        data_quality = {
            "overall_score": self.data_quality.overall_score,
            "completeness_score": max(0, 100 - (completeness_issues * 20)),
            "consistency_score": max(0, 100 - (consistency_issues * 20)),
            "validity_score": max(0, 100 - (validity_issues * 20)),
            "issues": [
                {
                    "column": i.column_name,
                    "issue_type": i.issue_type,
                    "description": i.description,
                    "severity": i.severity,
                    "affected_count": i.affected_count,
                }
                for i in self.data_quality.issues
            ],
            "recommendations": self.data_quality.recommendations,
        }

        return convert_numpy(
            {
                "column_roles": column_roles,
                "missingness": missingness,
                "descriptive_stats": descriptive_stats,
                "outliers": outliers,
                "correlations": correlations,
                "time_series_readiness": time_series_readiness,
                "segmentation_suggestions": segmentation_suggestions,
                "data_quality": data_quality,
            }
        )


# =============================================================================
# Deterministic Analyzer
# =============================================================================


class DeterministicAnalyzer:
    """Runs all 8 deterministic analyses on a DataFrame."""

    # Patterns for role inference
    ID_PATTERNS = re.compile(r"(^id$|_id$|^uuid$|^key$|_key$|^pk$)", re.IGNORECASE)
    TIMESTAMP_PATTERNS = re.compile(
        r"(date|time|_at$|_on$|created|updated|timestamp|dt$)", re.IGNORECASE
    )
    # Note: Metric detection is now data-first (any numeric column with >10 distinct values)
    # Keywords are no longer used for metric detection - the data speaks for itself
    DIMENSION_KEYWORDS = [
        "category",
        "type",
        "status",
        "region",
        "country",
        "city",
        "state",
        "segment",
        "channel",
        "source",
        "tier",
        "level",
        "group",
        "class",
        "name",
        "label",
    ]

    def __init__(self, df: pd.DataFrame, profile_summary: dict[str, Any] | None = None):
        """Initialize analyzer.

        Args:
            df: DataFrame to analyze
            profile_summary: Optional ydata-profiling summary for enhanced analysis
        """
        self.df = df
        self.profile_summary = profile_summary or {}
        self._numeric_df: pd.DataFrame | None = None

    def _get_numeric_df(self) -> pd.DataFrame:
        """Get DataFrame with string columns converted to numeric where possible.

        Caches the result for reuse across analyses.
        """
        if self._numeric_df is not None:
            return self._numeric_df

        numeric_df = self.df.select_dtypes(include=[np.number]).copy()

        # Try to convert object columns that look numeric
        for col in self.df.select_dtypes(include=["object"]).columns:
            try:
                # Remove common formatting: $, €, £, commas, % signs
                cleaned = self.df[col].astype(str).str.replace(r"[$€£,%]", "", regex=True)
                cleaned = cleaned.str.replace(",", "")
                numeric_series = pd.to_numeric(cleaned, errors="coerce")
                # If >50% values are numeric, include the column
                if numeric_series.notna().sum() > 0.5 * len(self.df[col].dropna()):
                    numeric_df[col] = numeric_series
            except (ValueError, TypeError):
                # Column cannot be converted to numeric - skip silently
                continue

        self._numeric_df = numeric_df
        return numeric_df

    def run_all(self) -> DatasetInvestigation:
        """Run all 8 analyses and return combined result."""
        logger.info(
            f"Running deterministic analyses on {len(self.df)} rows, {len(self.df.columns)} columns"
        )

        return DatasetInvestigation(
            column_roles=self.analyze_column_roles(),
            missingness=self.analyze_missingness(),
            descriptive_stats=self.analyze_descriptive_stats(),
            outliers=self.detect_outliers(),
            correlations=self.analyze_correlations(),
            time_series_readiness=self.analyze_time_series_readiness(),
            segmentation_suggestions=self.build_segmentation_suggestions(),
            data_quality=self.assess_data_quality(),
        )

    # -------------------------------------------------------------------------
    # Analysis 1: Column Role Inference
    # -------------------------------------------------------------------------

    def analyze_column_roles(self) -> ColumnRolesAnalysis:
        """Infer semantic roles: id, timestamp, metric, dimension."""
        roles: list[ColumnRole] = []
        primary_key_candidate = None
        time_column = None
        metric_columns = []
        dimension_columns = []

        for col in self.df.columns:
            series = self.df[col]
            role, confidence, reasoning = self._infer_column_role(col, series)

            roles.append(
                ColumnRole(
                    column_name=col,
                    inferred_role=role,
                    confidence=confidence,
                    reasoning=reasoning,
                )
            )

            if role == "identifier" and primary_key_candidate is None:
                primary_key_candidate = col
            elif role == "timestamp" and time_column is None:
                time_column = col
            elif role == "metric":
                metric_columns.append(col)
            elif role == "dimension":
                dimension_columns.append(col)

        return ColumnRolesAnalysis(
            columns=roles,
            primary_key_candidate=primary_key_candidate,
            time_column=time_column,
            metric_columns=metric_columns,
            dimension_columns=dimension_columns,
        )

    def _infer_column_role(self, col_name: str, series: pd.Series) -> tuple[str, float, str]:
        """Infer role for a single column using data-first approach.

        Priority order:
        1. ID detection (name pattern + high uniqueness)
        2. Timestamp detection (datetime type or parseable dates)
        3. Numeric columns: metric by default, dimension if binary/low-cardinality
        4. Non-numeric: dimension if low cardinality, unknown otherwise
        """
        n_rows = max(len(series), 1)
        n_unique = series.nunique()
        unique_ratio = n_unique / n_rows

        # 1. Check for ID patterns (name-based + data validation)
        if self.ID_PATTERNS.search(col_name):
            if unique_ratio > 0.9:
                return "identifier", 0.95, "Name pattern + high uniqueness"
            return "identifier", 0.7, "Name pattern suggests ID"

        # 2. Check for timestamp (datetime type or parseable)
        if pd.api.types.is_datetime64_any_dtype(series):
            return "timestamp", 0.95, "DateTime type"

        if self.TIMESTAMP_PATTERNS.search(col_name):
            try:
                pd.to_datetime(series.dropna().head(100), format="mixed")
                return "timestamp", 0.85, "Parseable as date + name pattern"
            except (ValueError, TypeError):
                pass

        # 3. Numeric columns - DATA-FIRST approach
        is_numeric = pd.api.types.is_numeric_dtype(series)

        # Try converting string columns that look numeric
        if not is_numeric and series.dtype == "object":
            try:
                cleaned = series.astype(str).str.replace(r"[$€£,%]", "", regex=True)
                cleaned = cleaned.str.replace(",", "")
                numeric_series = pd.to_numeric(cleaned, errors="coerce")
                if numeric_series.notna().sum() > 0.5 * len(series.dropna()):
                    is_numeric = True
                    n_unique = numeric_series.nunique()
            except (ValueError, TypeError):
                pass  # Column cannot be converted - continue with original type

        if is_numeric:
            # Binary column (0/1, yes/no encoded) → dimension
            if n_unique == 2:
                return "dimension", 0.8, "Binary numeric (2 distinct values)"

            # Very low cardinality numeric → likely categorical encoding → dimension
            if n_unique <= 10:
                return "dimension", 0.7, f"Low cardinality numeric ({n_unique} distinct values)"

            # All other numeric columns are metrics
            # This is the key change: numeric = metric by default
            return "metric", 0.85, f"Numeric column ({n_unique} distinct values)"

        # 4. Non-numeric columns
        # Check for dimension keywords (still useful for string columns)
        col_lower = col_name.lower()
        for keyword in self.DIMENSION_KEYWORDS:
            if keyword in col_lower:
                return "dimension", 0.85, f"'{keyword}' in name"

        # Low cardinality string/categorical → dimension
        if n_unique <= 50 and unique_ratio < 0.3:
            return "dimension", 0.8, f"Low cardinality categorical ({n_unique} distinct values)"

        # Medium cardinality categorical
        if n_unique <= 100:
            return "dimension", 0.6, f"Categorical ({n_unique} distinct values)"

        # High cardinality text - could be names, descriptions, etc.
        return "unknown", 0.5, f"High cardinality text ({n_unique} distinct values)"

    # -------------------------------------------------------------------------
    # Analysis 2: Missingness + Uniqueness + Cardinality
    # -------------------------------------------------------------------------

    def analyze_missingness(self) -> MissingnessAnalysis:
        """Analyze null patterns, uniqueness, cardinality."""
        columns: list[ColumnMissingness] = []
        columns_with_nulls = []
        high_cardinality_columns = []
        potential_id_columns = []
        total_cells = len(self.df) * len(self.df.columns)
        total_null = 0

        for col in self.df.columns:
            series = self.df[col]
            null_count = int(series.isna().sum())
            total_null += null_count
            null_percent = (null_count / len(series) * 100) if len(series) > 0 else 0
            unique_count = int(series.nunique())
            unique_percent = (unique_count / len(series) * 100) if len(series) > 0 else 0

            # Cardinality class
            if unique_count < 10:
                cardinality_class = "low"
            elif unique_count < 100:
                cardinality_class = "medium"
            else:
                cardinality_class = "high"
                high_cardinality_columns.append(col)

            is_complete = null_count == 0

            columns.append(
                ColumnMissingness(
                    column_name=col,
                    null_count=null_count,
                    null_percent=round(null_percent, 2),
                    unique_count=unique_count,
                    unique_percent=round(unique_percent, 2),
                    cardinality_class=cardinality_class,
                    is_complete=is_complete,
                )
            )

            if null_count > 0:
                columns_with_nulls.append(col)

            # Potential ID column: very high uniqueness
            if unique_percent > 95 and null_count == 0:
                potential_id_columns.append(col)

        overall_completeness = (
            ((total_cells - total_null) / total_cells * 100) if total_cells > 0 else 100
        )

        return MissingnessAnalysis(
            columns=columns,
            overall_completeness=round(overall_completeness, 2),
            columns_with_nulls=columns_with_nulls,
            high_cardinality_columns=high_cardinality_columns,
            potential_id_columns=potential_id_columns,
        )

    # -------------------------------------------------------------------------
    # Analysis 3: Descriptive Stats + Heavy Hitters
    # -------------------------------------------------------------------------

    def analyze_descriptive_stats(self) -> DescriptiveStatsAnalysis:
        """Stats for numeric columns, heavy hitters for categorical."""
        columns: list[ColumnDescriptiveStats] = []
        skewed_columns = []
        columns_with_dominant_values = []

        for col in self.df.columns:
            series = self.df[col]
            is_numeric = pd.api.types.is_numeric_dtype(series)

            # Try to convert string columns to numeric (handles "$1,234" or "1,234" formats)
            if not is_numeric and series.dtype == "object":
                try:
                    # Remove common formatting: $, €, £, commas, % signs
                    cleaned = series.astype(str).str.replace(r"[$€£,%]", "", regex=True)
                    cleaned = cleaned.str.replace(",", "")
                    numeric_series = pd.to_numeric(cleaned, errors="coerce")
                    # If >50% values are numeric, treat as numeric column
                    if numeric_series.notna().sum() > 0.5 * len(series.dropna()):
                        series = numeric_series
                        is_numeric = True
                except (ValueError, TypeError):
                    pass  # Column cannot be converted - keep as categorical

            stats = ColumnDescriptiveStats(
                column_name=col, data_type="numeric" if is_numeric else str(series.dtype)
            )

            if is_numeric:
                non_null = series.dropna()
                if len(non_null) > 0:
                    stats.mean = round(float(non_null.mean()), 4)
                    stats.median = round(float(non_null.median()), 4)
                    stats.std = round(float(non_null.std()), 4) if len(non_null) > 1 else 0
                    stats.min_val = float(non_null.min())
                    stats.max_val = float(non_null.max())
                    # Skewness
                    if len(non_null) > 2:
                        try:
                            stats.skewness = round(float(non_null.skew()), 4)
                            if abs(stats.skewness) > 1:
                                skewed_columns.append(col)
                        except (ValueError, TypeError):
                            pass
            else:
                # Categorical: find heavy hitters
                value_counts = series.value_counts()
                total = len(series.dropna())
                if total > 0:
                    heavy_hitters = []
                    for val, count in value_counts.head(5).items():
                        percent = count / total * 100
                        heavy_hitters.append(
                            HeavyHitter(
                                value=str(val)[:100],  # Truncate long values
                                count=int(count),
                                percent=round(percent, 2),
                            )
                        )
                        if percent > 30:
                            stats.has_dominant_value = True
                            if col not in columns_with_dominant_values:
                                columns_with_dominant_values.append(col)
                    stats.heavy_hitters = heavy_hitters

            columns.append(stats)

        return DescriptiveStatsAnalysis(
            columns=columns,
            skewed_columns=skewed_columns,
            columns_with_dominant_values=columns_with_dominant_values,
        )

    # -------------------------------------------------------------------------
    # Analysis 4: Outlier Detection
    # -------------------------------------------------------------------------

    def detect_outliers(self) -> OutlierAnalysis:
        """IQR-based outlier detection for numeric columns."""
        columns: list[ColumnOutliers] = []
        columns_with_outliers = []
        outlier_rows = set()

        numeric_df = self._get_numeric_df()

        for col in numeric_df.columns:
            series = numeric_df[col].dropna()
            if len(series) < 4:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outlier_mask.sum())

            if outlier_count > 0:
                outlier_percent = outlier_count / len(series) * 100
                sample_outliers = series[outlier_mask].head(5).tolist()
                outlier_rows.update(series[outlier_mask].index.tolist())

                columns.append(
                    ColumnOutliers(
                        column_name=col,
                        outlier_count=outlier_count,
                        outlier_percent=round(outlier_percent, 2),
                        lower_bound=round(lower_bound, 4),
                        upper_bound=round(upper_bound, 4),
                        sample_outliers=[round(x, 4) for x in sample_outliers],
                    )
                )
                columns_with_outliers.append(col)

        return OutlierAnalysis(
            columns=columns,
            total_outlier_rows=len(outlier_rows),
            columns_with_outliers=columns_with_outliers,
        )

    # -------------------------------------------------------------------------
    # Analysis 5: Correlation Matrix + Leakage Hints
    # -------------------------------------------------------------------------

    def analyze_correlations(self) -> CorrelationAnalysis:
        """Compute correlations, flag potential leakage."""
        notable_pairs: list[CorrelationPair] = []
        leakage_warnings = []
        highly_correlated_pairs = []

        numeric_df = self._get_numeric_df()
        numeric_cols = numeric_df.columns.tolist()

        # Limit to top 30 columns to avoid huge matrices
        if len(numeric_cols) > 30:
            numeric_cols = numeric_cols[:30]

        if len(numeric_cols) < 2:
            return CorrelationAnalysis(
                notable_pairs=[],
                leakage_warnings=[],
                highly_correlated_pairs=[],
            )

        try:
            corr_matrix = numeric_df[numeric_cols].corr()
        except (ValueError, TypeError, KeyError):
            # Correlation calculation failed - return empty analysis
            return CorrelationAnalysis(
                notable_pairs=[],
                leakage_warnings=[],
                highly_correlated_pairs=[],
            )

        # Find notable pairs
        for i, col_a in enumerate(numeric_cols):
            for col_b in numeric_cols[i + 1 :]:
                corr = corr_matrix.loc[col_a, col_b]
                if pd.isna(corr):
                    continue

                abs_corr = abs(corr)
                is_leakage = abs_corr > 0.95
                is_high = abs_corr > 0.8

                if is_high:
                    pair = CorrelationPair(
                        column_a=col_a,
                        column_b=col_b,
                        correlation=round(float(corr), 4),
                        is_leakage_risk=is_leakage,
                        is_highly_correlated=is_high,
                    )
                    notable_pairs.append(pair)

                    if is_leakage:
                        leakage_warnings.append(
                            f"{col_a} <-> {col_b} (r={corr:.2f}): Possible data leakage"
                        )
                    highly_correlated_pairs.append(f"{col_a} <-> {col_b}")

        return CorrelationAnalysis(
            notable_pairs=notable_pairs,
            leakage_warnings=leakage_warnings,
            highly_correlated_pairs=highly_correlated_pairs,
        )

    # -------------------------------------------------------------------------
    # Analysis 6: Time-Series Readiness
    # -------------------------------------------------------------------------

    def analyze_time_series_readiness(self) -> TimeSeriesAnalysis:
        """Check for date columns, cadence, gaps."""
        # Find date column
        date_col = self._find_date_column()

        if date_col is None:
            return TimeSeriesAnalysis(
                date_column=None,
                is_time_series_ready=False,
                cadence=None,
                date_range_days=None,
                min_date=None,
                max_date=None,
            )

        # Parse dates
        try:
            dates = pd.to_datetime(self.df[date_col], format="mixed", errors="coerce")
        except (ValueError, TypeError, KeyError):
            # Date parsing failed - column is not time-series ready
            return TimeSeriesAnalysis(
                date_column=date_col,
                is_time_series_ready=False,
                cadence=None,
                date_range_days=None,
                min_date=None,
                max_date=None,
            )

        valid_dates = dates.dropna().sort_values()

        if len(valid_dates) < 2:
            return TimeSeriesAnalysis(
                date_column=date_col,
                is_time_series_ready=False,
                cadence=None,
                date_range_days=None,
                min_date=None,
                max_date=None,
            )

        min_date = valid_dates.min()
        max_date = valid_dates.max()
        date_range_days = (max_date - min_date).days

        # Detect cadence
        diffs = valid_dates.diff().dropna()
        median_diff = diffs.median()

        if median_diff <= pd.Timedelta(days=1.5):
            cadence = "daily"
        elif median_diff <= pd.Timedelta(days=8):
            cadence = "weekly"
        elif median_diff <= pd.Timedelta(days=35):
            cadence = "monthly"
        else:
            cadence = "irregular"

        # Detect gaps (for daily/weekly data)
        gaps = []
        gap_count = 0
        if cadence in ("daily", "weekly"):
            expected_diff = pd.Timedelta(days=1) if cadence == "daily" else pd.Timedelta(days=7)
            threshold = expected_diff * 2

            for i in range(1, min(len(valid_dates), 100)):
                diff = valid_dates.iloc[i] - valid_dates.iloc[i - 1]
                if diff > threshold:
                    gap_count += 1
                    if len(gaps) < 5:
                        gaps.append(
                            f"{valid_dates.iloc[i - 1].date()} to {valid_dates.iloc[i].date()}"
                        )

        return TimeSeriesAnalysis(
            date_column=date_col,
            is_time_series_ready=True,
            cadence=cadence,
            date_range_days=date_range_days,
            min_date=str(min_date.date()),
            max_date=str(max_date.date()),
            gap_count=gap_count,
            gaps=gaps,
        )

    def _find_date_column(self) -> str | None:
        """Find the primary date column."""
        # First check columns with date-like names
        for col in self.df.columns:
            if self.TIMESTAMP_PATTERNS.search(col):
                if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                    return col
                # Try parsing
                try:
                    pd.to_datetime(self.df[col].dropna().head(50), format="mixed")
                    return col
                except (ValueError, TypeError):
                    continue

        # Check datetime columns without date-like names
        for col in self.df.columns:
            if pd.api.types.is_datetime64_any_dtype(self.df[col]):
                return col

        return None

    # -------------------------------------------------------------------------
    # Analysis 7: Segmentation Builder
    # -------------------------------------------------------------------------

    def build_segmentation_suggestions(self) -> SegmentationAnalysis:
        """Suggest good metric + dimension combinations."""
        suggestions: list[SegmentationSuggestion] = []

        # Find metrics and dimensions from role analysis
        roles = self.analyze_column_roles()
        metrics = roles.metric_columns[:5]  # Top 5 metrics
        dimensions = roles.dimension_columns[:5]  # Top 5 dimensions

        # If no clear metrics, find numeric columns
        if not metrics:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
            # Exclude likely IDs
            metrics = [c for c in numeric_cols if not self.ID_PATTERNS.search(c)][:5]

        # If no clear dimensions, find low-cardinality categoricals
        if not dimensions:
            for col in self.df.columns:
                if col in metrics:
                    continue
                series = self.df[col]
                if series.dtype == "object" or pd.api.types.is_categorical_dtype(series):
                    if 2 <= series.nunique() <= 20:
                        dimensions.append(col)
                        if len(dimensions) >= 5:
                            break

        # Generate suggestions
        priority = 1
        for metric in metrics[:3]:
            for dimension in dimensions[:3]:
                rationale = f"Analyze '{metric}' by '{dimension}'"
                suggestions.append(
                    SegmentationSuggestion(
                        metric_column=metric,
                        dimension_column=dimension,
                        rationale=rationale,
                        priority=priority,
                    )
                )
                priority += 1

        return SegmentationAnalysis(
            suggestions=suggestions[:9],  # Max 9 suggestions
            best_metric=metrics[0] if metrics else None,
            best_dimensions=dimensions[:3],
        )

    # -------------------------------------------------------------------------
    # Analysis 8: Data Quality Assessment
    # -------------------------------------------------------------------------

    def assess_data_quality(self) -> DataQualityAnalysis:
        """Assess consistency, format issues, encoding problems."""
        issues: list[QualityIssue] = []
        recommendations = []
        score_deductions = 0

        for col in self.df.columns:
            series = self.df[col]

            # Check high null rate
            null_rate = series.isna().mean()
            if null_rate > 0.5:
                issues.append(
                    QualityIssue(
                        column_name=col,
                        issue_type="high_nulls",
                        description=f"{null_rate * 100:.1f}% missing values",
                        severity="high",
                        affected_count=int(series.isna().sum()),
                    )
                )
                score_deductions += 10
            elif null_rate > 0.1:
                issues.append(
                    QualityIssue(
                        column_name=col,
                        issue_type="high_nulls",
                        description=f"{null_rate * 100:.1f}% missing values",
                        severity="medium",
                        affected_count=int(series.isna().sum()),
                    )
                )
                score_deductions += 5

            # Check for mixed types in object columns
            if series.dtype == "object":
                non_null = series.dropna()
                if len(non_null) > 0:
                    types = non_null.apply(type).unique()
                    if len(types) > 1:
                        issues.append(
                            QualityIssue(
                                column_name=col,
                                issue_type="mixed_types",
                                description=f"Contains mixed types: {[t.__name__ for t in types]}",
                                severity="medium",
                                affected_count=len(non_null),
                            )
                        )
                        score_deductions += 5

            # Check for suspicious values (empty strings, whitespace-only)
            if series.dtype == "object":
                empty_count = (series == "").sum() + series.str.strip().eq("").sum()
                if empty_count > 0:
                    issues.append(
                        QualityIssue(
                            column_name=col,
                            issue_type="suspicious_values",
                            description="Contains empty or whitespace-only strings",
                            severity="low",
                            affected_count=int(empty_count),
                        )
                    )
                    score_deductions += 2

        # Check for duplicate rows
        dup_count = self.df.duplicated().sum()
        if dup_count > 0:
            dup_rate = dup_count / len(self.df) * 100
            severity = "high" if dup_rate > 10 else "medium" if dup_rate > 1 else "low"
            issues.append(
                QualityIssue(
                    column_name="(entire row)",
                    issue_type="duplicates",
                    description=f"{dup_count} duplicate rows ({dup_rate:.1f}%)",
                    severity=severity,
                    affected_count=int(dup_count),
                )
            )
            score_deductions += 5 if severity == "low" else 10 if severity == "medium" else 15

        # Generate recommendations
        high_issues = [i for i in issues if i.severity == "high"]
        if high_issues:
            recommendations.append(f"Address {len(high_issues)} high-severity issues first")
        if any(i.issue_type == "high_nulls" for i in issues):
            recommendations.append("Consider imputation or filtering for columns with many nulls")
        if any(i.issue_type == "duplicates" for i in issues):
            recommendations.append("Review and deduplicate rows if appropriate")

        overall_score = max(0, min(100, 100 - score_deductions))

        return DataQualityAnalysis(
            overall_score=overall_score,
            issues=issues,
            recommendations=recommendations,
        )


# =============================================================================
# Convenience Function
# =============================================================================


def run_investigation(
    df: pd.DataFrame, profile_summary: dict[str, Any] | None = None
) -> DatasetInvestigation:
    """Run all 8 deterministic analyses on a DataFrame.

    Args:
        df: DataFrame to analyze
        profile_summary: Optional ydata-profiling summary

    Returns:
        DatasetInvestigation with all analysis results
    """
    analyzer = DeterministicAnalyzer(df, profile_summary)
    return analyzer.run_all()
