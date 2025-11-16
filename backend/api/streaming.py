"""SSE streaming endpoints for real-time deliberation updates.

Provides:
- GET /api/v1/sessions/{session_id}/stream - Stream deliberation events via SSE
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.events import (
    complete_event,
    error_event,
    node_end_event,
    node_start_event,
)
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["streaming"])


def _create_redis_manager() -> RedisManager:
    """Create Redis manager instance.

    Returns:
        RedisManager instance
    """
    return RedisManager()


async def stream_session_events(session_id: str) -> AsyncGenerator[str, None]:
    r"""Stream deliberation events for a session via SSE.

    This is a simplified implementation that demonstrates SSE streaming.
    In production, this would connect to the actual LangGraph execution
    and stream real events.

    Args:
        session_id: Session identifier

    Yields:
        SSE-formatted event strings

    Examples:
        >>> async for event in stream_session_events("bo1_abc123"):
        ...     print(event)  # SSE formatted: "event: node_start\ndata: {...}\n\n"
    """
    try:
        # Send initial connection event
        yield node_start_event("stream_connected", session_id)

        # Poll for state updates
        redis_manager = _create_redis_manager()

        # In a real implementation, we would:
        # 1. Use graph.astream_events() to get real-time events
        # 2. Filter events for client consumption
        # 3. Format and yield each event
        #
        # For now, we'll demonstrate with state polling

        last_round = -1
        max_iterations = 100  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Load current state
            state = redis_manager.load_state(session_id)

            if not state:
                # Session not found or completed
                yield error_event(session_id, "Session not found or completed")
                break

            # Check for completion
            if isinstance(state, dict) and state.get("final_output"):
                yield complete_event(
                    session_id=session_id,
                    final_output=state["final_output"],
                    total_cost=state.get("total_cost", 0.0),
                    total_rounds=state.get("round_number", 0),
                )
                break

            # Check for new round
            if isinstance(state, dict):
                current_round = state.get("round_number", 0)
                if current_round > last_round:
                    last_round = current_round

                    # Send round update event
                    yield node_start_event(f"round_{current_round}", session_id)

            # Poll every second
            await asyncio.sleep(1.0)

        # Send completion event
        yield node_end_event("stream_ended", session_id)

    except asyncio.CancelledError:
        # Client disconnected
        logger.info(f"Client disconnected from stream: {session_id}")
        yield error_event(session_id, "Client disconnected")
    except Exception as e:
        logger.error(f"Error streaming session {session_id}: {e}")
        yield error_event(session_id, str(e), error_type=type(e).__name__)


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
async def stream_deliberation(session_id: str) -> StreamingResponse:
    """Stream deliberation events via Server-Sent Events.

    Args:
        session_id: Session identifier

    Returns:
        StreamingResponse with SSE events

    Raises:
        HTTPException: If session not found
    """
    try:
        # Verify session exists
        redis_manager = _create_redis_manager()

        if not redis_manager.is_available:
            raise HTTPException(
                status_code=500,
                detail="Redis unavailable - cannot stream session",
            )

        # Check if session exists (metadata or state)
        metadata = redis_manager.load_metadata(session_id)
        if not metadata and not redis_manager.load_state(session_id):
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {session_id}",
            )

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
