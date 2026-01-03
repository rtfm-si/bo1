"""Tests for chart suggestion generation in insight_generator."""

from backend.services.insight_generator import (
    _generate_chart_suggestions,
    _pick_best_categorical,
    _pick_best_numeric,
)


class TestGenerateChartSuggestions:
    """Test _generate_chart_suggestions heuristics."""

    def test_empty_columns_returns_empty(self):
        """Empty dataset returns no suggestions."""
        profile = {"columns": [], "row_count": 0}
        result = _generate_chart_suggestions(profile)
        assert result == []

    def test_numeric_only_returns_distribution(self):
        """Dataset with only numeric columns suggests histogram."""
        profile = {
            "columns": [
                {"name": "amount", "inferred_type": "float", "stats": {"unique_count": 100}},
                {"name": "quantity", "inferred_type": "integer", "stats": {"unique_count": 50}},
            ],
            "row_count": 1000,
        }
        result = _generate_chart_suggestions(profile)

        # Should get distribution and scatter suggestions
        assert len(result) >= 2
        chart_types = [s.chart_spec.chart_type for s in result]
        assert "bar" in chart_types  # histogram
        assert "scatter" in chart_types

    def test_date_numeric_returns_time_series(self):
        """Dataset with date + numeric columns suggests line chart."""
        profile = {
            "columns": [
                {"name": "order_date", "inferred_type": "date", "stats": {}},
                {"name": "revenue", "inferred_type": "float", "stats": {"unique_count": 100}},
            ],
            "row_count": 1000,
        }
        result = _generate_chart_suggestions(profile)

        assert len(result) >= 1
        line_charts = [s for s in result if s.chart_spec.chart_type == "line"]
        assert len(line_charts) >= 1
        assert line_charts[0].chart_spec.x_field == "order_date"
        assert line_charts[0].chart_spec.y_field == "revenue"

    def test_categorical_numeric_returns_bar(self):
        """Dataset with categorical + numeric columns suggests bar chart."""
        profile = {
            "columns": [
                {"name": "category", "inferred_type": "string", "stats": {"unique_count": 5}},
                {"name": "sales", "inferred_type": "float", "stats": {"unique_count": 100}},
            ],
            "row_count": 1000,
        }
        result = _generate_chart_suggestions(profile)

        assert len(result) >= 1
        bar_charts = [s for s in result if s.chart_spec.chart_type == "bar"]
        assert len(bar_charts) >= 1

    def test_categorical_only_returns_pie(self):
        """Dataset with only categorical columns suggests pie chart."""
        profile = {
            "columns": [
                {"name": "status", "inferred_type": "string", "stats": {"unique_count": 3}},
                {"name": "region", "inferred_type": "string", "stats": {"unique_count": 8}},
            ],
            "row_count": 100,
        }
        result = _generate_chart_suggestions(profile)

        pie_charts = [s for s in result if s.chart_spec.chart_type == "pie"]
        assert len(pie_charts) >= 1

    def test_limits_to_3_suggestions(self):
        """Never returns more than 3 suggestions."""
        profile = {
            "columns": [
                {"name": "date", "inferred_type": "date", "stats": {}},
                {"name": "category", "inferred_type": "string", "stats": {"unique_count": 5}},
                {"name": "amount", "inferred_type": "float", "stats": {"unique_count": 100}},
                {"name": "quantity", "inferred_type": "integer", "stats": {"unique_count": 50}},
            ],
            "row_count": 1000,
        }
        result = _generate_chart_suggestions(profile)
        assert len(result) <= 3

    def test_limits_columns_to_20(self):
        """Only scans first 20 columns for wide datasets."""
        # Create 50 columns
        columns = [
            {"name": f"col_{i}", "inferred_type": "float", "stats": {"unique_count": 100}}
            for i in range(50)
        ]
        profile = {"columns": columns, "row_count": 1000}

        # Should not error and should produce suggestions
        result = _generate_chart_suggestions(profile)
        assert len(result) <= 3

    def test_high_cardinality_categorical_excluded(self):
        """High cardinality string columns are not treated as categorical."""
        profile = {
            "columns": [
                {"name": "user_id", "inferred_type": "string", "stats": {"unique_count": 10000}},
                {"name": "amount", "inferred_type": "float", "stats": {"unique_count": 100}},
            ],
            "row_count": 10000,
        }
        result = _generate_chart_suggestions(profile)

        # Should not suggest grouping by user_id (too many unique values)
        for suggestion in result:
            if suggestion.chart_spec.chart_type == "bar":
                assert suggestion.chart_spec.x_field != "user_id"


class TestPickBestNumeric:
    """Test _pick_best_numeric column selection."""

    def test_prefers_revenue_columns(self):
        """Prefers columns with business-relevant names."""
        cols = [
            {"name": "id", "stats": {}},
            {"name": "revenue", "stats": {}},
            {"name": "count", "stats": {}},
        ]
        result = _pick_best_numeric(cols)
        assert result["name"] == "revenue"

    def test_prefers_amount_columns(self):
        """Prefers 'amount' in column name."""
        cols = [
            {"name": "order_amount", "stats": {}},
            {"name": "some_number", "stats": {}},
        ]
        result = _pick_best_numeric(cols)
        assert result["name"] == "order_amount"

    def test_fallback_to_first_when_no_keywords(self):
        """Falls back to first column when no keyword matches."""
        cols = [
            {"name": "foo", "stats": {}},
            {"name": "bar", "stats": {}},
        ]
        result = _pick_best_numeric(cols)
        assert result["name"] == "foo"

    def test_empty_list_returns_empty(self):
        """Empty input returns empty dict."""
        result = _pick_best_numeric([])
        assert result == {}


class TestPickBestCategorical:
    """Test _pick_best_categorical column selection."""

    def test_prefers_moderate_cardinality(self):
        """Prefers columns with 3-20 unique values."""
        cols = [
            {"name": "binary_flag", "stats": {"unique_count": 2}},
            {"name": "category", "stats": {"unique_count": 10}},
            {"name": "user_id", "stats": {"unique_count": 1000}},
        ]
        result = _pick_best_categorical(cols)
        assert result["name"] == "category"

    def test_prefers_category_keywords(self):
        """Prefers columns with meaningful categorical names."""
        cols = [
            {"name": "field_a", "stats": {"unique_count": 5}},
            {"name": "status", "stats": {"unique_count": 5}},
        ]
        result = _pick_best_categorical(cols)
        assert result["name"] == "status"

    def test_empty_list_returns_empty(self):
        """Empty input returns empty dict."""
        result = _pick_best_categorical([])
        assert result == {}
