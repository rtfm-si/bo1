"""Pydantic models for workspaces and team collaboration.

Provides:
- WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
- MemberRole enum
- WorkspaceMemberResponse, WorkspaceInvite
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class MemberRole(str, Enum):
    """Role within a workspace."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class WorkspaceCreate(BaseModel):
    """Request model for creating a workspace."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(
        None,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="URL-friendly identifier. Auto-generated from name if not provided.",
    )


class WorkspaceUpdate(BaseModel):
    """Request model for updating a workspace."""

    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(
        None,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
    )


class WorkspaceResponse(BaseModel):
    """Response model for a workspace."""

    id: UUID
    name: str
    slug: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    member_count: int | None = None


class WorkspaceMemberResponse(BaseModel):
    """Response model for a workspace member."""

    id: UUID
    workspace_id: UUID
    user_id: str
    role: MemberRole
    invited_by: str | None = None
    joined_at: datetime
    # Optional user details (populated from join)
    user_email: str | None = None
    user_name: str | None = None


class WorkspaceInvite(BaseModel):
    """Request model for inviting a user to a workspace."""

    email: str = Field(..., description="Email of user to invite")
    role: MemberRole = Field(
        MemberRole.MEMBER,
        description="Role to assign to the invited user",
    )


class WorkspaceMemberUpdate(BaseModel):
    """Request model for updating a member's role."""

    role: MemberRole


class WorkspaceListResponse(BaseModel):
    """Response model for listing workspaces."""

    workspaces: list[WorkspaceResponse]
    total: int
