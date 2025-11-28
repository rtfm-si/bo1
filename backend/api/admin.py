"""Admin API endpoints for Board of One.

Provides:
- GET /api/admin/users - List all users with metrics
- GET /api/admin/users/{user_id} - Get single user detail
- PATCH /api/admin/users/{user_id} - Update user (subscription_tier, is_admin)
- GET /api/admin/sessions/active - List all active sessions
- GET /api/admin/sessions/{session_id}/full - Full session details
- POST /api/admin/sessions/{session_id}/kill - Admin kill (no ownership check)
- POST /api/admin/sessions/kill-all - Emergency shutdown
- GET /api/admin/beta-whitelist - List all whitelisted emails
- POST /api/admin/beta-whitelist - Add email to whitelist
- DELETE /api/admin/beta-whitelist/{email} - Remove email from whitelist
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_redis_manager, get_session_manager
from backend.api.metrics import metrics
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.validation import validate_session_id
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ==============================================================================
# User Management Endpoints
# ==============================================================================


class UserInfo(BaseModel):
    """Information about a user.

    Attributes:
        user_id: User identifier
        email: User email address
        auth_provider: Authentication provider (google, github, supertokens, etc.)
        subscription_tier: Subscription tier (free, pro, enterprise)
        is_admin: Whether user has admin privileges
        total_meetings: Total number of meetings created
        total_cost: Total cost across all meetings (USD)
        last_meeting_at: When user's most recent meeting was created
        last_meeting_id: ID of user's most recent meeting
        created_at: When user account was created
        updated_at: When user account was last updated
    """

    user_id: str = Field(..., description="User identifier", examples=["user_123"])
    email: str = Field(..., description="User email address", examples=["alice@example.com"])
    auth_provider: str = Field(
        ..., description="Authentication provider", examples=["google", "github", "supertokens"]
    )
    subscription_tier: str = Field(
        ..., description="Subscription tier", examples=["free", "pro", "enterprise"]
    )
    is_admin: bool = Field(..., description="Whether user has admin privileges", examples=[False])
    total_meetings: int = Field(..., description="Total number of meetings created", examples=[5])
    total_cost: float | None = Field(
        None, description="Total cost across all meetings (USD)", examples=[0.42]
    )
    last_meeting_at: str | None = Field(
        None,
        description="When user's most recent meeting was created (ISO 8601)",
        examples=["2025-01-15T12:00:00"],
    )
    last_meeting_id: str | None = Field(
        None, description="ID of user's most recent meeting", examples=["bo1_abc123"]
    )
    created_at: str = Field(
        ...,
        description="When user account was created (ISO 8601)",
        examples=["2025-01-01T10:00:00"],
    )
    updated_at: str = Field(
        ...,
        description="When user account was last updated (ISO 8601)",
        examples=["2025-01-15T10:00:00"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user_123",
                    "email": "alice@example.com",
                    "auth_provider": "google",
                    "subscription_tier": "free",
                    "is_admin": False,
                    "total_meetings": 5,
                    "total_cost": 0.42,
                    "last_meeting_at": "2025-01-15T12:00:00",
                    "last_meeting_id": "bo1_abc123",
                    "created_at": "2025-01-01T10:00:00",
                    "updated_at": "2025-01-15T10:00:00",
                }
            ]
        }
    }


class UserListResponse(BaseModel):
    """Response model for user list.

    Attributes:
        total_count: Total number of users
        users: List of user info
        page: Current page number
        per_page: Number of users per page
    """

    total_count: int = Field(..., description="Total number of users", examples=[100])
    users: list[UserInfo] = Field(..., description="List of user info")
    page: int = Field(..., description="Current page number", examples=[1])
    per_page: int = Field(..., description="Number of users per page", examples=[10])


class UpdateUserRequest(BaseModel):
    """Request model for updating user.

    Attributes:
        subscription_tier: New subscription tier (optional)
        is_admin: New admin status (optional)
    """

    subscription_tier: str | None = Field(
        None,
        description="New subscription tier",
        examples=["free", "pro", "enterprise"],
    )
    is_admin: bool | None = Field(None, description="New admin status", examples=[True, False])


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
        from bo1.state.postgres_manager import db_session

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
                total_count = cur.fetchone()[0] if cur.fetchone() else 0

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
                        user_id=row[0],
                        email=row[1],
                        auth_provider=row[2],
                        subscription_tier=row[3],
                        is_admin=row[4],
                        created_at=row[5].isoformat() if row[5] else "",
                        updated_at=row[6].isoformat() if row[6] else "",
                        total_meetings=row[7] or 0,
                        total_cost=float(row[8]) if row[8] else None,
                        last_meeting_at=row[9].isoformat() if row[9] else None,
                        last_meeting_id=row[10],
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
        from bo1.state.postgres_manager import db_session

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
                    user_id=row[0],
                    email=row[1],
                    auth_provider=row[2],
                    subscription_tier=row[3],
                    is_admin=row[4],
                    created_at=row[5].isoformat() if row[5] else "",
                    updated_at=row[6].isoformat() if row[6] else "",
                    total_meetings=row[7] or 0,
                    total_cost=float(row[8]) if row[8] else None,
                    last_meeting_at=row[9].isoformat() if row[9] else None,
                    last_meeting_id=row[10],
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
        from bo1.state.postgres_manager import db_session

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
                    user_id=row[0],
                    email=row[1],
                    auth_provider=row[2],
                    subscription_tier=row[3],
                    is_admin=row[4],
                    created_at=row[5].isoformat() if row[5] else "",
                    updated_at=row[6].isoformat() if row[6] else "",
                    total_meetings=row[7] or 0,
                    total_cost=float(row[8]) if row[8] else None,
                    last_meeting_at=row[9].isoformat() if row[9] else None,
                    last_meeting_id=row[10],
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


class ActiveSessionInfo(BaseModel):
    """Information about an active session.

    Attributes:
        session_id: Session identifier
        user_id: User who owns the session
        status: Current session status
        phase: Current deliberation phase
        started_at: When session started
        duration_seconds: How long session has been running
        cost: Total cost so far
    """

    session_id: str = Field(
        ..., description="Session identifier", examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    user_id: str = Field(..., description="User who owns the session", examples=["test_user_1"])
    status: str = Field(..., description="Current session status", examples=["active", "running"])
    phase: str | None = Field(
        None, description="Current deliberation phase", examples=["discussion", "voting"]
    )
    started_at: str = Field(
        ..., description="When session started (ISO 8601)", examples=["2025-01-15T12:00:00"]
    )
    duration_seconds: float = Field(
        ..., description="How long session has been running", examples=[120.5]
    )
    cost: float | None = Field(None, description="Total cost so far (USD)", examples=[0.0145])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "test_user_1",
                    "status": "running",
                    "phase": "discussion",
                    "started_at": "2025-01-15T12:00:00",
                    "duration_seconds": 120.5,
                    "cost": 0.0145,
                }
            ]
        }
    }


class ActiveSessionsResponse(BaseModel):
    """Response model for active sessions list.

    Attributes:
        active_count: Number of active sessions
        sessions: List of active session info
        longest_running: Top N longest running sessions
        most_expensive: Top N most expensive sessions
    """

    active_count: int = Field(..., description="Number of active sessions", examples=[3])
    sessions: list[ActiveSessionInfo] = Field(..., description="List of active sessions")
    longest_running: list[ActiveSessionInfo] = Field(
        ..., description="Top N longest running sessions"
    )
    most_expensive: list[ActiveSessionInfo] = Field(
        ..., description="Top N most expensive sessions"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "active_count": 3,
                    "sessions": [
                        {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "test_user_1",
                            "status": "running",
                            "phase": "discussion",
                            "started_at": "2025-01-15T12:00:00",
                            "duration_seconds": 120.5,
                            "cost": 0.0145,
                        }
                    ],
                    "longest_running": [
                        {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "test_user_1",
                            "status": "running",
                            "phase": "discussion",
                            "started_at": "2025-01-15T12:00:00",
                            "duration_seconds": 120.5,
                            "cost": 0.0145,
                        }
                    ],
                    "most_expensive": [
                        {
                            "session_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user_id": "test_user_1",
                            "status": "running",
                            "phase": "discussion",
                            "started_at": "2025-01-15T12:00:00",
                            "duration_seconds": 120.5,
                            "cost": 0.0145,
                        }
                    ],
                }
            ]
        }
    }


class FullSessionResponse(BaseModel):
    """Response model for full session details.

    Attributes:
        session_id: Session identifier
        metadata: Full session metadata
        state: Full deliberation state
        is_active: Whether session is currently running
    """

    session_id: str = Field(..., description="Session identifier")
    metadata: dict[str, Any] = Field(..., description="Full session metadata")
    state: dict[str, Any] | None = Field(None, description="Full deliberation state")
    is_active: bool = Field(..., description="Whether session is currently running")


class KillAllResponse(BaseModel):
    """Response model for kill-all operation.

    Attributes:
        killed_count: Number of sessions killed
        message: Human-readable message
    """

    killed_count: int = Field(..., description="Number of sessions killed")
    message: str = Field(..., description="Human-readable message")


@router.get(
    "/sessions/active",
    response_model=ActiveSessionsResponse,
    summary="List all active sessions",
    description="List all active deliberation sessions across all users (admin only).",
    responses={
        200: {"description": "Active sessions retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def list_active_sessions(
    top_n: int = Query(10, ge=1, le=100, description="Number of top sessions to return"),
    _admin: str = Depends(require_admin_any),
) -> ActiveSessionsResponse:
    """List all active sessions with stats.

    Returns active sessions with duration, cost, and top N longest/most expensive.

    Args:
        top_n: Number of top sessions to return (1-100)
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ActiveSessionsResponse with session stats

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        session_manager = get_session_manager()
        redis_manager = get_redis_manager()

        # Get all active session IDs
        active_session_ids = list(session_manager.active_executions.keys())

        # Build session info list
        sessions: list[ActiveSessionInfo] = []
        now = datetime.now(UTC)

        for session_id in active_session_ids:
            # Load metadata
            metadata = redis_manager.load_metadata(session_id)
            if not metadata:
                continue

            # Calculate duration
            try:
                started_at = datetime.fromisoformat(metadata.get("started_at", now.isoformat()))
                duration = (now - started_at).total_seconds()
            except (ValueError, TypeError):
                duration = 0.0
                started_at = now

            # Get cost
            cost = metadata.get("cost")

            session_info = ActiveSessionInfo(
                session_id=session_id,
                user_id=metadata.get("user_id", "unknown"),
                status=metadata.get("status", "unknown"),
                phase=metadata.get("phase"),
                started_at=started_at.isoformat(),
                duration_seconds=duration,
                cost=cost,
            )
            sessions.append(session_info)

        # Sort for top N
        longest_running = sorted(sessions, key=lambda s: s.duration_seconds, reverse=True)[:top_n]
        most_expensive = sorted(
            [s for s in sessions if s.cost is not None], key=lambda s: s.cost or 0, reverse=True
        )[:top_n]

        logger.info(f"Admin: Listed {len(sessions)} active sessions")

        return ActiveSessionsResponse(
            active_count=len(sessions),
            sessions=sessions,
            longest_running=longest_running,
            most_expensive=most_expensive,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to list active sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list active sessions: {str(e)}",
        ) from e


@router.get(
    "/sessions/{session_id}/full",
    response_model=FullSessionResponse,
    summary="Get full session details",
    description="Get complete session metadata and state (admin only).",
    responses={
        200: {"description": "Session details retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_full_session(
    session_id: str,
    _admin: str = Depends(require_admin_any),
) -> FullSessionResponse:
    """Get full session details including all metadata and state.

    Args:
        session_id: Session identifier
        _admin_key: Admin API key (injected by dependency)

    Returns:
        FullSessionResponse with all session data

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        session_manager = get_session_manager()
        redis_manager = get_redis_manager()

        # Load metadata
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

        # Load state
        state = redis_manager.load_state(session_id)

        # Convert state to dict if it's a DeliberationState
        state_dict: dict[str, Any] | None = None
        if state:
            if isinstance(state, dict):
                state_dict = state
            else:
                # Convert DeliberationState to dict
                state_dict = state.model_dump() if hasattr(state, "model_dump") else None

        # Check if active
        is_active = session_id in session_manager.active_executions

        logger.info(f"Admin: Retrieved full session {session_id}")

        return FullSessionResponse(
            session_id=session_id,
            metadata=metadata,
            state=state_dict,
            is_active=is_active,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to get full session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get full session: {str(e)}",
        ) from e


@router.post(
    "/sessions/{session_id}/kill",
    response_model=ControlResponse,
    summary="Kill any session (admin)",
    description="Kill any session without ownership check (admin only).",
    responses={
        200: {"description": "Session killed successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def admin_kill_session(
    session_id: str,
    reason: str = Query("Admin terminated", description="Reason for killing session"),
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Admin kill any session (no ownership check).

    Args:
        session_id: Session identifier
        reason: Reason for killing session
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with kill confirmation

    Raises:
        HTTPException: If session not found or kill fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)
        session_manager = get_session_manager()

        # Admin kill (no ownership check)
        killed = await session_manager.admin_kill_session(session_id, "admin", reason)

        if not killed:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found or not running: {session_id}",
            )

        logger.warning(f"Admin: Killed session {session_id}. Reason: {reason}")

        return ControlResponse(
            session_id=session_id,
            action="admin_kill",
            status="success",
            message=f"Admin killed session. Reason: {reason}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to kill session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to kill session: {str(e)}",
        ) from e


@router.post(
    "/sessions/kill-all",
    response_model=KillAllResponse,
    summary="Emergency shutdown - kill all sessions",
    description="Kill all active sessions (admin only, requires confirm=true).",
    responses={
        200: {"description": "All sessions killed successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        400: {"description": "Confirmation required", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def admin_kill_all_sessions(
    confirm: bool = Query(False, description="Must be true to confirm kill-all"),
    reason: str = Query("System maintenance", description="Reason for emergency shutdown"),
    _admin: str = Depends(require_admin_any),
) -> KillAllResponse:
    """Emergency shutdown - kill all active sessions.

    Requires confirm=true query parameter to prevent accidental use.

    Args:
        confirm: Must be true to confirm operation
        reason: Reason for mass termination
        _admin_key: Admin API key (injected by dependency)

    Returns:
        KillAllResponse with count of killed sessions

    Raises:
        HTTPException: If confirmation not provided or kill fails
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Must set confirm=true to kill all sessions",
            )

        session_manager = get_session_manager()

        # Admin kill all
        killed_count = await session_manager.admin_kill_all_sessions("admin", reason)

        logger.warning(f"Admin: KILL ALL - Terminated {killed_count} sessions. Reason: {reason}")

        return KillAllResponse(
            killed_count=killed_count,
            message=f"Admin killed all {killed_count} active sessions. Reason: {reason}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to kill all sessions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to kill all sessions: {str(e)}",
        ) from e


# Research Cache Admin Endpoints


class ResearchCacheStats(BaseModel):
    """Response model for research cache statistics.

    Attributes:
        total_cached_results: Total number of cached research results
        cache_hit_rate_30d: Cache hit rate in last 30 days (percentage)
        cost_savings_30d: Cost savings in last 30 days (USD)
        top_cached_questions: Top 10 most accessed cached questions
    """

    total_cached_results: int = Field(..., description="Total number of cached research results")
    cache_hit_rate_30d: float = Field(
        ..., description="Cache hit rate in last 30 days (percentage)"
    )
    cost_savings_30d: float = Field(..., description="Cost savings in last 30 days (USD)")
    top_cached_questions: list[dict[str, Any]] = Field(
        ..., description="Top 10 most accessed cached questions"
    )


class StaleEntriesResponse(BaseModel):
    """Response model for stale cache entries.

    Attributes:
        stale_count: Number of stale entries found
        entries: List of stale cache entries
    """

    stale_count: int = Field(..., description="Number of stale entries found")
    entries: list[dict[str, Any]] = Field(..., description="List of stale cache entries")


@router.get(
    "/research-cache/stats",
    response_model=ResearchCacheStats,
    summary="Get research cache statistics",
    description="Get analytics and statistics for the research cache (admin only).",
    responses={
        200: {"description": "Cache statistics retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_research_cache_stats(
    _admin: str = Depends(require_admin_any),
) -> ResearchCacheStats:
    """Get research cache analytics and statistics.

    Returns cache hit rates, cost savings, and top cached questions.

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ResearchCacheStats with analytics

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from bo1.state.postgres_manager import get_research_cache_stats as get_stats

        stats = get_stats()

        logger.info("Admin: Retrieved research cache statistics")

        return ResearchCacheStats(**stats)

    except Exception as e:
        logger.error(f"Admin: Failed to get research cache stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get research cache stats: {str(e)}",
        ) from e


@router.delete(
    "/research-cache/{cache_id}",
    response_model=ControlResponse,
    summary="Delete cached research result",
    description="Delete a specific research cache entry by ID (admin only).",
    responses={
        200: {"description": "Cache entry deleted successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        404: {"description": "Cache entry not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def delete_research_cache_entry(
    cache_id: str,
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Delete a specific research cache entry.

    Args:
        cache_id: Research cache entry ID (UUID)
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with deletion confirmation

    Raises:
        HTTPException: If cache entry not found or deletion fails
    """
    try:
        from bo1.state.postgres_manager import delete_research_cache_entry as delete_entry

        deleted = delete_entry(cache_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Research cache entry not found: {cache_id}",
            )

        logger.info(f"Admin: Deleted research cache entry {cache_id}")

        return ControlResponse(
            session_id=cache_id,  # Using session_id field for cache_id
            action="delete_cache",
            status="success",
            message=f"Research cache entry deleted: {cache_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to delete research cache entry {cache_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete research cache entry: {str(e)}",
        ) from e


@router.get(
    "/research-cache/stale",
    response_model=StaleEntriesResponse,
    summary="Get stale research cache entries",
    description="Get research cache entries older than specified days (admin only).",
    responses={
        200: {"description": "Stale entries retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_stale_research_cache_entries(
    days_old: int = Query(90, ge=1, le=365, description="Number of days to consider stale"),
    _admin: str = Depends(require_admin_any),
) -> StaleEntriesResponse:
    """Get research cache entries older than specified days.

    This endpoint helps admins identify stale cache entries that may need refreshing.

    Args:
        days_old: Number of days to consider stale (1-365, default: 90)
        _admin_key: Admin API key (injected by dependency)

    Returns:
        StaleEntriesResponse with list of stale entries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from bo1.state.postgres_manager import get_stale_research_cache_entries as get_stale

        entries = get_stale(days_old)

        logger.info(
            f"Admin: Retrieved {len(entries)} stale research cache entries (>{days_old} days)"
        )

        return StaleEntriesResponse(
            stale_count=len(entries),
            entries=entries,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to get stale research cache entries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stale research cache entries: {str(e)}",
        ) from e


# Beta Whitelist Admin Endpoints


class BetaWhitelistEntry(BaseModel):
    """Response model for beta whitelist entry.

    Attributes:
        id: Entry ID
        email: Whitelisted email address
        added_by: Admin who added this email
        notes: Optional notes about the beta tester
        created_at: When email was added
    """

    id: str = Field(..., description="Entry ID (UUID)")
    email: str = Field(..., description="Whitelisted email address")
    added_by: str | None = Field(None, description="Admin who added this email")
    notes: str | None = Field(None, description="Optional notes about the beta tester")
    created_at: str = Field(..., description="When email was added (ISO 8601)")


class BetaWhitelistResponse(BaseModel):
    """Response model for beta whitelist list.

    Attributes:
        total_count: Total number of whitelisted emails
        emails: List of whitelist entries
    """

    total_count: int = Field(..., description="Total number of whitelisted emails")
    emails: list[BetaWhitelistEntry] = Field(..., description="List of whitelist entries")


class AddWhitelistRequest(BaseModel):
    """Request model for adding email to whitelist.

    Attributes:
        email: Email address to whitelist
        notes: Optional notes about the beta tester
    """

    email: str = Field(
        ..., description="Email address to whitelist", examples=["alice@example.com"]
    )
    notes: str | None = Field(
        None,
        description="Optional notes about the beta tester",
        examples=["YC batch W25", "Referred by Alice"],
    )


@router.get(
    "/beta-whitelist",
    response_model=BetaWhitelistResponse,
    summary="List all whitelisted emails",
    description="Get list of all emails whitelisted for closed beta access (admin only).",
    responses={
        200: {"description": "Whitelist retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def list_beta_whitelist(
    _admin: str = Depends(require_admin_any),
) -> BetaWhitelistResponse:
    """List all whitelisted emails for closed beta.

    Returns all emails in the beta whitelist with metadata.

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        BetaWhitelistResponse with all whitelist entries

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        from bo1.state.postgres_manager import db_session

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, added_by, notes, created_at
                    FROM beta_whitelist
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()

                entries = [
                    BetaWhitelistEntry(
                        id=str(row[0]),
                        email=row[1],
                        added_by=row[2],
                        notes=row[3],
                        created_at=row[4].isoformat() if row[4] else "",
                    )
                    for row in rows
                ]

        logger.info(f"Admin: Retrieved {len(entries)} beta whitelist entries")

        return BetaWhitelistResponse(
            total_count=len(entries),
            emails=entries,
        )

    except Exception as e:
        logger.error(f"Admin: Failed to list beta whitelist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list beta whitelist: {str(e)}",
        ) from e


@router.post(
    "/beta-whitelist",
    response_model=BetaWhitelistEntry,
    summary="Add email to whitelist",
    description="Add email address to closed beta whitelist (admin only).",
    responses={
        200: {"description": "Email added to whitelist successfully"},
        400: {"description": "Invalid email or already exists", "model": ErrorResponse},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def add_to_beta_whitelist(
    request: AddWhitelistRequest,
    _admin: str = Depends(require_admin_any),
) -> BetaWhitelistEntry:
    """Add email to beta whitelist.

    Args:
        request: Email and optional notes
        _admin_key: Admin API key (injected by dependency)

    Returns:
        BetaWhitelistEntry with created entry

    Raises:
        HTTPException: If email is invalid or already exists
    """
    try:
        from bo1.state.postgres_manager import db_session

        # Normalize email
        email = request.email.strip().lower()

        # Simple email validation
        if "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email address: {email}",
            )

        with db_session() as conn:
            with conn.cursor() as cur:
                # Check if email already exists
                cur.execute("SELECT id FROM beta_whitelist WHERE email = %s", (email,))
                if cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Email already whitelisted: {email}",
                    )

                # Insert new entry
                cur.execute(
                    """
                    INSERT INTO beta_whitelist (email, added_by, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id, email, added_by, notes, created_at
                    """,
                    (email, "admin", request.notes),
                )
                row = cur.fetchone()

        entry = BetaWhitelistEntry(
            id=str(row[0]),
            email=row[1],
            added_by=row[2],
            notes=row[3],
            created_at=row[4].isoformat() if row[4] else "",
        )

        logger.info(f"Admin: Added {email} to beta whitelist")

        return entry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to add {request.email} to beta whitelist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add email to beta whitelist: {str(e)}",
        ) from e


@router.delete(
    "/beta-whitelist/{email}",
    response_model=ControlResponse,
    summary="Remove email from whitelist",
    description="Remove email address from closed beta whitelist (admin only).",
    responses={
        200: {"description": "Email removed from whitelist successfully"},
        404: {"description": "Email not found in whitelist", "model": ErrorResponse},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def remove_from_beta_whitelist(
    email: str,
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Remove email from beta whitelist.

    Args:
        email: Email address to remove
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with removal confirmation

    Raises:
        HTTPException: If email not found or removal fails
    """
    try:
        from bo1.state.postgres_manager import db_session

        # Normalize email
        email = email.strip().lower()

        with db_session() as conn:
            with conn.cursor() as cur:
                # Delete email
                cur.execute("DELETE FROM beta_whitelist WHERE email = %s RETURNING id", (email,))
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Email not found in whitelist: {email}",
                    )

        logger.info(f"Admin: Removed {email} from beta whitelist")

        return ControlResponse(
            session_id=str(row[0]),  # Using session_id field for whitelist ID
            action="remove_whitelist",
            status="success",
            message=f"Removed {email} from beta whitelist",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin: Failed to remove {email} from beta whitelist: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove email from beta whitelist: {str(e)}",
        ) from e


# ==============================================================================
# Metrics Endpoints
# ==============================================================================


@router.get(
    "/metrics",
    summary="Get system metrics",
    description="""
    Get all system metrics including API endpoint performance, LLM usage, and cache hit rates.

    Returns:
    - Counters: Success/error counts for API endpoints and LLM calls
    - Histograms: Latency distributions, token usage, costs

    Metrics reset on server restart.
    """,
    responses={
        200: {"description": "Metrics retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def get_metrics(
    _admin: str = Depends(require_admin_any),
) -> dict[str, Any]:
    """Get all system metrics (admin only).

    Returns counters and histogram statistics for:
    - API endpoint calls (success/error rates, latency)
    - LLM API calls (cache hits, token usage, costs)
    - Database queries (if instrumented)
    - Cache operations (hit rates)

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        Dict with counters and histograms

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        return metrics.get_stats()
    except Exception as e:
        logger.error(f"Admin: Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}",
        ) from e


@router.post(
    "/metrics/reset",
    summary="Reset all metrics",
    description="""
    Reset all metrics to zero.

    Use this to clear metrics after deployment or for debugging.
    Metrics automatically reset on server restart.
    """,
    responses={
        200: {"description": "Metrics reset successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def reset_metrics(
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Reset all metrics to zero (admin only).

    Args:
        _admin_key: Admin API key (injected by dependency)

    Returns:
        ControlResponse with reset confirmation

    Raises:
        HTTPException: If metrics reset fails
    """
    try:
        metrics.reset()
        logger.info("Admin: Reset all metrics")

        return ControlResponse(
            session_id="",  # Not session-specific
            action="reset_metrics",
            status="success",
            message="All metrics reset successfully",
        )
    except Exception as e:
        logger.error(f"Admin: Failed to reset metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset metrics: {str(e)}",
        ) from e
