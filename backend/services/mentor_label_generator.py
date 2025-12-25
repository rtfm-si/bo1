"""Mentor conversation label generator.

Generates short labels for mentor conversations based on the first user message.
Uses claude-3-5-haiku-latest via PromptBroker for fast, cheap label generation.
"""

import logging

from bo1.llm.broker import PromptBroker, PromptRequest

logger = logging.getLogger(__name__)

# Label generation prompt - concise to minimize tokens
LABEL_SYSTEM_PROMPT = """Generate a short conversation label (3-6 words) that summarizes the topic.
Be specific but concise. No punctuation at end. Examples:
- "Quarterly Revenue Strategy"
- "Team Hiring Prioritization"
- "Product Launch Timeline"
- "Data Export Help"
"""

LABEL_USER_TEMPLATE = "Generate a label for this conversation starting with: {message}"


async def generate_label(user_message: str) -> str:
    """Generate a short label for a mentor conversation.

    Uses claude-3-5-haiku-latest for fast, cheap generation.
    Falls back to truncating the first message if LLM fails.

    Args:
        user_message: The first user message in the conversation

    Returns:
        A short label (3-6 words, max 100 chars)
    """
    # Truncate long messages for prompt efficiency
    truncated = user_message[:500] if len(user_message) > 500 else user_message

    try:
        broker = PromptBroker()
        request = PromptRequest(
            system=LABEL_SYSTEM_PROMPT,
            user_message=LABEL_USER_TEMPLATE.format(message=truncated),
            model="haiku",  # Fast, cheap model
            max_tokens=20,
            temperature=0.3,
            agent_type="MentorLabelGenerator",
            prompt_type="label_generation",
        )

        response = await broker.call(request)
        label = response.text.strip().strip('"').strip("'")

        # Enforce length constraint
        if len(label) > 100:
            label = label[:97] + "..."

        return label

    except Exception as e:
        logger.warning(f"Label generation failed, using fallback: {e}")
        return _fallback_label(user_message)


def _fallback_label(user_message: str) -> str:
    """Generate fallback label by truncating first message.

    Args:
        user_message: Original user message

    Returns:
        Truncated message as label (max 50 chars)
    """
    # Remove newlines and extra whitespace
    clean = " ".join(user_message.split())

    if len(clean) <= 50:
        return clean

    # Truncate at word boundary
    truncated = clean[:47]
    last_space = truncated.rfind(" ")
    if last_space > 20:
        truncated = truncated[:last_space]

    return truncated + "..."


async def generate_and_save_label(
    conversation_id: str,
    user_id: str,
    user_message: str,
) -> None:
    """Generate label and save to database (fire-and-forget).

    This runs asynchronously after the first message is sent.
    Errors are logged but not raised.

    Args:
        conversation_id: Conversation UUID
        user_id: User UUID for RLS
        user_message: First user message
    """
    try:
        label = await generate_label(user_message)

        # Import here to avoid circular imports
        from backend.services.mentor_conversation_pg_repo import (
            get_mentor_conversation_pg_repo,
        )

        repo = get_mentor_conversation_pg_repo()
        success = repo.update_label(conversation_id, label, user_id)

        if success:
            logger.debug(f"Generated label for conversation {conversation_id}: {label}")
        else:
            logger.warning(
                f"Failed to save label for conversation {conversation_id} - "
                "conversation may have been deleted"
            )

    except Exception as e:
        # Log but don't raise - this is fire-and-forget
        logger.error(f"Error generating/saving label for conversation {conversation_id}: {e}")
