"""Admin API endpoints for user management.

Provides:
- GET /api/admin/stats - Get admin dashboard statistics
- GET /api/admin/users - List all users with metrics
- GET /api/admin/users/{user_id} - Get single user detail
- PATCH /api/admin/users/{user_id} - Update user (subscription_tier, is_admin)
"""

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.admin.models import (
    AdminStatsResponse,
    UpdateUserRequest,
    UserInfo,
    UserListResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from bo1.state.postgres_manager import db_session
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
async def get_admin_stats(
    _admin: str = Depends(require_admin_any),
) -> AdminStatsResponse:
    """Get aggregated statistics for the admin dashboard.

    Returns:
        AdminStatsResponse with total users, meetings, cost, whitelist, and waitlist counts

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get total users
                cur.execute("SELECT COUNT(*) as count FROM users")
                total_users = cur.fetchone()["count"]

                # Get total meetings and cost from sessions
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_meetings,
                        COALESCE(SUM(total_cost), 0) as total_cost
                    FROM sessions
                    """
                )
                session_stats = cur.fetchone()
                total_meetings = session_stats["total_meetings"]
                total_cost = float(session_stats["total_cost"])

                # Get whitelist count (db + env)
                cur.execute("SELECT COUNT(*) as count FROM beta_whitelist")
                db_whitelist_count = cur.fetchone()["count"]

                env_whitelist = os.getenv("BETA_WHITELIST", "")
                env_emails = [e.strip().lower() for e in env_whitelist.split(",") if e.strip()]
                # For simplicity, just add env count (may have overlap but that's fine for stats)
                whitelist_count = db_whitelist_count + len(env_emails)

                # Get pending waitlist count
                cur.execute("SELECT COUNT(*) as count FROM waitlist WHERE status = 'pending'")
                waitlist_pending = cur.fetchone()["count"]

        logger.info(
            f"Admin: Retrieved stats - users: {total_users}, meetings: {total_meetings}, "
            f"cost: ${total_cost:.2f}, whitelist: {whitelist_count}, waitlist: {waitlist_pending}"
        )

        return AdminStatsResponse(
            total_users=total_users,
            total_meetings=total_meetings,
            total_cost=total_cost,
            whitelist_count=whitelist_count,
            waitlist_pending=waitlist_pending,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to get stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get admin stats: {str(e)}",
        ) from e


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
async def list_users(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(10, ge=1, le=100, description="Users per page (1-100)"),
    email: str | None = Query(None, description="Search by email (partial match)"),
    _admin: str = Depends(require_admin_any),
) -> UserListResponse:
    """List all users with metrics.

    Returns paginated list of users with total meetings, costs, and last activity.

    Args:
        page: Page number (1-indexed)
        per_page: Number of users per page (1-100)
        email: Optional email search filter (case-insensitive partial match)
        _admin_key: Admin API key (injected by dependency)

    Returns:
        UserListResponse with user list and pagination info

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Build query with optional email filter
                count_query = """
                    SELECT COUNT(*)
                    FROM users
                """
                params: list[Any] = []

                if email:
                    count_query += " WHERE LOWER(email) LIKE LOWER(%s)"
                    params.append(f"%{email}%")

                # Get total count
                cur.execute(count_query, params)
                count_row = cur.fetchone()
                total_count = count_row["count"] if count_row else 0

                # Get paginated users with metrics
                offset = (page - 1) * per_page
                users_query = """
                    SELECT
                        u.id,
                        u.email,
                        u.auth_provider,
                        u.subscription_tier,
                        u.is_admin,
                        u.created_at,
                        u.updated_at,
                        COUNT(s.id) as total_meetings,
                        SUM(s.total_cost) as total_cost,
                        MAX(s.created_at) as last_meeting_at,
                        (SELECT id FROM sessions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_meeting_id
                    FROM users u
                    LEFT JOIN sessions s ON u.id = s.user_id
                """

                if email:
                    users_query += " WHERE LOWER(u.email) LIKE LOWER(%s)"

                users_query += """
                    GROUP BY u.id, u.email, u.auth_provider, u.subscription_tier, u.is_admin, u.created_at, u.updated_at
                    ORDER BY u.created_at DESC
                    LIMIT %s OFFSET %s
                """

                if email:
                    params_users = [f"%{email}%", per_page, offset]
                else:
                    params_users = [per_page, offset]

                cur.execute(users_query, params_users)
                rows = cur.fetchall()

                users = [
                    UserInfo(
                        user_id=row["id"],
                        email=row["email"],
                        auth_provider=row["auth_provider"],
                        subscription_tier=row["subscription_tier"],
                        is_admin=row["is_admin"],
                        created_at=row["created_at"].isoformat() if row["created_at"] else "",
                        updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                        total_meetings=row["total_meetings"] or 0,
                        total_cost=float(row["total_cost"]) if row["total_cost"] else None,
                        last_meeting_at=row["last_meeting_at"].isoformat()
                        if row["last_meeting_at"]
                        else None,
                        last_meeting_id=row["last_meeting_id"],
                    )
                    for row in rows
                ]

        logger.info(
            f"Admin: Listed {len(users)} users (page {page}, per_page {per_page}, total {total_count})"
        )

        return UserListResponse(
            total_count=total_count,
            users=users,
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to list users: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list users: {str(e)}",
        ) from e


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
async def get_user(
    user_id: str,
    _admin: str = Depends(require_admin_any),
) -> UserInfo:
    """Get detailed information about a user.

    Args:
        user_id: User identifier
        _admin_key: Admin API key (injected by dependency)

    Returns:
        UserInfo with user details and metrics

    Raises:
        HTTPException: If user not found or retrieval fails
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        u.id,
                        u.email,
                        u.auth_provider,
                        u.subscription_tier,
                        u.is_admin,
                        u.created_at,
                        u.updated_at,
                        COUNT(s.id) as total_meetings,
                        SUM(s.total_cost) as total_cost,
                        MAX(s.created_at) as last_meeting_at,
                        (SELECT id FROM sessions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_meeting_id
                    FROM users u
                    LEFT JOIN sessions s ON u.id = s.user_id
                    WHERE u.id = %s
                    GROUP BY u.id, u.email, u.auth_provider, u.subscription_tier, u.is_admin, u.created_at, u.updated_at
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"User not found: {user_id}",
                    )

                user = UserInfo(
                    user_id=row["id"],
                    email=row["email"],
                    auth_provider=row["auth_provider"],
                    subscription_tier=row["subscription_tier"],
                    is_admin=row["is_admin"],
                    created_at=row["created_at"].isoformat() if row["created_at"] else "",
                    updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                    total_meetings=row["total_meetings"] or 0,
                    total_cost=float(row["total_cost"]) if row["total_cost"] else None,
                    last_meeting_at=row["last_meeting_at"].isoformat()
                    if row["last_meeting_at"]
                    else None,
                    last_meeting_id=row["last_meeting_id"],
                )

        logger.info(f"Admin: Retrieved user {user_id}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to get user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user: {str(e)}",
        ) from e


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
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    _admin: str = Depends(require_admin_any),
) -> UserInfo:
    """Update user subscription tier or admin status.

    Args:
        user_id: User identifier
        request: Update request with optional subscription_tier and is_admin
        _admin_key: Admin API key (injected by dependency)

    Returns:
        UserInfo with updated user details

    Raises:
        HTTPException: If user not found, invalid request, or update fails
    """
    try:
        # Validate at least one field is provided
        if request.subscription_tier is None and request.is_admin is None:
            raise HTTPException(
                status_code=400,
                detail="At least one field (subscription_tier or is_admin) must be provided",
            )

        # Validate subscription_tier if provided
        if request.subscription_tier is not None:
            valid_tiers = ["free", "pro", "enterprise"]
            if request.subscription_tier not in valid_tiers:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid subscription_tier. Must be one of: {', '.join(valid_tiers)}",
                )

        with db_session() as conn:
            with conn.cursor() as cur:
                # Check if user exists
                cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if not cur.fetchone():
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
                query = f"""
                    UPDATE users
                    SET {", ".join(update_fields)}
                    WHERE id = %s
                """  # noqa: S608 - Safe: update_fields contains only controlled column names, values are parameterized

                cur.execute(query, params)

                # Fetch updated user with metrics
                cur.execute(
                    """
                    SELECT
                        u.id,
                        u.email,
                        u.auth_provider,
                        u.subscription_tier,
                        u.is_admin,
                        u.created_at,
                        u.updated_at,
                        COUNT(s.id) as total_meetings,
                        SUM(s.total_cost) as total_cost,
                        MAX(s.created_at) as last_meeting_at,
                        (SELECT id FROM sessions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_meeting_id
                    FROM users u
                    LEFT JOIN sessions s ON u.id = s.user_id
                    WHERE u.id = %s
                    GROUP BY u.id, u.email, u.auth_provider, u.subscription_tier, u.is_admin, u.created_at, u.updated_at
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to fetch updated user",
                    )

                user = UserInfo(
                    user_id=row["id"],
                    email=row["email"],
                    auth_provider=row["auth_provider"],
                    subscription_tier=row["subscription_tier"],
                    is_admin=row["is_admin"],
                    created_at=row["created_at"].isoformat() if row["created_at"] else "",
                    updated_at=row["updated_at"].isoformat() if row["updated_at"] else "",
                    total_meetings=row["total_meetings"] or 0,
                    total_cost=float(row["total_cost"]) if row["total_cost"] else None,
                    last_meeting_at=row["last_meeting_at"].isoformat()
                    if row["last_meeting_at"]
                    else None,
                    last_meeting_id=row["last_meeting_id"],
                )

        logger.info(f"Admin: Updated user {user_id} - {request}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to update user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user: {str(e)}",
        ) from e
