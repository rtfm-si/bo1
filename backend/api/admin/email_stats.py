"""Admin email statistics endpoints.

Provides:
- Total email counts by type and period
- Email delivery stats for admin dashboard
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-stats", tags=["admin-email"])


# ==============================================================================
# Models
# ==============================================================================


class EmailTypeCount(BaseModel):
    """Count for a specific email type."""

    email_type: str
    count: int


class EmailPeriodCounts(BaseModel):
    """Counts for different time periods."""

    today: int
    week: int
    month: int


class EmailRates(BaseModel):
    """Email engagement rates."""

    open_rate: float
    click_rate: float
    failed_rate: float


class EmailEventCounts(BaseModel):
    """Email event counts for rate calculation."""

    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    failed_count: int


class EmailStatsResponse(BaseModel):
    """Email statistics response."""

    total: int
    by_type: dict[str, int]
    by_period: EmailPeriodCounts
    # New fields for engagement metrics
    rates: EmailRates
    event_counts: EmailEventCounts
    by_type_rates: dict[str, EmailRates]


# ==============================================================================
# Endpoints
# ==============================================================================


def _calculate_rate(numerator: int, denominator: int) -> float:
    """Calculate rate, handling division by zero."""
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


@router.get(
    "",
    response_model=EmailStatsResponse,
    summary="Email statistics",
    description="Get email send counts by type and time period (admin only).",
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get email stats")
async def get_email_stats(
    request: Request,
    _admin: dict = Depends(require_admin_any),
    days: int = Query(30, ge=1, le=365, description="Max days for 'month' period"),
) -> EmailStatsResponse:
    """Get email send statistics."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Total and by type (last N days)
            cur.execute(
                """
                SELECT
                    email_type,
                    COUNT(*) as count
                FROM email_log
                WHERE created_at >= %s AND status = 'sent'
                GROUP BY email_type
                ORDER BY count DESC
                """,
                (month_ago,),
            )
            type_rows = cur.fetchall()

            # Today count
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM email_log
                WHERE DATE(created_at) = %s AND status = 'sent'
                """,
                (today,),
            )
            today_count = cur.fetchone()["count"]

            # Week count
            cur.execute(
                """
                SELECT COUNT(*) as count
                FROM email_log
                WHERE created_at >= %s AND status = 'sent'
                """,
                (week_ago,),
            )
            week_count = cur.fetchone()["count"]

            # Event counts for rates (overall)
            cur.execute(
                """
                SELECT
                    COUNT(*) as sent_count,
                    COUNT(delivered_at) as delivered_count,
                    COUNT(opened_at) as opened_count,
                    COUNT(clicked_at) as clicked_count,
                    COUNT(bounced_at) as bounced_count,
                    COUNT(failed_at) as failed_count
                FROM email_log
                WHERE created_at >= %s AND status = 'sent'
                """,
                (month_ago,),
            )
            event_row = cur.fetchone()

            # Event counts by email type for per-type rates
            cur.execute(
                """
                SELECT
                    email_type,
                    COUNT(*) as sent_count,
                    COUNT(delivered_at) as delivered_count,
                    COUNT(opened_at) as opened_count,
                    COUNT(clicked_at) as clicked_count,
                    COUNT(bounced_at) as bounced_count,
                    COUNT(failed_at) as failed_count
                FROM email_log
                WHERE created_at >= %s AND status = 'sent'
                GROUP BY email_type
                """,
                (month_ago,),
            )
            type_event_rows = cur.fetchall()

    by_type = {row["email_type"]: row["count"] for row in type_rows}
    total = sum(by_type.values())
    month_count = total  # Already filtered by month_ago

    # Calculate overall event counts
    event_counts = EmailEventCounts(
        sent_count=event_row["sent_count"],
        delivered_count=event_row["delivered_count"],
        opened_count=event_row["opened_count"],
        clicked_count=event_row["clicked_count"],
        bounced_count=event_row["bounced_count"],
        failed_count=event_row["failed_count"],
    )

    # Calculate overall rates
    # Use delivered_count as denominator if available, else sent_count
    rate_denominator = event_counts.delivered_count or event_counts.sent_count
    rates = EmailRates(
        open_rate=_calculate_rate(event_counts.opened_count, rate_denominator),
        click_rate=_calculate_rate(event_counts.clicked_count, rate_denominator),
        failed_rate=_calculate_rate(
            event_counts.bounced_count + event_counts.failed_count, event_counts.sent_count
        ),
    )

    # Calculate per-type rates
    by_type_rates: dict[str, EmailRates] = {}
    for row in type_event_rows:
        email_type = row["email_type"]
        delivered = row["delivered_count"]
        sent = row["sent_count"]
        denom = delivered or sent
        by_type_rates[email_type] = EmailRates(
            open_rate=_calculate_rate(row["opened_count"], denom),
            click_rate=_calculate_rate(row["clicked_count"], denom),
            failed_rate=_calculate_rate(row["bounced_count"] + row["failed_count"], sent),
        )

    return EmailStatsResponse(
        total=total,
        by_type=by_type,
        by_period=EmailPeriodCounts(
            today=today_count,
            week=week_count,
            month=month_count,
        ),
        rates=rates,
        event_counts=event_counts,
        by_type_rates=by_type_rates,
    )
