"""Unit tests for trend analyzer service.

Tests URL fetching, content extraction, LLM integration, and error handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.trend_analyzer import TrendAnalyzer, TrendInsightResult, get_trend_analyzer


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> TrendAnalyzer:
        """Create a TrendAnalyzer instance."""
        return TrendAnalyzer()

    def test_extract_title_from_html(self, analyzer: TrendAnalyzer) -> None:
        """Test title extraction from HTML."""
        html = """
        <html>
        <head><title>Test Article Title</title></head>
        <body>Content here</body>
        </html>
        """
        title = analyzer._extract_title(html)
        assert title == "Test Article Title"

    def test_extract_title_from_og_tag(self, analyzer: TrendAnalyzer) -> None:
        """Test title extraction from og:title meta tag."""
        html = """
        <html>
        <head>
        <meta property="og:title" content="Open Graph Title" />
        </head>
        </html>
        """
        title = analyzer._extract_title(html)
        assert title == "Open Graph Title"

    def test_extract_title_missing_returns_none(self, analyzer: TrendAnalyzer) -> None:
        """Test that missing title returns None."""
        html = "<html><head></head><body>No title</body></html>"
        title = analyzer._extract_title(html)
        assert title is None

    def test_extract_text_removes_scripts(self, analyzer: TrendAnalyzer) -> None:
        """Test that script tags are removed from extracted text."""
        html = """
        <html>
        <body>
        <script>console.log('removed');</script>
        <p>This text should remain</p>
        <script type="text/javascript">more scripts</script>
        </body>
        </html>
        """
        text = analyzer._extract_text(html)
        assert "console.log" not in text
        assert "removed" not in text
        assert "This text should remain" in text

    def test_extract_text_removes_styles(self, analyzer: TrendAnalyzer) -> None:
        """Test that style tags are removed from extracted text."""
        html = """
        <html>
        <head><style>.hidden { display: none; }</style></head>
        <body><p>Content here</p></body>
        </html>
        """
        text = analyzer._extract_text(html)
        assert "display: none" not in text
        assert "Content here" in text

    def test_extract_text_truncates_long_content(self, analyzer: TrendAnalyzer) -> None:
        """Test that extracted text is truncated to max length."""
        long_content = "x" * 20000
        html = f"<html><body><p>{long_content}</p></body></html>"
        text = analyzer._extract_text(html)
        assert len(text) <= analyzer.MAX_CONTENT_LENGTH

    def test_parse_insight_valid_json(self, analyzer: TrendAnalyzer) -> None:
        """Test parsing valid JSON response."""
        response = """
        {
            "title": "AI Revolution",
            "key_takeaway": "AI is changing everything",
            "relevance": "Your SaaS can leverage AI",
            "actions": ["Integrate AI", "Train team"],
            "timeframe": "short_term",
            "confidence": "high"
        }
        """
        result = analyzer._parse_insight(response, "https://example.com", None)

        assert result.status == "complete"
        assert result.title == "AI Revolution"
        assert result.key_takeaway == "AI is changing everything"
        assert result.relevance == "Your SaaS can leverage AI"
        assert result.actions == ["Integrate AI", "Train team"]
        assert result.timeframe == "short_term"
        assert result.confidence == "high"

    def test_parse_insight_with_markdown_wrapping(self, analyzer: TrendAnalyzer) -> None:
        """Test parsing JSON response wrapped in markdown code blocks."""
        response = """
        ```json
        {
            "title": "Test Title",
            "key_takeaway": "Test takeaway",
            "relevance": "Test relevance",
            "actions": ["Action 1"],
            "timeframe": "immediate",
            "confidence": "medium"
        }
        ```
        """
        result = analyzer._parse_insight(response, "https://example.com", None)

        assert result.status == "complete"
        assert result.title == "Test Title"
        assert result.timeframe == "immediate"

    def test_parse_insight_invalid_json_returns_error(self, analyzer: TrendAnalyzer) -> None:
        """Test that invalid JSON returns fallback result."""
        response = "This is not JSON at all"
        result = analyzer._parse_insight(response, "https://example.com", "Fallback Title")

        assert result.status == "error"
        assert "Parse error" in (result.error or "")
        assert result.title == "Fallback Title"  # Uses fallback title

    def test_parse_insight_normalizes_invalid_timeframe(self, analyzer: TrendAnalyzer) -> None:
        """Test that invalid timeframe values are normalized."""
        response = """
        {
            "title": "Test",
            "key_takeaway": "Test",
            "relevance": "Test",
            "actions": [],
            "timeframe": "invalid_value",
            "confidence": "high"
        }
        """
        result = analyzer._parse_insight(response, "https://example.com", None)

        assert result.timeframe == "short_term"  # Defaults to short_term

    def test_parse_insight_normalizes_invalid_confidence(self, analyzer: TrendAnalyzer) -> None:
        """Test that invalid confidence values are normalized."""
        response = """
        {
            "title": "Test",
            "key_takeaway": "Test",
            "relevance": "Test",
            "actions": [],
            "timeframe": "short_term",
            "confidence": "very_high"
        }
        """
        result = analyzer._parse_insight(response, "https://example.com", None)

        assert result.confidence == "medium"  # Defaults to medium

    def test_safe_str_truncates(self, analyzer: TrendAnalyzer) -> None:
        """Test that _safe_str truncates to max length."""
        long_string = "x" * 1000
        result = analyzer._safe_str(long_string, 100)
        assert result is not None
        assert len(result) == 100

    def test_safe_str_handles_none(self, analyzer: TrendAnalyzer) -> None:
        """Test that _safe_str handles None input."""
        result = analyzer._safe_str(None, 100)
        assert result is None

    def test_safe_list_limits_items(self, analyzer: TrendAnalyzer) -> None:
        """Test that _safe_list limits number of items."""
        long_list = [f"item{i}" for i in range(10)]
        result = analyzer._safe_list(long_list, 3)
        assert len(result) == 3

    def test_safe_list_handles_non_list(self, analyzer: TrendAnalyzer) -> None:
        """Test that _safe_list handles non-list input."""
        result = analyzer._safe_list("not a list", 3)
        assert result == []

        result = analyzer._safe_list(None, 3)
        assert result == []

    def test_fallback_insight(self, analyzer: TrendAnalyzer) -> None:
        """Test fallback insight generation."""
        result = analyzer._fallback_insight("https://example.com", "Test Title", "Test error")

        assert result.status == "error"
        assert result.error == "Test error"
        assert result.url == "https://example.com"
        assert result.title == "Test Title"
        assert result.confidence == "low"
        assert result.analyzed_at is not None


class TestTrendInsightResult:
    """Tests for TrendInsightResult dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        now = datetime.now(UTC)
        result = TrendInsightResult(
            url="https://example.com",
            title="Test Title",
            key_takeaway="Test takeaway",
            relevance="Test relevance",
            actions=["Action 1", "Action 2"],
            timeframe="short_term",
            confidence="high",
            analyzed_at=now,
            status="complete",
        )

        d = result.to_dict()

        assert d["url"] == "https://example.com"
        assert d["title"] == "Test Title"
        assert d["key_takeaway"] == "Test takeaway"
        assert d["relevance"] == "Test relevance"
        assert d["actions"] == ["Action 1", "Action 2"]
        assert d["timeframe"] == "short_term"
        assert d["confidence"] == "high"
        assert d["analyzed_at"] == now.isoformat()

    def test_to_dict_with_none_values(self) -> None:
        """Test conversion to dictionary with None values."""
        result = TrendInsightResult(
            url="https://example.com",
            status="error",
            error="Test error",
        )

        d = result.to_dict()

        assert d["url"] == "https://example.com"
        assert d["title"] is None
        assert d["actions"] == []
        assert d["analyzed_at"] is None


class TestGetTrendAnalyzer:
    """Tests for get_trend_analyzer singleton."""

    def test_returns_same_instance(self) -> None:
        """Test that get_trend_analyzer returns singleton."""
        # Reset singleton
        get_trend_analyzer.cache_clear()

        analyzer1 = get_trend_analyzer()
        analyzer2 = get_trend_analyzer()

        assert analyzer1 is analyzer2

        # Cleanup
        get_trend_analyzer.cache_clear()


@pytest.mark.asyncio
class TestTrendAnalyzerAsync:
    """Async tests for TrendAnalyzer."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self) -> None:
        """Reset singleton before each test to ensure isolation."""
        get_trend_analyzer.cache_clear()
        yield
        get_trend_analyzer.cache_clear()

    async def test_invalid_url_returns_error(self) -> None:
        """Test that invalid URLs return error result."""
        analyzer = TrendAnalyzer()
        result = await analyzer.analyze_trend("not-a-valid-url")

        assert result.status == "error"
        assert "Invalid URL" in (result.error or "")
        assert result.url == "not-a-valid-url"

    async def test_analyze_trend_with_mocked_fetch(self) -> None:
        """Test analyze_trend with mocked URL fetch."""
        analyzer = TrendAnalyzer()

        # Create content that's > 100 chars to avoid limited_data status
        long_content = "This is a detailed article about AI trends in the SaaS industry. " * 5

        with (
            patch.object(analyzer, "_fetch_url_content", new_callable=AsyncMock) as mock_fetch,
            patch.object(analyzer, "_get_broker") as mock_get_broker,
        ):
            mock_fetch.return_value = (long_content, "Test Article")

            mock_broker = MagicMock()
            mock_response = MagicMock()
            mock_response.text = """
            {
                "title": "Test Article",
                "key_takeaway": "Key insight here",
                "relevance": "Relevant to your business",
                "actions": ["Action 1"],
                "timeframe": "short_term",
                "confidence": "high"
            }
            """
            mock_broker.call = AsyncMock(return_value=mock_response)
            mock_get_broker.return_value = mock_broker

            result = await analyzer.analyze_trend(
                url="https://example.com/article",
                industry="SaaS",
            )

            assert result.status == "complete"
            assert result.title == "Test Article"
            assert result.key_takeaway == "Key insight here"

    async def test_analyze_trend_limited_data(self) -> None:
        """Test analyze_trend marks limited_data when content not accessible."""
        analyzer = TrendAnalyzer()

        with (
            patch.object(analyzer, "_fetch_url_content", new_callable=AsyncMock) as mock_fetch,
            patch.object(analyzer, "_get_broker") as mock_get_broker,
        ):
            # Simulate no content fetched
            mock_fetch.return_value = (None, "Title Only")

            mock_broker = MagicMock()
            mock_response = MagicMock()
            mock_response.text = """
            {
                "title": "Title Only",
                "key_takeaway": "Limited analysis",
                "relevance": "Unknown",
                "actions": [],
                "timeframe": "short_term",
                "confidence": "low"
            }
            """
            mock_broker.call = AsyncMock(return_value=mock_response)
            mock_get_broker.return_value = mock_broker

            result = await analyzer.analyze_trend(url="https://example.com/article")

            assert result.status == "limited_data"
            assert result.confidence == "low"
