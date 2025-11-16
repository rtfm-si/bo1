"""Admin API endpoints for Board of One.

Provides:
- GET /api/admin/sessions/active - List all active sessions
- GET /api/admin/sessions/{session_id}/full - Full session details
- POST /api/admin/sessions/{session_id}/kill - Admin kill (no ownership check)
- POST /api/admin/sessions/kill-all - Emergency shutdown
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin
from backend.api.models import ControlResponse, ErrorResponse
from bo1.graph.execution import SessionManager
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# Global session manager (initialized on first use)
_session_manager: SessionManager | None = None


def _get_session_manager() -> SessionManager:
    """Get or create the global session manager.

    Returns:
        SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        redis_manager = RedisManager()
        # For admin endpoints, we use a special admin user ID
        _session_manager = SessionManager(redis_manager, admin_user_ids={"admin"})
    return _session_manager


def _create_redis_manager() -> RedisManager:
    """Create Redis manager instance.

    Returns:
        RedisManager instance
    """
    return RedisManager()


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

    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User who owns the session")
    status: str = Field(..., description="Current session status")
    phase: str | None = Field(None, description="Current deliberation phase")
    started_at: str = Field(..., description="When session started (ISO 8601)")
    duration_seconds: float = Field(..., description="How long session has been running")
    cost: float | None = Field(None, description="Total cost so far (USD)")


class ActiveSessionsResponse(BaseModel):
    """Response model for active sessions list.

    Attributes:
        active_count: Number of active sessions
        sessions: List of active session info
        longest_running: Top N longest running sessions
        most_expensive: Top N most expensive sessions
    """

    active_count: int = Field(..., description="Number of active sessions")
    sessions: list[ActiveSessionInfo] = Field(..., description="List of active sessions")
    longest_running: list[ActiveSessionInfo] = Field(
        ..., description="Top N longest running sessions"
    )
    most_expensive: list[ActiveSessionInfo] = Field(
        ..., description="Top N most expensive sessions"
    )


class FullSessionResponse(BaseModel):
    """Response model for full session details.

    Attributes:
        session_id: Session identifier
        metadata: Full session metadata
        state: Full deliberation state
        is_active: Whether session is currently running
    """

    session_id: str = Field(..., description="Session identifier")
    metadata: dict = Field(..., description="Full session metadata")
    state: dict | None = Field(None, description="Full deliberation state")
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
    _admin_key: str = Depends(require_admin),
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
        session_manager = _get_session_manager()
        redis_manager = _create_redis_manager()

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
    _admin_key: str = Depends(require_admin),
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
        session_manager = _get_session_manager()
        redis_manager = _create_redis_manager()

        # Load metadata
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

        # Load state
        state = redis_manager.load_state(session_id)

        # Check if active
        is_active = session_id in session_manager.active_executions

        logger.info(f"Admin: Retrieved full session {session_id}")

        return FullSessionResponse(
            session_id=session_id,
            metadata=metadata,
            state=state,
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
    _admin_key: str = Depends(require_admin),
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
        session_manager = _get_session_manager()

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
    _admin_key: str = Depends(require_admin),
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

        session_manager = _get_session_manager()

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
