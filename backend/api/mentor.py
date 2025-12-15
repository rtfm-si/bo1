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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.tier_limits import record_mentor_usage, require_mentor_limit
from backend.api.utils.errors import handle_api_errors
from backend.services.mention_parser import parse_mentions
from backend.services.mention_resolver import get_mention_resolver
from backend.services.mentor_context import MentorContext, get_mentor_context_service
from backend.services.mentor_conversation_repo import get_mentor_conversation_repo
from backend.services.mentor_persona import (
    auto_select_persona,
    list_all_personas,
    validate_persona,
)
from backend.services.usage_tracking import UsageResult
from bo1.llm.client import ClaudeClient
from bo1.prompts.mentor import (
    build_mentor_prompt,
    format_active_actions,
    format_business_context,
    format_conversation_history,
    format_dataset_summaries,
    format_failure_patterns,
    format_mentioned_context,
    format_recent_meetings,
    get_mentor_system_prompt,
)
from bo1.security import sanitize_for_prompt

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


class MentorPersonaResponse(BaseModel):
    """Response model for a mentor persona."""

    id: str
    name: str
    description: str
    expertise: list[str]
    icon: str


class MentorPersonaListResponse(BaseModel):
    """Response model for listing mentor personas."""

    personas: list[MentorPersonaResponse]
    total: int


# =============================================================================
# Mention Search Models
# =============================================================================


class MentionSuggestion(BaseModel):
    """A single mention suggestion for autocomplete."""

    id: str
    type: str  # "meeting" | "action" | "dataset"
    title: str
    preview: str | None = None


class MentionSearchResponse(BaseModel):
    """Response model for mention search."""

    suggestions: list[MentionSuggestion]
    total: int


# =============================================================================
# Repeated Topics Models
# =============================================================================


class RepeatedTopicResponse(BaseModel):
    """Response model for a detected repeated topic."""

    topic_summary: str = Field(..., description="Summary of the repeated topic")
    count: int = Field(..., description="Number of times this topic was asked")
    first_asked: str = Field(..., description="ISO timestamp of first occurrence")
    last_asked: str = Field(..., description="ISO timestamp of most recent occurrence")
    conversation_ids: list[str] = Field(
        ..., description="IDs of conversations containing this topic"
    )
    representative_messages: list[str] = Field(
        ..., description="Sample messages from this topic cluster"
    )
    similarity_score: float = Field(
        ..., description="Average similarity score within cluster (0-1)"
    )


class RepeatedTopicsListResponse(BaseModel):
    """Response model for listing repeated topics."""

    topics: list[RepeatedTopicResponse]
    total: int
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")


# =============================================================================
# Failure Patterns Models
# =============================================================================


class ActionFailurePatternResponse(BaseModel):
    """Response model for a detected action failure pattern."""

    action_id: str = Field(..., description="Action UUID")
    title: str = Field(..., description="Action title")
    project_id: str | None = Field(None, description="Project UUID if assigned")
    project_name: str | None = Field(None, description="Project name if assigned")
    status: str = Field(..., description="Action status (cancelled or blocked)")
    priority: str = Field(..., description="Action priority")
    failure_reason: str | None = Field(None, description="Reason for failure")
    failure_category: str | None = Field(
        None, description="Category: blocker/scope_creep/dependency/unknown"
    )
    failed_at: str = Field(..., description="ISO timestamp of failure")
    tags: list[str] = Field(default_factory=list, description="Action tags")


class FailurePatternsResponse(BaseModel):
    """Response model for failure patterns analysis."""

    patterns: list[ActionFailurePatternResponse] = Field(..., description="List of failed actions")
    failure_rate: float = Field(..., ge=0.0, le=1.0, description="Failure rate (0.0-1.0)")
    total_actions: int = Field(..., description="Total actions in period")
    failed_actions: int = Field(..., description="Number of failed actions")
    period_days: int = Field(..., description="Analysis period in days")
    by_project: dict[str, int] = Field(..., description="Failure count by project name")
    by_category: dict[str, int] = Field(..., description="Failure count by category")
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")


# =============================================================================
# Improvement Plan Models
# =============================================================================


class ImprovementSuggestionResponse(BaseModel):
    """A single improvement suggestion."""

    category: str = Field(..., description="Category: execution, planning, knowledge, process")
    title: str = Field(..., description="Brief actionable title")
    description: str = Field(..., description="Explanation of the issue")
    action_steps: list[str] = Field(..., description="Specific action steps")
    priority: str = Field(..., description="Priority: high, medium, low")


class ImprovementPlanResponse(BaseModel):
    """Response model for improvement plan."""

    suggestions: list[ImprovementSuggestionResponse] = Field(
        ..., description="List of improvement suggestions"
    )
    generated_at: str = Field(..., description="ISO timestamp of generation")
    inputs_summary: dict[str, Any] = Field(..., description="Summary of inputs used for analysis")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")


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

        # Parse @mentions from message
        mention_result = parse_mentions(message)
        resolved_mentions = None
        mentioned_ctx = ""

        if mention_result.mentions:
            # Resolve mentions to actual entity data
            resolver = get_mention_resolver()
            resolved_mentions = resolver.resolve(user_id, mention_result.mentions)
            mentioned_ctx = format_mentioned_context(resolved_mentions)

        # Gather context
        context: MentorContext = mentor_context_service.gather_context(user_id)
        context_sources = context.sources_used()

        # Add mention types to context sources if any resolved
        if resolved_mentions and resolved_mentions.has_context():
            if resolved_mentions.meetings:
                context_sources.append("mentioned_meetings")
            if resolved_mentions.actions:
                context_sources.append("mentioned_actions")
            if resolved_mentions.datasets:
                context_sources.append("mentioned_datasets")

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

        # Format failure patterns for proactive mentoring (only if high failure rate)
        failure_ctx = ""
        if context.failure_patterns and context.failure_patterns.should_inject():
            failure_ctx = format_failure_patterns(
                failure_rate=context.failure_patterns.failure_rate,
                patterns=context.failure_patterns.patterns or [],
                by_project=context.failure_patterns.by_project or {},
                by_category=context.failure_patterns.by_category or {},
            )

        # Build prompt (use clean_text if mentions were parsed, else original message)
        # Sanitize user input to prevent prompt injection
        question_text = mention_result.clean_text if mention_result.mentions else message
        safe_question = sanitize_for_prompt(question_text)
        user_prompt = build_mentor_prompt(
            question=safe_question,
            business_context=business_ctx,
            meetings_context=meetings_ctx,
            actions_context=actions_ctx,
            datasets_context=datasets_ctx,
            conversation_history=conv_history,
            mentioned_context=mentioned_ctx,
            failure_context=failure_ctx,
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

        # Done event with conversation ID and mentions info
        done_data: dict[str, Any] = {
            "conversation_id": conversation_id,
            "persona": selected_persona,
            "tokens": usage.total_tokens,
        }
        # Include resolved mentions for UI display
        if resolved_mentions and resolved_mentions.has_context():
            done_data["mentions"] = {
                "meetings": [
                    {"id": m.id, "title": m.problem_statement[:50]}
                    for m in resolved_mentions.meetings
                ],
                "actions": [{"id": a.id, "title": a.title} for a in resolved_mentions.actions],
                "datasets": [{"id": d.id, "title": d.name} for d in resolved_mentions.datasets],
            }
        yield f"event: done\ndata: {json.dumps(done_data)}\n\n"

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
    tier_usage: UsageResult = Depends(require_mentor_limit),
) -> StreamingResponse:
    """Chat with the AI mentor.

    Returns SSE events: thinking, context, response, done, error.
    """
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Record mentor usage for tier tracking
    try:
        record_mentor_usage(user_id)
    except Exception as e:
        # Non-blocking - log and continue
        logger.debug(f"Usage tracking failed (non-blocking): {e}")

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
    "/personas",
    response_model=MentorPersonaListResponse,
    summary="List available mentor personas",
    description="Get all available mentor personas for manual selection",
)
@handle_api_errors("list mentor personas")
async def list_personas(
    user: dict = Depends(get_current_user),
) -> MentorPersonaListResponse:
    """List all available mentor personas.

    Returns personas with id, name, description, expertise areas, and icon.
    Includes an implicit 'auto' option that is handled client-side.
    """
    personas = list_all_personas()
    return MentorPersonaListResponse(
        personas=[
            MentorPersonaResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                expertise=p.expertise,
                icon=p.icon,
            )
            for p in personas
        ],
        total=len(personas),
    )


@router.get(
    "/mentions/search",
    response_model=MentionSearchResponse,
    summary="Search for mentionable entities",
    description="Search meetings, actions, or datasets for @mention autocomplete",
)
@handle_api_errors("search mentions")
async def search_mentions(
    type: str = Query(..., description="Entity type: meeting, action, dataset"),
    q: str = Query("", description="Search query (optional, returns recent if empty)"),
    limit: int = Query(10, ge=1, le=20, description="Max results"),
    user: dict = Depends(get_current_user),
) -> MentionSearchResponse:
    """Search for entities to mention in chat.

    Returns matching meetings, actions, or datasets with preview text.
    Used by frontend autocomplete when user types @.
    """
    from bo1.state.repositories.action_repository import ActionRepository
    from bo1.state.repositories.dataset_repository import DatasetRepository
    from bo1.state.repositories.session_repository import SessionRepository

    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    if type not in ("meeting", "action", "dataset"):
        raise HTTPException(
            status_code=400, detail="Invalid type. Must be: meeting, action, dataset"
        )

    suggestions: list[MentionSuggestion] = []
    query_lower = q.lower().strip()

    if type == "meeting":
        repo = SessionRepository()
        sessions = repo.list_by_user(
            user_id, limit=50, status_filter=None, include_task_count=False
        )
        for s in sessions:
            problem = s.get("problem_statement", "")
            # Filter by query if provided
            if query_lower and query_lower not in problem.lower():
                continue
            suggestions.append(
                MentionSuggestion(
                    id=str(s["id"]),
                    type="meeting",
                    title=problem[:80] + ("..." if len(problem) > 80 else ""),
                    preview=s.get("status", ""),
                )
            )
            if len(suggestions) >= limit:
                break

    elif type == "action":
        repo = ActionRepository()
        actions = repo.get_by_user(user_id, limit=50)
        for a in actions:
            title = a.get("title", "Untitled")
            # Filter by query if provided
            if query_lower and query_lower not in title.lower():
                continue
            suggestions.append(
                MentionSuggestion(
                    id=str(a["id"]),
                    type="action",
                    title=title,
                    preview=a.get("status", ""),
                )
            )
            if len(suggestions) >= limit:
                break

    elif type == "dataset":
        repo = DatasetRepository()
        datasets, _total = repo.list_by_user(user_id, limit=50)
        for d in datasets:
            name = d.get("name", "Unnamed")
            # Filter by query if provided
            if query_lower and query_lower not in name.lower():
                continue
            row_count = d.get("row_count", 0)
            suggestions.append(
                MentionSuggestion(
                    id=str(d["id"]),
                    type="dataset",
                    title=name,
                    preview=f"{row_count} rows" if row_count else None,
                )
            )
            if len(suggestions) >= limit:
                break

    return MentionSearchResponse(suggestions=suggestions, total=len(suggestions))


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


@router.get(
    "/repeated-topics",
    response_model=RepeatedTopicsListResponse,
    summary="Detect repeated help request topics",
    description="Analyze mentor conversations to find repeated topic patterns",
)
@handle_api_errors("detect repeated topics")
async def get_repeated_topics(
    threshold: float = Query(0.85, ge=0.7, le=0.95, description="Similarity threshold (0.7-0.95)"),
    min_occurrences: int = Query(
        3, ge=2, le=10, description="Minimum occurrences to report (2-10)"
    ),
    days: int = Query(30, ge=7, le=90, description="Days to look back (7-90)"),
    user: dict = Depends(get_current_user),
) -> RepeatedTopicsListResponse:
    """Detect repeated help request topics from mentor conversations.

    Uses embedding-based similarity to cluster semantically similar questions
    and surface topics the user has asked about multiple times.

    Results are cached for 1 hour to avoid repeated computation.
    """
    from datetime import UTC, datetime

    from backend.services.topic_detector import get_topic_detector

    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    # Get user's messages from mentor conversations
    mentor_conv_repo = get_mentor_conversation_repo()
    messages = mentor_conv_repo.get_all_user_messages(user_id, days=days)

    # Detect repeated topics
    detector = get_topic_detector()
    topics = detector.detect_repeated_topics(
        user_id=user_id,
        messages=messages,
        threshold=threshold,
        min_occurrences=min_occurrences,
    )

    return RepeatedTopicsListResponse(
        topics=[
            RepeatedTopicResponse(
                topic_summary=t.topic_summary,
                count=t.count,
                first_asked=t.first_asked,
                last_asked=t.last_asked,
                conversation_ids=t.conversation_ids,
                representative_messages=t.representative_messages,
                similarity_score=t.similarity_score,
            )
            for t in topics
        ],
        total=len(topics),
        analysis_timestamp=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/failure-patterns",
    response_model=FailurePatternsResponse,
    summary="Detect action failure patterns",
    description="Analyze actions to find failure patterns for proactive mentoring",
)
@handle_api_errors("detect failure patterns")
async def get_failure_patterns(
    days: int = Query(30, ge=7, le=90, description="Days to look back (7-90)"),
    min_failures: int = Query(3, ge=1, le=20, description="Minimum failures to report (1-20)"),
    user: dict = Depends(get_current_user),
) -> FailurePatternsResponse:
    """Detect action failure patterns for proactive mentoring.

    Analyzes cancelled and blocked actions to identify patterns
    that might indicate areas where the user needs support.

    Returns failure rate, patterns grouped by project and category.
    """
    from datetime import UTC, datetime

    from backend.services.action_failure_detector import get_action_failure_detector

    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    detector = get_action_failure_detector()
    summary = detector.detect_failure_patterns(
        user_id=user_id,
        days=days,
        min_failures=min_failures,
    )

    # Filter patterns if below min_failures threshold
    patterns_to_return = summary.patterns
    if len(patterns_to_return) < min_failures:
        patterns_to_return = []

    return FailurePatternsResponse(
        patterns=[
            ActionFailurePatternResponse(
                action_id=p.action_id,
                title=p.title,
                project_id=p.project_id,
                project_name=p.project_name,
                status=p.status,
                priority=p.priority,
                failure_reason=p.failure_reason,
                failure_category=p.failure_category,
                failed_at=p.failed_at,
                tags=p.tags,
            )
            for p in patterns_to_return
        ],
        failure_rate=summary.failure_rate,
        total_actions=summary.total_actions,
        failed_actions=summary.failed_actions,
        period_days=summary.period_days,
        by_project=summary.by_project,
        by_category=summary.by_category,
        analysis_timestamp=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/improvement-plan",
    response_model=ImprovementPlanResponse,
    summary="Get improvement plan",
    description="Generate a proactive improvement plan based on detected patterns",
)
@handle_api_errors("get improvement plan")
async def get_improvement_plan(
    days: int = Query(30, ge=7, le=90, description="Days to look back (7-90)"),
    force_refresh: bool = Query(False, description="Bypass cache and regenerate"),
    user: dict = Depends(get_current_user),
) -> ImprovementPlanResponse:
    """Generate an improvement plan for the current user.

    Analyzes repeated help topics and action failure patterns to generate
    actionable improvement suggestions. Results are cached for 1 hour.

    Returns 3-5 prioritized suggestions with action steps.
    """
    from backend.services.improvement_plan_generator import (
        get_improvement_plan_generator,
    )

    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    generator = get_improvement_plan_generator()
    plan = await generator.generate_plan(
        user_id=user_id,
        days=days,
        force_refresh=force_refresh,
    )

    return ImprovementPlanResponse(
        suggestions=[
            ImprovementSuggestionResponse(
                category=s.category,
                title=s.title,
                description=s.description,
                action_steps=s.action_steps,
                priority=s.priority,
            )
            for s in plan.suggestions
        ],
        generated_at=plan.generated_at,
        inputs_summary=plan.inputs_summary,
        confidence=plan.confidence,
    )
