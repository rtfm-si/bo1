"""Session management API endpoints.

Provides:
- POST /api/v1/sessions - Create new deliberation session
- GET /api/v1/sessions - List user's sessions
- GET /api/v1/sessions/{session_id} - Get session details
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import (
    VerifiedSession,
    get_redis_manager,
    get_session_manager,
)
from backend.api.metrics import track_api_call
from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    CreateSessionRequest,
    ErrorResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
)
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, raise_api_error
from backend.api.utils.text import truncate_text
from backend.api.utils.validation import validate_session_id
from bo1.agents.task_extractor import sync_extract_tasks_from_synthesis
from bo1.graph.execution import SessionManager
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=201,
    summary="Create new deliberation session",
    description="Create a new deliberation session with the given problem statement and context.",
    responses={
        201: {"description": "Session created successfully"},
        400: {
            "description": "Invalid request",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
@handle_api_errors("create session")
async def create_session(
    request: CreateSessionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> SessionResponse:
    """Create a new deliberation session.

    This endpoint creates a new session with a unique identifier and saves
    the initial state to Redis. The session is ready to be started via the
    /start endpoint.

    Args:
        request: Session creation request
        user: Authenticated user data

    Returns:
        SessionResponse with session details

    Raises:
        HTTPException: If session creation fails
    """
    with track_api_call("sessions.create", "POST"):
        # Create Redis manager
        redis_manager = get_redis_manager()

        if not redis_manager.is_available:
            raise_api_error("redis_unavailable")

        # Extract user ID from authenticated user
        user_id = extract_user_id(user)

        # Generate session ID
        session_id = redis_manager.create_session()

        # Create initial metadata
        now = datetime.now(UTC)
        metadata = {
            "status": "created",
            "phase": None,
            "user_id": user_id,  # SECURITY: Track session ownership
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "problem_statement": request.problem_statement,
            "problem_context": request.problem_context or {},
        }

        # Save metadata to Redis
        if not redis_manager.save_metadata(session_id, metadata):
            raise RuntimeError("Failed to save session metadata")

        # Add session to user's session index for fast lookup
        redis_manager.add_session_to_user_index(user_id, session_id)

        logger.info(f"Created session: {session_id} for user: {user_id}")

        # Return session response
        return SessionResponse(
            id=session_id,
            status="created",
            phase=None,
            created_at=now,
            updated_at=now,
            problem_statement=truncate_text(request.problem_statement),
            cost=None,
        )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List user's sessions",
    description="List all deliberation sessions for the current user (paginated).",
    responses={
        200: {"description": "Sessions retrieved successfully"},
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def list_sessions(
    user: dict[str, Any] = Depends(get_current_user),
    status: str | None = Query(
        None, description="Filter by status (active, completed, failed, paused)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
) -> SessionListResponse:
    """List user's deliberation sessions.

    Returns a paginated list of sessions with metadata. Full session state
    can be retrieved via the GET /sessions/{session_id} endpoint.

    Args:
        user: Authenticated user data
        status: Optional status filter
        limit: Page size (1-100)
        offset: Page offset

    Returns:
        SessionListResponse with list of sessions

    Raises:
        HTTPException: If listing fails
    """
    with track_api_call("sessions.list", "GET"):
        try:
            # Extract user ID from authenticated user
            user_id = extract_user_id(user)

            # Create Redis manager
            redis_manager = get_redis_manager()

            if not redis_manager.is_available:
                # Return empty list if Redis is unavailable
                return SessionListResponse(
                    sessions=[],
                    total=0,
                    limit=limit,
                    offset=offset,
                )

            # Get session IDs for this user only (uses Redis SET - O(1) lookup)
            session_ids = redis_manager.list_user_sessions(user_id)

            if not session_ids:
                return SessionListResponse(
                    sessions=[],
                    total=0,
                    limit=limit,
                    offset=offset,
                )

            # Batch load metadata for all user sessions (single Redis pipeline)
            metadata_dict = redis_manager.batch_load_metadata(session_ids)

            # Build session list from metadata
            sessions: list[SessionResponse] = []
            for session_id, metadata in metadata_dict.items():
                # Skip soft-deleted sessions
                if metadata.get("deleted_at"):
                    continue

                # Apply status filter
                if status and metadata.get("status") != status:
                    continue

                # Parse timestamps
                try:
                    created_at = datetime.fromisoformat(metadata["created_at"])
                    updated_at = datetime.fromisoformat(metadata["updated_at"])
                    last_activity_at = (
                        datetime.fromisoformat(metadata["last_activity_at"])
                        if metadata.get("last_activity_at")
                        else None
                    )
                except (KeyError, ValueError):
                    # Skip sessions with invalid timestamps
                    logger.warning(f"Invalid timestamps for session {session_id}")
                    continue

                # Create session response
                session = SessionResponse(
                    id=session_id,
                    status=metadata.get("status", "unknown"),
                    phase=metadata.get("phase"),
                    created_at=created_at,
                    updated_at=updated_at,
                    last_activity_at=last_activity_at,
                    problem_statement=truncate_text(
                        metadata.get("problem_statement", "Unknown problem")
                    ),
                    cost=metadata.get("cost"),
                )
                sessions.append(session)

            # Sort by updated_at descending (most recent first)
            sessions.sort(key=lambda s: s.updated_at, reverse=True)

            # Apply pagination
            total = len(sessions)
            paginated_sessions = sessions[offset : offset + limit]

            return SessionListResponse(
                sessions=paginated_sessions,
                total=total,
                limit=limit,
                offset=offset,
            )

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list sessions: {str(e)}",
            ) from e


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session details",
    description="Get detailed information about a specific deliberation session.",
    responses={
        200: {"description": "Session details retrieved successfully"},
        404: {
            "description": "Session not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_session(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> SessionDetailResponse:
    """Get detailed information about a session.

    Returns full session state including deliberation progress, contributions,
    metrics, and costs.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        SessionDetailResponse with full session details

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    with track_api_call("sessions.get", "GET"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Load full state (if available)
            state = redis_manager.load_state(session_id)

            # Parse timestamps
            try:
                created_at = datetime.fromisoformat(metadata["created_at"])
                updated_at = datetime.fromisoformat(metadata["updated_at"])
            except (KeyError, ValueError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid session metadata: {e}",
                ) from e

            # Build problem details
            problem_dict = {
                "statement": metadata.get("problem_statement", ""),
                "context": metadata.get("problem_context", {}),
            }

            # Convert state to dict if it's a DeliberationState
            state_dict: dict[str, Any] | None = None
            if state:
                if isinstance(state, dict):
                    state_dict = state
                else:
                    # Convert DeliberationState to dict
                    state_dict = state.model_dump() if hasattr(state, "model_dump") else None

            # Extract metrics from state if available
            metrics = None
            if state_dict:
                metrics = {
                    "round_number": state_dict.get("round_number", 0),
                    "total_cost": state_dict.get("total_cost", 0.0),
                    "phase_costs": state_dict.get("phase_costs", {}),
                    "contributions_count": len(state_dict.get("contributions", [])),
                }

            return SessionDetailResponse(
                id=session_id,
                status=metadata.get("status", "unknown"),
                phase=metadata.get("phase"),
                created_at=created_at,
                updated_at=updated_at,
                problem=problem_dict,
                state=state_dict,
                metrics=metrics,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get session: {str(e)}",
            ) from e


@router.delete(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Soft delete a session",
    description="Soft delete a deliberation session. Automatically kills any active executions. Session data is retained but hidden from lists.",
    responses={
        200: {"description": "Session soft deleted successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def delete_session(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionResponse:
    """Soft delete a session.

    This endpoint:
    1. Verifies user owns the session
    2. Kills any active execution
    3. Marks the session as soft deleted with deleted_at timestamp
    4. Updates session status to "deleted"

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance
        session_manager: Session manager instance

    Returns:
        SessionResponse with deleted status

    Raises:
        HTTPException: If session not found or user doesn't own it
    """
    with track_api_call("sessions.delete", "DELETE"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Check if already deleted
            if metadata.get("deleted_at"):
                raise HTTPException(
                    status_code=404,
                    detail=f"Session already deleted: {session_id}",
                )

            # Kill any active execution
            if session_id in session_manager.active_executions:
                try:
                    await session_manager.kill_session(session_id, user_id, "User deleted session")
                    logger.info(f"Killed active execution for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to kill active execution: {e}")
                    # Continue with soft delete even if kill fails

            # Update metadata with soft delete
            now = datetime.now(UTC)
            metadata["status"] = "deleted"
            metadata["deleted_at"] = now.isoformat()
            metadata["updated_at"] = now.isoformat()

            # Save updated metadata
            if not redis_manager.save_metadata(session_id, metadata):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update session metadata",
                )

            # Remove session from user's index for fast listing
            redis_manager.remove_session_from_user_index(user_id, session_id)

            logger.info(f"Soft deleted session: {session_id} for user: {user_id}")

            # Return session response
            return SessionResponse(
                id=session_id,
                status="deleted",
                phase=metadata.get("phase"),
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=now,
                problem_statement=truncate_text(
                    metadata.get("problem_statement", "Unknown problem")
                ),
                cost=metadata.get("cost"),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete session: {str(e)}",
            ) from e


@router.post(
    "/{session_id}/extract-tasks",
    summary="Extract actionable tasks from synthesis",
    description="Extract discrete, actionable tasks from session synthesis using AI.",
    responses={
        200: {"description": "Tasks extracted successfully"},
        404: {"description": "Session or synthesis not found", "model": ErrorResponse},
        500: {"description": "Task extraction failed", "model": ErrorResponse},
    },
)
async def extract_tasks(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> dict[str, Any]:
    """Extract actionable tasks from session synthesis.

    This endpoint:
    1. Retrieves the synthesis from session metadata
    2. Uses Claude to extract discrete, actionable tasks
    3. Returns tasks with priorities, dates, and dependencies

    Args:
        session_id: Session ID
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        Dict with extracted tasks and metadata

    Raises:
        HTTPException: If synthesis not found or extraction fails
    """
    with track_api_call("sessions.extract_tasks", "POST"):
        try:
            # Validate session ID format
            if not validate_session_id(session_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid session ID format",
                )

            # Unpack verified session data
            user_id, metadata = session_data

            # Check if synthesis exists
            synthesis = metadata.get("synthesis")
            if not synthesis:
                # Try to get synthesis from events
                events_key = f"events_history:{session_id}"
                events = redis_manager.redis.lrange(events_key, 0, -1)

                # Look for synthesis_complete or meta_synthesis_complete event
                synthesis = None
                for event_json in events:
                    import json

                    event = json.loads(event_json)
                    if event.get("event_type") in [
                        "synthesis_complete",
                        "meta_synthesis_complete",
                    ]:
                        synthesis = event.get("data", {}).get("synthesis")
                        if synthesis:
                            break

                if not synthesis:
                    raise HTTPException(
                        status_code=404,
                        detail="No synthesis found for this session. Run the deliberation to completion first.",
                    )

            # Extract tasks using AI
            logger.info(f"Extracting tasks from synthesis for session {session_id}")

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="AI service not configured",
                )

            result = sync_extract_tasks_from_synthesis(
                synthesis=synthesis,
                session_id=session_id,
                anthropic_api_key=api_key,
            )

            logger.info(
                f"Extracted {result.total_tasks} tasks from session {session_id} "
                f"(confidence: {result.extraction_confidence:.2f})"
            )

            # Return task extraction result
            return result.model_dump()

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to extract tasks for session {session_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Task extraction failed: {str(e)}",
            ) from e
