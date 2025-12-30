"""Tests for datasets API models and schemas."""

import pytest

from backend.api.models import (
    AggregateSpec,
    CompareSpec,
    CorrelateSpec,
    DatasetCreate,
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetProfileResponse,
    DatasetResponse,
    FilterSpec,
    GroupBySpec,
    ImportSheetsRequest,
    QueryResultResponse,
    QuerySpec,
    TrendSpec,
)


class TestDatasetModels:
    """Test Dataset Pydantic models."""

    def test_dataset_create_minimal(self):
        """Test DatasetCreate with minimal fields."""
        dataset = DatasetCreate(name="Test Dataset")
        assert dataset.name == "Test Dataset"
        assert dataset.source_type == "csv"
        assert dataset.description is None
        assert dataset.source_uri is None

    def test_dataset_create_full(self):
        """Test DatasetCreate with all fields."""
        dataset = DatasetCreate(
            name="Sales Q4",
            description="Quarterly sales data",
            source_type="sheets",
            source_uri="https://docs.google.com/spreadsheets/d/abc123",
        )
        assert dataset.name == "Sales Q4"
        assert dataset.description == "Quarterly sales data"
        assert dataset.source_type == "sheets"
        assert dataset.source_uri == "https://docs.google.com/spreadsheets/d/abc123"

    def test_dataset_create_invalid_source_type(self):
        """Test DatasetCreate rejects invalid source type."""
        with pytest.raises(ValueError):
            DatasetCreate(name="Test", source_type="invalid")

    def test_dataset_create_name_too_long(self):
        """Test DatasetCreate rejects name over 255 chars."""
        with pytest.raises(ValueError):
            DatasetCreate(name="x" * 256)

    def test_dataset_create_name_empty(self):
        """Test DatasetCreate rejects empty name."""
        with pytest.raises(ValueError):
            DatasetCreate(name="")


class TestDatasetResponseModels:
    """Test Dataset response models."""

    def test_dataset_response_creation(self):
        """Test DatasetResponse model creation."""
        response = DatasetResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            row_count=1000,
            column_count=5,
            file_size_bytes=50000,
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        assert response.id == "550e8400-e29b-41d4-a716-446655440000"
        assert response.name == "Sales Data"
        assert response.row_count == 1000

    def test_dataset_response_optional_fields(self):
        """Test DatasetResponse with optional fields as None."""
        response = DatasetResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        assert response.description is None
        assert response.file_key is None
        assert response.row_count is None
        assert response.warnings is None

    def test_dataset_response_with_warnings(self):
        """Test DatasetResponse with CSV injection warnings."""
        response = DatasetResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
            warnings=["Detected 3 cell(s) with formula injection prefixes"],
        )
        assert response.warnings is not None
        assert len(response.warnings) == 1
        assert "formula injection" in response.warnings[0]


class TestDatasetProfileModels:
    """Test DatasetProfile response model."""

    def test_profile_response_creation(self):
        """Test DatasetProfileResponse model creation."""
        profile = DatasetProfileResponse(
            id="660e8400-e29b-41d4-a716-446655440001",
            column_name="revenue",
            data_type="float",
            null_count=5,
            unique_count=950,
            min_value="100.00",
            max_value="99999.99",
            mean_value=5432.10,
            sample_values=[100.00, 500.00, 1000.00],
        )
        assert profile.column_name == "revenue"
        assert profile.data_type == "float"
        assert profile.mean_value == 5432.10

    def test_profile_response_minimal(self):
        """Test DatasetProfileResponse with minimal fields."""
        profile = DatasetProfileResponse(
            id="660e8400-e29b-41d4-a716-446655440001",
            column_name="id",
            data_type="integer",
        )
        assert profile.column_name == "id"
        assert profile.null_count is None
        assert profile.sample_values is None


class TestDatasetDetailResponse:
    """Test DatasetDetailResponse model."""

    def test_detail_response_with_profiles(self):
        """Test DatasetDetailResponse with profiles."""
        profiles = [
            DatasetProfileResponse(
                id="p1",
                column_name="revenue",
                data_type="float",
            ),
            DatasetProfileResponse(
                id="p2",
                column_name="date",
                data_type="date",
            ),
        ]
        detail = DatasetDetailResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
            profiles=profiles,
        )
        assert len(detail.profiles) == 2
        assert detail.profiles[0].column_name == "revenue"

    def test_detail_response_empty_profiles(self):
        """Test DatasetDetailResponse defaults to empty profiles."""
        detail = DatasetDetailResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="test_user_1",
            name="Sales Data",
            source_type="csv",
            created_at="2025-12-10T10:00:00+00:00",
            updated_at="2025-12-10T10:00:00+00:00",
        )
        assert detail.profiles == []


class TestDatasetListResponse:
    """Test DatasetListResponse model."""

    def test_list_response_creation(self):
        """Test DatasetListResponse model creation."""
        datasets = [
            DatasetResponse(
                id="d1",
                user_id="u1",
                name="Dataset 1",
                source_type="csv",
                created_at="2025-12-10T10:00:00+00:00",
                updated_at="2025-12-10T10:00:00+00:00",
            ),
            DatasetResponse(
                id="d2",
                user_id="u1",
                name="Dataset 2",
                source_type="sheets",
                created_at="2025-12-10T11:00:00+00:00",
                updated_at="2025-12-10T11:00:00+00:00",
            ),
        ]
        response = DatasetListResponse(
            datasets=datasets,
            total=50,
            limit=10,
            offset=0,
            has_more=True,
            next_offset=10,
        )
        assert len(response.datasets) == 2
        assert response.total == 50
        assert response.limit == 10
        assert response.offset == 0
        assert response.has_more is True
        assert response.next_offset == 10

    def test_list_response_empty(self):
        """Test DatasetListResponse with empty datasets."""
        response = DatasetListResponse(
            datasets=[],
            total=0,
            limit=50,
            offset=0,
            has_more=False,
            next_offset=None,
        )
        assert response.datasets == []
        assert response.total == 0
        assert response.has_more is False
        assert response.next_offset is None


# =============================================================================
# Query Model Tests (EPIC 3)
# =============================================================================


class TestFilterSpecModel:
    """Test FilterSpec model validation."""

    def test_filter_spec_valid(self):
        """Test FilterSpec with valid data."""
        spec = FilterSpec(field="age", operator="gt", value=30)
        assert spec.field == "age"
        assert spec.operator == "gt"
        assert spec.value == 30

    def test_filter_spec_all_operators(self):
        """Test all valid filter operators."""
        operators = ["eq", "ne", "gt", "lt", "gte", "lte", "contains", "in"]
        for op in operators:
            spec = FilterSpec(field="test", operator=op, value="x")
            assert spec.operator == op

    def test_filter_spec_invalid_operator(self):
        """Test FilterSpec rejects invalid operator."""
        with pytest.raises(ValueError):
            FilterSpec(field="test", operator="invalid", value="x")

    def test_filter_spec_empty_field(self):
        """Test FilterSpec rejects empty field."""
        with pytest.raises(ValueError):
            FilterSpec(field="", operator="eq", value="x")


class TestAggregateSpecModel:
    """Test AggregateSpec model validation."""

    def test_aggregate_spec_valid(self):
        """Test AggregateSpec with valid data."""
        spec = AggregateSpec(field="salary", function="sum")
        assert spec.field == "salary"
        assert spec.function == "sum"
        assert spec.alias is None

    def test_aggregate_spec_with_alias(self):
        """Test AggregateSpec with alias."""
        spec = AggregateSpec(field="salary", function="avg", alias="avg_salary")
        assert spec.alias == "avg_salary"

    def test_aggregate_spec_all_functions(self):
        """Test all valid aggregate functions."""
        functions = ["sum", "avg", "min", "max", "count", "distinct"]
        for func in functions:
            spec = AggregateSpec(field="test", function=func)
            assert spec.function == func

    def test_aggregate_spec_invalid_function(self):
        """Test AggregateSpec rejects invalid function."""
        with pytest.raises(ValueError):
            AggregateSpec(field="test", function="invalid")


class TestGroupBySpecModel:
    """Test GroupBySpec model validation."""

    def test_group_by_spec_valid(self):
        """Test GroupBySpec with valid data."""
        spec = GroupBySpec(
            fields=["department"], aggregates=[AggregateSpec(field="salary", function="sum")]
        )
        assert spec.fields == ["department"]
        assert len(spec.aggregates) == 1

    def test_group_by_spec_multiple_fields(self):
        """Test GroupBySpec with multiple groupby fields."""
        spec = GroupBySpec(
            fields=["department", "year"],
            aggregates=[
                AggregateSpec(field="salary", function="sum"),
                AggregateSpec(field="bonus", function="avg"),
            ],
        )
        assert len(spec.fields) == 2
        assert len(spec.aggregates) == 2


class TestTrendSpecModel:
    """Test TrendSpec model validation."""

    def test_trend_spec_valid(self):
        """Test TrendSpec with valid data."""
        spec = TrendSpec(date_field="date", value_field="revenue")
        assert spec.date_field == "date"
        assert spec.value_field == "revenue"
        assert spec.interval == "month"  # default
        assert spec.aggregate_function == "sum"  # default

    def test_trend_spec_all_intervals(self):
        """Test all valid trend intervals."""
        intervals = ["day", "week", "month", "quarter", "year"]
        for interval in intervals:
            spec = TrendSpec(date_field="date", value_field="amount", interval=interval)
            assert spec.interval == interval

    def test_trend_spec_invalid_interval(self):
        """Test TrendSpec rejects invalid interval."""
        with pytest.raises(ValueError):
            TrendSpec(date_field="date", value_field="amount", interval="invalid")


class TestCompareSpecModel:
    """Test CompareSpec model validation."""

    def test_compare_spec_valid(self):
        """Test CompareSpec with valid data."""
        spec = CompareSpec(group_field="category", value_field="sales")
        assert spec.group_field == "category"
        assert spec.value_field == "sales"
        assert spec.comparison_type == "absolute"  # default
        assert spec.aggregate_function == "sum"  # default

    def test_compare_spec_percentage(self):
        """Test CompareSpec with percentage comparison."""
        spec = CompareSpec(
            group_field="category", value_field="sales", comparison_type="percentage"
        )
        assert spec.comparison_type == "percentage"

    def test_compare_spec_invalid_type(self):
        """Test CompareSpec rejects invalid comparison type."""
        with pytest.raises(ValueError):
            CompareSpec(group_field="category", value_field="sales", comparison_type="invalid")


class TestCorrelateSpecModel:
    """Test CorrelateSpec model validation."""

    def test_correlate_spec_valid(self):
        """Test CorrelateSpec with valid data."""
        spec = CorrelateSpec(field_a="age", field_b="salary")
        assert spec.field_a == "age"
        assert spec.field_b == "salary"
        assert spec.method == "pearson"  # default

    def test_correlate_spec_spearman(self):
        """Test CorrelateSpec with Spearman method."""
        spec = CorrelateSpec(field_a="age", field_b="salary", method="spearman")
        assert spec.method == "spearman"

    def test_correlate_spec_invalid_method(self):
        """Test CorrelateSpec rejects invalid method."""
        with pytest.raises(ValueError):
            CorrelateSpec(field_a="age", field_b="salary", method="invalid")


class TestQuerySpecModel:
    """Test QuerySpec model validation."""

    def test_query_spec_filter(self):
        """Test QuerySpec for filter query."""
        spec = QuerySpec(
            query_type="filter", filters=[FilterSpec(field="age", operator="gt", value=25)]
        )
        assert spec.query_type == "filter"
        assert len(spec.filters) == 1

    def test_query_spec_aggregate(self):
        """Test QuerySpec for aggregate query."""
        spec = QuerySpec(
            query_type="aggregate",
            group_by=GroupBySpec(
                fields=["department"], aggregates=[AggregateSpec(field="salary", function="sum")]
            ),
        )
        assert spec.query_type == "aggregate"
        assert spec.group_by is not None

    def test_query_spec_trend(self):
        """Test QuerySpec for trend query."""
        spec = QuerySpec(
            query_type="trend", trend=TrendSpec(date_field="date", value_field="revenue")
        )
        assert spec.query_type == "trend"
        assert spec.trend is not None

    def test_query_spec_compare(self):
        """Test QuerySpec for compare query."""
        spec = QuerySpec(
            query_type="compare", compare=CompareSpec(group_field="category", value_field="sales")
        )
        assert spec.query_type == "compare"

    def test_query_spec_correlate(self):
        """Test QuerySpec for correlate query."""
        spec = QuerySpec(
            query_type="correlate", correlate=CorrelateSpec(field_a="age", field_b="salary")
        )
        assert spec.query_type == "correlate"

    def test_query_spec_invalid_type(self):
        """Test QuerySpec rejects invalid query type."""
        with pytest.raises(ValueError):
            QuerySpec(query_type="invalid")

    def test_query_spec_pagination_defaults(self):
        """Test QuerySpec has correct pagination defaults."""
        spec = QuerySpec(query_type="filter")
        assert spec.limit == 100
        assert spec.offset == 0

    def test_query_spec_pagination_custom(self):
        """Test QuerySpec with custom pagination."""
        spec = QuerySpec(query_type="filter", limit=50, offset=100)
        assert spec.limit == 50
        assert spec.offset == 100

    def test_query_spec_limit_max(self):
        """Test QuerySpec enforces maximum limit."""
        with pytest.raises(ValueError):
            QuerySpec(query_type="filter", limit=1001)

    def test_query_spec_limit_min(self):
        """Test QuerySpec enforces minimum limit."""
        with pytest.raises(ValueError):
            QuerySpec(query_type="filter", limit=0)

    def test_query_spec_offset_min(self):
        """Test QuerySpec enforces minimum offset."""
        with pytest.raises(ValueError):
            QuerySpec(query_type="filter", offset=-1)


class TestQueryResultResponseModel:
    """Test QueryResultResponse model."""

    def test_query_result_response_valid(self):
        """Test QueryResultResponse with valid data."""
        response = QueryResultResponse(
            rows=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            columns=["name", "age"],
            total_count=100,
            has_more=True,
            query_type="filter",
        )
        assert len(response.rows) == 2
        assert response.columns == ["name", "age"]
        assert response.total_count == 100
        assert response.has_more is True
        assert response.query_type == "filter"

    def test_query_result_response_empty(self):
        """Test QueryResultResponse with empty results."""
        response = QueryResultResponse(
            rows=[], columns=[], total_count=0, has_more=False, query_type="filter"
        )
        assert response.rows == []
        assert response.total_count == 0


# =============================================================================
# ImportSheetsRequest Model Tests (EPIC 1)
# =============================================================================


class TestImportSheetsRequestModel:
    """Test ImportSheetsRequest model validation."""

    def test_import_sheets_request_valid(self):
        """Test ImportSheetsRequest with valid data."""
        request = ImportSheetsRequest(
            url="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
        )
        assert (
            request.url
            == "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
        )
        assert request.name is None
        assert request.description is None

    def test_import_sheets_request_with_name(self):
        """Test ImportSheetsRequest with custom name."""
        request = ImportSheetsRequest(
            url="https://docs.google.com/spreadsheets/d/abc123", name="My Dataset"
        )
        assert request.name == "My Dataset"

    def test_import_sheets_request_with_all_fields(self):
        """Test ImportSheetsRequest with all fields."""
        request = ImportSheetsRequest(
            url="https://docs.google.com/spreadsheets/d/abc123",
            name="Sales Q4",
            description="Quarterly sales data imported from Google Sheets",
        )
        assert request.url == "https://docs.google.com/spreadsheets/d/abc123"
        assert request.name == "Sales Q4"
        assert request.description == "Quarterly sales data imported from Google Sheets"

    def test_import_sheets_request_url_too_short(self):
        """Test ImportSheetsRequest rejects URL under 10 chars."""
        with pytest.raises(ValueError):
            ImportSheetsRequest(url="http://x")

    def test_import_sheets_request_url_empty(self):
        """Test ImportSheetsRequest rejects empty URL."""
        with pytest.raises(ValueError):
            ImportSheetsRequest(url="")

    def test_import_sheets_request_name_too_long(self):
        """Test ImportSheetsRequest rejects name over 255 chars."""
        with pytest.raises(ValueError):
            ImportSheetsRequest(url="https://docs.google.com/spreadsheets/d/abc123", name="x" * 256)

    def test_import_sheets_request_description_too_long(self):
        """Test ImportSheetsRequest rejects description over 5000 chars."""
        with pytest.raises(ValueError):
            ImportSheetsRequest(
                url="https://docs.google.com/spreadsheets/d/abc123", description="x" * 5001
            )
