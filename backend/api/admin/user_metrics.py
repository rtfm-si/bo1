"""Admin API endpoints for user and usage metrics.

Provides:
- GET /api/admin/metrics/users - User signup and active user stats
- GET /api/admin/metrics/usage - Meeting and action usage stats
- GET /api/admin/metrics/onboarding - Onboarding funnel metrics
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from backend.services import onboarding_analytics, user_analytics
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/metrics", tags=["Admin - User Metrics"])


# =============================================================================
# Response Models
# =============================================================================


class DailyCount(BaseModel):
    """Daily count data point."""

    date: date
    count: int


class UserMetricsResponse(BaseModel):
    """User signup and activity metrics."""

    # Totals
    total_users: int
    new_users_today: int
    new_users_7d: int
    new_users_30d: int

    # Active users
    dau: int  # Daily active users
    wau: int  # Weekly active users
    mau: int  # Monthly active users

    # Daily breakdowns
    daily_signups: list[DailyCount]
    daily_active: list[DailyCount]


class UsageMetricsResponse(BaseModel):
    """Platform usage metrics."""

    # Meeting totals
    total_meetings: int
    meetings_today: int
    meetings_7d: int
    meetings_30d: int

    # Action totals
    total_actions: int
    actions_created_7d: int

    # Daily breakdowns
    daily_meetings: list[DailyCount]
    daily_actions: list[DailyCount]

    # Extended KPIs
    mentor_sessions_count: int = 0
    data_analyses_count: int = 0
    projects_count: int = 0
    actions_started_count: int = 0
    actions_completed_count: int = 0
    actions_cancelled_count: int = 0


class FunnelStageResponse(BaseModel):
    """Single funnel stage."""

    name: str
    count: int
    conversion_rate: float  # Percentage 0-100


class CohortResponse(BaseModel):
    """Cohort funnel metrics."""

    period_days: int
    signups: int
    context_completed: int
    first_meeting: int
    meeting_completed: int


class OnboardingFunnelResponse(BaseModel):
    """Onboarding funnel metrics."""

    # Totals
    total_signups: int
    context_completed: int
    first_meeting: int
    meeting_completed: int

    # Conversion rates (percentages 0-100)
    signup_to_context: float
    context_to_meeting: float
    meeting_to_complete: float
    overall_conversion: float

    # Funnel stages for visualization
    stages: list[FunnelStageResponse]

    # Time cohorts
    cohort_7d: CohortResponse
    cohort_30d: CohortResponse


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/users",
    summary="Get user metrics",
    description="""
    Get user signup and activity metrics.

    Returns:
    - Total users and new signups (today, 7d, 30d)
    - Active user counts (DAU, WAU, MAU)
    - Daily breakdown of signups and active users

    Use the `days` parameter to control the daily breakdown period (max 90 days).
    """,
    responses={
        200: {"description": "User metrics retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get user metrics")
async def get_user_metrics(
    days: int = Query(default=30, ge=1, le=90, description="Days for daily breakdown"),
    _admin: str = Depends(require_admin_any),
) -> UserMetricsResponse:
    """Get user signup and activity metrics (admin only)."""
    signup_stats = user_analytics.get_signup_stats(days)
    active_stats = user_analytics.get_active_user_stats(days)

    return UserMetricsResponse(
        total_users=signup_stats.total_users,
        new_users_today=signup_stats.new_users_today,
        new_users_7d=signup_stats.new_users_7d,
        new_users_30d=signup_stats.new_users_30d,
        dau=active_stats.dau,
        wau=active_stats.wau,
        mau=active_stats.mau,
        daily_signups=[DailyCount(date=d, count=c) for d, c in signup_stats.daily_signups],
        daily_active=[DailyCount(date=d, count=c) for d, c in active_stats.daily_active],
    )


@router.get(
    "/usage",
    summary="Get usage metrics",
    description="""
    Get platform usage metrics (meetings, actions).

    Returns:
    - Total meetings and actions
    - Meeting counts (today, 7d, 30d)
    - Actions created in last 7 days
    - Daily breakdown of meetings and actions

    Use the `days` parameter to control the daily breakdown period (max 90 days).
    """,
    responses={
        200: {"description": "Usage metrics retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get usage metrics")
async def get_usage_metrics(
    request: Request,
    days: int = Query(default=30, ge=1, le=90, description="Days for daily breakdown"),
    _admin: str = Depends(require_admin_any),
) -> UsageMetricsResponse:
    """Get platform usage metrics (admin only)."""
    usage_stats = user_analytics.get_usage_stats(days)

    return UsageMetricsResponse(
        total_meetings=usage_stats.total_meetings,
        meetings_today=usage_stats.meetings_today,
        meetings_7d=usage_stats.meetings_7d,
        meetings_30d=usage_stats.meetings_30d,
        total_actions=usage_stats.total_actions,
        actions_created_7d=usage_stats.actions_created_7d,
        daily_meetings=[DailyCount(date=d, count=c) for d, c in usage_stats.daily_meetings],
        daily_actions=[DailyCount(date=d, count=c) for d, c in usage_stats.daily_actions],
        mentor_sessions_count=usage_stats.mentor_sessions_count,
        data_analyses_count=usage_stats.data_analyses_count,
        projects_count=usage_stats.projects_count,
        actions_started_count=usage_stats.actions_started_count,
        actions_completed_count=usage_stats.actions_completed_count,
        actions_cancelled_count=usage_stats.actions_cancelled_count,
    )


@router.get(
    "/onboarding",
    summary="Get onboarding funnel metrics",
    description="""
    Get onboarding funnel metrics.

    Tracks user progression through:
    1. Signup - Account created
    2. Context Setup - Business context completed
    3. First Meeting - Started their first meeting
    4. Meeting Completed - Finished at least one meeting

    Returns conversion rates between each stage and cohort data for 7d and 30d.
    """,
    responses={
        200: {"description": "Onboarding metrics retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get onboarding metrics")
async def get_onboarding_metrics(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> OnboardingFunnelResponse:
    """Get onboarding funnel metrics (admin only)."""
    funnel = onboarding_analytics.get_funnel_metrics()
    stages = onboarding_analytics.get_funnel_stages()

    return OnboardingFunnelResponse(
        total_signups=funnel.total_signups,
        context_completed=funnel.context_completed,
        first_meeting=funnel.first_meeting,
        meeting_completed=funnel.meeting_completed,
        signup_to_context=funnel.signup_to_context,
        context_to_meeting=funnel.context_to_meeting,
        meeting_to_complete=funnel.meeting_to_complete,
        overall_conversion=funnel.overall_conversion,
        stages=[
            FunnelStageResponse(
                name=s.name,
                count=s.count,
                conversion_rate=s.conversion_rate,
            )
            for s in stages
        ],
        cohort_7d=CohortResponse(
            period_days=funnel.cohort_7d.period_days,
            signups=funnel.cohort_7d.signups,
            context_completed=funnel.cohort_7d.context_completed,
            first_meeting=funnel.cohort_7d.first_meeting,
            meeting_completed=funnel.cohort_7d.meeting_completed,
        ),
        cohort_30d=CohortResponse(
            period_days=funnel.cohort_30d.period_days,
            signups=funnel.cohort_30d.signups,
            context_completed=funnel.cohort_30d.context_completed,
            first_meeting=funnel.cohort_30d.first_meeting,
            meeting_completed=funnel.cohort_30d.meeting_completed,
        ),
    )
