"""Mention parser for mentor chat.

Parses @meeting:<id>, @action:<id>, @dataset:<id> mentions from message text.
"""

import re
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class MentionType(str, Enum):
    """Types of mentionable entities."""

    MEETING = "meeting"
    ACTION = "action"
    DATASET = "dataset"
    CHAT = "chat"


@dataclass
class Mention:
    """A parsed mention from user message."""

    type: MentionType
    id: str
    raw_text: str  # Original text including @ prefix


@dataclass
class MentionParseResult:
    """Result of parsing mentions from a message."""

    mentions: list[Mention]
    clean_text: str  # Message with mentions removed


# Regex pattern: @type:uuid (supports standard UUID format)
# Captures: (type)(uuid)
MENTION_PATTERN = re.compile(
    r"@(meeting|action|dataset|chat):([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)


def parse_mentions(message: str) -> MentionParseResult:
    """Parse mentions from a message.

    Extracts @meeting:<uuid>, @action:<uuid>, @dataset:<uuid> patterns.
    Returns list of mentions and cleaned message text.

    Args:
        message: Raw message text

    Returns:
        MentionParseResult with mentions list and clean_text
    """
    mentions: list[Mention] = []
    seen_ids: set[str] = set()  # Dedupe mentions

    for match in MENTION_PATTERN.finditer(message):
        mention_type_str = match.group(1).lower()
        entity_id = match.group(2).lower()  # Normalize UUID case

        # Skip duplicates
        key = f"{mention_type_str}:{entity_id}"
        if key in seen_ids:
            continue
        seen_ids.add(key)

        # Validate UUID format
        try:
            UUID(entity_id)
        except ValueError:
            continue  # Skip invalid UUIDs

        mention_type = MentionType(mention_type_str)
        mentions.append(
            Mention(
                type=mention_type,
                id=entity_id,
                raw_text=match.group(0),
            )
        )

    # Remove mentions from text, cleaning up extra whitespace
    clean_text = MENTION_PATTERN.sub("", message).strip()
    # Collapse multiple spaces to single space
    clean_text = re.sub(r"\s+", " ", clean_text)

    return MentionParseResult(mentions=mentions, clean_text=clean_text)


def format_mention(mention_type: MentionType, entity_id: str) -> str:
    """Format a mention for insertion into text.

    Args:
        mention_type: Type of mention
        entity_id: UUID of the entity

    Returns:
        Formatted mention string like @meeting:uuid
    """
    return f"@{mention_type.value}:{entity_id}"
