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

from bo1.models import WorkspaceRole

# Alias for backwards compatibility in OpenAPI schema
MemberRole = WorkspaceRole


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
    default_workspace_id: UUID | None = None


# =============================================================================
# Invitation Models
# =============================================================================


class InvitationStatus(str, Enum):
    """Status of a workspace invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"
    EXPIRED = "expired"


class InvitationCreate(BaseModel):
    """Request model for creating an invitation."""

    email: str = Field(..., description="Email of user to invite")
    role: MemberRole = Field(
        MemberRole.MEMBER,
        description="Role to assign when invitation is accepted",
    )


class InvitationResponse(BaseModel):
    """Response model for an invitation."""

    id: UUID
    workspace_id: UUID
    email: str
    role: MemberRole
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    invited_by: str | None = None
    accepted_at: datetime | None = None
    # Optional: workspace name for display
    workspace_name: str | None = None
    inviter_name: str | None = None


class InvitationAcceptRequest(BaseModel):
    """Request model for accepting an invitation."""

    token: str = Field(..., description="Invitation token from email link")


class InvitationDeclineRequest(BaseModel):
    """Request model for declining an invitation."""

    token: str = Field(..., description="Invitation token from email link")


class InvitationListResponse(BaseModel):
    """Response model for listing invitations."""

    invitations: list[InvitationResponse]
    total: int


# =============================================================================
# Join Request Models
# =============================================================================


class WorkspaceDiscoverability(str, Enum):
    """Discoverability setting for a workspace."""

    PRIVATE = "private"
    INVITE_ONLY = "invite_only"
    REQUEST_TO_JOIN = "request_to_join"


class JoinRequestStatus(str, Enum):
    """Status of a workspace join request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class JoinRequestCreate(BaseModel):
    """Request model for submitting a join request."""

    message: str | None = Field(
        None,
        max_length=1000,
        description="Optional message explaining why you want to join",
    )


class JoinRequestResponse(BaseModel):
    """Response model for a join request."""

    id: UUID
    workspace_id: UUID
    user_id: str
    message: str | None = None
    status: JoinRequestStatus
    rejection_reason: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    # Optional: populated from joins
    user_email: str | None = None
    user_name: str | None = None
    workspace_name: str | None = None


class JoinRequestRejectRequest(BaseModel):
    """Request model for rejecting a join request."""

    reason: str | None = Field(
        None,
        max_length=500,
        description="Optional reason for rejection",
    )


class JoinRequestListResponse(BaseModel):
    """Response model for listing join requests."""

    requests: list[JoinRequestResponse]
    total: int


class WorkspaceSettingsUpdate(BaseModel):
    """Request model for updating workspace settings."""

    discoverability: WorkspaceDiscoverability | None = None


# =============================================================================
# Role Transfer Models
# =============================================================================


class TransferOwnershipRequest(BaseModel):
    """Request model for transferring workspace ownership."""

    new_owner_id: str = Field(
        ...,
        description="User ID of the new owner",
    )
    confirm: bool = Field(
        ...,
        description="Must be true to confirm the transfer",
    )


class RoleChangeResponse(BaseModel):
    """Response model for a role change record."""

    id: UUID
    workspace_id: UUID
    user_id: str
    user_email: str | None = None
    old_role: str
    new_role: str
    change_type: str
    changed_by: str | None = None
    changed_by_email: str | None = None
    changed_at: datetime


class RoleHistoryResponse(BaseModel):
    """Response model for role change history."""

    changes: list[RoleChangeResponse]
    total: int
