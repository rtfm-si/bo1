"""Tests for the enrichment service.

Tests the website enrichment functionality including:
- URL normalization and validation
- Website metadata extraction
- HTML tag parsing
- Claude-based context extraction

Uses mocking to avoid external API calls.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bo1.services.enrichment import EnrichedContext, EnrichmentService


class TestEnrichmentService:
    """Tests for EnrichmentService class."""

    def test_normalize_url_adds_https(self) -> None:
        """Test that URLs without scheme get https:// added."""
        service = EnrichmentService()
        assert service._normalize_url("example.com") == "https://example.com"
        assert service._normalize_url("www.example.com") == "https://www.example.com"

    def test_normalize_url_preserves_https(self) -> None:
        """Test that https:// URLs are preserved."""
        service = EnrichmentService()
        assert service._normalize_url("https://example.com") == "https://example.com"

    def test_normalize_url_preserves_http(self) -> None:
        """Test that http:// URLs are preserved (not upgraded)."""
        service = EnrichmentService()
        assert service._normalize_url("http://example.com") == "http://example.com"

    def test_normalize_url_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        service = EnrichmentService()
        assert service._normalize_url("  example.com  ") == "https://example.com"

    def test_normalize_url_invalid_raises(self) -> None:
        """Test that invalid URLs raise ValueError."""
        service = EnrichmentService()
        with pytest.raises(ValueError, match="Invalid URL"):
            service._normalize_url("")

    def test_extract_tag_title(self) -> None:
        """Test title tag extraction."""
        service = EnrichmentService()
        html = "<html><head><title>My Company</title></head></html>"
        assert service._extract_tag(html, "title") == "My Company"

    def test_extract_tag_missing(self) -> None:
        """Test that missing tags return None."""
        service = EnrichmentService()
        html = "<html><head></head></html>"
        assert service._extract_tag(html, "title") is None

    def test_extract_meta_description(self) -> None:
        """Test meta description extraction."""
        service = EnrichmentService()
        html = '<html><head><meta name="description" content="A great company"></head></html>'
        assert service._extract_meta(html, "description") == "A great company"

    def test_extract_meta_og_title(self) -> None:
        """Test Open Graph title extraction."""
        service = EnrichmentService()
        html = '<html><head><meta property="og:title" content="OG Title"></head></html>'
        assert service._extract_meta(html, "og:title") == "OG Title"

    def test_extract_meta_missing(self) -> None:
        """Test that missing meta tags return None."""
        service = EnrichmentService()
        html = "<html><head></head></html>"
        assert service._extract_meta(html, "description") is None

    def test_format_search_results_empty(self) -> None:
        """Test formatting empty search results."""
        service = EnrichmentService()
        assert service._format_search_results({}) == "No search results available."
        assert service._format_search_results({"results": []}) == ""

    def test_format_search_results_with_data(self) -> None:
        """Test formatting search results with data."""
        service = EnrichmentService()
        search_data = {
            "results": [
                {"title": "Result 1", "description": "Description 1"},
                {"title": "Result 2", "description": "Description 2"},
            ]
        }
        formatted = service._format_search_results(search_data)
        assert "1. Result 1" in formatted
        assert "Description 1" in formatted
        assert "2. Result 2" in formatted


class TestEnrichedContext:
    """Tests for the EnrichedContext model."""

    def test_default_values(self) -> None:
        """Test that EnrichedContext has sensible defaults."""
        context = EnrichedContext()
        assert context.company_name is None
        assert context.industry is None
        assert context.enrichment_source == "api"
        assert context.confidence == "medium"
        assert context.enrichment_date is not None

    def test_full_context(self) -> None:
        """Test creating a full EnrichedContext."""
        context = EnrichedContext(
            company_name="Acme Corp",
            website="https://acme.com",
            industry="SaaS",
            business_model="B2B SaaS",
            target_market="Enterprise",
            product_description="Project management software",
            confidence="high",
        )
        assert context.company_name == "Acme Corp"
        assert context.industry == "SaaS"
        assert context.confidence == "high"


@pytest.mark.asyncio
class TestEnrichmentServiceAsync:
    """Async tests for EnrichmentService."""

    async def test_fetch_website_metadata_success(self) -> None:
        """Test successful website metadata fetch."""
        service = EnrichmentService()

        mock_html = """
        <html>
        <head>
            <title>Test Company</title>
            <meta name="description" content="A test company">
            <meta property="og:title" content="Test Company OG">
            <meta name="keywords" content="test, company, demo">
        </head>
        <body>
            <h1>Welcome to Test Company</h1>
            <p>We are the best at testing.</p>
        </body>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(service.http_client, "get", return_value=mock_response):
            metadata = await service._fetch_website_metadata("https://test.com")

        assert metadata["title"] == "Test Company"
        assert metadata["description"] == "A test company"
        assert metadata["og_title"] == "Test Company OG"
        assert metadata["keywords"] == "test, company, demo"
        assert "Welcome to Test Company" in metadata["text_snippet"]

    async def test_fetch_website_metadata_detects_tech_stack(self) -> None:
        """Test that tech stack is detected from HTML."""
        service = EnrichmentService()

        mock_html = """
        <html data-reactroot>
        <head><title>React App</title></head>
        <body>
            <div id="__next">Next.js app</div>
            <script src="/wp-content/themes/test/script.js"></script>
        </body>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()

        with patch.object(service.http_client, "get", return_value=mock_response):
            metadata = await service._fetch_website_metadata("https://test.com")

        assert "React" in metadata["detected_tech"]
        assert "Next.js" in metadata["detected_tech"]
        assert "WordPress" in metadata["detected_tech"]

    async def test_fetch_website_metadata_handles_error(self) -> None:
        """Test that HTTP errors are handled gracefully."""
        service = EnrichmentService()

        with patch.object(
            service.http_client,
            "get",
            side_effect=httpx.HTTPError("Connection failed"),
        ):
            metadata = await service._fetch_website_metadata("https://test.com")

        assert metadata["url"] == "https://test.com"
        assert "error" in metadata

    async def test_search_company_info_no_api_key(self) -> None:
        """Test that search returns empty when no API key configured."""
        service = EnrichmentService()
        service.settings.brave_api_key = None

        result = await service._search_company_info("example.com")
        assert result == {}

    async def test_search_company_info_with_api_key(self) -> None:
        """Test company search with API key."""
        service = EnrichmentService()
        service.settings.brave_api_key = "test-api-key"

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "web": {
                    "results": [
                        {
                            "title": "About Us",
                            "description": "Company info",
                            "url": "https://example.com/about",
                        }
                    ]
                }
            }
        )
        mock_response.raise_for_status = MagicMock()

        with patch.object(service.http_client, "get", return_value=mock_response):
            result = await service._search_company_info("example.com")

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "About Us"

    async def test_extract_with_claude(self) -> None:
        """Test Claude-based context extraction."""
        service = EnrichmentService()

        mock_claude_response = json.dumps(
            {
                "company_name": "Acme Corp",
                "industry": "SaaS",
                "business_model": "B2B SaaS",
                "pricing_model": "Subscription",
                "target_market": "Enterprise",
                "product_description": "Project management",
                "confidence": "high",
            }
        )

        website_data = {
            "title": "Acme Corp",
            "description": "Project management software",
            "detected_tech": ["React", "Node.js"],
        }

        with patch.object(
            service.claude_client,
            "call",
            return_value=(mock_claude_response, {"input_tokens": 100, "output_tokens": 50}),
        ):
            context = await service._extract_with_claude(
                "https://acme.com",
                website_data,
                {},
            )

        assert context.company_name == "Acme Corp"
        assert context.industry == "SaaS"
        assert context.business_model == "B2B SaaS"
        assert context.confidence == "high"
        assert context.tech_stack == ["React", "Node.js"]

    async def test_extract_with_claude_handles_json_error(self) -> None:
        """Test that invalid JSON from Claude is handled gracefully."""
        service = EnrichmentService()

        # Return invalid JSON
        mock_claude_response = "This is not valid JSON"

        website_data = {
            "title": "Test Company",
            "description": "A test",
            "detected_tech": [],
        }

        with patch.object(
            service.claude_client,
            "call",
            return_value=(mock_claude_response, {"input_tokens": 100, "output_tokens": 50}),
        ):
            context = await service._extract_with_claude(
                "https://test.com",
                website_data,
                {},
            )

        # Should return a low-confidence result based on metadata only
        assert context.website == "https://test.com"
        # When JSON parsing fails entirely, we get empty dict, so company_name could be None
        # The actual behavior depends on whether the regex extraction works

    async def test_enrich_from_url_full_flow(self) -> None:
        """Test the full enrichment flow with all mocked components."""
        service = EnrichmentService()
        service.settings.brave_api_key = None  # Skip search

        mock_html = """
        <html>
        <head>
            <title>Demo Company</title>
            <meta name="description" content="We make demos">
        </head>
        <body><p>Welcome to Demo Company</p></body>
        </html>
        """

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_response.raise_for_status = MagicMock()

        mock_claude_response = json.dumps(
            {
                "company_name": "Demo Company",
                "industry": "Technology",
                "business_model": "B2B",
                "confidence": "medium",
            }
        )

        with (
            patch.object(service.http_client, "get", return_value=mock_response),
            patch.object(
                service.claude_client,
                "call",
                return_value=(mock_claude_response, {}),
            ),
        ):
            context = await service.enrich_from_url("demo.com")

        assert context.company_name == "Demo Company"
        assert context.website == "https://demo.com"
        assert context.industry == "Technology"

    async def test_close(self) -> None:
        """Test that close properly closes the HTTP client."""
        service = EnrichmentService()

        with patch.object(service.http_client, "aclose") as mock_aclose:
            await service.close()
            mock_aclose.assert_called_once()
