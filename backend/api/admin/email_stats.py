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


class EmailStatsResponse(BaseModel):
    """Email statistics response."""

    total: int
    by_type: dict[str, int]
    by_period: EmailPeriodCounts


# ==============================================================================
# Endpoints
# ==============================================================================


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

    by_type = {row["email_type"]: row["count"] for row in type_rows}
    total = sum(by_type.values())
    month_count = total  # Already filtered by month_ago

    return EmailStatsResponse(
        total=total,
        by_type=by_type,
        by_period=EmailPeriodCounts(
            today=today_count,
            week=week_count,
            month=month_count,
        ),
    )
