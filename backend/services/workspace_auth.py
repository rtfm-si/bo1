"""Workspace authorization service.

Provides role-based permission checks for workspace access control.

Role Hierarchy: OWNER > ADMIN > MEMBER
- OWNER: Full control (delete, transfer ownership)
- ADMIN: Manage members, edit workspace settings
- MEMBER: View and use workspace resources

Permissions:
- VIEW: Read workspace and its resources
- EDIT: Create/modify resources within workspace
- MANAGE_MEMBERS: Add/remove/update member roles
- DELETE: Delete workspace (owner only)
"""

import logging
import uuid
from enum import Enum

from backend.api.workspaces.models import MemberRole
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Workspace permissions."""

    VIEW = "view"
    EDIT = "edit"
    MANAGE_MEMBERS = "manage_members"
    DELETE = "delete"


# Role-to-permissions mapping (higher roles inherit lower permissions)
ROLE_PERMISSIONS: dict[MemberRole, set[Permission]] = {
    MemberRole.MEMBER: {Permission.VIEW, Permission.EDIT},
    MemberRole.ADMIN: {Permission.VIEW, Permission.EDIT, Permission.MANAGE_MEMBERS},
    MemberRole.OWNER: {
        Permission.VIEW,
        Permission.EDIT,
        Permission.MANAGE_MEMBERS,
        Permission.DELETE,
    },
}


def check_permission(
    workspace_id: uuid.UUID,
    user_id: str,
    permission: Permission,
) -> bool:
    """Check if user has a specific permission in a workspace.

    Args:
        workspace_id: Workspace UUID
        user_id: User ID
        permission: Permission to check

    Returns:
        True if user has the permission, False otherwise
    """
    role = workspace_repository.get_member_role(workspace_id, user_id)
    if role is None:
        logger.debug(f"User {user_id} is not a member of workspace {workspace_id}")
        return False

    permissions = ROLE_PERMISSIONS.get(role, set())
    has_permission = permission in permissions
    logger.debug(
        f"Permission check: user={user_id}, workspace={workspace_id}, "
        f"role={role.value}, permission={permission.value}, result={has_permission}"
    )
    return has_permission


def check_role(
    workspace_id: uuid.UUID,
    user_id: str,
    min_role: MemberRole,
) -> bool:
    """Check if user has at least the specified role in a workspace.

    Role hierarchy: OWNER > ADMIN > MEMBER

    Args:
        workspace_id: Workspace UUID
        user_id: User ID
        min_role: Minimum role required

    Returns:
        True if user has at least the specified role
    """
    role = workspace_repository.get_member_role(workspace_id, user_id)
    if role is None:
        return False

    # Role hierarchy check
    role_order = {MemberRole.MEMBER: 0, MemberRole.ADMIN: 1, MemberRole.OWNER: 2}
    return role_order.get(role, -1) >= role_order.get(min_role, 999)


def is_member(workspace_id: uuid.UUID, user_id: str) -> bool:
    """Check if user is a member of the workspace.

    Args:
        workspace_id: Workspace UUID
        user_id: User ID

    Returns:
        True if user is a member
    """
    return workspace_repository.is_member(workspace_id, user_id)


def get_accessible_workspaces(user_id: str) -> list[uuid.UUID]:
    """Get list of workspace IDs the user can access.

    Args:
        user_id: User ID

    Returns:
        List of workspace UUIDs the user is a member of
    """
    workspaces = workspace_repository.get_user_workspaces(user_id)
    return [ws.id for ws in workspaces]


def can_transfer_ownership(
    workspace_id: uuid.UUID,
    current_user_id: str,
    new_owner_id: str,
) -> tuple[bool, str | None]:
    """Check if ownership transfer is allowed.

    Only current owner can transfer ownership, and new owner must be a member.

    Args:
        workspace_id: Workspace UUID
        current_user_id: Current user attempting transfer
        new_owner_id: Target user for ownership

    Returns:
        Tuple of (allowed, error_message)
    """
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        return False, "Workspace not found"

    if workspace.owner_id != current_user_id:
        return False, "Only the owner can transfer ownership"

    if not is_member(workspace_id, new_owner_id):
        return False, "New owner must be a workspace member"

    if current_user_id == new_owner_id:
        return False, "Cannot transfer ownership to yourself"

    return True, None


def can_remove_member(
    workspace_id: uuid.UUID,
    actor_id: str,
    target_id: str,
) -> tuple[bool, str | None]:
    """Check if member removal is allowed.

    Admins+ can remove members. Cannot remove owner.
    Members can only remove themselves (leave).

    Args:
        workspace_id: Workspace UUID
        actor_id: User performing the action
        target_id: User being removed

    Returns:
        Tuple of (allowed, error_message)
    """
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        return False, "Workspace not found"

    # Owner cannot be removed (must transfer ownership first)
    if target_id == workspace.owner_id:
        return False, "Cannot remove workspace owner. Transfer ownership first."

    # User removing themselves (leaving)
    if actor_id == target_id:
        return True, None

    # Check actor has manage_members permission
    if not check_permission(workspace_id, actor_id, Permission.MANAGE_MEMBERS):
        return False, "Insufficient permissions to remove members"

    return True, None


def can_promote_member(
    workspace_id: uuid.UUID,
    actor_id: str,
    target_id: str,
) -> tuple[bool, str | None]:
    """Check if promotion to admin is allowed.

    Only owner can promote members to admin.

    Args:
        workspace_id: Workspace UUID
        actor_id: User performing the action
        target_id: User being promoted

    Returns:
        Tuple of (allowed, error_message)
    """
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        return False, "Workspace not found"

    # Only owner can promote
    if workspace.owner_id != actor_id:
        return False, "Only the owner can promote members to admin"

    # Cannot promote self
    if actor_id == target_id:
        return False, "Cannot promote yourself"

    # Check target is a member
    target_role = workspace_repository.get_member_role(workspace_id, target_id)
    if not target_role:
        return False, "User is not a member of this workspace"

    # Can only promote members, not admins or owner
    if target_role != MemberRole.MEMBER:
        return False, f"User is already {target_role.value}, cannot promote"

    return True, None


def can_demote_admin(
    workspace_id: uuid.UUID,
    actor_id: str,
    target_id: str,
) -> tuple[bool, str | None]:
    """Check if demotion from admin is allowed.

    Only owner can demote admins. Cannot demote self or owner.

    Args:
        workspace_id: Workspace UUID
        actor_id: User performing the action
        target_id: User being demoted

    Returns:
        Tuple of (allowed, error_message)
    """
    workspace = workspace_repository.get_workspace(workspace_id)
    if not workspace:
        return False, "Workspace not found"

    # Only owner can demote
    if workspace.owner_id != actor_id:
        return False, "Only the owner can demote admins"

    # Cannot demote owner (which is self since only owner can demote)
    if target_id == workspace.owner_id:
        return False, "Cannot demote the workspace owner"

    # Check target is an admin
    target_role = workspace_repository.get_member_role(workspace_id, target_id)
    if not target_role:
        return False, "User is not a member of this workspace"

    if target_role != MemberRole.ADMIN:
        return False, f"User is {target_role.value}, not admin"

    return True, None
