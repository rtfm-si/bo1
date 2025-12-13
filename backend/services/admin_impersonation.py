"""Admin impersonation service.

Provides:
- start_impersonation: Start impersonation session
- end_impersonation: End active impersonation
- get_active_impersonation: Get target user if impersonating
- is_impersonating: Check if admin is currently impersonating
"""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from bo1.state.database import db_session
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Redis key prefix for impersonation tokens
IMPERSONATION_PREFIX = "impersonation:"

# Default impersonation duration
DEFAULT_DURATION_MINUTES = 30


@dataclass
class ImpersonationSession:
    """Active impersonation session data."""

    admin_user_id: str
    target_user_id: str
    target_email: str | None
    reason: str
    is_write_mode: bool
    started_at: datetime
    expires_at: datetime
    session_id: int


def _get_redis() -> RedisManager:
    """Get Redis manager instance."""
    return RedisManager()


def start_impersonation(
    admin_id: str,
    target_user_id: str,
    reason: str,
    write_mode: bool = False,
    duration_minutes: int = DEFAULT_DURATION_MINUTES,
) -> ImpersonationSession | None:
    """Start an impersonation session.

    Args:
        admin_id: Admin user ID
        target_user_id: Target user to impersonate
        reason: Reason for impersonation (for audit)
        write_mode: Allow mutations if True (default: read-only)
        duration_minutes: Session duration (default: 30 minutes)

    Returns:
        ImpersonationSession if successful, None on error
    """
    # End any existing impersonation first
    end_impersonation(admin_id)

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=duration_minutes)

    try:
        # Get target user email for display
        target_email = None
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM users WHERE id = %s", (target_user_id,))
                row = cur.fetchone()
                if not row:
                    logger.error(f"Target user not found: {target_user_id}")
                    return None
                target_email = row["email"]

        # Create DB record
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO admin_impersonation_sessions
                        (admin_user_id, target_user_id, reason, is_write_mode, started_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (admin_id, target_user_id, reason, write_mode, now, expires_at),
                )
                row = cur.fetchone()
                session_id = row["id"] if row else 0

        # Store in Redis for fast lookup
        redis = _get_redis()
        if redis.is_available and redis.redis:
            key = f"{IMPERSONATION_PREFIX}{admin_id}"
            session_data = {
                "admin_user_id": admin_id,
                "target_user_id": target_user_id,
                "target_email": target_email,
                "reason": reason,
                "is_write_mode": write_mode,
                "started_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "session_id": session_id,
            }
            ttl_seconds = duration_minutes * 60
            redis.redis.setex(key, ttl_seconds, json.dumps(session_data))

        logger.info(
            f"Admin {admin_id} started impersonation of {target_user_id} "
            f"(write_mode={write_mode}, expires={expires_at.isoformat()})"
        )

        return ImpersonationSession(
            admin_user_id=admin_id,
            target_user_id=target_user_id,
            target_email=target_email,
            reason=reason,
            is_write_mode=write_mode,
            started_at=now,
            expires_at=expires_at,
            session_id=session_id,
        )

    except Exception as e:
        logger.error(f"Failed to start impersonation: {e}", exc_info=True)
        return None


def end_impersonation(admin_id: str) -> bool:
    """End the active impersonation session.

    Args:
        admin_id: Admin user ID

    Returns:
        True if session was ended, False if no active session
    """
    try:
        # Clear Redis first
        redis = _get_redis()
        if redis.is_available and redis.redis:
            key = f"{IMPERSONATION_PREFIX}{admin_id}"
            redis.redis.delete(key)

        # Update DB record
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE admin_impersonation_sessions
                    SET ended_at = NOW()
                    WHERE admin_user_id = %s
                      AND ended_at IS NULL
                      AND expires_at > NOW()
                    """,
                    (admin_id,),
                )
                if cur.rowcount > 0:
                    logger.info(f"Admin {admin_id} ended impersonation session")
                    return True

        return False

    except Exception as e:
        logger.error(f"Failed to end impersonation: {e}", exc_info=True)
        return False


def get_active_impersonation(admin_id: str) -> ImpersonationSession | None:
    """Get the active impersonation session for an admin.

    Checks Redis first for performance, falls back to DB.

    Args:
        admin_id: Admin user ID

    Returns:
        ImpersonationSession if active, None otherwise
    """
    try:
        # Check Redis first
        redis = _get_redis()
        if redis.is_available and redis.redis:
            key = f"{IMPERSONATION_PREFIX}{admin_id}"
            data = redis.redis.get(key)
            if data:
                session_data = json.loads(str(data))
                expires_at = datetime.fromisoformat(session_data["expires_at"])
                if expires_at > datetime.now(UTC):
                    return ImpersonationSession(
                        admin_user_id=session_data["admin_user_id"],
                        target_user_id=session_data["target_user_id"],
                        target_email=session_data.get("target_email"),
                        reason=session_data["reason"],
                        is_write_mode=session_data["is_write_mode"],
                        started_at=datetime.fromisoformat(session_data["started_at"]),
                        expires_at=expires_at,
                        session_id=session_data["session_id"],
                    )

        # Fallback to DB
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.admin_user_id, s.target_user_id, s.reason,
                           s.is_write_mode, s.started_at, s.expires_at,
                           u.email as target_email
                    FROM admin_impersonation_sessions s
                    JOIN users u ON u.id = s.target_user_id
                    WHERE s.admin_user_id = %s
                      AND s.ended_at IS NULL
                      AND s.expires_at > NOW()
                    ORDER BY s.started_at DESC
                    LIMIT 1
                    """,
                    (admin_id,),
                )
                row = cur.fetchone()
                if row:
                    return ImpersonationSession(
                        admin_user_id=row["admin_user_id"],
                        target_user_id=row["target_user_id"],
                        target_email=row["target_email"],
                        reason=row["reason"],
                        is_write_mode=row["is_write_mode"],
                        started_at=row["started_at"],
                        expires_at=row["expires_at"],
                        session_id=row["id"],
                    )

        return None

    except Exception as e:
        logger.error(f"Failed to get impersonation session: {e}", exc_info=True)
        return None


def is_impersonating(admin_id: str) -> bool:
    """Check if admin is currently impersonating a user.

    Args:
        admin_id: Admin user ID

    Returns:
        True if impersonating, False otherwise
    """
    return get_active_impersonation(admin_id) is not None


def get_impersonation_history(
    admin_id: str | None = None,
    target_user_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Get impersonation history for audit.

    Args:
        admin_id: Filter by admin user ID
        target_user_id: Filter by target user ID
        limit: Maximum records to return

    Returns:
        List of impersonation session records
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT s.id, s.admin_user_id, s.target_user_id, s.reason,
                           s.is_write_mode, s.started_at, s.expires_at, s.ended_at,
                           a.email as admin_email, t.email as target_email
                    FROM admin_impersonation_sessions s
                    JOIN users a ON a.id = s.admin_user_id
                    JOIN users t ON t.id = s.target_user_id
                    WHERE 1=1
                """
                params: list = []

                if admin_id:
                    query += " AND s.admin_user_id = %s"
                    params.append(admin_id)

                if target_user_id:
                    query += " AND s.target_user_id = %s"
                    params.append(target_user_id)

                query += " ORDER BY s.started_at DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, tuple(params))
                return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        logger.error(f"Failed to get impersonation history: {e}", exc_info=True)
        return []
