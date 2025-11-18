"""Admin API endpoints for Board of One.

Provides:
- GET /api/admin/sessions/active - List all active sessions
- GET /api/admin/sessions/{session_id}/full - Full session details
- POST /api/admin/sessions/{session_id}/kill - Admin kill (no ownership check)
- POST /api/admin/sessions/kill-all - Emergency shutdown
- GET /api/admin/beta-whitelist - List all whitelisted emails
- POST /api/admin/beta-whitelist - Add email to whitelist
- DELETE /api/admin/beta-whitelist/{email} - Remove email from whitelist
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_redis_manager, get_session_manager
from backend.api.middleware.admin import require_admin
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.validation import validate_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


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
    _admin_key: str = Depends(require_admin),
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
    _admin_key: str = Depends(require_admin),
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
    _admin_key: str = Depends(require_admin),
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
    _admin_key: str = Depends(require_admin),
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
        from bo1.state.postgres_manager import get_connection

        with get_connection() as conn:
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
    _admin_key: str = Depends(require_admin),
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
        from bo1.state.postgres_manager import get_connection

        # Normalize email
        email = request.email.strip().lower()

        # Simple email validation
        if "@" not in email or "." not in email.split("@")[1]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email address: {email}",
            )

        with get_connection() as conn:
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
                conn.commit()

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
    _admin_key: str = Depends(require_admin),
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
        from bo1.state.postgres_manager import get_connection

        # Normalize email
        email = email.strip().lower()

        with get_connection() as conn:
            with conn.cursor() as cur:
                # Delete email
                cur.execute("DELETE FROM beta_whitelist WHERE email = %s RETURNING id", (email,))
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Email not found in whitelist: {email}",
                    )

                conn.commit()

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
