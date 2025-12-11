"""User cost tracking service for admin monitoring.

Provides:
- Recording session costs to monthly aggregates
- Checking cost thresholds (for abuse detection)
- Getting user cost history

All data is admin-only - never exposed to end users.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


def get_default_limit_for_tier(tier: str | None) -> int | None:
    """Get the default internal cost limit for a subscription tier.

    Args:
        tier: Subscription tier (free, starter, pro)

    Returns:
        Default limit in cents, or None if no limit
    """
    try:
        from bo1.config import get_settings

        settings = get_settings()
        tier_lower = (tier or "free").lower()

        if tier_lower == "pro":
            return settings.cost_limit_pro_cents
        elif tier_lower == "starter":
            return settings.cost_limit_starter_cents
        else:
            return settings.cost_limit_free_cents
    except Exception:
        # Fallback defaults
        return {"pro": 10000, "starter": 2500}.get((tier or "").lower(), 500)


class BudgetStatus(str, Enum):
    """Budget status levels."""

    UNDER = "under"
    WARNING = "warning"
    EXCEEDED = "exceeded"


@dataclass
class UserCostPeriod:
    """Cost totals for a user's billing period."""

    user_id: str
    period_start: date
    period_end: date
    total_cost_cents: int
    session_count: int


@dataclass
class UserBudgetSettings:
    """Budget settings for a user (admin-configured)."""

    user_id: str
    monthly_cost_limit_cents: int | None
    alert_threshold_pct: int
    hard_limit_enabled: bool
    alert_sent_at: datetime | None


@dataclass
class BudgetCheckResult:
    """Result of checking a user's budget status."""

    user_id: str
    status: BudgetStatus
    current_cost_cents: int
    limit_cents: int | None
    percentage_used: float | None
    should_alert: bool
    should_block: bool


def get_current_period_bounds() -> tuple[date, date]:
    """Get current month's start and end dates.

    Returns:
        Tuple of (period_start, period_end)
    """
    today = date.today()
    period_start = today.replace(day=1)
    # End is last day of month
    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)
    from datetime import timedelta

    period_end = next_month - timedelta(days=1)
    return period_start, period_end


def record_session_cost(
    user_id: str,
    session_id: str,
    cost_cents: int,
    default_limit_cents: int | None = None,
) -> tuple[UserCostPeriod, BudgetCheckResult | None]:
    """Record a session's cost to the user's current period aggregate.

    Args:
        user_id: User who owns the session
        session_id: Session ID (for logging)
        cost_cents: Cost in cents to add
        default_limit_cents: Default limit for budget check (optional)

    Returns:
        Tuple of (Updated UserCostPeriod, BudgetCheckResult if threshold crossed)
    """
    period_start, period_end = get_current_period_bounds()

    with db_session() as conn:
        with conn.cursor() as cur:
            # Upsert: create or update period aggregate
            cur.execute(
                """
                INSERT INTO user_cost_periods (
                    user_id, period_start, period_end, total_cost_cents, session_count
                )
                VALUES (%s, %s, %s, %s, 1)
                ON CONFLICT (user_id, period_start) DO UPDATE
                SET total_cost_cents = user_cost_periods.total_cost_cents + EXCLUDED.total_cost_cents,
                    session_count = user_cost_periods.session_count + 1,
                    updated_at = NOW()
                RETURNING user_id, period_start, period_end, total_cost_cents, session_count
                """,
                (user_id, period_start, period_end, cost_cents),
            )
            row = cur.fetchone()

            logger.info(
                "Recorded session cost",
                extra={
                    "user_id": user_id,
                    "session_id": session_id,
                    "cost_cents": cost_cents,
                    "period_total_cents": row["total_cost_cents"],
                },
            )

            period = UserCostPeriod(
                user_id=row["user_id"],
                period_start=row["period_start"],
                period_end=row["period_end"],
                total_cost_cents=row["total_cost_cents"],
                session_count=row["session_count"],
            )

    # Check if threshold crossed (for alerting)
    budget_result = check_budget_status(user_id, default_limit_cents)
    if budget_result.should_alert:
        return period, budget_result

    return period, None


def get_user_period_cost(
    user_id: str,
    period_start: date | None = None,
) -> UserCostPeriod | None:
    """Get a user's cost for a specific period.

    Args:
        user_id: User ID to query
        period_start: Start of period (default: current month)

    Returns:
        UserCostPeriod or None if no data
    """
    if period_start is None:
        period_start, _ = get_current_period_bounds()

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, period_start, period_end, total_cost_cents, session_count
                FROM user_cost_periods
                WHERE user_id = %s AND period_start = %s
                """,
                (user_id, period_start),
            )
            row = cur.fetchone()

            if not row:
                return None

            return UserCostPeriod(
                user_id=row["user_id"],
                period_start=row["period_start"],
                period_end=row["period_end"],
                total_cost_cents=row["total_cost_cents"],
                session_count=row["session_count"],
            )


def get_user_budget_settings(user_id: str) -> UserBudgetSettings | None:
    """Get budget settings for a user.

    Args:
        user_id: User ID

    Returns:
        UserBudgetSettings or None if not configured
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, monthly_cost_limit_cents, alert_threshold_pct,
                       hard_limit_enabled, alert_sent_at
                FROM user_budget_settings
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()

            if not row:
                return None

            return UserBudgetSettings(
                user_id=row["user_id"],
                monthly_cost_limit_cents=row["monthly_cost_limit_cents"],
                alert_threshold_pct=row["alert_threshold_pct"],
                hard_limit_enabled=row["hard_limit_enabled"],
                alert_sent_at=row["alert_sent_at"],
            )


def set_user_budget_settings(
    user_id: str,
    monthly_cost_limit_cents: int | None = None,
    alert_threshold_pct: int | None = None,
    hard_limit_enabled: bool | None = None,
) -> UserBudgetSettings:
    """Set or update budget settings for a user (admin only).

    Args:
        user_id: User ID
        monthly_cost_limit_cents: Monthly limit in cents (None = unlimited)
        alert_threshold_pct: Percentage at which to alert (default 80)
        hard_limit_enabled: Whether to block when limit exceeded

    Returns:
        Updated UserBudgetSettings
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Build update fields
            fields = []
            params: list[Any] = []

            if monthly_cost_limit_cents is not None:
                fields.append("monthly_cost_limit_cents = %s")
                params.append(monthly_cost_limit_cents)
            if alert_threshold_pct is not None:
                fields.append("alert_threshold_pct = %s")
                params.append(alert_threshold_pct)
            if hard_limit_enabled is not None:
                fields.append("hard_limit_enabled = %s")
                params.append(hard_limit_enabled)

            if fields:
                fields.append("updated_at = NOW()")
                set_clause = ", ".join(fields)

                cur.execute(
                    f"""
                    INSERT INTO user_budget_settings (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO UPDATE
                    SET {set_clause}
                    RETURNING user_id, monthly_cost_limit_cents, alert_threshold_pct,
                              hard_limit_enabled, alert_sent_at
                    """,
                    [user_id, *params],
                )
            else:
                # Just ensure record exists
                cur.execute(
                    """
                    INSERT INTO user_budget_settings (user_id)
                    VALUES (%s)
                    ON CONFLICT (user_id) DO NOTHING
                    RETURNING user_id, monthly_cost_limit_cents, alert_threshold_pct,
                              hard_limit_enabled, alert_sent_at
                    """,
                    (user_id,),
                )

            row = cur.fetchone()
            if not row:
                # Re-fetch if DO NOTHING triggered
                cur.execute(
                    """
                    SELECT user_id, monthly_cost_limit_cents, alert_threshold_pct,
                           hard_limit_enabled, alert_sent_at
                    FROM user_budget_settings WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

            return UserBudgetSettings(
                user_id=row["user_id"],
                monthly_cost_limit_cents=row["monthly_cost_limit_cents"],
                alert_threshold_pct=row["alert_threshold_pct"],
                hard_limit_enabled=row["hard_limit_enabled"],
                alert_sent_at=row["alert_sent_at"],
            )


def mark_alert_sent(user_id: str) -> None:
    """Mark that an alert was sent for this user's current period.

    Args:
        user_id: User ID
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_budget_settings
                SET alert_sent_at = NOW(), updated_at = NOW()
                WHERE user_id = %s
                """,
                (user_id,),
            )


def check_budget_status(
    user_id: str,
    default_limit_cents: int | None = None,
) -> BudgetCheckResult:
    """Check a user's current budget status.

    Args:
        user_id: User ID
        default_limit_cents: Default limit if no user-specific settings

    Returns:
        BudgetCheckResult with status and flags
    """
    # Get current period cost
    period = get_user_period_cost(user_id)
    current_cost = period.total_cost_cents if period else 0

    # Get budget settings
    settings = get_user_budget_settings(user_id)
    limit_cents = (settings.monthly_cost_limit_cents if settings else None) or default_limit_cents
    alert_threshold = settings.alert_threshold_pct if settings else 80
    hard_limit = settings.hard_limit_enabled if settings else False
    alert_sent_at = settings.alert_sent_at if settings else None

    # Determine status
    if limit_cents is None:
        # No limit configured
        return BudgetCheckResult(
            user_id=user_id,
            status=BudgetStatus.UNDER,
            current_cost_cents=current_cost,
            limit_cents=None,
            percentage_used=None,
            should_alert=False,
            should_block=False,
        )

    percentage = (current_cost / limit_cents) * 100 if limit_cents > 0 else 0

    if percentage >= 100:
        status = BudgetStatus.EXCEEDED
    elif percentage >= alert_threshold:
        status = BudgetStatus.WARNING
    else:
        status = BudgetStatus.UNDER

    # Determine if we should alert (only if not already alerted this period)
    period_start, _ = get_current_period_bounds()
    already_alerted = alert_sent_at is not None and alert_sent_at.date() >= period_start
    should_alert = status in (BudgetStatus.WARNING, BudgetStatus.EXCEEDED) and not already_alerted

    # Determine if we should block
    should_block = status == BudgetStatus.EXCEEDED and hard_limit

    return BudgetCheckResult(
        user_id=user_id,
        status=status,
        current_cost_cents=current_cost,
        limit_cents=limit_cents,
        percentage_used=percentage,
        should_alert=should_alert,
        should_block=should_block,
    )


def get_top_users_by_cost(
    period_start: date | None = None,
    limit: int = 20,
) -> list[UserCostPeriod]:
    """Get users ranked by cost for abuse detection.

    Args:
        period_start: Period to query (default: current month)
        limit: Max users to return

    Returns:
        List of UserCostPeriod sorted by cost descending
    """
    if period_start is None:
        period_start, _ = get_current_period_bounds()

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, period_start, period_end, total_cost_cents, session_count
                FROM user_cost_periods
                WHERE period_start = %s
                ORDER BY total_cost_cents DESC
                LIMIT %s
                """,
                (period_start, limit),
            )

            return [
                UserCostPeriod(
                    user_id=row["user_id"],
                    period_start=row["period_start"],
                    period_end=row["period_end"],
                    total_cost_cents=row["total_cost_cents"],
                    session_count=row["session_count"],
                )
                for row in cur.fetchall()
            ]


def get_user_cost_history(
    user_id: str,
    months: int = 6,
) -> list[UserCostPeriod]:
    """Get a user's cost history for the last N months.

    Args:
        user_id: User ID
        months: Number of months to include

    Returns:
        List of UserCostPeriod sorted by period descending
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, period_start, period_end, total_cost_cents, session_count
                FROM user_cost_periods
                WHERE user_id = %s
                ORDER BY period_start DESC
                LIMIT %s
                """,
                (user_id, months),
            )

            return [
                UserCostPeriod(
                    user_id=row["user_id"],
                    period_start=row["period_start"],
                    period_end=row["period_end"],
                    total_cost_cents=row["total_cost_cents"],
                    session_count=row["session_count"],
                )
                for row in cur.fetchall()
            ]
