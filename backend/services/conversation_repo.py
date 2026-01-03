"""Redis-backed conversation repository for dataset Q&A with PostgreSQL persistence.

Redis is the hot cache (24-hour TTL), PostgreSQL is the source of truth.
Dual-write pattern: all writes go to PostgreSQL first, then Redis.
On cache miss, PostgreSQL is consulted and Redis is repopulated.
"""

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from bo1.state.redis_manager import RedisManager

if TYPE_CHECKING:
    from backend.services.dataset_conversation_pg_repo import DatasetConversationPgRepository

logger = logging.getLogger(__name__)

# Redis key prefixes
CONV_PREFIX = "dataset_conv"
CONV_INDEX_PREFIX = "dataset_convs"

# TTL settings
CONVERSATION_TTL = 86400  # 24 hours


class ConversationRepository:
    """Redis-cached, PostgreSQL-backed storage for dataset Q&A conversations.

    Uses dual-write pattern:
    - All creates/updates go to PostgreSQL first (source of truth)
    - Redis is updated as a cache layer with 24h TTL
    - On cache miss, data is loaded from PostgreSQL and cached
    """

    def __init__(self, redis_manager: RedisManager | None = None) -> None:
        """Initialize repository.

        Args:
            redis_manager: Optional Redis manager instance
        """
        self._redis = redis_manager or RedisManager()
        self._pg_repo = None

    def _get_pg_repo(self) -> "DatasetConversationPgRepository":
        """Lazy load PostgreSQL repository to avoid circular imports."""
        if self._pg_repo is None:
            from backend.services.dataset_conversation_pg_repo import (
                get_dataset_conversation_pg_repo,
            )

            self._pg_repo = get_dataset_conversation_pg_repo()
        return self._pg_repo

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

        Writes to PostgreSQL first (source of truth), then caches in Redis.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID

        Returns:
            Conversation dict with id, dataset_id, created_at, messages
        """
        # Write to PostgreSQL first (source of truth)
        try:
            pg_repo = self._get_pg_repo()
            conversation = pg_repo.create(dataset_id, user_id)
            conversation_id = conversation["id"]
        except Exception as e:
            logger.error(f"PostgreSQL create failed for dataset {dataset_id}: {e}")
            raise

        # Cache in Redis
        try:
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
        except Exception as e:
            # Redis failure is not fatal - PostgreSQL has the data
            logger.warning(f"Redis cache failed for conversation {conversation_id}: {e}")

        logger.info(f"Created conversation {conversation_id} for dataset {dataset_id}")
        return conversation

    def get(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get a conversation by ID.

        Tries Redis cache first, falls back to PostgreSQL on miss.

        Args:
            conversation_id: Conversation UUID
            user_id: Optional user ID for ownership check

        Returns:
            Conversation dict or None if not found
        """
        # Try Redis cache first
        key = self._conv_key(conversation_id)
        try:
            data = self._redis.client.get(key)
            if data:
                conversation = json.loads(data)
                # Verify ownership if user_id provided
                if user_id and conversation.get("user_id") != user_id:
                    logger.warning(
                        f"User {user_id} attempted to access conversation {conversation_id} "
                        f"owned by {conversation.get('user_id')}"
                    )
                    return None
                return conversation
        except Exception as e:
            logger.warning(f"Redis get failed for {conversation_id}: {e}")

        # Cache miss - try PostgreSQL
        try:
            pg_repo = self._get_pg_repo()
            conversation = pg_repo.get(conversation_id, user_id)
            if conversation:
                # Re-populate Redis cache
                self._cache_conversation(conversation)
            return conversation
        except Exception as e:
            logger.error(f"PostgreSQL get failed for {conversation_id}: {e}")
            return None

    def _cache_conversation(self, conversation: dict[str, Any]) -> None:
        """Cache a conversation in Redis.

        Args:
            conversation: Conversation dict to cache
        """
        try:
            conversation_id = conversation["id"]
            key = self._conv_key(conversation_id)
            self._redis.client.setex(
                key,
                CONVERSATION_TTL,
                json.dumps(conversation),
            )

            # Update index
            dataset_id = conversation["dataset_id"]
            user_id = conversation["user_id"]
            index_key = self._index_key(dataset_id, user_id)
            self._redis.client.zadd(index_key, {conversation_id: datetime.now(UTC).timestamp()})
            self._redis.client.expire(index_key, CONVERSATION_TTL)
        except Exception as e:
            logger.warning(f"Redis cache update failed: {e}")

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        query_spec: dict[str, Any] | None = None,
        chart_spec: dict[str, Any] | None = None,
        query_result: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Append a message to a conversation.

        Writes to PostgreSQL first (source of truth), then updates Redis cache.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user or assistant)
            content: Message content
            query_spec: Optional query spec
            chart_spec: Optional chart spec
            query_result: Optional query result summary
            user_id: Optional user ID for RLS context

        Returns:
            Updated conversation dict or None if not found
        """
        # Write to PostgreSQL first (source of truth)
        try:
            pg_repo = self._get_pg_repo()
            conversation = pg_repo.append_message(
                conversation_id,
                role,
                content,
                query_spec=query_spec,
                chart_spec=chart_spec,
                query_result=query_result,
                user_id=user_id,
            )
            if not conversation:
                return None
        except Exception as e:
            logger.error(f"PostgreSQL append_message failed for {conversation_id}: {e}")
            raise

        # Update Redis cache
        self._cache_conversation(conversation)

        return conversation

    def list_by_dataset(
        self,
        dataset_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List recent conversations for a dataset.

        Queries PostgreSQL directly (source of truth) for complete history.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID
            limit: Maximum conversations to return

        Returns:
            List of conversation dicts (without full messages)
        """
        try:
            pg_repo = self._get_pg_repo()
            conversations, _ = pg_repo.list_by_dataset(dataset_id, user_id, limit=limit)
            return conversations
        except Exception as e:
            logger.error(f"PostgreSQL list_by_dataset failed for {dataset_id}: {e}")
            # Fallback to Redis-only for resilience
            return self._list_by_dataset_redis_fallback(dataset_id, user_id, limit)

    def _list_by_dataset_redis_fallback(
        self,
        dataset_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fallback to Redis when PostgreSQL is unavailable.

        Args:
            dataset_id: Dataset UUID
            user_id: User UUID
            limit: Maximum conversations to return

        Returns:
            List of conversation dicts from Redis cache
        """
        index_key = self._index_key(dataset_id, user_id)

        try:
            # Get conversation IDs sorted by recency
            conv_ids = self._redis.client.zrevrange(index_key, 0, limit - 1)

            conversations = []
            for conv_id in conv_ids:
                conv_id_str = conv_id.decode("utf-8") if isinstance(conv_id, bytes) else conv_id
                key = self._conv_key(conv_id_str)
                data = self._redis.client.get(key)
                if data:
                    conv = json.loads(data)
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
        except Exception as e:
            logger.error(f"Redis fallback failed for {dataset_id}: {e}")
            return []

    def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a conversation.

        Deletes from PostgreSQL first (source of truth), then clears Redis cache.

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID for ownership check

        Returns:
            True if deleted, False if not found
        """
        # Get conversation to find dataset_id for index cleanup
        conversation = self.get(conversation_id, user_id)
        dataset_id = conversation["dataset_id"] if conversation else None

        # Delete from PostgreSQL first (source of truth)
        try:
            pg_repo = self._get_pg_repo()
            deleted = pg_repo.delete(conversation_id, user_id)
            if not deleted:
                return False
        except Exception as e:
            logger.error(f"PostgreSQL delete failed for {conversation_id}: {e}")
            raise

        # Clear Redis cache
        try:
            key = self._conv_key(conversation_id)
            self._redis.client.delete(key)

            if dataset_id:
                index_key = self._index_key(dataset_id, user_id)
                self._redis.client.zrem(index_key, conversation_id)
        except Exception as e:
            # Redis failure is not fatal - PostgreSQL has deleted the data
            logger.warning(f"Redis cache cleanup failed for {conversation_id}: {e}")

        logger.info(f"Deleted conversation {conversation_id}")
        return True
