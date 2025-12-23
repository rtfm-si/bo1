"""Workspace models for Board of One.

Provides type-safe workspace and workspace member handling with Pydantic validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceRole(str, Enum):
    """Workspace member roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Workspace(BaseModel):
    """Workspace model matching PostgreSQL workspaces table.

    Workspaces group users and resources for team collaboration.
    """

    id: str = Field(..., description="Workspace UUID")
    name: str = Field(..., description="Workspace name", max_length=255)
    slug: str = Field(..., description="URL-friendly unique identifier", max_length=63)
    owner_id: str = Field(..., description="User who owns the workspace")
    created_at: datetime = Field(..., description="Workspace creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Acme Corp",
                    "slug": "acme-corp",
                    "owner_id": "user_456",
                }
            ]
        },
    )

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "Workspace":
        """Create Workspace from database row dict.

        Args:
            row: Dict from psycopg2 cursor with workspace columns

        Returns:
            Workspace instance with validated data

        Example:
            >>> row = {"id": "uuid", "name": "Acme Corp", "slug": "acme-corp", ...}
            >>> workspace = Workspace.from_db_row(row)
        """
        # Handle UUID field (psycopg2 may return UUID object or string)
        id_val = row["id"]
        if hasattr(id_val, "hex"):
            id_val = str(id_val)

        return cls(
            id=id_val,
            name=row["name"],
            slug=row["slug"],
            owner_id=row["owner_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class WorkspaceMember(BaseModel):
    """Workspace member model matching PostgreSQL workspace_members table.

    Represents a user's membership in a workspace with their role.
    """

    id: str = Field(..., description="Membership UUID")
    workspace_id: str = Field(..., description="Workspace this membership belongs to")
    user_id: str = Field(..., description="User who is a member")
    role: WorkspaceRole = Field(..., description="Member's role: owner, admin, member")
    invited_by: str | None = Field(None, description="User who invited this member")
    joined_at: datetime = Field(..., description="When the user joined the workspace")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "workspace_id": "456e7890-e89b-12d3-a456-426614174000",
                    "user_id": "user_123",
                    "role": "member",
                    "joined_at": "2025-01-01T00:00:00Z",
                }
            ]
        },
    )

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "WorkspaceMember":
        """Create WorkspaceMember from database row dict.

        Args:
            row: Dict from psycopg2 cursor with workspace_members columns

        Returns:
            WorkspaceMember instance with validated data

        Example:
            >>> row = {"id": "uuid", "workspace_id": "ws_uuid", "user_id": "u1", ...}
            >>> member = WorkspaceMember.from_db_row(row)
        """
        # Handle role as string or enum
        role = row["role"]
        if isinstance(role, str):
            role = WorkspaceRole(role)

        # Handle UUID fields (psycopg2 may return UUID object or string)
        id_val = row["id"]
        if hasattr(id_val, "hex"):
            id_val = str(id_val)

        workspace_id = row["workspace_id"]
        if hasattr(workspace_id, "hex"):
            workspace_id = str(workspace_id)

        return cls(
            id=id_val,
            workspace_id=workspace_id,
            user_id=row["user_id"],
            role=role,
            invited_by=row.get("invited_by"),
            joined_at=row["joined_at"],
        )
