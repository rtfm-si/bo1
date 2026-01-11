"""Unit tests for competitor detection quality improvements.

Tests validation heuristics, LLM extraction, and fallback search logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.api.context.competitors import (
    _build_competitor_search_query,
    _deduplicate_competitors,
    _extract_competitors_with_llm,
    _fallback_competitor_search,
    _guess_domain_from_name,
    _is_valid_competitor_name,
    _normalize_competitor_name,
    _normalize_competitor_url,
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


class TestNormalizeCompetitorUrl:
    """Tests for URL normalization and domain extraction."""

    def test_extracts_domain_from_g2_url(self):
        """Test extracting domain from G2 link."""
        url = "https://g2.com/products/asana/reviews"
        result = _normalize_competitor_url(url, "Asana")
        # Should guess domain from company name since it's a G2 link
        assert result == "https://asana.com"

    def test_extracts_domain_from_capterra_url(self):
        """Test extracting domain from Capterra link."""
        url = "https://capterra.com/p/12345/monday-com/"
        result = _normalize_competitor_url(url, "Monday.com")
        assert result == "https://mondaycom.com"

    def test_keeps_actual_company_domain(self):
        """Test preserving actual company domain."""
        url = "https://notion.so/product"
        result = _normalize_competitor_url(url, "Notion")
        assert result == "https://notion.so"

    def test_guesses_domain_for_missing_url(self):
        """Test domain guessing when URL is None."""
        result = _normalize_competitor_url(None, "HubSpot")
        assert result == "https://hubspot.com"

    def test_handles_empty_company_name(self):
        """Test handling empty company name."""
        result = _normalize_competitor_url(None, "")
        assert result is None


class TestGuessDomainFromName:
    """Tests for domain guessing from company name."""

    def test_simple_name(self):
        """Test simple company name."""
        assert _guess_domain_from_name("Notion") == "https://notion.com"

    def test_name_with_spaces(self):
        """Test name with spaces."""
        assert _guess_domain_from_name("Hub Spot") == "https://hubspot.com"

    def test_name_with_special_chars(self):
        """Test name with special characters."""
        assert _guess_domain_from_name("Monday.com") == "https://mondaycom.com"

    def test_empty_name(self):
        """Test empty name returns None."""
        assert _guess_domain_from_name("") is None

    def test_single_char_name(self):
        """Test single character name returns None."""
        assert _guess_domain_from_name("A") is None


class TestNormalizeCompetitorName:
    """Tests for competitor name normalization."""

    def test_lowercase(self):
        """Test lowercase conversion."""
        assert _normalize_competitor_name("HubSpot") == "hubspot"

    def test_removes_inc_suffix(self):
        """Test removing Inc suffix."""
        assert _normalize_competitor_name("Acme, Inc.") == "acme"
        assert _normalize_competitor_name("Acme Inc") == "acme"

    def test_removes_llc_suffix(self):
        """Test removing LLC suffix."""
        assert _normalize_competitor_name("Acme, LLC") == "acme"

    def test_removes_domain_suffix(self):
        """Test removing domain suffixes."""
        assert _normalize_competitor_name("monday.com") == "monday"
        assert _normalize_competitor_name("notion.io") == "notion"
        assert _normalize_competitor_name("linear.ai") == "linear"

    def test_removes_software_suffix(self):
        """Test removing software/platform suffixes."""
        assert _normalize_competitor_name("Acme Software") == "acme"
        assert _normalize_competitor_name("Acme Platform") == "acme"

    def test_strips_whitespace(self):
        """Test stripping whitespace."""
        assert _normalize_competitor_name("  HubSpot  ") == "hubspot"

    def test_empty_name(self):
        """Test empty name."""
        assert _normalize_competitor_name("") == ""


class TestDeduplicateCompetitors:
    """Tests for competitor deduplication."""

    def test_removes_exact_duplicates(self):
        """Test removing exact duplicates."""
        competitors = [
            {"name": "HubSpot", "url": "https://hubspot.com"},
            {"name": "HubSpot", "url": "https://hubspot.com"},
        ]
        result = _deduplicate_competitors(competitors)
        assert len(result) == 1
        assert result[0]["name"] == "HubSpot"

    def test_merges_different_cases(self):
        """Test merging names with different cases."""
        competitors = [
            {"name": "HubSpot", "url": "https://hubspot.com"},
            {"name": "hubspot", "url": None},
        ]
        result = _deduplicate_competitors(competitors)
        assert len(result) == 1
        # Should keep the first one (with URL)
        assert result[0]["url"] == "https://hubspot.com"

    def test_merges_with_suffix_variations(self):
        """Test merging names with suffix variations."""
        competitors = [
            {"name": "monday.com", "url": "https://monday.com", "description": "Work OS"},
            {"name": "Monday", "url": None, "description": None},
        ]
        result = _deduplicate_competitors(competitors)
        assert len(result) == 1
        assert result[0]["description"] == "Work OS"

    def test_keeps_best_data(self):
        """Test keeping the best data from merged entries."""
        competitors = [
            {"name": "Asana", "url": None, "description": None, "confidence": "low"},
            {
                "name": "Asana Inc",
                "url": "https://asana.com",
                "description": "Work management",
                "confidence": "high",
            },
        ]
        result = _deduplicate_competitors(competitors)
        assert len(result) == 1
        # Should have URL and description from second entry
        assert result[0]["url"] == "https://asana.com"
        assert result[0]["description"] == "Work management"
        # Should have higher confidence
        assert result[0]["confidence"] == "high"

    def test_preserves_unique_competitors(self):
        """Test that unique competitors are preserved."""
        competitors = [
            {"name": "HubSpot", "url": "https://hubspot.com"},
            {"name": "Salesforce", "url": "https://salesforce.com"},
            {"name": "Pipedrive", "url": "https://pipedrive.com"},
        ]
        result = _deduplicate_competitors(competitors)
        assert len(result) == 3
        names = [c["name"] for c in result]
        assert "HubSpot" in names
        assert "Salesforce" in names
        assert "Pipedrive" in names

    def test_handles_empty_list(self):
        """Test handling empty list."""
        result = _deduplicate_competitors([])
        assert result == []

    def test_skips_empty_names(self):
        """Test skipping entries with empty names."""
        competitors = [
            {"name": "HubSpot", "url": "https://hubspot.com"},
            {"name": "", "url": "https://example.com"},
            {"name": None, "url": "https://test.com"},
        ]
        result = _deduplicate_competitors(competitors)
        assert len(result) == 1
        assert result[0]["name"] == "HubSpot"


class TestBuildCompetitorSearchQuery:
    """Tests for _build_competitor_search_query with context-aware query building."""

    def test_company_name_takes_priority(self):
        """Test that company name is used directly when available."""
        result = _build_competitor_search_query(
            company_name="Acme Corp",
            industry="SaaS",
            product_description="Project management tool",
            target_market="Enterprise",
            business_model="B2B",
        )
        assert result == '"Acme Corp" competitors alternatives'

    def test_b2b_business_model(self):
        """Test B2B business model is included in query."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Healthcare",
            product_description=None,
            target_market=None,
            business_model="B2B SaaS",
        )
        assert "B2B" in result
        assert "Healthcare" in result

    def test_b2c_business_model(self):
        """Test B2C business model is included in query."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="E-commerce",
            product_description=None,
            target_market=None,
            business_model="B2C",
        )
        assert "B2C" in result
        assert "E-commerce" in result

    def test_saas_business_model(self):
        """Test SaaS business model is included in query."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Project Management",
            product_description=None,
            target_market=None,
            business_model="SaaS platform",
        )
        assert "SaaS" in result

    def test_marketplace_business_model(self):
        """Test marketplace business model is included in query."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Freelance",
            product_description=None,
            target_market=None,
            business_model="Two-sided marketplace",
        )
        assert "marketplace" in result

    def test_enterprise_target_market(self):
        """Test enterprise target market is included."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="CRM",
            product_description=None,
            target_market="Large Enterprise companies",
            business_model=None,
        )
        assert "enterprise" in result
        assert "CRM" in result

    def test_smb_target_market(self):
        """Test SMB target market is included."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Accounting",
            product_description=None,
            target_market="SMBs and small businesses",
            business_model=None,
        )
        assert "SMB" in result

    def test_startup_target_market(self):
        """Test startup target market is included."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Dev tools",
            product_description=None,
            target_market="Early-stage startups",
            business_model=None,
        )
        assert "startup" in result

    def test_product_description_truncated(self):
        """Test long product descriptions are truncated properly."""
        long_desc = "A comprehensive project management solution that helps teams collaborate effectively and track progress"
        result = _build_competitor_search_query(
            company_name=None,
            industry=None,
            product_description=long_desc,
            target_market=None,
            business_model=None,
        )
        # Should not include the full description
        assert len(result) < len(long_desc) + 50
        # Should end at a word boundary
        assert not result.endswith(" and")

    def test_all_context_combined(self):
        """Test all context fields are combined properly."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Marketing",
            product_description="Email automation for marketers",
            target_market="SMB companies",
            business_model="B2B SaaS",
        )
        assert "B2B" in result
        assert "Marketing" in result
        assert "SMB" in result
        # Product desc should be included
        assert "Email automation" in result

    def test_fallback_with_no_context(self):
        """Test fallback query when no context is provided."""
        result = _build_competitor_search_query(
            company_name=None,
            industry=None,
            product_description=None,
            target_market=None,
            business_model=None,
        )
        assert "software" in result.lower()
        assert "competitors" in result.lower()

    def test_industry_only(self):
        """Test query with only industry provided."""
        result = _build_competitor_search_query(
            company_name=None,
            industry="Fintech",
            product_description=None,
            target_market=None,
            business_model=None,
        )
        assert "Fintech" in result
        assert "competitors" in result.lower()
