"""Tests for mentor conversation label generator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.mentor_label_generator import (
    _fallback_label,
    generate_and_save_label,
    generate_label,
)


class TestFallbackLabel:
    """Tests for _fallback_label function."""

    def test_short_message_unchanged(self):
        """Short messages should be returned unchanged."""
        result = _fallback_label("How to fix my revenue?")
        assert result == "How to fix my revenue?"

    def test_long_message_truncated(self):
        """Long messages should be truncated at word boundary."""
        long_msg = "This is a very long message that goes well beyond fifty characters and should be truncated"
        result = _fallback_label(long_msg)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_whitespace_normalized(self):
        """Newlines and extra whitespace should be normalized."""
        result = _fallback_label("First line\nSecond line\n\nThird line")
        assert "\n" not in result
        assert "  " not in result

    def test_exactly_50_chars(self):
        """Message with exactly 50 chars should not be truncated."""
        msg = "a" * 50
        result = _fallback_label(msg)
        assert result == msg
        assert len(result) == 50


class TestGenerateLabel:
    """Tests for generate_label async function."""

    @pytest.mark.asyncio
    async def test_generate_label_success(self):
        """Successful LLM call should return the generated label."""
        mock_response = MagicMock()
        mock_response.text = "Quarterly Revenue Strategy"

        with patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker:
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            result = await generate_label("How should I increase my revenue this quarter?")

            assert result == "Quarterly Revenue Strategy"
            broker_instance.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_label_strips_quotes(self):
        """Generated labels should have quotes stripped."""
        mock_response = MagicMock()
        mock_response.text = '"Team Hiring Strategy"'

        with patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker:
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            result = await generate_label("How many people should I hire?")

            assert result == "Team Hiring Strategy"

    @pytest.mark.asyncio
    async def test_generate_label_fallback_on_llm_error(self):
        """LLM failures should fall back to message truncation."""
        with patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker:
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(side_effect=Exception("API error"))

            result = await generate_label("What should I do about declining sales?")

            # Should fall back to truncation
            assert "declining sales" in result or result.endswith("...")

    @pytest.mark.asyncio
    async def test_label_length_constraint(self):
        """Labels exceeding 100 chars should be truncated."""
        mock_response = MagicMock()
        mock_response.text = "A" * 150  # Very long label

        with patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker:
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            result = await generate_label("Test message")

            assert len(result) <= 100
            assert result.endswith("...")

    @pytest.mark.asyncio
    async def test_long_message_truncated_for_prompt(self):
        """Long input messages should be truncated before sending to LLM."""
        mock_response = MagicMock()
        mock_response.text = "Strategy Discussion"

        with patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker:
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            long_message = "A" * 1000
            await generate_label(long_message)

            # Verify the message was truncated in the request
            call_args = broker_instance.call.call_args
            request = call_args[0][0]
            assert len(request.user_message) < 600  # 500 + template overhead


class TestGenerateAndSaveLabel:
    """Tests for generate_and_save_label async function."""

    @pytest.mark.asyncio
    async def test_generates_and_saves_label(self):
        """Should generate label and save to repository."""
        mock_response = MagicMock()
        mock_response.text = "Product Launch Timeline"

        mock_repo = MagicMock()
        mock_repo.update_label = MagicMock(return_value=True)

        with (
            patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker,
            patch(
                "backend.services.mentor_conversation_pg_repo.get_mentor_conversation_pg_repo",
                return_value=mock_repo,
            ),
        ):
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            await generate_and_save_label(
                "conv-123", "user-456", "When should I launch my new product?"
            )

            mock_repo.update_label.assert_called_once_with(
                "conv-123", "Product Launch Timeline", "user-456"
            )

    @pytest.mark.asyncio
    async def test_handles_save_failure_gracefully(self):
        """Should log but not raise when save fails."""
        mock_response = MagicMock()
        mock_response.text = "Some Label"

        mock_repo = MagicMock()
        mock_repo.update_label = MagicMock(return_value=False)  # Conversation deleted

        with (
            patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker,
            patch(
                "backend.services.mentor_conversation_pg_repo.get_mentor_conversation_pg_repo",
                return_value=mock_repo,
            ),
        ):
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(return_value=mock_response)

            # Should not raise
            await generate_and_save_label("conv-123", "user-456", "Test message")

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        """Should catch and log any exceptions without raising."""
        with patch("backend.services.mentor_label_generator.PromptBroker") as MockBroker:
            broker_instance = MockBroker.return_value
            broker_instance.call = AsyncMock(side_effect=Exception("Network error"))

            # Should not raise
            await generate_and_save_label("conv-123", "user-456", "Test message")
