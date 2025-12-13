"""Cost analytics service for aggregating session costs.

Provides cost aggregation by user, date range, and time period.
Used by admin endpoints and CLI cost reports.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class UserCost:
    """Cost summary for a single user."""

    user_id: str
    email: str | None
    total_cost: float
    session_count: int


@dataclass
class DailyCost:
    """Cost summary for a single day."""

    date: date
    total_cost: float
    session_count: int


@dataclass
class ModelCost:
    """Cost breakdown by model."""

    model: str
    total_cost: float
    api_calls: int


@dataclass
class CostSummary:
    """Cost totals for different time periods."""

    today: float = 0.0
    this_week: float = 0.0
    this_month: float = 0.0
    all_time: float = 0.0
    session_count_today: int = 0
    session_count_week: int = 0
    session_count_month: int = 0
    session_count_total: int = 0


@dataclass
class CostReport:
    """Full cost report with breakdowns."""

    summary: CostSummary
    by_user: list[UserCost] = field(default_factory=list)
    by_day: list[DailyCost] = field(default_factory=list)
    by_model: list[ModelCost] = field(default_factory=list)


def get_cost_summary() -> CostSummary:
    """Get cost totals for today, this week, this month, and all time.

    Returns:
        CostSummary with aggregated cost totals.
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Get all-time totals
            cur.execute(
                """
                SELECT COALESCE(SUM(total_cost), 0) as total,
                       COUNT(*) as count
                FROM sessions
                WHERE status IN ('completed', 'running', 'killed')
                """
            )
            row = cur.fetchone()
            all_time = float(row["total"]) if row else 0.0
            count_total = row["count"] if row else 0

            # Today
            cur.execute(
                """
                SELECT COALESCE(SUM(total_cost), 0) as total,
                       COUNT(*) as count
                FROM sessions
                WHERE created_at >= %s
                  AND status IN ('completed', 'running', 'killed')
                """,
                (today_start,),
            )
            row = cur.fetchone()
            today = float(row["total"]) if row else 0.0
            count_today = row["count"] if row else 0

            # This week
            cur.execute(
                """
                SELECT COALESCE(SUM(total_cost), 0) as total,
                       COUNT(*) as count
                FROM sessions
                WHERE created_at >= %s
                  AND status IN ('completed', 'running', 'killed')
                """,
                (week_start,),
            )
            row = cur.fetchone()
            this_week = float(row["total"]) if row else 0.0
            count_week = row["count"] if row else 0

            # This month
            cur.execute(
                """
                SELECT COALESCE(SUM(total_cost), 0) as total,
                       COUNT(*) as count
                FROM sessions
                WHERE created_at >= %s
                  AND status IN ('completed', 'running', 'killed')
                """,
                (month_start,),
            )
            row = cur.fetchone()
            this_month = float(row["total"]) if row else 0.0
            count_month = row["count"] if row else 0

    return CostSummary(
        today=today,
        this_week=this_week,
        this_month=this_month,
        all_time=all_time,
        session_count_today=count_today,
        session_count_week=count_week,
        session_count_month=count_month,
        session_count_total=count_total,
    )


def get_user_costs(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserCost], int]:
    """Get costs aggregated by user.

    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        limit: Max results to return
        offset: Results to skip

    Returns:
        Tuple of (list of UserCost, total count)
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Build date filter
            date_filter = ""
            params: list[Any] = []

            if start_date:
                date_filter += " AND s.created_at >= %s"
                params.append(datetime.combine(start_date, datetime.min.time()))
            if end_date:
                date_filter += " AND s.created_at < %s"
                params.append(datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

            # Get total count
            cur.execute(
                f"""
                SELECT COUNT(DISTINCT s.user_id) as total
                FROM sessions s
                WHERE s.status IN ('completed', 'running', 'killed')
                {date_filter}
                """,
                params,
            )
            total = cur.fetchone()["total"]

            # Get user costs
            cur.execute(
                f"""
                SELECT s.user_id,
                       u.email,
                       COALESCE(SUM(s.total_cost), 0) as total_cost,
                       COUNT(*) as session_count
                FROM sessions s
                LEFT JOIN users u ON u.id = s.user_id
                WHERE s.status IN ('completed', 'running', 'killed')
                {date_filter}
                GROUP BY s.user_id, u.email
                ORDER BY total_cost DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )

            users = [
                UserCost(
                    user_id=row["user_id"],
                    email=row["email"],
                    total_cost=float(row["total_cost"]),
                    session_count=row["session_count"],
                )
                for row in cur.fetchall()
            ]

    return users, total


def get_daily_costs(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[DailyCost]:
    """Get costs aggregated by day.

    Args:
        start_date: Start of date range (inclusive, default: 30 days ago)
        end_date: End of date range (inclusive, default: today)

    Returns:
        List of DailyCost sorted by date ascending
    """
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DATE(created_at) as day,
                       COALESCE(SUM(total_cost), 0) as total_cost,
                       COUNT(*) as session_count
                FROM sessions
                WHERE created_at >= %s
                  AND created_at < %s
                  AND status IN ('completed', 'running', 'killed')
                GROUP BY DATE(created_at)
                ORDER BY day ASC
                """,
                (
                    datetime.combine(start_date, datetime.min.time()),
                    datetime.combine(end_date + timedelta(days=1), datetime.min.time()),
                ),
            )

            return [
                DailyCost(
                    date=row["day"],
                    total_cost=float(row["total_cost"]),
                    session_count=row["session_count"],
                )
                for row in cur.fetchall()
            ]


def get_session_cost(session_id: str) -> dict[str, Any] | None:
    """Get cost breakdown for a single session.

    Args:
        session_id: Session ID to query

    Returns:
        Dict with total_cost and breakdown, or None if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, total_cost, status, created_at
                FROM sessions
                WHERE id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            return {
                "session_id": row["id"],
                "total_cost": float(row["total_cost"] or 0),
                "status": row["status"],
                "created_at": row["created_at"].isoformat(),
            }


def get_full_report(
    start_date: date | None = None,
    end_date: date | None = None,
    top_users: int = 10,
) -> CostReport:
    """Generate full cost report with all breakdowns.

    Args:
        start_date: Start of date range
        end_date: End of date range
        top_users: Number of top users to include

    Returns:
        CostReport with summary and breakdowns
    """
    summary = get_cost_summary()
    users, _ = get_user_costs(start_date, end_date, limit=top_users)
    daily = get_daily_costs(start_date, end_date)

    return CostReport(
        summary=summary,
        by_user=users,
        by_day=daily,
        by_model=[],  # Model breakdown requires cost_events table
    )


def log_replan_suggestion_shown(action_id: str, user_id: str) -> None:
    """Log when a replanning suggestion is shown to a user.

    Args:
        action_id: UUID of the cancelled action
        user_id: User who is seeing the suggestion
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_events (user_id, event_type, event_data, created_at)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (user_id, "action_replan_suggested", {"action_id": str(action_id)}),
                )
    except Exception as e:
        logger.warning(f"Failed to log replan suggestion: {e}")


def log_replan_suggestion_accepted(action_id: str, user_id: str, new_session_id: str) -> None:
    """Log when user accepts a replanning suggestion and creates a new meeting.

    Args:
        action_id: UUID of the cancelled action
        user_id: User who accepted the suggestion
        new_session_id: UUID of newly created session
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics_events (user_id, event_type, event_data, created_at)
                    VALUES (%s, %s, %s, NOW())
                    """,
                    (
                        user_id,
                        "action_replan_accepted",
                        {
                            "action_id": str(action_id),
                            "new_session_id": str(new_session_id),
                        },
                    ),
                )
    except Exception as e:
        logger.warning(f"Failed to log replan acceptance: {e}")
