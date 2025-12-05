"""Admin API endpoints for user management.

Provides:
- GET /api/admin/stats - Get admin dashboard statistics
- GET /api/admin/users - List all users with metrics
- GET /api/admin/users/{user_id} - Get single user detail
- PATCH /api/admin/users/{user_id} - Update user (subscription_tier, is_admin)
- POST /api/admin/users/{user_id}/lock - Lock user account
- POST /api/admin/users/{user_id}/unlock - Unlock user account
- DELETE /api/admin/users/{user_id} - Delete user account
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.admin.helpers import (
    USER_WITH_METRICS_GROUP_BY,
    USER_WITH_METRICS_SELECT,
    AdminQueryService,
    AdminUserService,
    AdminValidationService,
    _row_to_user_info,
)
from backend.api.admin.models import (
    AdminStatsResponse,
    DeleteUserRequest,
    DeleteUserResponse,
    LockUserRequest,
    LockUserResponse,
    UpdateUserRequest,
    UserInfo,
    UserListResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Users"])


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get admin dashboard statistics",
    description="Get aggregated statistics for the admin dashboard.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get admin stats")
async def get_admin_stats(
    _admin: str = Depends(require_admin_any),
) -> AdminStatsResponse:
    """Get aggregated statistics for the admin dashboard."""
    stats = AdminQueryService.get_stats()
    logger.info(
        f"Admin: Retrieved stats - users: {stats.total_users}, meetings: {stats.total_meetings}, "
        f"cost: ${stats.total_cost:.2f}, whitelist: {stats.whitelist_count}, waitlist: {stats.waitlist_pending}"
    )
    return stats


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    description="List all users with metrics (total meetings, costs, last activity).",
    responses={
        200: {"description": "Users retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("list users")
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Users per page (1-100)"),
    email: str | None = Query(None, description="Search by email (partial match)"),
    _admin: str = Depends(require_admin_any),
) -> UserListResponse:
    """List all users with metrics."""
    total_count, users = AdminQueryService.list_users(page, per_page, email)
    logger.info(
        f"Admin: Listed {len(users)} users (page {page}, per_page {per_page}, total {total_count})"
    )
    return UserListResponse(
        total_count=total_count,
        users=users,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserInfo,
    summary="Get user details",
    description="Get detailed information about a specific user.",
    responses={
        200: {"description": "User retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get user")
async def get_user(
    user_id: str,
    _admin: str = Depends(require_admin_any),
) -> UserInfo:
    """Get detailed information about a user."""
    user = AdminQueryService.get_user(user_id)
    logger.info(f"Admin: Retrieved user {user_id}")
    return user


@router.patch(
    "/users/{user_id}",
    response_model=UserInfo,
    summary="Update user",
    description="Update user subscription tier or admin status.",
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("update user")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    _admin: str = Depends(require_admin_any),
) -> UserInfo:
    """Update user subscription tier or admin status."""
    # Validate at least one field is provided
    if request.subscription_tier is None and request.is_admin is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field (subscription_tier or is_admin) must be provided",
        )

    # Validate subscription_tier if provided
    if request.subscription_tier is not None:
        AdminValidationService.validate_subscription_tier(request.subscription_tier)

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}",
        )

    # Build dynamic UPDATE query
    update_fields = []
    params: list[Any] = []

    if request.subscription_tier is not None:
        update_fields.append("subscription_tier = %s")
        params.append(request.subscription_tier)

    if request.is_admin is not None:
        update_fields.append("is_admin = %s")
        params.append(request.is_admin)

    # Always update updated_at
    update_fields.append("updated_at = NOW()")
    params.append(user_id)

    # Execute update
    # noqa: S608 - Safe: update_fields contains only controlled column names, values are parameterized
    update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
    execute_query(update_query, tuple(params), fetch="none")

    # Fetch updated user with metrics
    # noqa: S608 - Safe: only uses controlled constants
    fetch_query = f"{USER_WITH_METRICS_SELECT} WHERE u.id = %s {USER_WITH_METRICS_GROUP_BY}"
    row = execute_query(fetch_query, (user_id,), fetch="one")

    if not row:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch updated user",
        )

    user = _row_to_user_info(row)

    logger.info(f"Admin: Updated user {user_id} - {request}")
    return user


@router.post(
    "/users/{user_id}/lock",
    response_model=LockUserResponse,
    summary="Lock user account",
    description="Lock a user account, preventing login. Revokes all active sessions.",
    responses={
        200: {"description": "User locked successfully"},
        400: {"description": "Cannot lock own account", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("lock user")
async def lock_user(
    user_id: str,
    request: LockUserRequest,
    admin_id: str = Depends(require_admin_any),
) -> LockUserResponse:
    """Lock a user account and revoke their sessions."""
    # Prevent admin from locking themselves
    if user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot lock your own account",
        )

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}",
        )

    # Lock the user
    result = AdminUserService.lock_user(user_id, admin_id, request.reason)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"User not found or already deleted: {user_id}",
        )

    # Revoke all sessions
    sessions_revoked = await AdminUserService.revoke_user_sessions(user_id)

    # Log the action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="user_locked",
        resource_type="user",
        resource_id=user_id,
        details={"reason": request.reason, "sessions_revoked": sessions_revoked},
    )

    logger.info(f"Admin {admin_id}: Locked user {user_id}, revoked {sessions_revoked} sessions")

    locked_at = result["locked_at"].isoformat() if result["locked_at"] else None
    return LockUserResponse(
        user_id=user_id,
        is_locked=True,
        locked_at=locked_at,
        lock_reason=result["lock_reason"],
        sessions_revoked=sessions_revoked,
        message=f"User {user_id} locked successfully. {sessions_revoked} session(s) revoked.",
    )


@router.post(
    "/users/{user_id}/unlock",
    response_model=LockUserResponse,
    summary="Unlock user account",
    description="Unlock a previously locked user account.",
    responses={
        200: {"description": "User unlocked successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("unlock user")
async def unlock_user(
    user_id: str,
    admin_id: str = Depends(require_admin_any),
) -> LockUserResponse:
    """Unlock a user account."""
    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}",
        )

    # Unlock the user
    result = AdminUserService.unlock_user(user_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}",
        )

    # Log the action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="user_unlocked",
        resource_type="user",
        resource_id=user_id,
    )

    logger.info(f"Admin {admin_id}: Unlocked user {user_id}")

    return LockUserResponse(
        user_id=user_id,
        is_locked=False,
        locked_at=None,
        lock_reason=None,
        sessions_revoked=0,
        message=f"User {user_id} unlocked successfully.",
    )


@router.delete(
    "/users/{user_id}",
    response_model=DeleteUserResponse,
    summary="Delete user account",
    description="Soft delete a user account (or hard delete if specified).",
    responses={
        200: {"description": "User deleted successfully"},
        400: {"description": "Cannot delete own account", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("delete user")
async def delete_user(
    user_id: str,
    request: DeleteUserRequest,
    admin_id: str = Depends(require_admin_any),
) -> DeleteUserResponse:
    """Delete a user account."""
    # Prevent admin from deleting themselves
    if user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own account",
        )

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}",
        )

    # Revoke sessions if requested
    sessions_revoked = 0
    if request.revoke_sessions:
        sessions_revoked = await AdminUserService.revoke_user_sessions(user_id)

    # Perform deletion
    if request.hard_delete:
        deleted = AdminUserService.hard_delete_user(user_id)
        action = "user_hard_deleted"
        message = f"User {user_id} permanently deleted."
    else:
        deleted = AdminUserService.soft_delete_user(user_id, admin_id)
        action = "user_soft_deleted"
        message = f"User {user_id} soft deleted."

    if not deleted:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user",
        )

    # Log the action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action=action,
        resource_type="user",
        resource_id=user_id,
        details={"hard_delete": request.hard_delete, "sessions_revoked": sessions_revoked},
    )

    logger.info(f"Admin {admin_id}: {action} user {user_id}, revoked {sessions_revoked} sessions")

    return DeleteUserResponse(
        user_id=user_id,
        deleted=True,
        hard_delete=request.hard_delete,
        sessions_revoked=sessions_revoked,
        message=f"{message} {sessions_revoked} session(s) revoked.",
    )
