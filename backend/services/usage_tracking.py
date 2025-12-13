"""Usage tracking service for tier-based limits.

Provides Redis-backed real-time usage counters with:
- Atomic increment operations (prevents race conditions)
- Daily/monthly period tracking
- Automatic TTL expiration
- Postgres rollup for historical data
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bo1.constants import TierLimits, UsageMetrics
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class UsageResult:
    """Result of a usage check."""

    allowed: bool
    current: int
    limit: int
    remaining: int
    reset_at: datetime | None = None


def _get_redis() -> Any:
    """Get Redis client."""
    try:
        from bo1.state.redis_cache import get_redis_client

        return get_redis_client()
    except Exception:
        return None


def _daily_key(user_id: str, metric: str) -> str:
    """Generate Redis key for daily usage."""
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    return UsageMetrics.DAILY_KEY_PATTERN.format(
        prefix=UsageMetrics.KEY_PREFIX, user_id=user_id, metric=metric, date=date
    )


def _monthly_key(user_id: str, metric: str) -> str:
    """Generate Redis key for monthly usage."""
    year_month = datetime.now(UTC).strftime("%Y-%m")
    return UsageMetrics.MONTHLY_KEY_PATTERN.format(
        prefix=UsageMetrics.KEY_PREFIX, user_id=user_id, metric=metric, year_month=year_month
    )


def increment_usage(user_id: str, metric: str, count: int = 1) -> int:
    """Increment usage counter for a metric.

    Uses Redis INCRBY for atomic operation. Falls back to Postgres if Redis unavailable.

    Args:
        user_id: User identifier
        metric: Metric name (from UsageMetrics)
        count: Amount to increment (default: 1)

    Returns:
        New usage count
    """
    redis = _get_redis()
    if not redis:
        logger.warning("Redis unavailable, falling back to Postgres for usage tracking")
        return _increment_postgres(user_id, metric, count)

    # Determine if daily or monthly metric
    if metric in (UsageMetrics.MENTOR_CHATS, UsageMetrics.API_CALLS):
        key = _daily_key(user_id, metric)
        ttl = UsageMetrics.DAILY_TTL
    else:
        key = _monthly_key(user_id, metric)
        ttl = UsageMetrics.MONTHLY_TTL

    try:
        pipe = redis.pipeline()
        pipe.incrby(key, count)
        pipe.expire(key, ttl)
        result = pipe.execute()
        new_count = result[0]
        logger.debug(f"Usage incremented: user={user_id} metric={metric} count={new_count}")
        return new_count
    except Exception as e:
        logger.error(f"Redis increment failed: {e}")
        return _increment_postgres(user_id, metric, count)


def get_usage(user_id: str, metric: str) -> int:
    """Get current usage for a metric.

    Args:
        user_id: User identifier
        metric: Metric name

    Returns:
        Current usage count
    """
    redis = _get_redis()
    if not redis:
        return _get_postgres_usage(user_id, metric)

    # Determine if daily or monthly metric
    if metric in (UsageMetrics.MENTOR_CHATS, UsageMetrics.API_CALLS):
        key = _daily_key(user_id, metric)
    else:
        key = _monthly_key(user_id, metric)

    try:
        value = redis.get(key)
        return int(value) if value else 0
    except Exception as e:
        logger.error(f"Redis get failed: {e}")
        return _get_postgres_usage(user_id, metric)


def check_limit(user_id: str, metric: str, tier: str) -> UsageResult:
    """Check if user is within their tier limit for a metric.

    Args:
        user_id: User identifier
        metric: Metric name
        tier: User's subscription tier

    Returns:
        UsageResult with allowed status and usage details
    """
    # Map metric to limit key
    limit_key_map = {
        UsageMetrics.MEETINGS_CREATED: "meetings_monthly",
        UsageMetrics.DATASETS_UPLOADED: "datasets_total",
        UsageMetrics.MENTOR_CHATS: "mentor_daily",
        UsageMetrics.API_CALLS: "api_daily",
    }

    limit_key = limit_key_map.get(metric)
    if not limit_key:
        return UsageResult(allowed=True, current=0, limit=-1, remaining=-1)

    limit = TierLimits.get_limit(tier, limit_key)

    # Unlimited check
    if TierLimits.is_unlimited(limit):
        current = get_usage(user_id, metric)
        return UsageResult(allowed=True, current=current, limit=-1, remaining=-1)

    current = get_usage(user_id, metric)
    allowed = current < limit
    remaining = max(0, limit - current)

    # Calculate reset time
    now = datetime.now(UTC)
    if metric in (UsageMetrics.MENTOR_CHATS, UsageMetrics.API_CALLS):
        # Daily reset at midnight UTC
        reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
        reset_at = reset_at.replace(day=reset_at.day + 1) if reset_at <= now else reset_at
    else:
        # Monthly reset on 1st of next month
        if now.month == 12:
            reset_at = now.replace(
                year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            reset_at = now.replace(
                month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )

    return UsageResult(
        allowed=allowed,
        current=current,
        limit=limit,
        remaining=remaining,
        reset_at=reset_at,
    )


def get_all_usage(user_id: str, tier: str) -> dict[str, UsageResult]:
    """Get usage for all metrics for a user.

    Args:
        user_id: User identifier
        tier: User's subscription tier

    Returns:
        Dict of metric -> UsageResult
    """
    return {metric: check_limit(user_id, metric, tier) for metric in UsageMetrics.ALL}


def check_tier_override(user_id: str) -> dict[str, Any] | None:
    """Check if user has a tier override.

    Args:
        user_id: User identifier

    Returns:
        Override dict with tier, expires_at, reason or None
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT tier_override
                    FROM users
                    WHERE id = %s AND tier_override IS NOT NULL
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    override = row[0]
                    # Check expiry
                    if override.get("expires_at"):
                        expires = datetime.fromisoformat(
                            override["expires_at"].replace("Z", "+00:00")
                        )
                        if expires < datetime.now(UTC):
                            # Override expired, clear it
                            _clear_tier_override(user_id)
                            return None
                    return override
                return None
    except Exception as e:
        logger.error(f"Failed to check tier override: {e}")
        return None


def get_effective_tier(user_id: str, base_tier: str) -> str:
    """Get effective tier for a user (considering overrides).

    Args:
        user_id: User identifier
        base_tier: User's subscription tier from users table

    Returns:
        Effective tier (override tier if active, else base_tier)
    """
    override = check_tier_override(user_id)
    if override:
        return override.get("tier", base_tier)
    return base_tier


def _increment_postgres(user_id: str, metric: str, count: int) -> int:
    """Increment usage in Postgres (fallback when Redis unavailable).

    Args:
        user_id: User identifier
        metric: Metric name
        count: Amount to increment

    Returns:
        New count
    """
    now = datetime.now(UTC)
    period = (
        now.strftime("%Y-%m")
        if metric in (UsageMetrics.MEETINGS_CREATED, UsageMetrics.DATASETS_UPLOADED)
        else now.strftime("%Y-%m-%d")
    )

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_usage (user_id, metric, period, count, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (user_id, metric, period)
                    DO UPDATE SET count = user_usage.count + EXCLUDED.count, updated_at = NOW()
                    RETURNING count
                    """,
                    (user_id, metric, period, count),
                )
                result = cur.fetchone()
                return result[0] if result else count
    except Exception as e:
        logger.error(f"Postgres increment failed: {e}")
        return count


def _get_postgres_usage(user_id: str, metric: str) -> int:
    """Get usage from Postgres (fallback when Redis unavailable).

    Args:
        user_id: User identifier
        metric: Metric name

    Returns:
        Current count
    """
    now = datetime.now(UTC)
    period = (
        now.strftime("%Y-%m")
        if metric in (UsageMetrics.MEETINGS_CREATED, UsageMetrics.DATASETS_UPLOADED)
        else now.strftime("%Y-%m-%d")
    )

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count FROM user_usage
                    WHERE user_id = %s AND metric = %s AND period = %s
                    """,
                    (user_id, metric, period),
                )
                row = cur.fetchone()
                return row[0] if row else 0
    except Exception as e:
        logger.error(f"Postgres get failed: {e}")
        return 0


def _clear_tier_override(user_id: str) -> None:
    """Clear an expired tier override.

    Args:
        user_id: User identifier
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users SET tier_override = NULL, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (user_id,),
                )
    except Exception as e:
        logger.error(f"Failed to clear tier override: {e}")


def rollup_to_postgres(user_id: str) -> None:
    """Sync Redis usage counters to Postgres for persistence.

    Called periodically or on significant events to ensure
    usage data survives Redis restarts.

    Args:
        user_id: User identifier
    """
    redis = _get_redis()
    if not redis:
        return

    now = datetime.now(UTC)

    for metric in UsageMetrics.ALL:
        try:
            # Get from Redis
            if metric in (UsageMetrics.MENTOR_CHATS, UsageMetrics.API_CALLS):
                key = _daily_key(user_id, metric)
                period = now.strftime("%Y-%m-%d")
            else:
                key = _monthly_key(user_id, metric)
                period = now.strftime("%Y-%m")

            value = redis.get(key)
            if not value:
                continue

            count = int(value)

            # Upsert to Postgres
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO user_usage (user_id, metric, period, count, updated_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (user_id, metric, period)
                        DO UPDATE SET count = GREATEST(user_usage.count, EXCLUDED.count), updated_at = NOW()
                        """,
                        (user_id, metric, period, count),
                    )
        except Exception as e:
            logger.error(f"Rollup failed for {user_id}/{metric}: {e}")
