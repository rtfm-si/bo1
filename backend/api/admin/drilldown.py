"""Admin API endpoints for drill-down views.

Provides paginated list views with time-period filtering for:
- Users (registered in period)
- Costs (incurred in period)
- Waitlist (added in period)
- Whitelist (added in period)
- Cache effectiveness insights
- Model impact analysis
- Feature efficiency metrics

All endpoints:
- Require admin authentication
- Support time periods: hour, day, week, month, all
- Support pagination via limit/offset
"""

from fastapi import APIRouter, Depends, Query, Request

from backend.api.admin.models import (
    CacheEffectivenessBucket,
    CacheEffectivenessResponse,
    CostDrillDownItem,
    CostDrillDownResponse,
    FeatureEfficiencyItem,
    FeatureEfficiencyResponse,
    ModelImpactItem,
    ModelImpactResponse,
    QualityIndicatorsResponse,
    TimePeriod,
    TuningRecommendation,
    TuningRecommendationsResponse,
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


def _to_iso(value: object) -> str:
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
        f"SELECT COUNT(*) FROM users WHERE {time_filter}",  # nosec B608 - time_filter from validated enum
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
        """,  # nosec B608 - time_filter from validated enum
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
        f"SELECT COUNT(*) as count, COALESCE(SUM(total_cost), 0) as total FROM api_costs WHERE {time_filter}",  # nosec B608
        (),
        fetch="one",
    )
    total = stats["count"] if stats else 0
    total_cost = float(stats["total"]) if stats else 0.0

    # Get paginated items with user email join
    rows = execute_query(
        f"""
        SELECT c.id, c.user_id, u.email, c.provider, c.model_name, c.total_cost, c.created_at
        FROM api_costs c
        LEFT JOIN users u ON c.user_id = u.id
        WHERE {time_filter.replace("created_at", "c.created_at")}
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
        """,  # nosec B608
        (limit, offset),
    )

    items = [
        CostDrillDownItem(
            id=row["id"],
            user_id=row["user_id"] or "unknown",
            email=row["email"],
            provider=row["provider"],
            model=row["model_name"],
            amount_usd=float(row["total_cost"]) if row["total_cost"] else 0.0,
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
        f"SELECT COUNT(*) FROM waitlist WHERE {time_filter}",  # nosec B608
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
        """,  # nosec B608
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
        f"SELECT COUNT(*) FROM beta_whitelist WHERE {time_filter}",  # nosec B608
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
        """,  # nosec B608
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


# ==============================================================================
# Insight Drill-Down Endpoints
# ==============================================================================


@router.get(
    "/cache-effectiveness",
    response_model=CacheEffectivenessResponse,
    summary="Cache effectiveness drill-down",
    description="Group sessions by cache hit rate buckets with cost analysis.",
    responses={
        200: {"description": "Cache effectiveness data retrieved"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get cache effectiveness drill-down")
async def get_cache_effectiveness(
    request: Request,
    period: TimePeriod = Query(TimePeriod.WEEK, description="Time period filter"),
    _admin: str = Depends(require_admin_any),
) -> CacheEffectivenessResponse:
    """Get cache effectiveness grouped by hit rate buckets."""
    time_filter = _get_time_filter(period)

    # Get session-level cache stats
    rows = execute_query(
        f"""
        WITH session_stats AS (
            SELECT
                session_id,
                COUNT(*) as request_count,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                SUM(total_cost) as total_cost,
                SUM(COALESCE(cost_without_optimization, total_cost) - total_cost) as savings
            FROM api_costs
            WHERE session_id IS NOT NULL
              AND {time_filter}
            GROUP BY session_id
        )
        SELECT
            CASE
                WHEN cache_hits::float / NULLIF(request_count, 0) < 0.25 THEN 1
                WHEN cache_hits::float / NULLIF(request_count, 0) < 0.50 THEN 2
                WHEN cache_hits::float / NULLIF(request_count, 0) < 0.75 THEN 3
                ELSE 4
            END as bucket,
            COUNT(*) as session_count,
            AVG(total_cost) as avg_cost,
            SUM(total_cost) as total_cost,
            SUM(savings) as total_saved,
            AVG(savings) as avg_savings,
            SUM(cache_hits)::float / NULLIF(SUM(request_count), 0) as bucket_hit_rate
        FROM session_stats
        GROUP BY bucket
        ORDER BY bucket
        """,  # nosec B608
        (),
    )

    # Build bucket responses
    bucket_labels = {
        1: ("0-25%", 0.0, 0.25),
        2: ("25-50%", 0.25, 0.50),
        3: ("50-75%", 0.50, 0.75),
        4: ("75-100%", 0.75, 1.0),
    }

    buckets = []
    total_sessions = 0
    total_cost = 0.0
    total_saved = 0.0

    for row in rows:
        bucket_num = row["bucket"]
        label, b_min, b_max = bucket_labels.get(bucket_num, ("Unknown", 0.0, 1.0))
        session_count = row["session_count"] or 0
        total_sessions += session_count
        bucket_cost = float(row["total_cost"] or 0)
        bucket_saved = float(row["total_saved"] or 0)
        total_cost += bucket_cost
        total_saved += bucket_saved

        buckets.append(
            CacheEffectivenessBucket(
                bucket_label=label,
                bucket_min=b_min,
                bucket_max=b_max,
                session_count=session_count,
                avg_cost=float(row["avg_cost"] or 0),
                total_cost=bucket_cost,
                total_saved=bucket_saved,
                avg_optimization_savings=float(row["avg_savings"] or 0),
            )
        )

    # Get overall hit rate
    overall_stats = execute_query(
        f"""
        SELECT
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as hit_rate
        FROM api_costs
        WHERE session_id IS NOT NULL AND {time_filter}
        """,  # nosec B608
        (),
        fetch="one",
    )
    overall_hit_rate = float(overall_stats["hit_rate"] or 0) if overall_stats else 0

    # Sample size warning
    min_sample_warning = None
    if total_sessions < 50:
        min_sample_warning = (
            f"Low sample size ({total_sessions} sessions). Insights may be unreliable."
        )

    logger.info(
        f"Admin: Cache effectiveness drill-down: {total_sessions} sessions, "
        f"{overall_hit_rate:.1%} hit rate, period={period.value}"
    )

    return CacheEffectivenessResponse(
        buckets=buckets,
        overall_hit_rate=overall_hit_rate,
        total_sessions=total_sessions,
        total_cost=total_cost,
        total_saved=total_saved,
        period=period.value,
        min_sample_warning=min_sample_warning,
    )


def _normalize_model_name(model_name: str) -> tuple[str, str]:
    """Normalize model name to canonical form and display name."""
    name_lower = (model_name or "unknown").lower()

    if "opus" in name_lower:
        return "opus", "Claude Opus"
    elif "sonnet" in name_lower:
        return "sonnet", "Claude Sonnet"
    elif "haiku" in name_lower:
        return "haiku", "Claude Haiku"
    elif "gpt-4" in name_lower:
        return "gpt-4", "GPT-4"
    elif "gpt-3" in name_lower:
        return "gpt-3.5", "GPT-3.5"
    else:
        return model_name or "unknown", model_name or "Unknown"


# Approximate cost per 1M tokens by model tier (input + output averaged)
MODEL_COST_MULTIPLIERS = {
    "opus": 25.0,  # ~$15/1M input + $75/1M output averaged
    "sonnet": 6.0,  # ~$3/1M input + $15/1M output averaged
    "haiku": 0.5,  # ~$0.25/1M input + $1.25/1M output averaged
}


@router.get(
    "/model-impact",
    response_model=ModelImpactResponse,
    summary="Model impact drill-down",
    description="Analyze cost impact by model tier with what-if scenarios.",
    responses={
        200: {"description": "Model impact data retrieved"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get model impact drill-down")
async def get_model_impact(
    request: Request,
    period: TimePeriod = Query(TimePeriod.WEEK, description="Time period filter"),
    _admin: str = Depends(require_admin_any),
) -> ModelImpactResponse:
    """Get model impact analysis with what-if scenarios."""
    time_filter = _get_time_filter(period)

    rows = execute_query(
        f"""
        SELECT
            model_name,
            COUNT(*) as request_count,
            SUM(total_cost) as total_cost,
            AVG(total_cost) as avg_cost,
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as cache_hit_rate,
            SUM(total_tokens) as total_tokens
        FROM api_costs
        WHERE provider = 'anthropic'
          AND {time_filter}
        GROUP BY model_name
        ORDER BY total_cost DESC
        """,  # nosec B608
        (),
    )

    models = []
    total_cost = 0.0
    total_requests = 0
    total_tokens_all = 0

    for row in rows:
        model_name = row["model_name"] or "unknown"
        normalized, display = _normalize_model_name(model_name)
        request_count = row["request_count"] or 0
        cost = float(row["total_cost"] or 0)
        tokens = row["total_tokens"] or 0

        total_cost += cost
        total_requests += request_count
        total_tokens_all += tokens

        models.append(
            ModelImpactItem(
                model_name=normalized,
                model_display=display,
                request_count=request_count,
                total_cost=cost,
                avg_cost_per_request=float(row["avg_cost"] or 0),
                cache_hit_rate=float(row["cache_hit_rate"] or 0),
                total_tokens=tokens,
            )
        )

    # Calculate what-if scenarios using token counts
    # Cost per 1M tokens
    cost_if_all_opus = (total_tokens_all / 1_000_000) * MODEL_COST_MULTIPLIERS["opus"]
    cost_if_all_haiku = (total_tokens_all / 1_000_000) * MODEL_COST_MULTIPLIERS["haiku"]
    savings_from_model_mix = cost_if_all_opus - total_cost

    logger.info(
        f"Admin: Model impact drill-down: {total_requests} requests, "
        f"${total_cost:.2f} actual, ${cost_if_all_opus:.2f} if all Opus, period={period.value}"
    )

    return ModelImpactResponse(
        models=models,
        total_cost=total_cost,
        total_requests=total_requests,
        cost_if_all_opus=cost_if_all_opus,
        cost_if_all_haiku=cost_if_all_haiku,
        savings_from_model_mix=savings_from_model_mix,
        period=period.value,
    )


@router.get(
    "/feature-efficiency",
    response_model=FeatureEfficiencyResponse,
    summary="Feature efficiency drill-down",
    description="Analyze cost and cache effectiveness by feature.",
    responses={
        200: {"description": "Feature efficiency data retrieved"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get feature efficiency drill-down")
async def get_feature_efficiency(
    request: Request,
    period: TimePeriod = Query(TimePeriod.WEEK, description="Time period filter"),
    _admin: str = Depends(require_admin_any),
) -> FeatureEfficiencyResponse:
    """Get feature efficiency analysis."""
    time_filter = _get_time_filter(period)

    rows = execute_query(
        f"""
        SELECT
            COALESCE(feature, 'unknown') as feature,
            COUNT(*) as request_count,
            SUM(total_cost) as total_cost,
            AVG(total_cost) as avg_cost,
            SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as cache_hit_rate,
            COUNT(DISTINCT session_id) as unique_sessions
        FROM api_costs
        WHERE {time_filter}
        GROUP BY feature
        ORDER BY total_cost DESC
        """,
        (),
    )

    features = []
    total_cost = 0.0
    total_requests = 0

    for row in rows:
        feature_name = row["feature"]
        request_count = row["request_count"] or 0
        cost = float(row["total_cost"] or 0)
        unique_sessions = row["unique_sessions"] or 0

        total_cost += cost
        total_requests += request_count

        features.append(
            FeatureEfficiencyItem(
                feature=feature_name,
                request_count=request_count,
                total_cost=cost,
                avg_cost=float(row["avg_cost"] or 0),
                cache_hit_rate=float(row["cache_hit_rate"] or 0),
                unique_sessions=unique_sessions,
                cost_per_session=cost / unique_sessions if unique_sessions > 0 else 0,
            )
        )

    logger.info(
        f"Admin: Feature efficiency drill-down: {len(features)} features, "
        f"${total_cost:.2f} total, period={period.value}"
    )

    return FeatureEfficiencyResponse(
        features=features,
        total_cost=total_cost,
        total_requests=total_requests,
        period=period.value,
    )


@router.get(
    "/tuning-recommendations",
    response_model=TuningRecommendationsResponse,
    summary="Cache tuning recommendations",
    description="Get AI-generated recommendations for cache and model optimization.",
    responses={
        200: {"description": "Tuning recommendations retrieved"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get tuning recommendations")
async def get_tuning_recommendations(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> TuningRecommendationsResponse:
    """Get tuning recommendations based on recent metrics."""
    # Get 30-day metrics
    try:
        stats = execute_query(
            """
            SELECT
                COUNT(*) as total_requests,
                COUNT(DISTINCT session_id) as total_sessions,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as cache_hit_rate,
                SUM(total_cost) as total_cost,
                SUM(COALESCE(cost_without_optimization, total_cost) - total_cost) as total_saved
            FROM api_costs
            WHERE created_at >= NOW() - INTERVAL '30 days'
            """,
            (),
            fetch="one",
        )
    except Exception as e:
        logger.warning(f"Failed to get tuning recommendations stats: {e}")
        stats = None

    recommendations = []
    total_requests = stats["total_requests"] or 0 if stats else 0
    cache_hit_rate = float(stats["cache_hit_rate"] or 0) if stats else 0
    total_cost = float(stats["total_cost"] or 0) if stats else 0

    # Determine data quality
    if total_requests < 100:
        data_quality = "insufficient"
    elif total_requests < 1000:
        data_quality = "limited"
    else:
        data_quality = "sufficient"

    # Cache hit rate recommendation
    if cache_hit_rate < 0.30:
        recommendations.append(
            TuningRecommendation(
                area="cache",
                current_value=f"{cache_hit_rate:.0%} cache hit rate",
                recommended_value="Target 40-50% hit rate",
                impact_description="Low cache hit rate indicates potential for optimization. "
                "Consider lowering similarity threshold for research cache.",
                estimated_savings_usd=total_cost * 0.1 if total_cost > 0 else None,
                confidence="medium" if data_quality != "insufficient" else "low",
            )
        )
    elif cache_hit_rate > 0.70:
        recommendations.append(
            TuningRecommendation(
                area="cache",
                current_value=f"{cache_hit_rate:.0%} cache hit rate",
                recommended_value="Monitor quality metrics",
                impact_description="High cache hit rate is good for cost savings. "
                "Monitor user satisfaction to ensure quality isn't impacted.",
                estimated_savings_usd=None,
                confidence="high",
            )
        )

    # Model mix recommendation
    try:
        model_stats = execute_query(
            """
            SELECT
                CASE
                    WHEN model_name ILIKE '%opus%' THEN 'opus'
                    WHEN model_name ILIKE '%sonnet%' THEN 'sonnet'
                    WHEN model_name ILIKE '%haiku%' THEN 'haiku'
                    ELSE 'other'
                END as model_tier,
                COUNT(*) as count,
                SUM(total_cost) as cost
            FROM api_costs
            WHERE provider = 'anthropic'
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY model_tier
            """,
            (),
        )
    except Exception as e:
        logger.warning(f"Failed to get model stats for tuning recommendations: {e}")
        model_stats = []

    model_mix = {r["model_tier"]: r for r in model_stats}
    opus_pct = (
        model_mix.get("opus", {}).get("count", 0) / total_requests if total_requests > 0 else 0
    )

    if opus_pct > 0.5:
        recommendations.append(
            TuningRecommendation(
                area="model",
                current_value=f"{opus_pct:.0%} Opus usage",
                recommended_value="Shift non-critical calls to Sonnet/Haiku",
                impact_description="High Opus usage increases costs. "
                "Consider using Sonnet for standard tasks and Haiku for simple operations.",
                estimated_savings_usd=total_cost * 0.3,
                confidence="high",
            )
        )

    # Feature efficiency recommendation
    try:
        feature_stats = execute_query(
            """
            SELECT
                feature,
                COUNT(*) as request_count,
                SUM(total_cost) as total_cost,
                AVG(total_cost) as avg_cost
            FROM api_costs
            WHERE feature IS NOT NULL
              AND created_at >= NOW() - INTERVAL '30 days'
            GROUP BY feature
            HAVING COUNT(*) > 100
            ORDER BY AVG(total_cost) DESC
            LIMIT 3
            """,
            (),
        )
    except Exception as e:
        logger.warning(f"Failed to get feature stats for tuning recommendations: {e}")
        feature_stats = []

    for row in feature_stats:
        avg_cost = float(row["avg_cost"] or 0)
        if avg_cost > 0.05:  # More than 5 cents per request
            recommendations.append(
                TuningRecommendation(
                    area="feature",
                    current_value=f"{row['feature']}: ${avg_cost:.3f}/request",
                    recommended_value="Review prompt efficiency",
                    impact_description=f"Feature '{row['feature']}' has high per-request cost. "
                    "Consider prompt optimization or model tier adjustment.",
                    estimated_savings_usd=float(row["total_cost"]) * 0.2,
                    confidence="medium",
                )
            )

    logger.info(
        f"Admin: Generated {len(recommendations)} tuning recommendations "
        f"from {total_requests} requests (data quality: {data_quality})"
    )

    return TuningRecommendationsResponse(
        recommendations=recommendations,
        analysis_period_days=30,
        data_quality=data_quality,
    )


@router.get(
    "/quality-indicators",
    response_model=QualityIndicatorsResponse,
    summary="Quality correlation indicators",
    description="Analyze correlation between cache hits and user behavior quality signals.",
    responses={
        200: {"description": "Quality indicators retrieved"},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get quality indicators")
async def get_quality_indicators(
    request: Request,
    period: TimePeriod = Query(TimePeriod.MONTH, description="Time period filter"),
    _admin: str = Depends(require_admin_any),
) -> QualityIndicatorsResponse:
    """Get quality correlation indicators for cache vs user behavior."""
    time_filter = _get_time_filter(period)

    # Get session-level stats with continuation proxy
    # Continuation = session has > 1 request (user continued after first response)
    stats = execute_query(
        f"""
        WITH session_metrics AS (
            SELECT
                session_id,
                COUNT(*) as request_count,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits,
                SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as hit_rate
            FROM api_costs
            WHERE session_id IS NOT NULL
              AND {time_filter}
            GROUP BY session_id
        )
        SELECT
            COUNT(*) as total_sessions,
            AVG(hit_rate) as avg_hit_rate,
            SUM(CASE WHEN request_count > 1 THEN 1 ELSE 0 END)::float / NULLIF(COUNT(*), 0) as continuation_rate,
            SUM(CASE WHEN hit_rate > 0.5 AND request_count > 1 THEN 1 ELSE 0 END)::float /
                NULLIF(SUM(CASE WHEN hit_rate > 0.5 THEN 1 ELSE 0 END), 0) as cached_continuation,
            SUM(CASE WHEN hit_rate <= 0.5 AND request_count > 1 THEN 1 ELSE 0 END)::float /
                NULLIF(SUM(CASE WHEN hit_rate <= 0.5 THEN 1 ELSE 0 END), 0) as uncached_continuation
        FROM session_metrics
        """,
        (),
        fetch="one",
    )

    sample_size = stats["total_sessions"] or 0 if stats else 0
    overall_hit_rate = float(stats["avg_hit_rate"] or 0) if stats else 0
    continuation_rate = float(stats["continuation_rate"] or 0) if stats else 0
    cached_continuation = float(stats["cached_continuation"] or 0) if stats else None
    uncached_continuation = float(stats["uncached_continuation"] or 0) if stats else None

    # Calculate correlation score (difference in continuation rates)
    correlation_score = None
    if cached_continuation is not None and uncached_continuation is not None:
        correlation_score = cached_continuation - uncached_continuation

    # Generate quality assessment
    if sample_size < 50:
        quality_assessment = "Insufficient data for reliable quality assessment."
    elif correlation_score is not None:
        if correlation_score > 0.1:
            quality_assessment = (
                "Cached responses show higher continuation rates, "
                "suggesting cache quality is acceptable."
            )
        elif correlation_score < -0.1:
            quality_assessment = (
                "Uncached responses show higher continuation rates. "
                "Consider reviewing cache quality and threshold settings."
            )
        else:
            quality_assessment = (
                "No significant difference in continuation between cached and uncached responses. "
                "Cache appears to maintain quality parity."
            )
    else:
        quality_assessment = "Unable to calculate correlation with available data."

    logger.info(
        f"Admin: Quality indicators: {sample_size} sessions, "
        f"hit_rate={overall_hit_rate:.1%}, continuation={continuation_rate:.1%}, "
        f"period={period.value}"
    )

    return QualityIndicatorsResponse(
        overall_cache_hit_rate=overall_hit_rate,
        session_continuation_rate=continuation_rate,
        correlation_score=correlation_score,
        sample_size=sample_size,
        cached_continuation_rate=cached_continuation,
        uncached_continuation_rate=uncached_continuation,
        quality_assessment=quality_assessment,
        period=period.value,
    )
