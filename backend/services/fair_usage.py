"""Fair Usage Service for variable-cost LLM features.

Implements:
- Per-user, per-feature daily cost tracking
- Soft cap warnings (80% of limit)
- Hard cap blocking (100% of limit)
- Top 10% (p90) heavy user detection
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Any

from bo1.billing.config import PlanConfig
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


class UsageStatus(str, Enum):
    """Status of fair usage check."""

    ALLOWED = "allowed"  # Under soft cap
    SOFT_WARNING = "soft_warning"  # Between soft and hard cap
    HARD_BLOCKED = "hard_blocked"  # At or over hard cap


@dataclass
class UsageCheckResult:
    """Result of a fair usage check."""

    status: UsageStatus
    current_cost: float  # Current daily cost for this feature
    daily_limit: float  # Daily limit for this feature (-1 = unlimited)
    percent_used: float  # Percentage of limit used (0-1)
    remaining: float  # Amount remaining until hard cap
    message: str | None = None  # User-facing message


@dataclass
class HeavyUser:
    """A user identified as heavy user for a feature."""

    user_id: str
    email: str | None
    feature: str
    total_cost_7d: float
    avg_daily_cost: float
    p90_threshold: float
    exceeds_p90_by: float  # How much they exceed p90


class FairUsageService:
    """Service for checking and enforcing fair usage limits."""

    @staticmethod
    def get_user_daily_cost(user_id: str, feature: str, target_date: date | None = None) -> float:
        """Get user's daily cost for a feature.

        Args:
            user_id: User identifier
            feature: Feature name (mentor_chat, dataset_qa, competitor_analysis, meeting)
            target_date: Date to check (defaults to today)

        Returns:
            Total cost in USD for the day
        """
        if target_date is None:
            target_date = date.today()

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COALESCE(total_cost, 0) as total_cost
                        FROM daily_user_feature_costs
                        WHERE user_id = %s AND feature = %s AND date = %s
                        """,
                        (user_id, feature, target_date),
                    )
                    row = cur.fetchone()
                    return float(row["total_cost"]) if row else 0.0
        except Exception as e:
            logger.warning(f"Error getting daily cost for {user_id}/{feature}: {e}")
            return 0.0

    @staticmethod
    def get_user_usage_summary(user_id: str, target_date: date | None = None) -> dict[str, float]:
        """Get user's daily cost for all features.

        Args:
            user_id: User identifier
            target_date: Date to check (defaults to today)

        Returns:
            Dict mapping feature name to cost
        """
        if target_date is None:
            target_date = date.today()

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT feature, total_cost
                        FROM daily_user_feature_costs
                        WHERE user_id = %s AND date = %s
                        """,
                        (user_id, target_date),
                    )
                    return {row["feature"]: float(row["total_cost"]) for row in cur.fetchall()}
        except Exception as e:
            logger.warning(f"Error getting usage summary for {user_id}: {e}")
            return {}

    @staticmethod
    def check_fair_usage(
        user_id: str,
        feature: str,
        tier: str,
        estimated_cost: float = 0.0,
    ) -> UsageCheckResult:
        """Check if user is within fair usage limits for a feature.

        Args:
            user_id: User identifier
            feature: Feature name (mentor_chat, dataset_qa, competitor_analysis, meeting)
            tier: User's subscription tier
            estimated_cost: Estimated cost of the operation (for pre-check)

        Returns:
            UsageCheckResult with status and details
        """
        daily_limit = PlanConfig.get_fair_usage_limit(tier, feature)

        # Unlimited tier - always allowed
        if PlanConfig.is_fair_usage_unlimited(daily_limit):
            return UsageCheckResult(
                status=UsageStatus.ALLOWED,
                current_cost=0.0,
                daily_limit=-1.0,
                percent_used=0.0,
                remaining=-1.0,  # Unlimited
                message=None,
            )

        # Get current daily cost
        current_cost = FairUsageService.get_user_daily_cost(user_id, feature)
        projected_cost = current_cost + estimated_cost

        # Calculate thresholds
        soft_threshold = daily_limit * PlanConfig.FAIR_USAGE_SOFT_CAP_PCT
        hard_threshold = daily_limit * PlanConfig.FAIR_USAGE_HARD_CAP_PCT

        percent_used = projected_cost / daily_limit if daily_limit > 0 else 0.0
        remaining = max(0.0, daily_limit - projected_cost)

        # Determine status
        if projected_cost >= hard_threshold:
            return UsageCheckResult(
                status=UsageStatus.HARD_BLOCKED,
                current_cost=current_cost,
                daily_limit=daily_limit,
                percent_used=min(1.0, percent_used),
                remaining=0.0,
                message=f"Daily {feature.replace('_', ' ')} limit reached. Resets at midnight UTC.",
            )
        elif projected_cost >= soft_threshold:
            return UsageCheckResult(
                status=UsageStatus.SOFT_WARNING,
                current_cost=current_cost,
                daily_limit=daily_limit,
                percent_used=percent_used,
                remaining=remaining,
                message=f"Approaching daily {feature.replace('_', ' ')} limit ({percent_used:.0%} used).",
            )
        else:
            return UsageCheckResult(
                status=UsageStatus.ALLOWED,
                current_cost=current_cost,
                daily_limit=daily_limit,
                percent_used=percent_used,
                remaining=remaining,
                message=None,
            )

    @staticmethod
    def get_p90_threshold(feature: str, days: int = 7) -> float:
        """Get p90 daily cost threshold for a feature.

        Args:
            feature: Feature name
            days: Number of days for rolling window

        Returns:
            p90 threshold in USD (returns 0.0 if insufficient data)
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    # Get per-user daily totals, then calculate p90
                    cur.execute(
                        """
                        SELECT PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_cost) as p90
                        FROM daily_user_feature_costs
                        WHERE feature = %s AND date >= %s AND date < %s
                        """,
                        (feature, start_date, end_date),
                    )
                    row = cur.fetchone()
                    return float(row["p90"]) if row and row["p90"] else 0.0
        except Exception as e:
            logger.warning(f"Error getting p90 for {feature}: {e}")
            return 0.0

    @staticmethod
    def get_heavy_users(
        feature: str | None = None,
        days: int = 7,
        limit: int = 50,
    ) -> list[HeavyUser]:
        """Get users exceeding p90 threshold for a feature.

        Args:
            feature: Feature name (None for all features)
            days: Number of days for rolling window
            limit: Maximum users to return

        Returns:
            List of HeavyUser objects sorted by cost descending
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    # Get p90 thresholds per feature
                    if feature:
                        feature_filter = "AND feature = %s"
                        params: tuple[Any, ...] = (start_date, end_date, feature)
                    else:
                        feature_filter = ""
                        params = (start_date, end_date)

                    # Get aggregated costs per user per feature
                    cur.execute(
                        f"""
                        WITH user_costs AS (
                            SELECT
                                user_id,
                                feature,
                                SUM(total_cost) as total_cost_7d,
                                SUM(total_cost) / %s as avg_daily_cost
                            FROM daily_user_feature_costs
                            WHERE date >= %s AND date < %s {feature_filter}
                            GROUP BY user_id, feature
                        ),
                        feature_p90 AS (
                            SELECT
                                feature,
                                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_cost_7d) as p90
                            FROM user_costs
                            GROUP BY feature
                        )
                        SELECT
                            uc.user_id,
                            u.email,
                            uc.feature,
                            uc.total_cost_7d,
                            uc.avg_daily_cost,
                            fp.p90 as p90_threshold,
                            uc.total_cost_7d - fp.p90 as exceeds_p90_by
                        FROM user_costs uc
                        JOIN feature_p90 fp ON uc.feature = fp.feature
                        LEFT JOIN users u ON uc.user_id = u.user_id
                        WHERE uc.total_cost_7d > fp.p90 AND fp.p90 > 0
                        ORDER BY exceeds_p90_by DESC
                        LIMIT %s
                        """,
                        (days,) + params + (limit,),
                    )

                    return [
                        HeavyUser(
                            user_id=row["user_id"],
                            email=row["email"],
                            feature=row["feature"],
                            total_cost_7d=float(row["total_cost_7d"]),
                            avg_daily_cost=float(row["avg_daily_cost"]),
                            p90_threshold=float(row["p90_threshold"]),
                            exceeds_p90_by=float(row["exceeds_p90_by"]),
                        )
                        for row in cur.fetchall()
                    ]
        except Exception as e:
            logger.warning(f"Error getting heavy users: {e}")
            return []

    @staticmethod
    def get_feature_cost_breakdown(
        days: int = 7,
    ) -> dict[str, dict[str, float]]:
        """Get cost breakdown by feature for admin dashboard.

        Args:
            days: Number of days to include

        Returns:
            Dict with feature -> {total_cost, user_count, avg_per_user, p90}
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        WITH feature_stats AS (
                            SELECT
                                feature,
                                SUM(total_cost) as total_cost,
                                COUNT(DISTINCT user_id) as user_count,
                                PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_cost) as p90_daily
                            FROM daily_user_feature_costs
                            WHERE date >= %s AND date < %s
                            GROUP BY feature
                        )
                        SELECT
                            feature,
                            total_cost,
                            user_count,
                            total_cost / NULLIF(user_count, 0) as avg_per_user,
                            p90_daily
                        FROM feature_stats
                        ORDER BY total_cost DESC
                        """,
                        (start_date, end_date),
                    )

                    return {
                        row["feature"]: {
                            "total_cost": float(row["total_cost"]),
                            "user_count": row["user_count"],
                            "avg_per_user": float(row["avg_per_user"] or 0),
                            "p90_daily": float(row["p90_daily"] or 0),
                        }
                        for row in cur.fetchall()
                    }
        except Exception as e:
            logger.warning(f"Error getting feature breakdown: {e}")
            return {}


# Singleton instance
_fair_usage_service: FairUsageService | None = None


def get_fair_usage_service() -> FairUsageService:
    """Get the fair usage service singleton."""
    global _fair_usage_service
    if _fair_usage_service is None:
        _fair_usage_service = FairUsageService()
    return _fair_usage_service
