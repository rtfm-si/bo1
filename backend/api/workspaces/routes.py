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

from fastapi import APIRouter, Depends, HTTPException, Path
from psycopg2.errors import UniqueViolation

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.workspace_auth import (
    WorkspaceAccessChecker,
    WorkspacePermissionChecker,
    WorkspaceRoleChecker,
)
from backend.api.workspaces.models import (
    MemberRole,
    WorkspaceCreate,
    WorkspaceInvite,
    WorkspaceListResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from backend.services.workspace_auth import Permission, can_remove_member
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/workspaces", tags=["workspaces"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=201,
    summary="Create new workspace",
)
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
    user_id = user["user_id"]
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
        raise HTTPException(
            status_code=409,
            detail="Workspace slug already exists",
        ) from e
    except Exception as e:
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(status_code=500, detail="Failed to create workspace") from e


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
        List of workspaces
    """
    user_id = user["user_id"]
    workspaces = workspace_repository.get_user_workspaces(user_id)
    return WorkspaceListResponse(workspaces=workspaces, total=len(workspaces))


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Get workspace details",
    dependencies=[Depends(WorkspaceAccessChecker())],
)
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
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    summary="Update workspace",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.ADMIN))],
)
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
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace
    except UniqueViolation as e:
        raise HTTPException(
            status_code=409,
            detail="Workspace slug already exists",
        ) from e


@router.delete(
    "/{workspace_id}",
    status_code=204,
    summary="Delete workspace",
    dependencies=[Depends(WorkspaceRoleChecker(MemberRole.OWNER))],
)
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
        raise HTTPException(status_code=404, detail="Workspace not found")


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
)
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
    actor_id = user["user_id"]
    logger.info(f"Adding member to workspace {workspace_id}: email={invite.email}")

    # Look up user by email
    from bo1.state.repositories.user_repository import user_repository

    target_user = user_repository.get_by_email(invite.email)
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User with this email not found",
        )
    target_id = target_user["id"]

    # Check not already a member
    if workspace_repository.is_member(workspace_id, target_id):
        raise HTTPException(
            status_code=409,
            detail="User is already a member of this workspace",
        )

    # Prevent admins from adding owners
    actor_role = workspace_repository.get_member_role(workspace_id, actor_id)
    if invite.role == MemberRole.OWNER and actor_role != MemberRole.OWNER:
        raise HTTPException(
            status_code=403,
            detail="Only owners can add other owners",
        )

    try:
        member = workspace_repository.add_member(
            workspace_id=workspace_id,
            user_id=target_id,
            role=invite.role,
            invited_by=actor_id,
        )
        logger.info(f"Added member {target_id} to workspace {workspace_id}")
        return member
    except Exception as e:
        logger.error(f"Failed to add member: {e}")
        raise HTTPException(status_code=500, detail="Failed to add member") from e


@router.patch(
    "/{workspace_id}/members/{target_user_id}",
    response_model=WorkspaceMemberResponse,
    summary="Update member role",
    dependencies=[Depends(WorkspacePermissionChecker(Permission.MANAGE_MEMBERS))],
)
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
    actor_id = user["user_id"]

    # Cannot change own role
    if actor_id == target_user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot change your own role",
        )

    # Cannot change owner's role
    workspace = workspace_repository.get_workspace(workspace_id)
    if workspace and workspace.owner_id == target_user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot change owner's role. Transfer ownership instead.",
        )

    # Only owners can promote to owner
    if update.role == MemberRole.OWNER:
        actor_role = workspace_repository.get_member_role(workspace_id, actor_id)
        if actor_role != MemberRole.OWNER:
            raise HTTPException(
                status_code=403,
                detail="Only owners can promote to owner",
            )

    member = workspace_repository.update_member_role(
        workspace_id=workspace_id,
        user_id=target_user_id,
        role=update.role,
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    logger.info(
        f"Updated member {target_user_id} role to {update.role.value} in workspace {workspace_id}"
    )
    return member


@router.delete(
    "/{workspace_id}/members/{target_user_id}",
    status_code=204,
    summary="Remove member from workspace",
)
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
    actor_id = user["user_id"]

    # Check removal is allowed
    can_remove, error = can_remove_member(workspace_id, actor_id, target_user_id)
    if not can_remove:
        raise HTTPException(status_code=403, detail=error)

    success = workspace_repository.remove_member(workspace_id, target_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")

    logger.info(f"Removed member {target_user_id} from workspace {workspace_id} (by {actor_id})")


# =============================================================================
# Include invitation routes
# =============================================================================

from backend.api.workspaces.invitations import workspace_router as invitations_router  # noqa: E402

router.include_router(invitations_router, prefix="")
