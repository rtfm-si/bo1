"""Unit tests for insight parser service.

Tests both LLM-based and fallback rule-based parsing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.insight_parser import (
    InsightCategory,
    InsightMetric,
    InsightParser,
    StructuredInsight,
    get_insight_parser,
    is_valid_insight_response,
    parse_insight,
)


class TestIsValidInsightResponse:
    """Test is_valid_insight_response validation function."""

    def test_empty_string_returns_false(self):
        """Empty string is invalid."""
        assert is_valid_insight_response("") is False

    def test_whitespace_only_returns_false(self):
        """Whitespace-only is invalid."""
        assert is_valid_insight_response("   ") is False
        assert is_valid_insight_response("\t\n  ") is False

    def test_none_returns_false(self):
        """None is invalid."""
        assert is_valid_insight_response(None) is False

    def test_none_literal_returns_false(self):
        """'none' by itself is invalid."""
        assert is_valid_insight_response("none") is False
        assert is_valid_insight_response("None") is False
        assert is_valid_insight_response("NONE") is False
        assert is_valid_insight_response("none.") is False

    def test_na_returns_false(self):
        """'n/a' and 'na' are invalid."""
        assert is_valid_insight_response("n/a") is False
        assert is_valid_insight_response("N/A") is False
        assert is_valid_insight_response("na") is False
        assert is_valid_insight_response("NA") is False

    def test_not_applicable_returns_false(self):
        """'not applicable' is invalid."""
        assert is_valid_insight_response("not applicable") is False
        assert is_valid_insight_response("Not Applicable") is False
        assert is_valid_insight_response("not applicable.") is False

    def test_no_returns_false(self):
        """Single 'no' is invalid."""
        assert is_valid_insight_response("no") is False
        assert is_valid_insight_response("No") is False

    def test_other_invalid_patterns(self):
        """Other common invalid patterns."""
        assert is_valid_insight_response("nothing") is False
        assert is_valid_insight_response("null") is False
        assert is_valid_insight_response("unknown") is False
        assert is_valid_insight_response("skip") is False
        assert is_valid_insight_response("skipped") is False
        assert is_valid_insight_response("-") is False
        assert is_valid_insight_response("—") is False
        assert is_valid_insight_response("...") is False
        assert is_valid_insight_response(".") is False

    def test_none_in_context_returns_true(self):
        """'none' in a longer response is valid (context matters)."""
        assert is_valid_insight_response("none of the above apply because we're B2B") is True
        assert is_valid_insight_response("We have none at the moment but planning to add") is True
        assert is_valid_insight_response("None of the competitors offer this feature") is True

    def test_valid_insight_text_returns_true(self):
        """Valid insight text is accepted."""
        assert is_valid_insight_response("Our MRR is $25,000") is True
        assert is_valid_insight_response("We have 5 employees") is True
        assert is_valid_insight_response("B2B SaaS targeting small businesses") is True
        assert is_valid_insight_response("We compete with Asana and Monday.com") is True
        assert is_valid_insight_response("Growth rate is 15% month over month") is True

    def test_short_but_valid_returns_true(self):
        """Short but meaningful responses are valid."""
        assert is_valid_insight_response("$50K MRR") is True
        assert is_valid_insight_response("5 people") is True
        assert is_valid_insight_response("15% growth") is True

    def test_punctuation_variants(self):
        """Invalid patterns with punctuation are still invalid."""
        assert is_valid_insight_response("none!") is False
        assert is_valid_insight_response("n/a?") is False
        assert is_valid_insight_response("not applicable;") is False


class TestInsightCategory:
    """Test InsightCategory enum."""

    def test_all_categories_defined(self):
        """Verify all expected categories exist."""
        expected = [
            "revenue",
            "growth",
            "customers",
            "team",
            "product",
            "operations",
            "market",
            "competition",
            "funding",
            "costs",
            "uncategorized",
            # D2C/product metrics
            "inventory",
            "margin",
            "conversion",
            "aov",
            "cogs",
            "returns",
        ]
        actual = [c.value for c in InsightCategory]
        assert set(expected) == set(actual)


class TestStructuredInsight:
    """Test StructuredInsight dataclass."""

    def test_to_dict_minimal(self):
        """Test to_dict with minimal fields."""
        insight = StructuredInsight(
            raw_text="test",
            category=InsightCategory.REVENUE,
            metric=None,
            confidence_score=0.8,
        )
        result = insight.to_dict()
        assert result["raw_text"] == "test"
        assert result["category"] == "revenue"
        assert result["confidence_score"] == 0.8
        assert "metric" not in result
        assert "summary" not in result

    def test_to_dict_with_metric(self):
        """Test to_dict with metric."""
        metric = InsightMetric(
            value=25000,
            unit="USD",
            metric_type="MRR",
            period="monthly",
            raw_text="$25,000",
        )
        insight = StructuredInsight(
            raw_text="Monthly revenue is $25,000",
            category=InsightCategory.REVENUE,
            metric=metric,
            confidence_score=0.95,
            summary="Monthly revenue of $25K",
        )
        result = insight.to_dict()
        assert result["metric"]["value"] == 25000
        assert result["metric"]["unit"] == "USD"
        assert result["metric"]["metric_type"] == "MRR"
        assert result["summary"] == "Monthly revenue of $25K"

    def test_from_dict_roundtrip(self):
        """Test from_dict reconstructs insight correctly."""
        original = StructuredInsight(
            raw_text="We have 50 customers",
            category=InsightCategory.CUSTOMERS,
            metric=InsightMetric(value=50, unit="count", metric_type="customers"),
            confidence_score=0.9,
            summary="50 customers",
            key_entities=["Acme Corp"],
            parsed_at="2025-01-15T12:00:00+00:00",
        )
        data = original.to_dict()
        restored = StructuredInsight.from_dict(data)

        assert restored.raw_text == original.raw_text
        assert restored.category == original.category
        assert restored.metric.value == original.metric.value
        assert restored.confidence_score == original.confidence_score
        assert restored.key_entities == original.key_entities


class TestFallbackParsing:
    """Test rule-based fallback parsing."""

    @pytest.fixture
    def parser(self):
        return InsightParser()

    def test_revenue_detection(self, parser):
        """Test revenue category detection."""
        result = parser._fallback_parse("Monthly revenue is $25,000")
        assert result.category == InsightCategory.REVENUE
        assert result.metric is not None
        assert result.metric.value == 25000
        assert result.metric.unit == "USD"

    def test_revenue_k_suffix(self, parser):
        """Test revenue with K suffix."""
        result = parser._fallback_parse("We're at $50K MRR")
        assert result.category == InsightCategory.REVENUE
        assert result.metric.value == 50000

    def test_revenue_m_suffix(self, parser):
        """Test revenue with M suffix."""
        result = parser._fallback_parse("ARR is $1.5M")
        assert result.category == InsightCategory.REVENUE
        assert result.metric.value == 1500000

    def test_growth_detection(self, parser):
        """Test growth category detection."""
        result = parser._fallback_parse("We're growing at 15% month over month")
        assert result.category == InsightCategory.GROWTH
        assert result.metric.value == 15
        assert result.metric.unit == "%"

    def test_team_detection(self, parser):
        """Test team category detection."""
        result = parser._fallback_parse("Team grew to 5 people last month")
        assert result.category == InsightCategory.TEAM
        assert result.metric.value == 5
        assert result.metric.unit == "count"

    def test_customers_detection(self, parser):
        """Test customers category detection."""
        result = parser._fallback_parse("We now have 150 customers")
        assert result.category == InsightCategory.CUSTOMERS
        assert result.metric.value == 150

    def test_competition_detection(self, parser):
        """Test competition category detection."""
        result = parser._fallback_parse("We compete with Asana and Monday.com")
        assert result.category == InsightCategory.COMPETITION

    def test_product_detection(self, parser):
        """Test product category detection."""
        result = parser._fallback_parse("We're launching a new feature next week")
        assert result.category == InsightCategory.PRODUCT

    def test_funding_detection(self, parser):
        """Test funding category detection."""
        result = parser._fallback_parse("We raised $2M in seed funding")
        assert result.category == InsightCategory.FUNDING
        assert result.metric.value == 2000000

    def test_uncategorized_fallback(self, parser):
        """Test uncategorized fallback."""
        result = parser._fallback_parse("The weather is nice today")
        assert result.category == InsightCategory.UNCATEGORIZED
        assert result.confidence_score == 0.2

    def test_empty_input(self, parser):
        """Test empty input handling."""
        result = parser._fallback_parse("")
        assert result.category == InsightCategory.UNCATEGORIZED
        assert result.confidence_score == 0.2

    def test_parsed_at_set(self, parser):
        """Test parsed_at timestamp is set."""
        result = parser._fallback_parse("Some text")
        assert result.parsed_at is not None


class TestLLMParsing:
    """Test LLM-based parsing with mocked Claude client."""

    @pytest.fixture
    def parser(self):
        return InsightParser()

    @pytest.mark.asyncio
    async def test_llm_parse_success(self, parser):
        """Test successful LLM parsing."""
        mock_response = """{
            "category": "revenue",
            "metric": {"value": 25000, "unit": "USD", "metric_type": "MRR", "period": "monthly", "raw_text": "$25,000"},
            "confidence": 0.95,
            "summary": "Monthly revenue of $25K",
            "key_entities": []
        }"""

        with patch.object(parser, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            result = await parser._parse_with_llm("Monthly revenue is $25,000")

            assert result.category == InsightCategory.REVENUE
            assert result.metric.value == 25000
            assert result.metric.unit == "USD"
            assert result.confidence_score == 0.95

    @pytest.mark.asyncio
    async def test_llm_parse_invalid_json_fallback(self, parser):
        """Test fallback when LLM returns invalid JSON."""
        with patch.object(parser, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=("not valid json at all", {}))
            mock_get_client.return_value = mock_client

            with pytest.raises(ValueError):
                await parser._parse_with_llm("Some text")

    @pytest.mark.asyncio
    async def test_llm_parse_with_json_extraction(self, parser):
        """Test JSON extraction from response with surrounding text."""
        mock_response = """Here is the analysis:
        {"category": "team", "metric": {"value": 10, "unit": "count"}, "confidence": 0.8, "summary": "Team of 10"}
        Hope that helps!"""

        with patch.object(parser, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.call = AsyncMock(return_value=(mock_response, {}))
            mock_get_client.return_value = mock_client

            result = await parser._parse_with_llm("We have 10 people")

            assert result.category == InsightCategory.TEAM
            assert result.metric.value == 10


class TestParseInsightFunction:
    """Test the parse_insight convenience function."""

    @pytest.mark.asyncio
    async def test_parse_empty_input(self):
        """Test parsing empty input."""
        result = await parse_insight("")
        assert result.category == InsightCategory.UNCATEGORIZED
        assert result.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_parse_whitespace_only(self):
        """Test parsing whitespace-only input."""
        result = await parse_insight("   \n\t  ")
        assert result.category == InsightCategory.UNCATEGORIZED
        assert result.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_parse_fallback_on_llm_failure(self):
        """Test fallback to rule-based parsing when LLM fails."""
        with patch(
            "backend.services.insight_parser.InsightParser._parse_with_llm",
            side_effect=Exception("LLM failed"),
        ):
            result = await parse_insight("Monthly revenue is $25,000")
            # Should fallback to rule-based parsing
            assert result.category == InsightCategory.REVENUE


class TestGetInsightParser:
    """Test singleton pattern."""

    def test_singleton(self):
        """Test that get_insight_parser returns singleton."""
        # Reset singleton for test
        get_insight_parser.cache_clear()

        parser1 = get_insight_parser()
        parser2 = get_insight_parser()
        assert parser1 is parser2
