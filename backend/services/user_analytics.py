"""User analytics service for admin metrics dashboard.

Provides aggregated user metrics:
- Signup statistics (daily signups, total users)
- Active user counts (DAU, WAU, MAU)
- Usage statistics (meetings, actions, sessions per day)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class SignupStats:
    """Signup statistics for a time period."""

    total_users: int
    new_users_today: int
    new_users_7d: int
    new_users_30d: int
    daily_signups: list[tuple[date, int]]  # (date, count) pairs


@dataclass
class ActiveUserStats:
    """Active user metrics (DAU, WAU, MAU)."""

    dau: int  # Daily active users (last 24h)
    wau: int  # Weekly active users (last 7 days)
    mau: int  # Monthly active users (last 30 days)
    daily_active: list[tuple[date, int]]  # (date, count) pairs


@dataclass
class UsageStats:
    """Platform usage statistics."""

    total_meetings: int
    total_actions: int
    meetings_today: int
    meetings_7d: int
    meetings_30d: int
    actions_created_7d: int
    daily_meetings: list[tuple[date, int]]  # (date, count) pairs
    daily_actions: list[tuple[date, int]]  # (date, created count) pairs

    # Extended KPIs
    mentor_sessions_count: int = 0
    data_analyses_count: int = 0
    projects_count: int = 0
    actions_started_count: int = 0
    actions_completed_count: int = 0
    actions_cancelled_count: int = 0


def get_signup_stats(days: int = 30) -> SignupStats:
    """Get signup statistics for the specified period.

    Args:
        days: Number of days to include in daily breakdown (max 90)

    Returns:
        SignupStats with totals and daily breakdown
    """
    days = min(days, 90)  # Cap at 90 days for performance
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today_start - timedelta(days=days)
    week_ago = today_start - timedelta(days=7)
    month_ago = today_start - timedelta(days=30)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Total users
            cur.execute("SELECT COUNT(*) as total FROM users")
            total_users = cur.fetchone()["total"]

            # New users today
            cur.execute(
                "SELECT COUNT(*) as count FROM users WHERE created_at >= %s",
                (today_start,),
            )
            new_today = cur.fetchone()["count"]

            # New users last 7 days
            cur.execute(
                "SELECT COUNT(*) as count FROM users WHERE created_at >= %s",
                (week_ago,),
            )
            new_7d = cur.fetchone()["count"]

            # New users last 30 days
            cur.execute(
                "SELECT COUNT(*) as count FROM users WHERE created_at >= %s",
                (month_ago,),
            )
            new_30d = cur.fetchone()["count"]

            # Daily signups breakdown
            cur.execute(
                """
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM users
                WHERE created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY day ASC
                """,
                (start_date,),
            )
            daily_signups = [(row["day"], row["count"]) for row in cur.fetchall()]

    return SignupStats(
        total_users=total_users,
        new_users_today=new_today,
        new_users_7d=new_7d,
        new_users_30d=new_30d,
        daily_signups=daily_signups,
    )


def get_active_user_stats(days: int = 30) -> ActiveUserStats:
    """Get active user metrics (DAU, WAU, MAU).

    Active users = users who started at least one session in the period.

    Args:
        days: Number of days to include in daily breakdown (max 90)

    Returns:
        ActiveUserStats with DAU/WAU/MAU and daily breakdown
    """
    days = min(days, 90)
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_ago = today_start - timedelta(days=7)
    month_ago = today_start - timedelta(days=30)
    start_date = today_start - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            # DAU (last 24h)
            cur.execute(
                """
                SELECT COUNT(DISTINCT user_id) as count
                FROM sessions
                WHERE created_at >= %s
                """,
                (yesterday_start,),
            )
            dau = cur.fetchone()["count"]

            # WAU (last 7 days)
            cur.execute(
                """
                SELECT COUNT(DISTINCT user_id) as count
                FROM sessions
                WHERE created_at >= %s
                """,
                (week_ago,),
            )
            wau = cur.fetchone()["count"]

            # MAU (last 30 days)
            cur.execute(
                """
                SELECT COUNT(DISTINCT user_id) as count
                FROM sessions
                WHERE created_at >= %s
                """,
                (month_ago,),
            )
            mau = cur.fetchone()["count"]

            # Daily active users breakdown
            cur.execute(
                """
                SELECT DATE(created_at) as day, COUNT(DISTINCT user_id) as count
                FROM sessions
                WHERE created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY day ASC
                """,
                (start_date,),
            )
            daily_active = [(row["day"], row["count"]) for row in cur.fetchall()]

    return ActiveUserStats(
        dau=dau,
        wau=wau,
        mau=mau,
        daily_active=daily_active,
    )


def get_usage_stats(days: int = 30) -> UsageStats:
    """Get platform usage statistics (meetings, actions).

    Args:
        days: Number of days to include in daily breakdown (max 90)

    Returns:
        UsageStats with meeting and action counts
    """
    days = min(days, 90)
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today_start - timedelta(days=7)
    month_ago = today_start - timedelta(days=30)
    start_date = today_start - timedelta(days=days)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Total meetings
            cur.execute("SELECT COUNT(*) as total FROM sessions")
            total_meetings = cur.fetchone()["total"]

            # Total actions
            cur.execute("SELECT COUNT(*) as total FROM actions WHERE deleted_at IS NULL")
            total_actions = cur.fetchone()["total"]

            # Meetings today
            cur.execute(
                "SELECT COUNT(*) as count FROM sessions WHERE created_at >= %s",
                (today_start,),
            )
            meetings_today = cur.fetchone()["count"]

            # Meetings last 7 days
            cur.execute(
                "SELECT COUNT(*) as count FROM sessions WHERE created_at >= %s",
                (week_ago,),
            )
            meetings_7d = cur.fetchone()["count"]

            # Meetings last 30 days
            cur.execute(
                "SELECT COUNT(*) as count FROM sessions WHERE created_at >= %s",
                (month_ago,),
            )
            meetings_30d = cur.fetchone()["count"]

            # Actions created last 7 days
            cur.execute(
                """
                SELECT COUNT(*) as count FROM actions
                WHERE created_at >= %s AND deleted_at IS NULL
                """,
                (week_ago,),
            )
            actions_7d = cur.fetchone()["count"]

            # Daily meetings breakdown
            cur.execute(
                """
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM sessions
                WHERE created_at >= %s
                GROUP BY DATE(created_at)
                ORDER BY day ASC
                """,
                (start_date,),
            )
            daily_meetings = [(row["day"], row["count"]) for row in cur.fetchall()]

            # Daily actions created breakdown
            cur.execute(
                """
                SELECT DATE(created_at) as day, COUNT(*) as count
                FROM actions
                WHERE created_at >= %s AND deleted_at IS NULL
                GROUP BY DATE(created_at)
                ORDER BY day ASC
                """,
                (start_date,),
            )
            daily_actions = [(row["day"], row["count"]) for row in cur.fetchall()]

            # Extended KPIs: mentor sessions (from user_usage table)
            cur.execute(
                """
                SELECT COALESCE(SUM(count), 0) as total
                FROM user_usage WHERE metric = 'mentor_chats'
                """
            )
            mentor_sessions = cur.fetchone()["total"]

            # Data analyses count
            cur.execute("SELECT COUNT(*) as total FROM dataset_analyses")
            data_analyses = cur.fetchone()["total"]

            # Projects count (projects table has no deleted_at)
            cur.execute("SELECT COUNT(*) as total FROM projects")
            projects_count = cur.fetchone()["total"]

            # Actions by status
            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'in_progress') as started,
                    COUNT(*) FILTER (WHERE status = 'done') as completed,
                    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled
                FROM actions WHERE deleted_at IS NULL
                """
            )
            action_stats = cur.fetchone()

    return UsageStats(
        total_meetings=total_meetings,
        total_actions=total_actions,
        meetings_today=meetings_today,
        meetings_7d=meetings_7d,
        meetings_30d=meetings_30d,
        actions_created_7d=actions_7d,
        daily_meetings=daily_meetings,
        daily_actions=daily_actions,
        mentor_sessions_count=mentor_sessions,
        data_analyses_count=data_analyses,
        projects_count=projects_count,
        actions_started_count=action_stats["started"],
        actions_completed_count=action_stats["completed"],
        actions_cancelled_count=action_stats["cancelled"],
    )
