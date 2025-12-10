"""Query engine for DataFrame operations.

Executes structured queries (filter, aggregate, trend, compare, correlate)
against pandas DataFrames loaded from datasets.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from backend.api.models import (
    FilterSpec,
    QuerySpec,
)
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Cache TTL for query results (5 minutes)
QUERY_CACHE_TTL = 300


class QueryError(Exception):
    """Error executing query."""

    pass


@dataclass
class QueryResult:
    """Result of a query execution."""

    rows: list[dict[str, Any]]
    columns: list[str]
    total_count: int
    has_more: bool
    query_type: str


def _compute_query_hash(dataset_id: str, spec: QuerySpec) -> str:
    """Compute cache key hash for a query."""
    spec_json = spec.model_dump_json(exclude={"limit", "offset"})
    content = f"{dataset_id}:{spec_json}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _get_cached_result(cache_key: str) -> QueryResult | None:
    """Get cached query result if exists."""
    try:
        redis = RedisManager()
        data = redis.client.get(cache_key)
        if data:
            result_dict = json.loads(data)
            return QueryResult(**result_dict)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    return None


def _cache_result(cache_key: str, result: QueryResult) -> None:
    """Cache query result."""
    try:
        redis = RedisManager()
        result_dict = {
            "rows": result.rows,
            "columns": result.columns,
            "total_count": result.total_count,
            "has_more": result.has_more,
            "query_type": result.query_type,
        }
        redis.client.setex(cache_key, QUERY_CACHE_TTL, json.dumps(result_dict))
    except Exception as e:
        logger.warning(f"Cache set error: {e}")


def _apply_filters(df: pd.DataFrame, filters: list[FilterSpec]) -> pd.DataFrame:
    """Apply filter conditions to DataFrame."""
    if not filters:
        return df

    for f in filters:
        if f.field not in df.columns:
            raise QueryError(f"Column '{f.field}' not found")

        col = df[f.field]
        value = f.value

        if f.operator == "eq":
            df = df[col == value]
        elif f.operator == "ne":
            df = df[col != value]
        elif f.operator == "gt":
            df = df[col > value]
        elif f.operator == "lt":
            df = df[col < value]
        elif f.operator == "gte":
            df = df[col >= value]
        elif f.operator == "lte":
            df = df[col <= value]
        elif f.operator == "contains":
            df = df[col.astype(str).str.contains(str(value), case=False, na=False)]
        elif f.operator == "in":
            if not isinstance(value, list):
                value = [value]
            df = df[col.isin(value)]

    return df


def _execute_filter(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    """Execute filter-only query."""
    return _apply_filters(df, spec.filters or [])


def _execute_aggregate(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    """Execute aggregate query with optional groupby."""
    df = _apply_filters(df, spec.filters or [])

    if not spec.group_by:
        raise QueryError("Aggregate query requires group_by specification")

    group_by = spec.group_by

    # Validate columns
    for field in group_by.fields:
        if field not in df.columns:
            raise QueryError(f"Group column '{field}' not found")

    for agg in group_by.aggregates:
        if agg.field not in df.columns:
            raise QueryError(f"Aggregate column '{agg.field}' not found")

    # Build aggregation dict
    agg_dict: dict[str, tuple[str, str]] = {}
    # Map API function names to pandas aggregation functions
    func_map = {
        "sum": "sum",
        "avg": "mean",  # pandas uses 'mean' not 'avg'
        "min": "min",
        "max": "max",
        "count": "count",
        "distinct": "nunique",
    }
    for agg in group_by.aggregates:
        col_name = agg.alias or f"{agg.field}_{agg.function}"
        pandas_func = func_map.get(agg.function, agg.function)
        agg_dict[col_name] = (agg.field, pandas_func)

    # Execute groupby
    grouped = df.groupby(group_by.fields, as_index=False)
    result = grouped.agg(**agg_dict)

    return result


def _execute_trend(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    """Execute trend query for time-series analysis."""
    df = _apply_filters(df, spec.filters or [])

    if not spec.trend:
        raise QueryError("Trend query requires trend specification")

    trend = spec.trend

    if trend.date_field not in df.columns:
        raise QueryError(f"Date column '{trend.date_field}' not found")
    if trend.value_field not in df.columns:
        raise QueryError(f"Value column '{trend.value_field}' not found")

    # Convert to datetime
    df = df.copy()
    try:
        df[trend.date_field] = pd.to_datetime(df[trend.date_field])
    except Exception:
        raise QueryError(f"Cannot convert '{trend.date_field}' to datetime") from None

    # Set date as index for resampling
    df = df.set_index(trend.date_field)

    # Map interval to pandas frequency
    interval_map = {
        "day": "D",
        "week": "W",
        "month": "ME",
        "quarter": "QE",
        "year": "YE",
    }
    freq = interval_map.get(trend.interval, "ME")

    # Resample and aggregate
    agg_func = trend.aggregate_function
    result = df[[trend.value_field]].resample(freq).agg(agg_func)
    result = result.reset_index()
    result.columns = [trend.date_field, f"{trend.value_field}_{agg_func}"]

    # Convert datetime back to string for JSON
    result[trend.date_field] = result[trend.date_field].dt.strftime("%Y-%m-%d")

    return result


def _execute_compare(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    """Execute comparison query for category analysis."""
    df = _apply_filters(df, spec.filters or [])

    if not spec.compare:
        raise QueryError("Compare query requires compare specification")

    compare = spec.compare

    if compare.group_field not in df.columns:
        raise QueryError(f"Group column '{compare.group_field}' not found")
    if compare.value_field not in df.columns:
        raise QueryError(f"Value column '{compare.value_field}' not found")

    # Group and aggregate
    result = df.groupby(compare.group_field, as_index=False).agg(
        {compare.value_field: compare.aggregate_function}
    )
    result.columns = [compare.group_field, f"{compare.value_field}_{compare.aggregate_function}"]

    # Add percentage if requested
    if compare.comparison_type == "percentage":
        value_col = result.columns[1]
        total = result[value_col].sum()
        if total > 0:
            result["percentage"] = (result[value_col] / total * 100).round(2)
        else:
            result["percentage"] = 0.0

    return result


def _execute_correlate(df: pd.DataFrame, spec: QuerySpec) -> pd.DataFrame:
    """Execute correlation query for column relationship analysis."""
    df = _apply_filters(df, spec.filters or [])

    if not spec.correlate:
        raise QueryError("Correlate query requires correlate specification")

    corr = spec.correlate

    if corr.field_a not in df.columns:
        raise QueryError(f"Column '{corr.field_a}' not found")
    if corr.field_b not in df.columns:
        raise QueryError(f"Column '{corr.field_b}' not found")

    # Ensure numeric
    try:
        col_a = pd.to_numeric(df[corr.field_a], errors="coerce")
        col_b = pd.to_numeric(df[corr.field_b], errors="coerce")
    except Exception:
        raise QueryError("Correlation requires numeric columns") from None

    # Compute correlation
    correlation = col_a.corr(col_b, method=corr.method)

    # Return as single-row DataFrame
    result = pd.DataFrame(
        [
            {
                "field_a": corr.field_a,
                "field_b": corr.field_b,
                "method": corr.method,
                "correlation": round(correlation, 4) if pd.notna(correlation) else None,
            }
        ]
    )

    return result


def execute_query(
    df: pd.DataFrame,
    spec: QuerySpec,
    dataset_id: str | None = None,
    use_cache: bool = True,
) -> QueryResult:
    """Execute a query against a DataFrame.

    Args:
        df: Input DataFrame
        spec: Query specification
        dataset_id: Dataset ID for caching (optional)
        use_cache: Whether to use result caching

    Returns:
        QueryResult with rows, columns, count, pagination info

    Raises:
        QueryError: If query execution fails
    """
    # Check cache
    cache_key = None
    if use_cache and dataset_id:
        query_hash = _compute_query_hash(dataset_id, spec)
        cache_key = f"query_result:{dataset_id}:{query_hash}"
        cached = _get_cached_result(cache_key)
        if cached:
            # Apply pagination to cached result
            start = spec.offset
            end = start + spec.limit
            paginated_rows = cached.rows[start:end]
            return QueryResult(
                rows=paginated_rows,
                columns=cached.columns,
                total_count=cached.total_count,
                has_more=end < cached.total_count,
                query_type=cached.query_type,
            )

    # Execute query by type
    if spec.query_type == "filter":
        result_df = _execute_filter(df, spec)
    elif spec.query_type == "aggregate":
        result_df = _execute_aggregate(df, spec)
    elif spec.query_type == "trend":
        result_df = _execute_trend(df, spec)
    elif spec.query_type == "compare":
        result_df = _execute_compare(df, spec)
    elif spec.query_type == "correlate":
        result_df = _execute_correlate(df, spec)
    else:
        raise QueryError(f"Unknown query type: {spec.query_type}")

    # Convert to records
    # Handle NaN values - convert to None for JSON compatibility
    result_df = result_df.fillna(value="")

    # Convert datetime/Timestamp columns to ISO strings for JSON serialization
    for col in result_df.columns:
        if pd.api.types.is_datetime64_any_dtype(result_df[col]):
            result_df[col] = result_df[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    all_rows = result_df.to_dict(orient="records")
    columns = list(result_df.columns)
    total_count = len(all_rows)

    # Apply pagination
    start = spec.offset
    end = start + spec.limit
    paginated_rows = all_rows[start:end]
    has_more = end < total_count

    result = QueryResult(
        rows=paginated_rows,
        columns=columns,
        total_count=total_count,
        has_more=has_more,
        query_type=spec.query_type,
    )

    # Cache full result (before pagination)
    if cache_key:
        full_result = QueryResult(
            rows=all_rows,
            columns=columns,
            total_count=total_count,
            has_more=False,
            query_type=spec.query_type,
        )
        _cache_result(cache_key, full_result)

    logger.info(
        f"Query executed: type={spec.query_type}, "
        f"total={total_count}, returned={len(paginated_rows)}"
    )

    return result
