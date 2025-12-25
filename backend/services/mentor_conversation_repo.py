"""Mentor conversation repository with PostgreSQL + Redis cache.

PostgreSQL is the source of truth for durable storage.
Redis caches hot conversations with 24-hour TTL for fast reads.

Architecture:
- create(): Write to PostgreSQL first, then cache in Redis
- get(): Check Redis first; on miss, load from PostgreSQL and populate cache
- append_message(): Write to PostgreSQL, update Redis cache
- list_by_user(): Read from PostgreSQL (not cached, always fresh)
- delete(): Delete from PostgreSQL, remove from Redis
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from bo1.state.redis_manager import RedisManager

if TYPE_CHECKING:
    from backend.services.mentor_conversation_pg_repo import MentorConversationPgRepository

logger = logging.getLogger(__name__)

# Redis key prefixes
MENTOR_CONV_PREFIX = "mentor_conv"
MENTOR_CONV_INDEX_PREFIX = "mentor_convs"

# TTL settings
CONVERSATION_TTL = 86400  # 24 hours


class MentorConversationRepository:
    """PostgreSQL + Redis cache storage for mentor chat conversations."""

    def __init__(
        self,
        redis_manager: RedisManager | None = None,
        pg_repo: "MentorConversationPgRepository | None" = None,
    ) -> None:
        """Initialize repository.

        Args:
            redis_manager: Optional Redis manager instance
            pg_repo: Optional PostgreSQL repository (for dependency injection in tests)
        """
        self._redis = redis_manager or RedisManager()
        self._pg_repo = pg_repo

    def _get_pg_repo(self) -> "MentorConversationPgRepository":
        """Get or create PostgreSQL repository (lazy init)."""
        if self._pg_repo is None:
            from backend.services.mentor_conversation_pg_repo import (
                get_mentor_conversation_pg_repo,
            )

            self._pg_repo = get_mentor_conversation_pg_repo()
        return self._pg_repo

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

        Writes to PostgreSQL first (source of truth), then caches in Redis.

        Args:
            user_id: User ID (string)
            persona: Initial persona (general, action_coach, data_analyst)

        Returns:
            Conversation dict with id, user_id, persona, created_at, messages
        """
        # Write to PostgreSQL first
        pg_repo = self._get_pg_repo()
        conversation = pg_repo.create(user_id, persona)
        conversation_id = conversation["id"]

        # Cache in Redis
        try:
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
        except Exception as e:
            # Redis cache failure is non-fatal - PostgreSQL is source of truth
            logger.warning(f"Failed to cache conversation {conversation_id} in Redis: {e}")

        logger.info(f"Created mentor conversation {conversation_id} for user {user_id}")
        return conversation

    def get(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get a conversation by ID.

        Checks Redis cache first; on miss, loads from PostgreSQL and populates cache.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID for ownership check and RLS context

        Returns:
            Conversation dict or None if not found
        """
        # Try Redis cache first
        try:
            key = self._conv_key(conversation_id)
            data = self._redis.client.get(key)

            if data:
                conversation = json.loads(data)
                # Verify ownership if user_id provided
                if user_id and conversation.get("user_id") != user_id:
                    logger.warning(
                        f"User {user_id} attempted to access mentor conversation "
                        f"{conversation_id} owned by {conversation.get('user_id')}"
                    )
                    return None
                return conversation
        except Exception as e:
            logger.warning(f"Redis cache lookup failed for {conversation_id}: {e}")

        # Cache miss or Redis failure - load from PostgreSQL
        pg_repo = self._get_pg_repo()
        conversation = pg_repo.get(conversation_id, user_id)

        if conversation:
            # Populate Redis cache
            try:
                key = self._conv_key(conversation_id)
                self._redis.client.setex(
                    key,
                    CONVERSATION_TTL,
                    json.dumps(conversation),
                )
                logger.debug(f"Cached conversation {conversation_id} from PostgreSQL")
            except Exception as e:
                logger.warning(f"Failed to cache conversation {conversation_id}: {e}")

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

        Writes to PostgreSQL first (source of truth), then updates Redis cache.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user or assistant)
            content: Message content
            persona: Optional persona used for this message
            context_sources: Optional list of context sources used

        Returns:
            Updated conversation dict or None if not found
        """
        # Get user_id from existing conversation for RLS
        existing = self.get(conversation_id)
        if not existing:
            return None
        user_id = existing.get("user_id")

        # Write to PostgreSQL
        pg_repo = self._get_pg_repo()
        conversation = pg_repo.append_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            persona=persona,
            context_sources=context_sources,
            user_id=user_id,
        )

        if not conversation:
            return None

        # Update Redis cache
        try:
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
        except Exception as e:
            # Redis cache failure is non-fatal
            logger.warning(f"Failed to update cache for conversation {conversation_id}: {e}")

        return conversation

    def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List recent mentor conversations for a user.

        Reads from PostgreSQL (not cached, always fresh).

        Args:
            user_id: User ID
            limit: Maximum conversations to return
            offset: Offset for pagination

        Returns:
            List of conversation dicts (without full messages)
        """
        pg_repo = self._get_pg_repo()
        conversations, _total = pg_repo.list_by_user(user_id, limit, offset)
        return conversations

    def update_label(
        self,
        conversation_id: str,
        user_id: str,
        label: str,
    ) -> bool:
        """Update conversation label.

        Writes to PostgreSQL first (source of truth), then invalidates Redis cache.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID for ownership check
            label: New label (1-100 chars)

        Returns:
            True if updated, False if not found
        """
        # Write to PostgreSQL
        pg_repo = self._get_pg_repo()
        updated = pg_repo.update_label(conversation_id, label, user_id)

        if updated:
            # Invalidate Redis cache (next get() will repopulate from PostgreSQL)
            try:
                key = self._conv_key(conversation_id)
                self._redis.client.delete(key)
            except Exception as e:
                # Redis cache failure is non-fatal
                logger.warning(
                    f"Failed to invalidate cache for conversation {conversation_id}: {e}"
                )

            logger.info(f"Updated label for mentor conversation {conversation_id}")

        return updated

    def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a mentor conversation.

        Deletes from PostgreSQL first (source of truth), then removes from Redis.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID for ownership check

        Returns:
            True if deleted, False if not found
        """
        # Delete from PostgreSQL
        pg_repo = self._get_pg_repo()
        deleted = pg_repo.delete(conversation_id, user_id)

        if deleted:
            # Remove from Redis cache
            try:
                index_key = self._index_key(user_id)
                self._redis.client.zrem(index_key, conversation_id)

                key = self._conv_key(conversation_id)
                self._redis.client.delete(key)
            except Exception as e:
                # Redis failure is non-fatal
                logger.warning(f"Failed to remove conversation {conversation_id} from cache: {e}")

            logger.info(f"Deleted mentor conversation {conversation_id}")

        return deleted

    def delete_all_for_user(self, user_id: str) -> int:
        """Delete all mentor conversations for a user (for GDPR deletion).

        Deletes from PostgreSQL first, then clears Redis cache.

        Args:
            user_id: User ID

        Returns:
            Number of conversations deleted
        """
        # Delete from PostgreSQL
        pg_repo = self._get_pg_repo()
        deleted = pg_repo.delete_all_for_user(user_id)

        # Clear Redis cache
        try:
            index_key = self._index_key(user_id)
            conv_ids = self._redis.client.zrange(index_key, 0, -1)

            for conv_id in conv_ids:
                conv_id_str = conv_id.decode("utf-8") if isinstance(conv_id, bytes) else conv_id
                key = self._conv_key(conv_id_str)
                self._redis.client.delete(key)

            self._redis.client.delete(index_key)
        except Exception as e:
            # Redis failure is non-fatal
            logger.warning(f"Failed to clear conversation cache for user {user_id}: {e}")

        logger.info(f"Deleted {deleted} mentor conversations for user {user_id}")
        return deleted

    def get_all_user_messages(
        self,
        user_id: str,
        days: int = 30,
        role: str = "user",
    ) -> list[dict[str, Any]]:
        """Get all messages from a user within time window.

        Retrieves user messages from all conversations for topic detection.
        Filters by timestamp if available, otherwise returns all messages.

        Args:
            user_id: User UUID
            days: Number of days to look back (7-90)
            role: Message role to filter ("user" or "assistant")

        Returns:
            List of message dicts with content, timestamp, conversation_id
        """
        index_key = self._index_key(user_id)

        # Get all conversation IDs (no limit)
        conv_ids = self._redis.client.zrange(index_key, 0, -1)

        cutoff = datetime.now(UTC) - timedelta(days=days)
        messages: list[dict[str, Any]] = []

        for conv_id in conv_ids:
            conv_id_str = conv_id.decode("utf-8") if isinstance(conv_id, bytes) else conv_id
            conv = self.get(conv_id_str, user_id)
            if not conv:
                continue

            for msg in conv.get("messages", []):
                if msg.get("role") != role:
                    continue

                # Filter by timestamp if available
                timestamp_str = msg.get("timestamp", "")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        if timestamp < cutoff:
                            continue
                    except ValueError:
                        pass  # Include message if timestamp parsing fails

                messages.append(
                    {
                        "content": msg.get("content", ""),
                        "timestamp": timestamp_str,
                        "conversation_id": conv_id_str,
                        "persona": msg.get("persona"),
                    }
                )

        return messages


# Singleton instance
_mentor_conversation_repo: MentorConversationRepository | None = None


def get_mentor_conversation_repo() -> MentorConversationRepository:
    """Get or create the mentor conversation repository singleton."""
    global _mentor_conversation_repo
    if _mentor_conversation_repo is None:
        _mentor_conversation_repo = MentorConversationRepository()
    return _mentor_conversation_repo
