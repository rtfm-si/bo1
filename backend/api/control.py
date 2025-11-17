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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.dependencies import get_redis_manager, get_session_manager
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils.validation import validate_session_id, validate_user_id
from bo1.data import load_personas
from bo1.graph.config import create_deliberation_graph
from bo1.graph.execution import PermissionError
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["deliberation-control"])


def _get_user_id_from_header() -> str:
    """Get user ID from request header.

    For MVP, we'll use a hardcoded user ID. In production (Week 7+),
    this will extract user ID from JWT token.

    Returns:
        User ID string
    """
    # TODO(Week 7): Extract from JWT token
    # For now, use a test user ID
    user_id = "test_user_1"

    # Validate user ID format (prevents injection even with hardcoded value)
    return validate_user_id(user_id)


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
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def start_deliberation(session_id: str) -> ControlResponse:
    """Start deliberation in background.

    This endpoint starts a deliberation session as an asyncio background task.
    The task is tracked in SessionManager.active_executions.

    Args:
        session_id: Session identifier

    Returns:
        ControlResponse with 202 Accepted

    Raises:
        HTTPException: If session not found, already running, or start fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        user_id = _get_user_id_from_header()
        session_manager = get_session_manager()
        redis_manager = get_redis_manager()

        # Check if session exists
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

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
        # Select first 3 personas as default for MVP
        personas = [
            {"code": p["code"], "name": p["name"], "system_prompt": p["system_prompt"]}
            for p in all_personas[:3]
        ]

        # Create initial state
        state = create_initial_state(
            session_id=session_id,
            problem=problem,
            personas=personas,
            max_rounds=10,
        )

        # Create graph
        graph = create_deliberation_graph()

        # Create coroutine
        config = {"configurable": {"thread_id": session_id}}
        coro = graph.ainvoke(state, config=config)

        # Start background task
        await session_manager.start_session(session_id, user_id, coro)

        logger.info(f"Started deliberation for session {session_id}")

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
async def pause_deliberation(session_id: str) -> ControlResponse:
    """Pause a running deliberation.

    This marks the session as paused in metadata. LangGraph automatically
    saves checkpoints, so the state is preserved.

    Args:
        session_id: Session identifier

    Returns:
        ControlResponse with pause confirmation

    Raises:
        HTTPException: If session not found or pause fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        redis_manager = get_redis_manager()

        # Check if session exists
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

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
async def resume_deliberation(session_id: str) -> ControlResponse:
    """Resume a paused deliberation from checkpoint.

    Loads the checkpoint from Redis and continues graph execution.

    Args:
        session_id: Session identifier

    Returns:
        ControlResponse with resume confirmation

    Raises:
        HTTPException: If session not found or resume fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        user_id = _get_user_id_from_header()
        session_manager = get_session_manager()
        redis_manager = get_redis_manager()

        # Check if session exists
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

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

        # Resume from checkpoint (pass None as state to continue from checkpoint)
        config = {"configurable": {"thread_id": session_id}}
        coro = graph.ainvoke(None, config=config)

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
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def kill_deliberation(session_id: str, request: KillRequest | None = None) -> ControlResponse:
    """Kill a running deliberation (user must own the session).

    This cancels the background task and logs the termination in an audit trail.

    Args:
        session_id: Session identifier
        request: Optional kill request with reason

    Returns:
        ControlResponse with kill confirmation

    Raises:
        HTTPException: If session not found, user doesn't own it, or kill fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        user_id = _get_user_id_from_header()
        session_manager = get_session_manager()

        reason = request.reason if request else "User requested stop"

        # Attempt to kill the session (with ownership check)
        killed = await session_manager.kill_session(session_id, user_id, reason)

        if not killed:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found or not running: {session_id}",
            )

        logger.info(f"Killed deliberation for session {session_id}. Reason: {reason}")

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

    Returns:
        ControlResponse with resume confirmation

    Raises:
        HTTPException: If session not found, no pending clarification, or submission fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        user_id = _get_user_id_from_header()
        redis_manager = get_redis_manager()

        # Check if session exists
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

        # Check ownership
        if metadata.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail=f"User {user_id} does not own session {session_id}",
            )

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
