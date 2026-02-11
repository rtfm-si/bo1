"""FastAPI router for trend-related context endpoints.

Provides:
- GET /v1/context/with-trends - Get context with trend indicators
- GET /v1/context/stale-metrics - Get stale business context metrics
- POST /v1/context/trends/analyze - Analyze a trend URL for insights
- GET /v1/context/trends/insights - List cached trend insights
- DELETE /v1/context/trends/insights/{url_hash} - Delete a cached trend insight
- GET /v1/context/trends/summary - Get cached trend summary
- POST /v1/context/trends/summary/refresh - Refresh trend summary
- GET /v1/context/trends/forecast - Get trend forecast for timeframe
- POST /v1/context/trends/forecast/refresh - Refresh trend forecast
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.api.context.models import (
    BusinessContext,
    ContextWithTrends,
    StaleMetricResponse,
    StaleMetricsResponse,
    TrendInsight,
    TrendInsightRequest,
    TrendInsightResponse,
    TrendInsightsListResponse,
)
from backend.api.context.models import (
    StalenessReason as ModelStalenessReason,
)
from backend.api.context.models import (
    VolatilityLevel as ModelVolatilityLevel,
)
from backend.api.context.services import context_data_to_model
from backend.api.middleware.auth import get_current_user
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])

# Rate limit: 1 refresh per hour per user
TREND_SUMMARY_REFRESH_COOLDOWN_HOURS = 1
TREND_SUMMARY_STALENESS_DAYS = 7


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
    responses={403: ERROR_403_RESPONSE},
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
    responses={403: ERROR_403_RESPONSE},
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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
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
        raise http_error(ErrorCode.API_BAD_REQUEST, "URL required", status=400)

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
    responses={403: ERROR_403_RESPONSE},
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
    responses={400: ERROR_400_RESPONSE, 403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
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
        raise http_error(ErrorCode.API_BAD_REQUEST, "Invalid URL hash", status=400) from None

    # Load context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    cached_insights = context_data.get("trend_insights", {})
    if url not in cached_insights:
        raise http_error(ErrorCode.API_NOT_FOUND, "Insight not found", status=404)

    # Remove insight
    del cached_insights[url]
    context_data["trend_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Deleted trend insight for {url[:50]}... (user={user_id})")

    return {"status": "deleted"}


# =============================================================================
# Trend Summary Endpoints (AI-generated industry summaries)
# =============================================================================


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
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("get trend summary")
async def get_trend_summary(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get cached trend summary with staleness check and refresh gating."""
    from datetime import timedelta

    from backend.api.context.models import TrendSummary, TrendSummaryResponse
    from backend.services.trend_summary_generator import get_available_timeframes

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Get available forecast timeframes for this tier
    available_timeframes = get_available_timeframes(tier)

    # Load user context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=False,
            needs_industry=True,
            available_timeframes=available_timeframes,
        ).model_dump()

    # Check if user has industry
    industry = context_data.get("industry")
    if not industry:
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=False,
            needs_industry=True,
            available_timeframes=available_timeframes,
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
            available_timeframes=available_timeframes,
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
            available_timeframes=available_timeframes,
        ).model_dump()
    except Exception as e:
        logger.warning(f"Failed to parse trend summary: {e}")
        return TrendSummaryResponse(
            success=True,
            summary=None,
            stale=True,
            needs_industry=False,
            available_timeframes=available_timeframes,
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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
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
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            "Industry is required. Set your industry in Business Context settings first.",
            status=400,
        )

    # Check rate limits
    summary_data = context_data.get("trend_summary") or {}
    generated_at_str = summary_data.get("generated_at") if isinstance(summary_data, dict) else None
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
                raise http_error(
                    ErrorCode.API_RATE_LIMIT,
                    f"Refresh available in {days_remaining} day{'s' if days_remaining != 1 else ''}. "
                    f"Upgrade to refresh anytime.",
                    status=429,
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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
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
        raise http_error(ErrorCode.API_BAD_REQUEST, f"Invalid timeframe: {timeframe}", status=400)

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
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
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
        raise http_error(ErrorCode.API_BAD_REQUEST, f"Invalid timeframe: {timeframe}", status=400)

    # Get available timeframes for tier
    available_timeframes = get_available_timeframes(tier)

    # Tier gating check
    if timeframe not in available_timeframes:
        upgrade_msg = {
            "12m": "Upgrade to Pro to access 12-month forecasts.",
            "24m": "Upgrade to Pro or Enterprise to access 24-month forecasts.",
        }.get(timeframe, "Upgrade to access this timeframe.")

        raise http_error(ErrorCode.API_FORBIDDEN, upgrade_msg, status=403)

    # Load user context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        context_data = {}

    # Check if user has industry
    industry = context_data.get("industry")
    if not industry:
        raise http_error(
            ErrorCode.API_BAD_REQUEST,
            "Industry is required. Set your industry in Business Context settings first.",
            status=400,
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
