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
from backend.api.utils.validation import validate_session_id
from bo1.data import load_personas
from bo1.graph.config import create_deliberation_graph
from bo1.graph.execution import PermissionError, SessionManager
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.state.postgres_manager import update_session_status
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["deliberation-control"])


class ClarificationRequest(BaseModel):
    """Request model for clarification answer.

    Attributes:
        answer: User's answer to the clarification question
    """

    answer: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Answer to clarification question",
        examples=["Our current churn rate is 3.5% monthly"],
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
async def kill_deliberation(
    request: Request,
    session_id: str,
    kill_request: KillRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> ControlResponse:
    """Kill a running deliberation (user must own the session).

    This cancels the background task and logs the termination in an audit trail.

    Args:
        session_id: Session identifier
        request: Optional kill request with reason
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


@router.post(
    "/{session_id}/clarify",
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
async def submit_clarification(
    session_id: str,
    request: ClarificationRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
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

        # Check for pending clarification
        pending_clarification = metadata.get("pending_clarification")
        if not pending_clarification:
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} has no pending clarification",
            )

        # Load state and inject answer into problem context
        state = redis_manager.load_state(session_id)
        if not state:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load state for session {session_id}",
            )

        # Convert state to dict if it's a DeliberationState
        if not isinstance(state, dict):
            state = state.model_dump() if hasattr(state, "model_dump") else {}

        # Inject clarification answer into problem context
        if "problem" not in state:
            state["problem"] = {}
        if "context" not in state["problem"]:
            state["problem"]["context"] = {}

        # Add clarification to context
        clarification_key = f"clarification_{pending_clarification['question_id']}"
        state["problem"]["context"][clarification_key] = request.answer

        # Save updated state
        redis_manager.save_state(session_id, state)

        # Clear pending clarification from metadata
        metadata["pending_clarification"] = None
        metadata["status"] = "paused"  # Mark as paused, ready to resume
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        redis_manager.save_metadata(session_id, metadata)

        logger.info(
            f"Clarification submitted for session {session_id}. "
            f"Question: {pending_clarification.get('question', 'N/A')}"
        )

        # Note: We return 202 but don't auto-resume. User must call /resume endpoint.
        # This gives them control over when to continue.
        return ControlResponse(
            session_id=session_id,
            action="clarify",
            status="success",
            message="Clarification submitted. Session ready to resume.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit clarification for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit clarification: {str(e)}",
        ) from e
