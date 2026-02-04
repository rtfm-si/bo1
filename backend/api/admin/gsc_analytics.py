"""GSC Analytics admin endpoints.

Provides admin dashboard for viewing and syncing GSC search analytics.
"""

import logging
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.gsc_sync import SyncError, sync_analytics, sync_daily_analytics
from bo1.config import get_settings
from bo1.logging.errors import ErrorCode
from bo1.state.repositories.gsc_repository import gsc_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gsc", tags=["admin-gsc"])


class GSCOverviewResponse(BaseModel):
    """Aggregated GSC metrics overview."""

    connected: bool
    site_url: str | None = None
    total_impressions: int = 0
    total_clicks: int = 0
    avg_ctr: float = 0.0
    avg_position: float | None = None
    decision_count: int = 0
    earliest_date: str | None = None
    latest_date: str | None = None
    last_sync: str | None = None


class GSCDecisionMetrics(BaseModel):
    """GSC metrics for a single decision."""

    id: str
    title: str
    slug: str
    category: str
    impressions: int
    clicks: int
    ctr: float
    position: float | None
    last_data_date: str | None


class GSCDecisionsResponse(BaseModel):
    """List of decisions with GSC metrics."""

    decisions: list[GSCDecisionMetrics]
    total_count: int


class GSCDecisionDetailResponse(BaseModel):
    """Detailed GSC data for a single decision."""

    id: str
    title: str
    slug: str
    category: str
    total_impressions: int
    total_clicks: int
    avg_ctr: float
    avg_position: float | None
    snapshots: list[dict[str, Any]]


class GSCSyncResponse(BaseModel):
    """Response from sync operation."""

    status: str
    start_date: str | None = None
    end_date: str | None = None
    pages_fetched: int = 0
    decisions_matched: int = 0
    snapshots_created: int = 0
    errors: list[str] = []


@router.get("/overview", response_model=GSCOverviewResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get GSC overview")
async def get_gsc_overview(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Days of data to aggregate"),
    _admin: str = Depends(require_admin_any),
) -> GSCOverviewResponse:
    """Get aggregated GSC metrics overview (admin only).

    Args:
        request: FastAPI request object
        days: Number of days to aggregate (default 30)

    Returns:
        Aggregated metrics across all decisions
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        return GSCOverviewResponse(connected=False)

    connection = gsc_repository.get_connection()
    if not connection:
        return GSCOverviewResponse(connected=False)

    # Calculate date range
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    # Get aggregated metrics
    metrics = gsc_repository.get_aggregated_metrics(
        start_date=start_date,
        end_date=end_date,
    )

    # Get last sync date
    last_sync = gsc_repository.get_last_sync_date()

    return GSCOverviewResponse(
        connected=True,
        site_url=connection.get("site_url"),
        total_impressions=int(metrics.get("total_impressions", 0)),
        total_clicks=int(metrics.get("total_clicks", 0)),
        avg_ctr=float(metrics.get("avg_ctr", 0)),
        avg_position=metrics.get("avg_position"),
        decision_count=int(metrics.get("decision_count", 0)),
        earliest_date=metrics.get("earliest_date").isoformat()
        if metrics.get("earliest_date")
        else None,
        latest_date=metrics.get("latest_date").isoformat() if metrics.get("latest_date") else None,
        last_sync=last_sync.isoformat() if last_sync else None,
    )


@router.get("/decisions", response_model=GSCDecisionsResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get GSC decisions")
async def get_gsc_decisions(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Days of data to aggregate"),
    order_by: str = Query(
        default="impressions", description="Sort by: impressions, clicks, ctr, position"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    _admin: str = Depends(require_admin_any),
) -> GSCDecisionsResponse:
    """Get decisions ranked by GSC metrics (admin only).

    Args:
        request: FastAPI request object
        days: Number of days to aggregate
        order_by: Column to sort by
        limit: Maximum results

    Returns:
        List of decisions with their GSC metrics
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    # Calculate date range
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    # Get decisions with metrics
    decisions = gsc_repository.get_decisions_with_metrics(
        start_date=start_date,
        end_date=end_date,
        order_by=order_by,
        limit=limit,
    )

    return GSCDecisionsResponse(
        decisions=[
            GSCDecisionMetrics(
                id=d["id"],
                title=d["title"],
                slug=d["slug"],
                category=d["category"],
                impressions=int(d.get("impressions", 0)),
                clicks=int(d.get("clicks", 0)),
                ctr=float(d.get("ctr", 0)),
                position=d.get("position"),
                last_data_date=d["last_data_date"].isoformat() if d.get("last_data_date") else None,
            )
            for d in decisions
        ],
        total_count=len(decisions),
    )


@router.get("/decisions/{decision_id}", response_model=GSCDecisionDetailResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get GSC decision detail")
async def get_gsc_decision_detail(
    request: Request,
    decision_id: str,
    days: int = Query(default=90, ge=1, le=365, description="Days of history"),
    _admin: str = Depends(require_admin_any),
) -> GSCDecisionDetailResponse:
    """Get detailed GSC data for a specific decision (admin only).

    Args:
        request: FastAPI request object
        decision_id: Decision ID
        days: Days of history to return

    Returns:
        Decision details with time-series snapshots
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    # Get decision info
    from bo1.state.repositories.decision_repository import decision_repository

    decision = decision_repository.get_by_id(decision_id)
    if not decision:
        raise http_error(ErrorCode.NOT_FOUND, "Decision not found", 404)

    # Calculate date range
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    # Get snapshots
    snapshots = gsc_repository.get_snapshots_for_decision(
        decision_id=decision_id,
        start_date=start_date,
        end_date=end_date,
        limit=days,
    )

    # Calculate aggregates
    total_impressions = sum(s.get("impressions", 0) for s in snapshots)
    total_clicks = sum(s.get("clicks", 0) for s in snapshots)
    avg_ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    positions = [s.get("position") for s in snapshots if s.get("position")]
    avg_position = sum(positions) / len(positions) if positions else None

    return GSCDecisionDetailResponse(
        id=decision["id"],
        title=decision["title"],
        slug=decision["slug"],
        category=decision["category"],
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        avg_ctr=avg_ctr,
        avg_position=avg_position,
        snapshots=[
            {
                "date": s["date"].isoformat() if s.get("date") else None,
                "impressions": s.get("impressions", 0),
                "clicks": s.get("clicks", 0),
                "ctr": s.get("ctr", 0),
                "position": s.get("position"),
            }
            for s in snapshots
        ],
    )


@router.post("/sync", response_model=GSCSyncResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("sync GSC data")
async def trigger_gsc_sync(
    request: Request,
    days: int = Query(default=7, ge=1, le=30, description="Days of data to sync"),
    _admin: str = Depends(require_admin_any),
) -> GSCSyncResponse:
    """Trigger manual GSC data sync (admin only).

    Fetches search analytics from GSC and stores snapshots.

    Args:
        request: FastAPI request object
        days: Number of days to sync (default 7)

    Returns:
        Sync result with counts
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    # Check connection
    connection = gsc_repository.get_connection()
    if not connection:
        raise http_error(ErrorCode.NOT_FOUND, "GSC not connected", 404)

    if not connection.get("site_url"):
        raise http_error(ErrorCode.VALIDATION_ERROR, "No GSC site selected", 400)

    try:
        # Calculate date range
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)

        result = sync_analytics(
            start_date=start_date,
            end_date=end_date,
        )

        return GSCSyncResponse(
            status="success" if not result.get("errors") else "partial",
            start_date=result.get("start_date"),
            end_date=result.get("end_date"),
            pages_fetched=result.get("pages_fetched", 0),
            decisions_matched=result.get("decisions_matched", 0),
            snapshots_created=result.get("snapshots_created", 0),
            errors=result.get("errors", []),
        )

    except SyncError as e:
        raise http_error(ErrorCode.EXT_API_ERROR, str(e), 502) from None


@router.post("/sync/historical", response_model=GSCSyncResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("sync GSC historical data")
async def trigger_gsc_historical_sync(
    request: Request,
    days: int = Query(default=90, ge=1, le=365, description="Days of history to sync"),
    _admin: str = Depends(require_admin_any),
) -> GSCSyncResponse:
    """Trigger historical GSC data sync (admin only).

    Fetches day-by-day data for time series analysis.
    Only fetches dates not already in the database.

    Args:
        request: FastAPI request object
        days: Days of history to sync (default 90)

    Returns:
        Sync result
    """
    settings = get_settings()

    if not settings.google_search_console_enabled:
        raise http_error(ErrorCode.FEATURE_DISABLED, "Search Console integration is disabled", 403)

    # Check connection
    connection = gsc_repository.get_connection()
    if not connection:
        raise http_error(ErrorCode.NOT_FOUND, "GSC not connected", 404)

    if not connection.get("site_url"):
        raise http_error(ErrorCode.VALIDATION_ERROR, "No GSC site selected", 400)

    try:
        result = sync_daily_analytics(days_back=days)

        if result.get("status") == "up_to_date":
            return GSCSyncResponse(
                status="up_to_date",
                errors=[],
            )

        return GSCSyncResponse(
            status="success" if not result.get("errors") else "partial",
            start_date=result.get("start_date"),
            end_date=result.get("end_date"),
            snapshots_created=result.get("total_snapshots", 0),
            errors=result.get("errors", []),
        )

    except SyncError as e:
        raise http_error(ErrorCode.EXT_API_ERROR, str(e), 502) from None
