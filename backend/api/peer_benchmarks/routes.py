"""Peer Benchmarking API endpoints.

Provides:
- GET /api/v1/peer-benchmarks/consent - Current consent status
- POST /api/v1/peer-benchmarks/consent - Opt in
- DELETE /api/v1/peer-benchmarks/consent - Opt out
- GET /api/v1/peer-benchmarks - Industry peer comparisons (tier-gated)
- GET /api/v1/peer-benchmarks/compare - User's percentile rank vs peers
"""

import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import PEER_BENCHMARKS_RATE_LIMIT, limiter
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import get_user_tier
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.industry_benchmark_researcher import IndustryBenchmarkResearcher
from backend.services.peer_benchmarks import (
    K_ANONYMITY_THRESHOLD,
    check_user_context,
    get_consent_status,
    get_peer_comparison,
    get_preview_metric,
    give_consent,
    revoke_consent,
)
from bo1.billing import PlanConfig
from bo1.logging import ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/peer-benchmarks", tags=["peer-benchmarks"])


# =============================================================================
# Models
# =============================================================================


class ConsentStatusResponse(BaseModel):
    """Consent status response."""

    consented: bool = Field(..., description="Whether user has active consent")
    consented_at: datetime | None = Field(None, description="When consent was given")
    revoked_at: datetime | None = Field(None, description="When consent was revoked")


class PeerMetric(BaseModel):
    """A single peer benchmark metric."""

    metric: str = Field(..., description="Metric identifier")
    display_name: str = Field(..., description="Human-readable metric name")
    p10: float | None = Field(None, description="10th percentile")
    p25: float | None = Field(None, description="25th percentile")
    p50: float | None = Field(None, description="50th percentile (median)")
    p75: float | None = Field(None, description="75th percentile")
    p90: float | None = Field(None, description="90th percentile")
    sample_count: int = Field(..., description="Number of data points")
    user_value: float | None = Field(None, description="User's current value")
    user_percentile: float | None = Field(None, description="User's percentile rank (0-100)")
    locked: bool = Field(False, description="Whether metric is tier-locked")


class PeerBenchmarksResponse(BaseModel):
    """Response containing peer benchmark data."""

    industry: str = Field(..., description="Industry segment")
    metrics: list[PeerMetric] = Field(default_factory=list, description="Benchmark metrics")
    updated_at: datetime | None = Field(None, description="When aggregates were last updated")
    k_anonymity_threshold: int = Field(
        K_ANONYMITY_THRESHOLD, description="Minimum sample size for data"
    )
    # New fields for research-based benchmarks
    source: Literal["peer_data", "industry_research", "similar_industry"] = Field(
        "peer_data", description="Data source type"
    )
    sources: list[str] | None = Field(None, description="Citation URLs for research data")
    confidence: float | None = Field(None, description="Confidence score (0-1) for research data")
    similar_industry: str | None = Field(
        None, description="If source is similar_industry, the matched industry"
    )


class ComparisonMetric(BaseModel):
    """User's comparison for a single metric."""

    metric: str = Field(..., description="Metric identifier")
    display_name: str = Field(..., description="Human-readable metric name")
    user_value: float | None = Field(None, description="User's value")
    user_percentile: float | None = Field(None, description="Percentile rank (0-100)")
    p50: float | None = Field(None, description="Industry median for context")
    sample_count: int = Field(..., description="Sample size")


class ComparisonResponse(BaseModel):
    """Response containing user's peer comparison."""

    industry: str = Field(..., description="Industry segment")
    comparisons: list[ComparisonMetric] = Field(
        default_factory=list, description="Metric comparisons"
    )


class PreviewMetricResponse(BaseModel):
    """Preview metric for non-opted users (shows industry median only)."""

    metric: str = Field(..., description="Metric identifier")
    display_name: str = Field(..., description="Human-readable metric name")
    industry: str = Field(..., description="Industry segment")
    p50: float = Field(..., description="Industry median value")
    sample_count: int = Field(..., description="Number of peers contributing")


# =============================================================================
# Consent Endpoints
# =============================================================================


@router.get("/consent", response_model=ConsentStatusResponse)
@handle_api_errors("get benchmark consent")
@limiter.limit(PEER_BENCHMARKS_RATE_LIMIT)
async def get_consent(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Get user's current peer benchmark consent status."""
    user_id = extract_user_id(current_user)

    status = get_consent_status(user_id)

    return ConsentStatusResponse(
        consented=status.consented,
        consented_at=status.consented_at,
        revoked_at=status.revoked_at,
    )


@router.post("/consent", response_model=ConsentStatusResponse)
@handle_api_errors("opt in benchmarks")
@limiter.limit(PEER_BENCHMARKS_RATE_LIMIT)
async def opt_in(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Opt in to peer benchmarking.

    User's anonymized metrics will be included in industry aggregates.
    """
    user_id = extract_user_id(current_user)

    status = give_consent(user_id)

    logger.info("peer_benchmark_consent_given", extra={"user_id": user_id})

    return ConsentStatusResponse(
        consented=status.consented,
        consented_at=status.consented_at,
        revoked_at=status.revoked_at,
    )


@router.delete("/consent", response_model=ConsentStatusResponse)
@handle_api_errors("opt out benchmarks")
@limiter.limit(PEER_BENCHMARKS_RATE_LIMIT)
async def opt_out(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ConsentStatusResponse:
    """Opt out of peer benchmarking.

    User's data is immediately excluded from future aggregations.
    """
    user_id = extract_user_id(current_user)

    status = revoke_consent(user_id)

    logger.info("peer_benchmark_consent_revoked", extra={"user_id": user_id})

    return ConsentStatusResponse(
        consented=status.consented,
        consented_at=status.consented_at,
        revoked_at=status.revoked_at,
    )


# =============================================================================
# Preview Endpoint (No Consent Required)
# =============================================================================


@router.get("/preview", response_model=PreviewMetricResponse)
@handle_api_errors("get benchmark preview")
@limiter.limit(PEER_BENCHMARKS_RATE_LIMIT)
async def get_preview(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> PreviewMetricResponse:
    """Get a sample benchmark metric preview.

    Returns one industry median metric (no user data) to show the value
    of opting in. Does not require consent.
    """
    user_id = extract_user_id(current_user)

    # Check user context status for specific error messages
    context_status = check_user_context(user_id)
    if not context_status.has_context:
        raise http_error(
            ErrorCode.API_CONTEXT_MISSING,
            "No business context found. Please set up your business context first.",
            status=404,
        )
    if not context_status.has_industry:
        raise http_error(
            ErrorCode.API_INDUSTRY_NOT_SET,
            "No industry selected. Please select an industry in your business context.",
            status=404,
        )

    result = get_preview_metric(user_id)

    if not result:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "No peer benchmark data available for your industry yet. "
            "As more users opt in, preview data will become available.",
            status=404,
        )

    return PreviewMetricResponse(
        metric=result["metric"],
        display_name=result["display_name"],
        industry=result["industry"],
        p50=result["p50"],
        sample_count=result["sample_count"],
    )


# =============================================================================
# Benchmark Data Endpoints
# =============================================================================


@router.get("", response_model=PeerBenchmarksResponse)
@handle_api_errors("get peer benchmarks")
@limiter.limit(PEER_BENCHMARKS_RATE_LIMIT)
async def get_benchmarks(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> PeerBenchmarksResponse:
    """Get industry peer benchmarks for user's industry.

    Returns percentile data (p10/p25/p50/p75/p90) for each metric.
    Metrics are tier-gated: free=3, starter=5, pro=unlimited.

    Falls back to research-based benchmarks if no peer data available.
    """
    user_id = extract_user_id(current_user)
    tier = get_user_tier(user_id)

    # Check user context status for specific error messages
    context_status = check_user_context(user_id)
    if not context_status.has_context:
        raise http_error(
            ErrorCode.API_CONTEXT_MISSING,
            "No business context found. Please set up your business context first.",
            status=404,
        )
    if not context_status.has_industry:
        raise http_error(
            ErrorCode.API_INDUSTRY_NOT_SET,
            "No industry selected. Please select an industry in your business context.",
            status=404,
        )

    # Get peer benchmark limit for this tier
    tier_config = PlanConfig.get_tier(tier)
    benchmark_limit = tier_config.peer_benchmarks_visible

    # Step 1: Try peer data first
    result = get_peer_comparison(user_id)
    has_peer_data = result and any(m.p50 is not None for m in result.metrics)

    if has_peer_data:
        # Apply tier gating to peer data
        metrics: list[PeerMetric] = []
        for i, m in enumerate(result.metrics):
            is_locked = benchmark_limit != -1 and i >= benchmark_limit

            metrics.append(
                PeerMetric(
                    metric=m.metric,
                    display_name=m.display_name,
                    p10=None if is_locked else m.p10,
                    p25=None if is_locked else m.p25,
                    p50=None if is_locked else m.p50,
                    p75=None if is_locked else m.p75,
                    p90=None if is_locked else m.p90,
                    sample_count=m.sample_count,
                    user_value=None if is_locked else m.user_value,
                    user_percentile=None if is_locked else m.user_percentile,
                    locked=is_locked,
                )
            )

        return PeerBenchmarksResponse(
            industry=result.industry,
            metrics=metrics,
            updated_at=result.updated_at,
            k_anonymity_threshold=K_ANONYMITY_THRESHOLD,
            source="peer_data",
        )

    # Step 2: Fallback to research-based benchmarks
    logger.info(f"No peer data for {context_status.industry}, trying research fallback")
    researcher = IndustryBenchmarkResearcher()

    research_result = await researcher.get_or_research_benchmarks(context_status.industry)

    if research_result and research_result.metrics:
        # Convert research metrics to API format
        metrics = []
        for i, m in enumerate(research_result.metrics):
            is_locked = benchmark_limit != -1 and i >= benchmark_limit

            metrics.append(
                PeerMetric(
                    metric=m.metric,
                    display_name=m.display_name,
                    p10=None,  # Research data typically doesn't have p10/p90
                    p25=None if is_locked else m.p25,
                    p50=None if is_locked else m.p50,
                    p75=None if is_locked else m.p75,
                    p90=None,
                    sample_count=0,  # No sample count for research data
                    user_value=None,  # No user comparison for research data
                    user_percentile=None,
                    locked=is_locked,
                )
            )

        return PeerBenchmarksResponse(
            industry=research_result.industry,
            metrics=metrics,
            updated_at=research_result.generated_at,
            k_anonymity_threshold=0,  # Not peer-based
            source="industry_research",
            sources=research_result.sources,
            confidence=research_result.confidence,
        )

    # Step 3: Fallback to similar industry via embeddings
    logger.info(f"No research data for {context_status.industry}, trying similar industry")
    similar_result = await researcher.find_similar_industry(context_status.industry)

    if similar_result and similar_result.metrics:
        metrics = []
        for i, m in enumerate(similar_result.metrics):
            is_locked = benchmark_limit != -1 and i >= benchmark_limit

            metrics.append(
                PeerMetric(
                    metric=m.metric,
                    display_name=m.display_name,
                    p10=None,
                    p25=None if is_locked else m.p25,
                    p50=None if is_locked else m.p50,
                    p75=None if is_locked else m.p75,
                    p90=None,
                    sample_count=0,
                    user_value=None,
                    user_percentile=None,
                    locked=is_locked,
                )
            )

        return PeerBenchmarksResponse(
            industry=similar_result.industry,
            metrics=metrics,
            updated_at=similar_result.generated_at,
            k_anonymity_threshold=0,
            source="similar_industry",
            sources=similar_result.sources,
            confidence=similar_result.confidence,
            similar_industry=similar_result.similar_industry,
        )

    # No data available from any source
    raise http_error(
        ErrorCode.API_NOT_FOUND,
        "No benchmark data available for your industry yet. "
        "Try again later as we research industry benchmarks.",
        status=404,
    )


@router.get("/compare", response_model=ComparisonResponse)
@handle_api_errors("get peer comparison")
@limiter.limit(PEER_BENCHMARKS_RATE_LIMIT)
async def get_comparison(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> ComparisonResponse:
    """Get user's percentile rank vs peers for each metric.

    Only includes metrics where user has a value and sufficient peer data.
    """
    user_id = extract_user_id(current_user)
    tier = get_user_tier(user_id)

    # Check user context status for specific error messages
    context_status = check_user_context(user_id)
    if not context_status.has_context:
        raise http_error(
            ErrorCode.API_CONTEXT_MISSING,
            "No business context found. Please set up your business context first.",
            status=404,
        )
    if not context_status.has_industry:
        raise http_error(
            ErrorCode.API_INDUSTRY_NOT_SET,
            "No industry selected. Please select an industry in your business context.",
            status=404,
        )

    # Get peer benchmark limit for this tier
    tier_config = PlanConfig.get_tier(tier)
    benchmark_limit = tier_config.peer_benchmarks_visible

    result = get_peer_comparison(user_id)

    if not result:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            "No peer benchmark data available for your industry yet. "
            "As more users in your industry opt in, comparison data will become available.",
            status=404,
        )

    # Filter to metrics with user values and apply tier gating
    comparisons: list[ComparisonMetric] = []
    visible_count = 0

    for m in result.metrics:
        # Skip if user has no value
        if m.user_value is None:
            continue

        # Apply tier gating
        if benchmark_limit != -1 and visible_count >= benchmark_limit:
            break

        comparisons.append(
            ComparisonMetric(
                metric=m.metric,
                display_name=m.display_name,
                user_value=m.user_value,
                user_percentile=m.user_percentile,
                p50=m.p50,
                sample_count=m.sample_count,
            )
        )
        visible_count += 1

    return ComparisonResponse(
        industry=result.industry,
        comparisons=comparisons,
    )
