"""Onboarding funnel analytics service.

Tracks user progression through the onboarding flow:
- Signup → Context setup → First meeting

Provides conversion rates and funnel metrics.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class FunnelStage:
    """Metrics for a single funnel stage."""

    name: str
    count: int
    conversion_rate: float  # Percentage from previous stage (0-100)


@dataclass
class OnboardingFunnel:
    """Complete onboarding funnel metrics."""

    total_signups: int
    context_completed: int  # Users who completed business context
    first_meeting: int  # Users who started their first meeting
    meeting_completed: int  # Users who completed their first meeting

    # Conversion rates (percentages 0-100)
    signup_to_context: float
    context_to_meeting: float
    meeting_to_complete: float
    overall_conversion: float  # Signup to meeting completed

    # Time-based cohort data
    cohort_7d: "OnboardingCohort"
    cohort_30d: "OnboardingCohort"


@dataclass
class OnboardingCohort:
    """Funnel metrics for a specific time cohort."""

    period_days: int
    signups: int
    context_completed: int
    first_meeting: int
    meeting_completed: int


def get_funnel_metrics() -> OnboardingFunnel:
    """Get complete onboarding funnel metrics.

    Stages tracked:
    1. Signup - user created in users table
    2. Context - user_context record with onboarding_completed=true
    3. First meeting - user has at least one session
    4. Meeting completed - user has at least one completed session

    Returns:
        OnboardingFunnel with counts and conversion rates
    """
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Total signups (all time)
            cur.execute("SELECT COUNT(*) as count FROM users")
            total_signups = cur.fetchone()["count"]

            # Users who completed context setup
            cur.execute(
                """
                SELECT COUNT(*) as count FROM user_context
                WHERE onboarding_completed = true
                """
            )
            context_completed = cur.fetchone()["count"]

            # Users who started at least one meeting
            cur.execute(
                """
                SELECT COUNT(DISTINCT user_id) as count FROM sessions
                """
            )
            first_meeting = cur.fetchone()["count"]

            # Users who completed at least one meeting
            cur.execute(
                """
                SELECT COUNT(DISTINCT user_id) as count FROM sessions
                WHERE status = 'completed'
                """
            )
            meeting_completed = cur.fetchone()["count"]

            # 7-day cohort
            cur.execute(
                "SELECT COUNT(*) as count FROM users WHERE created_at >= %s",
                (week_ago,),
            )
            cohort_7d_signups = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT COUNT(*) as count FROM user_context uc
                JOIN users u ON u.id = uc.user_id
                WHERE u.created_at >= %s AND uc.onboarding_completed = true
                """,
                (week_ago,),
            )
            cohort_7d_context = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT COUNT(DISTINCT s.user_id) as count FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE u.created_at >= %s
                """,
                (week_ago,),
            )
            cohort_7d_meeting = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT COUNT(DISTINCT s.user_id) as count FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE u.created_at >= %s AND s.status = 'completed'
                """,
                (week_ago,),
            )
            cohort_7d_completed = cur.fetchone()["count"]

            # 30-day cohort
            cur.execute(
                "SELECT COUNT(*) as count FROM users WHERE created_at >= %s",
                (month_ago,),
            )
            cohort_30d_signups = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT COUNT(*) as count FROM user_context uc
                JOIN users u ON u.id = uc.user_id
                WHERE u.created_at >= %s AND uc.onboarding_completed = true
                """,
                (month_ago,),
            )
            cohort_30d_context = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT COUNT(DISTINCT s.user_id) as count FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE u.created_at >= %s
                """,
                (month_ago,),
            )
            cohort_30d_meeting = cur.fetchone()["count"]

            cur.execute(
                """
                SELECT COUNT(DISTINCT s.user_id) as count FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE u.created_at >= %s AND s.status = 'completed'
                """,
                (month_ago,),
            )
            cohort_30d_completed = cur.fetchone()["count"]

    # Calculate conversion rates (prevent division by zero)
    def rate(numerator: int, denominator: int) -> float:
        if denominator == 0:
            return 0.0
        return round((numerator / denominator) * 100, 1)

    return OnboardingFunnel(
        total_signups=total_signups,
        context_completed=context_completed,
        first_meeting=first_meeting,
        meeting_completed=meeting_completed,
        signup_to_context=rate(context_completed, total_signups),
        context_to_meeting=rate(first_meeting, context_completed),
        meeting_to_complete=rate(meeting_completed, first_meeting),
        overall_conversion=rate(meeting_completed, total_signups),
        cohort_7d=OnboardingCohort(
            period_days=7,
            signups=cohort_7d_signups,
            context_completed=cohort_7d_context,
            first_meeting=cohort_7d_meeting,
            meeting_completed=cohort_7d_completed,
        ),
        cohort_30d=OnboardingCohort(
            period_days=30,
            signups=cohort_30d_signups,
            context_completed=cohort_30d_context,
            first_meeting=cohort_30d_meeting,
            meeting_completed=cohort_30d_completed,
        ),
    )


def get_funnel_stages() -> list[FunnelStage]:
    """Get funnel as a list of stages for visualization.

    Returns:
        List of FunnelStage objects in order
    """
    funnel = get_funnel_metrics()

    return [
        FunnelStage(
            name="Signups",
            count=funnel.total_signups,
            conversion_rate=100.0,
        ),
        FunnelStage(
            name="Context Setup",
            count=funnel.context_completed,
            conversion_rate=funnel.signup_to_context,
        ),
        FunnelStage(
            name="First Meeting",
            count=funnel.first_meeting,
            conversion_rate=funnel.context_to_meeting,
        ),
        FunnelStage(
            name="Meeting Completed",
            count=funnel.meeting_completed,
            conversion_rate=funnel.meeting_to_complete,
        ),
    ]
