"""Mentor Chat API endpoints.

Provides:
- POST /api/v1/mentor/chat - Chat with mentor (SSE streaming)
- GET /api/v1/mentor/conversations - List mentor conversations
- GET /api/v1/mentor/conversations/{id} - Get conversation detail
- DELETE /api/v1/mentor/conversations/{id} - Delete conversation
"""

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.errors import handle_api_errors
from backend.services.mentor_context import MentorContext, get_mentor_context_service
from backend.services.mentor_conversation_repo import get_mentor_conversation_repo
from backend.services.mentor_persona import auto_select_persona, validate_persona
from bo1.llm.client import ClaudeClient
from bo1.prompts.mentor import (
    build_mentor_prompt,
    format_active_actions,
    format_business_context,
    format_conversation_history,
    format_dataset_summaries,
    format_recent_meetings,
    get_mentor_system_prompt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/mentor", tags=["mentor"])


# =============================================================================
# Request/Response Models
# =============================================================================


class MentorChatRequest(BaseModel):
    """Request model for mentor chat."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's message to the mentor",
    )
    conversation_id: str | None = Field(
        None,
        description="Existing conversation ID to continue (optional)",
    )
    persona: str | None = Field(
        None,
        description="Persona to use: general, action_coach, data_analyst (auto-selects if not provided)",
    )


class MentorConversationResponse(BaseModel):
    """Response model for mentor conversation summary."""

    id: str
    user_id: str
    persona: str
    created_at: str
    updated_at: str
    message_count: int
    context_sources: list[str]


class MentorConversationListResponse(BaseModel):
    """Response model for listing mentor conversations."""

    conversations: list[MentorConversationResponse]
    total: int


class MentorMessage(BaseModel):
    """Model for a single mentor message."""

    role: str
    content: str
    timestamp: str
    persona: str | None = None


class MentorConversationDetailResponse(BaseModel):
    """Response model for full mentor conversation."""

    id: str
    user_id: str
    persona: str
    created_at: str
    updated_at: str
    message_count: int
    context_sources: list[str]
    messages: list[MentorMessage]


# =============================================================================
# SSE Streaming
# =============================================================================


async def _stream_mentor_response(
    user_id: str,
    message: str,
    conversation_id: str | None,
    persona: str | None,
) -> AsyncGenerator[str, None]:
    """Stream the mentor response as SSE events.

    Events:
    - thinking: Processing started
    - context: Context sources loaded
    - response: LLM response text
    - done: Processing complete with conversation_id
    - error: Error occurred
    """
    mentor_context_service = get_mentor_context_service()
    mentor_conv_repo = get_mentor_conversation_repo()

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
            # Auto-select persona if not provided
            selected_persona = (
                validate_persona(persona) if persona else auto_select_persona(message)
            )
            conversation = mentor_conv_repo.create(user_id, selected_persona)
            conversation_id = conversation["id"]

        # Determine persona (from request, conversation, or auto-select)
        if persona:
            selected_persona = validate_persona(persona)
        elif conversation.get("persona"):
            selected_persona = conversation["persona"]
        else:
            selected_persona = auto_select_persona(message)

        yield f"event: thinking\ndata: {json.dumps({'status': 'calling_llm', 'persona': selected_persona})}\n\n"

        # Add user message to conversation
        mentor_conv_repo.append_message(
            conversation_id,
            "user",
            message,
            persona=selected_persona,
            context_sources=context_sources,
        )

        # Format context for prompt
        business_ctx = format_business_context(context.business_context)
        meetings_ctx = format_recent_meetings(context.recent_meetings or [])
        actions_ctx = format_active_actions(context.active_actions or [])
        datasets_ctx = format_dataset_summaries(context.datasets or [])
        conv_history = format_conversation_history(conversation.get("messages", []))

        # Build prompt
        user_prompt = build_mentor_prompt(
            question=message,
            business_context=business_ctx,
            meetings_context=meetings_ctx,
            actions_context=actions_ctx,
            datasets_context=datasets_ctx,
            conversation_history=conv_history,
        )

        # Get system prompt for persona
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

        # Done event with conversation ID
        yield f"event: done\ndata: {json.dumps({'conversation_id': conversation_id, 'persona': selected_persona, 'tokens': usage.total_tokens})}\n\n"

    except Exception as e:
        logger.error(f"Error in mentor chat for user {user_id}: {e}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/chat",
    summary="Chat with mentor",
    description="Ask questions or get guidance from the AI mentor (SSE streaming)",
    responses={
        200: {
            "description": "SSE event stream",
            "content": {
                "text/event-stream": {"example": 'event: response\ndata: {"content": "..."}\n\n'}
            },
        },
    },
)
async def mentor_chat(
    request: MentorChatRequest,
    user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Chat with the AI mentor.

    Returns SSE events: thinking, context, response, done, error.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    return StreamingResponse(
        _stream_mentor_response(
            user_id,
            request.message,
            request.conversation_id,
            request.persona,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/conversations",
    response_model=MentorConversationListResponse,
    summary="List mentor conversations",
    description="List recent mentor conversations for the current user",
)
@handle_api_errors("list mentor conversations")
async def list_mentor_conversations(
    limit: int = Query(20, ge=1, le=100, description="Max conversations to return"),
    user: dict = Depends(get_current_user),
) -> MentorConversationListResponse:
    """List recent mentor conversations for the current user."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    mentor_conv_repo = get_mentor_conversation_repo()
    conversations = mentor_conv_repo.list_by_user(user_id, limit)

    return MentorConversationListResponse(
        conversations=[
            MentorConversationResponse(
                id=c["id"],
                user_id=c["user_id"],
                persona=c.get("persona", "general"),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                message_count=c["message_count"],
                context_sources=c.get("context_sources", []),
            )
            for c in conversations
        ],
        total=len(conversations),
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=MentorConversationDetailResponse,
    summary="Get mentor conversation",
    description="Get a mentor conversation with full message history",
)
@handle_api_errors("get mentor conversation")
async def get_mentor_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
) -> MentorConversationDetailResponse:
    """Get a mentor conversation with full message history."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    mentor_conv_repo = get_mentor_conversation_repo()
    conversation = mentor_conv_repo.get(conversation_id, user_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return MentorConversationDetailResponse(
        id=conversation["id"],
        user_id=conversation["user_id"],
        persona=conversation.get("persona", "general"),
        created_at=conversation["created_at"],
        updated_at=conversation["updated_at"],
        message_count=len(conversation.get("messages", [])),
        context_sources=conversation.get("context_sources", []),
        messages=[
            MentorMessage(
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
                persona=m.get("persona"),
            )
            for m in conversation.get("messages", [])
        ],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
    summary="Delete mentor conversation",
    description="Delete a mentor conversation",
)
@handle_api_errors("delete mentor conversation")
async def delete_mentor_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a mentor conversation."""
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    mentor_conv_repo = get_mentor_conversation_repo()
    deleted = mentor_conv_repo.delete(conversation_id, user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
