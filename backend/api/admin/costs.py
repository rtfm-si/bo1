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

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.api.admin.models import (
    CostsByProviderResponse,
    CreateFixedCostRequest,
    DailySummaryItem,
    DailySummaryResponse,
    FixedCostItem,
    FixedCostsResponse,
    MeetingCostResponse,
    PerUserCostItem,
    PerUserCostResponse,
    ProviderCostItem,
    UpdateFixedCostRequest,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.utils.errors import handle_api_errors
from backend.services import fixed_costs as fc
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
@handle_api_errors("list fixed costs")
async def list_fixed_costs(
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
@handle_api_errors("create fixed cost")
async def create_fixed_cost(
    request: CreateFixedCostRequest,
    _admin: dict = Depends(require_admin_any),
) -> FixedCostItem:
    """Create a fixed cost entry."""
    cost = fc.create_fixed_cost(
        provider=request.provider,
        description=request.description,
        monthly_amount_usd=Decimal(str(request.monthly_amount_usd)),
        category=request.category,
        notes=request.notes,
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
@handle_api_errors("update fixed cost")
async def update_fixed_cost(
    cost_id: int = Path(..., description="Fixed cost ID"),
    request: UpdateFixedCostRequest = ...,
    _admin: dict = Depends(require_admin_any),
) -> FixedCostItem:
    """Update a fixed cost entry."""
    cost = fc.update_fixed_cost(
        cost_id=cost_id,
        monthly_amount_usd=Decimal(str(request.monthly_amount_usd))
        if request.monthly_amount_usd is not None
        else None,
        active=request.active,
        notes=request.notes,
    )

    if not cost:
        raise HTTPException(status_code=404, detail="Fixed cost not found")

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
@handle_api_errors("delete fixed cost")
async def delete_fixed_cost(
    cost_id: int = Path(..., description="Fixed cost ID"),
    _admin: dict = Depends(require_admin_any),
) -> dict:
    """Delete (deactivate) a fixed cost."""
    deleted = fc.delete_fixed_cost(cost_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Fixed cost not found")
    return {"deleted": True, "cost_id": cost_id}


@router.post(
    "/fixed/seed",
    response_model=FixedCostsResponse,
    summary="Seed default fixed costs",
    description="Create default fixed cost entries if none exist (admin only).",
)
@handle_api_errors("seed fixed costs")
async def seed_fixed_costs(
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
@handle_api_errors("get costs by provider")
async def get_costs_by_provider(
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
@handle_api_errors("get meeting costs")
async def get_meeting_costs(
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
@handle_api_errors("get per-user costs")
async def get_per_user_costs(
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
                LEFT JOIN users u ON ac.user_id = u.user_id
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
@handle_api_errors("get daily summary")
async def get_daily_summary(
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
