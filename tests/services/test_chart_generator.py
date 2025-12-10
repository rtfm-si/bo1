"""Tests for chart generator service."""

import pandas as pd
import pytest

from backend.api.models import ChartSpec, FilterSpec
from backend.services.chart_generator import (
    ChartError,
    ChartResult,
    generate_chart,
    generate_chart_json,
    generate_chart_png,
)


@pytest.fixture
def sample_df():
    """Create a sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "category": ["A", "B", "C", "D", "E"],
            "value": [100, 150, 200, 175, 250],
            "group": ["X", "X", "Y", "Y", "X"],
        }
    )


@pytest.fixture
def time_series_df():
    """Create a time series DataFrame for line chart testing."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"]
            ),
            "sales": [100, 120, 150, 140, 180],
            "region": ["North", "North", "South", "South", "North"],
        }
    )


@pytest.fixture
def scatter_df():
    """Create a DataFrame for scatter chart testing."""
    return pd.DataFrame(
        {
            "x_val": [1, 2, 3, 4, 5, 6, 7, 8],
            "y_val": [10, 15, 13, 17, 20, 22, 19, 25],
            "category": ["A", "B", "A", "B", "A", "B", "A", "B"],
        }
    )


class TestBarChart:
    """Test bar chart generation."""

    def test_basic_bar_chart(self, sample_df):
        """Test basic bar chart generation."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
        )
        result = generate_chart(sample_df, spec)

        assert isinstance(result, ChartResult)
        assert result.chart_type == "bar"
        assert result.width == 800
        assert result.height == 600
        assert result.row_count == 5
        # Verify figure_json has expected structure
        assert "data" in result.figure_json
        assert "layout" in result.figure_json
        assert len(result.figure_json["data"]) > 0

    def test_grouped_bar_chart(self, sample_df):
        """Test bar chart with grouping."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
            group_field="group",
            title="Grouped Bar Chart",
        )
        result = generate_chart(sample_df, spec)

        assert result.chart_type == "bar"
        assert result.row_count == 5

    def test_bar_chart_custom_size(self, sample_df):
        """Test bar chart with custom dimensions."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
            width=1200,
            height=800,
        )
        result = generate_chart(sample_df, spec)

        assert result.width == 1200
        assert result.height == 800


class TestLineChart:
    """Test line chart generation."""

    def test_basic_line_chart(self, time_series_df):
        """Test basic line chart generation."""
        spec = ChartSpec(
            chart_type="line",
            x_field="date",
            y_field="sales",
        )
        result = generate_chart(time_series_df, spec)

        assert result.chart_type == "line"
        assert result.row_count == 5

    def test_grouped_line_chart(self, time_series_df):
        """Test line chart with grouping (multiple series)."""
        spec = ChartSpec(
            chart_type="line",
            x_field="date",
            y_field="sales",
            group_field="region",
            title="Sales by Region",
        )
        result = generate_chart(time_series_df, spec)

        assert result.chart_type == "line"


class TestPieChart:
    """Test pie chart generation."""

    def test_basic_pie_chart(self, sample_df):
        """Test basic pie chart generation."""
        spec = ChartSpec(
            chart_type="pie",
            x_field="category",
            y_field="value",
            title="Value Distribution",
        )
        result = generate_chart(sample_df, spec)

        assert result.chart_type == "pie"
        assert result.row_count == 5


class TestScatterChart:
    """Test scatter chart generation."""

    def test_basic_scatter_chart(self, scatter_df):
        """Test basic scatter chart generation."""
        spec = ChartSpec(
            chart_type="scatter",
            x_field="x_val",
            y_field="y_val",
        )
        result = generate_chart(scatter_df, spec)

        assert result.chart_type == "scatter"
        assert result.row_count == 8

    def test_grouped_scatter_chart(self, scatter_df):
        """Test scatter chart with color grouping."""
        spec = ChartSpec(
            chart_type="scatter",
            x_field="x_val",
            y_field="y_val",
            group_field="category",
            title="Scatter by Category",
        )
        result = generate_chart(scatter_df, spec)

        assert result.chart_type == "scatter"


class TestChartFilters:
    """Test chart generation with filters."""

    def test_chart_with_filter(self, sample_df):
        """Test chart with filter applied."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
            filters=[FilterSpec(field="group", operator="eq", value="X")],
        )
        result = generate_chart(sample_df, spec)

        # Should only have rows where group == "X" (A, B, E = 3 rows)
        assert result.row_count == 3

    def test_filter_removes_all_data(self, sample_df):
        """Test error when filter removes all data."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
            filters=[FilterSpec(field="value", operator="gt", value=1000)],
        )
        with pytest.raises(ChartError) as exc:
            generate_chart(sample_df, spec)
        assert "No data remaining" in str(exc.value)


class TestChartErrors:
    """Test error handling."""

    def test_empty_dataframe(self):
        """Test error on empty DataFrame."""
        df = pd.DataFrame()
        spec = ChartSpec(
            chart_type="bar",
            x_field="x",
            y_field="y",
        )
        with pytest.raises(ChartError) as exc:
            generate_chart(df, spec)
        assert "empty DataFrame" in str(exc.value)

    def test_missing_x_field(self, sample_df):
        """Test error when x_field doesn't exist."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="nonexistent",
            y_field="value",
        )
        with pytest.raises(ChartError) as exc:
            generate_chart(sample_df, spec)
        assert "nonexistent" in str(exc.value)

    def test_missing_y_field(self, sample_df):
        """Test error when y_field doesn't exist."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="nonexistent",
        )
        with pytest.raises(ChartError) as exc:
            generate_chart(sample_df, spec)
        assert "nonexistent" in str(exc.value)

    def test_missing_group_field(self, sample_df):
        """Test error when group_field doesn't exist."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
            group_field="nonexistent",
        )
        with pytest.raises(ChartError) as exc:
            generate_chart(sample_df, spec)
        assert "nonexistent" in str(exc.value)


class TestJsonOutput:
    """Test JSON output for frontend."""

    def test_generate_chart_json(self, sample_df):
        """Test JSON chart generation for frontend."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
        )
        result = generate_chart_json(sample_df, spec)

        assert isinstance(result, dict)
        assert "figure_json" in result
        assert "chart_type" in result
        assert "width" in result
        assert "height" in result
        assert "row_count" in result

        # Verify figure_json structure
        assert "data" in result["figure_json"]
        assert "layout" in result["figure_json"]

    def test_json_chart_type(self, sample_df):
        """Test that chart_type is preserved in JSON output."""
        spec = ChartSpec(
            chart_type="pie",
            x_field="category",
            y_field="value",
        )
        result = generate_chart_json(sample_df, spec)

        assert result["chart_type"] == "pie"


class TestPngExport:
    """Test PNG export for PDF embedding."""

    def test_generate_chart_png(self, sample_df):
        """Test PNG export via cairosvg."""
        spec = ChartSpec(
            chart_type="bar",
            x_field="category",
            y_field="value",
        )
        png_bytes = generate_chart_png(sample_df, spec)

        # Verify it's a valid PNG (magic bytes)
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
        # Should be reasonably sized (at least 1KB for a simple chart)
        assert len(png_bytes) > 1000
