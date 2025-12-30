"""Workspace invitation API routes.

Provides:
- POST /api/v1/workspaces/{id}/invitations - Send invitation (admin+)
- GET /api/v1/workspaces/{id}/invitations - List pending invitations
- DELETE /api/v1/workspaces/{id}/invitations/{invite_id} - Revoke invitation
- POST /api/v1/invitations/accept - Accept invitation
- POST /api/v1/invitations/decline - Decline invitation
- GET /api/v1/invitations/pending - Get current user's pending invitations
- GET /api/v1/invitations/{token} - Get invitation details by token (public)
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Path

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.workspace_auth import (
    WorkspaceAccessChecker,
    WorkspacePermissionChecker,
)
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
    ERROR_409_RESPONSE,
    ERROR_410_RESPONSE,
)
from backend.api.workspaces.models import (
    InvitationAcceptRequest,
    InvitationCreate,
    InvitationDeclineRequest,
    InvitationListResponse,
    InvitationResponse,
    MemberRole,
)
from backend.services import invitation_service
from backend.services.invitation_service import (
    AlreadyMemberError,
    DuplicateInvitationError,
    InvitationError,
    InvitationExpiredError,
    InvitationInvalidError,
    InvitationNotFoundError,
)
from backend.services.workspace_auth import Permission
from bo1.logging.errors import ErrorCode

logger = logging.getLogger(__name__)

# Router for workspace-scoped invitation endpoints
workspace_router = APIRouter(tags=["invitations"])

# Router for user-scoped invitation endpoints (not under /workspaces/{id})
user_router = APIRouter(prefix="/v1/invitations", tags=["invitations"])


@workspace_router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationResponse,
    status_code=201,
    summary="Send workspace invitation",
    dependencies=[Depends(WorkspacePermissionChecker(Permission.MANAGE_MEMBERS))],
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 409: ERROR_409_RESPONSE},
)
@handle_api_errors("send invitation")
async def send_invitation(
    request: InvitationCreate,
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> InvitationResponse:
    """Send an invitation to join the workspace.

    Requires MANAGE_MEMBERS permission (admin or owner).
    Admins can only invite members, not other admins or owners.

    Args:
        request: Invitation details (email, role)
        workspace_id: Target workspace UUID
        user: Current authenticated user

    Returns:
        Created invitation

    Raises:
        HTTPException: 400 if validation fails
        HTTPException: 403 if trying to invite with higher role
        HTTPException: 409 if duplicate invitation or already a member
    """
    actor_id = user["user_id"]
    logger.info(f"Sending invitation to {request.email} for workspace {workspace_id}")

    # Prevent admins from inviting owners
    if request.role == MemberRole.OWNER:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "Cannot invite users as owners",
            status=403,
        )

    # Admins can only invite members, not other admins
    from bo1.state.repositories.workspace_repository import workspace_repository

    actor_role = workspace_repository.get_member_role(workspace_id, actor_id)
    if actor_role == MemberRole.ADMIN and request.role not in [MemberRole.MEMBER]:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "Admins can only invite members",
            status=403,
        )

    try:
        invitation = invitation_service.send_invitation(
            workspace_id=workspace_id,
            email=request.email,
            role=request.role,
            invited_by=actor_id,
        )
        return invitation
    except AlreadyMemberError as e:
        raise http_error(ErrorCode.API_CONFLICT, str(e), status=409) from e
    except DuplicateInvitationError as e:
        raise http_error(ErrorCode.API_CONFLICT, str(e), status=409) from e
    except InvitationError as e:
        raise http_error(ErrorCode.API_BAD_REQUEST, str(e), status=400) from e


@workspace_router.get(
    "/{workspace_id}/invitations",
    response_model=InvitationListResponse,
    summary="List workspace invitations",
    dependencies=[Depends(WorkspaceAccessChecker())],
)
async def list_invitations(
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> InvitationListResponse:
    """List pending invitations for a workspace.

    Requires membership in the workspace.

    Args:
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        List of pending invitations
    """
    invitations = invitation_service.list_pending_invitations(workspace_id)
    return InvitationListResponse(invitations=invitations, total=len(invitations))


@workspace_router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=204,
    summary="Revoke invitation",
    dependencies=[Depends(WorkspacePermissionChecker(Permission.MANAGE_MEMBERS))],
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("revoke invitation")
async def revoke_invitation(
    workspace_id: uuid.UUID = Path(...),
    invitation_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Revoke a pending invitation.

    Requires MANAGE_MEMBERS permission (admin or owner).

    Args:
        workspace_id: Workspace UUID
        invitation_id: Invitation UUID to revoke
        user: Current authenticated user

    Raises:
        HTTPException: 404 if invitation not found
    """
    success = invitation_service.revoke_invitation(
        invitation_id=invitation_id,
        workspace_id=workspace_id,
        actor_id=user["user_id"],
    )
    if not success:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "Invitation not found or already processed",
            status=404,
        )


# =============================================================================
# User-scoped invitation endpoints (not under /workspaces/{id})
# =============================================================================


@user_router.get(
    "/pending",
    response_model=InvitationListResponse,
    summary="Get pending invitations for current user",
)
async def get_pending_invitations(
    user: dict[str, Any] = Depends(get_current_user),
) -> InvitationListResponse:
    """Get all pending invitations for the current user.

    Returns invitations sent to the user's email address that are still valid.

    Args:
        user: Current authenticated user

    Returns:
        List of pending invitations
    """
    email = user.get("email")
    if not email:
        return InvitationListResponse(invitations=[], total=0)

    invitations = invitation_service.get_user_pending_invitations(email)
    return InvitationListResponse(invitations=invitations, total=len(invitations))


@user_router.get(
    "/{token}",
    response_model=InvitationResponse,
    summary="Get invitation by token",
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("get invitation")
async def get_invitation(
    token: str = Path(..., description="Invitation token"),
) -> InvitationResponse:
    """Get invitation details by token.

    This endpoint is public (no auth required) to allow viewing
    invitation details before login/signup.

    Args:
        token: Invitation token from email

    Returns:
        Invitation details

    Raises:
        HTTPException: 404 if invitation not found
    """
    invitation = invitation_service.get_invitation_by_token(token)
    if not invitation:
        raise http_error(ErrorCode.API_NOT_FOUND, "Invitation not found", status=404)
    return invitation


@user_router.post(
    "/accept",
    response_model=InvitationResponse,
    summary="Accept invitation",
    responses={400: ERROR_400_RESPONSE, 404: ERROR_404_RESPONSE, 410: ERROR_410_RESPONSE},
)
@handle_api_errors("accept invitation")
async def accept_invitation(
    request: InvitationAcceptRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> InvitationResponse:
    """Accept a workspace invitation.

    The authenticated user's email must match the invitation email.

    Args:
        request: Acceptance request with token
        user: Current authenticated user

    Returns:
        Accepted invitation

    Raises:
        HTTPException: 400 if email mismatch or invalid state
        HTTPException: 404 if invitation not found
        HTTPException: 410 if invitation expired
    """
    user_id = user["user_id"]
    user_email = user.get("email", "")

    try:
        invitation = invitation_service.accept_invitation(
            token=request.token,
            user_id=user_id,
            user_email=user_email,
        )
        return invitation
    except InvitationNotFoundError as e:
        raise http_error(ErrorCode.API_NOT_FOUND, str(e), status=404) from e
    except InvitationExpiredError as e:
        raise http_error(ErrorCode.API_GONE, str(e), status=410) from e
    except InvitationInvalidError as e:
        raise http_error(ErrorCode.API_BAD_REQUEST, str(e), status=400) from e


@user_router.post(
    "/decline",
    status_code=204,
    summary="Decline invitation",
    responses={400: ERROR_400_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("decline invitation")
async def decline_invitation(
    request: InvitationDeclineRequest,
) -> None:
    """Decline a workspace invitation.

    This endpoint doesn't require authentication - anyone with the token
    can decline (useful for declining without creating an account).

    Args:
        request: Decline request with token

    Raises:
        HTTPException: 404 if invitation not found
        HTTPException: 400 if invitation not in valid state
    """
    try:
        invitation_service.decline_invitation(request.token)
    except InvitationNotFoundError as e:
        raise http_error(ErrorCode.API_NOT_FOUND, str(e), status=404) from e
    except InvitationInvalidError as e:
        raise http_error(ErrorCode.API_BAD_REQUEST, str(e), status=400) from e
