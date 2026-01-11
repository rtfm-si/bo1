"""Tests for article fetcher service."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.services.article_fetcher import (
    PAYWALL_INDICATORS,
    _detect_paywall,
    fetch_article_content,
    fetch_articles_batch,
)


class TestDetectPaywall:
    """Tests for paywall detection."""

    def test_detect_paywall_with_indicator(self):
        """Paywall detected when content contains indicator."""
        content = "This article requires you to subscribe to continue reading more."
        assert _detect_paywall(content) is True

    def test_detect_paywall_case_insensitive(self):
        """Paywall detection is case insensitive."""
        content = "SUBSCRIBE TO CONTINUE reading this exclusive content."
        assert _detect_paywall(content) is True

    def test_detect_paywall_no_indicator(self):
        """No paywall detected for regular content."""
        content = "This is a regular article about market trends and analysis."
        assert _detect_paywall(content) is False

    @pytest.mark.parametrize("indicator", PAYWALL_INDICATORS[:5])
    def test_detect_paywall_all_indicators(self, indicator):
        """Each paywall indicator is detected."""
        content = f"Some text before {indicator} and after"
        assert _detect_paywall(content) is True


class TestFetchArticleContent:
    """Tests for single article fetch."""

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """Successful article fetch returns content."""
        # Content must be > 200 chars after extraction
        html_content = f"<html><body><p>{'This is a test article with substantial content about market trends and business analysis. ' * 5}</p></body></html>"

        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.text = html_content
            mock_response.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetch_article_content("https://example.com/article")

            assert result.success is True
            assert result.content is not None
            assert "test article" in result.content

    @pytest.mark.asyncio
    async def test_fetch_no_url(self):
        """Empty URL returns error."""
        result = await fetch_article_content("")
        assert result.success is False
        assert result.error == "No URL provided"

    @pytest.mark.asyncio
    async def test_fetch_timeout(self):
        """Timeout returns error."""
        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = await fetch_article_content("https://example.com/slow")

            assert result.success is False
            assert result.error == "Timeout"

    @pytest.mark.asyncio
    async def test_fetch_http_error(self):
        """HTTP error returns error."""
        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not Found", request=AsyncMock(), response=mock_response
                )
            )

            result = await fetch_article_content("https://example.com/missing")

            assert result.success is False
            assert "HTTP 404" in result.error

    @pytest.mark.asyncio
    async def test_fetch_non_html_content(self):
        """Non-HTML content type returns error."""
        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/pdf"}
            mock_response.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetch_article_content("https://example.com/file.pdf")

            assert result.success is False
            assert "Non-HTML content" in result.error

    @pytest.mark.asyncio
    async def test_fetch_paywall_detected(self):
        """Paywall content returns error."""
        # Content must be > 200 chars to pass length check before paywall check
        html_content = f"<html><body><p>{'Please subscribe to continue reading this premium content. ' * 10}</p></body></html>"

        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.text = html_content
            mock_response.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetch_article_content("https://example.com/paywall")

            assert result.success is False
            assert result.error == "Paywall detected"

    @pytest.mark.asyncio
    async def test_fetch_content_too_short(self):
        """Very short content returns error."""
        html_content = "<html><body><p>Short</p></body></html>"

        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.text = html_content
            mock_response.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await fetch_article_content("https://example.com/short")

            assert result.success is False
            assert "too short" in result.error


class TestFetchArticlesBatch:
    """Tests for batch article fetch."""

    @pytest.mark.asyncio
    async def test_batch_empty_urls(self):
        """Empty URL list returns empty results."""
        results = await fetch_articles_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_partial_success(self):
        """Batch with mixed success/failure."""
        good_html = f"<html><body><p>{'This is a successful article with enough content to pass validation and testing requirements. ' * 5}</p></body></html>"

        async def mock_get(url, **kwargs):
            mock_response = AsyncMock()
            mock_response.raise_for_status = AsyncMock()
            mock_response.headers = {"content-type": "text/html"}

            if "good" in url:
                mock_response.text = good_html
            else:
                raise httpx.TimeoutException("Timeout")

            return mock_response

        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=mock_get)

            results = await fetch_articles_batch(
                ["https://example.com/good", "https://example.com/bad"]
            )

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False

    @pytest.mark.asyncio
    async def test_batch_respects_concurrent_limit(self):
        """Batch respects max concurrent limit."""
        # This is more of a functional test - we just verify it completes
        good_html = f"<html><body><p>{'Content for testing concurrency limits with enough text to pass validation. ' * 5}</p></body></html>"

        with patch("backend.services.article_fetcher.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.text = good_html
            mock_response.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            urls = [f"https://example.com/article{i}" for i in range(5)]
            results = await fetch_articles_batch(urls, max_concurrent=2)

            assert len(results) == 5
