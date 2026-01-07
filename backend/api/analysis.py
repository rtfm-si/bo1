"""Data Analysis API endpoints.

Provides unified interface for data analysis:
- POST /api/v1/analysis/ask - Ask data questions (SSE streaming)
  - With dataset_id: Routes to dataset Q&A
  - Without dataset_id: Uses mentor with data_analyst persona
"""

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.tier_limits import record_mentor_usage, require_mentor_limit
from backend.api.utils.errors import http_error
from backend.services.mentor_context import MentorContext, get_mentor_context_service
from backend.services.mentor_conversation_repo import get_mentor_conversation_repo
from backend.services.usage_tracking import UsageResult
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error
from bo1.prompts.mentor import (
    build_mentor_prompt,
    format_active_actions,
    format_business_context,
    format_conversation_history,
    format_dataset_summaries,
    format_recent_meetings,
    get_mentor_system_prompt,
)
from bo1.security import sanitize_for_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/analysis", tags=["analysis"])


# =============================================================================
# Request/Response Models
# =============================================================================


class AnalysisAskRequest(BaseModel):
    """Request model for analysis questions."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Question about data or analysis",
    )
    dataset_id: str | None = Field(
        None,
        description="Dataset ID to analyze (optional - uses general guidance if not provided)",
    )
    conversation_id: str | None = Field(
        None,
        description="Existing conversation ID to continue (optional)",
    )


# =============================================================================
# SSE Streaming
# =============================================================================


async def _stream_analysis_response(
    user_id: str,
    question: str,
    dataset_id: str | None,
    conversation_id: str | None,
) -> AsyncGenerator[str, None]:
    """Stream the analysis response as SSE events.

    Events:
    - thinking: Processing started
    - context: Context sources loaded
    - response: LLM response text
    - done: Processing complete with conversation_id
    - error: Error occurred
    """
    # If dataset_id provided, delegate to dataset Q&A
    if dataset_id:
        # Import here to avoid circular imports
        from backend.api.datasets import _stream_ask_response

        async for chunk in _stream_ask_response(dataset_id, user_id, question, conversation_id):
            yield chunk
        return

    # Otherwise, use mentor with data_analyst persona
    mentor_context_service = get_mentor_context_service()
    mentor_conv_repo = get_mentor_conversation_repo()
    selected_persona = "data_analyst"

    try:
        yield f"event: thinking\ndata: {json.dumps({'status': 'loading_context'})}\n\n"

        # Gather context
        context: MentorContext = mentor_context_service.gather_context(user_id)
        context_sources = context.sources_used()

        yield f"event: context\ndata: {json.dumps({'sources': context_sources})}\n\n"

        # Get or create conversation
        if conversation_id:
            conversation = mentor_conv_repo.get(conversation_id, user_id)
            if not conversation:
                yield f"event: error\ndata: {json.dumps({'error': 'Conversation not found'})}\n\n"
                return
        else:
            conversation = mentor_conv_repo.create(user_id, selected_persona)
            conversation_id = conversation["id"]

        yield f"event: thinking\ndata: {json.dumps({'status': 'calling_llm', 'persona': selected_persona})}\n\n"

        # Add user message to conversation
        mentor_conv_repo.append_message(
            conversation_id,
            "user",
            question,
            persona=selected_persona,
            context_sources=context_sources,
        )

        # Format context for prompt
        business_ctx = format_business_context(context.business_context)
        meetings_ctx = format_recent_meetings(context.recent_meetings or [])
        actions_ctx = format_active_actions(context.active_actions or [])
        datasets_ctx = format_dataset_summaries(context.datasets or [])
        conv_history = format_conversation_history(conversation.get("messages", []))

        # Build prompt (sanitize user input to prevent prompt injection)
        safe_question = sanitize_for_prompt(question)
        user_prompt = build_mentor_prompt(
            question=safe_question,
            business_context=business_ctx,
            meetings_context=meetings_ctx,
            actions_context=actions_ctx,
            datasets_context=datasets_ctx,
            conversation_history=conv_history,
        )

        # Get system prompt for data_analyst persona
        system_prompt = get_mentor_system_prompt(selected_persona)

        # Call LLM
        client = ClaudeClient()
        response, usage = await client.call(
            model="sonnet",
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=2000,
            temperature=0.7,
        )

        # Stream response
        yield f"event: response\ndata: {json.dumps({'content': response})}\n\n"

        # Save assistant response to conversation
        mentor_conv_repo.append_message(
            conversation_id,
            "assistant",
            response,
            persona=selected_persona,
            context_sources=context_sources,
        )

        # Done event
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id, 'persona': selected_persona, 'tokens': usage.total_tokens})}\n\n"

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_ANALYSIS_ERROR,
            f"Error in analysis for user {user_id}: {e}",
            user_id=user_id,
        )
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/ask",
    summary="Ask data analysis question",
    description="Ask questions about datasets or get general data analysis guidance (SSE streaming)",
    responses={
        200: {
            "description": "SSE event stream",
            "content": {
                "text/event-stream": {"example": 'event: response\ndata: {"content": "..."}\n\n'}
            },
        },
    },
)
async def ask_analysis(
    request: AnalysisAskRequest,
    user: dict = Depends(get_current_user),
    tier_usage: UsageResult = Depends(require_mentor_limit),
) -> StreamingResponse:
    """Ask data analysis questions.

    If dataset_id is provided, routes to dataset Q&A.
    Otherwise, uses mentor with data_analyst persona.

    Returns SSE events: thinking, context, response, done, error.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise http_error(ErrorCode.AUTH_TOKEN_ERROR, "User ID not found", 401)

    # Record usage for tier tracking (only for non-dataset queries)
    if not request.dataset_id:
        try:
            record_mentor_usage(user_id)
        except Exception as e:
            logger.debug(f"Usage tracking failed (non-blocking): {e}")

    return StreamingResponse(
        _stream_analysis_response(
            user_id,
            request.question,
            request.dataset_id,
            request.conversation_id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
