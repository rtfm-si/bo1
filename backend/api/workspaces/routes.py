"""Workspaces API routes.

Provides:
- POST /api/v1/workspaces - Create workspace
- GET /api/v1/workspaces - List user's workspaces
- GET /api/v1/workspaces/{id} - Get workspace details
- PATCH /api/v1/workspaces/{id} - Update workspace (admin+)
- DELETE /api/v1/workspaces/{id} - Delete workspace (owner only)
- GET /api/v1/workspaces/{id}/members - List members
- POST /api/v1/workspaces/{id}/members - Add member (admin+)
- PATCH /api/v1/workspaces/{id}/members/{user_id} - Update role (admin+)
- DELETE /api/v1/workspaces/{id}/members/{user_id} - Remove member (admin+)
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Path
from psycopg2.errors import UniqueViolation

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.workspace_auth import (
    WorkspaceAccessChecker,
    WorkspacePermissionChecker,
    WorkspaceRoleChecker,
)
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
    ERROR_409_RESPONSE,
    ERROR_500_RESPONSE,
)
from backend.api.workspaces.models import (
    JoinRequestCreate,
    JoinRequestListResponse,
    JoinRequestRejectRequest,
    JoinRequestResponse,
    MemberRole,
    RoleChangeResponse,
    RoleHistoryResponse,
    TransferOwnershipRequest,
    WorkspaceCreate,
    WorkspaceDiscoverability,
    WorkspaceInvite,
    WorkspaceListResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceSettingsUpdate,
    WorkspaceUpdate,
)
from backend.services.workspace_auth import (
    Permission,
    can_demote_admin,
    can_promote_member,
    can_remove_member,
    can_transfer_ownership,
)
from bo1.logging.errors import ErrorCode
from bo1.state.repositories.user_repository import user_repository
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/workspaces", tags=["workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=201,
    summary="Create new workspace",
    responses={409: ERROR_409_RESPONSE, 500: ERROR_500_RESPONSE},
)
@handle_api_errors("create workspace")
async def create_workspace(
    request: WorkspaceCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceResponse:
    """Create a new workspace.

    The creating user becomes the owner with full permissions.

    Args:
        request: Workspace creation data
        user: Current authenticated user

    Returns:
        Created workspace

    Raises:
        HTTPException: 409 if slug already exists
    """
    user_id = extract_user_id(user)
    logger.info(f"Creating workspace: name={request.name}, owner={user_id}")

    try:
        workspace = workspace_repository.create_workspace(
            name=request.name,
            owner_id=user_id,
            slug=request.slug,
        )
        logger.info(f"Created workspace {workspace.id} for user {user_id}")
        return workspace
    except UniqueViolation as e:
        raise http_error(
            ErrorCode.API_CONFLICT,
            "Workspace slug already exists",
            status=409,
        ) from e


@router.get(
    "",
    response_model=WorkspaceListResponse,
    summary="List user's workspaces",
)
async def list_workspaces(
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceListResponse:
    """List all workspaces the user is a member of.

    Args:
        user: Current authenticated user

    Returns:
        List of workspaces with default workspace indicator
    """
    user_id = extract_user_id(user)
    workspaces = workspace_repository.get_user_workspaces(user_id)
    default_workspace_id = user_repository.get_default_workspace(user_id)
    return WorkspaceListResponse(
        workspaces=workspaces,
        total=len(workspaces),
        default_workspace_id=default_workspace_id,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace details",
    dependencies=[Depends(WorkspaceAccessChecker())],
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("get workspace")
async def get_workspace(
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceResponse:
    """Get workspace details.

    Requires membership in the workspace.

    Args:
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        Workspace details
    """
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise http_error(ErrorCode.API_NOT_FOUND, "Workspace not found", status=404)
    return workspace


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
    responses={404: ERROR_404_RESPONSE, 409: ERROR_409_RESPONSE},
)
@handle_api_errors("update workspace")
async def update_workspace(
    request: WorkspaceUpdate,
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceResponse:
    """Update workspace name or slug.

    Requires admin or owner role.

    Args:
        request: Update data
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        Updated workspace

    Raises:
        HTTPException: 409 if new slug conflicts
    """
    logger.info(f"Updating workspace {workspace_id}")

    try:
        workspace = workspace_repository.update_workspace(
            workspace_id=workspace_id,
            name=request.name,
            slug=request.slug,
        )
        if not workspace:
            raise http_error(ErrorCode.API_NOT_FOUND, "Workspace not found", status=404)
        return workspace
    except UniqueViolation as e:
        raise http_error(
            ErrorCode.API_CONFLICT,
            "Workspace slug already exists",
            status=409,
        ) from e


@router.delete(
    "/{workspace_id}",
    status_code=204,
    summary="Delete workspace",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.OWNER))],
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("delete workspace")
async def delete_workspace(
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Delete a workspace.

    Only the owner can delete the workspace. All members and resources
    will be removed.

    Args:
        workspace_id: Workspace UUID
        user: Current authenticated user

    Raises:
        HTTPException: 404 if workspace not found
    """
    logger.info(f"Deleting workspace {workspace_id} by owner {user['user_id']}")

    success = workspace_repository.delete_workspace(workspace_id)
    if not success:
        raise http_error(ErrorCode.API_NOT_FOUND, "Workspace not found", status=404)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    summary="List workspace members",
    dependencies=[Depends(WorkspaceAccessChecker())],
)
async def list_members(
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[WorkspaceMemberResponse]:
    """List all members of a workspace.

    Requires membership in the workspace.

    Args:
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        List of workspace members
    """
    return workspace_repository.get_members(workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=201,
    summary="Add member to workspace",
    dependencies=[Depends(WorkspacePermissionChecker(Permission.MANAGE_MEMBERS))],
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE, 409: ERROR_409_RESPONSE},
)
@handle_api_errors("add member")
async def add_member(
    invite: WorkspaceInvite,
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    """Add a user to the workspace.

    Requires MANAGE_MEMBERS permission (admin or owner).
    Admins can only add members with role <= their own role.

    Args:
        invite: Invitation data (email and role)
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        Created membership

    Raises:
        HTTPException: 404 if user not found
        HTTPException: 409 if user already a member
        HTTPException: 403 if trying to add with higher role
    """
    actor_id = extract_user_id(user)
    logger.info(f"Adding member to workspace {workspace_id}: email={invite.email}")

    # Look up user by email
    from bo1.state.repositories.user_repository import user_repository

    target_user = user_repository.get_by_email(invite.email)
    if not target_user:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "User with this email not found",
            status=404,
        )
    target_id = target_user["id"]

    # Check not already a member
    if workspace_repository.is_member(workspace_id, target_id):
        raise http_error(
            ErrorCode.API_CONFLICT,
            "User is already a member of this workspace",
            status=409,
        )

    # Prevent admins from adding owners
    actor_role = workspace_repository.get_member_role(workspace_id, actor_id)
    if invite.role == MemberRole.OWNER and actor_role != MemberRole.OWNER:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "Only owners can add other owners",
            status=403,
        )

    member = workspace_repository.add_member(
        workspace_id=workspace_id,
        user_id=target_id,
        role=invite.role,
        invited_by=actor_id,
    )
    logger.info(f"Added member {target_id} to workspace {workspace_id}")
    return member


@router.patch(
    "/{workspace_id}/members/{target_user_id}",
    response_model=WorkspaceMemberResponse,
    summary="Update member role",
    dependencies=[Depends(WorkspacePermissionChecker(Permission.MANAGE_MEMBERS))],
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("update member role")
async def update_member_role(
    update: WorkspaceMemberUpdate,
    workspace_id: uuid.UUID = Path(...),
    target_user_id: str = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    """Update a member's role in the workspace.

    Requires MANAGE_MEMBERS permission. Cannot change own role.
    Cannot change owner's role.

    Args:
        update: New role
        workspace_id: Workspace UUID
        target_user_id: User ID to update
        user: Current authenticated user

    Returns:
        Updated membership

    Raises:
        HTTPException: 404 if member not found
        HTTPException: 403 if trying to change owner or self
    """
    actor_id = extract_user_id(user)

    # Cannot change own role
    if actor_id == target_user_id:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "Cannot change your own role",
            status=403,
        )

    # Cannot change owner's role
    workspace = workspace_repository.get_workspace(workspace_id)
    if workspace and workspace.owner_id == target_user_id:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "Cannot change owner's role. Transfer ownership instead.",
            status=403,
        )

    # Only owners can promote to owner
    if update.role == MemberRole.OWNER:
        actor_role = workspace_repository.get_member_role(workspace_id, actor_id)
        if actor_role != MemberRole.OWNER:
            raise http_error(
                ErrorCode.API_FORBIDDEN,
                "Only owners can promote to owner",
                status=403,
            )

    member = workspace_repository.update_member_role(
        workspace_id=workspace_id,
        user_id=target_user_id,
        role=update.role,
    )
    if not member:
        raise http_error(ErrorCode.API_NOT_FOUND, "Member not found", status=404)

    logger.info(
        f"Updated member {target_user_id} role to {update.role.value} in workspace {workspace_id}"
    )
    return member


@router.delete(
    "/{workspace_id}/members/{target_user_id}",
    status_code=204,
    summary="Remove member from workspace",
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("remove member")
async def remove_member(
    workspace_id: uuid.UUID = Path(...),
    target_user_id: str = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Remove a member from the workspace.

    Admins+ can remove other members. Members can only remove themselves.
    Owner cannot be removed (must transfer ownership first).

    Args:
        workspace_id: Workspace UUID
        target_user_id: User ID to remove
        user: Current authenticated user

    Raises:
        HTTPException: 404 if member not found
        HTTPException: 403 if not allowed to remove
    """
    actor_id = extract_user_id(user)

    # Check removal is allowed
    can_remove, error = can_remove_member(workspace_id, actor_id, target_user_id)
    if not can_remove:
        raise http_error(ErrorCode.API_FORBIDDEN, error or "Cannot remove member", status=403)

    success = workspace_repository.remove_member(workspace_id, target_user_id)
    if not success:
        raise http_error(ErrorCode.API_NOT_FOUND, "Member not found", status=404)

    logger.info(f"Removed member {target_user_id} from workspace {workspace_id} (by {actor_id})")


# =============================================================================
# Join Request Routes
# =============================================================================


@router.post(
    "/{workspace_id}/join-request",
    response_model=JoinRequestResponse,
    status_code=201,
    summary="Submit join request",
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE, 409: ERROR_409_RESPONSE},
)
@handle_api_errors("submit join request")
async def submit_join_request(
    request: JoinRequestCreate,
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> JoinRequestResponse:
    """Submit a request to join a workspace.

    Only works for workspaces with REQUEST_TO_JOIN discoverability.
    Users who are already members cannot submit requests.

    Args:
        request: Join request data (optional message)
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        Created join request

    Raises:
        HTTPException: 403 if workspace doesn't allow join requests
        HTTPException: 409 if user already has pending request or is member
        HTTPException: 404 if workspace not found
    """
    user_id = extract_user_id(user)
    logger.info(f"Join request for workspace {workspace_id} from user {user_id}")

    # Check workspace exists
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise http_error(ErrorCode.API_NOT_FOUND, "Workspace not found", status=404)

    # Check discoverability allows join requests
    discoverability = workspace_repository.get_discoverability(workspace_id)
    if discoverability != WorkspaceDiscoverability.REQUEST_TO_JOIN:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "This workspace does not accept join requests",
            status=403,
        )

    try:
        join_request = workspace_repository.create_join_request(
            workspace_id=workspace_id,
            user_id=user_id,
            message=request.message,
        )
        logger.info(f"Created join request {join_request.id}")

        # Send email notification to workspace admins
        _notify_admins_of_join_request(workspace_id, join_request)

        return join_request
    except ValueError as e:
        raise http_error(ErrorCode.API_CONFLICT, str(e), status=409) from e


@router.get(
    "/{workspace_id}/join-requests",
    response_model=JoinRequestListResponse,
    summary="List pending join requests",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
)
async def list_join_requests(
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> JoinRequestListResponse:
    """List all pending join requests for a workspace.

    Requires admin or owner role.

    Args:
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        List of pending join requests
    """
    requests = workspace_repository.list_pending_requests(workspace_id)
    return JoinRequestListResponse(requests=requests, total=len(requests))


@router.post(
    "/{workspace_id}/join-requests/{request_id}/approve",
    response_model=JoinRequestResponse,
    summary="Approve join request",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("approve join request")
async def approve_join_request(
    workspace_id: uuid.UUID = Path(...),
    request_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> JoinRequestResponse:
    """Approve a join request and add user as member.

    Requires admin or owner role.

    Args:
        workspace_id: Workspace UUID
        request_id: Join request UUID
        user: Current authenticated user

    Returns:
        Updated join request

    Raises:
        HTTPException: 404 if request not found or not pending
    """
    reviewer_id = extract_user_id(user)
    logger.info(f"Approving join request {request_id} by {reviewer_id}")

    # Verify request belongs to this workspace
    join_request = workspace_repository.get_join_request(request_id)
    if not join_request or join_request.workspace_id != workspace_id:
        raise http_error(ErrorCode.API_NOT_FOUND, "Join request not found", status=404)

    result = workspace_repository.approve_request(request_id, reviewer_id)
    if not result:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "Join request not found or already processed",
            status=404,
        )

    # Send approval notification
    _notify_user_of_approval(result)

    logger.info(f"Approved join request {request_id}, user {join_request.user_id} is now a member")
    return result


@router.post(
    "/{workspace_id}/join-requests/{request_id}/reject",
    response_model=JoinRequestResponse,
    summary="Reject join request",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("reject join request")
async def reject_join_request(
    request: JoinRequestRejectRequest,
    workspace_id: uuid.UUID = Path(...),
    request_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> JoinRequestResponse:
    """Reject a join request.

    Requires admin or owner role.

    Args:
        request: Rejection data (optional reason)
        workspace_id: Workspace UUID
        request_id: Join request UUID
        user: Current authenticated user

    Returns:
        Updated join request

    Raises:
        HTTPException: 404 if request not found or not pending
    """
    reviewer_id = extract_user_id(user)
    logger.info(f"Rejecting join request {request_id} by {reviewer_id}")

    # Verify request belongs to this workspace
    join_request = workspace_repository.get_join_request(request_id)
    if not join_request or join_request.workspace_id != workspace_id:
        raise http_error(ErrorCode.API_NOT_FOUND, "Join request not found", status=404)

    result = workspace_repository.reject_request(
        request_id,
        reviewer_id,
        request.reason,
    )
    if not result:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "Join request not found or already processed",
            status=404,
        )

    # Send rejection notification
    _notify_user_of_rejection(result)

    logger.info(f"Rejected join request {request_id}")
    return result


@router.patch(
    "/{workspace_id}/settings",
    response_model=WorkspaceResponse,
    summary="Update workspace settings",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
    responses={404: ERROR_404_RESPONSE},
)
@handle_api_errors("update workspace settings")
async def update_workspace_settings(
    request: WorkspaceSettingsUpdate,
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceResponse:
    """Update workspace settings including discoverability.

    Requires admin or owner role.

    Args:
        request: Settings update data
        workspace_id: Workspace UUID
        user: Current authenticated user

    Returns:
        Updated workspace

    Raises:
        HTTPException: 404 if workspace not found
    """
    logger.info(f"Updating workspace {workspace_id} settings")

    if request.discoverability:
        workspace_repository.update_discoverability(
            workspace_id,
            request.discoverability,
        )

    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise http_error(ErrorCode.API_NOT_FOUND, "Workspace not found", status=404)
    return workspace


def _notify_admins_of_join_request(
    workspace_id: uuid.UUID,
    join_request: JoinRequestResponse,
) -> None:
    """Send email notification to workspace admins about new join request."""
    try:
        from backend.services.email import send_email_async
        from backend.services.email_templates import render_join_request_email

        # Get workspace admins
        members = workspace_repository.get_members(workspace_id)
        admin_ids = [m.user_id for m in members if m.role in (MemberRole.ADMIN, MemberRole.OWNER)]

        # Get admin emails
        for admin_id in admin_ids:
            admin_user = user_repository.get_by_id(admin_id)
            if admin_user and admin_user.get("email"):
                workspace = workspace_repository.get_workspace(workspace_id)
                requester = user_repository.get_by_id(join_request.user_id)
                requester_email = requester.get("email", "Unknown") if requester else "Unknown"

                subject, html = render_join_request_email(
                    workspace_name=workspace.name if workspace else "Unknown",
                    requester_email=requester_email,
                    message=join_request.message,
                )
                send_email_async(
                    to_email=admin_user["email"],
                    subject=subject,
                    html_body=html,
                )
    except Exception as e:
        logger.warning(f"Failed to send join request notification: {e}")


def _notify_user_of_approval(join_request: JoinRequestResponse) -> None:
    """Send email notification to user that their join request was approved."""
    try:
        from backend.services.email import send_email_async
        from backend.services.email_templates import render_join_approved_email

        user = user_repository.get_by_id(join_request.user_id)
        if user and user.get("email"):
            workspace = workspace_repository.get_workspace(join_request.workspace_id)
            subject, html = render_join_approved_email(
                workspace_name=workspace.name if workspace else "Unknown",
            )
            send_email_async(
                to_email=user["email"],
                subject=subject,
                html_body=html,
            )
    except Exception as e:
        logger.warning(f"Failed to send approval notification: {e}")


def _notify_user_of_rejection(join_request: JoinRequestResponse) -> None:
    """Send email notification to user that their join request was rejected."""
    try:
        from backend.services.email import send_email_async
        from backend.services.email_templates import render_join_rejected_email

        user = user_repository.get_by_id(join_request.user_id)
        if user and user.get("email"):
            workspace = workspace_repository.get_workspace(join_request.workspace_id)
            subject, html = render_join_rejected_email(
                workspace_name=workspace.name if workspace else "Unknown",
                reason=join_request.rejection_reason,
            )
            send_email_async(
                to_email=user["email"],
                subject=subject,
                html_body=html,
            )
    except Exception as e:
        logger.warning(f"Failed to send rejection notification: {e}")


# =============================================================================
# Role Management Routes
# =============================================================================


@router.post(
    "/{workspace_id}/transfer-ownership",
    response_model=WorkspaceResponse,
    summary="Transfer workspace ownership",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.OWNER))],
    responses={
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
        500: ERROR_500_RESPONSE,
    },
)
@handle_api_errors("transfer ownership")
async def transfer_ownership(
    request: TransferOwnershipRequest,
    workspace_id: uuid.UUID = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceResponse:
    """Transfer workspace ownership to another member.

    Only the current owner can transfer ownership. The current owner
    will become an admin after the transfer.

    Args:
        request: Transfer request with new owner ID and confirmation
        workspace_id: Workspace UUID
        user: Current authenticated user (must be owner)

    Returns:
        Updated workspace

    Raises:
        HTTPException: 400 if confirmation not provided
        HTTPException: 403 if transfer not allowed
        HTTPException: 404 if workspace not found
    """
    actor_id = extract_user_id(user)
    logger.info(
        f"Ownership transfer requested: workspace={workspace_id}, "
        f"from={actor_id}, to={request.new_owner_id}"
    )

    # Require explicit confirmation
    if not request.confirm:
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            "Must confirm the transfer by setting confirm=true",
            status=400,
        )

    # Check transfer is allowed
    can_transfer, error = can_transfer_ownership(workspace_id, actor_id, request.new_owner_id)
    if not can_transfer:
        raise http_error(ErrorCode.API_FORBIDDEN, error or "Transfer not allowed", status=403)

    # Perform transfer
    success = workspace_repository.transfer_ownership(
        workspace_id=workspace_id,
        from_user_id=actor_id,
        to_user_id=request.new_owner_id,
    )
    if not success:
        raise http_error(
            ErrorCode.API_REQUEST_ERROR,
            "Failed to transfer ownership",
            status=500,
        )

    # Send email notifications
    _notify_ownership_transfer(workspace_id, actor_id, request.new_owner_id)

    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise http_error(ErrorCode.API_NOT_FOUND, "Workspace not found", status=404)

    logger.info(
        f"Ownership transferred: workspace={workspace_id}, new_owner={request.new_owner_id}"
    )
    return workspace


@router.post(
    "/{workspace_id}/members/{target_user_id}/promote",
    response_model=WorkspaceMemberResponse,
    summary="Promote member to admin",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.OWNER))],
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("promote member")
async def promote_member(
    workspace_id: uuid.UUID = Path(...),
    target_user_id: str = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    """Promote a member to admin role.

    Only the workspace owner can promote members to admin.

    Args:
        workspace_id: Workspace UUID
        target_user_id: User ID to promote
        user: Current authenticated user (must be owner)

    Returns:
        Updated member

    Raises:
        HTTPException: 403 if promotion not allowed
        HTTPException: 404 if member not found
    """
    actor_id = extract_user_id(user)
    logger.info(f"Promoting member {target_user_id} in workspace {workspace_id}")

    # Check promotion is allowed
    can_promote, error = can_promote_member(workspace_id, actor_id, target_user_id)
    if not can_promote:
        raise http_error(ErrorCode.API_FORBIDDEN, error or "Promotion not allowed", status=403)

    # Perform promotion
    result = workspace_repository.promote_to_admin(
        workspace_id=workspace_id,
        user_id=target_user_id,
        promoted_by=actor_id,
    )
    if not result:
        raise http_error(ErrorCode.API_NOT_FOUND, "Member not found", status=404)

    # Send email notification
    _notify_role_change(workspace_id, target_user_id, "member", "admin")

    logger.info(f"Promoted member {target_user_id} to admin in workspace {workspace_id}")
    return result


@router.post(
    "/{workspace_id}/members/{target_user_id}/demote",
    response_model=WorkspaceMemberResponse,
    summary="Demote admin to member",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.OWNER))],
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("demote member")
async def demote_member(
    workspace_id: uuid.UUID = Path(...),
    target_user_id: str = Path(...),
    user: dict[str, Any] = Depends(get_current_user),
) -> WorkspaceMemberResponse:
    """Demote an admin to member role.

    Only the workspace owner can demote admins.

    Args:
        workspace_id: Workspace UUID
        target_user_id: User ID to demote
        user: Current authenticated user (must be owner)

    Returns:
        Updated member

    Raises:
        HTTPException: 403 if demotion not allowed
        HTTPException: 404 if member not found
    """
    actor_id = extract_user_id(user)
    logger.info(f"Demoting admin {target_user_id} in workspace {workspace_id}")

    # Check demotion is allowed
    can_demote, error = can_demote_admin(workspace_id, actor_id, target_user_id)
    if not can_demote:
        raise http_error(ErrorCode.API_FORBIDDEN, error or "Demotion not allowed", status=403)

    # Perform demotion
    result = workspace_repository.demote_to_member(
        workspace_id=workspace_id,
        user_id=target_user_id,
        demoted_by=actor_id,
    )
    if not result:
        raise http_error(ErrorCode.API_NOT_FOUND, "Member not found", status=404)

    # Send email notification
    _notify_role_change(workspace_id, target_user_id, "admin", "member")

    logger.info(f"Demoted admin {target_user_id} to member in workspace {workspace_id}")
    return result


@router.get(
    "/{workspace_id}/role-history",
    response_model=RoleHistoryResponse,
    summary="Get role change history",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
)
async def get_role_history(
    workspace_id: uuid.UUID = Path(...),
    limit: int = 50,
    user: dict[str, Any] = Depends(get_current_user),
) -> RoleHistoryResponse:
    """Get role change history for a workspace.

    Requires admin or owner role.

    Args:
        workspace_id: Workspace UUID
        limit: Maximum number of records to return (default 50)
        user: Current authenticated user

    Returns:
        List of role changes
    """
    changes = workspace_repository.get_role_history(workspace_id, limit=limit)
    return RoleHistoryResponse(
        changes=[RoleChangeResponse(**c) for c in changes],
        total=len(changes),
    )


def _notify_ownership_transfer(
    workspace_id: uuid.UUID,
    old_owner_id: str,
    new_owner_id: str,
) -> None:
    """Send email notifications for ownership transfer."""
    try:
        from backend.services.email import send_email_async
        from backend.services.email_templates import render_ownership_transferred_email

        workspace = workspace_repository.get_workspace(workspace_id)
        workspace_name = workspace.name if workspace else "Unknown"

        # Notify old owner
        old_owner = user_repository.get_by_id(old_owner_id)
        if old_owner and old_owner.get("email"):
            subject, html = render_ownership_transferred_email(
                workspace_name=workspace_name,
                is_new_owner=False,
            )
            send_email_async(
                to_email=old_owner["email"],
                subject=subject,
                html_body=html,
            )

        # Notify new owner
        new_owner = user_repository.get_by_id(new_owner_id)
        if new_owner and new_owner.get("email"):
            subject, html = render_ownership_transferred_email(
                workspace_name=workspace_name,
                is_new_owner=True,
            )
            send_email_async(
                to_email=new_owner["email"],
                subject=subject,
                html_body=html,
            )
    except Exception as e:
        logger.warning(f"Failed to send ownership transfer notification: {e}")


def _notify_role_change(
    workspace_id: uuid.UUID,
    user_id: str,
    old_role: str,
    new_role: str,
) -> None:
    """Send email notification for role change."""
    try:
        from backend.services.email import send_email_async
        from backend.services.email_templates import render_role_changed_email

        workspace = workspace_repository.get_workspace(workspace_id)
        workspace_name = workspace.name if workspace else "Unknown"

        target_user = user_repository.get_by_id(user_id)
        if target_user and target_user.get("email"):
            subject, html = render_role_changed_email(
                workspace_name=workspace_name,
                old_role=old_role,
                new_role=new_role,
            )
            send_email_async(
                to_email=target_user["email"],
                subject=subject,
                html_body=html,
            )
    except Exception as e:
        logger.warning(f"Failed to send role change notification: {e}")


# =============================================================================
# Include invitation routes
# =============================================================================

from backend.api.workspaces.invitations import workspace_router as invitations_router  # noqa: E402

router.include_router(invitations_router, prefix="")
