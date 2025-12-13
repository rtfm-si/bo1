"""Invitation service for workspace invitations.

Provides:
- send_invitation(): Create and email invitation
- accept_invitation(): Accept and add user to workspace
- decline_invitation(): Decline invitation
"""

import logging
import uuid
from datetime import UTC, datetime

from backend.api.workspaces.models import InvitationResponse, MemberRole
from backend.services.email import send_email
from backend.services.email_templates import render_workspace_invitation_email
from backend.services.invitation_repository import invitation_repository
from bo1.config import get_settings
from bo1.state.repositories.user_repository import user_repository
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)


class InvitationError(Exception):
    """Base exception for invitation errors."""

    pass


class DuplicateInvitationError(InvitationError):
    """Raised when a pending invitation already exists."""

    pass


class AlreadyMemberError(InvitationError):
    """Raised when the invitee is already a member."""

    pass


class InvitationNotFoundError(InvitationError):
    """Raised when invitation not found."""

    pass


class InvitationExpiredError(InvitationError):
    """Raised when invitation has expired."""

    pass


class InvitationInvalidError(InvitationError):
    """Raised when invitation is in invalid state."""

    pass


def send_invitation(
    workspace_id: uuid.UUID,
    email: str,
    role: MemberRole,
    invited_by: str,
) -> InvitationResponse:
    """Create and send a workspace invitation.

    Args:
        workspace_id: Target workspace UUID
        email: Email address to invite
        role: Role to assign on acceptance
        invited_by: User ID of the inviter

    Returns:
        Created invitation

    Raises:
        AlreadyMemberError: If user is already a workspace member
        DuplicateInvitationError: If pending invitation exists
        InvitationError: If email fails to send (invitation still created)
    """
    email = email.lower().strip()

    # Check if workspace exists and get name
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise InvitationError("Workspace not found")

    # Check if user with this email is already a member
    existing_user = user_repository.get_by_email(email)
    if existing_user and workspace_repository.is_member(workspace_id, existing_user["id"]):
        raise AlreadyMemberError("User is already a member of this workspace")

    # Check for existing pending invitation
    if invitation_repository.has_pending_invitation(workspace_id, email):
        raise DuplicateInvitationError("A pending invitation already exists for this email")

    # Create invitation
    invitation = invitation_repository.create_invitation(
        workspace_id=workspace_id,
        email=email,
        role=role,
        invited_by=invited_by,
    )

    # Get token for email link
    token = invitation_repository.get_invitation_token(invitation.id)

    # Get inviter name
    inviter = user_repository.get_by_id(invited_by)
    inviter_name = inviter.get("email", "A team member") if inviter else "A team member"

    # Build accept URL
    settings = get_settings()
    base_url = settings.frontend_url.rstrip("/")
    accept_url = f"{base_url}/invite/{token}"

    # Send email
    try:
        html, text = render_workspace_invitation_email(
            workspace_name=workspace.name,
            inviter_name=inviter_name,
            role=role.value,
            accept_url=accept_url,
            expires_at=invitation.expires_at,
        )
        send_email(
            to=email,
            subject=f"You've been invited to join {workspace.name}",
            html=html,
            text=text,
            tags=[{"name": "category", "value": "invitation"}],
        )
        logger.info(f"Sent workspace invitation to {email} for workspace {workspace_id}")
    except Exception as e:
        # Log but don't fail - invitation was created
        logger.error(f"Failed to send invitation email to {email}: {e}")

    return invitation


def accept_invitation(token: str, user_id: str, user_email: str) -> InvitationResponse:
    """Accept a workspace invitation and add user to workspace.

    Args:
        token: Invitation token
        user_id: User ID accepting the invitation
        user_email: Email of the accepting user (must match invitation)

    Returns:
        Accepted invitation

    Raises:
        InvitationNotFoundError: If invitation not found
        InvitationExpiredError: If invitation has expired
        InvitationInvalidError: If invitation not in pending state or email mismatch
    """
    # Get invitation
    invitation = invitation_repository.get_invitation_by_token(token)
    if not invitation:
        raise InvitationNotFoundError("Invitation not found")

    # Check email matches
    if invitation.email.lower() != user_email.lower():
        raise InvitationInvalidError("This invitation was sent to a different email")

    # Check status
    if invitation.status.value != "pending":
        raise InvitationInvalidError(
            f"Invitation is no longer valid (status: {invitation.status.value})"
        )

    # Check expiry
    if invitation.expires_at < datetime.now(UTC):
        raise InvitationExpiredError("Invitation has expired")

    # Check not already a member
    if workspace_repository.is_member(invitation.workspace_id, user_id):
        raise InvitationInvalidError("You are already a member of this workspace")

    # Add user to workspace
    workspace_repository.add_member(
        workspace_id=invitation.workspace_id,
        user_id=user_id,
        role=invitation.role,
        invited_by=invitation.invited_by,
    )

    # Mark invitation as accepted
    invitation_repository.accept_invitation(token, user_id)

    logger.info(f"User {user_id} accepted invitation to workspace {invitation.workspace_id}")

    # Return updated invitation
    return invitation_repository.get_invitation_by_token(token)


def decline_invitation(token: str) -> bool:
    """Decline a workspace invitation.

    Args:
        token: Invitation token

    Returns:
        True if declined successfully

    Raises:
        InvitationNotFoundError: If invitation not found
        InvitationInvalidError: If invitation not in pending state
    """
    # Get invitation to check status
    invitation = invitation_repository.get_invitation_by_token(token)
    if not invitation:
        raise InvitationNotFoundError("Invitation not found")

    if invitation.status.value != "pending":
        raise InvitationInvalidError("Invitation is no longer valid")

    success = invitation_repository.decline_invitation(token)
    if success:
        logger.info(f"Invitation {invitation.id} declined")

    return success


def revoke_invitation(invitation_id: uuid.UUID, workspace_id: uuid.UUID, actor_id: str) -> bool:
    """Revoke a pending invitation.

    Args:
        invitation_id: Invitation UUID
        workspace_id: Workspace UUID
        actor_id: User ID revoking (for logging)

    Returns:
        True if revoked successfully
    """
    success = invitation_repository.revoke_invitation(invitation_id, workspace_id)
    if success:
        logger.info(f"Invitation {invitation_id} revoked by {actor_id} in workspace {workspace_id}")
    return success


def list_pending_invitations(workspace_id: uuid.UUID) -> list[InvitationResponse]:
    """List pending invitations for a workspace.

    Args:
        workspace_id: Workspace UUID

    Returns:
        List of pending invitations
    """
    return invitation_repository.list_pending_invitations(workspace_id)


def get_user_pending_invitations(email: str) -> list[InvitationResponse]:
    """Get pending invitations for a user by email.

    Args:
        email: User's email address

    Returns:
        List of pending invitations
    """
    return invitation_repository.get_user_pending_invitations(email)


def get_invitation_by_token(token: str) -> InvitationResponse | None:
    """Get invitation details by token.

    Args:
        token: Invitation token

    Returns:
        Invitation or None
    """
    return invitation_repository.get_invitation_by_token(token)
