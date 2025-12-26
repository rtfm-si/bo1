"""Tests for TrendSummaryGenerator service."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services.trend_summary_generator import (
    TIMEFRAME_LABELS,
    TREND_FORECAST_TIER_LIMITS,
    TrendSummaryGenerator,
    TrendSummaryResult,
    build_trend_summary_prompt,
    get_available_timeframes,
    get_trend_summary_generator,
    strip_html_to_text,
)


class TestBuildTrendSummaryPrompt:
    """Tests for building the trend summary prompt."""

    def test_build_prompt_with_results(self):
        """Test prompt building with search results."""
        industry = "SaaS"
        results = [
            {
                "title": "SaaS Trends 2025",
                "url": "https://example.com/1",
                "snippet": "Key trends...",
            },
            {"title": "Market Report", "url": "https://example.com/2", "snippet": "Analysis..."},
        ]

        prompt = build_trend_summary_prompt(industry, results)

        assert "SaaS" in prompt
        assert "SaaS Trends 2025" in prompt
        assert "Market Report" in prompt
        assert "https://example.com/1" in prompt
        assert "Key trends..." in prompt
        assert "JSON only" in prompt

    def test_build_prompt_limits_results(self):
        """Test prompt limits to 10 results."""
        industry = "Tech"
        results = [
            {"title": f"Article {i}", "url": f"https://x.com/{i}", "snippet": f"Snippet {i}"}
            for i in range(15)
        ]

        prompt = build_trend_summary_prompt(industry, results)

        # Should only include first 10
        assert "Article 9" in prompt
        assert "Article 10" not in prompt

    def test_build_prompt_handles_missing_fields(self):
        """Test prompt handles missing fields gracefully."""
        industry = "Finance"
        results = [
            {"title": "Article", "url": "https://x.com", "snippet": ""},
            {"url": "https://y.com"},
        ]

        prompt = build_trend_summary_prompt(industry, results)

        assert "No title" in prompt
        assert "No description" in prompt or prompt.count("snippet") == 0

    def test_build_prompt_includes_timeframe(self):
        """Test prompt includes timeframe reference."""
        industry = "Tech"
        results = [{"title": "Article", "url": "https://x.com", "snippet": "Test"}]

        prompt_3m = build_trend_summary_prompt(industry, results, "3m")
        prompt_12m = build_trend_summary_prompt(industry, results, "12m")
        prompt_24m = build_trend_summary_prompt(industry, results, "24m")

        assert "3 months" in prompt_3m
        assert "12 months" in prompt_12m
        assert "24 months" in prompt_24m

    def test_build_prompt_defaults_to_3m(self):
        """Test prompt defaults to 3 months timeframe."""
        industry = "Tech"
        results = [{"title": "Article", "url": "https://x.com", "snippet": "Test"}]

        prompt = build_trend_summary_prompt(industry, results)

        assert "3 months" in prompt


class TestTrendSummaryGenerator:
    """Tests for TrendSummaryGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return TrendSummaryGenerator()

    @pytest.fixture
    def mock_brave_response(self):
        """Mock Brave Search response."""
        return {
            "web": {
                "results": [
                    {
                        "title": "Tech Trends 2025",
                        "url": "https://techcrunch.com/trends",
                        "description": "The latest technology trends...",
                    },
                    {
                        "title": "Industry Report",
                        "url": "https://forbes.com/report",
                        "description": "Market analysis for 2025...",
                    },
                ]
            }
        }

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response JSON."""
        return json.dumps(
            {
                "summary": "The tech industry is experiencing rapid AI adoption.",
                "key_trends": ["AI adoption", "Cloud migration", "Cybersecurity focus"],
                "opportunities": ["AI-powered products", "Cloud services"],
                "threats": ["Regulatory uncertainty", "Talent shortage"],
            }
        )

    @pytest.mark.asyncio
    async def test_generate_summary_success(
        self, generator, mock_brave_response, mock_llm_response
    ):
        """Test successful summary generation."""
        with (
            patch.object(generator, "_brave_search", new_callable=AsyncMock) as mock_search,
            patch.object(generator, "_get_broker") as mock_get_broker,
        ):
            mock_search.return_value = mock_brave_response["web"]["results"]

            mock_broker = MagicMock()
            mock_response = MagicMock()
            mock_response.text = mock_llm_response
            mock_broker.call = AsyncMock(return_value=mock_response)
            mock_get_broker.return_value = mock_broker

            result = await generator.generate_summary("Technology")

            assert result.status == "complete"
            assert result.summary == "The tech industry is experiencing rapid AI adoption."
            assert len(result.key_trends) == 3
            assert "AI adoption" in result.key_trends
            assert len(result.opportunities) == 2
            assert len(result.threats) == 2
            assert result.industry == "Technology"
            assert result.generated_at is not None

    @pytest.mark.asyncio
    async def test_generate_summary_empty_industry(self, generator):
        """Test error when industry is empty."""
        result = await generator.generate_summary("")

        assert result.status == "error"
        assert "Industry is required" in result.error

    @pytest.mark.asyncio
    async def test_generate_summary_short_industry(self, generator):
        """Test error when industry is too short."""
        result = await generator.generate_summary("X")

        assert result.status == "error"
        assert "Industry is required" in result.error

    @pytest.mark.asyncio
    async def test_generate_summary_no_search_results(self, generator):
        """Test error when search returns no results."""
        with patch.object(generator, "_brave_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            result = await generator.generate_summary("Technology")

            assert result.status == "error"
            assert "search API unavailable" in result.error

    @pytest.mark.asyncio
    async def test_generate_summary_llm_parse_error(self, generator, mock_brave_response):
        """Test handling of LLM parse errors."""
        with (
            patch.object(generator, "_brave_search", new_callable=AsyncMock) as mock_search,
            patch.object(generator, "_get_broker") as mock_get_broker,
        ):
            mock_search.return_value = mock_brave_response["web"]["results"]

            mock_broker = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Not valid JSON"
            mock_broker.call = AsyncMock(return_value=mock_response)
            mock_get_broker.return_value = mock_broker

            result = await generator.generate_summary("Technology")

            assert result.status == "error"
            assert result.industry == "Technology"

    @pytest.mark.asyncio
    async def test_brave_search_success(self, mock_brave_response):
        """Test successful Brave Search call."""
        # Create new generator instance within the patch context
        with (
            patch("bo1.config.get_settings") as mock_settings,
            patch(
                "backend.services.trend_summary_generator.get_service_circuit_breaker"
            ) as mock_cb,
            patch("backend.services.trend_summary_generator.get_cost_context") as mock_ctx,
            patch("backend.services.trend_summary_generator.httpx.AsyncClient") as mock_client,
        ):
            mock_settings_instance = MagicMock()
            mock_settings_instance.brave_api_key = "test-key"
            mock_settings.return_value = mock_settings_instance

            mock_cb.return_value.state.value = "closed"
            mock_cb.return_value._record_success_sync = MagicMock()
            mock_ctx.return_value = {}

            mock_response = MagicMock()
            mock_response.json.return_value = mock_brave_response
            mock_response.raise_for_status = MagicMock()

            mock_async_client = MagicMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock()
            mock_client.return_value = mock_async_client

            # Create generator after patching settings
            generator = TrendSummaryGenerator()
            generator._settings = mock_settings_instance

            results = await generator._brave_search("Technology")

            assert len(results) == 2
            assert results[0]["title"] == "Tech Trends 2025"

    @pytest.mark.asyncio
    async def test_brave_search_no_api_key(self, generator):
        """Test Brave Search returns empty when no API key."""
        mock_settings = MagicMock()
        mock_settings.brave_api_key = None
        generator._settings = mock_settings

        results = await generator._brave_search("Technology")

        assert results == []

    @pytest.mark.asyncio
    async def test_brave_search_circuit_breaker_open(self, generator):
        """Test Brave Search returns empty when circuit breaker is open."""
        with (
            patch("backend.services.trend_summary_generator.get_settings") as mock_settings,
            patch(
                "backend.services.trend_summary_generator.get_service_circuit_breaker"
            ) as mock_cb,
        ):
            mock_settings.return_value.brave_api_key = "test-key"
            mock_cb.return_value.state.value = "open"

            results = await generator._brave_search("Technology")

            assert results == []


class TestTrendSummaryResult:
    """Tests for TrendSummaryResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = TrendSummaryResult(
            summary="Test summary",
            key_trends=["Trend 1", "Trend 2"],
            opportunities=["Opportunity 1"],
            threats=["Threat 1"],
            generated_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            industry="Tech",
            status="complete",
        )

        data = result.to_dict()

        assert data["summary"] == "Test summary"
        assert len(data["key_trends"]) == 2
        assert data["industry"] == "Tech"
        assert "2025-01-15" in data["generated_at"]

    def test_to_dict_with_none_values(self):
        """Test to_dict handles None values."""
        result = TrendSummaryResult(status="error", error="Failed")

        data = result.to_dict()

        assert data["summary"] is None
        assert data["key_trends"] == []
        assert data["generated_at"] is None


class TestGetTrendSummaryGenerator:
    """Tests for singleton getter."""

    def test_returns_singleton(self):
        """Test that generator is a singleton."""
        gen1 = get_trend_summary_generator()
        gen2 = get_trend_summary_generator()

        assert gen1 is gen2

    def test_returns_generator_instance(self):
        """Test that getter returns TrendSummaryGenerator instance."""
        gen = get_trend_summary_generator()

        assert isinstance(gen, TrendSummaryGenerator)


class TestParseListLimits:
    """Tests for list parsing with limits."""

    def test_parse_summary_limits_key_trends(self):
        """Test that key_trends are limited to MAX_KEY_TRENDS."""
        generator = TrendSummaryGenerator()

        response_text = json.dumps(
            {
                "summary": "Summary",
                "key_trends": ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
                "opportunities": ["O1"],
                "threats": ["T1"],
            }
        )

        result = generator._parse_summary(response_text, "Tech")

        assert len(result.key_trends) <= generator.MAX_KEY_TRENDS

    def test_parse_summary_limits_opportunities(self):
        """Test that opportunities are limited to MAX_OPPORTUNITIES."""
        generator = TrendSummaryGenerator()

        response_text = json.dumps(
            {
                "summary": "Summary",
                "key_trends": ["T1"],
                "opportunities": ["O1", "O2", "O3", "O4", "O5", "O6"],
                "threats": ["T1"],
            }
        )

        result = generator._parse_summary(response_text, "Tech")

        assert len(result.opportunities) <= generator.MAX_OPPORTUNITIES

    def test_parse_summary_limits_threats(self):
        """Test that threats are limited to MAX_THREATS."""
        generator = TrendSummaryGenerator()

        response_text = json.dumps(
            {
                "summary": "Summary",
                "key_trends": ["T1"],
                "opportunities": ["O1"],
                "threats": ["T1", "T2", "T3", "T4", "T5", "T6"],
            }
        )

        result = generator._parse_summary(response_text, "Tech")

        assert len(result.threats) <= generator.MAX_THREATS


class TestTierGating:
    """Tests for tier-based timeframe access."""

    def test_tier_limits_defined(self):
        """Test that tier limits are properly defined."""
        assert "free" in TREND_FORECAST_TIER_LIMITS
        assert "starter" in TREND_FORECAST_TIER_LIMITS
        assert "pro" in TREND_FORECAST_TIER_LIMITS
        assert "enterprise" in TREND_FORECAST_TIER_LIMITS

    def test_free_tier_only_3m(self):
        """Test that free tier only has 3m access."""
        available = get_available_timeframes("free")
        assert available == ["3m"]

    def test_starter_tier_has_3m_only(self):
        """Test that starter tier only has 3m access (12m/24m require pro)."""
        available = get_available_timeframes("starter")
        assert available == ["3m"]
        assert "12m" not in available
        assert "24m" not in available

    def test_pro_tier_has_all_timeframes(self):
        """Test that pro tier has all timeframes."""
        available = get_available_timeframes("pro")
        assert "3m" in available
        assert "12m" in available
        assert "24m" in available

    def test_enterprise_tier_has_all_timeframes(self):
        """Test that enterprise tier has all timeframes."""
        available = get_available_timeframes("enterprise")
        assert "3m" in available
        assert "12m" in available
        assert "24m" in available

    def test_unknown_tier_defaults_to_3m(self):
        """Test that unknown tier defaults to 3m only."""
        available = get_available_timeframes("unknown_tier")
        assert available == ["3m"]

    def test_timeframe_labels_defined(self):
        """Test that timeframe labels are properly defined."""
        assert TIMEFRAME_LABELS["3m"] == "3 months"
        assert TIMEFRAME_LABELS["12m"] == "12 months"
        assert TIMEFRAME_LABELS["24m"] == "24 months"


class TestTrendSummaryResultWithTimeframe:
    """Tests for TrendSummaryResult with timeframe support."""

    def test_to_dict_includes_timeframe(self):
        """Test that to_dict includes timeframe fields."""
        result = TrendSummaryResult(
            summary="Test",
            key_trends=["T1"],
            opportunities=["O1"],
            threats=["T1"],
            generated_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            industry="Tech",
            timeframe="12m",
            available_timeframes=["3m", "12m"],
            status="complete",
        )

        data = result.to_dict()

        assert data["timeframe"] == "12m"
        assert data["available_timeframes"] == ["3m", "12m"]

    def test_default_timeframe_is_3m(self):
        """Test that default timeframe is 3m."""
        result = TrendSummaryResult(status="complete")

        assert result.timeframe == "3m"
        data = result.to_dict()
        assert data["timeframe"] == "3m"

    def test_default_available_timeframes(self):
        """Test that default available_timeframes is [3m]."""
        result = TrendSummaryResult(status="complete")

        data = result.to_dict()
        assert data["available_timeframes"] == ["3m"]


class TestStripHtmlToText:
    """Tests for HTML-to-text conversion."""

    def test_strips_basic_tags(self):
        """Test stripping basic HTML tags."""
        html = "<p>Hello <strong>world</strong></p>"
        text = strip_html_to_text(html)
        assert "Hello" in text
        assert "world" in text
        assert "<p>" not in text
        assert "<strong>" not in text

    def test_removes_script_tags(self):
        """Test script tags are removed completely."""
        html = "<p>Before</p><script>alert('xss')</script><p>After</p>"
        text = strip_html_to_text(html)
        assert "Before" in text
        assert "After" in text
        assert "alert" not in text
        assert "script" not in text

    def test_removes_style_tags(self):
        """Test style tags are removed completely."""
        html = "<p>Content</p><style>.foo{color:red}</style>"
        text = strip_html_to_text(html)
        assert "Content" in text
        assert ".foo" not in text
        assert "color" not in text

    def test_decodes_html_entities(self):
        """Test HTML entities are decoded."""
        html = "<p>Price: &pound;50 &amp; &lt;more&gt;</p>"
        text = strip_html_to_text(html)
        assert "£" in text
        assert "&" in text
        assert "<more>" in text

    def test_normalizes_whitespace(self):
        """Test multiple spaces are collapsed."""
        html = "<p>Word1     Word2</p>"
        text = strip_html_to_text(html)
        assert "Word1 Word2" in text

    def test_respects_max_chars(self):
        """Test content is truncated to max_chars."""
        html = "<p>" + "A" * 1000 + "</p>"
        text = strip_html_to_text(html, max_chars=100)
        assert len(text) <= 100

    def test_handles_empty_input(self):
        """Test empty input returns empty string."""
        assert strip_html_to_text("") == ""
        assert strip_html_to_text(None) == ""


class TestBuildTrendSummaryPromptWithContent:
    """Tests for prompt building with extracted content."""

    def test_includes_content_when_present(self):
        """Test that extracted content is included in prompt."""
        industry = "SaaS"
        results = [
            {
                "title": "SaaS Trends",
                "url": "https://example.com",
                "snippet": "Brief snippet",
                "content": "Full article content about SaaS trends and market analysis.",
            }
        ]

        prompt = build_trend_summary_prompt(industry, results)

        assert "Article Content:" in prompt
        assert "Full article content" in prompt

    def test_truncates_long_content(self):
        """Test that content longer than 1500 chars is truncated."""
        long_content = "A" * 2000
        results = [
            {
                "title": "Test",
                "url": "https://x.com",
                "snippet": "Snippet",
                "content": long_content,
            }
        ]

        prompt = build_trend_summary_prompt("Tech", results)

        # Should include truncated content with ellipsis
        assert "A" * 100 in prompt  # Has some A's
        assert "..." in prompt  # Has truncation indicator
        # Original 2000 chars shouldn't all be there
        assert long_content not in prompt

    def test_works_without_content(self):
        """Test prompt works when content is missing."""
        results = [{"title": "Test", "url": "https://x.com", "snippet": "Just snippet"}]

        prompt = build_trend_summary_prompt("Tech", results)

        assert "Just snippet" in prompt
        assert "Article Content:" not in prompt


class TestFetchUrlContent:
    """Tests for URL content fetching."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return TrendSummaryGenerator()

    @pytest.mark.asyncio
    async def test_fetches_html_content(self, generator):
        """Test fetching and extracting HTML content."""
        # Content must be >100 chars to pass the minimum viable content check
        html_response = (
            "<html><body><p>Test article content here with enough text to pass the "
            "minimum content length check which requires at least 100 characters.</p></body></html>"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.headers = {"content-type": "text/html; charset=utf-8"}
            mock_response.raise_for_status = MagicMock()

            mock_async_client = MagicMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock()
            mock_client.return_value = mock_async_client

            content = await generator._fetch_url_content("https://example.com/article")

            assert content is not None
            assert "Test article content" in content

    @pytest.mark.asyncio
    async def test_returns_none_on_timeout(self, generator):
        """Test returns None on timeout."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = MagicMock()
            mock_async_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock()
            mock_client.return_value = mock_async_client

            content = await generator._fetch_url_content("https://example.com/slow")

            assert content is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self, generator):
        """Test returns None on HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404

            mock_async_client = MagicMock()
            mock_async_client.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not found", request=MagicMock(), response=mock_response
                )
            )
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock()
            mock_client.return_value = mock_async_client

            content = await generator._fetch_url_content("https://example.com/missing")

            assert content is None

    @pytest.mark.asyncio
    async def test_returns_none_for_non_html(self, generator):
        """Test returns None for non-HTML content types."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "binary data"
            mock_response.headers = {"content-type": "application/pdf"}
            mock_response.raise_for_status = MagicMock()

            mock_async_client = MagicMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock()
            mock_client.return_value = mock_async_client

            content = await generator._fetch_url_content("https://example.com/file.pdf")

            assert content is None

    @pytest.mark.asyncio
    async def test_returns_none_for_short_content(self, generator):
        """Test returns None when extracted content is too short."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><body>Hi</body></html>"  # Very short
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status = MagicMock()

            mock_async_client = MagicMock()
            mock_async_client.get = AsyncMock(return_value=mock_response)
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock()
            mock_client.return_value = mock_async_client

            content = await generator._fetch_url_content("https://example.com/tiny")

            assert content is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_url(self, generator):
        """Test returns None for empty URL."""
        content = await generator._fetch_url_content("")
        assert content is None

        content = await generator._fetch_url_content(None)
        assert content is None


class TestEnrichSearchResults:
    """Tests for batch content enrichment."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return TrendSummaryGenerator()

    @pytest.mark.asyncio
    async def test_enriches_top_results(self, generator):
        """Test enriches top N results with content."""
        results = [
            {"title": "Article 1", "url": "https://a.com", "snippet": "S1"},
            {"title": "Article 2", "url": "https://b.com", "snippet": "S2"},
            {"title": "Article 3", "url": "https://c.com", "snippet": "S3"},
            {"title": "Article 4", "url": "https://d.com", "snippet": "S4"},
        ]

        with patch.object(
            generator,
            "_fetch_url_content",
            new_callable=AsyncMock,
            side_effect=["Content A", "Content B", "Content C"],
        ):
            enriched, count = await generator._enrich_search_results(results)

            assert count == 3
            assert enriched[0].get("content") == "Content A"
            assert enriched[1].get("content") == "Content B"
            assert enriched[2].get("content") == "Content C"
            # 4th result not fetched (limit is 3)
            assert enriched[3].get("content") is None

    @pytest.mark.asyncio
    async def test_handles_partial_failures(self, generator):
        """Test handles some URLs failing."""
        results = [
            {"title": "Article 1", "url": "https://a.com", "snippet": "S1"},
            {"title": "Article 2", "url": "https://b.com", "snippet": "S2"},
            {"title": "Article 3", "url": "https://c.com", "snippet": "S3"},
        ]

        with patch.object(
            generator,
            "_fetch_url_content",
            new_callable=AsyncMock,
            side_effect=["Content A", None, "Content C"],  # Middle one fails
        ):
            enriched, count = await generator._enrich_search_results(results)

            assert count == 2  # Only 2 succeeded
            assert enriched[0].get("content") == "Content A"
            assert enriched[1].get("content") is None
            assert enriched[2].get("content") == "Content C"

    @pytest.mark.asyncio
    async def test_handles_empty_results(self, generator):
        """Test handles empty results list."""
        enriched, count = await generator._enrich_search_results([])

        assert enriched == []
        assert count == 0

    @pytest.mark.asyncio
    async def test_handles_missing_urls(self, generator):
        """Test handles results without URLs."""
        results = [
            {"title": "Article 1", "snippet": "S1"},  # No URL
            {"title": "Article 2", "url": "", "snippet": "S2"},  # Empty URL
        ]

        enriched, count = await generator._enrich_search_results(results)

        assert count == 0


class TestTrendSummaryResultSourcesEnriched:
    """Tests for sources_enriched field."""

    def test_to_dict_includes_sources_enriched(self):
        """Test that to_dict includes sources_enriched."""
        result = TrendSummaryResult(
            summary="Test",
            key_trends=["T1"],
            opportunities=["O1"],
            threats=["T1"],
            industry="Tech",
            sources_enriched=2,
            status="complete",
        )

        data = result.to_dict()

        assert "sources_enriched" in data
        assert data["sources_enriched"] == 2

    def test_default_sources_enriched_is_zero(self):
        """Test default sources_enriched is 0."""
        result = TrendSummaryResult(status="complete")

        assert result.sources_enriched == 0
        assert result.to_dict()["sources_enriched"] == 0
