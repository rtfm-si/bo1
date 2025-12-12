"""Workspace repository for team collaboration.

Provides:
- create_workspace(), get_workspace(), update_workspace()
- add_member(), remove_member(), get_members()
- get_user_workspaces()
"""

import logging
import re
import uuid
from typing import Any

from backend.api.workspaces.models import (
    MemberRole,
    WorkspaceMemberResponse,
    WorkspaceResponse,
)

from .base import BaseRepository

logger = logging.getLogger(__name__)


class WorkspaceRepository(BaseRepository):
    """Repository for workspace and team member operations."""

    def create_workspace(
        self,
        name: str,
        owner_id: str,
        slug: str | None = None,
    ) -> WorkspaceResponse:
        """Create a new workspace.

        Args:
            name: Workspace display name
            owner_id: User ID of the workspace owner
            slug: Optional URL-friendly slug (auto-generated if not provided)

        Returns:
            Created workspace

        Raises:
            ValueError: If slug already exists
        """
        workspace_id = uuid.uuid4()

        # Generate slug from name if not provided
        if not slug:
            slug = self._generate_slug(name, str(workspace_id))

        # Create workspace
        query = """
            INSERT INTO workspaces (id, name, slug, owner_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, slug, owner_id, created_at, updated_at
        """
        row = self._execute_returning(
            query,
            (workspace_id, name, slug, owner_id),
        )

        # Add owner as member with owner role
        self._add_member_internal(
            workspace_id=workspace_id,
            user_id=owner_id,
            role=MemberRole.OWNER,
            invited_by=None,
        )

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=1,
        )

    def get_workspace(self, workspace_id: uuid.UUID) -> WorkspaceResponse | None:
        """Get a workspace by ID.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workspace or None if not found
        """
        query = """
            SELECT w.id, w.name, w.slug, w.owner_id, w.created_at, w.updated_at,
                   COUNT(wm.id) as member_count
            FROM workspaces w
            LEFT JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE w.id = %s
            GROUP BY w.id
        """
        row = self._execute_one(query, (workspace_id,))
        if not row:
            return None

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=row["member_count"],
        )

    def get_workspace_by_slug(self, slug: str) -> WorkspaceResponse | None:
        """Get a workspace by slug.

        Args:
            slug: Workspace slug

        Returns:
            Workspace or None if not found
        """
        query = """
            SELECT w.id, w.name, w.slug, w.owner_id, w.created_at, w.updated_at,
                   COUNT(wm.id) as member_count
            FROM workspaces w
            LEFT JOIN workspace_members wm ON w.id = wm.workspace_id
            WHERE w.slug = %s
            GROUP BY w.id
        """
        row = self._execute_one(query, (slug,))
        if not row:
            return None

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            member_count=row["member_count"],
        )

    def update_workspace(
        self,
        workspace_id: uuid.UUID,
        name: str | None = None,
        slug: str | None = None,
    ) -> WorkspaceResponse | None:
        """Update a workspace.

        Args:
            workspace_id: Workspace UUID
            name: New name (optional)
            slug: New slug (optional)

        Returns:
            Updated workspace or None if not found
        """
        updates: list[str] = []
        params: list[Any] = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)

        if slug is not None:
            updates.append("slug = %s")
            params.append(slug)

        if not updates:
            return self.get_workspace(workspace_id)

        updates.append("updated_at = NOW()")
        params.append(workspace_id)

        query = f"""
            UPDATE workspaces
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, name, slug, owner_id, created_at, updated_at
        """
        row = self._execute_one(query, tuple(params))
        if not row:
            return None

        return WorkspaceResponse(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete_workspace(self, workspace_id: uuid.UUID) -> bool:
        """Delete a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            True if deleted, False if not found
        """
        query = "DELETE FROM workspaces WHERE id = %s"
        count = self._execute_count(query, (workspace_id,))
        return count > 0

    def add_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        role: MemberRole,
        invited_by: str | None = None,
    ) -> WorkspaceMemberResponse:
        """Add a user to a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID to add
            role: Member role
            invited_by: User ID who invited this member

        Returns:
            Created membership

        Raises:
            ValueError: If user is already a member
        """
        return self._add_member_internal(workspace_id, user_id, role, invited_by)

    def _add_member_internal(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        role: MemberRole,
        invited_by: str | None,
    ) -> WorkspaceMemberResponse:
        """Internal method to add a member."""
        member_id = uuid.uuid4()
        query = """
            INSERT INTO workspace_members (id, workspace_id, user_id, role, invited_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, workspace_id, user_id, role, invited_by, joined_at
        """
        row = self._execute_returning(
            query,
            (member_id, workspace_id, user_id, role.value, invited_by),
        )

        return WorkspaceMemberResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=MemberRole(row["role"]),
            invited_by=row["invited_by"],
            joined_at=row["joined_at"],
        )

    def remove_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> bool:
        """Remove a user from a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID to remove

        Returns:
            True if removed, False if not found
        """
        query = """
            DELETE FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
        """
        count = self._execute_count(query, (workspace_id, user_id))
        return count > 0

    def update_member_role(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
        role: MemberRole,
    ) -> WorkspaceMemberResponse | None:
        """Update a member's role.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID
            role: New role

        Returns:
            Updated membership or None if not found
        """
        query = """
            UPDATE workspace_members
            SET role = %s
            WHERE workspace_id = %s AND user_id = %s
            RETURNING id, workspace_id, user_id, role, invited_by, joined_at
        """
        row = self._execute_one(query, (role.value, workspace_id, user_id))
        if not row:
            return None

        return WorkspaceMemberResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=MemberRole(row["role"]),
            invited_by=row["invited_by"],
            joined_at=row["joined_at"],
        )

    def get_members(
        self,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceMemberResponse]:
        """Get all members of a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            List of workspace members
        """
        query = """
            SELECT wm.id, wm.workspace_id, wm.user_id, wm.role, wm.invited_by,
                   wm.joined_at, u.email as user_email
            FROM workspace_members wm
            LEFT JOIN users u ON wm.user_id = u.id
            WHERE wm.workspace_id = %s
            ORDER BY wm.joined_at
        """
        rows = self._execute_query(query, (workspace_id,))

        return [
            WorkspaceMemberResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                user_id=row["user_id"],
                role=MemberRole(row["role"]),
                invited_by=row["invited_by"],
                joined_at=row["joined_at"],
                user_email=row.get("user_email"),
            )
            for row in rows
        ]

    def get_member(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> WorkspaceMemberResponse | None:
        """Get a specific member of a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            Workspace member or None if not found
        """
        query = """
            SELECT wm.id, wm.workspace_id, wm.user_id, wm.role, wm.invited_by,
                   wm.joined_at, u.email as user_email
            FROM workspace_members wm
            LEFT JOIN users u ON wm.user_id = u.id
            WHERE wm.workspace_id = %s AND wm.user_id = %s
        """
        row = self._execute_one(query, (workspace_id, user_id))
        if not row:
            return None

        return WorkspaceMemberResponse(
            id=row["id"],
            workspace_id=row["workspace_id"],
            user_id=row["user_id"],
            role=MemberRole(row["role"]),
            invited_by=row["invited_by"],
            joined_at=row["joined_at"],
            user_email=row.get("user_email"),
        )

    def get_user_workspaces(self, user_id: str) -> list[WorkspaceResponse]:
        """Get all workspaces a user is a member of.

        Args:
            user_id: User ID

        Returns:
            List of workspaces
        """
        query = """
            SELECT w.id, w.name, w.slug, w.owner_id, w.created_at, w.updated_at,
                   COUNT(wm2.id) as member_count
            FROM workspaces w
            INNER JOIN workspace_members wm ON w.id = wm.workspace_id
            LEFT JOIN workspace_members wm2 ON w.id = wm2.workspace_id
            WHERE wm.user_id = %s
            GROUP BY w.id
            ORDER BY w.created_at DESC
        """
        rows = self._execute_query(query, (user_id,))

        return [
            WorkspaceResponse(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                owner_id=row["owner_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                member_count=row["member_count"],
            )
            for row in rows
        ]

    def is_member(self, workspace_id: uuid.UUID, user_id: str) -> bool:
        """Check if a user is a member of a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            True if user is a member
        """
        query = """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
            LIMIT 1
        """
        row = self._execute_one(query, (workspace_id, user_id))
        return row is not None

    def get_member_role(
        self,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> MemberRole | None:
        """Get a user's role in a workspace.

        Args:
            workspace_id: Workspace UUID
            user_id: User ID

        Returns:
            Member role or None if not a member
        """
        query = """
            SELECT role FROM workspace_members
            WHERE workspace_id = %s AND user_id = %s
        """
        row = self._execute_one(query, (workspace_id, user_id))
        if not row:
            return None
        return MemberRole(row["role"])

    def _generate_slug(self, name: str, workspace_id: str) -> str:
        """Generate a URL-friendly slug from the name.

        Args:
            name: Workspace name
            workspace_id: Workspace ID for fallback uniqueness

        Returns:
            Generated slug
        """
        # Convert to lowercase and replace non-alphanumeric with hyphens
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
        # Remove leading/trailing hyphens
        slug = slug.strip("-")
        # Limit length
        if len(slug) > 50:
            slug = slug[:50].rstrip("-")
        # If empty or too short, use ID prefix
        if len(slug) < 3:
            slug = f"workspace-{workspace_id[:8]}"

        # Check uniqueness and append ID if needed
        if self._slug_exists(slug):
            slug = f"{slug}-{workspace_id[:8]}"

        return slug

    def _slug_exists(self, slug: str) -> bool:
        """Check if a slug already exists."""
        query = "SELECT 1 FROM workspaces WHERE slug = %s LIMIT 1"
        row = self._execute_one(query, (slug,))
        return row is not None


# Singleton instance
workspace_repository = WorkspaceRepository()
