"""PostgreSQL-backed repository for dataset conversations.

Provides durable storage for dataset Q&A conversations. Redis cache layer
(in conversation_repo.py) uses this as the source of truth.
"""

import logging
from typing import Any

from psycopg2.extras import Json

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DatasetConversationPgRepository(BaseRepository):
    """PostgreSQL storage for dataset Q&A conversations."""

    def create(
        self,
        dataset_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """Create a new dataset conversation.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID (string, matches users.id)

        Returns:
            Conversation dict with id, dataset_id, user_id, created_at, messages
        """
        query = """
            INSERT INTO dataset_conversations (dataset_id, user_id)
            VALUES (%s, %s)
            RETURNING id, dataset_id, user_id, label, created_at, updated_at
        """
        row = self._execute_returning(
            query,
            (dataset_id, user_id),
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
            SELECT id, dataset_id, user_id, label, created_at, updated_at
            FROM dataset_conversations
            WHERE id = %s
        """
        conv_row = self._execute_one(conv_query, (conversation_id,), user_id=user_id)
        if not conv_row:
            return None

        # Verify ownership if user_id provided
        if user_id and str(conv_row.get("user_id")) != user_id:
            logger.warning(
                f"User {user_id} attempted to access dataset conversation {conversation_id} "
                f"owned by {conv_row.get('user_id')}"
            )
            return None

        # Get messages
        msg_query = """
            SELECT id, role, content, query_spec, chart_spec, query_result, created_at
            FROM dataset_messages
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
        query_spec: dict[str, Any] | None = None,
        chart_spec: dict[str, Any] | None = None,
        query_result: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Append a message to a dataset conversation.

        Args:
            conversation_id: Conversation UUID
            role: Message role (user or assistant)
            content: Message content
            query_spec: Optional SQL query spec
            chart_spec: Optional chart spec
            query_result: Optional query result summary
            user_id: User ID for RLS context

        Returns:
            Updated conversation dict or None if not found
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                # Insert message
                cur.execute(
                    """
                    INSERT INTO dataset_messages
                        (conversation_id, role, content, query_spec, chart_spec, query_result)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, role, content, query_spec, chart_spec, query_result, created_at
                    """,
                    (
                        conversation_id,
                        role,
                        content,
                        Json(query_spec) if query_spec else None,
                        Json(chart_spec) if chart_spec else None,
                        Json(query_result) if query_result else None,
                    ),
                )
                new_msg = cur.fetchone()
                if not new_msg:
                    return None

                # Update conversation updated_at
                cur.execute(
                    """
                    UPDATE dataset_conversations
                    SET updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, dataset_id, user_id, label, created_at, updated_at
                    """,
                    (conversation_id,),
                )
                conv_row = cur.fetchone()
                if not conv_row:
                    return None

                # Get all messages
                cur.execute(
                    """
                    SELECT id, role, content, query_spec, chart_spec, query_result, created_at
                    FROM dataset_messages
                    WHERE conversation_id = %s
                    ORDER BY created_at ASC
                    """,
                    (conversation_id,),
                )
                msg_rows = cur.fetchall()

        messages = [self._row_to_message(dict(r)) for r in msg_rows]
        return self._row_to_conversation(dict(conv_row), messages)

    def list_by_dataset(
        self,
        dataset_id: str,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List recent conversations for a dataset.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID
            limit: Maximum conversations to return
            offset: Offset for pagination

        Returns:
            Tuple of (conversations list, total count)
        """
        # Get total count
        count_query = """
            SELECT COUNT(*) as count
            FROM dataset_conversations
            WHERE dataset_id = %s AND user_id = %s
        """
        count_row = self._execute_one(count_query, (dataset_id, user_id), user_id=user_id)
        total = count_row["count"] if count_row else 0

        # Get conversations with message counts
        query = """
            SELECT
                c.id, c.dataset_id, c.user_id, c.label,
                c.created_at, c.updated_at,
                COUNT(m.id) as message_count
            FROM dataset_conversations c
            LEFT JOIN dataset_messages m ON c.id = m.conversation_id
            WHERE c.dataset_id = %s AND c.user_id = %s
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT %s OFFSET %s
        """
        rows = self._execute_query(query, (dataset_id, user_id, limit, offset), user_id=user_id)

        conversations = []
        for row in rows:
            conversations.append(
                {
                    "id": str(row["id"]),
                    "dataset_id": str(row["dataset_id"]),
                    "created_at": self._to_iso_string(row["created_at"]),
                    "updated_at": self._to_iso_string(row["updated_at"]),
                    "message_count": row.get("message_count", 0),
                }
            )

        return conversations, total

    def delete(
        self,
        conversation_id: str,
        user_id: str,
    ) -> bool:
        """Delete a dataset conversation.

        Args:
            conversation_id: Conversation UUID
            user_id: User UUID for ownership check

        Returns:
            True if deleted, False if not found
        """
        query = """
            DELETE FROM dataset_conversations
            WHERE id = %s AND user_id = %s
        """
        count = self._execute_count(query, (conversation_id, user_id), user_id=user_id)
        if count > 0:
            logger.info(f"Deleted dataset conversation {conversation_id}")
            return True
        return False

    def delete_all_for_user(self, user_id: str) -> int:
        """Delete all dataset conversations for a user (for GDPR deletion).

        Args:
            user_id: User ID

        Returns:
            Number of conversations deleted
        """
        query = """
            DELETE FROM dataset_conversations
            WHERE user_id = %s
        """
        count = self._execute_count(query, (user_id,), user_id=user_id)
        logger.info(f"Deleted {count} dataset conversations for user {user_id}")
        return count

    def delete_all_for_dataset(self, dataset_id: str, user_id: str) -> int:
        """Delete all conversations for a dataset (cascade on dataset delete).

        Args:
            dataset_id: Dataset UUID
            user_id: User ID for RLS context

        Returns:
            Number of conversations deleted
        """
        query = """
            DELETE FROM dataset_conversations
            WHERE dataset_id = %s AND user_id = %s
        """
        count = self._execute_count(query, (dataset_id, user_id), user_id=user_id)
        logger.info(f"Deleted {count} conversations for dataset {dataset_id}")
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
            UPDATE dataset_conversations
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
            SELECT id, dataset_id, user_id, label, created_at, updated_at
            FROM dataset_conversations
            WHERE user_id = %s
            ORDER BY created_at DESC
        """
        conv_rows = self._execute_query(conv_query, (user_id,), user_id=user_id)

        conversations = []
        for conv_row in conv_rows:
            conv_id = conv_row["id"]
            # Get messages for this conversation
            msg_query = """
                SELECT id, role, content, query_spec, chart_spec, query_result, created_at
                FROM dataset_messages
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
            "dataset_id": str(row["dataset_id"]),
            "user_id": str(row["user_id"]),
            "label": row.get("label"),
            "created_at": self._to_iso_string(row["created_at"]),
            "updated_at": self._to_iso_string(row["updated_at"]),
            "messages": messages,
        }

    def _row_to_message(self, row: dict[str, Any]) -> dict[str, Any]:
        """Convert database row to message dict.

        Args:
            row: Database row dict

        Returns:
            Message dict matching Redis format
        """
        msg = {
            "role": row["role"],
            "content": row["content"],
            "timestamp": self._to_iso_string(row["created_at"]),
        }
        if row.get("query_spec"):
            msg["query_spec"] = row["query_spec"]
        if row.get("chart_spec"):
            msg["chart_spec"] = row["chart_spec"]
        if row.get("query_result"):
            msg["query_result"] = row["query_result"]
        return msg


# Singleton instance
_dataset_conversation_pg_repo: DatasetConversationPgRepository | None = None


def get_dataset_conversation_pg_repo() -> DatasetConversationPgRepository:
    """Get or create the dataset conversation PostgreSQL repository singleton."""
    global _dataset_conversation_pg_repo
    if _dataset_conversation_pg_repo is None:
        _dataset_conversation_pg_repo = DatasetConversationPgRepository()
    return _dataset_conversation_pg_repo
