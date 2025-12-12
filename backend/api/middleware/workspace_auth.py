"""Workspace authorization middleware and dependencies.

Provides FastAPI dependencies for workspace access control:
- require_workspace_access: Verify user is a member of workspace
- require_workspace_role: Verify user has minimum role in workspace
- get_workspace_context: Extract and validate workspace from path/header
"""

import logging
import uuid
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Path

from backend.api.middleware.auth import get_current_user

# Import MemberRole at module level to avoid circular imports
# This is safe because models.py has no imports from this module
from backend.api.workspaces.models import MemberRole
from backend.services.workspace_auth import (
    Permission,
    check_permission,
    check_role,
    is_member,
)
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)


async def get_workspace_context(
    workspace_id: Annotated[uuid.UUID | None, Path()] = None,
    x_workspace_id: Annotated[str | None, Header()] = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> uuid.UUID | None:
    """Extract workspace ID from path parameter or header.

    Workspace can be specified via:
    1. Path parameter (e.g., /workspaces/{workspace_id}/...)
    2. X-Workspace-ID header (for cross-cutting endpoints)

    Args:
        workspace_id: Workspace ID from path parameter
        x_workspace_id: Workspace ID from header
        user: Current authenticated user

    Returns:
        Workspace UUID or None if no workspace context
    """
    # Path parameter takes precedence
    if workspace_id:
        return workspace_id

    # Try header
    if x_workspace_id:
        try:
            return uuid.UUID(x_workspace_id)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid X-Workspace-ID header format",
            ) from e

    return None


def require_workspace_access(
    workspace_id: uuid.UUID,
    user_id: str,
) -> None:
    """Verify user has access to workspace.

    Args:
        workspace_id: Workspace UUID
        user_id: User ID

    Raises:
        HTTPException: 403 if user is not a member
        HTTPException: 404 if workspace doesn't exist
    """
    # Check workspace exists
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check membership
    if not is_member(workspace_id, user_id):
        logger.warning(f"Access denied: user {user_id} is not a member of workspace {workspace_id}")
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this workspace",
        )


def require_workspace_role(
    workspace_id: uuid.UUID,
    user_id: str,
    min_role: MemberRole,
) -> None:
    """Verify user has at least the specified role in workspace.

    Args:
        workspace_id: Workspace UUID
        user_id: User ID
        min_role: Minimum required role

    Raises:
        HTTPException: 403 if user doesn't have sufficient role
        HTTPException: 404 if workspace doesn't exist
    """
    # Check workspace exists
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check role
    if not check_role(workspace_id, user_id, min_role):
        logger.warning(
            f"Insufficient role: user {user_id} needs {min_role.value} in workspace {workspace_id}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"This action requires {min_role.value} role or higher",
        )


def require_workspace_permission(
    workspace_id: uuid.UUID,
    user_id: str,
    permission: Permission,
) -> None:
    """Verify user has a specific permission in workspace.

    Args:
        workspace_id: Workspace UUID
        user_id: User ID
        permission: Required permission

    Raises:
        HTTPException: 403 if user doesn't have permission
        HTTPException: 404 if workspace doesn't exist
    """
    # Check workspace exists
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check permission
    if not check_permission(workspace_id, user_id, permission):
        logger.warning(
            f"Permission denied: user {user_id} lacks {permission.value} "
            f"in workspace {workspace_id}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"You do not have permission to {permission.value}",
        )


class WorkspaceAccessChecker:
    """Dependency class for workspace access checks.

    Usage:
        @router.get("/workspaces/{workspace_id}/resource")
        async def get_resource(
            workspace_id: uuid.UUID,
            user: dict = Depends(get_current_user),
            _: None = Depends(WorkspaceAccessChecker()),
        ):
            ...
    """

    def __call__(
        self,
        workspace_id: Annotated[uuid.UUID, Path()],
        user: dict[str, Any] = Depends(get_current_user),
    ) -> None:
        """Check user has access to workspace."""
        require_workspace_access(workspace_id, user["user_id"])


class WorkspaceRoleChecker:
    """Dependency class for role-based workspace access.

    Usage:
        @router.delete("/workspaces/{workspace_id}")
        async def delete_workspace(
            workspace_id: uuid.UUID,
            user: dict = Depends(get_current_user),
            _: None = Depends(WorkspaceRoleChecker(MemberRole.OWNER)),
        ):
            ...
    """

    def __init__(self, min_role: MemberRole) -> None:
        """Initialize with minimum required role.

        Args:
            min_role: Minimum role required for access
        """
        self.min_role = min_role

    def __call__(
        self,
        workspace_id: Annotated[uuid.UUID, Path()],
        user: dict[str, Any] = Depends(get_current_user),
    ) -> None:
        """Check user has required role in workspace."""
        require_workspace_role(workspace_id, user["user_id"], self.min_role)


class WorkspacePermissionChecker:
    """Dependency class for permission-based workspace access.

    Usage:
        @router.post("/workspaces/{workspace_id}/members")
        async def add_member(
            workspace_id: uuid.UUID,
            user: dict = Depends(get_current_user),
            _: None = Depends(WorkspacePermissionChecker(Permission.MANAGE_MEMBERS)),
        ):
            ...
    """

    def __init__(self, permission: Permission) -> None:
        """Initialize with required permission.

        Args:
            permission: Permission required for access
        """
        self.permission = permission

    def __call__(
        self,
        workspace_id: Annotated[uuid.UUID, Path()],
        user: dict[str, Any] = Depends(get_current_user),
    ) -> None:
        """Check user has required permission in workspace."""
        require_workspace_permission(workspace_id, user["user_id"], self.permission)
