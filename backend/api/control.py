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
from pydantic import BaseModel, Field, field_validator

from backend.api.dependencies import (
    VerifiedSession,
    get_redis_manager,
    get_session_manager,
    get_session_metadata_cache,
)
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTROL_RATE_LIMIT, limiter
from backend.api.models import ControlResponse, ErrorResponse
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
    ERROR_409_RESPONSE,
    ERROR_500_RESPONSE,
)
from backend.api.utils.validation import validate_session_id
from bo1.data import load_personas
from bo1.graph.config import create_deliberation_graph
from bo1.graph.execution import PermissionError, SessionManager
from bo1.graph.state import create_initial_state
from bo1.logging.errors import ErrorCode, log_error
from bo1.models.problem import Problem
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.security import check_for_injection
from bo1.state.database import db_session
from bo1.state.redis_lock import LockTimeout, session_lock
from bo1.state.redis_manager import RedisManager
from bo1.state.repositories import session_repository
from bo1.utils.async_context import create_task_with_context

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
            state = dict(checkpoint_state.values)

            # Validate sub_problems exist (critical for deliberation)
            problem = state.get("problem")
            if problem:
                sub_problems = (
                    problem.get("sub_problems", [])
                    if isinstance(problem, dict)
                    else getattr(problem, "sub_problems", [])
                )
                if not sub_problems:
                    logger.warning(
                        f"Checkpoint for {session_id} has empty sub_problems, "
                        f"falling back to PostgreSQL reconstruction"
                    )
                    return _reconstruct_state_from_postgres(session_id)

            logger.debug(f"Loaded state from checkpoint for session {session_id}")
            return state

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


def _recover_problem_from_postgres(session_id: str) -> Any:
    """Recover Problem object with sub_problems from PostgreSQL events.

    Used when LangGraph checkpoint lost sub_problems during serialization.
    This function does NOT check session status/phase - it just recovers the problem.

    Args:
        session_id: Session identifier

    Returns:
        Problem object with sub_problems, or None if not found
    """
    from bo1.models.problem import Problem, SubProblem
    from bo1.state.repositories import session_repository

    try:
        # Get session metadata for problem_statement
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT problem_statement FROM sessions WHERE id = %s""",
                    (session_id,),
                )
                session_row = cur.fetchone()

        if not session_row:
            logger.warning(f"Session {session_id} not found in PostgreSQL for problem recovery")
            return None

        # Get events to find decomposition_complete
        events = session_repository.get_events(session_id)
        if not events:
            logger.warning(f"No events found for session {session_id}")
            return None

        # Find decomposition_complete event for sub_problems
        decomp_event = None
        for event in events:
            event_type = event.get("event_type") or event.get("data", {}).get("event_type")
            if event_type == "decomposition_complete":
                decomp_event = event
                break

        if not decomp_event:
            logger.warning(f"No decomposition_complete event for session {session_id}")
            return None

        # Extract sub_problems from decomposition event
        decomp_data = decomp_event.get("data", {})
        if isinstance(decomp_data, dict) and "data" in decomp_data:
            decomp_data = decomp_data["data"]  # Handle nested structure

        sub_problems_data = decomp_data.get("sub_problems", [])
        if not sub_problems_data:
            logger.warning(f"decomposition_complete event has no sub_problems for {session_id}")
            return None

        # Build Problem object with sub_problems
        sub_problems = [
            SubProblem(
                id=sp.get("id", f"sp_{i:03d}"),
                goal=sp.get("goal", ""),
                context=sp.get("context") or "",
                rationale=sp.get("rationale") or "",
                dependencies=sp.get("dependencies", []),
                complexity_score=sp.get("complexity_score", 5),
            )
            for i, sp in enumerate(sub_problems_data)
        ]

        problem_description = session_row["problem_statement"] or ""
        problem = Problem(
            title=problem_description[:100],
            description=problem_description,
            context="",
            sub_problems=sub_problems,
        )

        logger.info(
            f"Recovered problem from PostgreSQL for {session_id}: {len(sub_problems)} sub_problems"
        )
        return problem

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to recover problem from PostgreSQL for {session_id}: {e}",
            session_id=session_id,
        )
        return None


def _reconstruct_state_from_postgres(
    session_id: str,
    allow_failed: bool = False,
) -> dict[str, Any] | None:
    """Reconstruct minimal deliberation state from PostgreSQL events and metadata.

    Used when LangGraph checkpoint is missing but session data exists in PostgreSQL.
    Reconstructs enough state to resume from clarification pause point or retry failed.

    Leverages denormalized session metadata (phase, round_number, expert_count,
    contribution_count, focus_area_count) for more complete state reconstruction
    when Redis checkpoint is unavailable.

    Args:
        session_id: Session identifier
        allow_failed: If True, also allows reconstruction of failed sessions (for retry)

    Returns:
        Reconstructed state dict, or None if reconstruction not possible
    """
    from bo1.models.problem import Problem, SubProblem
    from bo1.state.repositories import session_repository

    try:
        # Get session metadata including denormalized counts
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT problem_statement, problem_context, status, phase,
                              round_number, expert_count, contribution_count,
                              focus_area_count
                       FROM sessions WHERE id = %s""",
                    (session_id,),
                )
                session_row = cur.fetchone()

        if not session_row:
            logger.warning(f"Session {session_id} not found in PostgreSQL")
            return None

        status = session_row["status"]
        phase = session_row["phase"]

        # Determine valid reconstruction states
        valid_for_reconstruction = (status == "paused" and phase == "clarification_needed") or (
            allow_failed and status == "failed"
        )

        if not valid_for_reconstruction:
            logger.warning(
                f"Session {session_id} not in reconstructable state "
                f"(status={status}, phase={phase}, allow_failed={allow_failed})"
            )
            return None

        # Get events to reconstruct state
        events = session_repository.get_events(session_id)
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

        # Create proper metrics object (not a dict)
        from bo1.models.state import DeliberationMetrics

        metrics = DeliberationMetrics()

        # Use denormalized metadata for better reconstruction
        round_number = session_row.get("round_number", 0) or 0
        problem_context = session_row.get("problem_context") or {}

        # Get sub_problem_index from problem_context if persisted by fallback
        sub_problem_index = 0
        if isinstance(problem_context, dict):
            sub_problem_index = problem_context.get("sub_problem_index", 0) or 0

        # Determine stop_reason based on status
        stop_reason = "clarification_needed" if status == "paused" else "failed"

        # Reconstruct minimal state needed to resume from clarification or retry
        reconstructed_state = {
            "problem": problem,
            "sub_problem_index": sub_problem_index,
            "round_number": round_number,
            "should_stop": True,
            "stop_reason": stop_reason,
            "pending_clarification": pending_clarification,
            "current_node": phase or "identify_gaps",
            "current_phase": phase or "exploration",
            "personas": [],
            "contributions": [],
            "metrics": metrics,
        }

        logger.info(
            f"Reconstructed state for session {session_id} from PostgreSQL "
            f"(sub_problems={len(sub_problems)}, round={round_number}, "
            f"phase={phase}, has_clarification={pending_clarification is not None})"
        )

        return reconstructed_state

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to reconstruct state from PostgreSQL for {session_id}: {e}",
            session_id=session_id,
        )
        return None


async def save_state_to_checkpoint(
    session_id: str, state: dict[str, Any], as_node: str | None = None
) -> bool:
    """Save deliberation state to LangGraph checkpoint.

    Updates the checkpoint with new state values. This is used when
    modifying state outside of normal graph execution (e.g., adding
    clarification answers).

    Args:
        session_id: Session identifier (used as thread_id in checkpoint)
        state: State dict to save
        as_node: Optional node name to attribute this update to. When set,
                 LangGraph will resume from the edge AFTER this node. This is
                 critical for clarification flow - setting as_node="identify_gaps"
                 tells LangGraph to run the router after identify_gaps on resume.

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        from bo1.graph.state import serialize_state_for_checkpoint

        # Serialize Pydantic models before saving
        serialized_state = serialize_state_for_checkpoint(state)

        # Get initialized checkpointer
        checkpointer = await get_checkpointer()

        # Create graph with the initialized checkpointer
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Config uses thread_id to identify the checkpoint
        config = {"configurable": {"thread_id": session_id}}

        # Update state using graph's update_state method
        # as_node parameter tells LangGraph which node this update is "from"
        # so it knows where to resume execution
        await graph.aupdate_state(config, serialized_state, as_node=as_node)

        logger.debug(
            f"Saved state to checkpoint for session {session_id}"
            + (f" (as_node={as_node})" if as_node else "")
        )
        return True

    except Exception as e:
        log_error(
            logger,
            ErrorCode.GRAPH_CHECKPOINT_ERROR,
            f"Failed to save state to checkpoint for {session_id}: {e}",
            session_id=session_id,
        )
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
        description="Dict of question->answer pairs for multiple questions (max 5000 chars per answer)",
        examples=[
            {"What is your monthly churn rate?": "3.5%", "What is your current ARR?": "$500K"}
        ],
    )
    skip: bool = Field(
        False,
        description="Skip all questions without answering",
    )

    @field_validator("answers")
    @classmethod
    def validate_answer_lengths(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate that each answer in the dict doesn't exceed max length."""
        if v is None:
            return v
        max_len = 5000
        for question, answer in v.items():
            if len(answer) > max_len:
                raise ValueError(f"Answer for '{question[:50]}...' exceeds {max_len} characters")
        return v


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
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
        403: ERROR_403_RESPONSE,
        409: ERROR_409_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
        500: ERROR_500_RESPONSE,
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

        # Beta meeting cap check (only for new starts, not resumes)
        status = metadata.get("status")
        if status == "created":
            from backend.services.meeting_cap import MeetingCapExceededError, require_meeting_cap

            try:
                cap_status = require_meeting_cap(user_id)
                logger.info(
                    f"Meeting cap check passed for user {user_id}: "
                    f"{cap_status.remaining}/{cap_status.limit} remaining"
                )
            except MeetingCapExceededError as e:
                logger.warning(f"Meeting cap exceeded for user {user_id}: {e}")
                raise http_error(
                    ErrorCode.API_RATE_LIMIT,
                    str(e),
                    status=429,
                    reset_time=(e.status.reset_time.isoformat() if e.status.reset_time else None),
                    limit=e.status.limit,
                    remaining=0,
                ) from e

        # Check if already running
        if session_id in session_manager.active_executions:
            raise http_error(
                ErrorCode.API_CONFLICT,
                f"Session {session_id} is already running",
                status=409,
            )

        # Validate session status (status already loaded above for cap check)
        if status not in ["created", "paused"]:
            raise http_error(
                ErrorCode.API_BAD_REQUEST,
                f"Cannot start session with status: {status}",
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

        # Load user preferences (skip_clarification, subscription_tier)
        skip_clarification = False
        subscription_tier = "free"
        research_sharing_consented = False
        try:
            from bo1.state.database import db_session

            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT skip_clarification, subscription_tier FROM users WHERE id = %s",
                        (user_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        if row.get("skip_clarification"):
                            skip_clarification = True
                            logger.info(f"User {user_id} has skip_clarification=True")
                        if row.get("subscription_tier"):
                            subscription_tier = row["subscription_tier"]
                            logger.info(f"User {user_id} tier={subscription_tier}")
                    # Check research sharing consent
                    cur.execute(
                        """SELECT consented_at IS NOT NULL AND revoked_at IS NULL as consented
                           FROM research_sharing_consent WHERE user_id = %s""",
                        (user_id,),
                    )
                    consent_row = cur.fetchone()
                    research_sharing_consented = consent_row["consented"] if consent_row else False
        except Exception as e:
            logger.debug(f"Could not load user preferences: {e}")

        # Load A/B test variant from session record
        persona_count_variant = None
        try:
            from bo1.state.repositories import session_repository

            session_record = session_repository.get(session_id)
            if session_record:
                persona_count_variant = session_record.get("persona_count_variant")
                if persona_count_variant:
                    logger.info(
                        f"Session {session_id} A/B variant: persona_count={persona_count_variant}"
                    )
        except Exception as e:
            logger.debug(f"Could not load persona_count_variant: {e}")

        # Load context_ids from metadata (user-selected meetings/actions/datasets)
        context_ids = metadata.get("context_ids")

        # Extract request_id for correlation tracing through graph nodes
        request_id = getattr(request.state, "request_id", None)

        # Create initial state
        state = create_initial_state(
            session_id=session_id,
            problem=problem,
            personas=personas,
            max_rounds=6,  # Hard cap for parallel architecture
            skip_clarification=skip_clarification,
            context_ids=context_ids,
            subscription_tier=subscription_tier,
            research_sharing_consented=research_sharing_consented,
            request_id=request_id,
            persona_count_variant=persona_count_variant,
        )

        # Create graph
        graph = create_deliberation_graph()

        # Create event collector for real-time streaming
        from backend.api.dependencies import get_contribution_summarizer, get_event_publisher
        from backend.api.event_collector import EventCollector
        from bo1.state.repositories import session_repository

        event_collector = EventCollector(
            get_event_publisher(), get_contribution_summarizer(), session_repository
        )

        # Create coroutine with event collection
        from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": DELIBERATION_RECURSION_LIMIT,
        }

        coro = event_collector.collect_and_publish(
            session_id, graph, state, config, request_id=request_id
        )

        # Start background task
        await session_manager.start_session(session_id, user_id, coro)

        # Send ntfy notification (fire and forget with context)
        from backend.api.ntfy import notify_meeting_started

        create_task_with_context(notify_meeting_started(session_id, problem_statement))

        # Update session status to 'running' in PostgreSQL (with distributed lock)
        # Also invalidate cache to ensure SSE endpoint sees new status
        try:
            with session_lock(redis_manager.redis, session_id, timeout_seconds=5.0):
                session_repository.update_status(session_id=session_id, status="running")
                # Invalidate cached metadata so SSE sees "running" not stale "created"
                get_session_metadata_cache().invalidate(session_id)
                logger.info(
                    f"Started deliberation for session {session_id} (status updated in PostgreSQL)"
                )
        except LockTimeout:
            logger.warning(f"Could not acquire lock for session {session_id} status update")
            # Still invalidate cache - Redis is already updated to "running"
            get_session_metadata_cache().invalidate(session_id)
            # Don't fail - session is running, status update is secondary
        except Exception as e:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to update session status in PostgreSQL: {e}",
                session_id=session_id,
            )
            # Still invalidate cache - Redis is already updated to "running"
            get_session_metadata_cache().invalidate(session_id)
            # Don't fail the request - session is running in Redis

        return ControlResponse(
            session_id=session_id,
            action="start",
            status="success",
            message="Deliberation started in background",
        )

    except LockTimeout as e:
        logger.warning(f"Lock timeout starting session {session_id}: {e}")
        raise http_error(
            ErrorCode.API_CONFLICT,
            f"Session {session_id} is being modified by another request",
            status=409,
        ) from e
    except Exception as e:
        log_error(
            logger,
            ErrorCode.GRAPH_EXECUTION_ERROR,
            f"Failed to start deliberation for session {session_id}: {e}",
            session_id=session_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.GRAPH_EXECUTION_ERROR,
            f"Failed to start deliberation: {str(e)}",
            status=500,
        ) from e


@router.post(
    "/{session_id}/pause",
    response_model=ControlResponse,
    summary="Pause deliberation",
    description="Pause a running deliberation session. Checkpoint is auto-saved by LangGraph.",
    responses={
        200: {"description": "Deliberation paused successfully"},
        404: ERROR_404_RESPONSE,
        500: ERROR_500_RESPONSE,
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
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to pause deliberation for session {session_id}: {e}",
            session_id=session_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to pause deliberation: {str(e)}",
            status=500,
        ) from e


@router.post(
    "/{session_id}/resume",
    response_model=ControlResponse,
    status_code=202,
    summary="Resume deliberation from checkpoint",
    description="Resume a paused deliberation session from its last checkpoint.",
    responses={
        202: {"description": "Deliberation resumed in background"},
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
        409: ERROR_409_RESPONSE,
        410: {
            "description": "Session checkpoint expired",
            "model": ErrorResponse,
        },
        500: ERROR_500_RESPONSE,
    },
)
@handle_api_errors("resume deliberation")
async def resume_deliberation(
    request: Request,
    session_id: str,
    session_data: VerifiedSession,
    session_manager: SessionManager = Depends(get_session_manager),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Resume a paused deliberation from checkpoint.

    Loads the checkpoint from Redis and continues graph execution.

    Args:
        request: FastAPI request object
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
            raise http_error(
                ErrorCode.API_BAD_REQUEST,
                f"Cannot resume session with status: {status}. Session must be paused.",
            )

        # Check if already running
        if session_id in session_manager.active_executions:
            raise http_error(
                ErrorCode.API_CONFLICT,
                f"Session {session_id} is already running",
                status=409,
            )

        # Create graph with checkpointer for state access
        checkpointer = await get_checkpointer()
        graph = create_deliberation_graph(checkpointer=checkpointer)

        # Create event collector for real-time streaming
        from backend.api.dependencies import get_contribution_summarizer, get_event_publisher
        from backend.api.event_collector import EventCollector
        from bo1.state.repositories import session_repository

        event_collector = EventCollector(
            get_event_publisher(), get_contribution_summarizer(), session_repository
        )

        from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT

        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": DELIBERATION_RECURSION_LIMIT,
        }

        # Check if this is a clarification resume (has pending clarification answers)
        # CRITICAL FIX: aupdate_state with as_node creates a NEW checkpoint branch that
        # loses existing state like problem.sub_problems. We must load full state first.
        clarification_answers = metadata.get("clarification_answers_pending")
        if clarification_answers:
            from bo1.graph.state import serialize_state_for_checkpoint

            try:
                # CRITICAL: Load FULL current state from checkpoint first
                current_checkpoint = await graph.aget_state(config)
                if current_checkpoint and current_checkpoint.values:
                    full_state = dict(current_checkpoint.values)

                    # Check if sub_problems exists (LangGraph may lose nested Pydantic models)
                    problem = full_state.get("problem")
                    if problem:
                        if isinstance(problem, dict):
                            sub_problems = problem.get("sub_problems", [])
                        else:
                            sub_problems = getattr(problem, "sub_problems", []) or []
                        sub_problems_count = len(sub_problems) if sub_problems else 0
                    else:
                        sub_problems_count = 0

                    logger.info(
                        f"Loaded checkpoint for {session_id} (resume with answers): "
                        f"problem={bool(problem)}, sub_problems={sub_problems_count}"
                    )

                    # CRITICAL FIX: If checkpoint has problem but NO sub_problems,
                    # LangGraph's serialization lost them. Use PostgreSQL to recover.
                    if problem and sub_problems_count == 0:
                        logger.warning(
                            f"Checkpoint for {session_id} has problem but NO sub_problems! "
                            f"LangGraph serialization lost nested data. Recovering from PostgreSQL."
                        )
                        recovered_problem = _recover_problem_from_postgres(session_id)
                        if recovered_problem:
                            # Merge: use PostgreSQL's problem (with sub_problems) but keep
                            # other checkpoint state that wasn't lost
                            full_state["problem"] = recovered_problem
                            logger.info(
                                f"Recovered problem with {len(recovered_problem.sub_problems)} sub_problems from PostgreSQL"
                            )
                        else:
                            log_error(
                                logger,
                                ErrorCode.DB_QUERY_ERROR,
                                f"Failed to recover problem from PostgreSQL for {session_id}",
                                session_id=session_id,
                            )
                else:
                    # Fallback will be handled below
                    raise ValueError("No checkpoint found")

                # Merge our updates INTO the full state
                full_state["clarification_answers"] = clarification_answers
                full_state["should_stop"] = False  # Reset stop flag so router continues
                full_state["stop_reason"] = None  # Clear stop reason
                # ATOMICITY FIX: Clear pending_clarification to prevent stale pause state on resume
                full_state["pending_clarification"] = None

                # BUG FIX: Inject clarification answers directly into problem.context
                # When graph resumes, identify_gaps_node is NOT re-run (as_node="identify_gaps"
                # means resume from AFTER the node). So we must inject the answers here.
                problem = full_state.get("problem")
                if problem and clarification_answers:
                    # Build answer context (same format as identify_gaps_node)
                    answer_context = "\n\n## User Clarifications\n"
                    for question, answer in clarification_answers.items():
                        # Sanitize each answer to prevent indirect prompt injection
                        sanitized_answer = sanitize_user_input(
                            answer, context="clarification_answer"
                        )
                        answer_context += f"- **Q:** {question}\n  **A:** {sanitized_answer}\n"

                    # Inject into problem.context
                    if isinstance(problem, dict):
                        current_context = problem.get("context", "") or ""
                        problem["context"] = current_context + answer_context
                    else:
                        current_context = getattr(problem, "context", "") or ""
                        problem.context = current_context + answer_context
                    full_state["problem"] = problem

                    logger.info(
                        f"Injected {len(clarification_answers)} clarification answer(s) into "
                        f"problem.context ({len(answer_context)} chars added)"
                    )

                # Serialize the COMPLETE merged state
                serialized_state = serialize_state_for_checkpoint(full_state)

                # Use as_node="identify_gaps" to tell LangGraph to resume from
                # the edge AFTER identify_gaps (the router will run next)
                await graph.aupdate_state(config, serialized_state, as_node="identify_gaps")

                logger.info(
                    f"Updated checkpoint for session {session_id} with {len(clarification_answers)} "
                    f"clarification answer(s) (preserved full state) - will resume from identify_gaps edge"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to update checkpoint for {session_id}: {e}. "
                    f"Attempting PostgreSQL reconstruction fallback."
                )

                # Fallback: Reconstruct state from PostgreSQL
                reconstructed = _reconstruct_state_from_postgres(session_id)
                if reconstructed:
                    # Add clarification answers to reconstructed state
                    reconstructed["clarification_answers"] = clarification_answers
                    reconstructed["should_stop"] = False
                    reconstructed["stop_reason"] = None
                    # ATOMICITY FIX: Clear pending_clarification in fallback path too
                    reconstructed["pending_clarification"] = None

                    # BUG FIX: Also inject answers into problem.context for fallback path
                    problem = reconstructed.get("problem")
                    if problem and clarification_answers:
                        answer_context = "\n\n## User Clarifications\n"
                        for question, answer in clarification_answers.items():
                            answer_context += f"- **Q:** {question}\n  **A:** {answer}\n"

                        if isinstance(problem, dict):
                            current_context = problem.get("context", "") or ""
                            problem["context"] = current_context + answer_context
                        else:
                            current_context = getattr(problem, "context", "") or ""
                            problem.context = current_context + answer_context
                        reconstructed["problem"] = problem

                    logger.info(
                        f"Reconstructed state from PostgreSQL for {session_id}, "
                        f"will restart with clarification answers"
                    )

                    # Start with reconstructed state (will re-run from entry point)
                    # This is fallback - not ideal but better than failing
                    request_id = getattr(request.state, "request_id", None)
                    coro = event_collector.collect_and_publish(
                        session_id, graph, reconstructed, config, request_id=request_id
                    )

                    # Clear the pending flag and start session
                    metadata.pop("clarification_answers_pending", None)
                    redis_manager.save_metadata(session_id, metadata)

                    # Start background task
                    await session_manager.start_session(session_id, user_id, coro)

                    # Update metadata
                    now = datetime.now(UTC)
                    metadata["status"] = "running"
                    metadata["resumed_at"] = now.isoformat()
                    metadata["updated_at"] = now.isoformat()
                    redis_manager.save_metadata(session_id, metadata)

                    return ControlResponse(
                        session_id=session_id,
                        action="resume",
                        status="success",
                        message="Deliberation resumed (reconstructed from database)",
                    )
                else:
                    raise http_error(
                        ErrorCode.API_SESSION_ERROR,
                        "Session checkpoint expired and cannot be reconstructed. "
                        "Please start a new meeting.",
                        status=410,
                    ) from e

            # Clear the pending flag from metadata
            metadata.pop("clarification_answers_pending", None)
            redis_manager.save_metadata(session_id, metadata)

            # Resume from checkpoint (None = use checkpoint, don't restart from entry)
            # The graph will resume from the edge AFTER identify_gaps
            request_id = getattr(request.state, "request_id", None)
            coro = event_collector.collect_and_publish(
                session_id, graph, None, config, request_id=request_id
            )
        else:
            # Normal resume from checkpoint (no clarification answers)
            request_id = getattr(request.state, "request_id", None)
            coro = event_collector.collect_and_publish(
                session_id, graph, None, config, request_id=request_id
            )

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

    except Exception as e:
        log_error(
            logger,
            ErrorCode.GRAPH_EXECUTION_ERROR,
            f"Failed to resume deliberation for session {session_id}: {e}",
            session_id=session_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.GRAPH_EXECUTION_ERROR,
            f"Failed to resume deliberation: {str(e)}",
            status=500,
        ) from e


@router.post(
    "/{session_id}/kill",
    response_model=ControlResponse,
    summary="Kill deliberation",
    description="Kill a running deliberation session. Requires user ownership of the session.",
    responses={
        200: {"description": "Deliberation killed successfully"},
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
        500: ERROR_500_RESPONSE,
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("kill deliberation")
async def kill_deliberation(
    request: Request,
    session_id: str,
    kill_request: KillRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Kill a running deliberation (user must own the session).

    This cancels the background task and logs the termination in an audit trail.

    Args:
        request: FastAPI request object for rate limiting
        session_id: Session identifier
        kill_request: Optional kill request with reason
        user: Authenticated user data
        redis_manager: Redis manager instance

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
            raise http_error(
                ErrorCode.API_NOT_FOUND,
                f"Session not found or not running: {session_id}",
                status=404,
            )

        # Update session status to 'killed' in PostgreSQL (with distributed lock)
        try:
            with session_lock(redis_manager.redis, session_id, timeout_seconds=5.0):
                session_repository.update_status(session_id=session_id, status="killed")
                # Invalidate cached metadata on status change
                get_session_metadata_cache().invalidate(session_id)
                logger.info(
                    f"Killed deliberation for session {session_id}. Reason: {reason} (status updated in PostgreSQL)"
                )
        except LockTimeout:
            logger.warning(f"Could not acquire lock for session {session_id} killed status update")
            # Don't fail - session is already killed, status update is secondary
        except Exception as e:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to update killed session status in PostgreSQL: {e}",
                session_id=session_id,
            )
            # Don't fail the request - session is already killed

        return ControlResponse(
            session_id=session_id,
            action="kill",
            status="success",
            message=f"Deliberation killed. Reason: {reason}",
        )

    except PermissionError as e:
        logger.warning(f"Permission denied to kill session {session_id}: {e}")
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            str(e),
            status=403,
        ) from e
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to kill deliberation for session {session_id}: {e}",
            session_id=session_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to kill deliberation: {str(e)}",
            status=500,
        ) from e


@router.post(
    "/{session_id}/retry",
    response_model=ControlResponse,
    status_code=202,
    summary="Retry failed session from checkpoint",
    description="Retry a failed deliberation session from its last successful checkpoint.",
    responses={
        202: {"description": "Deliberation retried from checkpoint"},
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
        409: ERROR_409_RESPONSE,
        410: {
            "description": "Checkpoint expired and cannot be reconstructed",
            "model": ErrorResponse,
        },
        429: RATE_LIMIT_RESPONSE,
        500: ERROR_500_RESPONSE,
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("retry deliberation")
async def retry_deliberation(
    request: Request,
    session_id: str,
    session_data: VerifiedSession,
    session_manager: SessionManager = Depends(get_session_manager),
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Retry a failed deliberation from its last checkpoint.

    Unlike /resume (which handles paused sessions), /retry handles failed sessions
    by loading the last checkpoint, resetting error state, and resuming execution.

    Falls back to PostgreSQL reconstruction if the Redis checkpoint has expired.

    Args:
        request: FastAPI request object for rate limiting
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        session_manager: Session manager instance
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with retry confirmation

    Raises:
        HTTPException: If session not found, not failed, or retry fails
    """
    # Validate session ID format
    session_id = validate_session_id(session_id)

    # Unpack verified session data
    user_id, metadata = session_data

    # Validate session status - only allow retry for failed sessions
    status = metadata.get("status")
    if status != "failed":
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            f"Cannot retry session with status: {status}. Session must be failed.",
        )

    # Check if already running (shouldn't happen for failed, but be safe)
    if session_id in session_manager.active_executions:
        raise http_error(
            ErrorCode.API_CONFLICT,
            f"Session {session_id} is already running",
            status=409,
        )

    # Create graph with checkpointer for state access
    checkpointer = await get_checkpointer()
    graph = create_deliberation_graph(checkpointer=checkpointer)

    from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": DELIBERATION_RECURSION_LIMIT,
    }

    # Try to load and prepare state from checkpoint
    from bo1.graph.execution import resume_session_from_checkpoint

    state = await resume_session_from_checkpoint(session_id, graph, config)

    if not state:
        # Checkpoint not found - try PostgreSQL reconstruction (allow_failed=True for retry)
        logger.info(f"Checkpoint not found for {session_id}, attempting PostgreSQL reconstruction")
        state = _reconstruct_state_from_postgres(session_id, allow_failed=True)

        if not state:
            raise http_error(
                ErrorCode.API_SESSION_ERROR,
                "Session checkpoint expired and cannot be reconstructed. "
                "Please start a new meeting.",
                status=410,
            )

        logger.info(f"Reconstructed state from PostgreSQL for retry of {session_id}")

    # Check if sub_problems exist; if not, try to recover from PostgreSQL
    problem = state.get("problem")
    if problem:
        if isinstance(problem, dict):
            sub_problems = problem.get("sub_problems", [])
        else:
            sub_problems = getattr(problem, "sub_problems", []) or []

        if not sub_problems:
            logger.warning(
                f"Checkpoint for {session_id} has problem but NO sub_problems! "
                f"Recovering from PostgreSQL."
            )
            recovered_problem = _recover_problem_from_postgres(session_id)
            if recovered_problem:
                state["problem"] = recovered_problem
                logger.info(
                    f"Recovered problem with {len(recovered_problem.sub_problems)} sub_problems"
                )
            else:
                raise http_error(
                    ErrorCode.API_SESSION_ERROR,
                    "Session state is incomplete and cannot be reconstructed. "
                    "Please start a new meeting.",
                    status=410,
                )

    # Create event collector for real-time streaming
    from backend.api.dependencies import get_contribution_summarizer, get_event_publisher
    from backend.api.event_collector import EventCollector

    event_collector = EventCollector(
        get_event_publisher(), get_contribution_summarizer(), session_repository
    )

    # Save the prepared state back to checkpoint so graph can resume from it
    from bo1.graph.state import serialize_state_for_checkpoint

    serialized_state = serialize_state_for_checkpoint(state)

    # Use aupdate_state to set the state at the current node
    # We need to determine where to resume from based on current_node in state
    current_node = state.get("current_node", "decomposition")
    await graph.aupdate_state(config, serialized_state, as_node=current_node)
    logger.info(f"Saved prepared state for retry, will resume from {current_node}")

    # Resume from checkpoint (None = use checkpoint, don't restart from entry)
    request_id = getattr(request.state, "request_id", None)
    coro = event_collector.collect_and_publish(
        session_id, graph, None, config, request_id=request_id
    )

    # Start background task
    await session_manager.start_session(session_id, user_id, coro)

    # Update session status to 'running' in PostgreSQL
    try:
        with session_lock(redis_manager.redis, session_id, timeout_seconds=5.0):
            session_repository.update_status(session_id=session_id, status="running")
            logger.info(
                f"Retried deliberation for session {session_id} (status updated in PostgreSQL)"
            )
    except LockTimeout:
        logger.warning(f"Could not acquire lock for session {session_id} status update")
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to update session status in PostgreSQL: {e}",
            session_id=session_id,
        )

    # Update Redis metadata
    now = datetime.now(UTC)
    metadata["status"] = "running"
    metadata["retried_at"] = now.isoformat()
    metadata["updated_at"] = now.isoformat()
    redis_manager.save_metadata(session_id, metadata)

    logger.info(f"Retried failed deliberation for session {session_id}")

    return ControlResponse(
        session_id=session_id,
        action="retry",
        status="success",
        message="Deliberation retried from checkpoint",
    )


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
        404: ERROR_404_RESPONSE,
        500: ERROR_500_RESPONSE,
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

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get clarification for session {session_id}: {e}",
            session_id=session_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get clarification: {str(e)}",
            status=500,
        ) from e


@router.post(
    "/{session_id}/clarifications",
    response_model=ControlResponse,
    status_code=202,
    summary="Submit clarification answer",
    description="Submit an answer to a pending clarification question and resume deliberation.",
    responses={
        202: {"description": "Clarification submitted, deliberation resumed"},
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
        422: {
            "description": "Prompt injection detected",
            "model": ErrorResponse,
        },
        500: ERROR_500_RESPONSE,
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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
        500: ERROR_500_RESPONSE,
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

            # BUG FIX (P0 #2): Update checkpoint state to allow proper resume
            # CRITICAL: aupdate_state with as_node creates a NEW checkpoint branch that
            # loses existing state like problem.sub_problems. We must:
            # 1. Load the FULL current checkpoint state first
            # 2. Merge our updates INTO it
            # 3. Save the complete merged state
            try:
                from bo1.graph.state import serialize_state_for_checkpoint

                # Get initialized checkpointer and graph
                checkpointer = await get_checkpointer()
                graph = create_deliberation_graph(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": session_id}}

                # CRITICAL: Load FULL current state from checkpoint first
                current_checkpoint = await graph.aget_state(config)
                if current_checkpoint and current_checkpoint.values:
                    full_state = dict(current_checkpoint.values)

                    # Check if sub_problems exists (LangGraph may lose nested Pydantic models)
                    problem = full_state.get("problem")
                    if problem:
                        if isinstance(problem, dict):
                            sub_problems = problem.get("sub_problems", [])
                        else:
                            sub_problems = getattr(problem, "sub_problems", []) or []
                        sub_problems_count = len(sub_problems) if sub_problems else 0
                    else:
                        sub_problems_count = 0

                    logger.info(
                        f"Loaded checkpoint for {session_id}: "
                        f"problem={bool(problem)}, sub_problems={sub_problems_count}"
                    )

                    # CRITICAL FIX: If checkpoint has problem but NO sub_problems,
                    # LangGraph's serialization lost them. Use PostgreSQL to recover.
                    if problem and sub_problems_count == 0:
                        logger.warning(
                            f"Checkpoint for {session_id} has problem but NO sub_problems! "
                            f"LangGraph serialization lost nested data. Recovering from PostgreSQL."
                        )
                        recovered_problem = _recover_problem_from_postgres(session_id)
                        if recovered_problem:
                            # Merge: use PostgreSQL's problem (with sub_problems) but keep
                            # other checkpoint state that wasn't lost
                            full_state["problem"] = recovered_problem
                            logger.info(
                                f"Recovered problem with {len(recovered_problem.sub_problems)} sub_problems from PostgreSQL"
                            )
                        else:
                            log_error(
                                logger,
                                ErrorCode.DB_QUERY_ERROR,
                                f"Failed to recover problem from PostgreSQL for {session_id}",
                                session_id=session_id,
                            )
                else:
                    # Fallback: reconstruct from PostgreSQL
                    full_state = _reconstruct_state_from_postgres(session_id)
                    if not full_state:
                        raise ValueError("No checkpoint found and PostgreSQL reconstruction failed")
                    logger.info(f"Reconstructed state from PostgreSQL for {session_id}")

                # Merge our updates INTO the full state
                full_state["clarification_answers"] = {}  # Empty dict signals skip
                full_state["should_stop"] = False  # Reset stop flag so router continues
                full_state["stop_reason"] = None  # Clear stop reason
                full_state["pending_clarification"] = None  # Clear pending
                full_state["user_context_choice"] = "continue"  # Signal to continue without answers
                full_state["limited_context_mode"] = (
                    True  # Flag that we're operating with limited info
                )

                # Serialize the COMPLETE merged state
                serialized_state = serialize_state_for_checkpoint(full_state)
                await graph.aupdate_state(config, serialized_state, as_node="identify_gaps")

                logger.info(
                    f"Updated checkpoint for session {session_id} with skip signal (preserved full state) - "
                    f"will resume from identify_gaps edge"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to update checkpoint for skip on {session_id}: {e}. Resume may fail."
                )

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
            raise http_error(
                ErrorCode.API_BAD_REQUEST,
                "No answers provided. Use 'answers' dict or 'skip': true",
            )

        # Prompt injection audit on all answers
        for _question, answer in answers_to_process.items():
            await check_for_injection(
                content=answer,
                source="clarification_answer",
                raise_on_unsafe=True,
            )

        # Store answers in Redis metadata for the resume flow to pick up
        # We don't modify the LangGraph checkpoint here because as_node doesn't
        # properly merge state - it branches from an earlier checkpoint.
        # Instead, the resume_deliberation endpoint will inject these answers
        # into the checkpoint state before re-running the graph.
        metadata["clarification_answers_pending"] = answers_to_process
        metadata["pending_clarification"] = None
        metadata["status"] = "paused"  # Mark as paused, ready to resume
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        redis_manager.save_metadata(session_id, metadata)

        # ISSUE #4 FIX: Persist clarification answers to user's business context
        # This ensures future meetings can benefit from the clarifications
        try:
            from bo1.state.repositories import user_repository

            # Load existing business context
            existing_context = user_repository.get_context(user_id) or {}

            # Add/update clarifications section with structured parsing
            # Filter out null/empty responses before storage
            from backend.services.insight_parser import is_valid_insight_response, parse_insight

            clarifications = existing_context.get("clarifications", {})
            valid_answers: dict[str, str] = {}  # Track valid answers for context extraction
            for question, answer in answers_to_process.items():
                # Skip invalid/empty responses
                if not is_valid_insight_response(answer):
                    logger.debug(
                        f"Skipping invalid insight response for '{question[:30]}...': "
                        f"'{answer[:30] if answer else 'None'}...'"
                    )
                    continue

                valid_answers[question] = answer
                clarification_entry = {
                    "answer": answer,
                    "answered_at": datetime.now(UTC).isoformat(),
                    "session_id": session_id,
                }

                # Parse insight with Haiku for structured categorization
                try:
                    structured = await parse_insight(answer)
                    clarification_entry["category"] = structured.category.value
                    clarification_entry["confidence_score"] = structured.confidence_score
                    if structured.metric:
                        clarification_entry["metric"] = {
                            "value": structured.metric.value,
                            "unit": structured.metric.unit,
                            "metric_type": structured.metric.metric_type,
                            "period": structured.metric.period,
                            "raw_text": structured.metric.raw_text,
                        }
                    if structured.summary:
                        clarification_entry["summary"] = structured.summary
                    if structured.key_entities:
                        clarification_entry["key_entities"] = structured.key_entities
                    clarification_entry["parsed_at"] = structured.parsed_at
                except Exception as parse_err:
                    # Non-blocking - fallback to uncategorized
                    logger.debug(f"Insight parsing failed (non-blocking): {parse_err}")
                    clarification_entry["category"] = "uncategorized"
                    clarification_entry["confidence_score"] = 0.0

                # Validate entry before storage
                from backend.api.context.services import normalize_clarification_for_storage

                clarifications[question] = normalize_clarification_for_storage(clarification_entry)
            existing_context["clarifications"] = clarifications

            # Context Auto-Update: Extract business context updates from clarification answers
            try:
                from backend.services.context_extractor import (
                    ContextUpdateSource,
                    extract_context_updates,
                    filter_high_confidence_updates,
                )

                # Concatenate only valid answers for extraction
                all_answers = " ".join(valid_answers.values())
                updates = await extract_context_updates(
                    all_answers, existing_context, ContextUpdateSource.CLARIFICATION
                )

                if updates:
                    high_conf, low_conf = filter_high_confidence_updates(updates)

                    # Auto-apply high confidence updates
                    if high_conf:
                        metric_history = existing_context.get("context_metric_history", {})
                        for upd in high_conf:
                            # Update the context field
                            existing_context[upd.field_name] = upd.new_value
                            logger.info(
                                f"Auto-applied context update: {upd.field_name}={upd.new_value} "
                                f"(conf={upd.confidence:.2f})"
                            )

                            # Track in metric history (keep last 10 values)
                            if upd.field_name not in metric_history:
                                metric_history[upd.field_name] = []
                            metric_history[upd.field_name].insert(
                                0,
                                {
                                    "value": upd.new_value,
                                    "recorded_at": upd.extracted_at,
                                    "source_type": upd.source_type.value,
                                    "source_id": session_id,
                                },
                            )
                            # Keep only last 10 entries
                            metric_history[upd.field_name] = metric_history[upd.field_name][:10]

                        existing_context["context_metric_history"] = metric_history
                        logger.info(f"Auto-applied {len(high_conf)} context update(s)")

                    # Queue low confidence updates for user review
                    if low_conf:
                        import uuid

                        pending = existing_context.get("pending_updates", [])
                        for upd in low_conf:
                            # Limit to 5 pending updates
                            if len(pending) >= 5:
                                break
                            pending.append(
                                {
                                    "id": str(uuid.uuid4())[:8],
                                    "field_name": upd.field_name,
                                    "new_value": upd.new_value,
                                    "current_value": existing_context.get(upd.field_name),
                                    "confidence": upd.confidence,
                                    "source_type": upd.source_type.value,
                                    "source_text": upd.source_text,
                                    "extracted_at": upd.extracted_at,
                                    "session_id": session_id,
                                }
                            )
                        existing_context["pending_updates"] = pending
                        logger.info(f"Queued {len(low_conf)} low-confidence update(s) for review")

            except Exception as extract_err:
                # Non-blocking - don't fail if context extraction fails
                logger.debug(f"Context extraction failed (non-blocking): {extract_err}")

            # Save updated context
            user_repository.save_context(user_id, existing_context)
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

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to submit clarification for session {session_id}: {e}",
            session_id=session_id,
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to submit clarification: {str(e)}",
            status=500,
        ) from e


# =============================================================================
# Context Insufficiency Choice (Option D+E Hybrid)
# =============================================================================


class RaiseHandRequest(BaseModel):
    """Request model for user interjection during deliberation.

    Allows users to interject with a question or context during an active meeting.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's interjection message (question or context to add)",
        examples=["What about the regulatory compliance implications?"],
    )


@router.post(
    "/{session_id}/raise-hand",
    response_model=ControlResponse,
    status_code=202,
    summary="Raise hand to interject during deliberation",
    description="Submit a question or context during an active meeting. Experts will acknowledge and respond.",
    responses={
        202: {"description": "Interjection submitted, experts will respond"},
        400: ERROR_400_RESPONSE,
        404: ERROR_404_RESPONSE,
        422: {
            "description": "Prompt injection detected",
            "model": ErrorResponse,
        },
        429: RATE_LIMIT_RESPONSE,
        500: ERROR_500_RESPONSE,
    },
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("raise hand")
async def raise_hand(
    request: Request,
    session_id: str,
    body: RaiseHandRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Submit an interjection during an active deliberation.

    The interjection is saved to the checkpoint state and will be processed
    at the next round boundary. Experts will provide brief responses.

    Args:
        request: FastAPI request object for rate limiting
        session_id: Session identifier
        body: Interjection message
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with confirmation

    Raises:
        HTTPException: If session not running, injection detected, or save fails
    """
    # Validate session ID format
    session_id = validate_session_id(session_id)

    # Unpack verified session data
    user_id, metadata = session_data

    # Validate session is running
    status = metadata.get("status")
    if status != "running":
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            f"Cannot raise hand: session is not running (status: {status})",
        )

    # Prompt injection check
    await check_for_injection(
        content=body.message,
        source="raise_hand_interjection",
        raise_on_unsafe=True,
    )

    # Load current checkpoint state
    state = await load_state_from_checkpoint(session_id)
    if not state:
        raise http_error(
            ErrorCode.API_SESSION_ERROR,
            "Failed to load session state from checkpoint",
            status=500,
        )

    # Check for existing pending interjection (rate limit at state level)
    if state.get("needs_interjection_response"):
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            "An interjection is already pending. Please wait for experts to respond.",
            status=429,
        )

    # Update state with interjection (sanitize to prevent indirect prompt injection)
    state["user_interjection"] = sanitize_user_input(body.message, context="user_interjection")
    state["needs_interjection_response"] = True
    state["interjection_responses"] = []  # Clear previous responses

    # Save updated state to checkpoint
    saved = await save_state_to_checkpoint(session_id, state)
    if not saved:
        raise http_error(
            ErrorCode.API_SESSION_ERROR,
            "Failed to save interjection to session state",
            status=500,
        )

    # Emit SSE event for real-time UI update
    from backend.api.dependencies import get_event_publisher

    publisher = get_event_publisher()
    await publisher.publish(
        session_id,
        {
            "event_type": "user_interjection_raised",
            "data": {
                "message": body.message,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
    )

    logger.info(f"User raised hand in session {session_id}: {body.message[:50]}...")

    return ControlResponse(
        session_id=session_id,
        action="raise_hand",
        status="success",
        message="Interjection submitted. Experts will acknowledge your question.",
    )


class ContextChoiceRequest(BaseModel):
    """Request model for context insufficiency user choice.

    When >50% of contributions indicate experts need more context,
    the user is given 3 choices:
    - provide_more: Provide additional context and continue
    - continue: Proceed with best-effort analysis
    - end: End meeting early with current insights
    """

    choice: str = Field(
        ...,
        description="User's choice: 'provide_more', 'continue', or 'end'",
        examples=["continue"],
    )
    additional_context: str | None = Field(
        None,
        max_length=5000,
        description="Additional context (required if choice is 'provide_more')",
    )


@router.post(
    "/{session_id}/context-choice",
    response_model=ControlResponse,
    status_code=202,
    summary="Submit context insufficiency choice",
    description="Submit user's choice when experts indicate they need more context.",
    responses={
        202: {"description": "Choice submitted, deliberation will resume/end accordingly"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("submit context choice")
async def submit_context_choice(
    session_id: str,
    request: ContextChoiceRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> ControlResponse:
    """Handle user's choice when context is insufficient.

    This endpoint is called when the user responds to a context_insufficient event.
    It updates the session state and prepares for resume.

    Args:
        session_id: Session identifier
        request: User's choice and optional additional context
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        ControlResponse with status and next steps
    """
    session_id = validate_session_id(session_id)
    user_id, metadata = session_data

    # Validate choice
    valid_choices = {"provide_more", "continue", "end"}
    if request.choice not in valid_choices:
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            f"Invalid choice: {request.choice}. Must be one of: {valid_choices}",
        )

    # Validate additional_context for provide_more choice
    if request.choice == "provide_more" and not request.additional_context:
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            "Additional context required when choice is 'provide_more'",
        )

    logger.info(f"Context choice received for session {session_id}: {request.choice}")

    if request.choice == "end":
        # End meeting early - trigger early synthesis
        metadata["user_context_choice"] = "end"
        metadata["status"] = "paused"  # Will trigger early synthesis on resume
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        redis_manager.save_metadata(session_id, metadata)

        # Update checkpoint state for early end
        await _update_checkpoint_for_context_choice(session_id, "end", None)

        return ControlResponse(
            session_id=session_id,
            action="context_choice",
            status="success",
            message="Meeting will end with current insights. Call /resume to generate synthesis.",
        )

    elif request.choice == "provide_more":
        # Store additional context and prepare for resume
        metadata["user_context_choice"] = "provide_more"
        metadata["additional_context"] = request.additional_context
        metadata["status"] = "paused"
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        redis_manager.save_metadata(session_id, metadata)

        # Update checkpoint state with additional context
        await _update_checkpoint_for_context_choice(
            session_id, "provide_more", request.additional_context
        )

        return ControlResponse(
            session_id=session_id,
            action="context_choice",
            status="success",
            message="Additional context received. Call /resume to continue deliberation.",
        )

    else:  # continue
        # Continue with best effort mode
        metadata["user_context_choice"] = "continue"
        metadata["best_effort_mode"] = True
        metadata["status"] = "paused"
        metadata["updated_at"] = datetime.now(UTC).isoformat()
        redis_manager.save_metadata(session_id, metadata)

        # Update checkpoint state for best effort mode
        await _update_checkpoint_for_context_choice(session_id, "continue", None)

        return ControlResponse(
            session_id=session_id,
            action="context_choice",
            status="success",
            message="Continuing with best-effort analysis. Call /resume to continue deliberation.",
        )


async def _update_checkpoint_for_context_choice(
    session_id: str,
    choice: str,
    additional_context: str | None,
) -> bool:
    """Update checkpoint state with context choice.

    This updates the LangGraph checkpoint so that when the session resumes,
    the graph knows which choice the user made.

    Args:
        session_id: Session identifier
        choice: User's choice (provide_more, continue, end)
        additional_context: Additional context if provided

    Returns:
        True if update successful, False otherwise
    """
    try:
        # Load current state
        state = await load_state_from_checkpoint(session_id)
        if not state:
            logger.warning(f"No checkpoint found for {session_id} to update context choice")
            return False

        # Update state with user choice
        state["user_context_choice"] = choice
        state["should_stop"] = False  # Clear stop flag to allow resume

        if choice == "continue":
            state["best_effort_prompt_injected"] = False  # Will be injected on next round
            state["limited_context_mode"] = True
        elif choice == "provide_more" and additional_context:
            # Inject additional context into problem
            problem = state.get("problem")
            if problem:
                if isinstance(problem, dict):
                    current_context = problem.get("context", "") or ""
                    problem["context"] = (
                        current_context
                        + f"\n\n## Additional Context (from user)\n{additional_context}"
                    )
                else:
                    current_context = problem.context or ""
                    problem.context = (
                        current_context
                        + f"\n\n## Additional Context (from user)\n{additional_context}"
                    )
                state["problem"] = problem
        elif choice == "end":
            # Set up for early synthesis
            state["should_stop"] = True
            state["stop_reason"] = "user_ended_early"

        # Save updated state back to checkpoint
        return await save_state_to_checkpoint(session_id, state)

    except Exception as e:
        log_error(
            logger,
            ErrorCode.GRAPH_CHECKPOINT_ERROR,
            f"Failed to update checkpoint for context choice: {e}",
            session_id=session_id,
        )
        return False
