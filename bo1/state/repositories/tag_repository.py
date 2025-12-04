"""Tag repository for user-generated tag management.

Handles:
- Tag CRUD operations
- Action-tag associations
- Tag-based action filtering
"""

import logging
from typing import Any
from uuid import UUID

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TagRepository(BaseRepository):
    """Repository for tag management operations."""

    # =========================================================================
    # Tag CRUD
    # =========================================================================

    def create(
        self,
        user_id: str,
        name: str,
        color: str = "#6366F1",
    ) -> dict[str, Any]:
        """Create a new tag.

        Args:
            user_id: User who owns the tag
            name: Tag name (must be unique per user)
            color: Hex color code (default: brand color)

        Returns:
            Created tag record

        Raises:
            ValueError: If tag with same name already exists for user
        """
        return self._execute_returning(
            """
            INSERT INTO tags (user_id, name, color)
            VALUES (%s, %s, %s)
            RETURNING id, user_id, name, color, created_at, updated_at
            """,
            (user_id, name.strip(), color),
            user_id=user_id,
        )

    def get(self, tag_id: str | UUID) -> dict[str, Any] | None:
        """Get a single tag by ID.

        Args:
            tag_id: Tag UUID

        Returns:
            Tag record or None if not found
        """
        return self._execute_one(
            """
            SELECT id, user_id, name, color, created_at, updated_at
            FROM tags
            WHERE id = %s
            """,
            (str(tag_id),),
        )

    def get_by_user(self, user_id: str) -> list[dict[str, Any]]:
        """Get all tags for a user.

        Args:
            user_id: User ID

        Returns:
            List of tag records ordered by name
        """
        return self._execute_query(
            """
            SELECT t.id, t.user_id, t.name, t.color, t.created_at, t.updated_at,
                   COUNT(at.action_id) as action_count
            FROM tags t
            LEFT JOIN action_tags at ON t.id = at.tag_id
            WHERE t.user_id = %s
            GROUP BY t.id
            ORDER BY t.name
            """,
            (user_id,),
            user_id=user_id,
        )

    def update(
        self,
        tag_id: str | UUID,
        user_id: str,
        name: str | None = None,
        color: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a tag.

        Args:
            tag_id: Tag UUID
            user_id: User who owns the tag (for ownership check)
            name: New name (optional)
            color: New color (optional)

        Returns:
            Updated tag record or None if not found/not owned
        """
        updates = []
        params = []

        if name is not None:
            updates.append("name = %s")
            params.append(name.strip())
        if color is not None:
            updates.append("color = %s")
            params.append(color)

        if not updates:
            return self.get(tag_id)

        updates.append("updated_at = NOW()")
        params.extend([str(tag_id), user_id])

        return self._execute_one(
            f"""
            UPDATE tags
            SET {", ".join(updates)}
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, name, color, created_at, updated_at
            """,
            tuple(params),
            user_id=user_id,
        )

    def delete(self, tag_id: str | UUID, user_id: str) -> bool:
        """Delete a tag (also removes all action associations).

        Args:
            tag_id: Tag UUID
            user_id: User who owns the tag

        Returns:
            True if deleted, False if not found
        """
        count = self._execute_count(
            """
            DELETE FROM tags
            WHERE id = %s AND user_id = %s
            """,
            (str(tag_id), user_id),
            user_id=user_id,
        )
        return count > 0

    # =========================================================================
    # Action-Tag Associations
    # =========================================================================

    def add_tag_to_action(
        self,
        action_id: str | UUID,
        tag_id: str | UUID,
        user_id: str,
    ) -> bool:
        """Add a tag to an action.

        Args:
            action_id: Action UUID
            tag_id: Tag UUID
            user_id: User ID (for ownership verification)

        Returns:
            True if added, False if already exists or invalid
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                # Verify ownership of both action and tag
                cur.execute(
                    """
                    SELECT 1 FROM actions a, tags t
                    WHERE a.id = %s AND a.user_id = %s
                      AND t.id = %s AND t.user_id = %s
                    """,
                    (str(action_id), user_id, str(tag_id), user_id),
                )
                if not cur.fetchone():
                    return False

                # Insert (ignore if exists)
                cur.execute(
                    """
                    INSERT INTO action_tags (action_id, tag_id)
                    VALUES (%s, %s)
                    ON CONFLICT (action_id, tag_id) DO NOTHING
                    """,
                    (str(action_id), str(tag_id)),
                )
                return True

    def remove_tag_from_action(
        self,
        action_id: str | UUID,
        tag_id: str | UUID,
        user_id: str,
    ) -> bool:
        """Remove a tag from an action.

        Args:
            action_id: Action UUID
            tag_id: Tag UUID
            user_id: User ID (for ownership verification)

        Returns:
            True if removed, False if not found
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                # Verify user owns the action (tag ownership verified by FK)
                cur.execute(
                    """
                    DELETE FROM action_tags at
                    USING actions a
                    WHERE at.action_id = %s
                      AND at.tag_id = %s
                      AND a.id = at.action_id
                      AND a.user_id = %s
                    """,
                    (str(action_id), str(tag_id), user_id),
                )
                return bool(cur.rowcount and cur.rowcount > 0)

    def get_action_tags(
        self,
        action_id: str | UUID,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Get all tags for an action.

        Args:
            action_id: Action UUID
            user_id: User ID

        Returns:
            List of tag records
        """
        return self._execute_query(
            """
            SELECT t.id, t.user_id, t.name, t.color, t.created_at, t.updated_at
            FROM tags t
            JOIN action_tags at ON t.id = at.tag_id
            JOIN actions a ON at.action_id = a.id
            WHERE at.action_id = %s AND a.user_id = %s
            ORDER BY t.name
            """,
            (str(action_id), user_id),
            user_id=user_id,
        )

    def get_actions_by_tag(
        self,
        tag_id: str | UUID,
        user_id: str,
    ) -> list[str]:
        """Get all action IDs with a specific tag.

        Args:
            tag_id: Tag UUID
            user_id: User ID

        Returns:
            List of action ID strings
        """
        rows = self._execute_query(
            """
            SELECT at.action_id
            FROM action_tags at
            JOIN tags t ON at.tag_id = t.id
            WHERE t.id = %s AND t.user_id = %s
            """,
            (str(tag_id), user_id),
            user_id=user_id,
        )
        return [str(row["action_id"]) for row in rows]

    def set_action_tags(
        self,
        action_id: str | UUID,
        tag_ids: list[str | UUID],
        user_id: str,
    ) -> bool:
        """Set all tags for an action (replaces existing).

        Args:
            action_id: Action UUID
            tag_ids: List of tag UUIDs to set
            user_id: User ID

        Returns:
            True if successful
        """
        with db_session(user_id=user_id) as conn:
            with conn.cursor() as cur:
                # Verify action ownership
                cur.execute(
                    "SELECT 1 FROM actions WHERE id = %s AND user_id = %s",
                    (str(action_id), user_id),
                )
                if not cur.fetchone():
                    return False

                # Remove all existing tags
                cur.execute(
                    "DELETE FROM action_tags WHERE action_id = %s",
                    (str(action_id),),
                )

                # Add new tags (if any)
                if tag_ids:
                    # Verify all tags exist and belong to user
                    tag_id_strs = [str(t) for t in tag_ids]
                    cur.execute(
                        """
                        SELECT id FROM tags
                        WHERE id = ANY(%s) AND user_id = %s
                        """,
                        (tag_id_strs, user_id),
                    )
                    valid_tags = [str(row["id"]) for row in cur.fetchall()]

                    for tag_id in valid_tags:
                        cur.execute(
                            """
                            INSERT INTO action_tags (action_id, tag_id)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                            """,
                            (str(action_id), tag_id),
                        )

                return True


# Singleton instance
tag_repository = TagRepository()
