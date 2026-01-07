"""Admin cost tracking endpoints.

Provides:
- Fixed costs CRUD
- Cost breakdown by provider
- Meeting cost attribution
- Per-user cost averages
- Daily cost summaries
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.api.admin.models import (
    AggregatedCacheMetrics,
    CacheTypeMetrics,
    CategoryCostAggregation,
    CostAggregationsResponse,
    CostsByProviderResponse,
    CreateFixedCostRequest,
    DailyResearchCost,
    DailySummaryItem,
    DailySummaryResponse,
    FeatureCostBreakdown,
    FeatureCostBreakdownResponse,
    FeatureCostItem,
    FixedCostItem,
    FixedCostsResponse,
    HeavyUserItem,
    HeavyUsersResponse,
    InternalCostItem,
    InternalCostsByPeriod,
    InternalCostsResponse,
    MeetingCostResponse,
    PerUserCostItem,
    PerUserCostResponse,
    ProviderCostItem,
    ResearchCostItem,
    ResearchCostsByPeriod,
    ResearchCostsResponse,
    UnifiedCacheMetricsResponse,
    UpdateFixedCostRequest,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services import fixed_costs as fc
from bo1.logging import ErrorCode
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/costs", tags=["admin-costs"])


# ==============================================================================
# Fixed Costs CRUD
# ==============================================================================


@router.get(
    "/fixed",
    response_model=FixedCostsResponse,
    summary="List fixed costs",
    description="Get all fixed infrastructure costs (admin only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("list fixed costs")
async def list_fixed_costs(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    include_inactive: bool = Query(False, description="Include inactive costs"),
) -> FixedCostsResponse:
    """List all fixed costs."""
    costs = fc.list_fixed_costs(active_only=not include_inactive)
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


@router.post(
    "/fixed",
    response_model=FixedCostItem,
    summary="Create fixed cost",
    description="Add a new fixed infrastructure cost (admin only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("create fixed cost")
async def create_fixed_cost(
    request: Request,
    body: CreateFixedCostRequest,
    _admin: dict = Depends(require_admin_any),
) -> FixedCostItem:
    """Create a fixed cost entry."""
    cost = fc.create_fixed_cost(
        provider=body.provider,
        description=body.description,
        monthly_amount_usd=Decimal(str(body.monthly_amount_usd)),
        category=body.category,
        notes=body.notes,
    )

    return FixedCostItem(
        id=cost.id,
        provider=cost.provider,
        description=cost.description,
        monthly_amount_usd=float(cost.monthly_amount_usd),
        category=cost.category,
        active=cost.active,
        notes=cost.notes,
    )


@router.patch(
    "/fixed/{cost_id}",
    response_model=FixedCostItem,
    summary="Update fixed cost",
    description="Update a fixed cost entry (admin only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("update fixed cost")
async def update_fixed_cost(
    request: Request,
    cost_id: int = Path(..., description="Fixed cost ID"),
    body: UpdateFixedCostRequest = ...,
    _admin: dict = Depends(require_admin_any),
) -> FixedCostItem:
    """Update a fixed cost entry."""
    cost = fc.update_fixed_cost(
        cost_id=cost_id,
        monthly_amount_usd=Decimal(str(body.monthly_amount_usd))
        if body.monthly_amount_usd is not None
        else None,
        active=body.active,
        notes=body.notes,
    )

    if not cost:
        raise http_error(ErrorCode.API_NOT_FOUND, "Fixed cost not found", status=404)

    return FixedCostItem(
        id=cost.id,
        provider=cost.provider,
        description=cost.description,
        monthly_amount_usd=float(cost.monthly_amount_usd),
        category=cost.category,
        active=cost.active,
        notes=cost.notes,
    )


@router.delete(
    "/fixed/{cost_id}",
    summary="Delete fixed cost",
    description="Soft delete a fixed cost (admin only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("delete fixed cost")
async def delete_fixed_cost(
    request: Request,
    cost_id: int = Path(..., description="Fixed cost ID"),
    _admin: dict = Depends(require_admin_any),
) -> dict:
    """Delete (deactivate) a fixed cost."""
    deleted = fc.delete_fixed_cost(cost_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Fixed cost not found", status=404)
    return {"deleted": True, "cost_id": cost_id}


@router.post(
    "/fixed/seed",
    response_model=FixedCostsResponse,
    summary="Seed default fixed costs",
    description="Create default fixed cost entries if none exist (admin only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("seed fixed costs")
async def seed_fixed_costs(
    request: Request,
    _admin: dict = Depends(require_admin_any),
) -> FixedCostsResponse:
    """Seed default fixed costs."""
    fc.seed_default_fixed_costs()
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


# ==============================================================================
# Cost Analytics
# ==============================================================================


@router.get(
    "/by-provider",
    response_model=CostsByProviderResponse,
    summary="Costs by provider",
    description="Get cost breakdown by provider for the last 30 days.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get costs by provider")
async def get_costs_by_provider(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> CostsByProviderResponse:
    """Get cost breakdown by provider."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    provider,
                    COALESCE(SUM(total_cost), 0) as amount,
                    COUNT(*) as request_count
                FROM api_costs
                WHERE created_at >= %s AND created_at < %s + INTERVAL '1 day'
                GROUP BY provider
                ORDER BY amount DESC
                """,
                (start_date, end_date),
            )
            rows = cur.fetchall()

    total = sum(float(r["amount"]) for r in rows)
    providers = [
        ProviderCostItem(
            provider=r["provider"],
            amount_usd=float(r["amount"]),
            request_count=r["request_count"],
            percentage=round(float(r["amount"]) / total * 100, 1) if total > 0 else 0,
        )
        for r in rows
    ]

    return CostsByProviderResponse(
        providers=providers,
        total_usd=total,
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
    )


@router.get(
    "/by-meeting/{session_id}",
    response_model=MeetingCostResponse,
    summary="Meeting costs",
    description="Get total cost breakdown for a specific meeting/session.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get meeting costs")
async def get_meeting_costs(
    request: Request,
    session_id: str = Path(..., description="Session ID"),
    _admin: dict = Depends(require_admin_any),
) -> MeetingCostResponse:
    """Get cost breakdown for a meeting."""
    with db_session() as conn:
        with conn.cursor() as cur:
            # partition: api_costs - Include created_at filter for partition pruning
            # Sessions typically complete within 7 days; use 30 days for safety margin
            # Total and API calls
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(*) as api_calls
                FROM api_costs
                WHERE session_id = %s
                  AND created_at >= NOW() - INTERVAL '30 days'
                """,
                (session_id,),
            )
            totals = cur.fetchone()

            # By provider
            cur.execute(
                """
                SELECT provider, COALESCE(SUM(total_cost), 0) as amount
                FROM api_costs
                WHERE session_id = %s
                  AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY provider
                """,
                (session_id,),
            )
            by_provider = {r["provider"]: float(r["amount"]) for r in cur.fetchall()}

            # By phase
            cur.execute(
                """
                SELECT COALESCE(phase, 'other') as phase, COALESCE(SUM(total_cost), 0) as amount
                FROM api_costs
                WHERE session_id = %s
                  AND created_at >= NOW() - INTERVAL '30 days'
                GROUP BY phase
                """,
                (session_id,),
            )
            by_phase = {r["phase"]: float(r["amount"]) for r in cur.fetchall()}

    return MeetingCostResponse(
        session_id=session_id,
        total_cost=float(totals["total_cost"]),
        api_calls=totals["api_calls"],
        by_provider=by_provider,
        by_phase=by_phase,
    )


@router.get(
    "/per-user",
    response_model=PerUserCostResponse,
    summary="Average cost per user",
    description="Get cost metrics per active user.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get per-user costs")
async def get_per_user_costs(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(50, ge=1, le=200, description="Max users to return"),
) -> PerUserCostResponse:
    """Get average cost per user."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ac.user_id,
                    u.email,
                    COALESCE(SUM(ac.total_cost), 0) as total_cost,
                    COUNT(DISTINCT ac.session_id) as session_count
                FROM api_costs ac
                LEFT JOIN users u ON ac.user_id = u.id
                WHERE ac.created_at >= %s AND ac.created_at < %s + INTERVAL '1 day'
                  AND ac.user_id IS NOT NULL
                GROUP BY ac.user_id, u.email
                ORDER BY total_cost DESC
                LIMIT %s
                """,
                (start_date, end_date, limit),
            )
            rows = cur.fetchall()

    users = [
        PerUserCostItem(
            user_id=r["user_id"],
            email=r["email"],
            total_cost=float(r["total_cost"]),
            session_count=r["session_count"],
            avg_cost_per_session=float(r["total_cost"]) / r["session_count"]
            if r["session_count"] > 0
            else 0,
        )
        for r in rows
    ]

    total_cost = sum(u.total_cost for u in users)
    overall_avg = total_cost / len(users) if users else 0

    return PerUserCostResponse(
        users=users,
        overall_avg=overall_avg,
        total_users=len(users),
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
    )


@router.get(
    "/daily-summary",
    response_model=DailySummaryResponse,
    summary="Daily cost summary",
    description="Get aggregated daily cost totals.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get daily summary")
async def get_daily_summary(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> DailySummaryResponse:
    """Get daily cost summaries."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Try pre-aggregated table first
            cur.execute(
                """
                SELECT
                    date,
                    provider,
                    amount_usd,
                    request_count
                FROM daily_cost_summary
                WHERE date >= %s AND date <= %s
                ORDER BY date
                """,
                (start_date, end_date),
            )
            rows = cur.fetchall()

            # If no pre-aggregated data, query api_costs directly
            if not rows:
                cur.execute(
                    """
                    SELECT
                        DATE(created_at) as date,
                        provider,
                        COALESCE(SUM(total_cost), 0) as amount_usd,
                        COUNT(*) as request_count
                    FROM api_costs
                    WHERE created_at >= %s AND created_at < %s + INTERVAL '1 day'
                    GROUP BY DATE(created_at), provider
                    ORDER BY date
                    """,
                    (start_date, end_date),
                )
                rows = cur.fetchall()

    # Group by date
    days_data: dict[str, DailySummaryItem] = {}
    for row in rows:
        date_str = (
            row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"])
        )
        if date_str not in days_data:
            days_data[date_str] = DailySummaryItem(
                date=date_str,
                total_usd=0,
                by_provider={},
                request_count=0,
            )
        days_data[date_str].total_usd += float(row["amount_usd"])
        days_data[date_str].by_provider[row["provider"]] = float(row["amount_usd"])
        days_data[date_str].request_count += row["request_count"]

    return DailySummaryResponse(
        days=list(days_data.values()),
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
    )


# ==============================================================================
# Unified Cache Metrics
# ==============================================================================


@router.get(
    "/cache-metrics",
    response_model=UnifiedCacheMetricsResponse,
    summary="Unified cache metrics",
    description="Get aggregated cache metrics across prompt, research, and LLM caches.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get cache metrics")
async def get_cache_metrics(
    request: Request,
    _admin: dict = Depends(require_admin_any),
) -> UnifiedCacheMetricsResponse:
    """Get unified cache metrics from all cache systems."""
    from bo1.llm.cost_tracker import CostTracker

    metrics = CostTracker.get_cache_metrics()

    return UnifiedCacheMetricsResponse(
        prompt=CacheTypeMetrics(**metrics["prompt"]),
        research=CacheTypeMetrics(**metrics["research"]),
        llm=CacheTypeMetrics(**metrics["llm"]),
        aggregate=AggregatedCacheMetrics(**metrics["aggregate"]),
    )


# ==============================================================================
# Research Costs (Brave + Tavily)
# ==============================================================================


@router.get(
    "/research",
    response_model=ResearchCostsResponse,
    summary="Research costs",
    description="Get Brave and Tavily research API costs breakdown.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get research costs")
async def get_research_costs(
    request: Request,
    _admin: dict = Depends(require_admin_any),
) -> ResearchCostsResponse:
    """Get research costs for Brave and Tavily."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    with db_session() as conn:
        with conn.cursor() as cur:
            # All-time totals by provider
            cur.execute(
                """
                SELECT
                    provider,
                    COALESCE(SUM(total_cost), 0) as amount,
                    COUNT(*) as query_count
                FROM api_costs
                WHERE provider IN ('brave', 'tavily')
                  AND created_at >= NOW() - INTERVAL '365 days'
                GROUP BY provider
                """
            )
            provider_totals = {r["provider"]: r for r in cur.fetchall()}

            # Time-period breakdown (total)
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN DATE(created_at) = %s THEN total_cost ELSE 0 END), 0) as today,
                    COALESCE(SUM(CASE WHEN created_at >= %s THEN total_cost ELSE 0 END), 0) as week,
                    COALESCE(SUM(CASE WHEN created_at >= %s THEN total_cost ELSE 0 END), 0) as month,
                    COALESCE(SUM(total_cost), 0) as all_time
                FROM api_costs
                WHERE provider IN ('brave', 'tavily')
                  AND created_at >= NOW() - INTERVAL '365 days'
                """,
                (today, week_ago, month_ago),
            )
            period_row = cur.fetchone()

            # Daily breakdown for trend (last 7 days)
            cur.execute(
                """
                SELECT
                    DATE(created_at) as day,
                    provider,
                    COALESCE(SUM(total_cost), 0) as amount
                FROM api_costs
                WHERE provider IN ('brave', 'tavily')
                  AND created_at >= %s
                GROUP BY DATE(created_at), provider
                ORDER BY day
                """,
                (week_ago,),
            )
            daily_rows = cur.fetchall()

    # Build provider items
    brave_data = provider_totals.get("brave", {"amount": 0, "query_count": 0})
    tavily_data = provider_totals.get("tavily", {"amount": 0, "query_count": 0})

    brave = ResearchCostItem(
        provider="brave",
        amount_usd=float(brave_data["amount"]),
        query_count=brave_data["query_count"],
    )
    tavily = ResearchCostItem(
        provider="tavily",
        amount_usd=float(tavily_data["amount"]),
        query_count=tavily_data["query_count"],
    )

    # Build period breakdown
    by_period = ResearchCostsByPeriod(
        today=float(period_row["today"]),
        week=float(period_row["week"]),
        month=float(period_row["month"]),
        all_time=float(period_row["all_time"]),
    )

    # Build daily trend
    daily_dict: dict[str, DailyResearchCost] = {}
    # Initialize all 7 days
    for i in range(7):
        day = (week_ago + timedelta(days=i)).isoformat()
        daily_dict[day] = DailyResearchCost(date=day, brave=0.0, tavily=0.0, total=0.0)

    for row in daily_rows:
        day_str = row["day"].isoformat() if hasattr(row["day"], "isoformat") else str(row["day"])
        if day_str in daily_dict:
            if row["provider"] == "brave":
                daily_dict[day_str].brave = float(row["amount"])
            elif row["provider"] == "tavily":
                daily_dict[day_str].tavily = float(row["amount"])
            daily_dict[day_str].total = daily_dict[day_str].brave + daily_dict[day_str].tavily

    daily_trend = list(daily_dict.values())

    return ResearchCostsResponse(
        brave=brave,
        tavily=tavily,
        total_usd=brave.amount_usd + tavily.amount_usd,
        total_queries=brave.query_count + tavily.query_count,
        by_period=by_period,
        daily_trend=daily_trend,
    )


# ==============================================================================
# Fair Usage Analytics
# ==============================================================================


@router.get(
    "/fair-usage/heavy-users",
    response_model=HeavyUsersResponse,
    summary="Heavy users list",
    description="Get users exceeding p90 cost threshold for LLM features.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get heavy users")
async def get_heavy_users(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    feature: str | None = Query(None, description="Filter by feature name"),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    limit: int = Query(50, ge=1, le=200, description="Max users to return"),
) -> HeavyUsersResponse:
    """Get users exceeding p90 cost threshold."""
    from backend.services.fair_usage import get_fair_usage_service

    service = get_fair_usage_service()
    heavy_users = service.get_heavy_users(feature=feature, days=days, limit=limit)

    return HeavyUsersResponse(
        heavy_users=[
            HeavyUserItem(
                user_id=u.user_id,
                email=u.email,
                feature=u.feature,
                total_cost_7d=u.total_cost_7d,
                avg_daily_cost=u.avg_daily_cost,
                p90_threshold=u.p90_threshold,
                exceeds_p90_by=u.exceeds_p90_by,
            )
            for u in heavy_users
        ],
        total=len(heavy_users),
        period_days=days,
    )


@router.get(
    "/fair-usage/by-feature",
    response_model=FeatureCostBreakdownResponse,
    summary="Cost breakdown by feature",
    description="Get cost breakdown by feature for fair usage analysis.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feature cost breakdown")
async def get_feature_cost_breakdown(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
) -> FeatureCostBreakdownResponse:
    """Get cost breakdown by feature."""
    from backend.services.fair_usage import get_fair_usage_service

    service = get_fair_usage_service()
    breakdown = service.get_feature_cost_breakdown(days=days)

    features = [
        FeatureCostBreakdown(
            feature=feature,
            total_cost=stats["total_cost"],
            user_count=stats["user_count"],
            avg_per_user=stats["avg_per_user"],
            p90_daily=stats["p90_daily"],
        )
        for feature, stats in breakdown.items()
    ]

    total_cost = sum(f.total_cost for f in features)

    return FeatureCostBreakdownResponse(
        features=features,
        period_days=days,
        total_cost=total_cost,
    )


# ==============================================================================
# Cost Aggregations
# ==============================================================================


@router.get(
    "/aggregations",
    response_model=CostAggregationsResponse,
    summary="Cost aggregations",
    description="Get total/avg per meeting/avg per user breakdowns for each cost category.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get cost aggregations")
async def get_cost_aggregations(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
) -> CostAggregationsResponse:
    """Get cost aggregations by category with per-meeting and per-user averages."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Get costs by provider (category)
            cur.execute(
                """
                SELECT
                    provider,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(DISTINCT session_id) as session_count
                FROM api_costs
                WHERE created_at >= %s AND created_at < %s + INTERVAL '1 day'
                GROUP BY provider
                ORDER BY total_cost DESC
                """,
                (start_date, end_date),
            )
            provider_rows = cur.fetchall()

            # Get unique session count for the period
            cur.execute(
                """
                SELECT COUNT(DISTINCT session_id) as session_count
                FROM api_costs
                WHERE created_at >= %s AND created_at < %s + INTERVAL '1 day'
                  AND session_id IS NOT NULL
                """,
                (start_date, end_date),
            )
            total_sessions = cur.fetchone()["session_count"]

            # Get paying users count
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM users
                WHERE subscription_tier IN ('starter', 'pro', 'enterprise')
                """
            )
            paying_users = cur.fetchone()["count"]

    # Build category aggregations
    categories: list[CategoryCostAggregation] = []
    total_cost = 0.0

    for row in provider_rows:
        cost = float(row["total_cost"])
        session_count = row["session_count"] or 0
        total_cost += cost

        categories.append(
            CategoryCostAggregation(
                category=row["provider"],
                total_cost=cost,
                avg_per_session=cost / session_count if session_count > 0 else None,
                avg_per_user=cost / paying_users if paying_users > 0 else None,
                session_count=session_count,
                user_count=paying_users,
            )
        )

    # Build overall aggregation
    overall = CategoryCostAggregation(
        category="total",
        total_cost=total_cost,
        avg_per_session=total_cost / total_sessions if total_sessions > 0 else None,
        avg_per_user=total_cost / paying_users if paying_users > 0 else None,
        session_count=total_sessions,
        user_count=paying_users,
    )

    return CostAggregationsResponse(
        categories=categories,
        overall=overall,
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
    )


# ==============================================================================
# Paying Users Count
# ==============================================================================


@router.get(
    "/paying-users-count",
    summary="Count paying users",
    description="Get count of users with paid subscription tiers (starter, pro, enterprise).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get paying users count")
async def get_paying_users_count(
    request: Request,
    _admin: dict = Depends(require_admin_any),
) -> dict:
    """Get count of paying users."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM users
                WHERE subscription_tier IN ('starter', 'pro', 'enterprise')
                """
            )
            row = cur.fetchone()

    return {"paying_users_count": row["count"] if row else 0}


# ==============================================================================
# Internal Costs (Non-User)
# ==============================================================================


@router.get(
    "/internal",
    response_model=InternalCostsResponse,
    summary="Internal costs",
    description="Get costs for internal operations (SEO, system jobs) separate from user costs.",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get internal costs")
async def get_internal_costs(
    request: Request,
    _admin: dict = Depends(require_admin_any),
) -> InternalCostsResponse:
    """Get costs for internal (non-user) operations."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Get SEO costs breakdown by prompt_type
            cur.execute(
                """
                SELECT
                    provider,
                    metadata->>'prompt_type' as prompt_type,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens
                FROM api_costs
                WHERE cost_category = 'internal_seo'
                GROUP BY provider, metadata->>'prompt_type'
                ORDER BY total_cost DESC
                """
            )
            seo_rows = cur.fetchall()

            # Get system costs breakdown
            cur.execute(
                """
                SELECT
                    provider,
                    metadata->>'prompt_type' as prompt_type,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens
                FROM api_costs
                WHERE cost_category = 'internal_system'
                GROUP BY provider, metadata->>'prompt_type'
                ORDER BY total_cost DESC
                """
            )
            system_rows = cur.fetchall()

            # Get data analysis (dataset_qa) costs by feature
            cur.execute(
                """
                SELECT
                    feature,
                    provider,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COUNT(DISTINCT user_id) as user_count
                FROM api_costs
                WHERE feature = 'dataset_qa'
                GROUP BY feature, provider
                ORDER BY total_cost DESC
                """
            )
            data_analysis_rows = cur.fetchall()

            # Get mentor chat costs by feature
            cur.execute(
                """
                SELECT
                    feature,
                    provider,
                    COALESCE(SUM(total_cost), 0) as total_cost,
                    COUNT(*) as request_count,
                    COALESCE(SUM(input_tokens), 0) as input_tokens,
                    COALESCE(SUM(output_tokens), 0) as output_tokens,
                    COUNT(DISTINCT user_id) as user_count
                FROM api_costs
                WHERE feature = 'mentor_chat'
                GROUP BY feature, provider
                ORDER BY total_cost DESC
                """
            )
            mentor_rows = cur.fetchall()

            # Get period breakdown for all internal costs (includes feature costs)
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN created_at >= %s THEN total_cost ELSE 0 END), 0) as today,
                    COALESCE(SUM(CASE WHEN created_at >= %s THEN total_cost ELSE 0 END), 0) as week,
                    COALESCE(SUM(CASE WHEN created_at >= %s THEN total_cost ELSE 0 END), 0) as month,
                    COALESCE(SUM(total_cost), 0) as all_time,
                    COUNT(*) as total_requests
                FROM api_costs
                WHERE cost_category IN ('internal_seo', 'internal_system')
                   OR feature IN ('dataset_qa', 'mentor_chat')
                """,
                (today, week_ago, month_ago),
            )
            period_row = cur.fetchone()

    seo = [
        InternalCostItem(
            provider=r["provider"],
            prompt_type=r["prompt_type"],
            total_cost=float(r["total_cost"]),
            request_count=r["request_count"],
            input_tokens=r["input_tokens"],
            output_tokens=r["output_tokens"],
        )
        for r in seo_rows
    ]

    system = [
        InternalCostItem(
            provider=r["provider"],
            prompt_type=r["prompt_type"],
            total_cost=float(r["total_cost"]),
            request_count=r["request_count"],
            input_tokens=r["input_tokens"],
            output_tokens=r["output_tokens"],
        )
        for r in system_rows
    ]

    data_analysis = [
        FeatureCostItem(
            feature=r["feature"],
            provider=r["provider"],
            total_cost=float(r["total_cost"]),
            request_count=r["request_count"],
            input_tokens=r["input_tokens"],
            output_tokens=r["output_tokens"],
            user_count=r["user_count"],
        )
        for r in data_analysis_rows
    ]

    mentor_chat = [
        FeatureCostItem(
            feature=r["feature"],
            provider=r["provider"],
            total_cost=float(r["total_cost"]),
            request_count=r["request_count"],
            input_tokens=r["input_tokens"],
            output_tokens=r["output_tokens"],
            user_count=r["user_count"],
        )
        for r in mentor_rows
    ]

    by_period = InternalCostsByPeriod(
        today=float(period_row["today"]),
        week=float(period_row["week"]),
        month=float(period_row["month"]),
        all_time=float(period_row["all_time"]),
    )

    total_cost = (
        sum(item.total_cost for item in seo)
        + sum(item.total_cost for item in system)
        + sum(item.total_cost for item in data_analysis)
        + sum(item.total_cost for item in mentor_chat)
    )
    total_requests = period_row["total_requests"] if period_row else 0

    return InternalCostsResponse(
        seo=seo,
        system=system,
        data_analysis=data_analysis,
        mentor_chat=mentor_chat,
        by_period=by_period,
        total_usd=total_cost,
        total_requests=total_requests,
    )
