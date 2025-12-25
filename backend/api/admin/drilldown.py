"""Admin API endpoints for drill-down views.

Provides paginated list views with time-period filtering for:
- Users (registered in period)
- Costs (incurred in period)
- Waitlist (added in period)
- Whitelist (added in period)

All endpoints:
- Require admin authentication
- Support time periods: hour, day, week, month, all
- Support pagination via limit/offset
"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.admin.models import (
    CostDrillDownItem,
    CostDrillDownResponse,
    TimePeriod,
    UserDrillDownItem,
    UserDrillDownResponse,
    WaitlistDrillDownItem,
    WaitlistDrillDownResponse,
    WhitelistDrillDownItem,
    WhitelistDrillDownResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.db_helpers import execute_query, get_single_value
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.pagination import make_pagination_fields
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/drilldown", tags=["Admin - Drill-Down"])


def _get_time_filter(period: TimePeriod) -> str:
    """Convert time period to SQL interval filter.

    Args:
        period: Time period enum value

    Returns:
        SQL WHERE clause fragment for filtering by created_at
    """
    if period == TimePeriod.ALL:
        return "TRUE"

    intervals = {
        TimePeriod.HOUR: "1 hour",
        TimePeriod.DAY: "1 day",
        TimePeriod.WEEK: "7 days",
        TimePeriod.MONTH: "30 days",
    }
    interval = intervals[period]
    return f"created_at >= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - INTERVAL '{interval}'"


def _to_iso(value) -> str:
    """Convert datetime to ISO format string."""
    return value.isoformat() if value else ""


@router.get(
    "/users",
    response_model=UserDrillDownResponse,
    summary="List users with time filter",
    description="Get paginated list of users registered within the specified time period.",
    responses={
        200: {"description": "Users retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get user drill-down")
async def get_users_drilldown(
    request: Request,
    period: TimePeriod = Query(TimePeriod.DAY, description="Time period filter"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _admin: str = Depends(require_admin_any),
) -> UserDrillDownResponse:
    """Get paginated list of users registered in period."""
    time_filter = _get_time_filter(period)

    # Get total count
    total = get_single_value(
        f"SELECT COUNT(*) FROM users WHERE {time_filter}",
        (),
        column="count",
        default=0,
    )

    # Get paginated items
    rows = execute_query(
        f"""
        SELECT id, email, subscription_tier, is_admin, created_at
        FROM users
        WHERE {time_filter}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )

    items = [
        UserDrillDownItem(
            user_id=row["id"],
            email=row["email"],
            subscription_tier=row["subscription_tier"],
            is_admin=row["is_admin"],
            created_at=_to_iso(row["created_at"]),
        )
        for row in rows
    ]

    pagination = make_pagination_fields(total, limit, offset)
    logger.info(f"Admin: Retrieved {len(items)} users for period={period.value}")

    return UserDrillDownResponse(
        items=items,
        period=period.value,
        **pagination,
    )


@router.get(
    "/costs",
    response_model=CostDrillDownResponse,
    summary="List cost records with time filter",
    description="Get paginated list of cost records within the specified time period.",
    responses={
        200: {"description": "Costs retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get cost drill-down")
async def get_costs_drilldown(
    request: Request,
    period: TimePeriod = Query(TimePeriod.DAY, description="Time period filter"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _admin: str = Depends(require_admin_any),
) -> CostDrillDownResponse:
    """Get paginated list of cost records in period."""
    time_filter = _get_time_filter(period)

    # Get total count and sum
    stats = execute_query(
        f"SELECT COUNT(*) as count, COALESCE(SUM(cost_usd), 0) as total FROM api_costs WHERE {time_filter}",
        (),
        fetch="one",
    )
    total = stats["count"] if stats else 0
    total_cost = float(stats["total"]) if stats else 0.0

    # Get paginated items with user email join
    rows = execute_query(
        f"""
        SELECT c.id, c.user_id, u.email, c.provider, c.model, c.cost_usd, c.created_at
        FROM api_costs c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE c.{time_filter.replace("created_at", "c.created_at")}
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )

    items = [
        CostDrillDownItem(
            id=row["id"],
            user_id=row["user_id"] or "unknown",
            email=row["email"],
            provider=row["provider"],
            model=row["model"],
            amount_usd=float(row["cost_usd"]) if row["cost_usd"] else 0.0,
            created_at=_to_iso(row["created_at"]),
        )
        for row in rows
    ]

    pagination = make_pagination_fields(total, limit, offset)
    logger.info(
        f"Admin: Retrieved {len(items)} cost records for period={period.value}, total=${total_cost:.2f}"
    )

    return CostDrillDownResponse(
        items=items,
        period=period.value,
        total_cost_usd=total_cost,
        **pagination,
    )


@router.get(
    "/waitlist",
    response_model=WaitlistDrillDownResponse,
    summary="List waitlist entries with time filter",
    description="Get paginated list of waitlist entries added within the specified time period.",
    responses={
        200: {"description": "Waitlist entries retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get waitlist drill-down")
async def get_waitlist_drilldown(
    request: Request,
    period: TimePeriod = Query(TimePeriod.DAY, description="Time period filter"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _admin: str = Depends(require_admin_any),
) -> WaitlistDrillDownResponse:
    """Get paginated list of waitlist entries in period."""
    time_filter = _get_time_filter(period)

    # Get total count
    total = get_single_value(
        f"SELECT COUNT(*) FROM waitlist WHERE {time_filter}",
        (),
        column="count",
        default=0,
    )

    # Get paginated items
    rows = execute_query(
        f"""
        SELECT id, email, status, source, created_at
        FROM waitlist
        WHERE {time_filter}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )

    items = [
        WaitlistDrillDownItem(
            id=str(row["id"]),
            email=row["email"],
            status=row["status"],
            source=row["source"],
            created_at=_to_iso(row["created_at"]),
        )
        for row in rows
    ]

    pagination = make_pagination_fields(total, limit, offset)
    logger.info(f"Admin: Retrieved {len(items)} waitlist entries for period={period.value}")

    return WaitlistDrillDownResponse(
        items=items,
        period=period.value,
        **pagination,
    )


@router.get(
    "/whitelist",
    response_model=WhitelistDrillDownResponse,
    summary="List whitelist entries with time filter",
    description="Get paginated list of whitelist entries added within the specified time period.",
    responses={
        200: {"description": "Whitelist entries retrieved successfully"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get whitelist drill-down")
async def get_whitelist_drilldown(
    request: Request,
    period: TimePeriod = Query(TimePeriod.DAY, description="Time period filter"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    _admin: str = Depends(require_admin_any),
) -> WhitelistDrillDownResponse:
    """Get paginated list of whitelist entries in period."""
    time_filter = _get_time_filter(period)

    # Get total count
    total = get_single_value(
        f"SELECT COUNT(*) FROM beta_whitelist WHERE {time_filter}",
        (),
        column="count",
        default=0,
    )

    # Get paginated items
    rows = execute_query(
        f"""
        SELECT id, email, added_by, notes, created_at
        FROM beta_whitelist
        WHERE {time_filter}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
    )

    items = [
        WhitelistDrillDownItem(
            id=str(row["id"]),
            email=row["email"],
            added_by=row["added_by"],
            notes=row["notes"],
            created_at=_to_iso(row["created_at"]),
        )
        for row in rows
    ]

    pagination = make_pagination_fields(total, limit, offset)
    logger.info(f"Admin: Retrieved {len(items)} whitelist entries for period={period.value}")

    return WhitelistDrillDownResponse(
        items=items,
        period=period.value,
        **pagination,
    )
