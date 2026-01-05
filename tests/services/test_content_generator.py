"""Tests for blog content generation service."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.content_generator import (
    BlogContent,
    generate_blog_post,
    regenerate_blog_post,
)
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
        )  # Full JSON - client adds prefill which is included in response

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
            # Markdown wrapper should be handled by extract_json_from_response
            markdown_response = "```json\n" + json.dumps(inner_json) + "\n```"
            mock_client.call = AsyncMock(return_value=(markdown_response, mock_usage))

            result = await generate_blog_post("Test topic")

            assert isinstance(result, BlogContent)
            assert result.title == "Wrapped Title"

    @pytest.mark.asyncio
    async def test_json_with_trailing_text(self) -> None:
        """Test parsing JSON with trailing explanation text triggers retry."""
        inner_json = {
            "title": "Clean Title",
            "excerpt": "Excerpt",
            "content": "Content",
            "meta_title": "Meta",
            "meta_description": "Desc",
        }
        # Response with trailing text causes parse failure, then retry succeeds
        bad_response = json.dumps(inner_json) + "\n\nI hope this helps!"
        good_response = json.dumps(inner_json)

        mock_usage = TokenUsage(
            input_tokens=100,
            output_tokens=200,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            # First attempt with trailing text fails, retry succeeds
            mock_client.call = AsyncMock(
                side_effect=[
                    (bad_response, mock_usage),
                    (good_response, mock_usage),
                ]
            )

            result = await generate_blog_post("Test topic")
            assert isinstance(result, BlogContent)
            assert result.title == "Clean Title"

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
                    (json.dumps(valid_json), mock_usage),  # Retry succeeds
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
                    (json.dumps(valid_json), mock_usage),
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
            mock_client.call = AsyncMock(return_value=(json.dumps(incomplete_json), mock_usage))

            with pytest.raises(ValueError, match="missing required field"):
                await generate_blog_post("Test topic")


class TestRegenerateBlogPost:
    """Tests for regenerate_blog_post function."""

    @pytest.fixture
    def original_content(self) -> BlogContent:
        """Create a sample original blog content."""
        return BlogContent(
            title="Original Title",
            excerpt="Original excerpt",
            content="# Original Content\n\nThis is the original article.",
            meta_title="Original Meta Title",
            meta_description="Original meta description",
        )

    @pytest.mark.asyncio
    async def test_regenerate_with_changes(self, original_content: BlogContent) -> None:
        """Test regeneration with specific changes."""
        mock_response = json.dumps(
            {
                "title": "Improved Title",
                "excerpt": "Improved excerpt",
                "content": "# Improved Content\n\nWith requested changes.",
                "meta_title": "Improved Meta Title",
                "meta_description": "Improved meta description",
            }
        )

        mock_usage = TokenUsage(
            input_tokens=200,
            output_tokens=300,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(return_value=(mock_response, mock_usage))

            result = await regenerate_blog_post(
                original=original_content,
                changes=["Make the introduction more engaging", "Add more examples"],
            )

            assert isinstance(result, BlogContent)
            assert result.title == "Improved Title"
            assert result.content == "# Improved Content\n\nWith requested changes."
            # Verify changes were included in prompt
            call_messages = mock_client.call.call_args[1]["messages"]
            assert "Make the introduction more engaging" in call_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_regenerate_with_tone(self, original_content: BlogContent) -> None:
        """Test regeneration with tone adjustment."""
        mock_response = json.dumps(
            {
                "title": "Friendly Title",
                "excerpt": "Friendly excerpt",
                "content": "# Friendly Content",
                "meta_title": "Friendly Meta",
                "meta_description": "Friendly desc",
            }
        )

        mock_usage = TokenUsage(
            input_tokens=200,
            output_tokens=300,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(return_value=(mock_response, mock_usage))

            result = await regenerate_blog_post(
                original=original_content,
                tone="Friendly",
            )

            assert isinstance(result, BlogContent)
            assert result.title == "Friendly Title"
            # Verify tone was included in prompt
            call_messages = mock_client.call.call_args[1]["messages"]
            assert "friendly tone" in call_messages[0]["content"].lower()

    @pytest.mark.asyncio
    async def test_regenerate_with_changes_and_tone(self, original_content: BlogContent) -> None:
        """Test regeneration with both changes and tone."""
        mock_response = json.dumps(
            {
                "title": "Technical Title",
                "excerpt": "Technical excerpt",
                "content": "# Technical Content",
                "meta_title": "Technical Meta",
                "meta_description": "Technical desc",
            }
        )

        mock_usage = TokenUsage(
            input_tokens=200,
            output_tokens=300,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(return_value=(mock_response, mock_usage))

            result = await regenerate_blog_post(
                original=original_content,
                changes=["Add code examples"],
                tone="Technical",
            )

            assert isinstance(result, BlogContent)
            call_messages = mock_client.call.call_args[1]["messages"]
            content = call_messages[0]["content"]
            assert "Add code examples" in content
            assert "technical" in content.lower()

    @pytest.mark.asyncio
    async def test_regenerate_limits_changes_to_three(self, original_content: BlogContent) -> None:
        """Test that only first 3 changes are used."""
        mock_response = json.dumps(
            {
                "title": "Title",
                "excerpt": "Excerpt",
                "content": "Content",
                "meta_title": "Meta",
                "meta_description": "Desc",
            }
        )

        mock_usage = TokenUsage(
            input_tokens=200,
            output_tokens=300,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )

        with patch("backend.services.content_generator.ClaudeClient") as mock_client_cls:
            mock_client = mock_client_cls.return_value
            mock_client.call = AsyncMock(return_value=(mock_response, mock_usage))

            await regenerate_blog_post(
                original=original_content,
                changes=["Change 1", "Change 2", "Change 3", "Change 4", "Change 5"],
            )

            call_messages = mock_client.call.call_args[1]["messages"]
            content = call_messages[0]["content"]
            # First 3 should be included
            assert "Change 1" in content
            assert "Change 2" in content
            assert "Change 3" in content
            # 4th and 5th should not be included
            assert "Change 4" not in content
            assert "Change 5" not in content
