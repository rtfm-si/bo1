"""Deliberation control API endpoints.

Provides:
- POST /api/v1/sessions/{session_id}/start - Start deliberation in background
- POST /api/v1/sessions/{session_id}/pause - Pause deliberation
- POST /api/v1/sessions/{session_id}/resume - Resume from checkpoint
- POST /api/v1/sessions/{session_id}/kill - User kill (ownership check)
- POST /api/v1/sessions/{session_id}/clarify - Submit clarification answer
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.dependencies import (
    VerifiedSession,
    get_redis_manager,
    get_session_manager,
)
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTROL_RATE_LIMIT, limiter
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.validation import validate_session_id
from bo1.data import load_personas
from bo1.graph.config import create_deliberation_graph
from bo1.graph.execution import PermissionError, SessionManager
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.security import check_for_injection
from bo1.state.postgres_manager import update_session_status
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)


async def get_checkpointer() -> Any:
    """Get an initialized AsyncRedisSaver checkpointer.

    Creates and sets up the checkpointer with required Redis indexes.
    This must be called before using the checkpointer for state operations.

    Returns:
        Initialized AsyncRedisSaver instance
    """
    import os

    from langgraph.checkpoint.redis.aio import AsyncRedisSaver

    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_password = os.getenv("REDIS_PASSWORD", "")

    if redis_password:
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    checkpointer = AsyncRedisSaver(redis_url)
    # Setup creates required Redis search indexes
    await checkpointer.asetup()
    return checkpointer


async def load_state_from_checkpoint(session_id: str) -> dict[str, Any] | None:
    """Load deliberation state from LangGraph checkpoint, with PostgreSQL fallback.

    Uses the LangGraph checkpoint system (AsyncRedisSaver) to retrieve
    the most recent state for a session. If checkpoint is missing (e.g., Redis
    restart, TTL expiry), attempts to reconstruct minimal state from PostgreSQL
    events for sessions paused awaiting clarification.

    Args:
        session_id: Session identifier (used as thread_id in checkpoint)

    Returns:
        State dict if checkpoint exists or can be reconstructed, None otherwise
    """
    try:
        # Get initialized checkpointer
        checkpointer = await get_checkpointer()

        # Create graph with the initialized checkpointer
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Config uses thread_id to identify the checkpoint
        config = {"configurable": {"thread_id": session_id}}

        # Load state from checkpoint
        checkpoint_state = await graph.aget_state(config)

        if checkpoint_state and checkpoint_state.values:
            logger.debug(f"Loaded state from checkpoint for session {session_id}")
            return dict(checkpoint_state.values)

        logger.info(
            f"No checkpoint found for session {session_id}, attempting PostgreSQL reconstruction"
        )

    except Exception as e:
        logger.warning(
            f"Failed to load checkpoint for {session_id}: {e}, attempting PostgreSQL reconstruction"
        )

    # Fallback: Reconstruct state from PostgreSQL events
    # This handles cases where Redis checkpoint expired but session is paused for clarification
    return _reconstruct_state_from_postgres(session_id)


def _reconstruct_state_from_postgres(session_id: str) -> dict[str, Any] | None:
    """Reconstruct minimal deliberation state from PostgreSQL events.

    Used when LangGraph checkpoint is missing but session data exists in PostgreSQL.
    Reconstructs enough state to resume from clarification pause point.

    Args:
        session_id: Session identifier

    Returns:
        Reconstructed state dict, or None if reconstruction not possible
    """
    from bo1.models.problem import Problem, SubProblem
    from bo1.state.postgres_manager import db_session, get_session_events

    try:
        # Get session metadata
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT problem_statement, status, phase
                       FROM sessions WHERE id = %s""",
                    (session_id,),
                )
                session_row = cur.fetchone()

        if not session_row:
            logger.warning(f"Session {session_id} not found in PostgreSQL")
            return None

        # Only reconstruct for sessions paused for clarification
        if session_row["status"] != "paused" or session_row["phase"] != "clarification_needed":
            logger.warning(
                f"Session {session_id} not in clarification state "
                f"(status={session_row['status']}, phase={session_row['phase']})"
            )
            return None

        # Get events to reconstruct state
        events = get_session_events(session_id)
        if not events:
            logger.warning(f"No events found for session {session_id}")
            return None

        # Find decomposition_complete event for sub_problems
        decomp_event = None
        clarification_event = None
        for event in events:
            event_type = event.get("event_type") or event.get("data", {}).get("event_type")
            if event_type == "decomposition_complete":
                decomp_event = event
            elif event_type == "clarification_required":
                clarification_event = event

        if not decomp_event:
            logger.warning(f"No decomposition_complete event for session {session_id}")
            return None

        # Extract sub_problems from decomposition event
        decomp_data = decomp_event.get("data", {})
        if isinstance(decomp_data, dict) and "data" in decomp_data:
            decomp_data = decomp_data["data"]  # Handle nested structure

        sub_problems_data = decomp_data.get("sub_problems", [])

        # Build Problem object
        sub_problems = [
            SubProblem(
                id=sp.get("id", f"sp_{i:03d}"),
                goal=sp.get("goal", ""),
                context=sp.get("context") or "",  # Default empty string if None
                rationale=sp.get("rationale") or "",
                dependencies=sp.get("dependencies", []),
                complexity_score=sp.get("complexity_score", 5),
            )
            for i, sp in enumerate(sub_problems_data)
        ]

        problem_description = session_row["problem_statement"] or ""
        problem = Problem(
            title=problem_description[:100],  # Use first 100 chars as title
            description=problem_description,
            context="",  # Context not stored separately, may be in description
            sub_problems=sub_problems,
        )

        # Extract pending_clarification from clarification event
        pending_clarification = None
        if clarification_event:
            clar_data = clarification_event.get("data", {})
            if isinstance(clar_data, dict) and "data" in clar_data:
                clar_data = clar_data["data"]  # Handle nested structure
            pending_clarification = {
                "questions": clar_data.get("questions", []),
                "phase": clar_data.get("phase", "pre_deliberation"),
                "reason": clar_data.get("reason", ""),
            }

        # Reconstruct minimal state needed to resume from clarification
        reconstructed_state = {
            "problem": problem,
            "sub_problem_index": 0,
            "round_number": 0,
            "should_stop": True,
            "stop_reason": "clarification_needed",
            "pending_clarification": pending_clarification,
            "current_node": "identify_gaps",
            "personas": [],
            "contributions": [],
            "metrics": {},
        }

        logger.info(
            f"Reconstructed state for session {session_id} from PostgreSQL "
            f"(sub_problems={len(sub_problems)}, has_clarification={pending_clarification is not None})"
        )

        return reconstructed_state

    except Exception as e:
        logger.error(f"Failed to reconstruct state from PostgreSQL for {session_id}: {e}")
        return None


async def save_state_to_checkpoint(session_id: str, state: dict[str, Any]) -> bool:
    """Save deliberation state to LangGraph checkpoint.

    Updates the checkpoint with new state values. This is used when
    modifying state outside of normal graph execution (e.g., adding
    clarification answers).

    Args:
        session_id: Session identifier (used as thread_id in checkpoint)
        state: State dict to save

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Get initialized checkpointer
        checkpointer = await get_checkpointer()

        # Create graph with the initialized checkpointer
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Config uses thread_id to identify the checkpoint
        config = {"configurable": {"thread_id": session_id}}

        # Update state using graph's update_state method
        # This preserves checkpoint history and metadata
        await graph.aupdate_state(config, state)

        logger.debug(f"Saved state to checkpoint for session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to save state to checkpoint for {session_id}: {e}")
        return False


router = APIRouter(prefix="/v1/sessions", tags=["deliberation-control"])


class ClarificationRequest(BaseModel):
    """Request model for clarification answers.

    Supports both single answer (legacy) and multiple answers (new).

    Attributes:
        answer: Single answer to clarification question (legacy, optional)
        answers: Dict of question->answer pairs (new, optional)
        skip: Whether to skip all questions without answering
    """

    answer: str | None = Field(
        None,
        max_length=5000,
        description="Single answer to clarification question (legacy)",
        examples=["Our current churn rate is 3.5% monthly"],
    )
    answers: dict[str, str] | None = Field(
        None,
        description="Dict of question->answer pairs for multiple questions",
        examples=[
            {"What is your monthly churn rate?": "3.5%", "What is your current ARR?": "$500K"}
        ],
    )
    skip: bool = Field(
        False,
        description="Skip all questions without answering",
    )


class KillRequest(BaseModel):
    """Request model for killing a session.

    Attributes:
        reason: Reason for killing the session (optional)
    """

    reason: str | None = Field(
        None,
        max_length=500,
        description="Reason for killing the session",
        examples=["User requested stop"],
    )


@router.post(
    "/{session_id}/start",
    response_model=ControlResponse,
    status_code=202,
    summary="Start deliberation in background",
    description="Start a deliberation session as a background task. Returns 202 Accepted immediately.",
    responses={
        202: {"description": "Deliberation started in background"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        409: {"description": "Session already running", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("start deliberation")
async def start_deliberation(
    request: Request,
    session_id: str,
    session_data: VerifiedSession,
    session_manager: SessionManager = Depends(get_session_manager),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Start deliberation in background.

    This endpoint starts a deliberation session as an asyncio background task.
    The task is tracked in SessionManager.active_executions.

    Args:
        request: FastAPI request object for rate limiting
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        session_manager: Session manager instance
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with 202 Accepted

    Raises:
        HTTPException: If session not found, already running, or start fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Unpack verified session data
        user_id, metadata = session_data

        # Check if already running
        if session_id in session_manager.active_executions:
            raise HTTPException(
                status_code=409,
                detail=f"Session {session_id} is already running",
            )

        # Validate session status
        status = metadata.get("status")
        if status not in ["created", "paused"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot start session with status: {status}",
            )

        # Load problem from metadata
        # Problem model expects title, description, and context as string
        problem_statement = metadata.get("problem_statement", "")
        problem_context = metadata.get("problem_context", {})

        # Convert context dict to string if needed
        import json

        context_str = (
            json.dumps(problem_context)
            if isinstance(problem_context, dict)
            else str(problem_context)
        )

        problem = Problem(
            title=problem_statement[:100] if len(problem_statement) > 100 else problem_statement,
            description=problem_statement,
            context=context_str,
        )

        # Load personas (for MVP, we'll use a default set)
        # TODO(Week 7+): Load personas from session metadata or user selection
        all_personas = load_personas()  # Returns tuple of dicts
        # Select first 3 personas as default for MVP and convert to PersonaProfile objects
        from bo1.models.persona import PersonaProfile

        personas = [PersonaProfile(**p) for p in all_personas[:3]]

        # Create initial state
        state = create_initial_state(
            session_id=session_id,
            problem=problem,
            personas=personas,
            max_rounds=6,  # Hard cap for parallel architecture
        )

        # Create graph
        graph = create_deliberation_graph()

        # Create event collector for real-time streaming
        from backend.api.dependencies import get_event_publisher
        from backend.api.event_collector import EventCollector

        event_collector = EventCollector(get_event_publisher())

        # Create coroutine with event collection
        from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": DELIBERATION_RECURSION_LIMIT,
        }
        coro = event_collector.collect_and_publish(session_id, graph, state, config)

        # Start background task
        await session_manager.start_session(session_id, user_id, coro)

        # Send ntfy notification (fire and forget)
        import asyncio

        from backend.api.ntfy import notify_meeting_started

        asyncio.create_task(notify_meeting_started(session_id, problem_statement))

        # Update session status to 'running' in PostgreSQL
        try:
            update_session_status(session_id=session_id, status="running")
            logger.info(
                f"Started deliberation for session {session_id} (status updated in PostgreSQL)"
            )
        except Exception as e:
            logger.error(f"Failed to update session status in PostgreSQL: {e}")
            # Don't fail the request - session is running in Redis

        return ControlResponse(
            session_id=session_id,
            action="start",
            status="success",
            message="Deliberation started in background",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start deliberation for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start deliberation: {str(e)}",
        ) from e


@router.post(
    "/{session_id}/pause",
    response_model=ControlResponse,
    summary="Pause deliberation",
    description="Pause a running deliberation session. Checkpoint is auto-saved by LangGraph.",
    responses={
        200: {"description": "Deliberation paused successfully"},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("pause deliberation")
async def pause_deliberation(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Pause a running deliberation.

    This marks the session as paused in metadata. LangGraph automatically
    saves checkpoints, so the state is preserved.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with pause confirmation

    Raises:
        HTTPException: If session not found or pause fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Unpack verified session data
        user_id, metadata = session_data

        # Update metadata to mark as paused
        now = datetime.now(UTC)
        metadata["status"] = "paused"
        metadata["paused_at"] = now.isoformat()
        metadata["updated_at"] = now.isoformat()

        redis_manager.save_metadata(session_id, metadata)

        logger.info(f"Paused deliberation for session {session_id}")

        return ControlResponse(
            session_id=session_id,
            action="pause",
            status="success",
            message="Deliberation paused - checkpoint saved",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause deliberation for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to pause deliberation: {str(e)}",
        ) from e


@router.post(
    "/{session_id}/resume",
    response_model=ControlResponse,
    status_code=202,
    summary="Resume deliberation from checkpoint",
    description="Resume a paused deliberation session from its last checkpoint.",
    responses={
        202: {"description": "Deliberation resumed in background"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("resume deliberation")
async def resume_deliberation(
    session_id: str,
    session_data: VerifiedSession,
    session_manager: SessionManager = Depends(get_session_manager),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Resume a paused deliberation from checkpoint.

    Loads the checkpoint from Redis and continues graph execution.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        session_manager: Session manager instance
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with resume confirmation

    Raises:
        HTTPException: If session not found or resume fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Unpack verified session data
        user_id, metadata = session_data

        # Validate session status
        status = metadata.get("status")
        if status != "paused":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot resume session with status: {status}. Session must be paused.",
            )

        # Check if already running
        if session_id in session_manager.active_executions:
            raise HTTPException(
                status_code=409,
                detail=f"Session {session_id} is already running",
            )

        # Create graph
        graph = create_deliberation_graph()

        # Create event collector for real-time streaming
        from backend.api.dependencies import get_event_publisher
        from backend.api.event_collector import EventCollector

        event_collector = EventCollector(get_event_publisher())

        # Resume from checkpoint (pass None as state to continue from checkpoint)
        from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": DELIBERATION_RECURSION_LIMIT,
        }
        coro = event_collector.collect_and_publish(session_id, graph, None, config)

        # Start background task
        await session_manager.start_session(session_id, user_id, coro)

        # Update metadata
        now = datetime.now(UTC)
        metadata["status"] = "running"
        metadata["resumed_at"] = now.isoformat()
        metadata["updated_at"] = now.isoformat()
        redis_manager.save_metadata(session_id, metadata)

        logger.info(f"Resumed deliberation for session {session_id}")

        return ControlResponse(
            session_id=session_id,
            action="resume",
            status="success",
            message="Deliberation resumed from checkpoint",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume deliberation for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume deliberation: {str(e)}",
        ) from e


@router.post(
    "/{session_id}/kill",
    response_model=ControlResponse,
    summary="Kill deliberation",
    description="Kill a running deliberation session. Requires user ownership of the session.",
    responses={
        200: {"description": "Deliberation killed successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("kill deliberation")
async def kill_deliberation(
    request: Request,
    session_id: str,
    kill_request: KillRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> ControlResponse:
    """Kill a running deliberation (user must own the session).

    This cancels the background task and logs the termination in an audit trail.

    Args:
        request: FastAPI request object for rate limiting
        session_id: Session identifier
        kill_request: Optional kill request with reason
        user: Authenticated user data

    Returns:
        ControlResponse with kill confirmation

    Raises:
        HTTPException: If session not found, user doesn't own it, or kill fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        user_id = extract_user_id(user)
        session_manager = get_session_manager()

        reason = (
            kill_request.reason if kill_request and kill_request.reason else None
        ) or "User requested stop"

        # Attempt to kill the session (with ownership check)
        killed = await session_manager.kill_session(session_id, user_id, reason)

        if not killed:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found or not running: {session_id}",
            )

        # Update session status to 'killed' in PostgreSQL
        try:
            update_session_status(session_id=session_id, status="killed")
            logger.info(
                f"Killed deliberation for session {session_id}. Reason: {reason} (status updated in PostgreSQL)"
            )
        except Exception as e:
            logger.error(f"Failed to update killed session status in PostgreSQL: {e}")
            # Don't fail the request - session is already killed

        return ControlResponse(
            session_id=session_id,
            action="kill",
            status="success",
            message=f"Deliberation killed. Reason: {reason}",
        )

    except PermissionError as e:
        logger.warning(f"Permission denied to kill session {session_id}: {e}")
        raise HTTPException(
            status_code=403,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to kill deliberation for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to kill deliberation: {str(e)}",
        ) from e


class ClarificationResponse(BaseModel):
    """Response model for clarification questions.

    Attributes:
        session_id: Session identifier
        has_pending: Whether there's a pending clarification
        question: The clarification question (if pending)
        reason: Why clarification is needed (if pending)
        question_id: Unique ID for the question (if pending)
    """

    session_id: str
    has_pending: bool
    question: str | None = None
    reason: str | None = None
    question_id: str | None = None


@router.get(
    "/{session_id}/clarifications",
    response_model=ClarificationResponse,
    summary="Get pending clarification question",
    description="Check if there's a pending clarification question for this session.",
    responses={
        200: {"description": "Clarification status returned"},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("get pending clarification")
async def get_pending_clarification(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ClarificationResponse:
    """Get pending clarification question for a session.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        ClarificationResponse with pending question details or empty if none
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Unpack verified session data
        user_id, metadata = session_data

        # Check for pending clarification
        pending = metadata.get("pending_clarification")

        if pending:
            return ClarificationResponse(
                session_id=session_id,
                has_pending=True,
                question=pending.get("question"),
                reason=pending.get("reason"),
                question_id=pending.get("question_id"),
            )
        else:
            return ClarificationResponse(
                session_id=session_id,
                has_pending=False,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get clarification for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get clarification: {str(e)}",
        ) from e


@router.post(
    "/{session_id}/clarifications",
    response_model=ControlResponse,
    status_code=202,
    summary="Submit clarification answer",
    description="Submit an answer to a pending clarification question and resume deliberation.",
    responses={
        202: {"description": "Clarification submitted, deliberation resumed"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("submit clarification")
async def submit_clarification_new(
    session_id: str,
    request: ClarificationRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Submit clarification answer and resume deliberation (new endpoint).

    This is the preferred endpoint at POST /sessions/{id}/clarifications.
    """
    return await _submit_clarification_impl(session_id, request, session_data, redis_manager)


@router.post(
    "/{session_id}/clarify",
    response_model=ControlResponse,
    status_code=202,
    summary="Submit clarification answer (legacy)",
    description="Submit an answer to a pending clarification question and resume deliberation.",
    responses={
        202: {"description": "Clarification submitted, deliberation resumed"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    deprecated=True,
)
async def submit_clarification(
    session_id: str,
    request: ClarificationRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Submit clarification answer (legacy endpoint, use POST /clarifications instead)."""
    return await _submit_clarification_impl(session_id, request, session_data, redis_manager)


async def _submit_clarification_impl(
    session_id: str,
    request: ClarificationRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager,
) -> ControlResponse:
    """Submit clarification answer and resume deliberation.

    This endpoint:
    1. Validates user owns the session
    2. Checks session has a pending clarification
    3. Injects answer into problem context
    4. Resumes deliberation from checkpoint

    Args:
        session_id: Session identifier
        request: Clarification answer
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with resume confirmation

    Raises:
        HTTPException: If session not found, no pending clarification, or submission fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Unpack verified session data
        user_id, metadata = session_data

        # Handle skip request
        if request.skip:
            logger.info(f"User skipped clarification questions for session {session_id}")
            # Clear pending clarification and allow resume
            metadata["pending_clarification"] = None
            metadata["status"] = "paused"
            metadata["updated_at"] = datetime.now(UTC).isoformat()
            redis_manager.save_metadata(session_id, metadata)

            return ControlResponse(
                session_id=session_id,
                action="clarify",
                status="success",
                message="Questions skipped. Session ready to resume.",
            )

        # Get answers - support both legacy single answer and new multiple answers
        answers_to_process: dict[str, str] = {}
        if request.answers:
            answers_to_process = request.answers
        elif request.answer:
            # Legacy single answer - need to get question from pending_clarification
            pending_clarification = metadata.get("pending_clarification", {})
            question = pending_clarification.get("question", "Clarification")
            answers_to_process = {question: request.answer}

        if not answers_to_process:
            raise HTTPException(
                status_code=400,
                detail="No answers provided. Use 'answers' dict or 'skip': true",
            )

        # Prompt injection audit on all answers
        for _question, answer in answers_to_process.items():
            await check_for_injection(
                content=answer,
                source="clarification_answer",
                raise_on_unsafe=True,
            )

        # Load state from LangGraph checkpoint (authoritative source during deliberation)
        state = await load_state_from_checkpoint(session_id)
        if not state:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load state from checkpoint for session {session_id}. "
                "The session may have expired or the checkpoint may be unavailable.",
            )

        # Inject clarification answers into problem context
        if "problem" not in state:
            state["problem"] = {}

        # Build context string from answers
        clarification_context = "\n\n## Clarification Answers\n"
        for question, answer in answers_to_process.items():
            clarification_context += f"- **Q:** {question}\n  **A:** {answer}\n"

        # Append to existing context - handle both dict and object problem formats
        problem = state["problem"]
        if isinstance(problem, dict):
            existing_context = problem.get("context", "") or ""
            problem["context"] = existing_context + clarification_context
        elif hasattr(problem, "context"):
            problem.context = (problem.context or "") + clarification_context
        else:
            # Fallback: create new problem dict
            state["problem"] = {"context": clarification_context}

        # Store answers in state for identify_gaps_node to see
        state["clarification_answers"] = answers_to_process

        # Save updated state to checkpoint
        if not await save_state_to_checkpoint(session_id, state):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save updated state to checkpoint for session {session_id}",
            )

        # Clear pending clarification from metadata
        metadata["pending_clarification"] = None
        metadata["status"] = "paused"  # Mark as paused, ready to resume
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        redis_manager.save_metadata(session_id, metadata)

        # ISSUE #4 FIX: Persist clarification answers to user's business context
        # This ensures future meetings can benefit from the clarifications
        try:
            from bo1.state.postgres_manager import load_user_context, save_user_context

            # Load existing business context
            existing_context = load_user_context(user_id) or {}

            # Add/update clarifications section
            clarifications = existing_context.get("clarifications", {})
            for question, answer in answers_to_process.items():
                clarifications[question] = {
                    "answer": answer,
                    "answered_at": datetime.now(UTC).isoformat(),
                    "session_id": session_id,
                }
            existing_context["clarifications"] = clarifications

            # Save updated context
            save_user_context(user_id, existing_context)
            logger.info(
                f"Persisted {len(answers_to_process)} clarification(s) to business context "
                f"for user {user_id}"
            )
        except Exception as e:
            # Don't fail the request if business context persistence fails
            logger.warning(f"Failed to persist clarification to business context: {e}")

        logger.info(
            f"Clarification submitted for session {session_id}. "
            f"Answered {len(answers_to_process)} question(s)"
        )

        # Note: We return 202 but don't auto-resume. User must call /resume endpoint.
        # This gives them control over when to continue.
        return ControlResponse(
            session_id=session_id,
            action="clarify",
            status="success",
            message=f"Clarification submitted ({len(answers_to_process)} answer(s)). Session ready to resume.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit clarification for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit clarification: {str(e)}",
        ) from e
