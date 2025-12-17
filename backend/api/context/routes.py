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
    ContextResponse,
    ContextUpdateSource,
    ContextUpdateSuggestion,
    ContextWithTrends,
    DismissRefreshRequest,
    EnrichmentRequest,
    EnrichmentResponse,
    InsightCategory,
    InsightMetricResponse,
    InsightsResponse,
    PendingUpdatesResponse,
    RefreshCheckResponse,
    StaleFieldSummary,
    StaleMetricResponse,
    StaleMetricsResponse,
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

    # Parse into BusinessContext
    context = context_data_to_model(context_data)

    # Parse benchmark timestamps from raw data
    benchmark_timestamps = context_data.get("benchmark_timestamps")

    return ContextResponse(
        exists=True,
        context=context,
        updated_at=context_data.get("updated_at"),
        benchmark_timestamps=benchmark_timestamps,
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
    context_dict["benchmark_timestamps"] = update_benchmark_timestamps(
        context_dict, existing_context
    )

    # Append to benchmark history for trend tracking
    context_dict["benchmark_history"] = append_benchmark_history(context_dict, existing_context)

    # Save to database
    user_repository.save_context(user_id, context_dict)

    logger.info(f"Updated context for user {user_id}")

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
        logger.error(f"Enrichment failed: {e}")
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

    # Get context with extended fields
    row = execute_query(
        """
        SELECT updated_at, last_refresh_prompt, onboarding_completed
        FROM user_context
        WHERE user_id = %s
        """,
        (user_id,),
        fetch="one",
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

    # Update timestamp in DB
    result = execute_query(
        """
        UPDATE user_context
        SET last_refresh_prompt = NOW(), updated_at = updated_at
        WHERE user_id = %s
        RETURNING user_id
        """,
        (user_id,),
        fetch="one",
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
