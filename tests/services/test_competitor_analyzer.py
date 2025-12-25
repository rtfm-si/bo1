"""Tests for competitor insight analyzer service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.competitor_analyzer import (
    CompetitorInsightAnalyzer,
    CompetitorInsightResult,
    get_competitor_analyzer,
)


class TestCompetitorInsightResult:
    """Tests for CompetitorInsightResult dataclass."""

    def test_to_dict_complete(self):
        """Test to_dict with all fields populated."""
        now = datetime.now(UTC)
        result = CompetitorInsightResult(
            name="Acme Corp",
            tagline="Building the future",
            size_estimate="50-200 employees",
            revenue_estimate="$5M-20M ARR",
            strengths=["Strong brand", "Great UX"],
            weaknesses=["Limited integrations", "High price"],
            market_gaps=["SMB segment", "API-first approach"],
            last_updated=now,
            status="complete",
        )

        d = result.to_dict()

        assert d["name"] == "Acme Corp"
        assert d["tagline"] == "Building the future"
        assert d["size_estimate"] == "50-200 employees"
        assert d["revenue_estimate"] == "$5M-20M ARR"
        assert d["strengths"] == ["Strong brand", "Great UX"]
        assert d["weaknesses"] == ["Limited integrations", "High price"]
        assert d["market_gaps"] == ["SMB segment", "API-first approach"]
        assert d["last_updated"] == now.isoformat()

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        result = CompetitorInsightResult(name="Minimal Co")

        d = result.to_dict()

        assert d["name"] == "Minimal Co"
        assert d["tagline"] is None
        assert d["size_estimate"] is None
        assert d["strengths"] == []
        assert d["weaknesses"] == []
        assert d["market_gaps"] == []
        assert d["last_updated"] is None


class TestCompetitorInsightAnalyzer:
    """Tests for CompetitorInsightAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return CompetitorInsightAnalyzer()

    @pytest.fixture
    def valid_llm_response(self):
        """Valid JSON response from LLM."""
        return json.dumps(
            {
                "name": "Notion",
                "tagline": "Your connected workspace",
                "size_estimate": "500-1000 employees",
                "revenue_estimate": "$100M-200M ARR",
                "strengths": [
                    "Excellent user experience",
                    "Strong brand recognition",
                    "Flexible workspace model",
                ],
                "weaknesses": [
                    "Performance with large databases",
                    "Limited offline support",
                ],
                "market_gaps": [
                    "Enterprise security features",
                    "Advanced automation",
                ],
            }
        )

    @pytest.mark.asyncio
    async def test_generate_insight_success(self, analyzer, valid_llm_response):
        """Test successful insight generation."""
        mock_response = MagicMock()
        mock_response.text = valid_llm_response

        with (
            patch.object(analyzer, "_get_broker") as mock_broker,
            patch.object(analyzer, "_search_competitor", return_value=None),
        ):
            broker_instance = MagicMock()
            broker_instance.call = AsyncMock(return_value=mock_response)
            mock_broker.return_value = broker_instance

            result = await analyzer.generate_insight(
                competitor_name="Notion",
                industry="Productivity Software",
                product_description="Team collaboration tool",
            )

        assert result.status == "limited_data"  # No search results
        assert result.name == "Notion"
        assert result.tagline == "Your connected workspace"
        assert len(result.strengths) == 3
        assert len(result.weaknesses) == 2
        assert len(result.market_gaps) == 2
        assert result.error is None

    @pytest.mark.asyncio
    async def test_generate_insight_with_search(self, analyzer, valid_llm_response):
        """Test insight generation with search results."""
        mock_response = MagicMock()
        mock_response.text = valid_llm_response

        search_results = [
            {"title": "Notion Review", "content": "Great tool", "url": "https://example.com"},
        ]

        with (
            patch.object(analyzer, "_get_broker") as mock_broker,
            patch.object(analyzer, "_search_competitor", return_value=search_results),
        ):
            broker_instance = MagicMock()
            broker_instance.call = AsyncMock(return_value=mock_response)
            mock_broker.return_value = broker_instance

            result = await analyzer.generate_insight(
                competitor_name="Notion",
                industry="Productivity",
            )

        assert result.status == "complete"  # Has search results
        assert result.name == "Notion"

    @pytest.mark.asyncio
    async def test_generate_insight_llm_error(self, analyzer):
        """Test insight generation when LLM fails."""
        with (
            patch.object(analyzer, "_get_broker") as mock_broker,
            patch.object(analyzer, "_search_competitor", return_value=None),
        ):
            broker_instance = MagicMock()
            broker_instance.call = AsyncMock(side_effect=Exception("LLM timeout"))
            mock_broker.return_value = broker_instance

            result = await analyzer.generate_insight(
                competitor_name="FailCo",
            )

        assert result.status == "error"
        assert result.name == "FailCo"
        assert "LLM timeout" in result.error
        assert result.strengths == []
        assert result.weaknesses == []

    def test_parse_insight_valid_json(self, analyzer):
        """Test parsing valid JSON response."""
        response = json.dumps(
            {
                "name": "TestCo",
                "tagline": "Test tagline",
                "strengths": ["A", "B"],
                "weaknesses": ["C"],
                "market_gaps": ["D", "E", "F"],
            }
        )

        result = analyzer._parse_insight(response, "TestCo")

        assert result.name == "TestCo"
        assert result.tagline == "Test tagline"
        assert result.strengths == ["A", "B"]
        assert result.weaknesses == ["C"]
        assert result.market_gaps == ["D", "E", "F"]
        assert result.status == "complete"

    def test_parse_insight_markdown_wrapped(self, analyzer):
        """Test parsing JSON wrapped in markdown code blocks."""
        response = """```json
{
    "name": "MarkdownCo",
    "tagline": null,
    "strengths": ["Strong"],
    "weaknesses": [],
    "market_gaps": []
}
```"""

        result = analyzer._parse_insight(response, "MarkdownCo")

        assert result.name == "MarkdownCo"
        assert result.tagline is None
        assert result.strengths == ["Strong"]

    def test_parse_insight_invalid_json(self, analyzer):
        """Test parsing invalid JSON returns fallback."""
        response = "This is not JSON at all"

        result = analyzer._parse_insight(response, "FallbackCo")

        assert result.name == "FallbackCo"
        assert result.status == "error"
        assert result.error is not None
        assert result.strengths == []

    def test_parse_insight_truncates_long_values(self, analyzer):
        """Test that long values are truncated."""
        long_string = "x" * 300
        response = json.dumps(
            {
                "name": "a" * 200,  # Should be truncated to 100
                "tagline": long_string,  # Should be truncated to 200
                "strengths": [long_string, long_string],  # Each truncated to 200
                "weaknesses": [],
                "market_gaps": [],
            }
        )

        result = analyzer._parse_insight(response, "LongCo")

        assert len(result.name) == 100
        assert len(result.tagline) == 200
        assert len(result.strengths[0]) == 200

    def test_parse_insight_limits_list_items(self, analyzer):
        """Test that lists are limited to max items."""
        response = json.dumps(
            {
                "name": "ListCo",
                "tagline": None,
                "strengths": ["1", "2", "3", "4", "5", "6", "7", "8"],  # >5 items
                "weaknesses": ["1", "2", "3", "4", "5", "6", "7"],
                "market_gaps": ["1", "2", "3", "4", "5", "6"],
            }
        )

        result = analyzer._parse_insight(response, "ListCo")

        assert len(result.strengths) == 5
        assert len(result.weaknesses) == 5
        assert len(result.market_gaps) == 5

    def test_safe_str_none(self, analyzer):
        """Test _safe_str with None value."""
        assert analyzer._safe_str(None, 100) is None

    def test_safe_str_truncation(self, analyzer):
        """Test _safe_str truncates long strings."""
        assert analyzer._safe_str("hello world", 5) == "hello"

    def test_safe_list_invalid_type(self, analyzer):
        """Test _safe_list with invalid type."""
        assert analyzer._safe_list("not a list", 5) == []
        assert analyzer._safe_list(None, 5) == []
        assert analyzer._safe_list(123, 5) == []

    def test_fallback_insight(self, analyzer):
        """Test fallback insight has correct structure."""
        result = analyzer._fallback_insight("ErrorCo", "Test error")

        assert result.name == "ErrorCo"
        assert result.status == "error"
        assert result.error == "Test error"
        assert result.tagline is None
        assert result.strengths == []
        assert result.weaknesses == []
        assert result.market_gaps == []
        assert result.last_updated is not None


class TestGetCompetitorAnalyzer:
    """Tests for singleton getter."""

    def test_returns_same_instance(self):
        """Test that get_competitor_analyzer returns singleton."""
        # Reset singleton for clean test
        import backend.services.competitor_analyzer as module

        module._analyzer = None

        analyzer1 = get_competitor_analyzer()
        analyzer2 = get_competitor_analyzer()

        assert analyzer1 is analyzer2

    def test_creates_instance(self):
        """Test that get_competitor_analyzer creates instance."""
        import backend.services.competitor_analyzer as module

        module._analyzer = None

        analyzer = get_competitor_analyzer()

        assert isinstance(analyzer, CompetitorInsightAnalyzer)
