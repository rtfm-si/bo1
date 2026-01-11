"""Dataset folder repository for hierarchical dataset organization.

Handles:
- Folder CRUD operations
- Tag management
- Dataset membership
- Nested folder tree queries
"""

import logging
from typing import Any

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DatasetFolderRepository(BaseRepository):
    """Repository for dataset folder management."""

    # =========================================================================
    # Folder CRUD
    # =========================================================================

    def create_folder(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        parent_folder_id: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new folder.

        Args:
            user_id: Folder owner
            name: Folder name
            description: Optional description
            color: Hex color (e.g. #FF5733)
            icon: Icon name
            parent_folder_id: Parent folder UUID for nesting
            tags: Initial tags

        Returns:
            Created folder record with tags
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Create folder
                cur.execute(
                    """
                    INSERT INTO dataset_folders (user_id, name, description, color, icon, parent_folder_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, name, description, color, icon, parent_folder_id,
                              created_at, updated_at
                    """,
                    (user_id, name, description, color, icon, parent_folder_id),
                )
                row = cur.fetchone()
                folder_id = row["id"]

                # Insert tags if provided
                if tags:
                    for tag in tags:
                        cur.execute(
                            """
                            INSERT INTO dataset_folder_tags (folder_id, tag_name)
                            VALUES (%s, %s)
                            ON CONFLICT (folder_id, tag_name) DO NOTHING
                            """,
                            (folder_id, tag.strip().lower()),
                        )

                conn.commit()

        # Return folder with tags
        return self.get_folder(str(folder_id), user_id)  # type: ignore

    def get_folder(self, folder_id: str, user_id: str) -> dict[str, Any] | None:
        """Get a folder by ID with tags and dataset count.

        Args:
            folder_id: Folder UUID
            user_id: User ID for ownership check

        Returns:
            Folder dict with tags and dataset_count, or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        f.id, f.user_id, f.name, f.description, f.color, f.icon,
                        f.parent_folder_id, f.created_at, f.updated_at,
                        COALESCE(
                            (SELECT array_agg(tag_name ORDER BY tag_name)
                             FROM dataset_folder_tags WHERE folder_id = f.id),
                            ARRAY[]::text[]
                        ) as tags,
                        (SELECT COUNT(*) FROM dataset_folder_memberships WHERE folder_id = f.id) as dataset_count
                    FROM dataset_folders f
                    WHERE f.id = %s AND f.user_id = %s
                    """,
                    (folder_id, user_id),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
                return None

    def list_folders(
        self,
        user_id: str,
        parent_folder_id: str | None = None,
        tag: str | None = None,
    ) -> list[dict[str, Any]]:
        """List folders for a user.

        Args:
            user_id: Folder owner
            parent_folder_id: Filter by parent (None = root folders only)
            tag: Filter by tag name

        Returns:
            List of folder dicts with tags and dataset counts
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT
                        f.id, f.user_id, f.name, f.description, f.color, f.icon,
                        f.parent_folder_id, f.created_at, f.updated_at,
                        COALESCE(
                            (SELECT array_agg(tag_name ORDER BY tag_name)
                             FROM dataset_folder_tags WHERE folder_id = f.id),
                            ARRAY[]::text[]
                        ) as tags,
                        (SELECT COUNT(*) FROM dataset_folder_memberships WHERE folder_id = f.id) as dataset_count
                    FROM dataset_folders f
                    WHERE f.user_id = %s
                """
                params: list[Any] = [user_id]

                if parent_folder_id is not None:
                    base_query += " AND f.parent_folder_id = %s"
                    params.append(parent_folder_id)
                else:
                    base_query += " AND f.parent_folder_id IS NULL"

                if tag:
                    base_query += """
                        AND EXISTS (
                            SELECT 1 FROM dataset_folder_tags t
                            WHERE t.folder_id = f.id AND t.tag_name = %s
                        )
                    """
                    params.append(tag.strip().lower())

                base_query += " ORDER BY f.name"
                cur.execute(base_query, params)
                return [dict(row) for row in cur.fetchall()]

    def list_all_folders(self, user_id: str) -> list[dict[str, Any]]:
        """List all folders for a user (flat list).

        Args:
            user_id: Folder owner

        Returns:
            All folders with tags and dataset counts
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        f.id, f.user_id, f.name, f.description, f.color, f.icon,
                        f.parent_folder_id, f.created_at, f.updated_at,
                        COALESCE(
                            (SELECT array_agg(tag_name ORDER BY tag_name)
                             FROM dataset_folder_tags WHERE folder_id = f.id),
                            ARRAY[]::text[]
                        ) as tags,
                        (SELECT COUNT(*) FROM dataset_folder_memberships WHERE folder_id = f.id) as dataset_count
                    FROM dataset_folders f
                    WHERE f.user_id = %s
                    ORDER BY f.name
                    """,
                    (user_id,),
                )
                return [dict(row) for row in cur.fetchall()]

    def update_folder(
        self,
        folder_id: str,
        user_id: str,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        parent_folder_id: str | None = None,
        tags: list[str] | None = None,
        clear_parent: bool = False,
    ) -> dict[str, Any] | None:
        """Update folder fields.

        Args:
            folder_id: Folder UUID
            user_id: User ID for ownership check
            name: New name
            description: New description
            color: New color
            icon: New icon
            parent_folder_id: New parent folder
            tags: Replace tags if provided
            clear_parent: If True, set parent to NULL

        Returns:
            Updated folder or None if not found
        """
        updates: list[str] = []
        params: list[Any] = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if color is not None:
            updates.append("color = %s")
            params.append(color)
        if icon is not None:
            updates.append("icon = %s")
            params.append(icon)
        if parent_folder_id is not None:
            updates.append("parent_folder_id = %s")
            params.append(parent_folder_id)
        elif clear_parent:
            updates.append("parent_folder_id = NULL")

        if not updates and tags is None:
            return self.get_folder(folder_id, user_id)

        with db_session() as conn:
            with conn.cursor() as cur:
                if updates:
                    updates.append("updated_at = now()")
                    query = f"""
                        UPDATE dataset_folders
                        SET {", ".join(updates)}
                        WHERE id = %s AND user_id = %s
                        RETURNING id
                    """
                    params.extend([folder_id, user_id])
                    cur.execute(query, params)
                    if not cur.fetchone():
                        return None

                if tags is not None:
                    # Replace all tags
                    cur.execute(
                        "DELETE FROM dataset_folder_tags WHERE folder_id = %s",
                        (folder_id,),
                    )
                    for tag in tags:
                        cur.execute(
                            """
                            INSERT INTO dataset_folder_tags (folder_id, tag_name)
                            VALUES (%s, %s)
                            ON CONFLICT (folder_id, tag_name) DO NOTHING
                            """,
                            (folder_id, tag.strip().lower()),
                        )

                conn.commit()

        return self.get_folder(folder_id, user_id)

    def delete_folder(self, folder_id: str, user_id: str) -> bool:
        """Delete a folder. Datasets are removed from folder (not deleted).

        Args:
            folder_id: Folder UUID
            user_id: User ID for ownership check

        Returns:
            True if deleted, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM dataset_folders
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (folder_id, user_id),
                )
                return cur.fetchone() is not None

    # =========================================================================
    # Folder Tree (Recursive CTE)
    # =========================================================================

    def get_folder_tree(self, user_id: str, max_depth: int = 4) -> list[dict[str, Any]]:
        """Get folders as a nested tree structure.

        Args:
            user_id: Folder owner
            max_depth: Maximum nesting depth (default 4)

        Returns:
            Root folders with nested children
        """
        # Get all folders flat first
        all_folders = self.list_all_folders(user_id)

        # Build tree in memory (more efficient than recursive CTE for moderate folder counts)
        folder_map = {str(f["id"]): {**f, "children": []} for f in all_folders}

        roots = []
        for folder in all_folders:
            folder_id = str(folder["id"])
            parent_id = str(folder["parent_folder_id"]) if folder["parent_folder_id"] else None

            if parent_id and parent_id in folder_map:
                folder_map[parent_id]["children"].append(folder_map[folder_id])
            else:
                roots.append(folder_map[folder_id])

        return roots

    # =========================================================================
    # Dataset Membership
    # =========================================================================

    def add_datasets_to_folder(
        self,
        folder_id: str,
        dataset_ids: list[str],
        user_id: str,
    ) -> int:
        """Add datasets to a folder.

        Args:
            folder_id: Folder UUID
            dataset_ids: Dataset UUIDs to add
            user_id: User ID for ownership check

        Returns:
            Number of datasets added
        """
        # First verify folder ownership
        folder = self.get_folder(folder_id, user_id)
        if not folder:
            return 0

        added = 0
        with db_session() as conn:
            with conn.cursor() as cur:
                for dataset_id in dataset_ids:
                    # Verify dataset ownership
                    cur.execute(
                        "SELECT id FROM datasets WHERE id = %s AND user_id = %s",
                        (dataset_id, user_id),
                    )
                    if cur.fetchone():
                        cur.execute(
                            """
                            INSERT INTO dataset_folder_memberships (folder_id, dataset_id)
                            VALUES (%s, %s)
                            ON CONFLICT (folder_id, dataset_id) DO NOTHING
                            """,
                            (folder_id, dataset_id),
                        )
                        if cur.rowcount > 0:
                            added += 1
                conn.commit()

        return added

    def remove_dataset_from_folder(
        self,
        folder_id: str,
        dataset_id: str,
        user_id: str,
    ) -> bool:
        """Remove a dataset from a folder.

        Args:
            folder_id: Folder UUID
            dataset_id: Dataset UUID
            user_id: User ID for ownership check

        Returns:
            True if removed, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Verify folder ownership
                cur.execute(
                    "SELECT id FROM dataset_folders WHERE id = %s AND user_id = %s",
                    (folder_id, user_id),
                )
                if not cur.fetchone():
                    return False

                cur.execute(
                    """
                    DELETE FROM dataset_folder_memberships
                    WHERE folder_id = %s AND dataset_id = %s
                    RETURNING folder_id
                    """,
                    (folder_id, dataset_id),
                )
                return cur.fetchone() is not None

    def get_folder_datasets(
        self,
        folder_id: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Get datasets in a folder.

        Args:
            folder_id: Folder UUID
            user_id: User ID for ownership check

        Returns:
            List of dataset info dicts
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.id, d.name, m.added_at
                    FROM dataset_folder_memberships m
                    JOIN datasets d ON d.id = m.dataset_id
                    JOIN dataset_folders f ON f.id = m.folder_id
                    WHERE m.folder_id = %s AND f.user_id = %s
                    ORDER BY d.name
                    """,
                    (folder_id, user_id),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_dataset_folders(self, dataset_id: str, user_id: str) -> list[dict[str, Any]]:
        """Get all folders a dataset belongs to.

        Args:
            dataset_id: Dataset UUID
            user_id: User ID for ownership check

        Returns:
            List of folder info dicts
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT f.id, f.name, f.color, f.icon, m.added_at
                    FROM dataset_folder_memberships m
                    JOIN dataset_folders f ON f.id = m.folder_id
                    WHERE m.dataset_id = %s AND f.user_id = %s
                    ORDER BY f.name
                    """,
                    (dataset_id, user_id),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_uncategorized_datasets(self, user_id: str) -> list[dict[str, Any]]:
        """Get datasets not in any folder.

        Args:
            user_id: Dataset owner

        Returns:
            List of dataset info dicts
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.id, d.name, d.created_at
                    FROM datasets d
                    WHERE d.user_id = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM dataset_folder_memberships m
                        WHERE m.dataset_id = d.id
                    )
                    ORDER BY d.name
                    """,
                    (user_id,),
                )
                return [dict(row) for row in cur.fetchall()]

    # =========================================================================
    # Tags
    # =========================================================================

    def get_all_tags(self, user_id: str) -> list[str]:
        """Get all unique folder tags for a user.

        Args:
            user_id: Folder owner

        Returns:
            Sorted list of unique tag names
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT t.tag_name
                    FROM dataset_folder_tags t
                    JOIN dataset_folders f ON f.id = t.folder_id
                    WHERE f.user_id = %s
                    ORDER BY t.tag_name
                    """,
                    (user_id,),
                )
                return [row["tag_name"] for row in cur.fetchall()]

    def search_folders_by_tag(self, user_id: str, tag: str) -> list[dict[str, Any]]:
        """Search folders by tag.

        Args:
            user_id: Folder owner
            tag: Tag to search for

        Returns:
            Matching folders
        """
        return self.list_folders(user_id, tag=tag.strip().lower())


# Module-level singleton
dataset_folder_repository = DatasetFolderRepository()
