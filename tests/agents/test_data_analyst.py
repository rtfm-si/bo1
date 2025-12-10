"""Tests for DataAnalysisAgent."""

from bo1.agents.data_analyst import DataAnalysisAgent


class TestDataAnalysisAgent:
    """Tests for DataAnalysisAgent class."""

    def test_question_to_query_spec_aggregate(self) -> None:
        """Test question to query spec conversion for aggregate queries."""
        agent = DataAnalysisAgent()

        # Default case - aggregate
        spec = agent._question_to_query_spec("What are the top products by revenue?")
        assert spec["query_type"] == "aggregate"

    def test_question_to_query_spec_trend(self) -> None:
        """Test question to query spec conversion for trend queries."""
        agent = DataAnalysisAgent()

        spec = agent._question_to_query_spec("How has revenue changed over time?")
        assert spec["query_type"] == "trend"

        spec = agent._question_to_query_spec("Show sales by month")
        assert spec["query_type"] == "trend"

    def test_question_to_query_spec_compare(self) -> None:
        """Test question to query spec conversion for comparison queries."""
        agent = DataAnalysisAgent()

        spec = agent._question_to_query_spec("Compare sales Q1 versus Q2")
        assert spec["query_type"] == "compare"

    def test_question_to_query_spec_correlate(self) -> None:
        """Test question to query spec conversion for correlation queries."""
        agent = DataAnalysisAgent()

        spec = agent._question_to_query_spec("What is the correlation between price and sales?")
        assert spec["query_type"] == "correlate"

    def test_question_to_query_spec_filter(self) -> None:
        """Test question to query spec conversion for filter queries."""
        agent = DataAnalysisAgent()

        spec = agent._question_to_query_spec("Show me all products where price > 100")
        assert spec["query_type"] == "filter"

    def test_should_generate_chart_true(self) -> None:
        """Test chart generation detection - should generate."""
        agent = DataAnalysisAgent()

        query_result = {"total_count": 10, "rows": [{}] * 10}
        assert agent._should_generate_chart("Show the trend chart", query_result) is True
        assert agent._should_generate_chart("What are the top 5 products?", query_result) is True

    def test_should_generate_chart_false(self) -> None:
        """Test chart generation detection - should not generate."""
        agent = DataAnalysisAgent()

        # Too few rows
        query_result = {"total_count": 1, "rows": [{}]}
        assert agent._should_generate_chart("Any question", query_result) is False

    def test_question_to_chart_spec_bar(self) -> None:
        """Test chart spec generation - bar chart."""
        agent = DataAnalysisAgent()

        query_result = {"columns": ["product", "revenue"], "rows": []}
        spec = agent._question_to_chart_spec("What are the top products?", query_result)

        assert spec is not None
        assert spec["chart_type"] == "bar"
        assert spec["x_field"] == "product"
        assert spec["y_field"] == "revenue"

    def test_question_to_chart_spec_line(self) -> None:
        """Test chart spec generation - line chart."""
        agent = DataAnalysisAgent()

        query_result = {"columns": ["month", "revenue"], "rows": []}
        spec = agent._question_to_chart_spec("Show trend over time", query_result)

        assert spec is not None
        assert spec["chart_type"] == "line"

    def test_question_to_chart_spec_pie(self) -> None:
        """Test chart spec generation - pie chart."""
        agent = DataAnalysisAgent()

        query_result = {"columns": ["category", "count"], "rows": []}
        spec = agent._question_to_chart_spec("Show distribution percentage", query_result)

        assert spec is not None
        assert spec["chart_type"] == "pie"

    def test_format_analysis_context_empty(self) -> None:
        """Test formatting empty analysis results."""
        agent = DataAnalysisAgent()

        result = agent.format_analysis_context([])
        assert result == ""

    def test_format_analysis_context_with_results(self) -> None:
        """Test formatting analysis results with data."""
        agent = DataAnalysisAgent()

        results = [
            {
                "question": "What are top products?",
                "query_result": {
                    "rows": [{"product": "A", "sales": 100}],
                    "columns": ["product", "sales"],
                    "total_count": 1,
                },
                "chart_result": {"chart_type": "bar"},
            }
        ]

        formatted = agent.format_analysis_context(results)

        assert "<dataset_analysis>" in formatted
        assert "<question>What are top products?</question>" in formatted
        assert "<data" in formatted
        assert "product, sales" in formatted
        assert '<chart type="bar">' in formatted
        assert "</dataset_analysis>" in formatted

    def test_format_analysis_context_with_error(self) -> None:
        """Test formatting analysis results with error."""
        agent = DataAnalysisAgent()

        results = [
            {
                "question": "Invalid query",
                "error": "Dataset not found",
                "query_result": None,
                "chart_result": None,
            }
        ]

        formatted = agent.format_analysis_context(results)

        assert "<error>Dataset not found</error>" in formatted
