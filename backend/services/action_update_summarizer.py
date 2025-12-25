"""Action update summarizer service using Claude Haiku.

Cleans up and formats user-submitted action updates for improved readability.
Cost: ~$0.001/request (500 input + 200 output tokens at Haiku rates)

Provides:
- Grammar and typo correction
- Structured bullet point extraction
- Graceful fallback to original on error
"""

import logging

from bo1.config import TokenBudgets, get_settings
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.prompts.action_update import ACTION_UPDATE_SYSTEM_PROMPT, build_action_update_prompt

logger = logging.getLogger(__name__)


async def summarize_action_update(
    content: str,
    update_type: str,
    user_id: str | None = None,
) -> str:
    """Summarize and clean up an action update using Haiku.

    Args:
        content: Raw user-submitted update content
        update_type: Type of update (progress, blocker, note)
        user_id: Optional user ID for cost tracking

    Returns:
        Cleaned content, or original content on failure
    """
    settings = get_settings()

    # Check feature flag
    if not settings.action_update_summarizer_enabled:
        logger.debug("Action update summarizer disabled, returning original")
        return content

    # Skip very short updates (not worth the API call)
    if len(content.strip()) < 20:
        return content

    try:
        broker = PromptBroker()

        request = PromptRequest(
            system=ACTION_UPDATE_SYSTEM_PROMPT,
            user_message=build_action_update_prompt(content, update_type),
            model="haiku",  # Fast and cheap
            max_tokens=TokenBudgets.SMALL_TASK,  # 500 tokens max
            temperature=0.3,  # Low creativity, high consistency
            prompt_type="action_update_summarizer",
            agent_type="ActionUpdateSummarizer",
        )

        response = await broker.send_prompt(request, user_id=user_id)

        if response.success and response.content:
            cleaned = response.content.strip()
            # Sanity check: don't return empty or significantly longer content
            if cleaned and len(cleaned) <= len(content) * 2:
                logger.debug(f"Summarized update: {len(content)} -> {len(cleaned)} chars")
                return cleaned

        logger.warning("Summarizer returned invalid response, using original")
        return content

    except Exception as e:
        # Graceful degradation: return original on any error
        logger.warning(f"Action update summarization failed: {e}, using original")
        return content
