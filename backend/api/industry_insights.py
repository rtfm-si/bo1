"""Industry Insights API endpoints.

Phase 4 of ACCOUNT_CONTEXT_PLAN - Cross-User Intelligence.

This module provides endpoints for retrieving aggregated industry insights
that benefit all users. Currently returns stub data; full aggregation
pipeline to be implemented later.

Provides:
- GET /api/v1/industry-insights - Get insights for user's industry (tier-limited)
- GET /api/v1/industry-insights/:industry - Get insights for specific industry
- GET /api/v1/industry-insights/compare - Compare user metrics against benchmarks
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2 import DatabaseError, OperationalError
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import get_user_tier
from backend.api.utils.errors import handle_api_errors
from backend.services.insight_staleness import get_stale_benchmarks
from bo1.constants import IndustryBenchmarkLimits
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["industry-insights"])


# =============================================================================
# Models
# =============================================================================


class BenchmarkCategory(str, Enum):
    """Benchmark metric categories."""

    GROWTH = "growth"
    RETENTION = "retention"
    EFFICIENCY = "efficiency"
    ENGAGEMENT = "engagement"


class InsightContent(BaseModel):
    """Base content for all insight types."""

    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class BenchmarkContent(InsightContent):
    """Content for benchmark insights."""

    metric_name: str = Field(..., description="Metric being benchmarked")
    metric_unit: str = Field(..., description="Unit of measurement")
    category: BenchmarkCategory = Field(..., description="Benchmark category")
    industry_segment: str = Field(..., description="Industry segment")
    p25: float | None = Field(None, description="25th percentile")
    p50: float | None = Field(None, description="Median (50th percentile)")
    p75: float | None = Field(None, description="75th percentile")
    sample_size: int | None = Field(None, description="Number of data points")


class IndustryInsight(BaseModel):
    """An industry insight."""

    id: str = Field(..., description="Insight ID")
    industry: str = Field(..., description="Industry vertical")
    insight_type: str = Field(..., description="trend, benchmark, competitor, best_practice")
    content: dict[str, Any] = Field(..., description="Insight content (structure varies by type)")
    source_count: int = Field(1, description="Number of contributing users")
    confidence: float = Field(0.5, description="Confidence score 0-1")
    expires_at: datetime | None = Field(None, description="When this insight expires")
    created_at: datetime = Field(..., description="Creation timestamp")
    locked: bool = Field(False, description="Whether this insight is tier-locked")


class IndustryInsightsResponse(BaseModel):
    """Response containing industry insights."""

    industry: str = Field(..., description="Industry the insights are for")
    insights: list[IndustryInsight] = Field(default_factory=list, description="List of insights")
    has_benchmarks: bool = Field(False, description="Whether benchmark data is available")
    locked_count: int = Field(0, description="Number of tier-locked benchmarks")
    upgrade_prompt: str | None = Field(None, description="Upgrade message if benchmarks are locked")
    user_tier: str = Field("free", description="User's current subscription tier")


class BenchmarkHistoryEntry(BaseModel):
    """A single historical benchmark value."""

    value: float = Field(..., description="Historical metric value")
    date: str = Field(..., description="Date value was recorded (YYYY-MM-DD)")


class BenchmarkComparison(BaseModel):
    """User's metrics compared to industry benchmarks."""

    metric_name: str = Field(..., description="Metric being compared")
    metric_unit: str = Field(..., description="Unit of measurement")
    category: BenchmarkCategory = Field(..., description="Benchmark category")
    user_value: float | None = Field(None, description="User's metric value")
    user_value_updated_at: str | None = Field(
        None, description="When user's value was last set (ISO timestamp)"
    )
    history: list[BenchmarkHistoryEntry] = Field(
        default_factory=list, description="Historical values (max 6, newest first)"
    )
    p25: float | None = Field(None, description="25th percentile")
    p50: float | None = Field(None, description="Median (50th percentile)")
    p75: float | None = Field(None, description="75th percentile")
    percentile: float | None = Field(None, description="User's percentile rank (0-100)")
    status: str = Field(
        "unknown",
        description="Performance status: below_average, average, above_average, top_performer",
    )
    locked: bool = Field(False, description="Whether this comparison is tier-locked")


class BenchmarkComparisonResponse(BaseModel):
    """Response with user benchmark comparisons."""

    industry: str = Field(..., description="Industry used for comparison")
    comparisons: list[BenchmarkComparison] = Field(
        default_factory=list, description="List of comparisons"
    )
    total_metrics: int = Field(0, description="Total benchmark metrics available")
    compared_count: int = Field(0, description="Metrics user has data for")
    locked_count: int = Field(0, description="Tier-locked metrics")
    upgrade_prompt: str | None = Field(
        None, description="Upgrade message if comparisons are locked"
    )


# =============================================================================
# Stub Data (to be replaced with real aggregation)
# =============================================================================


# Comprehensive benchmark data by industry segment
BENCHMARK_DATA: dict[str, list[dict[str, Any]]] = {
    "SaaS": [
        # Retention metrics
        {
            "title": "Monthly Churn Rate",
            "description": "Average monthly customer churn for SaaS companies",
            "metric_name": "monthly_churn",
            "metric_unit": "%",
            "category": BenchmarkCategory.RETENTION,
            "industry_segment": "SaaS",
            "p25": 1.5,
            "p50": 3.0,
            "p75": 5.0,
            "sample_size": 150,
        },
        {
            "title": "Net Revenue Retention",
            "description": "NRR measures expansion minus churn from existing customers",
            "metric_name": "nrr",
            "metric_unit": "%",
            "category": BenchmarkCategory.RETENTION,
            "industry_segment": "SaaS",
            "p25": 95,
            "p50": 105,
            "p75": 120,
            "sample_size": 120,
        },
        # Efficiency metrics
        {
            "title": "LTV:CAC Ratio",
            "description": "Healthy LTV to CAC ratio benchmarks",
            "metric_name": "ltv_cac",
            "metric_unit": "ratio",
            "category": BenchmarkCategory.EFFICIENCY,
            "industry_segment": "SaaS",
            "p25": 2.0,
            "p50": 3.5,
            "p75": 5.0,
            "sample_size": 100,
        },
        {
            "title": "CAC Payback Period",
            "description": "Months to recover customer acquisition cost",
            "metric_name": "cac_payback",
            "metric_unit": "months",
            "category": BenchmarkCategory.EFFICIENCY,
            "industry_segment": "SaaS",
            "p25": 18,
            "p50": 12,
            "p75": 6,
            "sample_size": 95,
        },
        # Growth metrics
        {
            "title": "Average Revenue Per User",
            "description": "Monthly ARPU for B2B SaaS",
            "metric_name": "arpu",
            "metric_unit": "USD/month",
            "category": BenchmarkCategory.GROWTH,
            "industry_segment": "SaaS",
            "p25": 25,
            "p50": 75,
            "p75": 200,
            "sample_size": 180,
        },
        {
            "title": "MRR Growth Rate",
            "description": "Month-over-month recurring revenue growth",
            "metric_name": "mrr_growth",
            "metric_unit": "%",
            "category": BenchmarkCategory.GROWTH,
            "industry_segment": "SaaS",
            "p25": 3,
            "p50": 8,
            "p75": 15,
            "sample_size": 140,
        },
        # Engagement metrics
        {
            "title": "DAU/MAU Ratio",
            "description": "Daily to monthly active user engagement ratio",
            "metric_name": "dau_mau",
            "metric_unit": "ratio",
            "category": BenchmarkCategory.ENGAGEMENT,
            "industry_segment": "SaaS",
            "p25": 0.10,
            "p50": 0.20,
            "p75": 0.40,
            "sample_size": 110,
        },
        {
            "title": "Activation Rate",
            "description": "Percentage of signups reaching activation milestone",
            "metric_name": "activation_rate",
            "metric_unit": "%",
            "category": BenchmarkCategory.ENGAGEMENT,
            "industry_segment": "SaaS",
            "p25": 20,
            "p50": 35,
            "p75": 55,
            "sample_size": 130,
        },
    ],
    "E-commerce": [
        {
            "title": "Cart Abandonment Rate",
            "description": "Percentage of carts abandoned before checkout",
            "metric_name": "cart_abandonment",
            "metric_unit": "%",
            "category": BenchmarkCategory.RETENTION,
            "industry_segment": "E-commerce",
            "p25": 75,
            "p50": 70,
            "p75": 60,
            "sample_size": 200,
        },
        {
            "title": "Customer Return Rate",
            "description": "Percentage of customers making repeat purchases",
            "metric_name": "return_rate",
            "metric_unit": "%",
            "category": BenchmarkCategory.RETENTION,
            "industry_segment": "E-commerce",
            "p25": 15,
            "p50": 25,
            "p75": 40,
            "sample_size": 175,
        },
        {
            "title": "Average Order Value",
            "description": "Average transaction value",
            "metric_name": "aov",
            "metric_unit": "USD",
            "category": BenchmarkCategory.GROWTH,
            "industry_segment": "E-commerce",
            "p25": 45,
            "p50": 85,
            "p75": 150,
            "sample_size": 190,
        },
    ],
    "Fintech": [
        {
            "title": "Customer Acquisition Cost",
            "description": "Average cost to acquire a new customer",
            "metric_name": "cac",
            "metric_unit": "USD",
            "category": BenchmarkCategory.EFFICIENCY,
            "industry_segment": "Fintech",
            "p25": 200,
            "p50": 350,
            "p75": 600,
            "sample_size": 80,
        },
        {
            "title": "Net Promoter Score",
            "description": "Customer satisfaction and loyalty metric",
            "metric_name": "nps",
            "metric_unit": "score",
            "category": BenchmarkCategory.ENGAGEMENT,
            "industry_segment": "Fintech",
            "p25": 20,
            "p50": 40,
            "p75": 60,
            "sample_size": 95,
        },
    ],
    "Marketplace": [
        {
            "title": "Take Rate",
            "description": "Percentage commission on transactions",
            "metric_name": "take_rate",
            "metric_unit": "%",
            "category": BenchmarkCategory.GROWTH,
            "industry_segment": "Marketplace",
            "p25": 8,
            "p50": 15,
            "p75": 25,
            "sample_size": 65,
        },
        {
            "title": "Gross Merchandise Value Growth",
            "description": "Year-over-year GMV growth",
            "metric_name": "gmv_growth",
            "metric_unit": "%",
            "category": BenchmarkCategory.GROWTH,
            "industry_segment": "Marketplace",
            "p25": 20,
            "p50": 40,
            "p75": 80,
            "sample_size": 55,
        },
    ],
}

# Metric name to context field mapping (for comparison endpoint)
METRIC_TO_CONTEXT_FIELD: dict[str, str] = {
    "monthly_churn": "churn_rate",
    "nrr": "net_revenue_retention",
    "ltv_cac": "ltv_cac_ratio",
    "cac_payback": "cac_payback_months",
    "arpu": "arpu",
    "mrr_growth": "mrr_growth_rate",
    "dau_mau": "dau_mau_ratio",
    "activation_rate": "activation_rate",
    "cac": "cac",
    "nps": "nps_score",
    "aov": "average_order_value",
    "cart_abandonment": "cart_abandonment_rate",
    "return_rate": "customer_return_rate",
    "take_rate": "take_rate",
    "gmv_growth": "gmv_growth_rate",
}


def get_benchmarks_for_industry(industry: str) -> list[dict[str, Any]]:
    """Get benchmark data for a specific industry.

    Matches industry string to closest segment.
    """
    industry_lower = industry.lower()

    # Direct segment match
    for segment in BENCHMARK_DATA:
        if segment.lower() in industry_lower:
            return BENCHMARK_DATA[segment]

    # Fallback matches
    if any(term in industry_lower for term in ["software", "tech", "b2b", "subscription"]):
        return BENCHMARK_DATA["SaaS"]
    if any(term in industry_lower for term in ["retail", "shop", "commerce", "store"]):
        return BENCHMARK_DATA["E-commerce"]
    if any(term in industry_lower for term in ["finance", "bank", "payment", "insurance"]):
        return BENCHMARK_DATA["Fintech"]
    if any(term in industry_lower for term in ["marketplace", "platform", "two-sided"]):
        return BENCHMARK_DATA["Marketplace"]

    # Default to SaaS
    return BENCHMARK_DATA["SaaS"]


def get_stub_insights(industry: str, tier: str = "free") -> tuple[list[IndustryInsight], int]:
    """Generate stub insights for demonstration with tier filtering.

    In production, these would come from the industry_insights table
    populated by an aggregation job.

    Returns:
        Tuple of (insights list, locked_count)
    """
    now = datetime.now(UTC)
    limit = IndustryBenchmarkLimits.get_limit_for_tier(tier)

    # Get benchmarks for industry
    benchmarks = get_benchmarks_for_industry(industry)
    insights: list[IndustryInsight] = []
    locked_count = 0

    # Add benchmarks with tier filtering
    for i, bm in enumerate(benchmarks):
        is_locked = limit != -1 and i >= limit
        if is_locked:
            locked_count += 1

        insights.append(
            IndustryInsight(
                id=f"benchmark-{i + 1}",
                industry=industry,
                insight_type="benchmark",
                content=bm,
                source_count=bm.get("sample_size", 50),
                confidence=0.85,
                expires_at=now + timedelta(days=90),
                created_at=now - timedelta(days=30),
                locked=is_locked,
            )
        )

    # General trends (not tier-limited)
    general_trends = [
        {
            "title": "AI Integration Acceleration",
            "description": "Companies are rapidly integrating AI into core products, with 70% of tech companies planning AI features in 2025.",
        },
        {
            "title": "Focus on Unit Economics",
            "description": "Investors emphasizing profitability metrics over pure growth. CAC payback under 12 months increasingly important.",
        },
        {
            "title": "Product-Led Growth",
            "description": "Self-serve onboarding and freemium models driving customer acquisition, reducing reliance on sales teams.",
        },
    ]

    for i, trend in enumerate(general_trends):
        insights.append(
            IndustryInsight(
                id=f"trend-{i + 1}",
                industry=industry,
                insight_type="trend",
                content=trend,
                source_count=200,
                confidence=0.75,
                expires_at=now + timedelta(days=7),
                created_at=now - timedelta(days=2),
                locked=False,
            )
        )

    # Best practices (not tier-limited)
    best_practices = [
        {
            "title": "Customer Health Scoring",
            "description": "Leading companies use multi-factor health scores combining usage, NPS, and support tickets to predict and prevent churn.",
        },
        {
            "title": "Data-Driven Pricing",
            "description": "Regular pricing experiments and value-based pricing strategies outperform cost-plus models by 20-30%.",
        },
    ]

    for i, bp in enumerate(best_practices):
        insights.append(
            IndustryInsight(
                id=f"practice-{i + 1}",
                industry=industry,
                insight_type="best_practice",
                content=bp,
                source_count=50,
                confidence=0.8,
                expires_at=None,
                created_at=now - timedelta(days=60),
                locked=False,
            )
        )

    return insights, locked_count


def calculate_percentile(
    value: float, p25: float, p50: float, p75: float, lower_is_better: bool = False
) -> float:
    """Calculate approximate percentile for a user value.

    Uses linear interpolation between known percentiles.

    Args:
        value: User's metric value
        p25: 25th percentile benchmark
        p50: 50th percentile benchmark (median)
        p75: 75th percentile benchmark
        lower_is_better: If True, lower values rank higher (e.g., churn)

    Returns:
        Estimated percentile (0-100)
    """
    if lower_is_better:
        # Invert for metrics where lower is better
        if value >= p25:
            return 12.5 + (p25 - value) / max(p25, 0.01) * 12.5  # 0-25
        elif value >= p50:
            return 25 + (p25 - value) / max(p25 - p50, 0.01) * 25  # 25-50
        elif value >= p75:
            return 50 + (p50 - value) / max(p50 - p75, 0.01) * 25  # 50-75
        else:
            return min(100, 75 + (p75 - value) / max(p75, 0.01) * 25)  # 75-100
    else:
        # Higher values rank higher
        if value <= p25:
            return max(0, value / max(p25, 0.01) * 25)  # 0-25
        elif value <= p50:
            return 25 + (value - p25) / max(p50 - p25, 0.01) * 25  # 25-50
        elif value <= p75:
            return 50 + (value - p50) / max(p75 - p50, 0.01) * 25  # 50-75
        else:
            return min(100, 75 + (value - p75) / max(p75, 0.01) * 25)  # 75-100


def get_performance_status(percentile: float) -> str:
    """Get performance status label from percentile."""
    if percentile < 25:
        return "below_average"
    elif percentile < 50:
        return "average"
    elif percentile < 75:
        return "above_average"
    else:
        return "top_performer"


# Metrics where lower values are better
LOWER_IS_BETTER_METRICS = {"monthly_churn", "cac_payback", "cac", "cart_abandonment"}


# =============================================================================
# Helper Functions
# =============================================================================


def get_upgrade_prompt(tier: str, locked_count: int) -> str | None:
    """Get upgrade prompt message based on tier and locked count."""
    if locked_count == 0:
        return None

    if tier == "free":
        return f"Upgrade to Starter to unlock {min(2, locked_count)} more benchmarks, or Pro for unlimited access."
    elif tier == "starter":
        return f"Upgrade to Pro to unlock all {locked_count} remaining benchmarks."
    return None


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/v1/industry-insights",
    response_model=IndustryInsightsResponse,
    summary="Get insights for user's industry",
    description="""
    Retrieve aggregated industry insights for the authenticated user's industry.

    Uses the industry from the user's saved business context.
    Returns benchmarks, trends, and best practices.

    **Tier Limits:**
    - Free: 3 benchmark metrics
    - Starter: 5 benchmark metrics
    - Pro/Enterprise: Unlimited

    Locked benchmarks are returned with `locked=true` and limited content.
    """,
)
@handle_api_errors("get insights for user")
async def get_insights_for_user(
    insight_type: str | None = Query(
        None, description="Filter by type: trend, benchmark, best_practice"
    ),
    category: str | None = Query(
        None, description="Filter benchmarks by category: growth, retention, efficiency, engagement"
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> IndustryInsightsResponse:
    """Get industry insights for the user's industry with tier-based filtering."""
    try:
        user_id = extract_user_id(user)

        # Get user's industry from context
        context_data = user_repository.get_context(user_id)
        industry = context_data.get("industry") if context_data else None

        if not industry:
            return IndustryInsightsResponse(
                industry="Unknown",
                insights=[],
                has_benchmarks=False,
                locked_count=0,
                user_tier="free",
            )

        # Get user's tier
        tier = get_user_tier(user_id)

        # Get insights with tier filtering
        insights, locked_count = get_stub_insights(industry, tier)

        # Filter by type if specified
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
            # Recalculate locked count for filtered results
            if insight_type == "benchmark":
                locked_count = sum(1 for i in insights if i.locked)
            else:
                locked_count = 0

        # Filter by category if specified (only applies to benchmarks)
        if category:
            insights = [
                i
                for i in insights
                if i.insight_type != "benchmark" or i.content.get("category") == category
            ]
            locked_count = sum(1 for i in insights if i.locked)

        # Get upgrade prompt if needed
        upgrade_prompt = get_upgrade_prompt(tier, locked_count)

        return IndustryInsightsResponse(
            industry=industry,
            insights=insights,
            has_benchmarks=any(i.insight_type == "benchmark" for i in insights),
            locked_count=locked_count,
            upgrade_prompt=upgrade_prompt,
            user_tier=tier,
        )

    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Database error getting insights: {e}",
            user_id=user_id,
            industry=industry if "industry" in locals() else None,
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving insights",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error getting insights: {e}",
            exc_info=True,
            user_id=user_id if "user_id" in locals() else None,
            industry=industry if "industry" in locals() else None,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get insights: {str(e)}",
        ) from e


@router.get(
    "/v1/industry-insights/compare",
    response_model=BenchmarkComparisonResponse,
    summary="Compare user metrics against benchmarks",
    description="""
    Compare the authenticated user's metrics against industry benchmarks.

    Extracts metrics from the user's business context (churn rate, revenue, etc.)
    and calculates their percentile ranking against industry benchmarks.

    **Tier Limits:**
    - Free: 3 comparisons
    - Starter: 5 comparisons
    - Pro/Enterprise: Unlimited

    Returns percentile ranking and performance status for each metric.
    """,
)
@handle_api_errors("compare benchmarks")
async def compare_benchmarks(
    user: dict[str, Any] = Depends(get_current_user),
) -> BenchmarkComparisonResponse:
    """Compare user metrics against industry benchmarks."""
    try:
        user_id = extract_user_id(user)

        # Get user's context
        context_data = user_repository.get_context(user_id)
        industry = context_data.get("industry") if context_data else None

        if not industry:
            return BenchmarkComparisonResponse(
                industry="Unknown",
                comparisons=[],
                total_metrics=0,
                compared_count=0,
                locked_count=0,
            )

        # Get user's tier
        tier = get_user_tier(user_id)
        limit = IndustryBenchmarkLimits.get_limit_for_tier(tier)

        # Get benchmarks for industry
        benchmarks = get_benchmarks_for_industry(industry)
        comparisons: list[BenchmarkComparison] = []
        compared_count = 0
        locked_count = 0

        # Get benchmark timestamps and history for user value dates
        benchmark_timestamps = context_data.get("benchmark_timestamps", {}) if context_data else {}
        benchmark_history = context_data.get("benchmark_history", {}) if context_data else {}

        for i, bm in enumerate(benchmarks):
            is_locked = limit != -1 and i >= limit
            if is_locked:
                locked_count += 1

            metric_name = bm["metric_name"]
            context_field = METRIC_TO_CONTEXT_FIELD.get(metric_name)

            # Try to get user's value for this metric
            user_value = None
            user_value_updated_at = None
            history_entries: list[BenchmarkHistoryEntry] = []
            if context_field and context_data:
                user_value = context_data.get(context_field)
                # Also try nested fields
                if user_value is None and "metrics" in context_data:
                    user_value = context_data["metrics"].get(context_field)
                # Get timestamp for this field
                user_value_updated_at = benchmark_timestamps.get(context_field)
                # Get history for this field
                field_history = benchmark_history.get(context_field, [])
                for h in field_history[:6]:  # Max 6 entries
                    if "value" in h and "date" in h:
                        try:
                            history_entries.append(
                                BenchmarkHistoryEntry(value=float(h["value"]), date=h["date"])
                            )
                        except (ValueError, TypeError):
                            continue

            # Calculate percentile if we have user data
            percentile = None
            status = "unknown"
            if user_value is not None and not is_locked:
                compared_count += 1
                lower_is_better = metric_name in LOWER_IS_BETTER_METRICS
                percentile = calculate_percentile(
                    float(user_value),
                    bm["p25"],
                    bm["p50"],
                    bm["p75"],
                    lower_is_better,
                )
                status = get_performance_status(percentile)

            comparisons.append(
                BenchmarkComparison(
                    metric_name=metric_name,
                    metric_unit=bm["metric_unit"],
                    category=bm["category"],
                    user_value=float(user_value)
                    if user_value is not None and not is_locked
                    else None,
                    user_value_updated_at=user_value_updated_at
                    if user_value is not None and not is_locked
                    else None,
                    history=history_entries if not is_locked else [],
                    p25=bm["p25"] if not is_locked else None,
                    p50=bm["p50"] if not is_locked else None,
                    p75=bm["p75"] if not is_locked else None,
                    percentile=round(percentile, 1) if percentile is not None else None,
                    status=status if not is_locked else "locked",
                    locked=is_locked,
                )
            )

        # Get upgrade prompt if needed
        upgrade_prompt = get_upgrade_prompt(tier, locked_count)

        return BenchmarkComparisonResponse(
            industry=industry,
            comparisons=comparisons,
            total_metrics=len(benchmarks),
            compared_count=compared_count,
            locked_count=locked_count,
            upgrade_prompt=upgrade_prompt,
        )

    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Database error comparing benchmarks: {e}",
            user_id=user_id,
            industry=industry if "industry" in locals() else None,
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while comparing benchmarks",
        ) from e
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error comparing benchmarks: {e}",
            exc_info=True,
            user_id=user_id if "user_id" in locals() else None,
            industry=industry if "industry" in locals() else None,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare benchmarks: {str(e)}",
        ) from e


@router.get(
    "/v1/industry-insights/{industry}",
    response_model=IndustryInsightsResponse,
    summary="Get insights for specific industry",
    description="""
    Retrieve aggregated industry insights for a specific industry.

    Returns benchmarks, trends, and best practices for the specified industry.
    Tier limits are applied based on the authenticated user's subscription.
    """,
)
@handle_api_errors("get insights by industry")
async def get_insights_by_industry(
    industry: str,
    insight_type: str | None = Query(
        None, description="Filter by type: trend, benchmark, best_practice"
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> IndustryInsightsResponse:
    """Get industry insights for a specific industry."""
    try:
        user_id = extract_user_id(user)
        tier = get_user_tier(user_id)

        # Get insights with tier filtering
        insights, locked_count = get_stub_insights(industry, tier)

        # Filter by type if specified
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]
            if insight_type == "benchmark":
                locked_count = sum(1 for i in insights if i.locked)
            else:
                locked_count = 0

        # Get upgrade prompt if needed
        upgrade_prompt = get_upgrade_prompt(tier, locked_count)

        return IndustryInsightsResponse(
            industry=industry,
            insights=insights,
            has_benchmarks=any(i.insight_type == "benchmark" for i in insights),
            locked_count=locked_count,
            upgrade_prompt=upgrade_prompt,
            user_tier=tier,
        )

    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error getting insights for {industry}: {e}",
            exc_info=True,
            user_id=user_id if "user_id" in locals() else None,
            industry=industry,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get insights: {str(e)}",
        ) from e


# =============================================================================
# Stale Benchmarks Endpoint (Monthly Check-ins)
# =============================================================================


class StaleBenchmarkResponse(BaseModel):
    """A stale benchmark in API response."""

    field_name: str = Field(..., description="Metric field name")
    display_name: str = Field(..., description="Human-readable name")
    current_value: float | int | str | None = Field(None, description="Current value")
    days_since_update: int = Field(..., description="Days since last update")


class StaleBenchmarksResponse(BaseModel):
    """Response for stale benchmarks check."""

    has_stale_benchmarks: bool = Field(..., description="Whether any benchmarks are stale")
    stale_benchmarks: list[StaleBenchmarkResponse] = Field(
        default_factory=list, description="List of stale benchmarks"
    )
    threshold_days: int = Field(30, description="Staleness threshold in days")


@router.get(
    "/v1/benchmarks/stale",
    response_model=StaleBenchmarksResponse,
    summary="Check for stale benchmark values",
    description="""
    Check which benchmark values need refreshing (monthly check-in).

    Returns benchmarks that haven't been updated in 30+ days.
    Use this to prompt users to confirm their values are still accurate.

    **Use Cases:**
    - Show refresh banner on Reports > Benchmarks page
    - Prompt user during monthly check-in flow
    """,
)
@handle_api_errors("check stale benchmarks")
async def check_stale_benchmarks(
    user: dict[str, Any] = Depends(get_current_user),
) -> StaleBenchmarksResponse:
    """Check for stale benchmark values needing user confirmation."""
    user_id = extract_user_id(user)

    result = get_stale_benchmarks(user_id)

    return StaleBenchmarksResponse(
        has_stale_benchmarks=result.has_stale_benchmarks,
        stale_benchmarks=[
            StaleBenchmarkResponse(
                field_name=b.field_name,
                display_name=b.display_name,
                current_value=b.current_value,
                days_since_update=b.days_since_update,
            )
            for b in result.stale_benchmarks
        ],
        threshold_days=30,
    )
