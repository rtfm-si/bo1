"""Feature flag service for gradual rollouts and tier-based features.

Provides:
- Flag evaluation with tier targeting
- Percentage-based rollouts (deterministic via user_id hash)
- Per-user overrides
- Redis caching for fast evaluation
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Redis cache key prefix and TTL
CACHE_PREFIX = "feature_flag:"
CACHE_TTL = 60  # seconds


@dataclass
class FeatureFlag:
    """Feature flag definition."""

    id: UUID
    name: str
    description: str | None
    enabled: bool
    rollout_pct: int
    tiers: list[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class FeatureFlagOverride:
    """Per-user flag override."""

    id: UUID
    flag_id: UUID
    user_id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


def _get_redis() -> Any:
    """Get Redis client."""
    try:
        from bo1.state.redis_cache import get_redis_client

        return get_redis_client()
    except Exception:
        return None


def _cache_key(flag_name: str) -> str:
    """Generate cache key for a flag."""
    return f"{CACHE_PREFIX}{flag_name}"


def _invalidate_cache(flag_name: str) -> None:
    """Invalidate cached flag data."""
    redis = _get_redis()
    if redis:
        try:
            redis.delete(_cache_key(flag_name))
        except Exception as e:
            logger.warning("Failed to invalidate flag cache: %s", e)


def _hash_user_for_rollout(flag_name: str, user_id: str) -> int:
    """Generate deterministic hash for rollout bucket (0-99)."""
    combined = f"{flag_name}:{user_id}"
    hash_bytes = hashlib.md5(combined.encode(), usedforsecurity=False).digest()
    return int.from_bytes(hash_bytes[:2], "big") % 100


def get_flag(flag_name: str) -> FeatureFlag | None:
    """Get a feature flag by name.

    Args:
        flag_name: Flag name

    Returns:
        FeatureFlag or None if not found
    """
    # Try cache first
    redis = _get_redis()
    if redis:
        try:
            cached = redis.get(_cache_key(flag_name))
            if cached:
                data = json.loads(cached)
                return FeatureFlag(
                    id=UUID(data["id"]),
                    name=data["name"],
                    description=data.get("description"),
                    enabled=data["enabled"],
                    rollout_pct=data["rollout_pct"],
                    tiers=data["tiers"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                )
        except Exception as e:
            logger.warning("Cache read failed for flag %s: %s", flag_name, e)

    # Fetch from database
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, enabled, rollout_pct, tiers, "
                "created_at, updated_at FROM feature_flags WHERE name = %s",
                (flag_name,),
            )
            row = cur.fetchone()
            if not row:
                return None

            flag = FeatureFlag(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                enabled=row["enabled"],
                rollout_pct=row["rollout_pct"],
                tiers=row["tiers"]
                if isinstance(row["tiers"], list)
                else json.loads(row["tiers"] or "[]"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        # Cache the result
        if redis:
            try:
                cache_data = {
                    "id": str(flag.id),
                    "name": flag.name,
                    "description": flag.description,
                    "enabled": flag.enabled,
                    "rollout_pct": flag.rollout_pct,
                    "tiers": flag.tiers,
                    "created_at": flag.created_at.isoformat(),
                    "updated_at": flag.updated_at.isoformat(),
                }
                redis.setex(_cache_key(flag_name), CACHE_TTL, json.dumps(cache_data))
            except Exception as e:
                logger.warning("Cache write failed for flag %s: %s", flag_name, e)

        return flag


def get_user_override(flag_id: UUID, user_id: str) -> bool | None:
    """Get user-specific override for a flag.

    Args:
        flag_id: Flag UUID
        user_id: User ID

    Returns:
        Override enabled value, or None if no override exists
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT enabled FROM feature_flag_overrides WHERE flag_id = %s AND user_id = %s",
                (flag_id, user_id),
            )
            row = cur.fetchone()
            return row["enabled"] if row else None


def is_enabled(
    flag_name: str,
    user_id: str | None = None,
    tier: str | None = None,
) -> bool:
    """Evaluate if a feature flag is enabled for a user.

    Evaluation order:
    1. User override (if exists)
    2. Tier match (if tiers specified and user tier provided)
    3. Rollout percentage (deterministic via user_id hash)
    4. Global enabled flag

    Args:
        flag_name: Flag name
        user_id: Optional user ID for override/rollout checks
        tier: Optional user tier for tier-based flags

    Returns:
        True if flag is enabled for this context
    """
    flag = get_flag(flag_name)
    if not flag:
        logger.debug("Flag %s not found, returning False", flag_name)
        return False

    # Check global enabled first
    if not flag.enabled:
        return False

    # Check user override
    if user_id:
        override = get_user_override(flag.id, user_id)
        if override is not None:
            return override

    # Check tier restriction
    if flag.tiers and len(flag.tiers) > 0:
        if not tier:
            return False
        if tier.lower() not in [t.lower() for t in flag.tiers]:
            return False

    # Check rollout percentage
    if flag.rollout_pct < 100 and user_id:
        bucket = _hash_user_for_rollout(flag_name, user_id)
        if bucket >= flag.rollout_pct:
            return False

    return True


def get_all_flags() -> list[FeatureFlag]:
    """Get all feature flags (admin use).

    Returns:
        List of all flags
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, enabled, rollout_pct, tiers, "
                "created_at, updated_at FROM feature_flags ORDER BY name"
            )
            flags = []
            for row in cur.fetchall():
                flags.append(
                    FeatureFlag(
                        id=row["id"],
                        name=row["name"],
                        description=row["description"],
                        enabled=row["enabled"],
                        rollout_pct=row["rollout_pct"],
                        tiers=row["tiers"]
                        if isinstance(row["tiers"], list)
                        else json.loads(row["tiers"] or "[]"),
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )
            return flags


def create_flag(
    name: str,
    description: str | None = None,
    enabled: bool = False,
    rollout_pct: int = 100,
    tiers: list[str] | None = None,
) -> FeatureFlag:
    """Create a new feature flag.

    Args:
        name: Unique flag name
        description: Optional description
        enabled: Whether flag is enabled globally
        rollout_pct: Percentage of users to roll out to (0-100)
        tiers: List of tiers that can access this feature

    Returns:
        Created flag

    Raises:
        ValueError: If flag name already exists
    """
    tiers = tiers or []
    now = datetime.now(UTC)

    with db_session() as conn:
        with conn.cursor() as cur:
            # Check for existing flag
            cur.execute("SELECT id FROM feature_flags WHERE name = %s", (name,))
            if cur.fetchone():
                raise ValueError(f"Flag '{name}' already exists")

            cur.execute(
                """
                INSERT INTO feature_flags (name, description, enabled, rollout_pct, tiers, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (name, description, enabled, rollout_pct, json.dumps(tiers), now, now),
            )
            flag_id = cur.fetchone()["id"]
            conn.commit()

            return FeatureFlag(
                id=flag_id,
                name=name,
                description=description,
                enabled=enabled,
                rollout_pct=rollout_pct,
                tiers=tiers,
                created_at=now,
                updated_at=now,
            )


def update_flag(
    name: str,
    description: str | None = None,
    enabled: bool | None = None,
    rollout_pct: int | None = None,
    tiers: list[str] | None = None,
) -> FeatureFlag | None:
    """Update an existing feature flag.

    Args:
        name: Flag name
        description: New description (None = no change)
        enabled: New enabled state (None = no change)
        rollout_pct: New rollout percentage (None = no change)
        tiers: New tiers list (None = no change)

    Returns:
        Updated flag, or None if not found
    """
    updates = []
    params: list[Any] = []
    now = datetime.now(UTC)

    if description is not None:
        updates.append("description = %s")
        params.append(description)
    if enabled is not None:
        updates.append("enabled = %s")
        params.append(enabled)
    if rollout_pct is not None:
        updates.append("rollout_pct = %s")
        params.append(rollout_pct)
    if tiers is not None:
        updates.append("tiers = %s")
        params.append(json.dumps(tiers))

    if not updates:
        return get_flag(name)

    updates.append("updated_at = %s")
    params.append(now)
    params.append(name)  # WHERE name = %s

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE feature_flags SET {', '.join(updates)} WHERE name = %s RETURNING id",
                params,
            )
            row = cur.fetchone()
            if not row:
                return None
            conn.commit()

    # Invalidate cache
    _invalidate_cache(name)

    return get_flag(name)


def delete_flag(name: str) -> bool:
    """Delete a feature flag.

    Args:
        name: Flag name

    Returns:
        True if deleted, False if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feature_flags WHERE name = %s RETURNING id", (name,))
            row = cur.fetchone()
            if row:
                conn.commit()
                _invalidate_cache(name)
                return True
            return False


def set_user_override(flag_name: str, user_id: str, enabled: bool) -> bool:
    """Set a per-user override for a flag.

    Args:
        flag_name: Flag name
        user_id: User ID
        enabled: Override value

    Returns:
        True if set successfully, False if flag not found
    """
    flag = get_flag(flag_name)
    if not flag:
        return False

    now = datetime.now(UTC)
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feature_flag_overrides (flag_id, user_id, enabled, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (flag_id, user_id) DO UPDATE SET enabled = EXCLUDED.enabled, updated_at = EXCLUDED.updated_at
                """,
                (flag.id, user_id, enabled, now, now),
            )
            conn.commit()
    return True


def delete_user_override(flag_name: str, user_id: str) -> bool:
    """Delete a per-user override for a flag.

    Args:
        flag_name: Flag name
        user_id: User ID

    Returns:
        True if deleted, False if not found
    """
    flag = get_flag(flag_name)
    if not flag:
        return False

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM feature_flag_overrides WHERE flag_id = %s AND user_id = %s RETURNING id",
                (flag.id, user_id),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                return True
            return False


def get_flags_for_user(user_id: str, tier: str | None = None) -> dict[str, bool]:
    """Get all flags evaluated for a specific user.

    Args:
        user_id: User ID
        tier: User's subscription tier

    Returns:
        Dict of flag_name -> enabled
    """
    flags = get_all_flags()
    return {flag.name: is_enabled(flag.name, user_id, tier) for flag in flags}
