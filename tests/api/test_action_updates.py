"""Tests for action update endpoints with summarization.

Tests the integration of the action update summarizer with the API endpoint.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestActionUpdateSummarization:
    """Tests for action update summarization integration."""

    @pytest.mark.asyncio
    async def test_summarizer_preserves_short_content(self):
        """Short content should be returned as-is without LLM call."""
        from backend.services.action_update_summarizer import summarize_action_update

        result = await summarize_action_update(
            content="Done",
            update_type="note",
        )

        # Short content is returned unchanged
        assert result == "Done"

    @pytest.mark.asyncio
    async def test_summarizer_graceful_degradation(self):
        """Summarizer failure should return original content."""
        with patch("backend.services.action_update_summarizer.get_settings") as mock_settings:
            mock_settings.return_value.action_update_summarizer_enabled = True

            with patch("backend.services.action_update_summarizer.PromptBroker") as MockBroker:
                broker_instance = MockBroker.return_value
                broker_instance.send_prompt = AsyncMock(side_effect=Exception("Network error"))

                from backend.services.action_update_summarizer import summarize_action_update

                original = "this is my original update content"
                result = await summarize_action_update(original, "progress")

                # Should return original on failure
                assert result == original
