"""Redis-backed conversation repository for dataset Q&A.

Stores multi-turn conversation state with 24-hour TTL.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Redis key prefixes
CONV_PREFIX = "dataset_conv"
CONV_INDEX_PREFIX = "dataset_convs"

# TTL settings
CONVERSATION_TTL = 86400  # 24 hours


class ConversationRepository:
    """Redis-backed storage for dataset Q&A conversations."""

    def __init__(self, redis_manager: RedisManager | None = None) -> None:
        """Initialize repository.

        Args:
            redis_manager: Optional Redis manager instance
        """
        self._redis = redis_manager or RedisManager()

    def _conv_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation."""
        return f"{CONV_PREFIX}:{conversation_id}"

    def _index_key(self, dataset_id: str, user_id: str) -> str:
        """Generate Redis key for user's conversation index."""
        return f"{CONV_INDEX_PREFIX}:{user_id}:{dataset_id}"

    def create(
        self,
        dataset_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Create a new conversation.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID

        Returns:
            Conversation dict with id, dataset_id, created_at, messages
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        conversation = {
            "id": conversation_id,
            "dataset_id": dataset_id,
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }

        # Store conversation
        key = self._conv_key(conversation_id)
        self._redis.client.setex(
            key,
            CONVERSATION_TTL,
            json.dumps(conversation),
        )

        # Add to user's conversation index
        index_key = self._index_key(dataset_id, user_id)
        self._redis.client.zadd(index_key, {conversation_id: datetime.now(UTC).timestamp()})
        self._redis.client.expire(index_key, CONVERSATION_TTL)

        logger.info(f"Created conversation {conversation_id} for dataset {dataset_id}")
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
                f"User {user_id} attempted to access conversation {conversation_id} "
                f"owned by {conversation.get('user_id')}"
            )
            return None

        return conversation

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        query_spec: dict[str, Any] | None = None,
        chart_spec: dict[str, Any] | None = None,
        query_result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Append a message to a conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user or assistant)
            content: Message content
            query_spec: Optional query spec
            chart_spec: Optional chart spec
            query_result: Optional query result summary

        Returns:
            Updated conversation dict or None if not found
        """
        conversation = self.get(conversation_id)
        if not conversation:
            return None

        now = datetime.now(UTC).isoformat()
        message = {
            "role": role,
            "content": content,
            "timestamp": now,
        }

        if query_spec:
            message["query_spec"] = query_spec
        if chart_spec:
            message["chart_spec"] = chart_spec
        if query_result:
            message["query_result"] = query_result

        conversation["messages"].append(message)
        conversation["updated_at"] = now

        # Update in Redis with TTL refresh
        key = self._conv_key(conversation_id)
        self._redis.client.setex(
            key,
            CONVERSATION_TTL,
            json.dumps(conversation),
        )

        # Update index timestamp
        index_key = self._index_key(conversation["dataset_id"], conversation["user_id"])
        self._redis.client.zadd(
            index_key,
            {conversation_id: datetime.now(UTC).timestamp()},
        )

        return conversation

    def list_by_dataset(
        self,
        dataset_id: str,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent conversations for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID
            limit: Maximum conversations to return

        Returns:
            List of conversation dicts (without full messages)
        """
        index_key = self._index_key(dataset_id, user_id)

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
                        "dataset_id": conv["dataset_id"],
                        "created_at": conv["created_at"],
                        "updated_at": conv["updated_at"],
                        "message_count": len(conv.get("messages", [])),
                    }
                )

        return conversations

    def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation.

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
        index_key = self._index_key(conversation["dataset_id"], user_id)
        self._redis.client.zrem(index_key, conversation_id)

        # Delete conversation
        key = self._conv_key(conversation_id)
        self._redis.client.delete(key)

        logger.info(f"Deleted conversation {conversation_id}")
        return True
