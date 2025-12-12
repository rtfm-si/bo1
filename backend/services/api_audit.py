"""API audit logging service.

Provides:
- log_api_request: Insert request log to api_audit_log
- get_user_requests: Query logs by user_id (for admin/GDPR)
- cleanup_old_logs: Delete logs older than retention period
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Default retention period (days)
DEFAULT_RETENTION_DAYS = 30


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> int | None:
    """Log an API request to the audit trail.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        user_id: Authenticated user ID (optional)
        ip_address: Client IP address (optional)
        user_agent: User-Agent header (optional)
        request_id: Correlation ID (optional)

    Returns:
        Audit log entry ID if successful, None on error
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO api_audit_log
                        (method, path, user_id, status_code, duration_ms,
                         ip_address, user_agent, request_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        method,
                        path,
                        user_id,
                        status_code,
                        duration_ms,
                        ip_address,
                        user_agent,
                        request_id,
                    ),
                )
                row = cur.fetchone()
                return row["id"] if row else None

    except Exception as e:
        logger.error(f"Failed to log API request: {e}")
        return None


def get_user_requests(
    user_id: str,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Get API audit log entries for a user.

    Args:
        user_id: User identifier
        limit: Maximum entries to return
        offset: Number of entries to skip

    Returns:
        List of audit log entries
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, timestamp, method, path, status_code,
                           duration_ms, ip_address, user_agent, request_id
                    FROM api_audit_log
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset),
                )
                return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        logger.error(f"Failed to get audit log for user {user_id}: {e}")
        return []


def cleanup_old_logs(retention_days: int = DEFAULT_RETENTION_DAYS) -> dict[str, int]:
    """Delete audit logs older than the retention period.

    Args:
        retention_days: Number of days to retain logs (default: 30)

    Returns:
        Dict with count of deleted records
    """
    stats = {"deleted": 0, "errors": 0}
    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

    logger.info(f"Cleaning up API audit logs before {cutoff_date.isoformat()}")

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM api_audit_log
                    WHERE timestamp < %s
                    """,
                    (cutoff_date,),
                )
                stats["deleted"] = cur.rowcount

        logger.info(f"API audit cleanup complete: {stats['deleted']} rows deleted")
        return stats

    except Exception as e:
        logger.error(f"API audit cleanup failed: {e}", exc_info=True)
        stats["errors"] = 1
        return stats


def get_request_stats(
    hours: int = 24,
) -> dict[str, Any]:
    """Get aggregate request statistics for the time period.

    Args:
        hours: Number of hours to look back (default: 24)

    Returns:
        Dict with aggregate statistics
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_requests,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(duration_ms)::int as avg_duration_ms,
                        MAX(duration_ms) as max_duration_ms,
                        COUNT(*) FILTER (WHERE status_code >= 400) as error_count,
                        COUNT(*) FILTER (WHERE status_code >= 500) as server_error_count
                    FROM api_audit_log
                    WHERE timestamp > NOW() - INTERVAL '%s hours'
                    """,
                    (hours,),
                )
                row = cur.fetchone()
                return dict(row) if row else {}

    except Exception as e:
        logger.error(f"Failed to get request stats: {e}")
        return {}
