"""SSE streaming endpoints for real-time deliberation updates.

Provides:
- GET /api/v1/sessions/{session_id}/stream - Stream deliberation events via SSE
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.api.dependencies import VerifiedSession, get_redis_manager
from backend.api.events import (
    error_event,
    gap_detected_event,
    node_start_event,
)
from backend.api.metrics import metrics
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import STREAMING_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse, EventHistoryResponse
from backend.api.utils.auth_helpers import is_admin
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.validation import validate_session_id

# SSE event types that contain sensitive cost data (admin-only)
COST_EVENT_TYPES = {"phase_cost_breakdown", "cost_anomaly"}

# Fields within events that contain cost data (strip for non-admin)
COST_FIELDS = {"cost", "total_cost", "phase_costs", "by_provider"}


def strip_cost_data_from_event(event: dict) -> dict:
    """Remove cost data from an event payload for non-admin users.

    Args:
        event: SSE event payload dict

    Returns:
        Event with cost fields stripped
    """
    # Skip cost-only events entirely
    event_type = event.get("type")
    if event_type in COST_EVENT_TYPES:
        return None

    # Strip cost fields from other events
    result = {}
    for key, value in event.items():
        if key in COST_FIELDS:
            continue  # Skip cost fields
        if isinstance(value, dict):
            # Recursively strip from nested dicts
            result[key] = {k: v for k, v in value.items() if k not in COST_FIELDS}
        else:
            result[key] = value
    return result


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["streaming"])


@router.get(
    "/{session_id}/events",
    response_model=EventHistoryResponse,
    summary="Get session event history",
    description="""
    Get all historical events for a session.

    Checks Redis first (for recent/active sessions), falls back to PostgreSQL
    (for sessions after Redis restart). Frontend should call this first to get
    history, then connect to SSE stream for live updates.
    """,
    responses={
        200: {"description": "Event history retrieved successfully"},
        403: {
            "description": "Not authorized to access this session",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Not authorized to access this session"}}
            },
        },
        404: {
            "description": "Session not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Session not found", "session_id": "bo1_abc123"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Internal server error",
                        "error_code": "EVENT_FETCH_FAILED",
                    }
                }
            },
        },
    },
)
@handle_api_errors("get event history")
async def get_event_history(
    session_id: str,
    session_data: VerifiedSession,
    current_user: dict = Depends(get_current_user),
) -> EventHistoryResponse:
    """Get historical events for a session.

    Checks Redis first (transient storage), then PostgreSQL (permanent storage).

    Security: Cost data is stripped from events for non-admin users.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        current_user: Current authenticated user (for admin check)

    Returns:
        EventHistoryResponse with events array and count

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    user_is_admin = is_admin(current_user)
    from backend.api.event_publisher import get_event_history_with_fallback

    try:
        # Unpack verified session data
        user_id, metadata = session_data

        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Get Redis manager (metadata already verified by VerifiedSession dependency)
        redis_manager = get_redis_manager()

        # Get events with automatic Redis/PostgreSQL fallback
        # This handles Redis connection errors gracefully
        redis_client = redis_manager.redis if redis_manager.is_available else None
        events = await get_event_history_with_fallback(
            redis_client=redis_client,
            session_id=session_id,
            last_event_id=None,  # No filtering for full history
        )

        logger.info(f"Retrieved {len(events)} historical events for session {session_id}")

        # Security: Strip cost data from events for non-admin users
        if not user_is_admin:
            filtered_events = []
            for event in events:
                filtered = strip_cost_data_from_event(event)
                if filtered is not None:  # None means skip entirely
                    filtered_events.append(filtered)
            events = filtered_events

        # Find last_event_id from events for resume support
        last_event_id = None
        last_sequence = 0
        for event in events:
            seq = event.get("sequence", 0)
            if seq > last_sequence:
                last_sequence = seq
        if last_sequence > 0:
            from backend.api.events import make_event_id

            last_event_id = make_event_id(session_id, last_sequence)

        # Check if session is resumable (running or completed)
        status = metadata.get("status") if metadata else None
        can_resume = status in ["running", "completed"]

        return EventHistoryResponse(
            session_id=session_id,
            events=events,
            count=len(events),
            last_event_id=last_event_id,
            can_resume=can_resume,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get event history for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get event history: {str(e)}",
        ) from e


def format_sse_for_type(event_type: str, data: dict) -> str:
    """Map event type to SSE formatter function.

    Args:
        event_type: Event type name (e.g., "decomposition_complete")
        data: Event data payload

    Returns:
        SSE-formatted event string

    Examples:
        >>> event_str = format_sse_for_type("decomposition_complete", {...})
    """
    from backend.api import events

    session_id = data.get("session_id", "")

    # Map event_type to formatter function
    formatters = {
        "session_started": lambda: events.session_started_event(
            session_id,
            data.get("problem_statement", ""),
            data.get("max_rounds", 10),
            data.get("user_id", ""),
        ),
        "decomposition_started": lambda: events.decomposition_started_event(session_id),
        "decomposition_complete": lambda: events.decomposition_complete_event(
            session_id, data.get("sub_problems", [])
        ),
        "persona_selection_started": lambda: events.persona_selection_started_event(session_id),
        "persona_selected": lambda: events.persona_selected_event(
            session_id,
            data.get("persona", {}),
            data.get("rationale", ""),
            data.get("order", 1),
            sub_problem_index=data.get("sub_problem_index"),
        ),
        "persona_selection_complete": lambda: events.persona_selection_complete_event(
            session_id,
            data.get("personas", []),
            sub_problem_index=data.get("sub_problem_index"),
        ),
        "subproblem_started": lambda: events.subproblem_started_event(
            session_id,
            data.get("sub_problem_index", 0),
            data.get("sub_problem_id", ""),
            data.get("goal", ""),
            data.get("total_sub_problems", 1),
        ),
        "initial_round_started": lambda: events.initial_round_started_event(
            session_id, data.get("experts", [])
        ),
        "contribution": lambda: events.contribution_event(
            session_id,
            data.get("persona_code", ""),
            data.get("persona_name", ""),
            data.get("content", ""),
            data.get("round", 1),
            archetype=data.get("archetype"),
            domain_expertise=data.get("domain_expertise"),
            summary=data.get("summary"),
            contribution_type=data.get("contribution_type"),
            sub_problem_index=data.get("sub_problem_index"),
        ),
        "facilitator_decision": lambda: events.facilitator_decision_event(
            session_id,
            data.get("action", ""),
            data.get("reasoning", ""),
            data.get("round", 1),
        ),
        "moderator_intervention": lambda: events.moderator_intervention_event(
            session_id,
            data.get("moderator_type", ""),
            data.get("content", ""),
            data.get("trigger_reason", ""),
            data.get("round", 1),
        ),
        "convergence": lambda: events.convergence_event(
            session_id,
            data.get("score", 0.0),
            data.get("converged", False),
            data.get("round", 1),
            data.get("threshold", 0.85),
            data.get("should_stop", False),
            data.get("stop_reason"),
            data.get("max_rounds", 10),
            data.get("sub_problem_index", 0),
            data.get("novelty_score"),
            data.get("conflict_score"),
            data.get("drift_events", 0),
        ),
        "round_started": lambda: events.round_started_event(
            session_id, data.get("round_number", 1)
        ),
        "voting_started": lambda: events.voting_started_event(session_id, data.get("experts", [])),
        "persona_vote": lambda: events.persona_vote_event(
            session_id,
            data.get("persona_code", ""),
            data.get("persona_name", ""),
            data.get("recommendation", ""),
            data.get("confidence", 0.0),
            data.get("reasoning", ""),
            data.get("conditions", []),
        ),
        "voting_complete": lambda: events.voting_complete_event(
            session_id, data.get("votes_count", 0), data.get("consensus_level", "unknown")
        ),
        "synthesis_started": lambda: events.synthesis_started_event(session_id),
        "synthesis_complete": lambda: events.synthesis_complete_event(
            session_id,
            data.get("synthesis", ""),
            data.get("word_count", 0),
            data.get("sub_problem_index"),
        ),
        "subproblem_complete": lambda: events.subproblem_complete_event(
            session_id,
            data.get("sub_problem_index", 0),
            data.get("sub_problem_id", ""),
            data.get("goal", ""),
            data.get("synthesis", ""),
            data.get("cost", 0.0),
            data.get("duration_seconds", 0.0),
            data.get("expert_panel", []),
            data.get("contribution_count", 0),
            data.get("expert_summaries", {}),  # AUDIT FIX (Priority 3, Task 3.2)
        ),
        "meta_synthesis_started": lambda: events.meta_synthesis_started_event(
            session_id,
            data.get("sub_problem_count", 0),
            data.get("total_contributions", 0),
            data.get("total_cost", 0.0),
        ),
        "meta_synthesis_complete": lambda: events.meta_synthesis_complete_event(
            session_id, data.get("synthesis", ""), data.get("word_count", 0)
        ),
        "phase_cost_breakdown": lambda: events.phase_cost_breakdown_event(
            session_id, data.get("phase_costs", {}), data.get("total_cost", 0.0)
        ),
        "complete": lambda: events.complete_event(
            session_id,
            data.get("final_output", ""),
            data.get("total_cost", 0.0),
            data.get("total_rounds", 0),
        ),
        "error": lambda: events.error_event(
            session_id, data.get("error", ""), data.get("error_type")
        ),
        "clarification_requested": lambda: events.clarification_requested_event(
            session_id, data.get("question", ""), data.get("reason", ""), data.get("round", 1)
        ),
        "clarification_required": lambda: events.clarification_required_event(
            session_id,
            data.get("questions", []),
            data.get("phase", "pre_deliberation"),
            data.get("reason", ""),
        ),
    }

    formatter = formatters.get(event_type)
    if formatter:
        return formatter()
    else:
        # Fallback: Generic event
        return events.format_sse_event(event_type, data)


async def stream_session_events(
    session_id: str,
    last_event_id: str | None = None,
    strip_cost_data: bool = False,
) -> AsyncGenerator[str, None]:
    r"""Stream deliberation events for a session via SSE using Redis PubSub.

    Supports session resume via Last-Event-ID header. If provided, replays
    any missed events from history before streaming new events.

    Security: When strip_cost_data=True, cost-related fields are stripped from events.

    Args:
        session_id: Session identifier
        last_event_id: Optional Last-Event-ID from SSE reconnection (format: session_id:sequence)
        strip_cost_data: If True, strip cost data from events (for non-admin users)

    Yields:
        SSE-formatted event strings with id field for resume support

    Examples:
        >>> async for event in stream_session_events("bo1_abc123"):
        ...     print(event)  # SSE formatted: "id: bo1_abc123:1\nevent: node_start\ndata: {...}\n\n"
        >>> # Resume from event 5:
        >>> async for event in stream_session_events("bo1_abc123", "bo1_abc123:5"):
        ...     print(event)  # Events with sequence > 5
    """
    from backend.api.events import make_event_id, parse_event_id

    redis_manager = get_redis_manager()
    redis_client = redis_manager.redis

    # Create pubsub connection
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    channel = f"events:{session_id}"
    _history_key = f"events_history:{session_id}"  # noqa: F841 - reserved for gap detection

    # SSE lifecycle tracking (P1: observability)
    connect_time = time.time()
    events_sent = 0

    # Parse last_event_id to get resume sequence
    resume_from_sequence = 0
    if last_event_id:
        parsed = parse_event_id(last_event_id)
        if parsed:
            _, resume_from_sequence = parsed
            logger.info(
                f"[SSE RESUME] session={session_id}, resuming from sequence {resume_from_sequence}"
            )
            metrics.increment("sse.resume_attempts")

    # Track seen sequences to dedupe between replay and live
    seen_sequences: set[int] = set()

    try:
        # Subscribe to PubSub FIRST to avoid missing events during replay
        pubsub.subscribe(channel)

        # Increment active SSE connections metric
        metrics.increment("sse.connections.active")

        # Send connection confirmation event
        yield node_start_event("stream_connected", session_id)
        events_sent += 1

        # Log SSE connection lifecycle
        logger.info(
            f"[SSE CONNECT] session={session_id}, channel={channel}, "
            f"last_event_id={last_event_id}, timestamp={connect_time:.3f}"
        )

        # REPLAY: If resuming, fetch missed events from history (with Redis/PostgreSQL fallback)
        if resume_from_sequence > 0:
            try:
                from backend.api.event_publisher import get_event_history_with_fallback

                # Use fallback function that handles Redis connection errors
                missed_events = await get_event_history_with_fallback(
                    redis_client=redis_client if redis_manager.is_available else None,
                    session_id=session_id,
                    last_event_id=last_event_id,
                )

                # GAP DETECTION: Check for missing events between resume point and first replayed event
                if missed_events:
                    first_seq = missed_events[0].get("sequence", 0)
                    expected_seq = resume_from_sequence + 1

                    # Check for gap at the start (events lost before first replayed event)
                    if first_seq > expected_seq:
                        missed_count = first_seq - expected_seq
                        logger.warning(
                            f"[SSE GAP] session={session_id}, expected_seq={expected_seq}, "
                            f"actual_seq={first_seq}, missed={missed_count}"
                        )
                        metrics.increment("sse.sequence_gaps")
                        metrics.increment("sse.sequence_gaps.missed_events", missed_count)

                        # Emit gap_detected event before replay
                        yield gap_detected_event(session_id, expected_seq, first_seq, missed_count)
                        events_sent += 1

                    # Check for internal gaps in the replayed sequence
                    prev_seq = first_seq
                    for _i, payload in enumerate(missed_events[1:], start=1):
                        curr_seq = payload.get("sequence", 0)
                        if curr_seq > prev_seq + 1:
                            internal_gap = curr_seq - prev_seq - 1
                            logger.warning(
                                f"[SSE GAP INTERNAL] session={session_id}, "
                                f"after_seq={prev_seq}, gap={internal_gap}"
                            )
                            metrics.increment("sse.sequence_gaps.internal")
                        prev_seq = curr_seq

                replay_count = 0
                for payload in missed_events:
                    try:
                        seq = payload.get("sequence", 0)
                        event_type = payload.get("event_type")
                        data = payload.get("data", {})

                        # Security: Filter cost data for non-admin users
                        if strip_cost_data:
                            if event_type in COST_EVENT_TYPES:
                                continue  # Skip cost-only events entirely
                            data = strip_cost_data_from_event(data) or data

                        event_id = make_event_id(session_id, seq)

                        # Track as seen to dedupe later
                        seen_sequences.add(seq)

                        # Format and yield with event ID
                        sse_event = format_sse_for_type(event_type, data)
                        # Inject event ID into SSE output
                        sse_event = f"id: {event_id}\n{sse_event}"
                        yield sse_event
                        events_sent += 1
                        replay_count += 1
                    except (json.JSONDecodeError, KeyError):
                        continue

                if replay_count > 0:
                    logger.info(
                        f"[SSE REPLAY] session={session_id}, replayed {replay_count} events"
                    )
                    metrics.increment("sse.events_replayed", replay_count)

            except Exception as e:
                logger.warning(f"Failed to replay events for {session_id}: {e}")

        # Track keepalive timing
        last_keepalive = time.time()
        keepalive_interval = 15  # Send keepalive every 15 seconds

        # P2-005: Track time between messages for performance monitoring
        last_message_time = time.time()

        # Stream events from Redis pubsub
        while True:
            # Check for message with timeout
            # P2-005 Quick Win: Reduced from 1.0s to 0.1s for faster event delivery
            message = pubsub.get_message(timeout=0.1)

            if message and message["type"] == "message":
                # P2-005: Track SSE gap (time between messages)
                now = time.time()
                gap_ms = (now - last_message_time) * 1000
                metrics.observe("sse.gap_ms", gap_ms)
                last_message_time = now

                try:
                    # Parse event payload
                    payload = json.loads(message["data"])
                    event_type = payload.get("event_type")
                    data = payload.get("data", {})
                    seq = payload.get("sequence", 0)

                    # Dedupe: skip if already sent during replay
                    if seq in seen_sequences:
                        continue

                    # Security: Filter cost data for non-admin users
                    if strip_cost_data:
                        if event_type in COST_EVENT_TYPES:
                            continue  # Skip cost-only events entirely
                        data = strip_cost_data_from_event(data) or data

                    # Create event ID for SSE resume support
                    event_id = make_event_id(session_id, seq) if seq > 0 else None

                    # Format as SSE using event formatters
                    sse_event = format_sse_for_type(event_type, data)

                    # Inject event ID for resume support
                    if event_id:
                        sse_event = f"id: {event_id}\n{sse_event}"

                    yield sse_event
                    events_sent += 1

                    # Reset keepalive timer on message
                    last_keepalive = time.time()

                    # If complete event, send explicit close and then break
                    if event_type == "complete":
                        logger.info(f"Session {session_id} completed, closing stream")
                        yield format_sse_for_type("stream_closed", {"reason": "session_complete"})
                        break

                    # If error event that's not recoverable, close stream
                    if event_type == "error":
                        logger.warning(f"Session {session_id} error event, closing stream")
                        break

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse event for session {session_id}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing event for session {session_id}: {e}")
                    continue

            # Send keepalive if interval elapsed
            now = time.time()
            if now - last_keepalive >= keepalive_interval:
                yield ": keepalive\n\n"
                last_keepalive = now

            # P2-005 Quick Win: Reduced from 0.1s to 0.01s for faster event delivery
            await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        # Client disconnected
        logger.info(f"Client disconnected from stream: {session_id}")
    except Exception as e:
        logger.error(f"Error streaming session {session_id}: {e}", exc_info=True)
        yield error_event(session_id, str(e), error_type=type(e).__name__)
    finally:
        # Calculate connection duration
        disconnect_time = time.time()
        duration_seconds = disconnect_time - connect_time

        # Decrement active SSE connections metric
        metrics.decrement("sse.connections.active")

        # Log SSE disconnect lifecycle
        logger.info(
            f"[SSE DISCONNECT] session={session_id}, duration_seconds={duration_seconds:.2f}, "
            f"events_sent={events_sent}"
        )

        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
        except Exception as e:
            logger.warning(f"Error closing pubsub for session {session_id}: {e}")


@router.get(
    "/{session_id}/stream",
    summary="Stream deliberation events via SSE",
    description="""
    Stream real-time deliberation events for a session using Server-Sent Events (SSE).

    **Rate Limited:** 5 connections per minute per IP to prevent connection exhaustion.

    **Session Resume Support:**
    If the client disconnects and reconnects, include the `Last-Event-ID` header
    with the ID from the last received event. The server will replay any missed
    events before resuming live streaming.

    Event types:
    - `node_start` - Node execution started
    - `node_end` - Node execution completed
    - `contribution` - Persona contributed to discussion
    - `facilitator_decision` - Facilitator made a decision
    - `convergence` - Convergence check result
    - `complete` - Deliberation finished
    - `error` - Error occurred

    The connection will remain open until the deliberation completes or
    the client disconnects.
    """,
    responses={
        200: {
            "description": "SSE event stream",
            "content": {
                "text/event-stream": {
                    "example": "id: bo1_abc123:1\nevent: node_start\ndata: {...}\n\n"
                }
            },
        },
        403: {
            "description": "Not authorized to access this session",
            "model": ErrorResponse,
            "content": {
                "application/json": {"example": {"detail": "Not authorized to access this session"}}
            },
        },
        404: {
            "description": "Session not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {"detail": "Session not found", "session_id": "bo1_abc123"}
                }
            },
        },
        409: {
            "description": "Session not ready for streaming",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "not_started": {
                            "summary": "Session not started",
                            "value": {
                                "detail": "Session bo1_abc123 has not been started yet. Call /start endpoint first.",
                                "session_id": "bo1_abc123",
                                "status": "created",
                            },
                        },
                        "paused": {
                            "summary": "Session paused",
                            "value": {
                                "detail": "Session bo1_abc123 is paused. Call /resume endpoint to continue.",
                                "session_id": "bo1_abc123",
                                "status": "paused",
                            },
                        },
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Session bo1_abc123 failed: killed",
                        "error_code": "SESSION_FAILED",
                    }
                }
            },
        },
    },
)
@limiter.limit(STREAMING_RATE_LIMIT)
async def stream_deliberation(
    request: Request,
    session_id: str,
    session_data: VerifiedSession,
    current_user: dict = Depends(get_current_user),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """Stream deliberation events via Server-Sent Events.

    Supports session resume via Last-Event-ID header.

    Security: Cost data is stripped from events for non-admin users.
    Rate Limited: 5 connections per minute per IP to prevent connection exhaustion.

    Args:
        request: FastAPI request object (used by rate limiter)
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        current_user: Current authenticated user (for admin check)
        last_event_id: Optional Last-Event-ID header for resume support

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If session not found
    """
    user_is_admin = is_admin(current_user)
    try:
        # Unpack verified session data
        user_id, metadata = session_data

        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Check metadata status to determine if graph is ready for streaming
        # Note: LangGraph uses checkpoint:* keys, not session:* keys, so we check metadata
        # status instead of waiting for state that will never exist
        status = metadata.get("status") if metadata else None

        # If no status (session metadata missing or incomplete), treat as not found
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or not properly initialized",
            )

        if status in ["killed", "failed"]:
            raise HTTPException(
                status_code=500,
                detail=f"Session {session_id} failed: {status}",
            )

        if status == "created":
            # Graph hasn't started yet - frontend should call /start first
            raise HTTPException(
                status_code=409,
                detail=f"Session {session_id} has not been started yet. Call /start endpoint first.",
            )

        if status == "paused":
            # Session is paused - frontend should call /resume first
            raise HTTPException(
                status_code=409,
                detail=f"Session {session_id} is paused. Call /resume endpoint to continue.",
            )

        # Status is "running" or "completed" - proceed to streaming
        # Events flow through Redis PubSub, and history is available via /events endpoint
        logger.info(
            f"SSE connection established for session {session_id} "
            f"(status: {status}, last_event_id: {last_event_id})"
        )

        # Return streaming response with resume support
        # Security: Pass admin flag to filter cost events for non-admin users
        return StreamingResponse(
            stream_session_events(
                session_id, last_event_id=last_event_id, strip_cost_data=not user_is_admin
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start stream for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start stream: {str(e)}",
        ) from e
