"""Admin cost analytics endpoints.

Provides admin-only endpoints for:
- Cost analytics (summary, per-user, daily)
- Cost time series for charts
- Per-user cost tracking and budget settings

All endpoints require admin authentication.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Path, Query

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    CostSummaryResponse,
    DailyCostItem,
    DailyCostsResponse,
    ErrorResponse,
    TopUsersCostResponse,
    UpdateBudgetSettingsRequest,
    UserBudgetSettingsItem,
    UserCostDetailResponse,
    UserCostItem,
    UserCostPeriodItem,
    UserCostsResponse,
)
from backend.api.utils.auth_helpers import require_admin_role
from backend.api.utils.errors import handle_api_errors
from backend.services import analytics
from backend.services import user_cost_tracking as uct

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["admin"])


@router.get(
    "/costs",
    response_model=CostSummaryResponse,
    summary="Get cost summary (admin only)",
    description="Get cost totals for today, this week, this month, and all time.",
    responses={
        200: {"description": "Cost summary retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("get cost summary")
async def get_cost_summary(
    current_user: dict = Depends(get_current_user),
) -> CostSummaryResponse:
    """Get cost summary with totals for different time periods.

    Args:
        current_user: Current authenticated user (for admin check)

    Returns:
        CostSummaryResponse with today, week, month, all_time totals

    Raises:
        HTTPException 403: If user is not an admin
    """
    require_admin_role(current_user)

    summary = analytics.get_cost_summary()

    return CostSummaryResponse(
        today=summary.today,
        this_week=summary.this_week,
        this_month=summary.this_month,
        all_time=summary.all_time,
        session_count_today=summary.session_count_today,
        session_count_week=summary.session_count_week,
        session_count_month=summary.session_count_month,
        session_count_total=summary.session_count_total,
    )


@router.get(
    "/costs/users",
    response_model=UserCostsResponse,
    summary="Get per-user costs (admin only)",
    description="Get cost breakdown by user, sorted by total cost descending.",
    responses={
        200: {"description": "User costs retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("get user costs")
async def get_user_costs(
    current_user: dict = Depends(get_current_user),
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
) -> UserCostsResponse:
    """Get costs aggregated by user.

    Args:
        current_user: Current authenticated user (for admin check)
        start_date: Start of date range (optional)
        end_date: End of date range (optional)
        limit: Max results to return
        offset: Results to skip

    Returns:
        UserCostsResponse with per-user cost breakdown

    Raises:
        HTTPException 403: If user is not an admin
    """
    require_admin_role(current_user)

    users, total = analytics.get_user_costs(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return UserCostsResponse(
        users=[
            UserCostItem(
                user_id=u.user_id,
                email=u.email,
                total_cost=u.total_cost,
                session_count=u.session_count,
            )
            for u in users
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/costs/daily",
    response_model=DailyCostsResponse,
    summary="Get daily costs (admin only)",
    description="Get cost time series by day for a date range.",
    responses={
        200: {"description": "Daily costs retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("get daily costs")
async def get_daily_costs(
    current_user: dict = Depends(get_current_user),
    start_date: date | None = Query(None, description="Start date (default: 30 days ago)"),
    end_date: date | None = Query(None, description="End date (default: today)"),
) -> DailyCostsResponse:
    """Get costs aggregated by day.

    Args:
        current_user: Current authenticated user (for admin check)
        start_date: Start of date range (default: 30 days ago)
        end_date: End of date range (default: today)

    Returns:
        DailyCostsResponse with daily cost time series

    Raises:
        HTTPException 403: If user is not an admin
    """
    require_admin_role(current_user)

    # Default to last 30 days
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    daily = analytics.get_daily_costs(start_date=start_date, end_date=end_date)

    return DailyCostsResponse(
        days=[
            DailyCostItem(
                date=d.date.isoformat(),
                total_cost=d.total_cost,
                session_count=d.session_count,
            )
            for d in daily
        ],
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )


# =============================================================================
# Per-User Cost Tracking (Admin Only)
# =============================================================================


def _period_to_item(p: uct.UserCostPeriod) -> UserCostPeriodItem:
    """Convert service dataclass to response model."""
    return UserCostPeriodItem(
        user_id=p.user_id,
        period_start=p.period_start.isoformat(),
        period_end=p.period_end.isoformat(),
        total_cost_cents=p.total_cost_cents,
        session_count=p.session_count,
    )


def _settings_to_item(s: uct.UserBudgetSettings) -> UserBudgetSettingsItem:
    """Convert service dataclass to response model."""
    return UserBudgetSettingsItem(
        user_id=s.user_id,
        monthly_cost_limit_cents=s.monthly_cost_limit_cents,
        alert_threshold_pct=s.alert_threshold_pct,
        hard_limit_enabled=s.hard_limit_enabled,
    )


@router.get(
    "/costs/top-users",
    response_model=TopUsersCostResponse,
    summary="Get top users by cost (admin only)",
    description="Get users ranked by cost for abuse detection.",
    responses={
        200: {"description": "Top users retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("get top users by cost")
async def get_top_users_by_cost(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100, description="Max users to return"),
) -> TopUsersCostResponse:
    """Get users ranked by cost for the current period.

    Args:
        current_user: Current authenticated user (for admin check)
        limit: Max users to return

    Returns:
        TopUsersCostResponse with users sorted by cost descending
    """
    require_admin_role(current_user)

    period_start, _ = uct.get_current_period_bounds()
    users = uct.get_top_users_by_cost(limit=limit)

    return TopUsersCostResponse(
        period_start=period_start.isoformat(),
        users=[_period_to_item(u) for u in users],
    )


@router.get(
    "/users/{user_id}/costs",
    response_model=UserCostDetailResponse,
    summary="Get user cost details (admin only)",
    description="Get detailed cost info for a specific user.",
    responses={
        200: {"description": "User costs retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("get user costs")
async def get_user_cost_detail(
    user_id: str = Path(..., description="User ID"),
    current_user: dict = Depends(get_current_user),
    history_months: int = Query(6, ge=1, le=24, description="Months of history"),
) -> UserCostDetailResponse:
    """Get detailed cost info for a user including history and settings.

    Args:
        user_id: User ID to query
        current_user: Current authenticated user (for admin check)
        history_months: Number of months of history to include

    Returns:
        UserCostDetailResponse with current period, settings, and history
    """
    require_admin_role(current_user)

    # Get email from users table
    from bo1.state.database import db_session

    email = None
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                email = row["email"]

    current = uct.get_user_period_cost(user_id)
    settings = uct.get_user_budget_settings(user_id)
    history = uct.get_user_cost_history(user_id, months=history_months)

    return UserCostDetailResponse(
        user_id=user_id,
        email=email,
        current_period=_period_to_item(current) if current else None,
        budget_settings=_settings_to_item(settings) if settings else None,
        history=[_period_to_item(p) for p in history],
    )


@router.patch(
    "/users/{user_id}/budget",
    response_model=UserBudgetSettingsItem,
    summary="Update user budget settings (admin only)",
    description="Set cost limits and alert thresholds for a user.",
    responses={
        200: {"description": "Budget settings updated successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
)
@handle_api_errors("update user budget settings")
async def update_user_budget_settings(
    user_id: str = Path(..., description="User ID"),
    request: UpdateBudgetSettingsRequest = ...,
    current_user: dict = Depends(get_current_user),
) -> UserBudgetSettingsItem:
    """Update budget settings for a user.

    Args:
        user_id: User ID to update
        request: Budget settings to update
        current_user: Current authenticated user (for admin check)

    Returns:
        Updated UserBudgetSettingsItem
    """
    require_admin_role(current_user)

    settings = uct.set_user_budget_settings(
        user_id=user_id,
        monthly_cost_limit_cents=request.monthly_cost_limit_cents,
        alert_threshold_pct=request.alert_threshold_pct,
        hard_limit_enabled=request.hard_limit_enabled,
    )

    logger.info(
        "Admin updated user budget settings",
        extra={
            "admin_user_id": current_user.get("user_id"),
            "target_user_id": user_id,
            "settings": {
                "limit_cents": settings.monthly_cost_limit_cents,
                "threshold_pct": settings.alert_threshold_pct,
                "hard_limit": settings.hard_limit_enabled,
            },
        },
    )

    return _settings_to_item(settings)
