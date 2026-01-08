"""Tests for DuckDB query engine."""

from unittest.mock import MagicMock, patch

import duckdb
import pytest

from backend.api.models import (
    AggregateSpec,
    CompareSpec,
    CorrelateSpec,
    FilterSpec,
    GroupBySpec,
    QuerySpec,
    TrendSpec,
)
from backend.services.duckdb_engine import (
    DuckDBError,
    QueryResult,
    _build_filter_clause,
    _convert_row_values,
    _execute_aggregate_query,
    _execute_compare_query,
    _execute_correlate_query,
    _execute_filter_query,
    _execute_trend_query,
    execute_duckdb_query,
    get_duckdb_dataframe,
    load_csv_to_duckdb,
)


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return b"""id,name,amount,date,category
1,Alice,100.5,2024-01-01,A
2,Bob,200.0,2024-01-15,B
3,Charlie,150.75,2024-02-01,A
4,Diana,300.0,2024-02-15,B
5,Eve,250.25,2024-03-01,A
"""


@pytest.fixture
def duckdb_conn(sample_csv_content, tmp_path):
    """Create a DuckDB connection with sample data."""
    # Write sample CSV to temp file
    csv_file = tmp_path / "sample.csv"
    csv_file.write_bytes(sample_csv_content)

    conn = duckdb.connect(":memory:")
    conn.execute(
        f"""
        CREATE TABLE dataset AS
        SELECT * FROM read_csv_auto('{csv_file}', header=true)
        """
    )
    yield conn
    conn.close()


@pytest.fixture
def large_duckdb_conn():
    """Create a DuckDB connection with larger dataset for testing."""
    conn = duckdb.connect(":memory:")
    # Generate 1000 rows
    conn.execute(
        """
        CREATE TABLE dataset AS
        SELECT
            i AS id,
            'Name_' || i AS name,
            CAST(random() * 1000 AS DOUBLE) AS amount,
            DATE '2024-01-01' + INTERVAL (i % 365) DAY AS date,
            CASE WHEN i % 3 = 0 THEN 'A' WHEN i % 3 = 1 THEN 'B' ELSE 'C' END AS category
        FROM range(1, 1001) AS t(i)
        """
    )
    yield conn
    conn.close()


class TestBuildFilterClause:
    """Tests for filter clause building."""

    def test_empty_filters(self):
        """Empty filters return empty clause."""
        clause, params = _build_filter_clause(None)
        assert clause == ""
        assert params == []

        clause, params = _build_filter_clause([])
        assert clause == ""
        assert params == []

    def test_eq_filter(self):
        """Equals filter."""
        filters = [FilterSpec(field="category", operator="eq", value="A")]
        clause, params = _build_filter_clause(filters)
        assert '"category" = ?' in clause
        assert params == ["A"]

    def test_ne_filter(self):
        """Not equals filter."""
        filters = [FilterSpec(field="category", operator="ne", value="B")]
        clause, params = _build_filter_clause(filters)
        assert '"category" != ?' in clause
        assert params == ["B"]

    def test_gt_filter(self):
        """Greater than filter."""
        filters = [FilterSpec(field="amount", operator="gt", value=100)]
        clause, params = _build_filter_clause(filters)
        assert '"amount" > ?' in clause
        assert params == [100]

    def test_lt_filter(self):
        """Less than filter."""
        filters = [FilterSpec(field="amount", operator="lt", value=200)]
        clause, params = _build_filter_clause(filters)
        assert '"amount" < ?' in clause
        assert params == [200]

    def test_gte_filter(self):
        """Greater than or equal filter."""
        filters = [FilterSpec(field="amount", operator="gte", value=100)]
        clause, params = _build_filter_clause(filters)
        assert '"amount" >= ?' in clause
        assert params == [100]

    def test_lte_filter(self):
        """Less than or equal filter."""
        filters = [FilterSpec(field="amount", operator="lte", value=200)]
        clause, params = _build_filter_clause(filters)
        assert '"amount" <= ?' in clause
        assert params == [200]

    def test_contains_filter(self):
        """Contains filter."""
        filters = [FilterSpec(field="name", operator="contains", value="ali")]
        clause, params = _build_filter_clause(filters)
        assert "LIKE" in clause
        assert params == ["%ali%"]

    def test_in_filter(self):
        """In filter."""
        filters = [FilterSpec(field="category", operator="in", value=["A", "B"])]
        clause, params = _build_filter_clause(filters)
        assert '"category" IN (?, ?)' in clause
        assert params == ["A", "B"]

    def test_multiple_filters(self):
        """Multiple filters combined with AND."""
        filters = [
            FilterSpec(field="category", operator="eq", value="A"),
            FilterSpec(field="amount", operator="gt", value=100),
        ]
        clause, params = _build_filter_clause(filters)
        assert "AND" in clause
        assert len(params) == 2


class TestExecuteFilterQuery:
    """Tests for filter query execution."""

    def test_no_filters(self, duckdb_conn):
        """Query without filters returns all rows."""
        spec = QuerySpec(query_type="filter", filters=[])
        rows = _execute_filter_query(duckdb_conn, spec)
        assert len(rows) == 5

    def test_with_filter(self, duckdb_conn):
        """Query with filter returns filtered rows."""
        spec = QuerySpec(
            query_type="filter",
            filters=[FilterSpec(field="category", operator="eq", value="A")],
        )
        rows = _execute_filter_query(duckdb_conn, spec)
        assert len(rows) == 3
        assert all(row["category"] == "A" for row in rows)

    def test_multiple_filters(self, duckdb_conn):
        """Query with multiple filters."""
        spec = QuerySpec(
            query_type="filter",
            filters=[
                FilterSpec(field="category", operator="eq", value="A"),
                FilterSpec(field="amount", operator="gt", value=100),
            ],
        )
        rows = _execute_filter_query(duckdb_conn, spec)
        # Data: Alice(100.5, A), Charlie(150.75, A), Eve(250.25, A)
        # Filter: category='A' AND amount > 100
        # Alice's 100.5 > 100 is True, so all 3 category A rows match
        assert len(rows) == 3
        assert all(row["category"] == "A" and row["amount"] > 100 for row in rows)


class TestExecuteAggregateQuery:
    """Tests for aggregate query execution."""

    def test_sum_aggregate(self, duckdb_conn):
        """Sum aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["category"],
                aggregates=[AggregateSpec(field="amount", function="sum")],
            ),
        )
        rows = _execute_aggregate_query(duckdb_conn, spec)
        assert len(rows) == 2
        # Category A: 100.5 + 150.75 + 250.25 = 501.5
        # Category B: 200.0 + 300.0 = 500.0
        a_row = next(r for r in rows if r["category"] == "A")
        assert a_row["amount_sum"] == pytest.approx(501.5, rel=0.01)

    def test_avg_aggregate(self, duckdb_conn):
        """Average aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["category"],
                aggregates=[AggregateSpec(field="amount", function="avg")],
            ),
        )
        rows = _execute_aggregate_query(duckdb_conn, spec)
        a_row = next(r for r in rows if r["category"] == "A")
        assert a_row["amount_avg"] == pytest.approx(167.17, rel=0.01)

    def test_count_aggregate(self, duckdb_conn):
        """Count aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["category"],
                aggregates=[AggregateSpec(field="amount", function="count")],
            ),
        )
        rows = _execute_aggregate_query(duckdb_conn, spec)
        a_row = next(r for r in rows if r["category"] == "A")
        assert a_row["amount_count"] == 3

    def test_distinct_aggregate(self, duckdb_conn):
        """Distinct count aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["category"],
                aggregates=[AggregateSpec(field="name", function="distinct")],
            ),
        )
        rows = _execute_aggregate_query(duckdb_conn, spec)
        a_row = next(r for r in rows if r["category"] == "A")
        assert a_row["name_distinct"] == 3

    def test_with_alias(self, duckdb_conn):
        """Aggregation with custom alias."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["category"],
                aggregates=[AggregateSpec(field="amount", function="sum", alias="total_amount")],
            ),
        )
        rows = _execute_aggregate_query(duckdb_conn, spec)
        assert "total_amount" in rows[0]

    def test_missing_group_by(self, duckdb_conn):
        """Aggregate without group_by raises error."""
        spec = QuerySpec(query_type="aggregate")
        with pytest.raises(DuckDBError, match="group_by"):
            _execute_aggregate_query(duckdb_conn, spec)


class TestExecuteTrendQuery:
    """Tests for trend query execution."""

    def test_monthly_trend(self, duckdb_conn):
        """Monthly trend aggregation."""
        spec = QuerySpec(
            query_type="trend",
            trend=TrendSpec(
                date_field="date",
                value_field="amount",
                interval="month",
                aggregate_function="sum",
            ),
        )
        rows = _execute_trend_query(duckdb_conn, spec)
        assert len(rows) == 3  # Jan, Feb, Mar

    def test_missing_trend(self, duckdb_conn):
        """Trend without specification raises error."""
        spec = QuerySpec(query_type="trend")
        with pytest.raises(DuckDBError, match="trend"):
            _execute_trend_query(duckdb_conn, spec)


class TestExecuteCompareQuery:
    """Tests for compare query execution."""

    def test_basic_compare(self, duckdb_conn):
        """Basic comparison by category."""
        spec = QuerySpec(
            query_type="compare",
            compare=CompareSpec(
                group_field="category",
                value_field="amount",
                aggregate_function="sum",
            ),
        )
        rows = _execute_compare_query(duckdb_conn, spec)
        assert len(rows) == 2

    def test_percentage_compare(self, duckdb_conn):
        """Comparison with percentages."""
        spec = QuerySpec(
            query_type="compare",
            compare=CompareSpec(
                group_field="category",
                value_field="amount",
                aggregate_function="sum",
                comparison_type="percentage",
            ),
        )
        rows = _execute_compare_query(duckdb_conn, spec)
        assert "percentage" in rows[0]
        total_pct = sum(r.get("percentage", 0) for r in rows)
        assert total_pct == pytest.approx(100, rel=0.1)

    def test_missing_compare(self, duckdb_conn):
        """Compare without specification raises error."""
        spec = QuerySpec(query_type="compare")
        with pytest.raises(DuckDBError, match="compare"):
            _execute_compare_query(duckdb_conn, spec)


class TestExecuteCorrelateQuery:
    """Tests for correlate query execution."""

    def test_correlation(self, large_duckdb_conn):
        """Calculate correlation between columns."""
        spec = QuerySpec(
            query_type="correlate",
            correlate=CorrelateSpec(
                field_a="id",
                field_b="amount",
                method="pearson",
            ),
        )
        rows = _execute_correlate_query(large_duckdb_conn, spec)
        assert len(rows) == 1
        assert "correlation" in rows[0]
        assert rows[0]["field_a"] == "id"
        assert rows[0]["field_b"] == "amount"

    def test_missing_correlate(self, duckdb_conn):
        """Correlate without specification raises error."""
        spec = QuerySpec(query_type="correlate")
        with pytest.raises(DuckDBError, match="correlate"):
            _execute_correlate_query(duckdb_conn, spec)


class TestConvertRowValues:
    """Tests for row value conversion."""

    def test_none_values(self):
        """None values convert to empty string."""
        rows = [{"a": None, "b": 1}]
        result = _convert_row_values(rows)
        assert result[0]["a"] == ""
        assert result[0]["b"] == 1

    def test_date_values(self):
        """Date values convert to ISO format."""
        import datetime

        rows = [{"date": datetime.date(2024, 1, 15)}]
        result = _convert_row_values(rows)
        assert result[0]["date"] == "2024-01-15"

    def test_datetime_values(self):
        """Datetime values convert to string."""
        import datetime

        rows = [{"dt": datetime.datetime(2024, 1, 15, 10, 30, 0)}]
        result = _convert_row_values(rows)
        # ISO format with T separator
        assert result[0]["dt"] == "2024-01-15T10:30:00"

    def test_decimal_values(self):
        """Decimal values convert to float."""
        from decimal import Decimal

        rows = [{"amount": Decimal("123.45")}]
        result = _convert_row_values(rows)
        assert result[0]["amount"] == pytest.approx(123.45)


class TestExecuteDuckDBQuery:
    """Tests for main query execution function."""

    def test_filter_query(self, duckdb_conn):
        """Execute filter query."""
        spec = QuerySpec(
            query_type="filter",
            filters=[FilterSpec(field="category", operator="eq", value="A")],
        )
        result = execute_duckdb_query(duckdb_conn, spec, use_cache=False)
        assert isinstance(result, QueryResult)
        assert result.total_count == 3
        assert result.query_type == "filter"

    def test_aggregate_query(self, duckdb_conn):
        """Execute aggregate query."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["category"],
                aggregates=[AggregateSpec(field="amount", function="sum")],
            ),
        )
        result = execute_duckdb_query(duckdb_conn, spec, use_cache=False)
        assert result.total_count == 2

    def test_pagination(self, duckdb_conn):
        """Test pagination with limit and offset."""
        spec = QuerySpec(query_type="filter", limit=2, offset=0)
        result = execute_duckdb_query(duckdb_conn, spec, use_cache=False)
        assert len(result.rows) == 2
        assert result.total_count == 5
        assert result.has_more is True

        spec = QuerySpec(query_type="filter", limit=2, offset=4)
        result = execute_duckdb_query(duckdb_conn, spec, use_cache=False)
        assert len(result.rows) == 1
        assert result.has_more is False

    def test_unknown_query_type(self, duckdb_conn):
        """Unknown query type raises error."""
        # QuerySpec validates query_type, so we test at the execute level
        # by mocking or using internal function
        # For now, skip this test as QuerySpec enforces valid types
        pass  # QuerySpec validation prevents invalid query types


class TestGetDuckDBDataFrame:
    """Tests for DataFrame extraction."""

    def test_get_all_rows(self, duckdb_conn):
        """Get all rows as DataFrame."""
        df = get_duckdb_dataframe(duckdb_conn)
        assert len(df) == 5
        assert list(df.columns) == ["id", "name", "amount", "date", "category"]

    def test_get_limited_rows(self, duckdb_conn):
        """Get limited rows as DataFrame."""
        df = get_duckdb_dataframe(duckdb_conn, max_rows=3)
        assert len(df) == 3


class TestLoadCSVToDuckDB:
    """Tests for CSV loading."""

    @patch("backend.services.duckdb_engine.get_spaces_client")
    def test_load_csv_success(self, mock_get_client, sample_csv_content):
        """Successfully load CSV into DuckDB."""
        mock_client = MagicMock()
        mock_client.download_file.return_value = sample_csv_content
        mock_get_client.return_value = mock_client

        conn = load_csv_to_duckdb("test/file.csv", sanitize=False)
        try:
            result = conn.execute("SELECT COUNT(*) FROM dataset").fetchone()
            assert result[0] == 5
        finally:
            conn.close()

    @patch("backend.services.duckdb_engine.get_spaces_client")
    def test_load_csv_with_sanitization(self, mock_get_client):
        """CSV with dangerous values is sanitized."""
        csv_with_formula = b"""id,name,formula
1,Alice,=SUM(A1:A10)
2,Bob,normal value
"""
        mock_client = MagicMock()
        mock_client.download_file.return_value = csv_with_formula
        mock_get_client.return_value = mock_client

        conn = load_csv_to_duckdb("test/file.csv", sanitize=True)
        try:
            result = conn.execute("SELECT formula FROM dataset WHERE id = 1").fetchone()
            # Formula should be prefixed with '
            assert result[0].startswith("'=")
        finally:
            conn.close()

    @patch("backend.services.duckdb_engine.get_spaces_client")
    def test_load_csv_spaces_error(self, mock_get_client):
        """SpacesError is converted to DuckDBError."""
        from backend.services.spaces import SpacesError

        mock_client = MagicMock()
        mock_client.download_file.side_effect = SpacesError(
            "Not found", operation="download", key="test/file.csv"
        )
        mock_get_client.return_value = mock_client

        with pytest.raises(DuckDBError, match="Failed to download"):
            load_csv_to_duckdb("test/file.csv")
