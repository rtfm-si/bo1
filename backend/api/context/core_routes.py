"""Core context CRUD endpoints and refresh/enrichment.

Provides:
- GET /api/v1/context - Get user's saved business context
- PUT /api/v1/context - Update user's business context
- DELETE /api/v1/context - Delete user's saved context
- POST /api/v1/context/enrich - Enrich context from website
- GET /api/v1/context/refresh-check - Check if refresh prompt needed
- POST /api/v1/context/dismiss-refresh - Dismiss refresh prompt
- POST /api/v1/context/competitors/detect - Auto-detect competitors
- POST /api/v1/context/trends/refresh - Refresh market trends
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

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
    BusinessContext,
    CompetitorDetectRequest,
    CompetitorDetectResponse,
    ContextResponse,
    DismissRefreshRequest,
    EnrichmentRequest,
    EnrichmentResponse,
    RefreshCheckResponse,
    StaleFieldSummary,
    TrendsRefreshRequest,
    TrendsRefreshResponse,
)
from backend.api.context.services import (
    CONTEXT_REFRESH_DAYS,
    append_benchmark_history,
    context_data_to_model,
    enriched_data_to_dict,
    enriched_to_context_model,
    merge_context,
    sanitize_context_values,
    update_benchmark_timestamps,
)
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTEXT_RATE_LIMIT, limiter
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.logging.errors import log_error
from bo1.services.enrichment import EnrichmentService
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


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
        403: ERROR_403_RESPONSE,
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

    # Get auto-detect status for competitor refresh indicator (non-critical)
    try:
        auto_detect_status = get_auto_detect_status(user_id)
    except Exception as e:
        logger.warning(f"Failed to get auto-detect status for user {user_id}: {e}")
        auto_detect_status = {}

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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
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
    context_dict = context.model_dump(exclude_unset=True)

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
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@handle_api_errors("delete context")
async def delete_context(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    """Delete user's saved business context."""
    user_id = extract_user_id(user)

    # Delete from database
    deleted = user_repository.delete_context(user_id)

    if not deleted:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "No context found to delete",
            status=404,
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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("enrich context")
async def enrich_context(
    request: Request,
    body: EnrichmentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> EnrichmentResponse:
    """Enrich business context from website URL and auto-save."""
    try:
        user_id = extract_user_id(user)
        logger.info(f"Enriching context from {body.website_url} for user {user_id}")

        # Run enrichment
        service = EnrichmentService()
        try:
            enriched = await service.enrich_from_url(body.website_url)
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
            url=body.website_url,
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
    responses={403: ERROR_403_RESPONSE},
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

    # Get stale metrics (non-critical - return empty if fails)
    try:
        stale_result = get_stale_metrics_for_session(
            user_id=user_id,
            action_affected_fields=action_affected_fields if action_affected_fields else None,
        )
    except Exception as e:
        logger.warning(f"Failed to get stale metrics for user {user_id}: {e}")
        from backend.services.insight_staleness import StaleMetricsResult

        stale_result = StaleMetricsResult(
            has_stale_metrics=False,
            stale_metrics=[],
            total_metrics_checked=0,
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
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
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
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    # Store expiry in context JSON
    context_data = user_repository.get_context(user_id) or {}
    context_data["refresh_dismissed_until"] = dismissed_until.isoformat()
    user_repository.save_context(user_id, context_data)

    logger.info(
        f"User {user_id} dismissed refresh prompt for {expiry_days} days (volatility={volatility})"
    )

    return {"status": "dismissed", "dismissed_until": dismissed_until.isoformat()}


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
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("detect competitors")
async def detect_competitors(
    request: Request,
    body: CompetitorDetectRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorDetectResponse:
    """Detect competitors using Tavily Search API and auto-save to Competitor Watch."""
    user_id = extract_user_id(user)
    industry = body.industry if body else None
    product_description = body.product_description if body else None

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
    responses={403: ERROR_403_RESPONSE, 429: RATE_LIMIT_RESPONSE},
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("refresh trends")
async def refresh_trends(
    request: Request,
    body: TrendsRefreshRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> TrendsRefreshResponse:
    """Refresh market trends using Brave Search."""
    user_id = extract_user_id(user)
    industry = body.industry if body else None

    return await refresh_market_trends(user_id, industry)
