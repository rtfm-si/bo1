"""GDPR audit logging service.

Provides:
- Audit logging for data export and deletion requests
- Query interface for audit trail
"""

import logging
from typing import Any

from psycopg2.extras import Json

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Valid GDPR audit actions
GDPR_ACTIONS = {
    "export_requested",
    "export_completed",
    "deletion_requested",
    "deletion_completed",
    "deletion_failed",
}


def log_gdpr_event(
    user_id: str,
    action: str,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> int | None:
    """Log a GDPR-related event to the audit trail.

    Args:
        user_id: User identifier
        action: Action type (export_requested, deletion_requested, etc.)
        details: Optional additional details
        ip_address: Client IP address

    Returns:
        Audit log entry ID if successful, None on error
    """
    if action not in GDPR_ACTIONS:
        logger.warning(f"Invalid GDPR action: {action}")
        return None

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO gdpr_audit_log (user_id, action, details, ip_address)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (user_id, action, Json(details) if details else None, ip_address),
                )
                row = cur.fetchone()
                log_id = row["id"] if row else None

        logger.info(f"GDPR audit log: user={user_id}, action={action}, id={log_id}")
        return log_id

    except Exception as e:
        logger.error(f"Failed to log GDPR event: {e}")
        return None


def get_user_audit_log(
    user_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get GDPR audit log entries for a user.

    Args:
        user_id: User identifier
        limit: Maximum entries to return

    Returns:
        List of audit log entries
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, action, details, ip_address, created_at
                    FROM gdpr_audit_log
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        logger.error(f"Failed to get audit log for user {user_id}: {e}")
        return []


def get_recent_export_request(user_id: str, window_hours: int = 24) -> dict[str, Any] | None:
    """Check if user has a recent export request within the window.

    Used for rate limiting - only allow one export per 24 hours.

    Args:
        user_id: User identifier
        window_hours: Time window in hours

    Returns:
        Most recent export request within window, or None
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_at
                    FROM gdpr_audit_log
                    WHERE user_id = %s
                      AND action = 'export_requested'
                      AND created_at > NOW() - INTERVAL '%s hours'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (user_id, window_hours),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    except Exception as e:
        logger.error(f"Failed to check recent export request: {e}")
        return None


def get_recent_deletion_request(user_id: str, window_hours: int = 24) -> dict[str, Any] | None:
    """Check if user has a recent deletion request within the window.

    Used for rate limiting and preventing accidental multiple deletions.

    Args:
        user_id: User identifier
        window_hours: Time window in hours

    Returns:
        Most recent deletion request within window, or None
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, action, created_at
                    FROM gdpr_audit_log
                    WHERE user_id = %s
                      AND action IN ('deletion_requested', 'deletion_completed')
                      AND created_at > NOW() - INTERVAL '%s hours'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (user_id, window_hours),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    except Exception as e:
        logger.error(f"Failed to check recent deletion request: {e}")
        return None
