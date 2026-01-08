"""Tests for query engine service."""

from unittest.mock import MagicMock, patch

import pandas as pd
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
from backend.services.query_engine import (
    LARGE_DATASET_THRESHOLD,
    QueryError,
    QueryResult,
    execute_query,
    should_use_duckdb,
)


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "age": [25, 30, 35, 28, 32],
            "department": ["Sales", "Engineering", "Sales", "Engineering", "Sales"],
            "salary": [50000, 75000, 60000, 80000, 55000],
            "hire_date": pd.to_datetime(
                ["2020-01-15", "2019-06-20", "2021-03-10", "2020-08-05", "2022-01-01"]
            ),
        }
    )


@pytest.fixture
def sales_df():
    """Create a sales DataFrame for trend testing."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2024-01-15",
                    "2024-01-20",
                    "2024-02-10",
                    "2024-02-25",
                    "2024-03-05",
                    "2024-03-15",
                    "2024-04-01",
                    "2024-04-20",
                ]
            ),
            "amount": [100, 150, 200, 175, 250, 300, 180, 220],
            "category": ["A", "B", "A", "A", "B", "A", "B", "A"],
        }
    )


class TestFilterOperations:
    """Test filter query operations."""

    def test_filter_eq(self, sample_df):
        """Test equality filter."""
        spec = QuerySpec(
            query_type="filter",
            filters=[FilterSpec(field="department", operator="eq", value="Sales")],
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 3
        assert all(r["department"] == "Sales" for r in result.rows)

    def test_filter_ne(self, sample_df):
        """Test not-equal filter."""
        spec = QuerySpec(
            query_type="filter",
            filters=[FilterSpec(field="department", operator="ne", value="Sales")],
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2
        assert all(r["department"] != "Sales" for r in result.rows)

    def test_filter_gt(self, sample_df):
        """Test greater-than filter."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="age", operator="gt", value=30)]
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2
        assert all(r["age"] > 30 for r in result.rows)

    def test_filter_lt(self, sample_df):
        """Test less-than filter."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="salary", operator="lt", value=60000)]
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2

    def test_filter_gte(self, sample_df):
        """Test greater-than-or-equal filter."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="age", operator="gte", value=30)]
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 3

    def test_filter_lte(self, sample_df):
        """Test less-than-or-equal filter."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="age", operator="lte", value=30)]
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 3

    def test_filter_contains(self, sample_df):
        """Test contains filter (case-insensitive)."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="name", operator="contains", value="li")]
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2  # Alice, Charlie

    def test_filter_in(self, sample_df):
        """Test in-list filter."""
        spec = QuerySpec(
            query_type="filter",
            filters=[FilterSpec(field="name", operator="in", value=["Alice", "Bob"])],
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2

    def test_filter_multiple_conditions(self, sample_df):
        """Test multiple filter conditions (AND logic)."""
        spec = QuerySpec(
            query_type="filter",
            filters=[
                FilterSpec(field="department", operator="eq", value="Sales"),
                FilterSpec(field="age", operator="gt", value=26),
            ],
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2  # Charlie and Eve

    def test_filter_invalid_column(self, sample_df):
        """Test filter with invalid column name."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="nonexistent", operator="eq", value="x")]
        )
        with pytest.raises(QueryError, match="not found"):
            execute_query(sample_df, spec, use_cache=False)


class TestAggregateOperations:
    """Test aggregate query operations."""

    def test_aggregate_sum(self, sample_df):
        """Test sum aggregation with groupby."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"], aggregates=[AggregateSpec(field="salary", function="sum")]
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2
        sales_row = next(r for r in result.rows if r["department"] == "Sales")
        assert sales_row["salary_sum"] == 165000  # 50000 + 60000 + 55000

    def test_aggregate_avg(self, sample_df):
        """Test average aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"], aggregates=[AggregateSpec(field="age", function="avg")]
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        eng_row = next(r for r in result.rows if r["department"] == "Engineering")
        assert eng_row["age_avg"] == 29.0  # (30 + 28) / 2

    def test_aggregate_min_max(self, sample_df):
        """Test min/max aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"],
                aggregates=[
                    AggregateSpec(field="salary", function="min"),
                    AggregateSpec(field="salary", function="max"),
                ],
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        sales_row = next(r for r in result.rows if r["department"] == "Sales")
        assert sales_row["salary_min"] == 50000
        assert sales_row["salary_max"] == 60000

    def test_aggregate_count(self, sample_df):
        """Test count aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"], aggregates=[AggregateSpec(field="name", function="count")]
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        sales_row = next(r for r in result.rows if r["department"] == "Sales")
        assert sales_row["name_count"] == 3

    def test_aggregate_distinct(self, sample_df):
        """Test distinct count aggregation."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"], aggregates=[AggregateSpec(field="name", function="distinct")]
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        # All names are unique
        sales_row = next(r for r in result.rows if r["department"] == "Sales")
        assert sales_row["name_distinct"] == 3

    def test_aggregate_with_alias(self, sample_df):
        """Test aggregation with custom alias."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"],
                aggregates=[AggregateSpec(field="salary", function="sum", alias="total_salary")],
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert "total_salary" in result.columns

    def test_aggregate_with_filter(self, sample_df):
        """Test aggregation with pre-filter."""
        spec = QuerySpec(
            query_type="aggregate",
            filters=[FilterSpec(field="age", operator="gt", value=27)],
            group_by=GroupBySpec(
                fields=["department"], aggregates=[AggregateSpec(field="salary", function="sum")]
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        # Only Bob(30), Charlie(35), Diana(28), Eve(32) pass filter
        assert result.total_count == 2

    def test_aggregate_missing_group_by(self, sample_df):
        """Test aggregate query without group_by raises error."""
        spec = QuerySpec(query_type="aggregate")
        with pytest.raises(QueryError, match="requires group_by"):
            execute_query(sample_df, spec, use_cache=False)


class TestTrendOperations:
    """Test trend query operations."""

    def test_trend_monthly(self, sales_df):
        """Test monthly trend aggregation."""
        spec = QuerySpec(
            query_type="trend",
            trend=TrendSpec(
                date_field="date", value_field="amount", interval="month", aggregate_function="sum"
            ),
        )
        result = execute_query(sales_df, spec, use_cache=False)

        assert result.total_count == 4  # Jan, Feb, Mar, Apr
        assert result.query_type == "trend"

    def test_trend_with_filter(self, sales_df):
        """Test trend with category filter."""
        spec = QuerySpec(
            query_type="trend",
            filters=[FilterSpec(field="category", operator="eq", value="A")],
            trend=TrendSpec(date_field="date", value_field="amount", interval="month"),
        )
        result = execute_query(sales_df, spec, use_cache=False)

        # Only category A entries
        assert result.total_count <= 4

    def test_trend_invalid_date_column(self, sample_df):
        """Test trend with non-date column raises error."""
        spec = QuerySpec(
            query_type="trend",
            trend=TrendSpec(
                date_field="name",  # Not a date
                value_field="salary",
                interval="month",
            ),
        )
        with pytest.raises(QueryError, match="(?i)cannot convert"):
            execute_query(sample_df, spec, use_cache=False)

    def test_trend_missing_spec(self, sales_df):
        """Test trend query without spec raises error."""
        spec = QuerySpec(query_type="trend")
        with pytest.raises(QueryError, match="requires trend"):
            execute_query(sales_df, spec, use_cache=False)


class TestCompareOperations:
    """Test compare query operations."""

    def test_compare_absolute(self, sample_df):
        """Test absolute comparison."""
        spec = QuerySpec(
            query_type="compare",
            compare=CompareSpec(
                group_field="department",
                value_field="salary",
                comparison_type="absolute",
                aggregate_function="sum",
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 2
        assert "salary_sum" in result.columns

    def test_compare_percentage(self, sample_df):
        """Test percentage comparison."""
        spec = QuerySpec(
            query_type="compare",
            compare=CompareSpec(
                group_field="department",
                value_field="salary",
                comparison_type="percentage",
                aggregate_function="sum",
            ),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert "percentage" in result.columns
        # Percentages should sum to ~100
        total_pct = sum(r["percentage"] for r in result.rows)
        assert abs(total_pct - 100) < 0.1

    def test_compare_missing_spec(self, sample_df):
        """Test compare query without spec raises error."""
        spec = QuerySpec(query_type="compare")
        with pytest.raises(QueryError, match="requires compare"):
            execute_query(sample_df, spec, use_cache=False)


class TestCorrelateOperations:
    """Test correlate query operations."""

    def test_correlate_pearson(self, sample_df):
        """Test Pearson correlation."""
        spec = QuerySpec(
            query_type="correlate",
            correlate=CorrelateSpec(field_a="age", field_b="salary", method="pearson"),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.total_count == 1
        assert "correlation" in result.columns
        assert result.rows[0]["method"] == "pearson"

    def test_correlate_spearman(self, sample_df):
        """Test Spearman correlation."""
        spec = QuerySpec(
            query_type="correlate",
            correlate=CorrelateSpec(field_a="age", field_b="salary", method="spearman"),
        )
        result = execute_query(sample_df, spec, use_cache=False)

        assert result.rows[0]["method"] == "spearman"

    def test_correlate_missing_spec(self, sample_df):
        """Test correlate query without spec raises error."""
        spec = QuerySpec(query_type="correlate")
        with pytest.raises(QueryError, match="requires correlate"):
            execute_query(sample_df, spec, use_cache=False)


class TestPagination:
    """Test query pagination."""

    def test_pagination_limit(self, sample_df):
        """Test limit pagination."""
        spec = QuerySpec(query_type="filter", limit=2)
        result = execute_query(sample_df, spec, use_cache=False)

        assert len(result.rows) == 2
        assert result.total_count == 5
        assert result.has_more is True

    def test_pagination_offset(self, sample_df):
        """Test offset pagination."""
        spec = QuerySpec(query_type="filter", limit=2, offset=3)
        result = execute_query(sample_df, spec, use_cache=False)

        assert len(result.rows) == 2
        assert result.total_count == 5
        assert result.has_more is False

    def test_pagination_no_more(self, sample_df):
        """Test has_more=False when at end."""
        spec = QuerySpec(query_type="filter", limit=10)
        result = execute_query(sample_df, spec, use_cache=False)

        assert len(result.rows) == 5
        assert result.has_more is False


class TestCaching:
    """Test query result caching."""

    @patch("backend.services.query_engine.RedisManager")
    def test_cache_miss_then_hit(self, mock_redis_manager, sample_df):
        """Test cache miss followed by cache hit."""
        mock_client = MagicMock()
        mock_client.get.return_value = None  # Cache miss
        mock_redis_manager.return_value.client = mock_client

        spec = QuerySpec(query_type="filter", limit=2)
        execute_query(sample_df, spec, dataset_id="test-123", use_cache=True)

        # Should have called setex to cache result
        assert mock_client.setex.called

    @patch("backend.services.query_engine.RedisManager")
    def test_cache_disabled(self, mock_redis_manager, sample_df):
        """Test caching can be disabled."""
        mock_client = MagicMock()
        mock_redis_manager.return_value.client = mock_client

        spec = QuerySpec(query_type="filter")
        execute_query(sample_df, spec, use_cache=False)

        # Should not access Redis
        assert not mock_client.get.called


class TestQueryResult:
    """Test QueryResult dataclass."""

    def test_query_result_structure(self, sample_df):
        """Test QueryResult has correct structure."""
        spec = QuerySpec(query_type="filter")
        result = execute_query(sample_df, spec, use_cache=False)

        assert isinstance(result, QueryResult)
        assert isinstance(result.rows, list)
        assert isinstance(result.columns, list)
        assert isinstance(result.total_count, int)
        assert isinstance(result.has_more, bool)
        assert isinstance(result.query_type, str)


class TestBackendSelection:
    """Test DuckDB vs pandas backend selection."""

    def test_should_use_duckdb_small_dataset(self):
        """Small datasets should use pandas."""
        assert should_use_duckdb(1000) is False
        assert should_use_duckdb(50000) is False
        assert should_use_duckdb(99999) is False

    def test_should_use_duckdb_large_dataset(self):
        """Large datasets should use DuckDB."""
        assert should_use_duckdb(100000) is True
        assert should_use_duckdb(150000) is True
        assert should_use_duckdb(1000000) is True

    def test_should_use_duckdb_at_threshold(self):
        """Datasets at threshold should use DuckDB (>= not >)."""
        assert should_use_duckdb(LARGE_DATASET_THRESHOLD) is True
        assert should_use_duckdb(LARGE_DATASET_THRESHOLD - 1) is False

    def test_threshold_value(self):
        """Verify threshold is 100K."""
        assert LARGE_DATASET_THRESHOLD == 100_000
