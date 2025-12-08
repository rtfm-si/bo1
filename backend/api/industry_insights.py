"""Industry Insights API endpoints.

Phase 4 of ACCOUNT_CONTEXT_PLAN - Cross-User Intelligence.

This module provides endpoints for retrieving aggregated industry insights
that benefit all users. Currently returns stub data; full aggregation
pipeline to be implemented later.

Provides:
- GET /api/v1/industry-insights - Get insights for user's industry
- GET /api/v1/industry-insights/:industry - Get insights for specific industry
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2 import DatabaseError, OperationalError
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["industry-insights"])


# =============================================================================
# Models
# =============================================================================


class InsightContent(BaseModel):
    """Base content for all insight types."""

    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Insight description")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class BenchmarkContent(InsightContent):
    """Content for benchmark insights."""

    metric_name: str = Field(..., description="Metric being benchmarked")
    metric_unit: str = Field(..., description="Unit of measurement")
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


class IndustryInsightsResponse(BaseModel):
    """Response containing industry insights."""

    industry: str = Field(..., description="Industry the insights are for")
    insights: list[IndustryInsight] = Field(default_factory=list, description="List of insights")
    has_benchmarks: bool = Field(False, description="Whether benchmark data is available")


# =============================================================================
# Stub Data (to be replaced with real aggregation)
# =============================================================================


def get_stub_insights(industry: str) -> list[IndustryInsight]:
    """Generate stub insights for demonstration.

    In production, these would come from the industry_insights table
    populated by an aggregation job.
    """
    now = datetime.now(UTC)

    # SaaS-specific benchmarks
    saas_benchmarks = [
        {
            "title": "Monthly Churn Rate",
            "description": "Average monthly customer churn for SaaS companies",
            "metric_name": "monthly_churn",
            "metric_unit": "%",
            "p25": 1.5,
            "p50": 3.0,
            "p75": 5.0,
            "sample_size": 150,
        },
        {
            "title": "Net Revenue Retention",
            "description": "Typical NRR for B2B SaaS companies",
            "metric_name": "nrr",
            "metric_unit": "%",
            "p25": 95,
            "p50": 105,
            "p75": 120,
            "sample_size": 120,
        },
        {
            "title": "LTV:CAC Ratio",
            "description": "Healthy LTV to CAC ratio benchmarks",
            "metric_name": "ltv_cac_ratio",
            "metric_unit": "ratio",
            "p25": 2.0,
            "p50": 3.5,
            "p75": 5.0,
            "sample_size": 100,
        },
    ]

    # General trends (apply to most industries)
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

    # Best practices
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

    insights = []

    # Add benchmarks for SaaS
    if "saas" in industry.lower() or "software" in industry.lower():
        for i, bm in enumerate(saas_benchmarks):
            insights.append(
                IndustryInsight(
                    id=f"benchmark-{i + 1}",
                    industry=industry,
                    insight_type="benchmark",
                    content=bm,
                    source_count=bm.get("sample_size", 50),
                    confidence=0.85,
                    expires_at=now + timedelta(days=90),  # Quarterly refresh
                    created_at=now - timedelta(days=30),
                )
            )

    # Add trends
    for i, trend in enumerate(general_trends):
        insights.append(
            IndustryInsight(
                id=f"trend-{i + 1}",
                industry=industry,
                insight_type="trend",
                content=trend,
                source_count=200,
                confidence=0.75,
                expires_at=now + timedelta(days=7),  # Weekly refresh
                created_at=now - timedelta(days=2),
            )
        )

    # Add best practices
    for i, bp in enumerate(best_practices):
        insights.append(
            IndustryInsight(
                id=f"practice-{i + 1}",
                industry=industry,
                insight_type="best_practice",
                content=bp,
                source_count=50,
                confidence=0.8,
                expires_at=None,  # Evergreen
                created_at=now - timedelta(days=60),
            )
        )

    return insights


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

    **Note:** Currently returns example data. Real aggregation pipeline coming soon.
    """,
)
@handle_api_errors("get insights for user")
async def get_insights_for_user(
    insight_type: str | None = Query(
        None, description="Filter by type: trend, benchmark, best_practice"
    ),
    user: dict[str, Any] = Depends(get_current_user),
) -> IndustryInsightsResponse:
    """Get industry insights for the user's industry."""
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
            )

        # Get insights (currently stub data)
        insights = get_stub_insights(industry)

        # Filter by type if specified
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]

        return IndustryInsightsResponse(
            industry=industry,
            insights=insights,
            has_benchmarks=any(i.insight_type == "benchmark" for i in insights),
        )

    except (DatabaseError, OperationalError) as e:
        logger.error(f"Database error getting insights: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error while retrieving insights",
        ) from e
    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error getting insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get insights: {str(e)}",
        ) from e


@router.get(
    "/v1/industry-insights/{industry}",
    response_model=IndustryInsightsResponse,
    summary="Get insights for specific industry",
    description="""
    Retrieve aggregated industry insights for a specific industry.

    Returns benchmarks, trends, and best practices for the specified industry.

    **Note:** Currently returns example data. Real aggregation pipeline coming soon.
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
        # Get insights (currently stub data)
        insights = get_stub_insights(industry)

        # Filter by type if specified
        if insight_type:
            insights = [i for i in insights if i.insight_type == insight_type]

        return IndustryInsightsResponse(
            industry=industry,
            insights=insights,
            has_benchmarks=any(i.insight_type == "benchmark" for i in insights),
        )

    except asyncio.CancelledError:
        raise  # Always re-raise CancelledError
    except Exception as e:
        logger.error(f"Unexpected error getting insights for {industry}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get insights: {str(e)}",
        ) from e
