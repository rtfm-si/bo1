"""DuckDB query engine for large dataset operations.

Provides efficient SQL-based queries for datasets >100K rows using DuckDB's
in-memory columnar storage. Implements the same query interface as pandas
query_engine for drop-in compatibility.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

import duckdb
import pandas as pd

from backend.api.models import (
    FilterSpec,
    QuerySpec,
)
from backend.services.spaces import SpacesError, get_spaces_client
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Cache TTL for query results (5 minutes)
QUERY_CACHE_TTL = 300


class DuckDBError(Exception):
    """Error during DuckDB operations."""

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
    content = f"duckdb:{dataset_id}:{spec_json}"
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


def load_csv_to_duckdb(file_key: str, sanitize: bool = True) -> duckdb.DuckDBPyConnection:
    """Load CSV from Spaces directly into DuckDB in-memory table.

    Args:
        file_key: Spaces object key
        sanitize: If True, sanitize cell values after loading

    Returns:
        DuckDB connection with 'dataset' table populated

    Raises:
        DuckDBError: If loading fails
    """
    import tempfile

    try:
        spaces_client = get_spaces_client()
        content = spaces_client.download_file(file_key)
    except SpacesError as e:
        raise DuckDBError(f"Failed to download {file_key}: {e}") from e

    # Create in-memory DuckDB connection
    conn = duckdb.connect(":memory:")

    # Write content to temp file for DuckDB to read (more compatible than BytesIO)
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Try UTF-8 first, fallback to latin-1
        for encoding in ["utf-8", "latin-1"]:
            try:
                # Load CSV from temp file
                conn.execute(
                    f"""
                    CREATE TABLE dataset AS
                    SELECT * FROM read_csv_auto('{tmp_path}', header=true, sample_size=-1)
                    """
                )
                logger.info(f"Loaded {file_key} into DuckDB ({encoding})")
                break
            except duckdb.InvalidInputException:
                # If UTF-8 fails, try latin-1
                if encoding == "latin-1":
                    raise DuckDBError(f"Failed to decode {file_key} with any encoding") from None
                continue
            except Exception as e:
                raise DuckDBError(f"DuckDB load error: {e}") from e
    finally:
        # Clean up temp file
        import os

        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    # Get row count
    row_count = conn.execute("SELECT COUNT(*) FROM dataset").fetchone()[0]
    col_count = len(conn.execute("DESCRIBE dataset").fetchall())
    logger.info(f"DuckDB table created: {row_count} rows, {col_count} columns")

    # Sanitize string columns to prevent formula injection
    if sanitize:
        _sanitize_duckdb_table(conn)

    return conn


def _sanitize_duckdb_table(conn: duckdb.DuckDBPyConnection) -> None:
    """Sanitize string columns in DuckDB table to prevent formula injection."""
    # Get string columns
    columns = conn.execute("DESCRIBE dataset").fetchall()
    string_cols = [col[0] for col in columns if "VARCHAR" in str(col[1]).upper()]

    if not string_cols:
        return

    # For each string column, update values that start with dangerous characters
    for col in string_cols:
        # Quote column name to handle special characters
        quoted_col = f'"{col}"'
        # In DuckDB, string literals use single quotes, and to include a literal single quote
        # in a string, double it ('')
        conn.execute(
            f"""
            UPDATE dataset
            SET {quoted_col} = CASE
                WHEN LEFT({quoted_col}, 1) IN ('=', '+', '-', '@', chr(9), chr(13))
                THEN '''' || {quoted_col}
                ELSE {quoted_col}
            END
            WHERE {quoted_col} IS NOT NULL
            """
        )

    logger.debug("Sanitized string columns in DuckDB table")


def get_row_count(file_key: str) -> int:
    """Get row count from CSV file efficiently using DuckDB.

    Args:
        file_key: Spaces object key

    Returns:
        Number of rows in the CSV

    Raises:
        DuckDBError: If counting fails
    """
    import tempfile

    try:
        spaces_client = get_spaces_client()
        content = spaces_client.download_file(file_key)
    except SpacesError as e:
        raise DuckDBError(f"Failed to download {file_key}: {e}") from e

    conn = duckdb.connect(":memory:")

    # Write content to temp file for DuckDB to read
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = conn.execute(
            f"SELECT COUNT(*) FROM read_csv_auto('{tmp_path}', header=true)"
        ).fetchone()
        count = result[0] if result else 0
        logger.debug(f"Row count for {file_key}: {count}")
        return count
    except Exception as e:
        raise DuckDBError(f"Failed to count rows: {e}") from e
    finally:
        conn.close()
        # Clean up temp file
        import os

        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _build_filter_clause(filters: list[FilterSpec] | None) -> tuple[str, list[Any]]:
    """Build SQL WHERE clause from filters.

    Returns:
        Tuple of (SQL clause string, parameter values list)
    """
    if not filters:
        return "", []

    clauses = []
    params = []

    for f in filters:
        # Quote column name to handle special characters
        col = f'"{f.field}"'

        if f.operator == "eq":
            clauses.append(f"{col} = ?")
            params.append(f.value)
        elif f.operator == "ne":
            clauses.append(f"{col} != ?")
            params.append(f.value)
        elif f.operator == "gt":
            clauses.append(f"{col} > ?")
            params.append(f.value)
        elif f.operator == "lt":
            clauses.append(f"{col} < ?")
            params.append(f.value)
        elif f.operator == "gte":
            clauses.append(f"{col} >= ?")
            params.append(f.value)
        elif f.operator == "lte":
            clauses.append(f"{col} <= ?")
            params.append(f.value)
        elif f.operator == "contains":
            clauses.append(f"LOWER(CAST({col} AS VARCHAR)) LIKE ?")
            params.append(f"%{str(f.value).lower()}%")
        elif f.operator == "in":
            values = f.value if isinstance(f.value, list) else [f.value]
            placeholders = ", ".join(["?" for _ in values])
            clauses.append(f"{col} IN ({placeholders})")
            params.extend(values)

    where_clause = " AND ".join(clauses) if clauses else ""
    return where_clause, params


def _execute_filter_query(conn: duckdb.DuckDBPyConnection, spec: QuerySpec) -> list[dict[str, Any]]:
    """Execute filter-only query."""
    where_clause, params = _build_filter_clause(spec.filters)

    sql = "SELECT * FROM dataset"
    if where_clause:
        sql += f" WHERE {where_clause}"

    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    return rows


def _execute_aggregate_query(
    conn: duckdb.DuckDBPyConnection, spec: QuerySpec
) -> list[dict[str, Any]]:
    """Execute aggregate query with groupby."""
    if not spec.group_by:
        raise DuckDBError("Aggregate query requires group_by specification")

    group_by = spec.group_by
    where_clause, params = _build_filter_clause(spec.filters)

    # Build SELECT clause with aggregations
    # Map API function names to SQL functions
    func_map = {
        "sum": "SUM",
        "avg": "AVG",
        "min": "MIN",
        "max": "MAX",
        "count": "COUNT",
        "distinct": "COUNT(DISTINCT",
    }

    select_parts = [f'"{f}"' for f in group_by.fields]

    for agg in group_by.aggregates:
        sql_func = func_map.get(agg.function, agg.function.upper())
        alias = agg.alias or f"{agg.field}_{agg.function}"
        quoted_field = f'"{agg.field}"'

        if agg.function == "distinct":
            select_parts.append(f'{sql_func} {quoted_field}) AS "{alias}"')
        else:
            select_parts.append(f'{sql_func}({quoted_field}) AS "{alias}"')

    select_clause = ", ".join(select_parts)
    group_clause = ", ".join([f'"{f}"' for f in group_by.fields])

    sql = f"SELECT {select_clause} FROM dataset"
    if where_clause:
        sql += f" WHERE {where_clause}"
    sql += f" GROUP BY {group_clause}"

    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    return rows


def _execute_trend_query(conn: duckdb.DuckDBPyConnection, spec: QuerySpec) -> list[dict[str, Any]]:
    """Execute trend query for time-series analysis."""
    if not spec.trend:
        raise DuckDBError("Trend query requires trend specification")

    trend = spec.trend
    where_clause, params = _build_filter_clause(spec.filters)

    # Map interval to DuckDB date_trunc intervals
    interval_map = {
        "day": "day",
        "week": "week",
        "month": "month",
        "quarter": "quarter",
        "year": "year",
    }
    interval = interval_map.get(trend.interval, "month")

    # Map aggregate function
    agg_func = trend.aggregate_function.upper()
    date_col = f'"{trend.date_field}"'
    value_col = f'"{trend.value_field}"'
    result_value_col = f"{trend.value_field}_{trend.aggregate_function}"

    sql = f"""
        SELECT
            DATE_TRUNC('{interval}', TRY_CAST({date_col} AS DATE)) AS {date_col},
            {agg_func}({value_col}) AS "{result_value_col}"
        FROM dataset
    """

    if where_clause:
        sql += f" WHERE {where_clause}"

    sql += f"""
        GROUP BY DATE_TRUNC('{interval}', TRY_CAST({date_col} AS DATE))
        ORDER BY 1
    """

    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = []
    for row in result.fetchall():
        row_dict = dict(zip(columns, row, strict=True))
        # Convert date to string format
        if row_dict.get(trend.date_field) is not None:
            row_dict[trend.date_field] = str(row_dict[trend.date_field])[:10]
        rows.append(row_dict)

    return rows


def _execute_compare_query(
    conn: duckdb.DuckDBPyConnection, spec: QuerySpec
) -> list[dict[str, Any]]:
    """Execute comparison query for category analysis."""
    if not spec.compare:
        raise DuckDBError("Compare query requires compare specification")

    compare = spec.compare
    where_clause, params = _build_filter_clause(spec.filters)

    agg_func = compare.aggregate_function.upper()
    group_col = f'"{compare.group_field}"'
    value_col = f'"{compare.value_field}"'
    result_value_col = f"{compare.value_field}_{compare.aggregate_function}"

    if compare.comparison_type == "percentage":
        # Include percentage calculation
        sql = f"""
            WITH totals AS (
                SELECT {agg_func}({value_col}) AS total FROM dataset
                {f"WHERE {where_clause}" if where_clause else ""}
            )
            SELECT
                {group_col},
                {agg_func}({value_col}) AS "{result_value_col}",
                ROUND({agg_func}({value_col}) * 100.0 / NULLIF(totals.total, 0), 2) AS percentage
            FROM dataset, totals
            {f"WHERE {where_clause}" if where_clause else ""}
            GROUP BY {group_col}, totals.total
        """
    else:
        sql = f"""
            SELECT
                {group_col},
                {agg_func}({value_col}) AS "{result_value_col}"
            FROM dataset
        """
        if where_clause:
            sql += f" WHERE {where_clause}"
        sql += f" GROUP BY {group_col}"

    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    return rows


def _execute_correlate_query(
    conn: duckdb.DuckDBPyConnection, spec: QuerySpec
) -> list[dict[str, Any]]:
    """Execute correlation query for column relationship analysis."""
    if not spec.correlate:
        raise DuckDBError("Correlate query requires correlate specification")

    corr = spec.correlate
    where_clause, params = _build_filter_clause(spec.filters)

    col_a = f'"{corr.field_a}"'
    col_b = f'"{corr.field_b}"'

    # DuckDB supports CORR() aggregate function
    sql = f"""
        SELECT
            '{corr.field_a}' AS field_a,
            '{corr.field_b}' AS field_b,
            '{corr.method}' AS method,
            ROUND(CORR(CAST({col_a} AS DOUBLE), CAST({col_b} AS DOUBLE)), 4) AS correlation
        FROM dataset
    """
    if where_clause:
        sql += f" WHERE {where_clause}"

    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    rows = [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    return rows


def _convert_row_values(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert DuckDB values to JSON-compatible types."""
    import datetime
    from decimal import Decimal

    converted = []
    for row in rows:
        new_row = {}
        for k, v in row.items():
            if v is None:
                new_row[k] = ""
            elif isinstance(v, datetime.datetime):
                # datetime must be checked before date since datetime is a subclass of date
                new_row[k] = v.isoformat()
            elif isinstance(v, datetime.date):
                new_row[k] = v.isoformat()
            elif isinstance(v, Decimal):
                new_row[k] = float(v)
            elif hasattr(v, "item"):  # numpy types
                new_row[k] = v.item()
            else:
                new_row[k] = v
        converted.append(new_row)
    return converted


def execute_duckdb_query(
    conn: duckdb.DuckDBPyConnection,
    spec: QuerySpec,
    dataset_id: str | None = None,
    use_cache: bool = True,
) -> QueryResult:
    """Execute a query against a DuckDB connection.

    Args:
        conn: DuckDB connection with 'dataset' table
        spec: Query specification
        dataset_id: Dataset ID for caching (optional)
        use_cache: Whether to use result caching

    Returns:
        QueryResult with rows, columns, count, pagination info

    Raises:
        DuckDBError: If query execution fails
    """
    # Check cache
    cache_key = None
    if use_cache and dataset_id:
        query_hash = _compute_query_hash(dataset_id, spec)
        cache_key = f"duckdb_query_result:{dataset_id}:{query_hash}"
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
    try:
        if spec.query_type == "filter":
            rows = _execute_filter_query(conn, spec)
        elif spec.query_type == "aggregate":
            rows = _execute_aggregate_query(conn, spec)
        elif spec.query_type == "trend":
            rows = _execute_trend_query(conn, spec)
        elif spec.query_type == "compare":
            rows = _execute_compare_query(conn, spec)
        elif spec.query_type == "correlate":
            rows = _execute_correlate_query(conn, spec)
        else:
            raise DuckDBError(f"Unknown query type: {spec.query_type}")
    except duckdb.Error as e:
        raise DuckDBError(f"Query execution failed: {e}") from e

    # Convert values for JSON compatibility
    all_rows = _convert_row_values(rows)
    columns = list(all_rows[0].keys()) if all_rows else []
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
        f"DuckDB query executed: type={spec.query_type}, "
        f"total={total_count}, returned={len(paginated_rows)}"
    )

    return result


def get_duckdb_dataframe(
    conn: duckdb.DuckDBPyConnection, max_rows: int | None = None
) -> pd.DataFrame:
    """Get pandas DataFrame from DuckDB table.

    Useful for chart generation that requires a DataFrame.

    Args:
        conn: DuckDB connection with 'dataset' table
        max_rows: Maximum rows to return (None for all)

    Returns:
        pandas DataFrame
    """
    sql = "SELECT * FROM dataset"
    if max_rows:
        sql += f" LIMIT {max_rows}"

    return conn.execute(sql).df()
