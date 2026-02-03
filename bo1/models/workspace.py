"""Workspace models for Board of One.

Provides type-safe workspace and workspace member handling with Pydantic validation.
"""

from datetime import datetime
from enum import Enum

from pydantic import ConfigDict, Field

from bo1.models.util import AuditFieldsMixin, FromDbRowMixin


class WorkspaceRole(str, Enum):
    """Workspace member roles."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Workspace(AuditFieldsMixin, FromDbRowMixin):
    """Workspace model matching PostgreSQL workspaces table.

    Workspaces group users and resources for team collaboration.
    """

    id: str = Field(..., description="Workspace UUID")
    name: str = Field(..., description="Workspace name", max_length=255)
    slug: str = Field(..., description="URL-friendly unique identifier", max_length=63)
    owner_id: str = Field(..., description="User who owns the workspace")

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


class WorkspaceMember(FromDbRowMixin):
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
