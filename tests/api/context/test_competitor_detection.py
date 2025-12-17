"""Unit tests for competitor detection quality improvements.

Tests validation heuristics, LLM extraction, and fallback search logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.api.context.competitors import (
    _extract_competitors_with_llm,
    _fallback_competitor_search,
    _is_valid_competitor_name,
)


class TestIsValidCompetitorName:
    """Tests for _is_valid_competitor_name validation function."""

    def test_rejects_empty_string(self):
        assert _is_valid_competitor_name("") is False

    def test_rejects_single_char(self):
        assert _is_valid_competitor_name("A") is False

    def test_rejects_too_long_name(self):
        # Names >40 chars are likely sentences, not company names
        long_name = "This Is A Very Long Name That Is Definitely A Sentence Not A Company"
        assert _is_valid_competitor_name(long_name) is False

    def test_rejects_starts_with_number(self):
        assert _is_valid_competitor_name("10 Best Tools") is False
        assert _is_valid_competitor_name("5 Top Companies") is False

    def test_rejects_starts_with_the_best(self):
        assert _is_valid_competitor_name("The best CRM software") is False

    def test_rejects_starts_with_top(self):
        assert _is_valid_competitor_name("Top productivity apps") is False

    def test_rejects_starts_with_best(self):
        assert _is_valid_competitor_name("Best project management") is False

    def test_rejects_starts_with_how_to(self):
        assert _is_valid_competitor_name("How to choose software") is False

    @pytest.mark.parametrize(
        "invalid_name",
        [
            "Best CRM Tools",
            "Top 10 Software",
            "Software Review 2025",
            "Compare Tools Guide",
            "Alternative Solutions",
            "Platform Comparison",
            "Tool Rankings",
            "Highly Rated Apps",
        ],
    )
    def test_rejects_generic_terms(self, invalid_name):
        """Test that names containing generic patterns are rejected."""
        assert _is_valid_competitor_name(invalid_name) is False

    @pytest.mark.parametrize(
        "valid_name",
        [
            "Notion",
            "Asana",
            "Monday",
            "HubSpot",
            "ClickUp",
            "Salesforce",
            "Linear",
            "Coda",
            "Airtable",
            "Figma",
        ],
    )
    def test_accepts_real_company_names(self, valid_name):
        """Test that real company names are accepted."""
        assert _is_valid_competitor_name(valid_name) is True

    def test_accepts_camelcase_names(self):
        """Test CamelCase company names."""
        assert _is_valid_competitor_name("HubSpot") is True
        assert _is_valid_competitor_name("ClickUp") is True
        assert _is_valid_competitor_name("BaseCamp") is True

    def test_accepts_domain_style_names(self):
        """Test names ending in domain suffixes."""
        assert _is_valid_competitor_name("monday.com") is True
        assert _is_valid_competitor_name("notion.io") is True
        assert _is_valid_competitor_name("linear.ai") is True
        assert _is_valid_competitor_name("example.co") is True

    def test_accepts_multi_word_proper_nouns(self):
        """Test multi-word company names."""
        assert _is_valid_competitor_name("Microsoft Teams") is True
        assert _is_valid_competitor_name("Google Workspace") is True
        assert _is_valid_competitor_name("Zoho Projects") is True

    def test_rejects_all_lowercase(self):
        """Test that all-lowercase strings are rejected."""
        assert _is_valid_competitor_name("notion") is False
        assert _is_valid_competitor_name("asana") is False


class TestExtractCompetitorsWithLLM:
    """Tests for LLM-based competitor extraction."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_results(self):
        """Test that empty results return empty list."""
        result = await _extract_competitors_with_llm([], None)
        assert result == []

    @pytest.mark.asyncio
    async def test_extracts_company_names_from_results(self):
        """Test LLM extraction from mixed results."""
        mock_results = [
            {
                "title": "Notion vs Competitors | G2 Reviews",
                "url": "https://g2.com/products/notion/competitors",
                "content": "Compare Notion to Asana, Monday, and ClickUp. See how they stack up.",
            },
            {
                "title": "Top 10 Project Management Tools 2025",
                "url": "https://example.com/best-tools",
                "content": "Best productivity software including Asana and Monday.com",
            },
        ]

        with patch("backend.api.context.competitors.ClaudeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.call.return_value = (
                '[{"name": "Asana", "url": "https://asana.com", "confidence": "high"}, '
                '{"name": "Monday.com", "url": "https://monday.com", "confidence": "high"}, '
                '{"name": "ClickUp", "url": "https://clickup.com", "confidence": "medium"}]',
                None,
            )
            mock_client_class.return_value = mock_client

            result = await _extract_competitors_with_llm(mock_results, "Notion")

            assert len(result) == 3
            assert result[0]["name"] == "Asana"
            assert result[1]["name"] == "Monday.com"
            assert result[2]["name"] == "ClickUp"

    @pytest.mark.asyncio
    async def test_filters_invalid_names_from_llm_response(self):
        """Test that invalid names from LLM are filtered out."""
        mock_results = [{"title": "Test", "url": "https://test.com", "content": "Test content"}]

        with patch("backend.api.context.competitors.ClaudeClient") as mock_client_class:
            mock_client = AsyncMock()
            # LLM returns mix of valid and invalid names
            mock_client.call.return_value = (
                '[{"name": "Asana", "confidence": "high"}, '
                '{"name": "Top 10 Tools", "confidence": "low"}, '
                '{"name": "Monday.com", "confidence": "high"}, '
                '{"name": "Best Software 2025", "confidence": "low"}]',
                None,
            )
            mock_client_class.return_value = mock_client

            result = await _extract_competitors_with_llm(mock_results, None)

            # Only valid names should remain
            names = [r["name"] for r in result]
            assert "Asana" in names
            assert "Monday.com" in names
            assert "Top 10 Tools" not in names
            assert "Best Software 2025" not in names

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self):
        """Test graceful handling of LLM errors."""
        mock_results = [{"title": "Test", "url": "https://test.com", "content": "Test"}]

        with patch("backend.api.context.competitors.ClaudeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.call.side_effect = Exception("LLM API error")
            mock_client_class.return_value = mock_client

            result = await _extract_competitors_with_llm(mock_results, None)

            assert result == []

    @pytest.mark.asyncio
    async def test_handles_malformed_json_response(self):
        """Test handling of malformed JSON from LLM."""
        mock_results = [{"title": "Test", "url": "https://test.com", "content": "Test"}]

        with patch("backend.api.context.competitors.ClaudeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.call.return_value = ("not valid json at all", None)
            mock_client_class.return_value = mock_client

            result = await _extract_competitors_with_llm(mock_results, None)

            assert result == []

    @pytest.mark.asyncio
    async def test_extracts_json_from_mixed_response(self):
        """Test extraction of JSON from response with surrounding text."""
        mock_results = [{"title": "Test", "url": "https://test.com", "content": "Test"}]

        with patch("backend.api.context.competitors.ClaudeClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.call.return_value = (
                'Here are the competitors:\n[{"name": "Asana", "confidence": "high"}]\nThat is all.',
                None,
            )
            mock_client_class.return_value = mock_client

            result = await _extract_competitors_with_llm(mock_results, None)

            assert len(result) == 1
            assert result[0]["name"] == "Asana"


class TestFallbackCompetitorSearch:
    """Tests for fallback search when initial results are insufficient."""

    @pytest.mark.asyncio
    async def test_fallback_search_uses_targeted_query(self):
        """Test that fallback uses more targeted query format."""
        with (
            patch("backend.api.context.competitors.httpx.AsyncClient") as mock_client_class,
            patch("backend.api.context.competitors._extract_competitors_with_llm") as mock_extract,
        ):
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status = AsyncMock()
            mock_client.post.return_value = mock_response

            # Use context manager mock
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = None

            mock_extract.return_value = []

            await _fallback_competitor_search("api_key", "Notion")

            # Check the query format
            call_args = mock_client.post.call_args
            query = call_args[1]["json"]["query"]
            assert '"Notion"' in query
            assert "vs" in query
            assert "alternatives" in query or "competitors" in query

    @pytest.mark.asyncio
    async def test_fallback_handles_http_error(self):
        """Test fallback gracefully handles HTTP errors."""
        with patch("backend.api.context.competitors.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("HTTP error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client_class.return_value.__aexit__.return_value = None

            result = await _fallback_competitor_search("api_key", "Notion")

            assert result == []


class TestIntegrationScenarios:
    """Integration-style tests for full competitor detection flow."""

    @pytest.mark.asyncio
    async def test_mixed_results_returns_only_valid_companies(self):
        """Test that mixed results are properly filtered to real companies."""
        # Simulate Tavily returning mix of good and bad results
        mock_results = [
            {
                "title": "Best Project Management Software 2025",
                "url": "https://example.com/best",
                "content": "Top rated tools for teams",
            },
            {
                "title": "Asana Reviews | G2",
                "url": "https://g2.com/products/asana",
                "content": "Asana is a work management platform",
            },
            {
                "title": "10 Notion Alternatives You Should Try",
                "url": "https://blog.com/alternatives",
                "content": "Check out Monday.com, ClickUp, and Coda",
            },
        ]

        with patch("backend.api.context.competitors.ClaudeClient") as mock_client_class:
            mock_client = AsyncMock()
            # LLM correctly extracts only company names
            mock_client.call.return_value = (
                '[{"name": "Asana", "url": "https://g2.com/products/asana", "confidence": "high"}, '
                '{"name": "Monday.com", "confidence": "high"}, '
                '{"name": "ClickUp", "confidence": "medium"}, '
                '{"name": "Coda", "confidence": "medium"}]',
                None,
            )
            mock_client_class.return_value = mock_client

            result = await _extract_competitors_with_llm(mock_results, "Notion")

            # Should only have real company names
            names = [r["name"] for r in result]
            assert all(
                name
                in [
                    "Asana",
                    "Monday.com",
                    "ClickUp",
                    "Coda",
                    "Notion",
                    "Linear",
                    "Airtable",
                ]
                for name in names
            )
            # Should not have generic terms
            assert "Best Project Management Software 2025" not in names
            assert "10 Notion Alternatives" not in names
