"""Tests for blog content generation service."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.content_generator import BlogContent, generate_blog_post
from bo1.llm.client import TokenUsage


class TestGenerateBlogPost:
    """Tests for generate_blog_post function."""

    @pytest.mark.asyncio
    async def test_valid_json_response(self) -> None:
        """Test successful generation with valid JSON."""
        mock_response = json.dumps(
            {
                "title": "Test Title",
                "excerpt": "Test excerpt",
                "content": "# Test Content",
                "meta_title": "Meta Title",
                "meta_description": "Meta description",
            }
        )[1:]  # Remove leading { since prefill adds it

        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(return_value=(mock_response, mock_usage))

            result = await generate_blog_post("Test topic")

            assert isinstance(result, BlogContent)
            assert result.title == "Test Title"
            assert result.excerpt == "Test excerpt"
            assert result.content == "# Test Content"

    @pytest.mark.asyncio
    async def test_json_with_markdown_wrapper(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        # Simulates LLM returning ```json ... ``` wrapper
        inner_json = {
            "title": "Wrapped Title",
            "excerpt": "Wrapped excerpt",
            "content": "Content here",
            "meta_title": "Meta",
            "meta_description": "Desc",
        }
        # For markdown-wrapped, the LLM might ignore prefill - test both cases

        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            # First call fails (JSON with markdown), second call succeeds with plain JSON
            fail_response = "```json\n" + json.dumps(inner_json) + "\n```"
            success_response = json.dumps(inner_json)[1:]  # Remove leading {

            mock_client.call = AsyncMock(
                side_effect=[
                    (fail_response, mock_usage),  # First attempt with markdown
                    (success_response, mock_usage),  # Retry with clean JSON
                ]
            )

            result = await generate_blog_post("Test topic")

            assert isinstance(result, BlogContent)
            assert result.title == "Wrapped Title"

    @pytest.mark.asyncio
    async def test_json_with_trailing_text(self) -> None:
        """Test parsing JSON with trailing explanation text."""
        inner_json = {
            "title": "Clean Title",
            "excerpt": "Excerpt",
            "content": "Content",
            "meta_title": "Meta",
            "meta_description": "Desc",
        }
        # Response with trailing text after JSON
        mock_response = json.dumps(inner_json)[1:] + "\n\nI hope this helps!"

        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            # First attempt with trailing text might fail, second succeeds
            success_response = json.dumps(inner_json)[1:]
            mock_client.call = AsyncMock(
                side_effect=[
                    (mock_response, mock_usage),  # First attempt
                    (success_response, mock_usage),  # Retry
                ]
            )

            result = await generate_blog_post("Test topic")
            assert isinstance(result, BlogContent)

    @pytest.mark.asyncio
    async def test_retry_on_parse_failure(self) -> None:
        """Test that retry is attempted on JSON parse failure."""
        valid_json = {
            "title": "Retry Success",
            "excerpt": "Excerpt",
            "content": "Content",
            "meta_title": "Meta",
            "meta_description": "Desc",
        }
        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            # First call returns malformed JSON, second returns valid
            mock_client.call = AsyncMock(
                side_effect=[
                    ("not valid json at all", mock_usage),  # First attempt fails
                    (json.dumps(valid_json)[1:], mock_usage),  # Retry succeeds
                ]
            )

            result = await generate_blog_post("Test topic")

            assert isinstance(result, BlogContent)
            assert result.title == "Retry Success"
            # Verify call was made twice
            assert mock_client.call.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_includes_error_feedback(self) -> None:
        """Test that retry includes feedback about JSON error."""
        valid_json = {
            "title": "Success",
            "excerpt": "E",
            "content": "C",
            "meta_title": "M",
            "meta_description": "D",
        }
        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(
                side_effect=[
                    ("invalid", mock_usage),
                    (json.dumps(valid_json)[1:], mock_usage),
                ]
            )

            await generate_blog_post("Test topic")

            # Check second call has the error feedback message
            second_call_messages = mock_client.call.call_args_list[1][1]["messages"]
            assert len(second_call_messages) == 2  # Original + feedback
            assert "JSON" in second_call_messages[1]["content"]

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_error(self) -> None:
        """Test that ValueError is raised after retries exhausted."""
        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            # Both attempts fail
            mock_client.call = AsyncMock(
                side_effect=[
                    ("not json", mock_usage),
                    ("still not json", mock_usage),
                ]
            )

            with pytest.raises(ValueError, match="invalid JSON format"):
                await generate_blog_post("Test topic")

    @pytest.mark.asyncio
    async def test_missing_required_field_raises_error(self) -> None:
        """Test that missing required fields raise ValueError."""
        incomplete_json = {
            "title": "Missing Content",
            "excerpt": "Excerpt",
            # Missing: content, meta_title, meta_description
        }
        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(return_value=(json.dumps(incomplete_json)[1:], mock_usage))

            with pytest.raises(ValueError, match="missing required field"):
                await generate_blog_post("Test topic")
