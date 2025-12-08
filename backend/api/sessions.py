"""Session management API endpoints.

Provides:
- POST /api/v1/sessions - Create new deliberation session
- GET /api/v1/sessions - List user's sessions
- GET /api/v1/sessions/{session_id} - Get session details
"""

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.dependencies import (
    VerifiedSession,
    get_redis_manager,
    get_session_manager,
)
from backend.api.metrics import track_api_call
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import SESSION_RATE_LIMIT, limiter, user_rate_limiter
from backend.api.models import (
    CreateSessionRequest,
    ErrorResponse,
    SessionActionsResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    TaskStatusUpdate,
    TaskWithStatus,
)
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, raise_api_error
from backend.api.utils.text import truncate_text
from backend.api.utils.validation import validate_session_id
from bo1.agents.task_extractor import sync_extract_tasks_from_synthesis
from bo1.graph.execution import SessionManager
from bo1.security import check_for_injection
from bo1.state.redis_manager import RedisManager
from bo1.state.repositories.session_repository import session_repository
from bo1.state.repositories.user_repository import user_repository
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

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
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
@limiter.limit(SESSION_RATE_LIMIT)
@handle_api_errors("create session")
async def create_session(
    request: Request,
    session_request: CreateSessionRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> SessionResponse:
    """Create a new deliberation session.

    This endpoint creates a new session with a unique identifier and saves
    the initial state to Redis. The session is ready to be started via the
    /start endpoint.

    Args:
        request: FastAPI request object for rate limiting
        session_request: Session creation request with problem statement
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

        # User-based rate limiting (prevents free tier abuse)
        # This runs AFTER auth, checking per-user limits in Redis
        subscription_tier = user.get("subscription_tier", "free")
        await user_rate_limiter.check_limit(
            user_id=user_id,
            action="session_create",
            limit=5,  # 5 meetings/minute for free tier
            window_seconds=60,
            tier=subscription_tier,
        )

        # Prompt injection audit (LLM-based detection)
        # Checks problem statement for injection attempts before processing
        await check_for_injection(
            content=session_request.problem_statement,
            source="problem_statement",
            raise_on_unsafe=True,
        )

        # Generate session ID
        session_id = redis_manager.create_session()

        # Fetch user's business context and merge with request context
        # User context provides business background, request context can override/add specifics
        merged_context: dict[str, Any] = {}
        try:
            user_context = user_repository.get_context(user_id)
            if user_context:
                # Include relevant business context fields
                context_fields = [
                    "company_name",
                    "business_model",
                    "target_market",
                    "product_description",
                    "business_stage",
                    "primary_objective",
                    "industry",
                    "competitors",
                    "revenue",
                    "customers",
                    "growth_rate",
                    "website",
                    "pricing_model",
                    "brand_positioning",
                    "ideal_customer_profile",
                    "team_size",
                    "budget_constraints",
                    "time_constraints",
                    "regulatory_constraints",
                ]
                for field in context_fields:
                    if field in user_context and user_context[field]:
                        merged_context[field] = user_context[field]
                logger.debug(
                    f"Injected {len(merged_context)} business context fields for user {user_id}"
                )
        except Exception as e:
            logger.warning(f"Failed to load user context for session creation: {e}")

        # Merge request context (overrides user context if same keys)
        if session_request.problem_context:
            merged_context.update(session_request.problem_context)

        # Create initial metadata
        now = datetime.now(UTC)
        metadata = {
            "status": "created",
            "phase": None,
            "user_id": user_id,  # SECURITY: Track session ownership
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "problem_statement": session_request.problem_statement,
            "problem_context": merged_context,
        }

        # Save metadata to Redis (for live state and fast lookup)
        if not redis_manager.save_metadata(session_id, metadata):
            raise RuntimeError("Failed to save session metadata")

        # Add session to user's session index for fast lookup
        redis_manager.add_session_to_user_index(user_id, session_id)

        # Save session to PostgreSQL for permanent storage
        # CRITICAL: PostgreSQL is the primary storage - failure should abort the request
        try:
            # Safety net: Ensure user exists in PostgreSQL (FK constraint requires this)
            # Primary sync happens in SuperTokens sign_in_up() override (supertokens_config.py)
            # This is a fallback for edge cases where OAuth sync failed or for direct API calls
            user_email = user.get("email") if user else None
            user_repository.ensure_exists(
                user_id=user_id,
                email=user_email,
                auth_provider="supertokens",  # Unknown at this point, use generic
                subscription_tier=user.get("subscription_tier", "free") if user else "free",
            )

            session_repository.create(
                session_id=session_id,
                user_id=user_id,
                problem_statement=session_request.problem_statement,
                problem_context=merged_context if merged_context else None,
                status="created",
            )
            logger.info(
                f"Created session: {session_id} for user: {user_id} (saved to both Redis and PostgreSQL)"
            )
        except Exception as e:
            # PostgreSQL is primary storage - propagate error to client
            logger.error(f"Failed to save session to PostgreSQL: {e}", exc_info=True)
            # Clean up Redis state since PostgreSQL failed
            try:
                redis_manager.delete_session(session_id)
                redis_manager.remove_session_from_user_index(user_id, session_id)
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up Redis after PostgreSQL failure: {cleanup_error}"
                )
            raise HTTPException(
                status_code=500,
                detail="Failed to create session. Please try again.",
            ) from e

        # Return session response
        return SessionResponse(
            id=session_id,
            status="created",
            phase=None,
            created_at=now,
            updated_at=now,
            problem_statement=truncate_text(session_request.problem_statement),
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

            # PRIMARY SOURCE: Query PostgreSQL for persistent session records
            try:
                pg_sessions = session_repository.list_by_user(
                    user_id=user_id,
                    limit=limit,
                    offset=offset,
                    status_filter=status,
                )
                logger.debug(
                    f"Loaded {len(pg_sessions)} sessions from PostgreSQL for user {user_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load sessions from PostgreSQL: {e}, falling back to Redis"
                )
                pg_sessions = []

            # If Postgres returned sessions, enrich with Redis live state
            if pg_sessions:
                # Create Redis manager for enrichment
                redis_manager = get_redis_manager()

                sessions: list[SessionResponse] = []
                for pg_session in pg_sessions:
                    session_id = pg_session["id"]

                    # Try to enrich with live metadata from Redis (if available)
                    redis_metadata = None
                    if redis_manager.is_available:
                        redis_metadata = redis_manager.load_metadata(session_id)

                    # Use Redis data if available and more recent, otherwise use Postgres
                    if redis_metadata:
                        # Check if Redis has newer data (e.g., for active sessions)
                        redis_updated = redis_metadata.get("updated_at")
                        pg_updated = (
                            pg_session["updated_at"].isoformat()
                            if pg_session["updated_at"]
                            else None
                        )

                        use_redis = redis_updated and pg_updated and redis_updated > pg_updated
                        status_val = (
                            redis_metadata.get("status") if use_redis else pg_session["status"]
                        )
                        phase_val = (
                            redis_metadata.get("phase") if use_redis else pg_session["phase"]
                        )
                        cost_val = (
                            redis_metadata.get("cost")
                            if use_redis
                            else pg_session.get("total_cost")
                        )
                        last_activity_at = (
                            datetime.fromisoformat(redis_metadata["last_activity_at"])
                            if redis_metadata.get("last_activity_at")
                            else None
                        )
                    else:
                        # Use Postgres data only
                        status_val = pg_session["status"]
                        phase_val = pg_session["phase"]
                        cost_val = pg_session.get("total_cost")
                        last_activity_at = None

                    # Create session response with summary counts
                    session = SessionResponse(
                        id=session_id,
                        status=status_val,
                        phase=phase_val,
                        created_at=pg_session["created_at"],
                        updated_at=pg_session["updated_at"],
                        last_activity_at=last_activity_at,
                        problem_statement=truncate_text(pg_session["problem_statement"]),
                        cost=cost_val,
                        # Summary counts for dashboard cards
                        expert_count=pg_session.get("expert_count"),
                        contribution_count=pg_session.get("contribution_count"),
                        task_count=pg_session.get("task_count"),
                        focus_area_count=pg_session.get("focus_area_count"),
                    )
                    sessions.append(session)

                # Total is already filtered by status in Postgres query
                # For accurate pagination, we'd need a count query, but this approximation works
                total = len(sessions)

                return SessionListResponse(
                    sessions=sessions,
                    total=total,
                    limit=limit,
                    offset=offset,
                )

            # FALLBACK: If Postgres failed or returned empty, try Redis
            redis_manager = get_redis_manager()

            if not redis_manager.is_available:
                # No data available from either source
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
            sessions_fallback: list[SessionResponse] = []
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
                sessions_fallback.append(session)

            # Sort by updated_at descending (most recent first)
            sessions_fallback.sort(key=lambda s: s.updated_at, reverse=True)

            # Apply pagination
            total_fallback = len(sessions_fallback)
            paginated_sessions = sessions_fallback[offset : offset + limit]

            logger.info(
                f"Returning {len(paginated_sessions)} sessions from Redis fallback for user {user_id}"
            )

            return SessionListResponse(
                sessions=paginated_sessions,
                total=total_fallback,
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

            # Also update PostgreSQL status to ensure consistency
            try:
                session_repository.update_status(session_id=session_id, status="deleted")
            except Exception as pg_err:
                logger.warning(f"Failed to update PostgreSQL status for {session_id}: {pg_err}")
                # Continue - Redis is the source of truth for active sessions

            # P1-006: Cascade soft delete to actions
            try:
                from bo1.state.repositories.action_repository import ActionRepository

                action_repo = ActionRepository()
                deleted_actions = action_repo.soft_delete_by_session(session_id)
                if deleted_actions > 0:
                    logger.info(
                        f"Cascade soft-deleted {deleted_actions} actions for session {session_id}"
                    )
            except Exception as cascade_err:
                logger.warning(f"Failed to cascade delete actions for {session_id}: {cascade_err}")
                # Continue - session delete should still succeed

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

            # 1. Check PostgreSQL first for persistent storage (survives Redis expiry)
            try:
                db_tasks = session_repository.get_tasks(session_id)
                if db_tasks:
                    logger.info(f"Returning tasks from PostgreSQL for session {session_id}")
                    return {
                        "tasks": db_tasks["tasks"],
                        "total_tasks": db_tasks["total_tasks"],
                        "extraction_confidence": float(db_tasks["extraction_confidence"]),
                        "synthesis_sections_analyzed": db_tasks["synthesis_sections_analyzed"],
                    }
            except Exception as e:
                logger.warning(
                    f"Failed to load tasks from PostgreSQL: {e}, falling back to extraction"
                )

            # 2. Check Redis cache as fallback (for backwards compatibility)
            cache_key = f"extracted_tasks:{session_id}"
            cached_tasks = redis_manager.redis.get(cache_key)

            if cached_tasks:
                import json

                logger.info(f"Returning cached tasks from Redis for session {session_id}")
                cached_data = json.loads(cached_tasks)

                # Backfill to PostgreSQL if not already there (fixes missing task counts)
                try:
                    session_repository.save_tasks(
                        session_id=session_id,
                        tasks=cached_data.get("tasks", []),
                        total_tasks=cached_data.get("total_tasks", 0),
                        extraction_confidence=cached_data.get("extraction_confidence", 0.0),
                        synthesis_sections_analyzed=cached_data.get(
                            "synthesis_sections_analyzed", []
                        ),
                    )
                    logger.info(f"Backfilled tasks to PostgreSQL for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to backfill tasks to PostgreSQL: {e}")

                return cached_data

            # Extract tasks from ALL synthesis events (sub-problems + meta-synthesis)
            # This ensures tasks are associated with their respective sub-problems
            # Try Redis first (for active sessions), fall back to PostgreSQL (for completed sessions)
            events_key = f"events_history:{session_id}"
            redis_events = redis_manager.redis.lrange(events_key, 0, -1)

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="AI service not configured",
                )

            # Collect all synthesis events
            synthesis_events: list[tuple[str, int | None]] = []  # (synthesis, sub_problem_index)

            # Parse events from Redis (JSON strings) or PostgreSQL (dicts)
            if redis_events:
                logger.info(
                    f"Reading {len(redis_events)} events from Redis for session {session_id}"
                )
                for event_json in redis_events:
                    import json

                    event = json.loads(event_json)
                    event_type = event.get("event_type")
                    event_data = event.get("data", {})
                    if event_type == "synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        sub_problem_index = event_data.get("sub_problem_index")
                        if synthesis:
                            synthesis_events.append((synthesis, sub_problem_index))
                    elif event_type == "meta_synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        if synthesis:
                            synthesis_events.append((synthesis, None))
            else:
                # Fall back to PostgreSQL for completed sessions where Redis expired
                logger.info(f"Redis empty, reading events from PostgreSQL for session {session_id}")
                pg_events = session_repository.get_events(session_id)
                for event in pg_events:
                    event_type = event.get("event_type")
                    # PostgreSQL data column has nested structure: {"data": {...payload...}, ...}
                    full_data = event.get("data", {})
                    event_data = full_data.get("data", {}) if isinstance(full_data, dict) else {}
                    if event_type == "synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        sub_problem_index = event_data.get("sub_problem_index")
                        if synthesis:
                            synthesis_events.append((synthesis, sub_problem_index))
                    elif event_type == "meta_synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        if synthesis:
                            synthesis_events.append((synthesis, None))

            if not synthesis_events:
                raise HTTPException(
                    status_code=404,
                    detail="No synthesis found for this session. Run the deliberation to completion first.",
                )

            # Build sub-problem context for cross-sub-problem dependency extraction
            # Filter to get only sub-problem syntheses (not meta-synthesis)
            sub_problem_syntheses = [(s, idx) for s, idx in synthesis_events if idx is not None]
            total_sub_problems = len(sub_problem_syntheses)

            # Build goal map from decomposition_complete event (if available)
            sub_problem_goals: dict[int, str] = {}
            for event_json in redis_events or []:
                try:
                    import json as json_mod

                    event = (
                        json_mod.loads(event_json)
                        if isinstance(event_json, (str, bytes))
                        else event_json
                    )
                    if event.get("event_type") == "decomposition_complete":
                        for idx, sp in enumerate(event.get("data", {}).get("sub_problems", [])):
                            sub_problem_goals[idx] = sp.get("goal", f"Sub-problem {idx + 1}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to parse event JSON: {e}")
                    continue

            # Extract tasks from each synthesis and tag with sub_problem_index
            all_tasks: list[dict[str, Any]] = []
            all_sections_analyzed: list[str] = []
            total_confidence_sum = 0.0
            tasks_by_sp: dict[int | None, int] = {}  # Track task count per sub-problem

            for synthesis, sub_problem_index in synthesis_events:
                logger.info(
                    f"Extracting tasks from synthesis (sub_problem_index={sub_problem_index}) "
                    f"for session {session_id}"
                )

                # Build context for other sub-problems (for cross-sp dependencies)
                other_goals = [
                    f"[sp{idx}] {goal}"
                    for idx, goal in sub_problem_goals.items()
                    if idx != sub_problem_index
                ]

                result = sync_extract_tasks_from_synthesis(
                    synthesis=synthesis,
                    session_id=session_id,
                    anthropic_api_key=api_key,
                    sub_problem_index=sub_problem_index,
                    total_sub_problems=total_sub_problems,
                    other_sub_problem_goals=other_goals,
                )

                # Tag each task with its sub_problem_index
                task_count = 0
                for task in result.tasks:
                    task_dict = task.model_dump() if hasattr(task, "model_dump") else task
                    task_dict["sub_problem_index"] = sub_problem_index
                    all_tasks.append(task_dict)
                    task_count += 1

                # Track task count per sub-problem for validation
                tasks_by_sp[sub_problem_index] = task_count

                all_sections_analyzed.extend(result.synthesis_sections_analyzed)
                total_confidence_sum += result.extraction_confidence

            # ISSUE #2 FIX: Validation that all sub-problems have tasks extracted
            sp_indices_with_tasks = {idx for idx in tasks_by_sp.keys() if idx is not None}
            expected_sp_indices = set(range(total_sub_problems))
            missing_sp_indices = expected_sp_indices - sp_indices_with_tasks

            if missing_sp_indices:
                logger.warning(
                    f"TASK EXTRACTION WARNING: Sub-problems {sorted(missing_sp_indices)} "
                    f"have no tasks extracted for session {session_id}. "
                    f"Tasks by sub-problem: {tasks_by_sp}"
                )

            # Log task distribution for debugging
            logger.info(f"Task distribution by sub-problem for session {session_id}: {tasks_by_sp}")

            # Calculate average confidence across all syntheses
            avg_confidence = (
                total_confidence_sum / len(synthesis_events) if synthesis_events else 0.0
            )

            logger.info(
                f"Extracted {len(all_tasks)} tasks total from {len(synthesis_events)} "
                f"synthesis events for session {session_id} (avg confidence: {avg_confidence:.2f})"
            )

            # Prepare result dictionary
            result_dict = {
                "tasks": all_tasks,
                "total_tasks": len(all_tasks),
                "extraction_confidence": avg_confidence,
                "synthesis_sections_analyzed": list(set(all_sections_analyzed)),
            }

            # 1. Save to PostgreSQL for long-term persistence (PRIMARY storage)
            try:
                session_repository.save_tasks(
                    session_id=session_id,
                    tasks=all_tasks,
                    total_tasks=len(all_tasks),
                    extraction_confidence=avg_confidence,
                    synthesis_sections_analyzed=list(set(all_sections_analyzed)),
                )
                logger.info(f"Saved extracted tasks to PostgreSQL for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to save tasks to PostgreSQL: {e}")

            # 2. Cache in Redis with 24-hour TTL (SECONDARY cache for speed)
            try:
                import json

                redis_manager.redis.setex(cache_key, 86400, json.dumps(result_dict))
                logger.info(f"Cached extracted tasks in Redis for session {session_id} (24h TTL)")
            except Exception as e:
                logger.warning(f"Failed to cache tasks in Redis: {e}")

            # Return task extraction result
            return result_dict

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to extract tasks for session {session_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Task extraction failed: {str(e)}",
            ) from e


# =============================================================================
# Action/Task Endpoints (Kanban)
# =============================================================================


def _tasks_with_statuses(
    tasks: list[dict[str, Any]], task_statuses: dict[str, str]
) -> list[TaskWithStatus]:
    """Merge tasks with their statuses.

    Args:
        tasks: List of task dictionaries
        task_statuses: Mapping of task_id -> status

    Returns:
        List of TaskWithStatus objects
    """
    result = []
    for task in tasks:
        task_id = task.get("id", "")
        status = task_statuses.get(task_id, "todo")  # Default to "todo"
        result.append(
            TaskWithStatus(
                id=task_id,
                title=task.get("title", ""),
                description=task.get("description", ""),
                what_and_how=task.get("what_and_how", []),
                success_criteria=task.get("success_criteria", []),
                kill_criteria=task.get("kill_criteria", []),
                dependencies=task.get("dependencies", []),
                timeline=task.get("timeline", ""),
                priority=task.get("priority", "medium"),
                category=task.get("category", "implementation"),
                source_section=task.get("source_section"),
                confidence=task.get("confidence", 0.0),
                sub_problem_index=task.get("sub_problem_index"),
                status=status,
            )
        )
    return result


def _count_by_status(tasks: list[TaskWithStatus]) -> dict[str, int]:
    """Count tasks by status.

    Args:
        tasks: List of tasks with statuses

    Returns:
        Dict mapping status -> count
    """
    counts = {"todo": 0, "doing": 0, "done": 0}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
    return counts


@router.get(
    "/{session_id}/actions",
    response_model=SessionActionsResponse,
    summary="Get session actions with statuses",
    description="Get all extracted tasks for a session with their Kanban statuses.",
    responses={
        200: {"description": "Actions retrieved successfully"},
        404: {"description": "Session or tasks not found", "model": ErrorResponse},
    },
)
async def get_session_actions(
    session_id: str,
    session_data: VerifiedSession,
) -> SessionActionsResponse:
    """Get all actions/tasks for a session with their statuses.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        SessionActionsResponse with tasks and status counts
    """
    with track_api_call("sessions.get_actions", "GET"):
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Get tasks from database
        task_record = session_repository.get_tasks(session_id)

        if not task_record:
            raise HTTPException(
                status_code=404,
                detail="No tasks found for this session. Extract tasks first using POST /sessions/{id}/extract-tasks",
            )

        # Merge tasks with statuses
        tasks = task_record.get("tasks", [])
        task_statuses = task_record.get("task_statuses", {}) or {}

        tasks_with_status = _tasks_with_statuses(tasks, task_statuses)
        by_status = _count_by_status(tasks_with_status)

        return SessionActionsResponse(
            session_id=session_id,
            tasks=tasks_with_status,
            total_tasks=len(tasks_with_status),
            by_status=by_status,
        )


@router.patch(
    "/{session_id}/actions/{task_id}",
    response_model=dict[str, str],
    summary="Update task status",
    description="Update the Kanban status of a specific task.",
    responses={
        200: {"description": "Status updated successfully"},
        400: {"description": "Invalid status", "model": ErrorResponse},
        404: {"description": "Session or task not found", "model": ErrorResponse},
    },
)
async def update_task_status(
    session_id: str,
    task_id: str,
    status_update: TaskStatusUpdate,
    session_data: VerifiedSession,
) -> dict[str, str]:
    """Update the status of a task in a session.

    Args:
        session_id: Session identifier
        task_id: Task identifier (e.g., "task_1")
        status_update: New status
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        Success message
    """
    with track_api_call("sessions.update_task_status", "PATCH"):
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Validate task_id format (should be "task_N")
        if not task_id or not task_id.startswith("task_"):
            raise HTTPException(
                status_code=400,
                detail="Invalid task ID format. Expected 'task_N' format.",
            )

        # Update task status in database
        try:
            success = session_repository.update_task_status(
                session_id=session_id,
                task_id=task_id,
                status=status_update.status,
            )

            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found or no tasks extracted",
                )

            logger.info(
                f"Updated task {task_id} status to {status_update.status} for session {session_id}"
            )

            return {
                "status": "success",
                "message": f"Task {task_id} status updated to {status_update.status}",
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
