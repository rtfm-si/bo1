"""Admin API endpoints for session management.

Provides:
- GET /api/admin/sessions/active - List all active sessions
- GET /api/admin/sessions/{session_id}/full - Full session details
- POST /api/admin/sessions/{session_id}/kill - Admin kill (no ownership check)
- POST /api/admin/sessions/kill-all - Emergency shutdown
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.admin.models import (
    ActiveSessionInfo,
    ActiveSessionsResponse,
    FullSessionResponse,
    KillAllResponse,
    SessionKillResponse,
    SessionKillsResponse,
)
from backend.api.dependencies import (
    VerifiedSessionAdmin,
    get_redis_manager,
    get_session_manager,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.validation import validate_session_id
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Sessions"])


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
@handle_api_errors("list active sessions")
async def list_active_sessions(
    top_n: int = Query(10, ge=1, le=100, description="Number of top sessions to return"),
    _admin: str = Depends(require_admin_any),
) -> ActiveSessionsResponse:
    """List all active sessions with stats."""
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
@handle_api_errors("get full session")
async def get_full_session(
    session_id: str,
    metadata: VerifiedSessionAdmin,
) -> FullSessionResponse:
    """Get full session details including all metadata and state.

    Uses VerifiedSessionAdmin dependency which:
    - Validates admin API key
    - Validates session_id format
    - Loads metadata with caching
    - Raises 404 if session not found
    """
    session_manager = get_session_manager()
    redis_manager = get_redis_manager()

    # Load state (metadata already loaded by dependency)
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
        metadata=dict(metadata),
        state=state_dict,
        is_active=is_active,
    )


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
@handle_api_errors("admin kill session")
async def admin_kill_session(
    session_id: str,
    reason: str = Query("Admin terminated", description="Reason for killing session"),
    _admin: str = Depends(require_admin_any),
) -> ControlResponse:
    """Admin kill any session (no ownership check)."""
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
@handle_api_errors("admin kill all sessions")
async def admin_kill_all_sessions(
    confirm: bool = Query(False, description="Must be true to confirm kill-all"),
    reason: str = Query("System maintenance", description="Reason for emergency shutdown"),
    _admin: str = Depends(require_admin_any),
) -> KillAllResponse:
    """Emergency shutdown - kill all active sessions."""
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


@router.get(
    "/sessions/kill-history",
    response_model=SessionKillsResponse,
    summary="Get session kill audit history",
    description="Get the audit trail of all session kills (admin only).",
    responses={
        200: {"description": "Kill history retrieved successfully"},
        401: {"description": "Admin API key required", "model": ErrorResponse},
        403: {"description": "Invalid admin API key", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get session kill history")
async def get_session_kill_history(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    session_id: str | None = Query(None, description="Filter to specific session"),
    _admin: str = Depends(require_admin_any),
) -> SessionKillsResponse:
    """Get session kill audit history."""
    from bo1.state.database import db_session

    # Get total count
    with db_session() as conn:
        with conn.cursor() as cur:
            if session_id:
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM session_kills WHERE session_id = %s",
                    (session_id,),
                )
            else:
                cur.execute("SELECT COUNT(*) as cnt FROM session_kills")
            total = cur.fetchone()["cnt"]

    # Get paginated records
    with db_session() as conn:
        with conn.cursor() as cur:
            if session_id:
                cur.execute(
                    """
                    SELECT id, session_id, killed_by, reason, cost_at_kill,
                           created_at, updated_at
                    FROM session_kills
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (session_id, limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT id, session_id, killed_by, reason, cost_at_kill,
                           created_at, updated_at
                    FROM session_kills
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
            rows = [dict(row) for row in cur.fetchall()]

    kills = [
        SessionKillResponse(
            id=row["id"],
            session_id=row["session_id"],
            killed_by=row["killed_by"],
            reason=row["reason"],
            cost_at_kill=float(row["cost_at_kill"]) if row["cost_at_kill"] else None,
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
            updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        )
        for row in rows
    ]

    logger.info(f"Admin: Retrieved {len(kills)} session kill records")

    return SessionKillsResponse(
        total=total,
        kills=kills,
        limit=limit,
        offset=offset,
    )
