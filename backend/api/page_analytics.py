"""Page analytics API endpoints for landing page metrics.

Public endpoints (rate limited):
- POST /api/v1/analytics/page-view - Record page view
- POST /api/v1/analytics/conversion - Record conversion event
- PATCH /api/v1/analytics/page-view/{id} - Update page view with duration/scroll

Admin endpoint:
- GET /api/admin/analytics/landing-page - Get aggregated metrics
"""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field

from backend.api.middleware.auth import require_admin
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors
from backend.services import page_analytics
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])
admin_router = APIRouter(prefix="/admin/analytics", tags=["admin"])

# Rate limits for public endpoints (prevent abuse)
PAGE_VIEW_RATE_LIMIT = "10/minute"
CONVERSION_RATE_LIMIT = "5/minute"


# Request/Response models
class PageViewRequest(BaseModel):
    """Request to record a page view."""

    path: str = Field(..., max_length=500, description="Page path (e.g., /, /pricing)")
    session_id: str = Field(
        ..., max_length=64, description="Visitor session identifier (fingerprint or cookie)"
    )
    referrer: str | None = Field(None, max_length=2000, description="HTTP referer header")
    duration_ms: int | None = Field(None, ge=0, description="Time spent on page (ms)")
    scroll_depth: int | None = Field(None, ge=0, le=100, description="Max scroll depth (0-100%)")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class PageViewResponse(BaseModel):
    """Response after recording a page view."""

    id: str = Field(..., description="Page view UUID (for later updates)")
    timestamp: datetime = Field(..., description="View timestamp")
    path: str = Field(..., description="Page path")
    session_id: str = Field(..., description="Session identifier")


class PageViewUpdateRequest(BaseModel):
    """Request to update page view with engagement metrics (on unload)."""

    duration_ms: int | None = Field(None, ge=0, description="Time spent on page (ms)")
    scroll_depth: int | None = Field(None, ge=0, le=100, description="Max scroll depth (0-100%)")


class ConversionRequest(BaseModel):
    """Request to record a conversion event."""

    event_type: str = Field(
        ...,
        max_length=50,
        pattern="^(signup_click|signup_complete|cta_click|waitlist_submit)$",
        description="Event type",
    )
    source_path: str = Field(..., max_length=500, description="Page where event occurred")
    session_id: str = Field(..., max_length=64, description="Visitor session identifier")
    element_id: str | None = Field(None, max_length=100, description="ID of clicked element")
    element_text: str | None = Field(None, max_length=200, description="Text of clicked element")
    metadata: dict[str, Any] | None = Field(None, description="Additional data")


class ConversionResponse(BaseModel):
    """Response after recording a conversion event."""

    id: str = Field(..., description="Conversion event UUID")
    timestamp: datetime = Field(..., description="Event timestamp")
    event_type: str = Field(..., description="Event type")
    source_path: str = Field(..., description="Source page")


class LandingPageMetricsResponse(BaseModel):
    """Aggregated landing page metrics for admin dashboard."""

    daily_stats: list[dict[str, Any]] = Field(..., description="Daily page view stats")
    geo_breakdown: list[dict[str, Any]] = Field(..., description="Visitors by country")
    funnel: dict[str, Any] = Field(..., description="Conversion funnel stats")
    bounce_rate: dict[str, Any] = Field(..., description="Bounce rate for landing page")


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request headers (respects X-Forwarded-For for proxies)."""
    # Check X-Forwarded-For header (set by nginx/proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take first IP in chain (original client)
        return forwarded.split(",")[0].strip()
    # Check X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    return None


# Public endpoints (rate limited)


@router.post(
    "/page-view",
    response_model=PageViewResponse,
    summary="Record page view (public, no auth required)",
    description="Record a page view event. Rate limited to 10/minute per IP. No authentication required.",
)
@limiter.limit(PAGE_VIEW_RATE_LIMIT)
@handle_api_errors("record page view")
async def record_page_view(
    request: Request,
    body: PageViewRequest,
    user_agent: str | None = Header(None, alias="User-Agent"),
) -> PageViewResponse:
    """Record a page view with optional geo lookup."""
    ip_address = get_client_ip(request)

    result = await page_analytics.record_page_view(
        path=body.path,
        session_id=body.session_id,
        ip_address=ip_address,
        referrer=body.referrer,
        user_agent=user_agent,
        metadata=body.metadata,
    )

    logger.debug(f"Page view recorded: path={body.path} session={body.session_id[:8]}...")

    return PageViewResponse(
        id=str(result["id"]),
        timestamp=result["timestamp"],
        path=result["path"],
        session_id=result["session_id"],
    )


@router.api_route(
    "/page-view/{view_id}",
    methods=["PATCH", "POST"],
    response_model=PageViewResponse | None,
    summary="Update page view (public, no auth required)",
    description="Update page view with duration/scroll data (call on page unload). Supports POST for sendBeacon. No authentication required.",
)
@limiter.limit(PAGE_VIEW_RATE_LIMIT)
@handle_api_errors("update page view")
async def update_page_view(
    request: Request,
    view_id: str,
    body: PageViewUpdateRequest,
) -> PageViewResponse | None:
    """Update page view with engagement metrics."""
    result = page_analytics.update_page_view(
        view_id=view_id,
        duration_ms=body.duration_ms,
        scroll_depth=body.scroll_depth,
    )

    if not result:
        return None

    return PageViewResponse(
        id=str(result["id"]),
        timestamp=result["timestamp"],
        path=result["path"],
        session_id=result["session_id"],
    )


@router.post(
    "/conversion",
    response_model=ConversionResponse,
    summary="Record conversion event (public, no auth required)",
    description="Record a conversion event (signup click, etc.). Rate limited to 5/minute per IP. No authentication required.",
)
@limiter.limit(CONVERSION_RATE_LIMIT)
@handle_api_errors("record conversion")
async def record_conversion(
    request: Request,
    body: ConversionRequest,
) -> ConversionResponse:
    """Record a conversion event."""
    result = page_analytics.record_conversion(
        event_type=body.event_type,
        source_path=body.source_path,
        session_id=body.session_id,
        element_id=body.element_id,
        element_text=body.element_text,
        metadata=body.metadata,
    )

    logger.info(f"Conversion recorded: type={body.event_type} path={body.source_path}")

    return ConversionResponse(
        id=str(result["id"]),
        timestamp=result["timestamp"],
        event_type=result["event_type"],
        source_path=result["source_path"],
    )


# Admin endpoints


@admin_router.get(
    "/landing-page",
    response_model=LandingPageMetricsResponse,
    summary="Get landing page metrics",
    description="Get aggregated landing page analytics (admin only).",
    dependencies=[Depends(require_admin)],
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get landing page metrics")
async def get_landing_page_metrics(
    request: Request,
    start_date: date | None = Query(None, description="Start of date range (default: 30 days ago)"),
    end_date: date | None = Query(None, description="End of date range (default: today)"),
) -> LandingPageMetricsResponse:
    """Get comprehensive landing page analytics."""
    metrics = page_analytics.get_landing_page_metrics(start_date, end_date)
    return LandingPageMetricsResponse(**metrics)


@admin_router.get(
    "/daily-stats",
    summary="Get daily page view stats",
    description="Get daily page view statistics (admin only).",
    dependencies=[Depends(require_admin)],
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get daily stats")
async def get_daily_stats(
    request: Request,
    start_date: date | None = Query(None, description="Start date"),
    end_date: date | None = Query(None, description="End date"),
    path: str | None = Query(None, description="Filter by path"),
) -> list[dict[str, Any]]:
    """Get daily page view statistics."""
    return page_analytics.get_daily_stats(start_date, end_date, path)


@admin_router.get(
    "/geo-breakdown",
    summary="Get visitor geo breakdown",
    description="Get visitor breakdown by country (admin only).",
    dependencies=[Depends(require_admin)],
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get geo breakdown")
async def get_geo_breakdown(
    request: Request,
    start_date: date | None = Query(None, description="Start date"),
    end_date: date | None = Query(None, description="End date"),
    limit: int = Query(20, ge=1, le=100, description="Max countries to return"),
) -> list[dict[str, Any]]:
    """Get visitor breakdown by country."""
    return page_analytics.get_geo_breakdown(start_date, end_date, limit)


@admin_router.get(
    "/funnel",
    summary="Get conversion funnel stats",
    description="Get conversion funnel statistics (admin only).",
    dependencies=[Depends(require_admin)],
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get funnel stats")
async def get_funnel_stats(
    request: Request,
    start_date: date | None = Query(None, description="Start date"),
    end_date: date | None = Query(None, description="End date"),
) -> dict[str, Any]:
    """Get conversion funnel statistics."""
    return page_analytics.get_funnel_stats(start_date, end_date)


@admin_router.get(
    "/bounce-rate",
    summary="Get bounce rate",
    description="Get bounce rate for a specific page (admin only).",
    dependencies=[Depends(require_admin)],
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get bounce rate")
async def get_bounce_rate(
    request: Request,
    start_date: date | None = Query(None, description="Start date"),
    end_date: date | None = Query(None, description="End date"),
    path: str = Query("/", description="Page path to analyze"),
) -> dict[str, Any]:
    """Get bounce rate for a page."""
    return page_analytics.get_bounce_rate(start_date, end_date, path)
