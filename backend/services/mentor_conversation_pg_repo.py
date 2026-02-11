"""PostgreSQL-backed repository for mentor conversations.

Provides durable storage for mentor chat conversations. Redis cache layer
(in mentor_conversation_repo.py) uses this as the source of truth.
"""

import logging
from functools import lru_cache
from typing import Any

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MentorConversationPgRepository(BaseRepository):
    """PostgreSQL storage for mentor chat conversations."""

    def create(
        self,
        user_id: str,
        persona: str = "general",
    ) -> dict[str, Any]:
        """Create a new mentor conversation.

        Args:
            user_id: User ID (string, matches users.id)
            persona: Initial persona (general, action_coach, data_analyst)

        Returns:
            Conversation dict with id, user_id, persona, created_at, messages
        """
        query = """
            INSERT INTO mentor_conversations (user_id, persona, context_sources)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, persona, label, context_sources, created_at, updated_at
        """
        row = self._execute_returning(
            query,
            (user_id, persona, []),
            user_id=user_id,
        )

        return self._row_to_conversation(row, messages=[])

    def get(
        self,
        conversation_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get a conversation by ID with messages.

        Args:
            conversation_id: Conversation UUID
            user_id: User ID for RLS context

        Returns:
            Conversation dict with messages or None if not found
        """
        # Get conversation
        conv_query = """
            SELECT id, user_id, persona, label, context_sources, created_at, updated_at
            FROM mentor_conversations
            WHERE id = %s
        """
        conv_row = self._execute_one(conv_query, (conversation_id,), user_id=user_id)
        if not conv_row:
            return None

        # Verify ownership if user_id provided
        if user_id and str(conv_row.get("user_id")) != user_id:
            logger.warning(
                f"User {user_id} attempted to access mentor conversation {conversation_id} "
                f"owned by {conv_row.get('user_id')}"
            )
            return None

        # Get messages
        msg_query = """
            SELECT id, role, content, persona, created_at
            FROM mentor_messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """
        msg_rows = self._execute_query(msg_query, (conversation_id,), user_id=user_id)

        messages = [self._row_to_message(r) for r in msg_rows]
        return self._row_to_conversation(conv_row, messages)

    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        persona: str | None = None,
        context_sources: list[str] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Append a message to a mentor conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user or assistant)
            content: Message content
            persona: Optional persona used for this message
            context_sources: Optional list of context sources used
            user_id: User ID for RLS context

        Returns:
            Updated conversation dict or None if not found
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                # Insert message
                cur.execute(
                    """
                    INSERT INTO mentor_messages (conversation_id, role, content, persona)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, role, content, persona, created_at
                    """,
                    (conversation_id, role, content, persona),
                )
                new_msg = cur.fetchone()
                if not new_msg:
                    return None

                # Update conversation updated_at and optionally persona/context_sources
                update_parts = ["updated_at = NOW()"]
                params: list[Any] = []

                if persona:
                    update_parts.append("persona = %s")
                    params.append(persona)

                if context_sources:
                    # Merge with existing context_sources
                    update_parts.append(
                        "context_sources = ARRAY(SELECT DISTINCT unnest(context_sources || %s))"
                    )
                    params.append(context_sources)

                params.append(conversation_id)

                cur.execute(
                    f"""
                    UPDATE mentor_conversations
                    SET {", ".join(update_parts)}
                    WHERE id = %s
                    RETURNING id, user_id, persona, label, context_sources, created_at, updated_at
                    """,
                    tuple(params),
                )
                conv_row = cur.fetchone()
                if not conv_row:
                    return None

                # Get all messages
                cur.execute(
                    """
                    SELECT id, role, content, persona, created_at
                    FROM mentor_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC
                    """,
                    (conversation_id,),
                )
                msg_rows = cur.fetchall()

        messages = [self._row_to_message(dict(r)) for r in msg_rows]
        return self._row_to_conversation(dict(conv_row), messages)

    def list_by_context_source(
        self,
        user_id: str,
        source_prefix: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List conversations with a specific context source prefix.

        Args:
            user_id: User ID
            source_prefix: Prefix to match (e.g., "blindspot:" matches "blindspot:over_planning")
            limit: Maximum conversations to return

        Returns:
            List of conversation dicts with message counts
        """
        query = """
            SELECT
                c.id, c.user_id, c.persona, c.label, c.context_sources,
                c.created_at, c.updated_at,
                COUNT(m.id) as message_count
            FROM mentor_conversations c
            LEFT JOIN mentor_messages m ON c.id = m.conversation_id
            WHERE c.user_id = %s
              AND EXISTS (
                  SELECT 1 FROM unnest(c.context_sources) AS src
                  WHERE src LIKE %s
              )
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT %s
        """
        rows = self._execute_query(query, (user_id, f"{source_prefix}%", limit), user_id=user_id)

        conversations = []
        for row in rows:
            conversations.append(
                {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "persona": row.get("persona", "general"),
                    "label": row.get("label"),
                    "created_at": self._to_iso_string(row["created_at"]),
                    "updated_at": self._to_iso_string(row["updated_at"]),
                    "message_count": row.get("message_count", 0),
                    "context_sources": row.get("context_sources") or [],
                }
            )

        return conversations

    def count_by_context_source(
        self,
        user_id: str,
        source_prefix: str,
    ) -> int:
        """Count conversations with a specific context source prefix.

        Args:
            user_id: User ID
            source_prefix: Prefix to match (e.g., "blindspot:")

        Returns:
            Count of matching conversations
        """
        query = """
            SELECT COUNT(*) as count
            FROM mentor_conversations
            WHERE user_id = %s
              AND EXISTS (
                  SELECT 1 FROM unnest(context_sources) AS src
                  WHERE src LIKE %s
              )
        """
        row = self._execute_one(query, (user_id, f"{source_prefix}%"), user_id=user_id)
        return row["count"] if row else 0

    def list_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List recent mentor conversations for a user.

        Args:
            user_id: User ID
            limit: Maximum conversations to return
            offset: Offset for pagination

        Returns:
            Tuple of (conversations list, total count)
        """
        # Get total count
        count_query = """
            SELECT COUNT(*) as count
            FROM mentor_conversations
            WHERE user_id = %s
        """
        count_row = self._execute_one(count_query, (user_id,), user_id=user_id)
        total = count_row["count"] if count_row else 0

        # Get conversations with message counts
        query = """
            SELECT
                c.id, c.user_id, c.persona, c.label, c.context_sources,
                c.created_at, c.updated_at,
                COUNT(m.id) as message_count
            FROM mentor_conversations c
            LEFT JOIN mentor_messages m ON c.id = m.conversation_id
            WHERE c.user_id = %s
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT %s OFFSET %s
        """
        rows = self._execute_query(query, (user_id, limit, offset), user_id=user_id)

        conversations = []
        for row in rows:
            conversations.append(
                {
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "persona": row.get("persona", "general"),
                    "label": row.get("label"),
                    "created_at": self._to_iso_string(row["created_at"]),
                    "updated_at": self._to_iso_string(row["updated_at"]),
                    "message_count": row.get("message_count", 0),
                    "context_sources": row.get("context_sources") or [],
                }
            )

        return conversations, total

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
        query = """
            DELETE FROM mentor_conversations
            WHERE id = %s AND user_id = %s
        """
        count = self._execute_count(query, (conversation_id, user_id), user_id=user_id)
        if count > 0:
            logger.info(f"Deleted mentor conversation {conversation_id}")
            return True
        return False

    def delete_all_for_user(self, user_id: str) -> int:
        """Delete all mentor conversations for a user (for GDPR deletion).

        Args:
            user_id: User ID

        Returns:
            Number of conversations deleted
        """
        query = """
            DELETE FROM mentor_conversations
            WHERE user_id = %s
        """
        count = self._execute_count(query, (user_id,), user_id=user_id)
        logger.info(f"Deleted {count} mentor conversations for user {user_id}")
        return count

    def update_label(
        self,
        conversation_id: str,
        label: str,
        user_id: str,
    ) -> bool:
        """Update conversation label.

        Args:
            conversation_id: Conversation UUID
            label: New label
            user_id: User ID for ownership check

        Returns:
            True if updated, False if not found
        """
        query = """
            UPDATE mentor_conversations
            SET label = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
        """
        count = self._execute_count(query, (label, conversation_id, user_id), user_id=user_id)
        return count > 0

    def get_all_for_export(self, user_id: str) -> list[dict[str, Any]]:
        """Get all conversations with messages for GDPR export.

        Args:
            user_id: User ID

        Returns:
            List of conversation dicts with full messages
        """
        # Get all conversations
        conv_query = """
            SELECT id, user_id, persona, label, context_sources, created_at, updated_at
            FROM mentor_conversations
            WHERE user_id = %s
            ORDER BY created_at DESC
        """
        conv_rows = self._execute_query(conv_query, (user_id,), user_id=user_id)

        conversations = []
        for conv_row in conv_rows:
            conv_id = conv_row["id"]
            # Get messages for this conversation
            msg_query = """
                SELECT id, role, content, persona, created_at
                FROM mentor_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            """
            msg_rows = self._execute_query(msg_query, (conv_id,), user_id=user_id)
            messages = [self._row_to_message(r) for r in msg_rows]
            conversations.append(self._row_to_conversation(conv_row, messages))

        return conversations

    def _row_to_conversation(
        self,
        row: dict[str, Any],
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Convert database row to conversation dict.

        Args:
            row: Database row dict
            messages: List of message dicts

        Returns:
            Conversation dict matching Redis format
        """
        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "persona": row.get("persona", "general"),
            "label": row.get("label"),
            "created_at": self._to_iso_string(row["created_at"]),
            "updated_at": self._to_iso_string(row["updated_at"]),
            "messages": messages,
            "context_sources": row.get("context_sources") or [],
        }

    def _row_to_message(self, row: dict[str, Any]) -> dict[str, Any]:
        """Convert database row to message dict.

        Args:
            row: Database row dict

        Returns:
            Message dict matching Redis format
        """
        return {
            "role": row["role"],
            "content": row["content"],
            "timestamp": self._to_iso_string(row["created_at"]),
            "persona": row.get("persona"),
        }


# Singleton instance


@lru_cache(maxsize=1)
def get_mentor_conversation_pg_repo() -> MentorConversationPgRepository:
    """Get or create the mentor conversation PostgreSQL repository singleton."""
    return MentorConversationPgRepository()
