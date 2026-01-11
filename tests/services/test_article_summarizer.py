"""Tests for article summarizer service."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.services.article_summarizer import (
    _parse_summary_response,
    summarize_article,
    summarize_articles_batch,
)


class TestParseSummaryResponse:
    """Tests for LLM response parsing."""

    def test_parse_valid_json(self):
        """Valid JSON response parsed correctly."""
        response = '{"summary": "Test summary.", "key_points": ["Point 1", "Point 2", "Point 3"]}'
        result = _parse_summary_response("https://example.com", response)

        assert result.success is True
        assert result.summary == "Test summary."
        assert result.key_points == ["Point 1", "Point 2", "Point 3"]

    def test_parse_json_with_markdown_wrapper(self):
        """JSON wrapped in markdown code block parsed correctly."""
        response = '```json\n{"summary": "Test summary.", "key_points": ["Point 1"]}\n```'
        result = _parse_summary_response("https://example.com", response)

        assert result.success is True
        assert result.summary == "Test summary."

    def test_parse_json_embedded_in_text(self):
        """JSON embedded in other text extracted correctly."""
        response = (
            'Here is the summary: {"summary": "Test summary.", "key_points": ["Point 1"]} End.'
        )
        result = _parse_summary_response("https://example.com", response)

        assert result.success is True
        assert result.summary == "Test summary."

    def test_parse_missing_summary(self):
        """Missing summary field returns error."""
        response = '{"key_points": ["Point 1"]}'
        result = _parse_summary_response("https://example.com", response)

        assert result.success is False
        assert "No summary" in result.error

    def test_parse_invalid_json(self):
        """Invalid JSON returns error."""
        response = "This is not JSON at all"
        result = _parse_summary_response("https://example.com", response)

        assert result.success is False
        assert "Parse error" in result.error

    def test_parse_truncates_long_summary(self):
        """Long summary is truncated to 500 chars."""
        long_summary = "x" * 600
        response = f'{{"summary": "{long_summary}", "key_points": []}}'
        result = _parse_summary_response("https://example.com", response)

        assert result.success is True
        assert len(result.summary) == 500

    def test_parse_limits_key_points(self):
        """Key points limited to 3 items."""
        response = '{"summary": "Test.", "key_points": ["1", "2", "3", "4", "5"]}'
        result = _parse_summary_response("https://example.com", response)

        assert result.success is True
        assert len(result.key_points) == 3

    def test_parse_handles_invalid_key_points(self):
        """Invalid key_points field handled gracefully."""
        response = '{"summary": "Test.", "key_points": "not a list"}'
        result = _parse_summary_response("https://example.com", response)

        assert result.success is True
        assert result.key_points == []


class TestSummarizeArticle:
    """Tests for single article summarization."""

    @pytest.mark.asyncio
    async def test_summarize_success(self):
        """Successful summarization returns result."""
        mock_response = AsyncMock()
        mock_response.content = (
            '{"summary": "Test summary.", "key_points": ["Point 1", "Point 2", "Point 3"]}'
        )

        with patch("backend.services.article_summarizer.PromptBroker") as mock_broker:
            mock_broker.return_value.call = AsyncMock(return_value=mock_response)

            result = await summarize_article(
                url="https://example.com",
                content="This is test article content " * 50,
                title="Test Article",
            )

            assert result.success is True
            assert result.summary == "Test summary."
            assert len(result.key_points) == 3

    @pytest.mark.asyncio
    async def test_summarize_content_too_short(self):
        """Short content returns error."""
        result = await summarize_article(
            url="https://example.com",
            content="Too short",
            title="Test",
        )

        assert result.success is False
        assert "too short" in result.error

    @pytest.mark.asyncio
    async def test_summarize_empty_content(self):
        """Empty content returns error."""
        result = await summarize_article(
            url="https://example.com",
            content="",
            title="Test",
        )

        assert result.success is False
        assert "too short" in result.error

    @pytest.mark.asyncio
    async def test_summarize_llm_error(self):
        """LLM error returns error result."""
        with patch("backend.services.article_summarizer.PromptBroker") as mock_broker:
            mock_broker.return_value.call = AsyncMock(side_effect=Exception("LLM unavailable"))

            result = await summarize_article(
                url="https://example.com",
                content="This is test article content " * 50,
                title="Test Article",
            )

            assert result.success is False
            assert "LLM unavailable" in result.error


class TestSummarizeArticlesBatch:
    """Tests for batch article summarization."""

    @pytest.mark.asyncio
    async def test_batch_empty_list(self):
        """Empty article list returns empty results."""
        results = await summarize_articles_batch([])
        assert results == []

    @pytest.mark.asyncio
    async def test_batch_no_content_articles(self):
        """Articles without content return error results."""
        articles = [
            {"url": "https://example.com/1", "content": None},
            {"url": "https://example.com/2", "content": ""},
        ]
        results = await summarize_articles_batch(articles)

        assert len(results) == 2
        assert all(r.success is False for r in results)
        assert all("No content" in r.error for r in results)

    @pytest.mark.asyncio
    async def test_batch_mixed_results(self):
        """Batch with mixed content/no-content articles."""
        mock_response = AsyncMock()
        mock_response.content = '{"summary": "Test summary.", "key_points": ["Point 1"]}'

        with patch("backend.services.article_summarizer.PromptBroker") as mock_broker:
            mock_broker.return_value.call = AsyncMock(return_value=mock_response)

            articles = [
                {"url": "https://example.com/1", "content": "Good content " * 50, "title": "Good"},
                {"url": "https://example.com/2", "content": None, "title": "No Content"},
            ]
            results = await summarize_articles_batch(articles)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False

    @pytest.mark.asyncio
    async def test_batch_preserves_order(self):
        """Results maintain same order as input articles."""
        mock_response = AsyncMock()
        mock_response.content = '{"summary": "Test summary.", "key_points": ["Point 1"]}'

        with patch("backend.services.article_summarizer.PromptBroker") as mock_broker:
            mock_broker.return_value.call = AsyncMock(return_value=mock_response)

            articles = [
                {"url": "https://example.com/a", "content": "Content A " * 50},
                {"url": "https://example.com/b", "content": "Content B " * 50},
                {"url": "https://example.com/c", "content": "Content C " * 50},
            ]
            results = await summarize_articles_batch(articles)

            assert len(results) == 3
            assert results[0].url == "https://example.com/a"
            assert results[1].url == "https://example.com/b"
            assert results[2].url == "https://example.com/c"
