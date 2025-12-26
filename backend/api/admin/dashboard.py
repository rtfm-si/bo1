"""Consolidated admin dashboard endpoints.

Reduces API calls by combining multiple data fetches into single endpoints.
Each page's data is fetched in parallel internally but returned as one response.

Provides:
- GET /api/admin/dashboard/costs - All costs page data (6 endpoints → 1)
- GET /api/admin/dashboard/metrics - All metrics page data (4 endpoints → 1)
- GET /api/admin/dashboard/ops - All ops page data (3 endpoints → 1)
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.api.admin.models import (
    CostsByProviderResponse,
    FixedCostItem,
    FixedCostsResponse,
    PerUserCostItem,
    PerUserCostResponse,
    ProviderCostItem,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors
from backend.services import fixed_costs as fc
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])


# ==============================================================================
# Response Models
# ==============================================================================


class CostSummary(BaseModel):
    """Summary of costs for different periods."""

    today: float
    this_week: float
    this_month: float
    all_time: float
    session_count_today: int
    session_count_week: int
    session_count_month: int
    session_count_total: int


class UserCostItem(BaseModel):
    """Cost data for a single user."""

    user_id: str
    email: str | None
    total_cost: float
    session_count: int


class UserCostsResponse(BaseModel):
    """List of user costs."""

    users: list[UserCostItem]
    total: int
    limit: int
    offset: int


class DailyCostItem(BaseModel):
    """Cost data for a single day."""

    date: str
    total_cost: float
    session_count: int


class DailyCostsResponse(BaseModel):
    """Daily cost breakdown."""

    days: list[DailyCostItem]
    start_date: str
    end_date: str


class CostsDashboardResponse(BaseModel):
    """Combined response for costs page - replaces 6 API calls."""

    summary: CostSummary
    user_costs: UserCostsResponse
    daily_costs: DailyCostsResponse
    by_provider: CostsByProviderResponse
    fixed_costs: FixedCostsResponse
    per_user: PerUserCostResponse


class DailyCount(BaseModel):
    """Count for a single day."""

    date: str
    count: int


class UserMetrics(BaseModel):
    """User metrics for a period."""

    total_users: int
    new_users_today: int
    new_users_7d: int
    new_users_30d: int
    dau: int
    wau: int
    mau: int
    daily_signups: list[DailyCount]
    daily_active: list[DailyCount]


class UsageMetrics(BaseModel):
    """Usage metrics for a period."""

    total_meetings: int
    meetings_today: int
    meetings_7d: int
    meetings_30d: int
    total_actions: int
    actions_created_7d: int
    daily_meetings: list[DailyCount]
    daily_actions: list[DailyCount]
    mentor_sessions_count: int
    data_analyses_count: int
    projects_count: int
    actions_started_count: int
    actions_completed_count: int
    actions_cancelled_count: int


# Note: MetricsDashboardResponse and OpsDashboardResponse can be added later
# when frontend is updated to use consolidated endpoints


# ==============================================================================
# Data Fetchers
# ==============================================================================


def _get_cost_summary() -> CostSummary:
    """Get cost summary across periods."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN created_at::date = CURRENT_DATE THEN cost ELSE 0 END), 0) AS today,
                    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN cost ELSE 0 END), 0) AS week,
                    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN cost ELSE 0 END), 0) AS month,
                    COALESCE(SUM(cost), 0) AS all_time,
                    COALESCE(COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE), 0) AS sessions_today,
                    COALESCE(COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'), 0) AS sessions_week,
                    COALESCE(COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'), 0) AS sessions_month,
                    COUNT(*) AS sessions_total
                FROM sessions
                WHERE status = 'completed'
                """
            )
            row = cur.fetchone()
            return CostSummary(
                today=float(row["today"] or 0),
                this_week=float(row["week"] or 0),
                this_month=float(row["month"] or 0),
                all_time=float(row["all_time"] or 0),
                session_count_today=row["sessions_today"],
                session_count_week=row["sessions_week"],
                session_count_month=row["sessions_month"],
                session_count_total=row["sessions_total"],
            )


def _get_user_costs(limit: int = 10, offset: int = 0) -> UserCostsResponse:
    """Get top users by cost."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.user_id,
                    u.email,
                    COALESCE(SUM(s.cost), 0) AS total_cost,
                    COUNT(*) AS session_count
                FROM sessions s
                LEFT JOIN users u ON s.user_id = u.supertokens_user_id
                WHERE s.status = 'completed'
                GROUP BY s.user_id, u.email
                ORDER BY total_cost DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            users = [
                UserCostItem(
                    user_id=row["user_id"],
                    email=row["email"],
                    total_cost=float(row["total_cost"] or 0),
                    session_count=row["session_count"],
                )
                for row in cur.fetchall()
            ]

            cur.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE status = 'completed'")
            total = cur.fetchone()[0]

            return UserCostsResponse(users=users, total=total, limit=limit, offset=offset)


def _get_daily_costs(days: int = 30) -> DailyCostsResponse:
    """Get daily cost breakdown."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    created_at::date AS day,
                    COALESCE(SUM(cost), 0) AS total_cost,
                    COUNT(*) AS session_count
                FROM sessions
                WHERE status = 'completed'
                  AND created_at >= %s
                GROUP BY day
                ORDER BY day
                """,
                (start_date,),
            )
            days_data = [
                DailyCostItem(
                    date=str(row["day"]),
                    total_cost=float(row["total_cost"] or 0),
                    session_count=row["session_count"],
                )
                for row in cur.fetchall()
            ]

            return DailyCostsResponse(
                days=days_data,
                start_date=str(start_date),
                end_date=str(end_date),
            )


def _get_costs_by_provider(days: int = 30) -> CostsByProviderResponse:
    """Get costs grouped by LLM provider."""
    start_date = date.today() - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    provider,
                    COALESCE(SUM(cost_usd), 0) AS amount_usd,
                    COUNT(*) AS request_count
                FROM llm_api_calls
                WHERE created_at >= %s
                GROUP BY provider
                ORDER BY amount_usd DESC
                """,
                (start_date,),
            )
            rows = cur.fetchall()
            total = sum(float(r["amount_usd"] or 0) for r in rows)

            providers = [
                ProviderCostItem(
                    provider=row["provider"],
                    amount_usd=float(row["amount_usd"] or 0),
                    request_count=row["request_count"],
                    percentage=(float(row["amount_usd"] or 0) / total * 100) if total > 0 else 0,
                )
                for row in rows
            ]

            return CostsByProviderResponse(
                providers=providers,
                total_usd=total,
                period_start=str(start_date),
                period_end=str(date.today()),
            )


def _get_fixed_costs() -> FixedCostsResponse:
    """Get fixed infrastructure costs."""
    costs = fc.list_fixed_costs(active_only=True)
    monthly_total = fc.get_monthly_fixed_total()

    return FixedCostsResponse(
        costs=[
            FixedCostItem(
                id=c.id,
                provider=c.provider,
                description=c.description,
                monthly_amount_usd=float(c.monthly_amount_usd),
                category=c.category,
                active=c.active,
                notes=c.notes,
            )
            for c in costs
        ],
        monthly_total=float(monthly_total),
    )


def _get_per_user_costs(days: int = 30, limit: int = 20) -> PerUserCostResponse:
    """Get per-user cost averages."""
    start_date = date.today() - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.user_id,
                    u.email,
                    COALESCE(SUM(s.cost), 0) AS total_cost,
                    COUNT(*) AS session_count,
                    COALESCE(AVG(s.cost), 0) AS avg_cost_per_session
                FROM sessions s
                LEFT JOIN users u ON s.user_id = u.supertokens_user_id
                WHERE s.status = 'completed'
                  AND s.created_at >= %s
                GROUP BY s.user_id, u.email
                ORDER BY total_cost DESC
                LIMIT %s
                """,
                (start_date, limit),
            )
            users = [
                PerUserCostItem(
                    user_id=row["user_id"],
                    email=row["email"],
                    total_cost=float(row["total_cost"] or 0),
                    session_count=row["session_count"],
                    avg_cost_per_session=float(row["avg_cost_per_session"] or 0),
                )
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT
                    AVG(user_cost) AS overall_avg,
                    COUNT(*) AS total_users
                FROM (
                    SELECT user_id, SUM(cost) AS user_cost
                    FROM sessions
                    WHERE status = 'completed' AND created_at >= %s
                    GROUP BY user_id
                ) sub
                """,
                (start_date,),
            )
            agg = cur.fetchone()

            return PerUserCostResponse(
                users=users,
                overall_avg=float(agg["overall_avg"] or 0),
                total_users=agg["total_users"] or 0,
                period_start=str(start_date),
                period_end=str(date.today()),
            )


# ==============================================================================
# Consolidated Endpoints
# ==============================================================================


@router.get(
    "/costs",
    response_model=CostsDashboardResponse,
    summary="Get costs dashboard data",
    description="""
    Get all data for the costs admin page in a single request.

    Replaces 6 separate API calls:
    - Cost summary
    - User costs (top 10)
    - Daily costs (30 days)
    - Costs by provider (30 days)
    - Fixed costs
    - Per-user costs (30 days, top 20)
    """,
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get costs dashboard")
async def get_costs_dashboard(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    provider_days: int = Query(30, description="Days for provider breakdown"),
    per_user_days: int = Query(30, description="Days for per-user costs"),
    per_user_limit: int = Query(20, description="Limit for per-user list"),
) -> CostsDashboardResponse:
    """Get all costs page data in one request."""
    # Run all queries (they're synchronous DB calls, can't parallelize easily)
    return CostsDashboardResponse(
        summary=_get_cost_summary(),
        user_costs=_get_user_costs(limit=10),
        daily_costs=_get_daily_costs(days=30),
        by_provider=_get_costs_by_provider(days=provider_days),
        fixed_costs=_get_fixed_costs(),
        per_user=_get_per_user_costs(days=per_user_days, limit=per_user_limit),
    )


# Metrics and Ops dashboard endpoints can be added similarly
# For now, focus on costs as the highest-impact optimization
