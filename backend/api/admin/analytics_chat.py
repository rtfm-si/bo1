"""Admin analytics chat API — LLM-powered SQL analytics console.

Provides SSE streaming endpoint for natural language database queries,
plus CRUD for conversation history and saved analyses.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.admin_analytics.agent import AdminAnalyticsAgent
from backend.services.admin_analytics.saved_analyses import (
    create_conversation,
    delete_saved_analysis,
    get_conversation_messages,
    get_saved_analysis,
    list_conversations,
    list_saved_analyses,
    save_analysis,
    save_message,
)
from bo1.logging import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics-chat", tags=["admin-analytics-chat"])


# =============================================================================
# Request / Response Models
# =============================================================================


class AskRequest(BaseModel):
    """Request for analytics question."""

    question: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = Field(None, description="Continue existing conversation")
    model: str = Field("sonnet", pattern="^(sonnet|opus)$", description="Model for SQL generation")


class SaveAnalysisRequest(BaseModel):
    """Request to save an analysis for re-running."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=1000)
    original_question: str = Field(..., min_length=1, max_length=5000)
    steps: list[dict] = Field(..., description="Analysis steps with SQL and chart config")


# =============================================================================
# SSE Streaming Endpoint
# =============================================================================


async def _stream_analytics(
    question: str,
    model: str,
    conversation_id: str | None,
    admin_user_id: str,
) -> AsyncGenerator[str, None]:
    """Stream analytics response as SSE events."""
    # Get or create conversation
    if not conversation_id:
        conv = create_conversation(admin_user_id, question[:100], model)
        conversation_id = conv["id"]
        yield f"event: conversation\ndata: {json.dumps({'conversation_id': conversation_id})}\n\n"

    # Save user message
    save_message(conversation_id, "user", question)

    # Get conversation history for context
    messages = get_conversation_messages(conversation_id)
    history = []
    for msg in messages[:-1]:  # Exclude current message
        history.append({"role": msg["role"], "content": msg["content"]})

    # Run agent
    agent = AdminAnalyticsAgent(model_preference=model)
    all_steps = []
    suggestions = []
    total_cost = 0.0

    async for event in agent.run(question, history, admin_user_id):
        event_type = event.get("event", "")
        event_data = event.get("data", {})

        # Collect results for saving
        if event_type == "done":
            all_steps = event_data.get("steps", [])
            suggestions = event_data.get("suggestions", [])
            total_cost = event_data.get("total_cost", 0.0)

        # Stream SSE
        yield f"event: {event_type}\ndata: {json.dumps(event_data, default=str)}\n\n"

    # Save assistant message with full results
    summary_parts = []
    for step in all_steps:
        if "summary" in step:
            summary_parts.append(step["summary"])

    save_message(
        conversation_id,
        "assistant",
        "\n\n".join(summary_parts) if summary_parts else "Analysis complete.",
        steps=all_steps,
        suggestions=suggestions,
        llm_cost=total_cost,
    )


@router.post("/ask")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("ask analytics question")
async def ask_analytics(
    request: Request,
    body: AskRequest,
    admin_user_id: str = Depends(require_admin_any),
) -> StreamingResponse:
    """Ask an analytics question — returns SSE stream."""
    return StreamingResponse(
        _stream_analytics(
            question=body.question,
            model=body.model,
            conversation_id=body.conversation_id,
            admin_user_id=admin_user_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Conversation History
# =============================================================================


@router.get("/history")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list analytics history")
async def get_history(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    admin_user_id: str = Depends(require_admin_any),
) -> list[dict[str, Any]]:
    """List analytics conversations."""
    return list_conversations(admin_user_id, limit)


@router.get("/history/{conversation_id}")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get analytics conversation")
async def get_conversation(
    request: Request,
    conversation_id: str,
    admin_user_id: str = Depends(require_admin_any),
) -> dict[str, Any]:
    """Get messages for a single conversation."""
    messages = get_conversation_messages(conversation_id)
    if not messages:
        raise http_error(ErrorCode.NOT_FOUND, "Conversation not found", status=404)
    return {"conversation_id": conversation_id, "messages": messages}


# =============================================================================
# Saved Analyses
# =============================================================================


@router.post("/saved")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("save analytics analysis")
async def create_saved(
    request: Request,
    body: SaveAnalysisRequest,
    admin_user_id: str = Depends(require_admin_any),
) -> dict[str, Any]:
    """Save an analysis for later re-running."""
    return save_analysis(
        admin_user_id=admin_user_id,
        title=body.title,
        description=body.description,
        original_question=body.original_question,
        steps=body.steps,
    )


@router.get("/saved")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list saved analyses")
async def list_saved(
    request: Request,
    admin_user_id: str = Depends(require_admin_any),
) -> list[dict[str, Any]]:
    """List saved analyses."""
    return list_saved_analyses(admin_user_id)


@router.post("/saved/{analysis_id}/run")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("rerun saved analysis")
async def rerun_saved(
    request: Request,
    analysis_id: str,
    admin_user_id: str = Depends(require_admin_any),
) -> StreamingResponse:
    """Re-run a saved analysis with fresh data."""
    analysis = get_saved_analysis(analysis_id)
    if not analysis:
        raise http_error(ErrorCode.NOT_FOUND, "Saved analysis not found", status=404)

    # Re-run using the original question
    return StreamingResponse(
        _stream_analytics(
            question=analysis["original_question"],
            model="sonnet",
            conversation_id=None,
            admin_user_id=admin_user_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/saved/{analysis_id}")
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete saved analysis")
async def delete_saved(
    request: Request,
    analysis_id: str,
    admin_user_id: str = Depends(require_admin_any),
) -> dict[str, Any]:
    """Delete a saved analysis."""
    if not delete_saved_analysis(analysis_id):
        raise http_error(ErrorCode.NOT_FOUND, "Saved analysis not found", status=404)
    return {"deleted": True, "analysis_id": analysis_id}
