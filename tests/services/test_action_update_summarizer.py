"""Tests for action update summarizer service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.action_update_summarizer import summarize_action_update
from bo1.prompts.action_update import (
    UPDATE_TYPE_CONSTRAINTS,
    build_action_update_prompt,
)


class TestBuildActionUpdatePrompt:
    """Tests for prompt building."""

    def test_build_prompt_progress(self):
        """Progress update should include char limit constraint."""
        prompt = build_action_update_prompt("did the thing", "progress")
        assert "Update type: progress" in prompt
        assert "max 280 chars" in prompt
        assert "did the thing" in prompt

    def test_build_prompt_note(self):
        """Note update should include structure constraint."""
        prompt = build_action_update_prompt("some notes here", "note")
        assert "Update type: note" in prompt
        assert "Preserve detail" in prompt

    def test_build_prompt_blocker(self):
        """Blocker update should include clarification constraint."""
        prompt = build_action_update_prompt("stuck on X", "blocker")
        assert "Update type: blocker" in prompt
        assert "Clarify the blocking issue" in prompt

    def test_build_prompt_unknown_type_uses_default(self):
        """Unknown update type should use default constraints."""
        prompt = build_action_update_prompt("content", "unknown_type")
        assert "Update type: unknown_type" in prompt
        assert "Clean up the text" in prompt


class TestUpdateTypeConstraints:
    """Tests for constraint configuration."""

    def test_progress_constraints(self):
        """Progress should have 280 char limit."""
        assert UPDATE_TYPE_CONSTRAINTS["progress"]["max_chars"] == 280

    def test_note_constraints(self):
        """Note should have 500 char limit."""
        assert UPDATE_TYPE_CONSTRAINTS["note"]["max_chars"] == 500

    def test_blocker_constraints(self):
        """Blocker should have 500 char limit."""
        assert UPDATE_TYPE_CONSTRAINTS["blocker"]["max_chars"] == 500


class TestSummarizeActionUpdate:
    """Tests for the summarize_action_update function."""

    @pytest.mark.asyncio
    async def test_short_content_skipped(self):
        """Content under 20 chars should be returned as-is."""
        result = await summarize_action_update("Done", "progress")
        assert result == "Done"

    @pytest.mark.asyncio
    async def test_disabled_returns_original(self):
        """When disabled, should return original content."""
        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = False
            result = await summarize_action_update(
                "This is a longer content that would normally be summarized",
                "progress",
            )
            assert "longer content" in result

    @pytest.mark.asyncio
    async def test_successful_summarization(self):
        """Successful LLM call should return cleaned content."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "Completed the task successfully."

        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(return_value=mock_response)

                result = await summarize_action_update(
                    "i did the thing and it worked out pretty good",
                    "progress",
                    user_id="user-123",
                )

                assert result == "Completed the task successfully."
                broker_instance.send_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_haiku_model(self):
        """Should use Haiku model for cost efficiency."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "Cleaned content"

        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(return_value=mock_response)

                await summarize_action_update(
                    "longer content here that needs summarizing",
                    "note",
                )

                call_args = broker_instance.send_prompt.call_args
                request = call_args[0][0]
                assert request.model == "haiku"

    @pytest.mark.asyncio
    async def test_tracks_prompt_type(self):
        """Should track as action_update_summarizer prompt type."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "Cleaned content"

        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(return_value=mock_response)

                await summarize_action_update(
                    "longer content here that needs summarizing",
                    "progress",
                )

                call_args = broker_instance.send_prompt.call_args
                request = call_args[0][0]
                assert request.prompt_type == "action_update_summarizer"

    @pytest.mark.asyncio
    async def test_llm_failure_returns_original(self):
        """LLM failure should return original content."""
        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(side_effect=Exception("API error"))

                original = "my original messy content here"
                result = await summarize_action_update(original, "note")

                assert result == original

    @pytest.mark.asyncio
    async def test_empty_response_returns_original(self):
        """Empty LLM response should return original content."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = ""

        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(return_value=mock_response)

                original = "my original content that was not summarized"
                result = await summarize_action_update(original, "progress")

                assert result == original

    @pytest.mark.asyncio
    async def test_unsuccessful_response_returns_original(self):
        """Unsuccessful LLM response should return original content."""
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.content = None

        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(return_value=mock_response)

                original = "my original content for this test"
                result = await summarize_action_update(original, "blocker")

                assert result == original

    @pytest.mark.asyncio
    async def test_excessively_long_response_returns_original(self):
        """Response more than 2x original length should return original."""
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "x" * 200  # Much longer than original

        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as mock_broker:
                broker_instance = mock_broker.return_value
                broker_instance.send_prompt = AsyncMock(return_value=mock_response)

                original = "short original content"  # ~21 chars
                result = await summarize_action_update(original, "note")

                assert result == original
