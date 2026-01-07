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

from fastapi import APIRouter, Depends, Query, Request

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
    NonprofitStatusResponse,
    SetNonprofitRequest,
    SetTierOverrideRequest,
    TierOverrideResponse,
    UpdateUserRequest,
    UserInfo,
    UserListResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.pagination import make_page_pagination_fields
from bo1.logging.errors import ErrorCode
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get admin stats")
async def get_admin_stats(
    request: Request,
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list users")
async def list_users(
    request: Request,
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
    pagination = make_page_pagination_fields(total_count, page, per_page)
    return UserListResponse(
        total_count=total_count,
        users=users,
        page=page,
        per_page=per_page,
        has_more=pagination["has_more"],
        next_offset=pagination["next_offset"],
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get user")
async def get_user(
    request: Request,
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update user")
async def update_user(
    request: Request,
    user_id: str,
    body: UpdateUserRequest,
    _admin: str = Depends(require_admin_any),
) -> UserInfo:
    """Update user subscription tier or admin status."""
    # Validate at least one field is provided
    if body.subscription_tier is None and body.is_admin is None:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "At least one field (subscription_tier or is_admin) must be provided",
            status=400,
        )

    # Validate subscription_tier if provided
    if body.subscription_tier is not None:
        AdminValidationService.validate_subscription_tier(body.subscription_tier)

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Build dynamic UPDATE query
    update_fields = []
    params: list[Any] = []

    if body.subscription_tier is not None:
        update_fields.append("subscription_tier = %s")
        params.append(body.subscription_tier)

    if body.is_admin is not None:
        update_fields.append("is_admin = %s")
        params.append(body.is_admin)

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
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to fetch updated user", status=500
        )

    user = _row_to_user_info(row)

    logger.info(f"Admin: Updated user {user_id} - {body}")
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("lock user")
async def lock_user(
    request: Request,
    user_id: str,
    body: LockUserRequest,
    admin_id: str = Depends(require_admin_any),
) -> LockUserResponse:
    """Lock a user account and revoke their sessions."""
    # Prevent admin from locking themselves
    if user_id == admin_id:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Cannot lock your own account", status=400)

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Lock the user
    result = AdminUserService.lock_user(user_id, admin_id, body.reason)
    if not result:
        raise http_error(
            ErrorCode.API_NOT_FOUND, f"User not found or already deleted: {user_id}", status=404
        )

    # Revoke all sessions
    sessions_revoked = await AdminUserService.revoke_user_sessions(user_id)

    # Log the action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="user_locked",
        resource_type="user",
        resource_id=user_id,
        details={"reason": body.reason, "sessions_revoked": sessions_revoked},
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("unlock user")
async def unlock_user(
    request: Request,
    user_id: str,
    admin_id: str = Depends(require_admin_any),
) -> LockUserResponse:
    """Unlock a user account."""
    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Unlock the user
    result = AdminUserService.unlock_user(user_id)
    if not result:
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete user")
async def delete_user(
    request: Request,
    user_id: str,
    body: DeleteUserRequest,
    admin_id: str = Depends(require_admin_any),
) -> DeleteUserResponse:
    """Delete a user account."""
    # Prevent admin from deleting themselves
    if user_id == admin_id:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Cannot delete your own account", status=400)

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Revoke sessions if requested
    sessions_revoked = 0
    if body.revoke_sessions:
        sessions_revoked = await AdminUserService.revoke_user_sessions(user_id)

    # Perform deletion
    if body.hard_delete:
        deleted = AdminUserService.hard_delete_user(user_id)
        action = "user_hard_deleted"
        message = f"User {user_id} permanently deleted."
    else:
        deleted = AdminUserService.soft_delete_user(user_id, admin_id)
        action = "user_soft_deleted"
        message = f"User {user_id} soft deleted."

    if not deleted:
        raise http_error(ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to delete user", status=500)

    # Log the action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action=action,
        resource_type="user",
        resource_id=user_id,
        details={"hard_delete": body.hard_delete, "sessions_revoked": sessions_revoked},
    )

    logger.info(f"Admin {admin_id}: {action} user {user_id}, revoked {sessions_revoked} sessions")

    return DeleteUserResponse(
        user_id=user_id,
        deleted=True,
        hard_delete=body.hard_delete,
        sessions_revoked=sessions_revoked,
        message=f"{message} {sessions_revoked} session(s) revoked.",
    )


# ==============================================================================
# Tier Override Endpoints
# ==============================================================================


@router.get(
    "/users/{user_id}/tier-override",
    response_model=TierOverrideResponse,
    summary="Get user tier override",
    description="Get the current tier override for a user.",
    responses={
        200: {"description": "Tier override retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get tier override")
async def get_tier_override(
    request: Request,
    user_id: str,
    _admin: str = Depends(require_admin_any),
) -> TierOverrideResponse:
    """Get the current tier override for a user."""
    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Get user's tier info
    row = execute_query(
        "SELECT subscription_tier, tier_override FROM users WHERE id = %s",
        (user_id,),
        fetch="one",
    )

    if not row:
        raise http_error(ErrorCode.API_NOT_FOUND, "User not found", status=404)

    base_tier = row["subscription_tier"]
    tier_override = row["tier_override"]

    # Determine effective tier
    effective_tier = base_tier
    if tier_override and isinstance(tier_override, dict):
        # Check expiry
        if tier_override.get("expires_at"):
            from datetime import UTC, datetime

            expires = datetime.fromisoformat(tier_override["expires_at"].replace("Z", "+00:00"))
            if expires > datetime.now(UTC):
                effective_tier = tier_override.get("tier", base_tier)
        else:
            effective_tier = tier_override.get("tier", base_tier)

    return TierOverrideResponse(
        user_id=user_id,
        tier_override=tier_override,
        effective_tier=effective_tier,
        message="Tier override retrieved" if tier_override else "No tier override set",
    )


@router.post(
    "/users/{user_id}/tier-override",
    response_model=TierOverrideResponse,
    summary="Set user tier override",
    description="Set a temporary tier override for a user (e.g., for beta testers or goodwill).",
    responses={
        200: {"description": "Tier override set successfully"},
        400: {"description": "Invalid tier", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("set tier override")
async def set_tier_override(
    request: Request,
    user_id: str,
    body: SetTierOverrideRequest,
    admin_id: str = Depends(require_admin_any),
) -> TierOverrideResponse:
    """Set a tier override for a user."""
    import json
    from datetime import UTC, datetime

    # Validate tier
    valid_tiers = ["free", "starter", "pro", "enterprise"]
    if body.tier.lower() not in valid_tiers:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid tier: {body.tier}. Must be one of: {', '.join(valid_tiers)}",
            status=400,
        )

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Build override object
    override = {
        "tier": body.tier.lower(),
        "reason": body.reason,
        "set_by": admin_id,
        "set_at": datetime.now(UTC).isoformat(),
    }
    if body.expires_at:
        override["expires_at"] = body.expires_at

    # Update user
    execute_query(
        "UPDATE users SET tier_override = %s, updated_at = NOW() WHERE id = %s",
        (json.dumps(override), user_id),
        fetch="none",
    )

    # Log admin action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="tier_override_set",
        resource_type="user",
        resource_id=user_id,
        details=override,
    )

    logger.info(f"Admin {admin_id}: Set tier override for {user_id} to {body.tier}")

    return TierOverrideResponse(
        user_id=user_id,
        tier_override=override,
        effective_tier=body.tier.lower(),
        message=f"Tier override set to {body.tier}",
    )


@router.delete(
    "/users/{user_id}/tier-override",
    response_model=TierOverrideResponse,
    summary="Delete user tier override",
    description="Remove the tier override for a user, reverting to their base subscription tier.",
    responses={
        200: {"description": "Tier override removed successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete tier override")
async def delete_tier_override(
    request: Request,
    user_id: str,
    admin_id: str = Depends(require_admin_any),
) -> TierOverrideResponse:
    """Remove the tier override for a user."""
    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Get base tier before clearing
    row = execute_query(
        "SELECT subscription_tier FROM users WHERE id = %s",
        (user_id,),
        fetch="one",
    )

    if not row:
        raise http_error(ErrorCode.API_NOT_FOUND, "User not found", status=404)

    base_tier = row["subscription_tier"]

    # Clear override
    execute_query(
        "UPDATE users SET tier_override = NULL, updated_at = NOW() WHERE id = %s",
        (user_id,),
        fetch="none",
    )

    # Log admin action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="tier_override_deleted",
        resource_type="user",
        resource_id=user_id,
    )

    logger.info(f"Admin {admin_id}: Removed tier override for {user_id}")

    return TierOverrideResponse(
        user_id=user_id,
        tier_override=None,
        effective_tier=base_tier,
        message=f"Tier override removed. User reverted to {base_tier} tier.",
    )


# ==============================================================================
# Nonprofit Status Endpoints
# ==============================================================================


@router.post(
    "/users/{user_id}/nonprofit",
    response_model=NonprofitStatusResponse,
    summary="Set nonprofit status",
    description="Mark a user as a verified nonprofit and optionally apply a discount promo.",
    responses={
        200: {"description": "Nonprofit status set successfully"},
        400: {"description": "Invalid request or promo code", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("set nonprofit status")
async def set_nonprofit_status(
    request: Request,
    user_id: str,
    body: SetNonprofitRequest,
    admin_id: str = Depends(require_admin_any),
) -> NonprofitStatusResponse:
    """Set nonprofit status for a user and optionally apply promo."""
    from datetime import UTC, datetime

    from backend.services.promotion_service import PromoValidationError, validate_and_apply_code

    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Validate promo code if provided
    if body.apply_promo_code:
        code = body.apply_promo_code.upper()
        if code not in ("NONPROFIT80", "NONPROFIT100"):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "Promo code must be NONPROFIT80 or NONPROFIT100",
                status=400,
            )

    # Set nonprofit status
    now = datetime.now(UTC)
    execute_query(
        """
        UPDATE users
        SET is_nonprofit = true,
            nonprofit_org_name = %s,
            nonprofit_verified_at = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (body.org_name, now, user_id),
        fetch="none",
    )

    # Apply promo code if requested
    promo_applied = False
    if body.apply_promo_code:
        try:
            validate_and_apply_code(user_id, body.apply_promo_code)
            promo_applied = True
            logger.info(f"Applied nonprofit promo {body.apply_promo_code} to user {user_id}")
        except PromoValidationError as e:
            # Don't fail the nonprofit status, just note promo wasn't applied
            logger.warning(f"Could not apply promo to {user_id}: {e.message}")

    # Log admin action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="nonprofit_status_set",
        resource_type="user",
        resource_id=user_id,
        details={
            "org_name": body.org_name,
            "promo_code": body.apply_promo_code,
            "promo_applied": promo_applied,
        },
    )

    logger.info(f"Admin {admin_id}: Set nonprofit status for {user_id} ({body.org_name})")

    message = f"Nonprofit status set for {body.org_name}"
    if promo_applied:
        message += f" with {body.apply_promo_code} promo applied"

    return NonprofitStatusResponse(
        user_id=user_id,
        is_nonprofit=True,
        nonprofit_org_name=body.org_name,
        nonprofit_verified_at=now.isoformat(),
        promo_applied=promo_applied,
        message=message,
    )


@router.delete(
    "/users/{user_id}/nonprofit",
    response_model=NonprofitStatusResponse,
    summary="Remove nonprofit status",
    description="Remove nonprofit status from a user. Does not revoke applied promos.",
    responses={
        200: {"description": "Nonprofit status removed successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("remove nonprofit status")
async def remove_nonprofit_status(
    request: Request,
    user_id: str,
    admin_id: str = Depends(require_admin_any),
) -> NonprofitStatusResponse:
    """Remove nonprofit status from a user."""
    # Check if user exists
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Remove nonprofit status
    execute_query(
        """
        UPDATE users
        SET is_nonprofit = false,
            nonprofit_org_name = NULL,
            nonprofit_verified_at = NULL,
            updated_at = NOW()
        WHERE id = %s
        """,
        (user_id,),
        fetch="none",
    )

    # Log admin action
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="nonprofit_status_removed",
        resource_type="user",
        resource_id=user_id,
    )

    logger.info(f"Admin {admin_id}: Removed nonprofit status from {user_id}")

    return NonprofitStatusResponse(
        user_id=user_id,
        is_nonprofit=False,
        nonprofit_org_name=None,
        nonprofit_verified_at=None,
        promo_applied=False,
        message="Nonprofit status removed. Note: Previously applied promos are not revoked.",
    )
