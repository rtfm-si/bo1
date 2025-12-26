"""FastAPI router and endpoints for context management.

Provides:
- GET /api/v1/context - Get user's saved business context
- PUT /api/v1/context - Update user's business context
- DELETE /api/v1/context - Delete user's saved context
- GET /api/v1/context/refresh-check - Check if refresh prompt needed
- POST /api/v1/context/dismiss-refresh - Dismiss refresh prompt
- POST /api/v1/context/enrich - Enrich context from website
- POST /api/v1/context/competitors/detect - Auto-detect competitors
- POST /api/v1/context/trends/refresh - Refresh market trends
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.api.context.auto_detect import (
    get_auto_detect_status,
    run_auto_detect_competitors,
    should_trigger_auto_detect,
)
from backend.api.context.competitors import (
    detect_competitors_for_user,
    refresh_market_trends,
)
from backend.api.context.models import (
    ApproveUpdateResponse,
    BusinessContext,
    ClarificationInsight,
    CompetitorDetectRequest,
    CompetitorDetectResponse,
    CompetitorInsightResponse,
    CompetitorInsightsListResponse,
    ContextResponse,
    ContextUpdateSource,
    ContextUpdateSuggestion,
    ContextWithTrends,
    DismissRefreshRequest,
    EnrichmentRequest,
    EnrichmentResponse,
    GoalHistoryEntry,
    GoalHistoryResponse,
    GoalProgressResponse,
    GoalStalenessResponse,
    InsightCategory,
    InsightMetricResponse,
    InsightsResponse,
    ManagedCompetitor,
    ManagedCompetitorCreate,
    ManagedCompetitorListResponse,
    ManagedCompetitorResponse,
    ManagedCompetitorUpdate,
    PendingUpdatesResponse,
    RefreshCheckResponse,
    StaleFieldSummary,
    StaleMetricResponse,
    StaleMetricsResponse,
    TrendInsight,
    TrendInsightRequest,
    TrendInsightResponse,
    TrendInsightsListResponse,
    TrendsRefreshRequest,
    TrendsRefreshResponse,
    UpdateInsightRequest,
)
from backend.api.context.models import (
    StalenessReason as ModelStalenessReason,
)
from backend.api.context.models import (
    VolatilityLevel as ModelVolatilityLevel,
)
from backend.api.context.services import (
    append_benchmark_history,
    context_data_to_model,
    context_model_to_dict,
    enriched_data_to_dict,
    enriched_to_context_model,
    merge_context,
    sanitize_context_values,
    update_benchmark_timestamps,
)
from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors
from bo1.logging.errors import ErrorCode, log_error
from bo1.services.enrichment import EnrichmentService
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])

# Context refresh interval (3 months)
CONTEXT_REFRESH_DAYS = 90


@router.get(
    "/v1/context",
    response_model=ContextResponse,
    summary="Get user's saved business context",
    description="""
    Retrieve the authenticated user's saved business context.

    Business context is persistent across sessions and helps the AI personas
    provide more relevant recommendations. Context includes:
    - Business model and target market
    - Product/service description
    - Revenue and growth metrics
    - Competitor information

    **Use Cases:**
    - Check if user has saved context before starting deliberation
    - Display saved context in user profile
    - Pre-fill forms with existing context
    """,
    responses={
        200: {
            "description": "Context retrieved successfully (exists=true if saved, false if not)",
            "content": {
                "application/json": {
                    "examples": {
                        "with_context": {
                            "summary": "User has saved context",
                            "value": {
                                "exists": True,
                                "context": {
                                    "business_model": "B2B SaaS",
                                    "target_market": "Small businesses in North America",
                                    "product_description": "AI-powered project management tool",
                                    "revenue": 50000.0,
                                    "customers": 150,
                                    "growth_rate": 15.5,
                                    "competitors": ["Asana", "Monday.com", "Jira"],
                                    "website": "https://example.com",
                                },
                                "updated_at": "2025-01-15T12:00:00",
                            },
                        },
                        "no_context": {
                            "summary": "User has no saved context",
                            "value": {
                                "exists": False,
                                "context": None,
                                "updated_at": None,
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Database error"},
    },
)
@handle_api_errors("get context")
async def get_context(user: dict[str, Any] = Depends(get_current_user)) -> ContextResponse:
    """Get user's saved business context."""
    user_id = extract_user_id(user)

    # Load context from database
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return ContextResponse(exists=False, context=None, updated_at=None)

    # Parse into BusinessContext - handle incomplete data gracefully
    try:
        context = context_data_to_model(context_data)
    except Exception:
        # Incomplete or malformed context data - treat as non-existent
        return ContextResponse(exists=False, context=None, updated_at=None)

    # Parse benchmark timestamps from raw data
    benchmark_timestamps = context_data.get("benchmark_timestamps")

    # Get auto-detect status for competitor refresh indicator
    auto_detect_status = get_auto_detect_status(user_id)

    return ContextResponse(
        exists=True,
        context=context,
        updated_at=context_data.get("updated_at"),
        benchmark_timestamps=benchmark_timestamps,
        needs_competitor_refresh=auto_detect_status.get("needs_competitor_refresh", False),
        competitor_count=auto_detect_status.get("competitor_count", 0),
    )


@router.put(
    "/v1/context",
    response_model=dict[str, str],
    summary="Update user's business context",
    description="""
    Create or update the authenticated user's business context.

    Business context is saved to PostgreSQL and persists across sessions.
    This context is used during deliberations to provide more relevant
    recommendations from AI personas.

    **Use Cases:**
    - Save business context during onboarding
    - Update context when business metrics change
    - Pre-populate context for faster deliberation setup

    **Note:** All fields are optional. Only provided fields will be saved.
    """,
    responses={
        200: {
            "description": "Context updated successfully",
            "content": {"application/json": {"example": {"status": "updated"}}},
        },
        500: {"description": "Database error"},
    },
)
@handle_api_errors("update context")
async def update_context(
    context: BusinessContext, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, str]:
    """Update user's business context."""
    user_id = extract_user_id(user)

    # Get existing context to detect changed metrics
    existing_context = user_repository.get_context(user_id)

    # Convert to dict for save function
    context_dict = context_model_to_dict(context)

    # Sanitize user-provided text values to prevent prompt injection
    context_dict = sanitize_context_values(context_dict)

    # Update benchmark timestamps for changed metrics
    new_timestamps = update_benchmark_timestamps(context_dict, existing_context)
    context_dict["benchmark_timestamps"] = new_timestamps

    # Append to benchmark history for trend tracking
    context_dict["benchmark_history"] = append_benchmark_history(context_dict, existing_context)

    # Clean up action metric triggers for updated metrics
    old_timestamps = existing_context.get("benchmark_timestamps", {}) if existing_context else {}
    updated_metrics = [
        field for field in new_timestamps if new_timestamps.get(field) != old_timestamps.get(field)
    ]
    if updated_metrics and existing_context:
        existing_triggers = existing_context.get("action_metric_triggers", [])
        if existing_triggers:
            # Remove triggers for metrics that were just updated
            context_dict["action_metric_triggers"] = [
                t for t in existing_triggers if t.get("metric_field") not in updated_metrics
            ]
            removed_count = len(existing_triggers) - len(
                context_dict.get("action_metric_triggers", [])
            )
            if removed_count > 0:
                logger.debug(f"Removed {removed_count} action triggers for updated metrics")

    # Save to database
    user_repository.save_context(user_id, context_dict)

    # Record goal change if north_star_goal changed
    new_goal = context_dict.get("north_star_goal")
    previous_goal = existing_context.get("north_star_goal") if existing_context else None
    if new_goal and new_goal != previous_goal:
        from backend.services.goal_tracker import record_goal_change

        try:
            record_goal_change(user_id, new_goal, previous_goal)
        except Exception as e:
            logger.warning(f"Failed to record goal change for user {user_id}: {e}")

    logger.info(f"Updated context for user {user_id}")

    # Check if auto-detect should trigger (background task)
    if should_trigger_auto_detect(user_id, context_dict):
        import asyncio

        logger.info(f"Triggering auto-detect competitors for user {user_id}")
        # Schedule as background task (don't block response)
        asyncio.create_task(run_auto_detect_competitors(user_id))

    return {"status": "updated"}


@router.delete(
    "/v1/context",
    response_model=dict[str, str],
    status_code=200,
    summary="Delete user's saved context",
    description="""
    Delete the authenticated user's saved business context.

    This permanently removes all saved business context from the database.
    Future deliberations will not have access to this context unless
    it is re-entered.

    **Use Cases:**
    - User wants to start fresh
    - User wants to remove outdated business information
    - Privacy: Remove all stored business data

    **Warning:** This action cannot be undone.
    """,
    responses={
        200: {
            "description": "Context deleted successfully",
            "content": {"application/json": {"example": {"status": "deleted"}}},
        },
        404: {"description": "No context found to delete"},
        500: {"description": "Database error"},
    },
)
@handle_api_errors("delete context")
async def delete_context(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    """Delete user's saved business context."""
    user_id = extract_user_id(user)

    # Delete from database
    deleted = user_repository.delete_context(user_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="No context found to delete",
        )

    logger.info(f"Deleted context for user {user_id}")

    return {"status": "deleted"}


@router.post(
    "/v1/context/enrich",
    response_model=EnrichmentResponse,
    summary="Enrich context from website",
    description="""
    Analyze a website URL and extract business context information.

    Uses:
    - Website metadata (title, description, OG tags)
    - Brave Search API for company information
    - Claude AI for intelligent extraction

    **Auto-save**: The enriched data is automatically merged with existing
    context and saved. Empty fields are not overwritten.
    """,
    responses={
        200: {
            "description": "Enrichment completed (check success field)",
        },
        422: {"description": "Invalid URL format"},
        500: {"description": "Enrichment service error"},
    },
)
@handle_api_errors("enrich context")
async def enrich_context(
    request: EnrichmentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> EnrichmentResponse:
    """Enrich business context from website URL and auto-save."""
    try:
        user_id = extract_user_id(user)
        logger.info(f"Enriching context from {request.website_url} for user {user_id}")

        # Run enrichment
        service = EnrichmentService()
        try:
            enriched = await service.enrich_from_url(request.website_url)
        finally:
            await service.close()

        # Convert to BusinessContext
        context = enriched_to_context_model(enriched)

        # Auto-save: Merge enriched data with existing context
        existing_context = user_repository.get_context(user_id) or {}
        enriched_dict = enriched_data_to_dict(enriched)

        # Merge (preserve existing user values)
        merged_context = merge_context(existing_context, enriched_dict, preserve_existing=True)

        # Save merged context
        user_repository.save_context(user_id, merged_context)
        logger.info(f"Auto-saved enriched context for user {user_id}")

        return EnrichmentResponse(
            success=True,
            context=context,
            enrichment_source=enriched.enrichment_source,
            confidence=enriched.confidence,
        )

    except ValueError as e:
        logger.warning(f"Invalid URL: {e}")
        return EnrichmentResponse(
            success=False,
            error=f"Invalid URL: {str(e)}",
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Enrichment failed: {e}",
            user_id=user_id,
            url=request.website_url,
        )
        return EnrichmentResponse(
            success=False,
            error=f"Enrichment failed: {str(e)}",
        )


@router.get(
    "/v1/context/refresh-check",
    response_model=RefreshCheckResponse,
    summary="Check if context refresh needed",
    description=f"""
    Check if the user's business context needs refreshing.

    Returns true if:
    - No context exists
    - Context hasn't been updated in {CONTEXT_REFRESH_DAYS} days
    - Last refresh prompt was dismissed and dismiss has expired
    - Stale metrics exist (based on volatility thresholds)

    Also returns stale_metrics array with field names, volatility, and urgency
    for the refresh banner to display specific fields needing attention.
    """,
)
@handle_api_errors("check refresh needed")
async def check_refresh_needed(
    user: dict[str, Any] = Depends(get_current_user),
) -> RefreshCheckResponse:
    """Check if context refresh is needed, including stale metrics."""
    from backend.services.insight_staleness import get_stale_metrics_for_session

    user_id = extract_user_id(user)

    # Get context with extended fields (requires RLS context)
    row = execute_query(
        """
        SELECT updated_at, last_refresh_prompt, onboarding_completed
        FROM user_context
        WHERE user_id = %s
        """,
        (user_id,),
        fetch="one",
        user_id=user_id,
    )

    if not row:
        return RefreshCheckResponse(
            needs_refresh=True,
            last_updated=None,
            days_since_update=None,
        )

    updated_at = row.get("updated_at")
    onboarding_completed = row.get("onboarding_completed", False)

    # Get refresh_dismissed_until from context JSON
    context_data = user_repository.get_context(user_id)
    refresh_dismissed_until_str = (
        context_data.get("refresh_dismissed_until") if context_data else None
    )
    refresh_dismissed_until = None
    if refresh_dismissed_until_str:
        try:
            refresh_dismissed_until = datetime.fromisoformat(
                refresh_dismissed_until_str.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            pass

    # If onboarding not completed, don't show refresh prompts
    if not onboarding_completed:
        return RefreshCheckResponse(
            needs_refresh=False,
            last_updated=updated_at,
            days_since_update=None,
        )

    now = datetime.now(UTC)
    days_since_update = (now - updated_at).days if updated_at else None

    # Check if dismiss is still valid
    dismiss_valid = refresh_dismissed_until and refresh_dismissed_until > now

    # Get stale metrics with volatility
    context_data = user_repository.get_context(user_id)
    action_affected_fields: list[str] = []
    if context_data:
        pending = context_data.get("pending_updates", [])
        for p in pending:
            if p.get("refresh_reason") == "action_affected" and p.get("field_name"):
                action_affected_fields.append(p["field_name"])

    stale_result = get_stale_metrics_for_session(
        user_id=user_id,
        action_affected_fields=action_affected_fields if action_affected_fields else None,
    )

    # Build stale metrics summary for frontend
    stale_summaries: list[StaleFieldSummary] = []
    highest_urgency: str | None = None
    field_display_names = {
        "revenue": "Revenue",
        "customers": "Customer count",
        "growth_rate": "Growth rate",
        "team_size": "Team size",
        "mau_bucket": "Monthly active users",
        "competitors": "Competitors",
        "business_stage": "Business stage",
        "primary_objective": "Primary objective",
    }

    for m in stale_result.stale_metrics:
        is_action_affected = m.reason.value == "action_affected"
        stale_summaries.append(
            StaleFieldSummary(
                field_name=m.field_name,
                display_name=field_display_names.get(
                    m.field_name, m.field_name.replace("_", " ").title()
                ),
                volatility=m.volatility.value,
                days_since_update=m.days_since_update,
                action_affected=is_action_affected,
            )
        )
        # Track highest urgency
        if is_action_affected:
            highest_urgency = "action_affected"
        elif highest_urgency != "action_affected":
            if m.volatility.value == "volatile" and highest_urgency not in ["action_affected"]:
                highest_urgency = "volatile"
            elif m.volatility.value == "moderate" and highest_urgency not in [
                "action_affected",
                "volatile",
            ]:
                highest_urgency = "moderate"
            elif m.volatility.value == "stable" and highest_urgency is None:
                highest_urgency = "stable"

    # Determine if refresh needed: stale metrics exist AND dismiss has expired
    needs_refresh = stale_result.has_stale_metrics and not dismiss_valid

    return RefreshCheckResponse(
        needs_refresh=needs_refresh,
        last_updated=updated_at,
        days_since_update=days_since_update,
        stale_metrics=stale_summaries,
        highest_urgency=highest_urgency,
    )


@router.post(
    "/v1/context/dismiss-refresh",
    response_model=dict[str, str],
    summary="Dismiss refresh prompt",
    description="""
    Dismiss the "Are these details still correct?" refresh prompt.

    Dismiss expiry varies by volatility of the most urgent stale metric:
    - volatile: 7 days (revenue, customers change frequently)
    - moderate: 30 days (team size, competitors change occasionally)
    - stable: 90 days (business stage, industry rarely change)

    If no volatility provided, defaults to 30 days.
    """,
)
@handle_api_errors("dismiss refresh prompt")
async def dismiss_refresh_prompt(
    request: DismissRefreshRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Dismiss the refresh prompt with volatility-aware expiry."""
    from datetime import timedelta

    user_id = extract_user_id(user)

    # Determine expiry based on volatility
    volatility = request.volatility if request else "moderate"
    expiry_days = {
        "volatile": 7,
        "action_affected": 7,  # Same as volatile
        "moderate": 30,
        "stable": 90,
    }.get(volatility, 30)

    dismissed_until = datetime.now(UTC) + timedelta(days=expiry_days)

    # Update timestamp in DB (requires RLS context)
    result = execute_query(
        """
        UPDATE user_context
        SET last_refresh_prompt = NOW(), updated_at = updated_at
        WHERE user_id = %s
        RETURNING user_id
        """,
        (user_id,),
        fetch="one",
        user_id=user_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="No context found")

    # Store expiry in context JSON
    context_data = user_repository.get_context(user_id) or {}
    context_data["refresh_dismissed_until"] = dismissed_until.isoformat()
    user_repository.save_context(user_id, context_data)

    logger.info(
        f"User {user_id} dismissed refresh prompt for {expiry_days} days (volatility={volatility})"
    )

    return {"status": "dismissed", "dismissed_until": dismissed_until.isoformat()}


# =============================================================================
# Phase 3: Strategic Context Endpoints
# =============================================================================


@router.post(
    "/v1/context/competitors/detect",
    response_model=CompetitorDetectResponse,
    summary="Auto-detect competitors",
    description="""
    Automatically detect competitors using Tavily Search API.

    First checks if competitors were already detected during website enrichment.
    If not, uses Tavily to search G2, Capterra, and other review sites for
    high-quality competitor information.

    **Auto-save**: Detected competitors are automatically saved to Competitor Watch
    (up to the user's tier limit). Existing competitors are not duplicated.

    Returns a list of detected competitors with names, URLs, and descriptions.
    """,
)
@handle_api_errors("detect competitors")
async def detect_competitors(
    request: CompetitorDetectRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorDetectResponse:
    """Detect competitors using Tavily Search API and auto-save to Competitor Watch."""
    user_id = extract_user_id(user)
    industry = request.industry if request else None
    product_description = request.product_description if request else None

    return await detect_competitors_for_user(user_id, industry, product_description)


@router.post(
    "/v1/context/trends/refresh",
    response_model=TrendsRefreshResponse,
    summary="Refresh market trends",
    description="""
    Fetch current market trends for the user's industry using Brave Search API.

    Uses the industry from saved context or the request to search for
    recent trends and news.

    Returns a list of trends with sources.
    """,
)
@handle_api_errors("refresh trends")
async def refresh_trends(
    request: TrendsRefreshRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> TrendsRefreshResponse:
    """Refresh market trends using Brave Search."""
    user_id = extract_user_id(user)
    industry = request.industry if request else None

    return await refresh_market_trends(user_id, industry)


# =============================================================================
# Phase 4: Insights Endpoints (Clarifications from Meetings)
# =============================================================================


@router.get(
    "/v1/context/insights",
    response_model=InsightsResponse,
    summary="Get accumulated insights from meetings",
    description="""
    Retrieve insights accumulated from user's meetings.

    Currently includes:
    - **Clarifications**: Q&A pairs from clarifying questions answered during meetings

    These insights are automatically collected during meetings when users answer
    clarifying questions. They help improve future meetings by providing
    relevant context.

    **Use Cases:**
    - Display clarification history in settings
    - Show what the system has learned about the user's business
    - Allow users to review and potentially edit their responses
    """,
    responses={
        200: {
            "description": "Insights retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "clarifications": [
                            {
                                "question": "What is your primary revenue model?",
                                "answer": "Subscription-based SaaS with annual contracts",
                                "answered_at": "2025-01-15T12:00:00Z",
                                "session_id": "bo1_abc123",
                            }
                        ],
                        "total_count": 1,
                    }
                }
            },
        },
    },
)
@handle_api_errors("get insights")
async def get_insights(
    user: dict[str, Any] = Depends(get_current_user),
) -> InsightsResponse:
    """Get accumulated insights from user's meetings."""
    user_id = extract_user_id(user)

    # Load context from database
    context_data = user_repository.get_context(user_id)

    if not context_data:
        return InsightsResponse(clarifications=[], total_count=0)

    # Extract clarifications from context
    raw_clarifications = context_data.get("clarifications", {})
    clarifications: list[ClarificationInsight] = []

    for question, data in raw_clarifications.items():
        if isinstance(data, dict):
            # Build metric response if present
            metric_response = None
            if data.get("metric"):
                m = data["metric"]
                metric_response = InsightMetricResponse(
                    value=m.get("value"),
                    unit=m.get("unit"),
                    metric_type=m.get("metric_type"),
                    period=m.get("period"),
                    raw_text=m.get("raw_text"),
                )

            # Parse category
            category = None
            if data.get("category"):
                try:
                    category = InsightCategory(data["category"])
                except ValueError:
                    category = InsightCategory.UNCATEGORIZED

            # New format with metadata (including structured fields)
            clarifications.append(
                ClarificationInsight(
                    question=question,
                    answer=data.get("answer", ""),
                    answered_at=data.get("answered_at"),
                    session_id=data.get("session_id"),
                    category=category,
                    metric=metric_response,
                    confidence_score=data.get("confidence_score"),
                    summary=data.get("summary"),
                    key_entities=data.get("key_entities"),
                    parsed_at=data.get("parsed_at"),
                )
            )
        else:
            # Legacy format (string value only)
            clarifications.append(
                ClarificationInsight(
                    question=question,
                    answer=str(data),
                    answered_at=None,
                    session_id=None,
                )
            )

    # Sort by answered_at (newest first), with None values at the end
    clarifications.sort(
        key=lambda c: c.answered_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    logger.info(f"Retrieved {len(clarifications)} clarification insights for user {user_id}")

    return InsightsResponse(
        clarifications=clarifications,
        total_count=len(clarifications),
    )


@router.patch(
    "/v1/context/insights/{question_hash}",
    response_model=ClarificationInsight,
    summary="Update a clarification insight",
    description="""
    Update a user's answer to a clarifying question.

    The question_hash is a URL-safe base64 encoding of the question text.
    When updated, the answer and updated timestamp are persisted, allowing
    users to keep their responses current as their business evolves.
    """,
)
@handle_api_errors("update insight")
async def update_insight(
    question_hash: str,
    request: UpdateInsightRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> ClarificationInsight:
    """Update a specific clarification insight."""
    import base64

    user_id = extract_user_id(user)

    # Decode the question from the hash
    try:
        question = base64.urlsafe_b64decode(question_hash.encode()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode question hash: {e}")
        raise HTTPException(status_code=400, detail="Invalid question hash") from None

    # Load and update context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    clarifications = context_data.get("clarifications", {})
    if question not in clarifications:
        raise HTTPException(status_code=404, detail="Clarification not found")

    # Validate the new value before storing
    from backend.services.insight_parser import is_valid_insight_response

    if not is_valid_insight_response(request.value):
        raise HTTPException(
            status_code=400,
            detail="Invalid insight response: please provide a meaningful answer",
        )

    # Get existing clarification data
    existing = clarifications[question]
    if isinstance(existing, str):
        # Legacy format, convert to new format
        existing = {"answer": existing, "answered_at": None, "source": "meeting"}

    # Update the answer and timestamp
    existing["answer"] = request.value
    existing["updated_at"] = datetime.now(UTC).isoformat()
    if request.note:
        existing["update_note"] = request.note

    # Re-parse with Haiku for structured fields
    try:
        from backend.services.insight_parser import parse_insight

        structured = await parse_insight(request.value)
        existing["category"] = structured.category.value
        existing["confidence_score"] = structured.confidence_score
        if structured.metric:
            existing["metric"] = {
                "value": structured.metric.value,
                "unit": structured.metric.unit,
                "metric_type": structured.metric.metric_type,
                "period": structured.metric.period,
                "raw_text": structured.metric.raw_text,
            }
        else:
            existing.pop("metric", None)
        if structured.summary:
            existing["summary"] = structured.summary
        else:
            existing.pop("summary", None)
        if structured.key_entities:
            existing["key_entities"] = structured.key_entities
        else:
            existing.pop("key_entities", None)
        existing["parsed_at"] = structured.parsed_at
    except Exception as parse_err:
        logger.debug(f"Insight parsing failed during update (non-blocking): {parse_err}")
        existing["category"] = "uncategorized"
        existing["confidence_score"] = 0.0

    # Validate entry before storage
    from backend.api.context.services import normalize_clarification_for_storage

    clarifications[question] = normalize_clarification_for_storage(existing)
    context_data["clarifications"] = clarifications

    # Save updated context
    user_repository.save_context(user_id, context_data)
    logger.info(f"Updated clarification insight for user {user_id}: {question[:50]}...")

    # Build metric response if present
    metric_response = None
    if existing.get("metric"):
        m = existing["metric"]
        metric_response = InsightMetricResponse(
            value=m.get("value"),
            unit=m.get("unit"),
            metric_type=m.get("metric_type"),
            period=m.get("period"),
            raw_text=m.get("raw_text"),
        )

    # Return updated insight with structured fields
    return ClarificationInsight(
        question=question,
        answer=existing["answer"],
        answered_at=existing.get("answered_at"),
        session_id=existing.get("session_id"),
        category=InsightCategory(existing.get("category", "uncategorized")),
        metric=metric_response,
        confidence_score=existing.get("confidence_score"),
        summary=existing.get("summary"),
        key_entities=existing.get("key_entities"),
        parsed_at=existing.get("parsed_at"),
    )


@router.delete(
    "/v1/context/insights/{question_hash}",
    response_model=dict[str, str],
    summary="Delete a specific clarification insight",
    description="""
    Delete a specific clarification from the user's insights.

    The question_hash is a URL-safe base64 encoding of the question text.
    This allows deleting clarifications that may contain special characters.
    """,
)
@handle_api_errors("delete insight")
async def delete_insight(
    question_hash: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a specific clarification insight."""
    import base64

    user_id = extract_user_id(user)

    # Decode the question from the hash
    try:
        question = base64.urlsafe_b64decode(question_hash.encode()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode question hash: {e}")
        raise HTTPException(status_code=400, detail="Invalid question hash") from None

    # Load and update context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    clarifications = context_data.get("clarifications", {})
    if question not in clarifications:
        raise HTTPException(status_code=404, detail="Clarification not found")

    # Remove the clarification
    del clarifications[question]
    context_data["clarifications"] = clarifications

    # Save updated context
    user_repository.save_context(user_id, context_data)
    logger.info(f"Deleted clarification insight for user {user_id}: {question[:50]}...")

    return {"status": "deleted"}


# =============================================================================
# Phase 5: Onboarding Demo Questions
# =============================================================================


@router.get(
    "/v1/context/demo-questions",
    summary="Get personalized demo questions",
    description="""
    Get personalized business questions for new users based on their context.

    Uses the user's saved business context to generate relevant, actionable
    questions they can explore in their first meeting.

    **Features:**
    - Questions are cached for 7 days
    - Falls back to generic questions if no context or LLM fails
    - Uses "fast" tier (Haiku) to minimize cost

    **Use Cases:**
    - Onboarding flow: show suggested questions to new users
    - Help users get started with relevant decisions
    - Demonstrate platform value during first session
    """,
    responses={
        200: {
            "description": "Demo questions generated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "questions": [
                            {
                                "question": "Should we expand to the European market this year?",
                                "category": "growth",
                                "relevance": "Given your growth rate and product maturity, international expansion could be timely.",
                            }
                        ],
                        "generated": True,
                        "cached": False,
                    }
                }
            },
        },
    },
)
@handle_api_errors("get demo questions")
async def get_demo_questions(
    refresh: bool = False,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get personalized demo questions based on user's context."""
    from backend.services.demo_questions import generate_demo_questions

    user_id = extract_user_id(user)

    # Get user's business context
    context_data = user_repository.get_context(user_id)

    # Generate questions
    result = await generate_demo_questions(
        user_id=user_id,
        context=context_data,
        force_refresh=refresh,
    )

    return {
        "questions": [q.model_dump() for q in result.questions],
        "generated": result.generated,
        "cached": result.cached,
    }


@router.delete(
    "/v1/context/demo-questions",
    summary="Clear cached demo questions",
    description="""
    Clear the cached demo questions for the current user.

    Use this when:
    - User updates their business context significantly
    - User wants fresh suggestions

    Next call to GET /demo-questions will regenerate.
    """,
)
@handle_api_errors("clear demo questions cache")
async def clear_demo_questions(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Clear cached demo questions."""
    from backend.services.demo_questions import clear_cached_questions

    user_id = extract_user_id(user)
    clear_cached_questions(user_id)

    return {"status": "cleared"}


# =============================================================================
# Phase 6: Pending Updates Endpoints (Context Auto-Update)
# =============================================================================


@router.get(
    "/v1/context/pending-updates",
    response_model=PendingUpdatesResponse,
    summary="List pending context update suggestions",
    description="""
    Get pending context update suggestions that require user approval.

    These are updates extracted with < 80% confidence from:
    - Clarification answers during meetings
    - Problem statements when creating meetings
    - Action completion/cancellation notes

    **Use Cases:**
    - Display "Suggested Updates" section in Settings > Context
    - Allow users to review and approve/dismiss detected changes
    """,
)
@handle_api_errors("get pending updates")
async def get_pending_updates(
    user: dict[str, Any] = Depends(get_current_user),
) -> PendingUpdatesResponse:
    """Get pending context update suggestions."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        return PendingUpdatesResponse(suggestions=[], count=0)

    pending = context_data.get("pending_updates", [])
    suggestions = []

    for item in pending:
        try:
            suggestions.append(
                ContextUpdateSuggestion(
                    id=item.get("id", ""),
                    field_name=item.get("field_name", ""),
                    new_value=item.get("new_value", ""),
                    current_value=item.get("current_value"),
                    confidence=item.get("confidence", 0.5),
                    source_type=ContextUpdateSource(item.get("source_type", "clarification")),
                    source_text=item.get("source_text", ""),
                    extracted_at=datetime.fromisoformat(
                        item.get("extracted_at", "2025-01-01T00:00:00")
                    ),
                    session_id=item.get("session_id"),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse pending update: {e}")
            continue

    return PendingUpdatesResponse(suggestions=suggestions, count=len(suggestions))


@router.post(
    "/v1/context/pending-updates/{suggestion_id}/approve",
    response_model=ApproveUpdateResponse,
    summary="Approve a pending context update",
    description="""
    Apply a pending context update suggestion.

    This will:
    1. Update the specified context field with the suggested value
    2. Record the change in metric history for trend tracking
    3. Remove the suggestion from pending updates
    """,
)
@handle_api_errors("approve pending update")
async def approve_pending_update(
    suggestion_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> ApproveUpdateResponse:
    """Approve and apply a pending context update."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    pending = context_data.get("pending_updates", [])

    # Find the suggestion
    suggestion = None
    suggestion_idx = None
    for idx, item in enumerate(pending):
        if item.get("id") == suggestion_id:
            suggestion = item
            suggestion_idx = idx
            break

    if suggestion is None:
        raise HTTPException(status_code=404, detail="Pending update not found")

    # Apply the update
    field_name = suggestion.get("field_name", "")
    new_value = suggestion.get("new_value", "")

    context_data[field_name] = new_value

    # Track in metric history
    metric_history = context_data.get("context_metric_history", {})
    if field_name not in metric_history:
        metric_history[field_name] = []
    metric_history[field_name].insert(
        0,
        {
            "value": new_value,
            "recorded_at": datetime.now(UTC).isoformat(),
            "source_type": suggestion.get("source_type", "clarification"),
            "source_id": suggestion.get("session_id"),
        },
    )
    metric_history[field_name] = metric_history[field_name][:10]
    context_data["context_metric_history"] = metric_history

    # Remove from pending
    pending.pop(suggestion_idx)
    context_data["pending_updates"] = pending

    # Save
    user_repository.save_context(user_id, context_data)
    logger.info(f"User {user_id} approved pending update: {field_name}={new_value}")

    return ApproveUpdateResponse(
        success=True,
        field_name=field_name,
        new_value=new_value,
    )


@router.delete(
    "/v1/context/pending-updates/{suggestion_id}",
    response_model=dict[str, str],
    summary="Dismiss a pending context update",
    description="""
    Dismiss a pending context update suggestion without applying it.

    The suggestion is removed from the pending list and will not be shown again.
    """,
)
@handle_api_errors("dismiss pending update")
async def dismiss_pending_update(
    suggestion_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Dismiss a pending context update without applying it."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    pending = context_data.get("pending_updates", [])

    # Find and remove the suggestion
    new_pending = [item for item in pending if item.get("id") != suggestion_id]

    if len(new_pending) == len(pending):
        raise HTTPException(status_code=404, detail="Pending update not found")

    context_data["pending_updates"] = new_pending
    user_repository.save_context(user_id, context_data)
    logger.info(f"User {user_id} dismissed pending update: {suggestion_id}")

    return {"status": "dismissed"}


@router.get(
    "/v1/context/with-trends",
    response_model=ContextWithTrends,
    summary="Get business context with trend indicators",
    description="""
    Get the user's business context along with trend indicators for metrics
    that have historical values.

    **Use Cases:**
    - Display metrics with up/down indicators in the context overview
    - Show change percentages for revenue, customers, growth, etc.
    """,
)
@handle_api_errors("get context with trends")
async def get_context_with_trends(
    user: dict[str, Any] = Depends(get_current_user),
) -> ContextWithTrends:
    """Get business context with trend calculations."""
    from backend.services.trend_calculator import calculate_all_trends

    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        return ContextWithTrends(
            context=BusinessContext(),
            trends=[],
            updated_at=None,
        )

    # Convert to BusinessContext model
    context_model = context_data_to_model(context_data)

    # Calculate trends from metric history
    metric_history = context_data.get("context_metric_history", {})
    trends = calculate_all_trends(metric_history)

    return ContextWithTrends(
        context=context_model,
        trends=trends,
        updated_at=context_data.get("updated_at"),
    )


@router.get(
    "/v1/context/stale-metrics",
    response_model=StaleMetricsResponse,
    summary="Get stale business context metrics",
    description="""
    Check which business context metrics are stale and need refreshing.

    Staleness is determined by:
    - **Age-based**: Metric hasn't been updated within its volatility threshold
      - VOLATILE metrics (revenue, customers): stale after 30 days
      - MODERATE metrics (team_size, competitors): stale after 90 days
      - STABLE metrics (industry, business_stage): stale after 180 days
    - **Action-affected**: Related action was recently completed

    Returns max 3 stale metrics, prioritized by:
    1. Action-affected metrics (most urgent)
    2. Days since last update (longer = higher priority)

    **Use Cases:**
    - Check before starting a meeting to prompt user to update context
    - Show stale metric warnings in context settings page
    """,
)
@handle_api_errors("get stale metrics")
async def get_stale_metrics(
    user: dict[str, Any] = Depends(get_current_user),
) -> StaleMetricsResponse:
    """Get list of stale metrics that need refreshing."""
    from backend.services.insight_staleness import get_stale_metrics_for_session

    user_id = extract_user_id(user)

    # Get action-affected fields from pending updates
    context_data = user_repository.get_context(user_id)
    action_affected_fields: list[str] = []

    if context_data:
        pending = context_data.get("pending_updates", [])
        for p in pending:
            if p.get("refresh_reason") == "action_affected" and p.get("field_name"):
                action_affected_fields.append(p["field_name"])

    result = get_stale_metrics_for_session(
        user_id=user_id,
        action_affected_fields=action_affected_fields if action_affected_fields else None,
    )

    # Convert to response model
    stale_metrics_response = [
        StaleMetricResponse(
            field_name=m.field_name,
            current_value=m.current_value,
            updated_at=m.updated_at,
            days_since_update=m.days_since_update,
            reason=ModelStalenessReason(m.reason.value),
            volatility=ModelVolatilityLevel(m.volatility.value),
            threshold_days=m.threshold_days,
            action_id=m.action_id,
        )
        for m in result.stale_metrics
    ]

    return StaleMetricsResponse(
        has_stale_metrics=result.has_stale_metrics,
        stale_metrics=stale_metrics_response,
        total_metrics_checked=result.total_metrics_checked,
    )


# =============================================================================
# Competitor Insights Endpoints
# =============================================================================

# Tier limits for visible competitor insights
COMPETITOR_INSIGHT_TIER_LIMITS = {
    "free": 1,
    "starter": 3,
    "pro": 100,  # effectively unlimited
    "enterprise": 100,
}


def _get_insight_limit_for_tier(tier: str) -> int:
    """Get the insight visibility limit for a tier."""
    return COMPETITOR_INSIGHT_TIER_LIMITS.get(tier, 1)


@router.post(
    "/v1/context/competitors/{name}/insights",
    response_model=CompetitorInsightResponse,
    summary="Generate insight for a competitor",
    description="""
    Generate an AI-powered insight card for a specific competitor.

    Uses Haiku for fast, cost-effective analysis (~$0.003/request).
    Includes web search for fresh company data when available.

    **Rate Limit:** 3 requests per minute per user (LLM cost control).

    **Caching:** Results are cached in user context. Subsequent calls
    for the same competitor return cached data unless forced refresh.
    """,
    responses={
        200: {"description": "Insight generated or retrieved from cache"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Analysis failed"},
    },
)
@handle_api_errors("generate competitor insight")
async def generate_competitor_insight(
    name: str,
    refresh: bool = False,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorInsightResponse:
    """Generate AI-powered insight for a competitor."""
    from backend.services.competitor_analyzer import get_competitor_analyzer

    user_id = extract_user_id(user)

    # Sanitize competitor name
    name = name.strip()[:100]
    if not name:
        raise HTTPException(status_code=400, detail="Competitor name required")

    # Load user context
    context_data = user_repository.get_context(user_id) or {}

    # Check cache first (unless refresh requested)
    cached_insights = context_data.get("competitor_insights", {})
    if name in cached_insights and not refresh:
        insight_data = cached_insights[name]
        from backend.api.context.models import CompetitorInsight

        return CompetitorInsightResponse(
            success=True,
            insight=CompetitorInsight(**insight_data),
            generation_status="cached",
        )

    # Generate new insight
    analyzer = get_competitor_analyzer()
    result = await analyzer.generate_insight(
        competitor_name=name,
        industry=context_data.get("industry"),
        product_description=context_data.get("product_description"),
        value_proposition=context_data.get("main_value_proposition"),
    )

    if result.status == "error":
        return CompetitorInsightResponse(
            success=False,
            insight=None,
            error=result.error,
            generation_status="error",
        )

    # Cache the result
    insight_dict = result.to_dict()
    cached_insights[name] = insight_dict
    context_data["competitor_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Generated competitor insight for {name} (user={user_id})")

    from backend.api.context.models import CompetitorInsight

    return CompetitorInsightResponse(
        success=True,
        insight=CompetitorInsight(**insight_dict),
        generation_status=result.status,
    )


@router.get(
    "/v1/context/competitors/insights",
    response_model=CompetitorInsightsListResponse,
    summary="List cached competitor insights",
    description="""
    Retrieve all cached competitor insights for the user.

    **Tier Gating:**
    - Free: 1 visible insight
    - Starter: 3 visible insights
    - Pro: Unlimited insights

    Returns `visible_count` and `total_count` to show users what they're missing.
    Includes `upgrade_prompt` when tier limit is reached.
    """,
)
@handle_api_errors("list competitor insights")
async def list_competitor_insights(
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorInsightsListResponse:
    """List all cached competitor insights with tier gating."""
    from backend.api.context.models import CompetitorInsight

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Load cached insights
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return CompetitorInsightsListResponse(
            success=True,
            insights=[],
            visible_count=0,
            total_count=0,
            tier=tier,
        )

    cached_insights = context_data.get("competitor_insights", {})
    total_count = len(cached_insights)

    # Apply tier limit
    limit = _get_insight_limit_for_tier(tier)
    visible_count = min(total_count, limit)

    # Convert to list and apply limit
    insights = []
    for i, (name, data) in enumerate(cached_insights.items()):
        if i >= limit:
            break
        try:
            insights.append(CompetitorInsight(**data))
        except Exception as e:
            logger.warning(f"Failed to parse cached insight for {name}: {e}")
            continue

    # Build upgrade prompt if limit reached
    upgrade_prompt = None
    if total_count > visible_count:
        hidden_count = total_count - visible_count
        upgrade_prompt = (
            f"Upgrade to see {hidden_count} more competitor insight"
            f"{'s' if hidden_count > 1 else ''}."
        )

    return CompetitorInsightsListResponse(
        success=True,
        insights=insights,
        visible_count=visible_count,
        total_count=total_count,
        tier=tier,
        upgrade_prompt=upgrade_prompt,
    )


@router.delete(
    "/v1/context/competitors/{name}/insights",
    response_model=dict[str, str],
    summary="Delete cached competitor insight",
    description="""
    Remove a cached competitor insight.

    This frees up a slot for users on limited tiers.
    The insight can be regenerated by calling the POST endpoint.
    """,
)
@handle_api_errors("delete competitor insight")
async def delete_competitor_insight(
    name: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a cached competitor insight."""
    user_id = extract_user_id(user)

    # Load context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    cached_insights = context_data.get("competitor_insights", {})
    if name not in cached_insights:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Remove insight
    del cached_insights[name]
    context_data["competitor_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Deleted competitor insight for {name} (user={user_id})")

    return {"status": "deleted"}


# =============================================================================
# Managed Competitors Endpoints (User-submitted competitor list)
# =============================================================================


@router.get(
    "/v1/context/managed-competitors",
    response_model=ManagedCompetitorListResponse,
    summary="List user's managed competitors",
    description="""
    Retrieve the user's manually managed competitor list.

    These are competitors the user has explicitly added, distinct from:
    - Auto-detected competitors (from enrichment)
    - Competitor insights (AI-generated analysis cards)

    Returns competitors sorted by added_at (newest first).
    """,
)
@handle_api_errors("list managed competitors")
async def list_managed_competitors(
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorListResponse:
    """List user's managed competitors."""
    import time

    user_id = extract_user_id(user)

    start_time = time.monotonic()
    logger.debug(f"[MANAGED_COMPETITORS] Fetching for user {user_id[:8]}...")
    competitors_data = user_repository.get_managed_competitors(user_id)
    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.debug(
        f"[MANAGED_COMPETITORS] Fetched {len(competitors_data)} competitors in {elapsed_ms:.1f}ms"
    )

    # Convert to models and sort by added_at (newest first)
    competitors = []
    for c in competitors_data:
        try:
            added_at = c.get("added_at")
            if isinstance(added_at, str):
                added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
            competitors.append(
                ManagedCompetitor(
                    name=c.get("name", ""),
                    url=c.get("url"),
                    notes=c.get("notes"),
                    added_at=added_at or datetime.now(UTC),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse managed competitor: {e}")
            continue

    # Sort by added_at (newest first)
    competitors.sort(key=lambda c: c.added_at, reverse=True)

    return ManagedCompetitorListResponse(
        success=True,
        competitors=competitors,
        count=len(competitors),
    )


@router.post(
    "/v1/context/managed-competitors",
    response_model=ManagedCompetitorResponse,
    summary="Add a managed competitor",
    description="""
    Add a new competitor to the user's managed list.

    Performs case-insensitive deduplication - if a competitor with
    the same name (ignoring case) already exists, returns error.

    **Use Cases:**
    - User manually adds known competitor
    - Capture competitor from external source
    """,
    responses={
        200: {"description": "Competitor added successfully"},
        409: {"description": "Competitor with this name already exists"},
    },
)
@handle_api_errors("add managed competitor")
async def add_managed_competitor(
    request: ManagedCompetitorCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorResponse:
    """Add a new managed competitor."""
    user_id = extract_user_id(user)

    result = user_repository.add_managed_competitor(
        user_id=user_id,
        name=request.name,
        url=request.url,
        notes=request.notes,
    )

    if result is None:
        raise HTTPException(
            status_code=409,
            detail=f"Competitor '{request.name}' already exists",
        )

    # Convert added_at to datetime
    added_at = result.get("added_at")
    if isinstance(added_at, str):
        added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

    return ManagedCompetitorResponse(
        success=True,
        competitor=ManagedCompetitor(
            name=result.get("name", ""),
            url=result.get("url"),
            notes=result.get("notes"),
            added_at=added_at or datetime.now(UTC),
        ),
    )


@router.patch(
    "/v1/context/managed-competitors/{name}",
    response_model=ManagedCompetitorResponse,
    summary="Update a managed competitor",
    description="""
    Update the URL and/or notes for a managed competitor.

    Competitor is matched by name (case-insensitive).
    Only provided fields are updated - omitted fields remain unchanged.
    """,
    responses={
        200: {"description": "Competitor updated successfully"},
        404: {"description": "Competitor not found"},
    },
)
@handle_api_errors("update managed competitor")
async def update_managed_competitor(
    name: str,
    request: ManagedCompetitorUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorResponse:
    """Update a managed competitor's url and/or notes."""
    user_id = extract_user_id(user)

    result = user_repository.update_managed_competitor(
        user_id=user_id,
        name=name,
        url=request.url,
        notes=request.notes,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Competitor '{name}' not found",
        )

    # Convert added_at to datetime
    added_at = result.get("added_at")
    if isinstance(added_at, str):
        added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

    return ManagedCompetitorResponse(
        success=True,
        competitor=ManagedCompetitor(
            name=result.get("name", ""),
            url=result.get("url"),
            notes=result.get("notes"),
            added_at=added_at or datetime.now(UTC),
        ),
    )


@router.delete(
    "/v1/context/managed-competitors/{name}",
    response_model=dict[str, str],
    summary="Remove a managed competitor",
    description="""
    Remove a competitor from the user's managed list.

    Competitor is matched by name (case-insensitive).
    This does not delete any associated competitor insights.
    """,
    responses={
        200: {"description": "Competitor removed successfully"},
        404: {"description": "Competitor not found"},
    },
)
@handle_api_errors("remove managed competitor")
async def remove_managed_competitor(
    name: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Remove a managed competitor."""
    user_id = extract_user_id(user)

    success = user_repository.remove_managed_competitor(user_id, name)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Competitor '{name}' not found",
        )

    return {"status": "deleted"}


# =============================================================================
# Phase 9: Goal Progress Endpoint
# =============================================================================


@router.get(
    "/v1/context/goal-progress",
    response_model=GoalProgressResponse,
    summary="Get goal progress metrics",
    description="""
    Get action completion stats for the last 30 days.

    Returns:
    - Progress percentage (completed / total active actions)
    - Trend compared to previous 30-day period (up/down/stable)
    - Completed and total counts

    Useful for displaying goal progress on the dashboard.
    """,
)
@handle_api_errors("get goal progress")
async def get_goal_progress(
    user: dict[str, Any] = Depends(get_current_user),
) -> GoalProgressResponse:
    """Get goal progress based on action completion."""
    from datetime import timedelta

    from bo1.state import db_session

    user_id = extract_user_id(user)

    # Calculate date ranges
    now = datetime.now(UTC)
    period_30d_start = now - timedelta(days=30)
    period_60d_start = now - timedelta(days=60)

    # Query action stats for current 30-day period
    with db_session(user_id=user_id) as conn:
        # Current period (last 30 days)
        result = execute_query(
            conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'done') as completed,
                COUNT(*) FILTER (WHERE status IN ('todo', 'in_progress', 'done')) as total
            FROM actions
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND (
                  completed_at >= %s
                  OR (status IN ('todo', 'in_progress') AND created_at <= %s)
              )
            """,
            (user_id, period_30d_start, now),
            user_id=user_id,
        )
        current = result.fetchone() if result else None
        current_completed = current[0] if current else 0
        current_total = current[1] if current else 0

        # Previous period (30-60 days ago)
        result = execute_query(
            conn,
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'done') as completed,
                COUNT(*) FILTER (WHERE status IN ('todo', 'in_progress', 'done')) as total
            FROM actions
            WHERE user_id = %s
              AND deleted_at IS NULL
              AND (
                  completed_at >= %s AND completed_at < %s
                  OR (status IN ('todo', 'in_progress') AND created_at <= %s AND created_at >= %s)
              )
            """,
            (user_id, period_60d_start, period_30d_start, period_30d_start, period_60d_start),
            user_id=user_id,
        )
        previous = result.fetchone() if result else None
        prev_completed = previous[0] if previous else 0
        prev_total = previous[1] if previous else 0

    # Calculate progress percentage
    progress_percent = 0
    if current_total > 0:
        progress_percent = min(100, int((current_completed / current_total) * 100))

    # Calculate trend
    current_rate = current_completed / current_total if current_total > 0 else 0
    prev_rate = prev_completed / prev_total if prev_total > 0 else 0

    if current_rate > prev_rate + 0.05:
        trend = "up"
    elif current_rate < prev_rate - 0.05:
        trend = "down"
    else:
        trend = "stable"

    logger.info(
        f"Goal progress for user {user_id}: {progress_percent}% ({current_completed}/{current_total}), trend={trend}"
    )

    return GoalProgressResponse(
        progress_percent=progress_percent,
        trend=trend,
        completed_count=current_completed,
        total_count=current_total,
    )


# =============================================================================
# Trend Insights Endpoints
# =============================================================================


@router.post(
    "/v1/context/trends/analyze",
    response_model=TrendInsightResponse,
    summary="Analyze a trend URL for insights",
    description="""
    Analyze a market trend URL and generate structured insights.

    Uses Haiku for fast, cost-effective analysis (~$0.003/request).
    Fetches URL content and extracts key takeaways, relevance to user's
    business, and recommended actions.

    **Rate Limit:** 3 requests per minute per user (web fetching cost control).

    **Caching:** Results are cached in user context. Subsequent calls
    for the same URL return cached data unless forced refresh.

    **Supported content:** HTML pages. PDFs and other formats are not supported.
    """,
    responses={
        200: {"description": "Insight generated or retrieved from cache"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Analysis failed"},
    },
)
@handle_api_errors("analyze trend")
async def analyze_trend(
    request: TrendInsightRequest,
    refresh: bool = False,
    user: dict[str, Any] = Depends(get_current_user),
) -> TrendInsightResponse:
    """Analyze a trend URL and generate structured insights."""
    from backend.services.trend_analyzer import get_trend_analyzer

    user_id = extract_user_id(user)

    # Validate URL
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL required")

    # Load user context
    context_data = user_repository.get_context(user_id) or {}

    # Check cache first (unless refresh requested)
    cached_insights = context_data.get("trend_insights", {})
    if url in cached_insights and not refresh:
        insight_data = cached_insights[url]
        return TrendInsightResponse(
            success=True,
            insight=TrendInsight(**insight_data),
            analysis_status="cached",
        )

    # Generate new insight
    analyzer = get_trend_analyzer()
    result = await analyzer.analyze_trend(
        url=url,
        industry=context_data.get("industry"),
        product_description=context_data.get("product_description"),
        business_model=context_data.get("business_model"),
        target_market=context_data.get("target_market"),
    )

    if result.status == "error":
        return TrendInsightResponse(
            success=False,
            insight=None,
            error=result.error,
            analysis_status="error",
        )

    # Cache the result
    insight_dict = result.to_dict()
    cached_insights[url] = insight_dict
    context_data["trend_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Generated trend insight for {url[:50]}... (user={user_id})")

    return TrendInsightResponse(
        success=True,
        insight=TrendInsight(**insight_dict),
        analysis_status=result.status,
    )


@router.get(
    "/v1/context/trends/insights",
    response_model=TrendInsightsListResponse,
    summary="List cached trend insights",
    description="""
    Retrieve all cached trend insights for the user.

    Returns insights sorted by analysis date (newest first).
    """,
)
@handle_api_errors("list trend insights")
async def list_trend_insights(
    user: dict[str, Any] = Depends(get_current_user),
) -> TrendInsightsListResponse:
    """List all cached trend insights."""
    user_id = extract_user_id(user)

    # Load cached insights
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return TrendInsightsListResponse(
            success=True,
            insights=[],
            count=0,
        )

    cached_insights = context_data.get("trend_insights", {})

    # Convert to list and sort by analyzed_at
    insights = []
    for url, data in cached_insights.items():
        try:
            insights.append(TrendInsight(**data))
        except Exception as e:
            logger.warning(f"Failed to parse cached trend insight for {url}: {e}")
            continue

    # Sort by analyzed_at (newest first)
    insights.sort(
        key=lambda i: i.analyzed_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )

    return TrendInsightsListResponse(
        success=True,
        insights=insights,
        count=len(insights),
    )


@router.delete(
    "/v1/context/trends/insights/{url_hash}",
    response_model=dict[str, str],
    summary="Delete a cached trend insight",
    description="""
    Remove a cached trend insight by URL hash.

    The url_hash is a URL-safe base64 encoding of the URL.
    """,
)
@handle_api_errors("delete trend insight")
async def delete_trend_insight(
    url_hash: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a cached trend insight."""
    import base64

    user_id = extract_user_id(user)

    # Decode the URL from the hash
    try:
        url = base64.urlsafe_b64decode(url_hash.encode()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decode URL hash: {e}")
        raise HTTPException(status_code=400, detail="Invalid URL hash") from None

    # Load context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise HTTPException(status_code=404, detail="No context found")

    cached_insights = context_data.get("trend_insights", {})
    if url not in cached_insights:
        raise HTTPException(status_code=404, detail="Insight not found")

    # Remove insight
    del cached_insights[url]
    context_data["trend_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Deleted trend insight for {url[:50]}... (user={user_id})")

    return {"status": "deleted"}


# =============================================================================
# Trend Summary Endpoints (AI-generated industry summaries)
# =============================================================================


# Rate limit: 1 refresh per hour per user
TREND_SUMMARY_REFRESH_COOLDOWN_HOURS = 1
TREND_SUMMARY_STALENESS_DAYS = 7


@router.get(
    "/v1/context/trends/summary",
    summary="Get cached trend summary",
    description="""
    Get the AI-generated market trend summary for the user's industry.

    Returns cached summary if available, with staleness indicator.
    If summary is stale (>7 days) or industry has changed, `stale` will be true.
    If user has no industry set, `needs_industry` will be true.

    **Refresh gating for "Now" view:**
    - Free tier: can only refresh if last refresh >28 days
    - Paid tiers (starter/pro/enterprise): can refresh anytime (1hr rate limit still applies)

    **Auto-refresh:** Frontend should call POST /refresh if stale=true.
    """,
)
@handle_api_errors("get trend summary")
async def get_trend_summary(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get cached trend summary with staleness check and refresh gating."""
    from datetime import timedelta

    from backend.api.context.models import TrendSummary, TrendSummaryResponse

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Load user context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=False,
            needs_industry=True,
        ).model_dump()

    # Check if user has industry
    industry = context_data.get("industry")
    if not industry:
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=False,
            needs_industry=True,
        ).model_dump()

    # Get cached trend summary
    summary_data = context_data.get("trend_summary")
    if not summary_data:
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=True,  # No summary = stale
            needs_industry=False,
            can_refresh_now=True,  # Allow initial generation
        ).model_dump()

    # Check staleness
    generated_at_str = summary_data.get("generated_at")
    summary_industry = summary_data.get("industry", "")
    is_stale = True
    days_since_generation = 0

    if generated_at_str:
        try:
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            age = datetime.now(UTC) - generated_at
            days_since_generation = age.days
            # Stale if >7 days old OR industry changed
            is_stale = (
                age > timedelta(days=TREND_SUMMARY_STALENESS_DAYS)
                or summary_industry.lower() != industry.lower()
            )
        except Exception as e:
            logger.warning(f"Failed to parse generated_at: {e}")
            is_stale = True

    # Determine if refresh is allowed (for "Now" view)
    # Free tier: only if >28 days since last generation
    # Paid tiers: always allowed (1hr rate limit handled in POST endpoint)
    can_refresh_now = True
    refresh_blocked_reason = None
    refresh_threshold_days = 28

    if tier == "free" and days_since_generation < refresh_threshold_days:
        can_refresh_now = False
        days_remaining = refresh_threshold_days - days_since_generation
        refresh_blocked_reason = f"Refresh available in {days_remaining} day{'s' if days_remaining != 1 else ''}. Upgrade to refresh anytime."

    # Build response
    try:
        summary = TrendSummary(
            summary=summary_data.get("summary", ""),
            key_trends=summary_data.get("key_trends", []),
            opportunities=summary_data.get("opportunities", []),
            threats=summary_data.get("threats", []),
            generated_at=datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            if generated_at_str
            else datetime.now(UTC),
            industry=summary_industry,
        )
        return TrendSummaryResponse(
            success=True,
            summary=summary,
            stale=is_stale,
            needs_industry=False,
            can_refresh_now=can_refresh_now,
            refresh_blocked_reason=refresh_blocked_reason,
        ).model_dump()
    except Exception as e:
        logger.warning(f"Failed to parse trend summary: {e}")
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=True,
            needs_industry=False,
        ).model_dump()


@router.post(
    "/v1/context/trends/summary/refresh",
    summary="Refresh trend summary",
    description="""
    Generate or refresh the AI-powered market trend summary.

    Uses Brave Search + Claude Haiku to generate a structured summary:
    - Executive summary of current market conditions
    - Key trends (3-5 items)
    - Opportunities (2-4 items)
    - Threats/challenges (2-4 items)

    **Rate Limits:**
    - All tiers: 1 refresh per hour (short-term rate limit)
    - Free tier: can only refresh if last refresh was >28 days ago
    - Paid tiers (starter/pro/enterprise): 1hr rate limit only

    **Cost:** ~$0.005 per generation.

    Returns 429 if free tier user tries to refresh within 28 days.
    Returns `rate_limited=true` if called within 1 hour of last refresh.
    """,
    responses={
        200: {"description": "Summary generated or rate limited"},
        400: {"description": "Industry not set"},
        429: {"description": "Free tier refresh blocked (28-day limit)"},
    },
)
@handle_api_errors("refresh trend summary")
async def refresh_trend_summary(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate or refresh the trend summary."""
    from datetime import timedelta

    from backend.api.context.models import TrendSummary, TrendSummaryRefreshResponse
    from backend.services.trend_summary_generator import get_trend_summary_generator

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Load user context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        context_data = {}

    # Check if user has industry
    industry = context_data.get("industry")
    if not industry:
        raise HTTPException(
            status_code=400,
            detail="Industry is required. Set your industry in Business Context settings first.",
        )

    # Check rate limits
    summary_data = context_data.get("trend_summary", {})
    generated_at_str = summary_data.get("generated_at")
    if generated_at_str:
        try:
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            time_since = datetime.now(UTC) - generated_at
            days_since = time_since.days

            # Free tier: 28-day minimum between refreshes
            refresh_threshold_days = 28
            if tier == "free" and days_since < refresh_threshold_days:
                days_remaining = refresh_threshold_days - days_since
                logger.info(
                    f"Trend summary refresh blocked for free user {user_id} "
                    f"({days_remaining} days remaining until refresh allowed)"
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Refresh available in {days_remaining} day{'s' if days_remaining != 1 else ''}. "
                    f"Upgrade to refresh anytime.",
                )

            # All tiers: 1-hour rate limit
            if time_since < timedelta(hours=TREND_SUMMARY_REFRESH_COOLDOWN_HOURS):
                minutes_remaining = int(
                    (timedelta(hours=TREND_SUMMARY_REFRESH_COOLDOWN_HOURS) - time_since).seconds
                    / 60
                )
                logger.info(
                    f"Trend summary refresh rate limited for user {user_id} "
                    f"({minutes_remaining} min remaining)"
                )
                return TrendSummaryRefreshResponse(
                    success=False,
                    summary=None,
                    error=f"Please wait {minutes_remaining} minutes before refreshing again",
                    rate_limited=True,
                ).model_dump()
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Failed to check rate limit: {e}")
            # Continue with refresh if we can't parse the date

    # Generate new summary
    generator = get_trend_summary_generator()
    result = await generator.generate_summary(industry)

    if result.status == "error":
        return TrendSummaryRefreshResponse(
            success=False,
            summary=None,
            error=result.error,
            rate_limited=False,
        ).model_dump()

    # Save to context
    summary_dict = result.to_dict()
    context_data["trend_summary"] = summary_dict
    user_repository.save_context(user_id, context_data)

    logger.info(f"Generated trend summary for {industry} (user={user_id})")

    # Build response
    summary = TrendSummary(
        summary=result.summary or "",
        key_trends=result.key_trends or [],
        opportunities=result.opportunities or [],
        threats=result.threats or [],
        generated_at=result.generated_at or datetime.now(UTC),
        industry=result.industry or industry,
    )

    return TrendSummaryRefreshResponse(
        success=True,
        summary=summary,
        rate_limited=False,
    ).model_dump()


# =============================================================================
# Trend Forecast Endpoints (Tier-Gated Timeframe Views)
# =============================================================================


@router.get(
    "/v1/context/trends/forecast",
    summary="Get trend forecast for timeframe",
    description="""
    Get AI-generated market forecast for a specific timeframe.

    **Tier Gating:**
    - Free: 3m only
    - Starter: 3m, 12m
    - Pro/Enterprise: 3m, 12m, 24m

    Returns 403 with upgrade_prompt if tier insufficient for requested timeframe.
    Cache key: `trend_forecasts_{timeframe}` in user_context.
    """,
    responses={
        200: {"description": "Forecast retrieved or tier-gated"},
        400: {"description": "Invalid timeframe"},
    },
)
@handle_api_errors("get trend forecast")
async def get_trend_forecast(
    timeframe: str = "3m",
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get trend forecast for a specific timeframe with tier gating."""
    from datetime import timedelta

    from backend.api.context.models import TrendForecastResponse, TrendSummary
    from backend.services.trend_summary_generator import (
        TIMEFRAME_LABELS,
        get_available_timeframes,
    )

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Validate timeframe
    if timeframe not in TIMEFRAME_LABELS:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

    # Get available timeframes for tier
    available_timeframes = get_available_timeframes(tier)

    # Load user context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return TrendForecastResponse(
            success=True,
            summary=None,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            stale=False,
            needs_industry=True,
        ).model_dump()

    # Check if user has industry
    industry = context_data.get("industry")
    if not industry:
        return TrendForecastResponse(
            success=True,
            summary=None,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            stale=False,
            needs_industry=True,
        ).model_dump()

    # Tier gating check
    if timeframe not in available_timeframes:
        upgrade_msg = {
            "12m": "Upgrade to Pro to access 12-month forecasts.",
            "24m": "Upgrade to Pro or Enterprise to access 24-month forecasts.",
        }.get(timeframe, "Upgrade to access this timeframe.")

        return TrendForecastResponse(
            success=False,
            summary=None,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            upgrade_prompt=upgrade_msg,
        ).model_dump()

    # Get cached forecast for this timeframe
    forecasts = context_data.get("trend_forecasts", {})
    forecast_data = forecasts.get(timeframe)

    if not forecast_data:
        return TrendForecastResponse(
            success=True,
            summary=None,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            stale=True,  # No forecast = stale
            needs_industry=False,
        ).model_dump()

    # Check staleness
    generated_at_str = forecast_data.get("generated_at")
    forecast_industry = forecast_data.get("industry", "")
    is_stale = True

    if generated_at_str:
        try:
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            age = datetime.now(UTC) - generated_at
            # Stale if >7 days old OR industry changed
            is_stale = (
                age > timedelta(days=TREND_SUMMARY_STALENESS_DAYS)
                or forecast_industry.lower() != industry.lower()
            )
        except Exception as e:
            logger.warning(f"Failed to parse generated_at: {e}")
            is_stale = True

    # Build response
    try:
        summary = TrendSummary(
            summary=forecast_data.get("summary", ""),
            key_trends=forecast_data.get("key_trends", []),
            opportunities=forecast_data.get("opportunities", []),
            threats=forecast_data.get("threats", []),
            generated_at=datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            if generated_at_str
            else datetime.now(UTC),
            industry=forecast_industry,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
        )
        return TrendForecastResponse(
            success=True,
            summary=summary,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            stale=is_stale,
            needs_industry=False,
        ).model_dump()
    except Exception as e:
        logger.warning(f"Failed to parse trend forecast: {e}")
        return TrendForecastResponse(
            success=True,
            summary=None,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            stale=True,
            needs_industry=False,
        ).model_dump()


@router.post(
    "/v1/context/trends/forecast/refresh",
    summary="Refresh trend forecast for timeframe",
    description="""
    Generate or refresh the AI-powered market forecast for a specific timeframe.

    **Tier Gating:**
    - Free: 3m only
    - Starter: 3m, 12m
    - Pro/Enterprise: 3m, 12m, 24m

    **Rate Limit:** 1 refresh per hour per timeframe.
    **Cost:** ~$0.005 per generation.

    Returns 403 with upgrade_prompt if tier insufficient.
    """,
    responses={
        200: {"description": "Forecast generated or rate limited"},
        400: {"description": "Industry not set or invalid timeframe"},
        403: {"description": "Tier insufficient for requested timeframe"},
    },
)
@handle_api_errors("refresh trend forecast")
async def refresh_trend_forecast(
    timeframe: str = "3m",
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate or refresh the trend forecast for a specific timeframe."""
    from datetime import timedelta

    from backend.api.context.models import TrendForecastResponse, TrendSummary
    from backend.services.trend_summary_generator import (
        TIMEFRAME_LABELS,
        get_available_timeframes,
        get_trend_summary_generator,
    )

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Validate timeframe
    if timeframe not in TIMEFRAME_LABELS:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}")

    # Get available timeframes for tier
    available_timeframes = get_available_timeframes(tier)

    # Tier gating check
    if timeframe not in available_timeframes:
        upgrade_msg = {
            "12m": "Upgrade to Pro to access 12-month forecasts.",
            "24m": "Upgrade to Pro or Enterprise to access 24-month forecasts.",
        }.get(timeframe, "Upgrade to access this timeframe.")

        raise HTTPException(
            status_code=403,
            detail=upgrade_msg,
        )

    # Load user context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        context_data = {}

    # Check if user has industry
    industry = context_data.get("industry")
    if not industry:
        raise HTTPException(
            status_code=400,
            detail="Industry is required. Set your industry in Business Context settings first.",
        )

    # Check rate limit (1 per hour per timeframe)
    forecasts = context_data.get("trend_forecasts", {})
    forecast_data = forecasts.get(timeframe, {})
    generated_at_str = forecast_data.get("generated_at")

    if generated_at_str:
        try:
            generated_at = datetime.fromisoformat(generated_at_str.replace("Z", "+00:00"))
            time_since = datetime.now(UTC) - generated_at
            if time_since < timedelta(hours=TREND_SUMMARY_REFRESH_COOLDOWN_HOURS):
                minutes_remaining = int(
                    (timedelta(hours=TREND_SUMMARY_REFRESH_COOLDOWN_HOURS) - time_since).seconds
                    / 60
                )
                logger.info(
                    f"Trend forecast refresh rate limited for user {user_id} "
                    f"(timeframe={timeframe}, {minutes_remaining} min remaining)"
                )
                return TrendForecastResponse(
                    success=False,
                    summary=None,
                    timeframe=timeframe,
                    available_timeframes=available_timeframes,
                    error=f"Please wait {minutes_remaining} minutes before refreshing again",
                ).model_dump()
        except Exception as e:
            logger.warning(f"Failed to check rate limit: {e}")
            # Continue with refresh if we can't parse the date

    # Generate new forecast
    generator = get_trend_summary_generator()
    result = await generator.generate_summary(
        industry,
        timeframe=timeframe,
        available_timeframes=available_timeframes,
    )

    if result.status == "error":
        return TrendForecastResponse(
            success=False,
            summary=None,
            timeframe=timeframe,
            available_timeframes=available_timeframes,
            error=result.error,
        ).model_dump()

    # Save to context under trend_forecasts[timeframe]
    forecast_dict = result.to_dict()
    forecasts[timeframe] = forecast_dict
    context_data["trend_forecasts"] = forecasts
    user_repository.save_context(user_id, context_data)

    logger.info(f"Generated trend forecast for {industry} ({timeframe}) (user={user_id})")

    # Build response
    summary = TrendSummary(
        summary=result.summary or "",
        key_trends=result.key_trends or [],
        opportunities=result.opportunities or [],
        threats=result.threats or [],
        generated_at=result.generated_at or datetime.now(UTC),
        industry=result.industry or industry,
        timeframe=timeframe,
        available_timeframes=available_timeframes,
    )

    return TrendForecastResponse(
        success=True,
        summary=summary,
        timeframe=timeframe,
        available_timeframes=available_timeframes,
        stale=False,
    ).model_dump()


# =============================================================================
# Goal History Endpoints (North Star Goal Tracking)
# =============================================================================

# Staleness threshold: prompt user to review goal after 180 days (strategic position)
GOAL_STALENESS_THRESHOLD_DAYS = 180


@router.get(
    "/v1/context/goal-history",
    response_model=GoalHistoryResponse,
    summary="Get goal change history",
    description="""
    Retrieve the history of north star goal changes for the user.

    Returns up to 10 most recent goal changes, newest first.
    Each entry includes the goal text, when it was changed, and the previous goal.

    **Use Cases:**
    - Display goal evolution timeline in strategic context page
    - Show users how their focus has shifted over time
    """,
)
@handle_api_errors("get goal history")
async def get_goal_history_endpoint(
    limit: int = 10,
    user: dict[str, Any] = Depends(get_current_user),
) -> GoalHistoryResponse:
    """Get history of goal changes."""
    from backend.services.goal_tracker import get_goal_history as fetch_goal_history

    user_id = extract_user_id(user)

    try:
        history = fetch_goal_history(user_id, limit=min(limit, 50))
    except Exception as e:
        logger.error(f"Failed to fetch goal history for user {user_id}: {e}")
        return GoalHistoryResponse(entries=[], count=0)

    entries = [
        GoalHistoryEntry(
            goal_text=h["goal_text"],
            changed_at=h["changed_at"],
            previous_goal=h["previous_goal"],
        )
        for h in history
    ]

    return GoalHistoryResponse(entries=entries, count=len(entries))


@router.get(
    "/v1/context/goal-staleness",
    response_model=GoalStalenessResponse,
    summary="Check goal staleness",
    description="""
    Check if the user's north star goal needs review.

    Returns:
    - Days since the goal was last changed
    - Whether to show a "Review your goal?" prompt (>30 days unchanged)
    - The current/last goal text

    **Use Cases:**
    - Dashboard banner prompting goal review
    - Strategic context page staleness indicator
    """,
)
@handle_api_errors("check goal staleness")
async def check_goal_staleness(
    user: dict[str, Any] = Depends(get_current_user),
) -> GoalStalenessResponse:
    """Check if goal needs review based on staleness."""
    from backend.services.goal_tracker import get_days_since_last_change

    user_id = extract_user_id(user)

    # Get current goal from context
    context_data = user_repository.get_context(user_id)
    current_goal = context_data.get("north_star_goal") if context_data else None

    if not current_goal:
        return GoalStalenessResponse(
            days_since_change=None,
            should_prompt=False,
            last_goal=None,
        )

    # Get days since last change
    try:
        days = get_days_since_last_change(user_id)
    except Exception as e:
        logger.warning(f"Failed to check goal staleness for user {user_id}: {e}")
        days = None

    should_prompt = days is not None and days >= GOAL_STALENESS_THRESHOLD_DAYS

    return GoalStalenessResponse(
        days_since_change=days,
        should_prompt=should_prompt,
        last_goal=current_goal,
    )
