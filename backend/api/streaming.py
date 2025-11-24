"""SSE streaming endpoints for real-time deliberation updates.

Provides:
- GET /api/v1/sessions/{session_id}/stream - Stream deliberation events via SSE
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_redis_manager
from backend.api.events import (
    error_event,
    node_start_event,
)
from backend.api.middleware.auth import get_current_user
from backend.api.utils.validation import validate_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["streaming"])


@router.get(
    "/{session_id}/events",
    summary="Get session event history",
    description="""
    Get all historical events for a session from Redis.

    This endpoint returns all stored events for reconnection scenarios.
    Frontend should call this first to get history, then connect to SSE stream.
    """,
    responses={
        200: {"description": "Event history retrieved successfully"},
        404: {"description": "Session not found"},
        500: {"description": "Internal server error"},
    },
)
async def get_event_history(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get historical events for a session.

    Args:
        session_id: Session identifier
        user: Authenticated user data

    Returns:
        Dict with events array and count

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Verify session exists
        redis_manager = get_redis_manager()

        if not redis_manager.is_available:
            raise HTTPException(
                status_code=500,
                detail="Redis unavailable - cannot retrieve events",
            )

        # Check if session metadata exists
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

        # Load event history
        history_key = f"events_history:{session_id}"
        historical_events = redis_manager.redis.lrange(history_key, 0, -1)

        # Parse events
        events = []
        for event_data in historical_events:
            try:
                payload = json.loads(event_data)
                events.append(payload)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse historical event for {session_id}")
                continue

        logger.info(f"Retrieved {len(events)} historical events for session {session_id}")

        return {
            "session_id": session_id,
            "events": events,
            "count": len(events),
        }

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
        ),
        "persona_selection_complete": lambda: events.persona_selection_complete_event(
            session_id, data.get("personas", [])
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
            session_id, data.get("synthesis", ""), data.get("word_count", 0)
        ),
        "subproblem_complete": lambda: events.subproblem_complete_event(
            session_id,
            data.get("sub_problem_index", 0),
            data.get("sub_problem_id", ""),
            data.get("goal", ""),
            data.get("cost", 0.0),
            data.get("duration_seconds", 0.0),
            data.get("expert_panel", []),
            data.get("contribution_count", 0),
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
    }

    formatter = formatters.get(event_type)
    if formatter:
        return formatter()
    else:
        # Fallback: Generic event
        return events.format_sse_event(event_type, data)


async def stream_session_events(session_id: str) -> AsyncGenerator[str, None]:
    r"""Stream deliberation events for a session via SSE using Redis PubSub.

    This replaces the old polling approach with real-time event streaming
    from Redis PubSub channels. Events are published by EventCollector during
    graph execution.

    Args:
        session_id: Session identifier

    Yields:
        SSE-formatted event strings

    Examples:
        >>> async for event in stream_session_events("bo1_abc123"):
        ...     print(event)  # SSE formatted: "event: node_start\ndata: {...}\n\n"
    """
    import json
    import time

    redis_manager = get_redis_manager()
    redis_client = redis_manager.redis

    # Create pubsub connection
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    channel = f"events:{session_id}"

    try:
        # Frontend loads historical events via REST API (/api/v1/sessions/{id}/events)
        # So we don't replay history here - just subscribe to new events
        # This avoids duplicates and ensures clean separation of concerns
        pubsub.subscribe(channel)

        # Send connection confirmation event
        yield node_start_event("stream_connected", session_id)

        logger.info(f"SSE client subscribed to {channel} (history loaded via REST API)")

        # Track keepalive timing
        last_keepalive = time.time()
        keepalive_interval = 15  # Send keepalive every 15 seconds

        # Stream events from Redis pubsub
        while True:
            # Check for message with timeout
            message = pubsub.get_message(timeout=1.0)

            if message and message["type"] == "message":
                try:
                    # Parse event payload
                    payload = json.loads(message["data"])
                    event_type = payload.get("event_type")
                    data = payload.get("data", {})

                    # Format as SSE using event formatters
                    sse_event = format_sse_for_type(event_type, data)
                    yield sse_event

                    # Reset keepalive timer on message
                    last_keepalive = time.time()

                    # If complete event, close stream
                    if event_type == "complete":
                        logger.info(f"Session {session_id} completed, closing stream")
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

            # Small sleep to prevent busy loop
            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        # Client disconnected
        logger.info(f"Client disconnected from stream: {session_id}")
    except Exception as e:
        logger.error(f"Error streaming session {session_id}: {e}", exc_info=True)
        yield error_event(session_id, str(e), error_type=type(e).__name__)
    finally:
        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
        except Exception as e:
            logger.warning(f"Error closing pubsub for session {session_id}: {e}")
        logger.info(f"SSE client disconnected from {channel}")


@router.get(
    "/{session_id}/stream",
    summary="Stream deliberation events via SSE",
    description="""
    Stream real-time deliberation events for a session using Server-Sent Events (SSE).

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
            "content": {"text/event-stream": {"example": "event: node_start\ndata: {...}\n\n"}},
        },
        404: {"description": "Session not found"},
        500: {"description": "Internal server error"},
    },
)
async def stream_deliberation(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> StreamingResponse:
    """Stream deliberation events via Server-Sent Events.

    Args:
        session_id: Session identifier
        user: Authenticated user data

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If session not found
    """
    try:
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Verify session exists
        redis_manager = get_redis_manager()

        if not redis_manager.is_available:
            raise HTTPException(
                status_code=500,
                detail="Redis unavailable - cannot stream session",
            )

        # Check if session metadata exists (created via POST /api/v1/sessions)
        metadata = redis_manager.load_metadata(session_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

        # Wait for state to be initialized (with timeout)
        # This handles race condition where frontend connects before graph initializes state
        max_wait_seconds = 10
        poll_interval = 0.5
        elapsed = 0.0

        while elapsed < max_wait_seconds:
            state = redis_manager.load_state(session_id)
            if state:
                # State exists, proceed to streaming
                break

            # Check if session was killed/failed during initialization
            current_metadata = redis_manager.load_metadata(session_id)
            if current_metadata and current_metadata.get("status") in ["killed", "failed"]:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} failed to initialize: {current_metadata.get('status')}",
                )

            # Wait and retry
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # If we exit the loop without finding state, session may still be initializing
        # Continue anyway and let stream_session_events handle it
        logger.info(f"SSE connection established for session {session_id} after {elapsed:.1f}s")

        # Return streaming response
        return StreamingResponse(
            stream_session_events(session_id),
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
