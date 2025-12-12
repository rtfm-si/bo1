"""Redis-backed conversation repository for mentor chat.

Stores multi-turn mentor conversation state with 24-hour TTL.
Similar to ConversationRepository but for mentor (not dataset-scoped).
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Redis key prefixes
MENTOR_CONV_PREFIX = "mentor_conv"
MENTOR_CONV_INDEX_PREFIX = "mentor_convs"

# TTL settings
CONVERSATION_TTL = 86400  # 24 hours


class MentorConversationRepository:
    """Redis-backed storage for mentor chat conversations."""

    def __init__(self, redis_manager: RedisManager | None = None) -> None:
        """Initialize repository.

        Args:
            redis_manager: Optional Redis manager instance
        """
        self._redis = redis_manager or RedisManager()

    def _conv_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation."""
        return f"{MENTOR_CONV_PREFIX}:{conversation_id}"

    def _index_key(self, user_id: str) -> str:
        """Generate Redis key for user's mentor conversation index."""
        return f"{MENTOR_CONV_INDEX_PREFIX}:{user_id}"

    def create(
        self,
        user_id: str,
        persona: str = "general",
    ) -> dict[str, Any]:
        """Create a new mentor conversation.

        Args:
            user_id: User UUID
            persona: Initial persona (general, action_coach, data_analyst)

        Returns:
            Conversation dict with id, user_id, persona, created_at, messages
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "persona": persona,
            "created_at": now,
            "updated_at": now,
            "messages": [],
            "context_sources": [],  # Track which context was used
        }

        # Store conversation
        key = self._conv_key(conversation_id)
        self._redis.client.setex(
            key,
            CONVERSATION_TTL,
            json.dumps(conversation),
        )

        # Add to user's conversation index
        index_key = self._index_key(user_id)
        self._redis.client.zadd(index_key, {conversation_id: datetime.now(UTC).timestamp()})
        self._redis.client.expire(index_key, CONVERSATION_TTL)

        logger.info(f"Created mentor conversation {conversation_id} for user {user_id}")
        return conversation

    def get(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get a conversation by ID.

        Args:
            conversation_id: Conversation UUID
            user_id: Optional user ID for ownership check

        Returns:
            Conversation dict or None if not found
        """
        key = self._conv_key(conversation_id)
        data = self._redis.client.get(key)

        if not data:
            return None

        conversation = json.loads(data)

        # Verify ownership if user_id provided
        if user_id and conversation.get("user_id") != user_id:
            logger.warning(
                f"User {user_id} attempted to access mentor conversation {conversation_id} "
                f"owned by {conversation.get('user_id')}"
            )
            return None

        return conversation

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        persona: str | None = None,
        context_sources: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Append a message to a mentor conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user or assistant)
            content: Message content
            persona: Optional persona used for this message
            context_sources: Optional list of context sources used

        Returns:
            Updated conversation dict or None if not found
        """
        conversation = self.get(conversation_id)
        if not conversation:
            return None

        now = datetime.now(UTC).isoformat()
        message: dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": now,
        }

        if persona:
            message["persona"] = persona

        conversation["messages"].append(message)
        conversation["updated_at"] = now

        # Update persona if changed
        if persona:
            conversation["persona"] = persona

        # Update context sources
        if context_sources:
            conversation["context_sources"] = list(
                set(conversation.get("context_sources", []) + context_sources)
            )

        # Update in Redis with TTL refresh
        key = self._conv_key(conversation_id)
        self._redis.client.setex(
            key,
            CONVERSATION_TTL,
            json.dumps(conversation),
        )

        # Update index timestamp
        index_key = self._index_key(conversation["user_id"])
        self._redis.client.zadd(
            index_key,
            {conversation_id: datetime.now(UTC).timestamp()},
        )

        return conversation

    def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent mentor conversations for a user.

        Args:
            user_id: User UUID
            limit: Maximum conversations to return

        Returns:
            List of conversation dicts (without full messages)
        """
        index_key = self._index_key(user_id)

        # Get conversation IDs sorted by recency
        conv_ids = self._redis.client.zrevrange(index_key, 0, limit - 1)

        conversations = []
        for conv_id in conv_ids:
            conv_id_str = conv_id.decode("utf-8") if isinstance(conv_id, bytes) else conv_id
            conv = self.get(conv_id_str, user_id)
            if conv:
                # Return summary without full messages
                conversations.append(
                    {
                        "id": conv["id"],
                        "user_id": conv["user_id"],
                        "persona": conv.get("persona", "general"),
                        "created_at": conv["created_at"],
                        "updated_at": conv["updated_at"],
                        "message_count": len(conv.get("messages", [])),
                        "context_sources": conv.get("context_sources", []),
                    }
                )

        return conversations

    def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a mentor conversation.

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID for ownership check

        Returns:
            True if deleted, False if not found
        """
        conversation = self.get(conversation_id, user_id)
        if not conversation:
            return False

        # Remove from index
        index_key = self._index_key(user_id)
        self._redis.client.zrem(index_key, conversation_id)

        # Delete conversation
        key = self._conv_key(conversation_id)
        self._redis.client.delete(key)

        logger.info(f"Deleted mentor conversation {conversation_id}")
        return True

    def delete_all_for_user(self, user_id: str) -> int:
        """Delete all mentor conversations for a user (for GDPR deletion).

        Args:
            user_id: User UUID

        Returns:
            Number of conversations deleted
        """
        index_key = self._index_key(user_id)

        # Get all conversation IDs
        conv_ids = self._redis.client.zrange(index_key, 0, -1)

        deleted = 0
        for conv_id in conv_ids:
            conv_id_str = conv_id.decode("utf-8") if isinstance(conv_id, bytes) else conv_id
            key = self._conv_key(conv_id_str)
            if self._redis.client.delete(key):
                deleted += 1

        # Delete the index
        self._redis.client.delete(index_key)

        logger.info(f"Deleted {deleted} mentor conversations for user {user_id}")
        return deleted


# Singleton instance
_mentor_conversation_repo: MentorConversationRepository | None = None


def get_mentor_conversation_repo() -> MentorConversationRepository:
    """Get or create the mentor conversation repository singleton."""
    global _mentor_conversation_repo
    if _mentor_conversation_repo is None:
        _mentor_conversation_repo = MentorConversationRepository()
    return _mentor_conversation_repo
