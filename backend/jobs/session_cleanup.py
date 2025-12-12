"""Session cleanup job for GDPR data retention compliance.

Provides:
- cleanup_expired_sessions: Delete sessions older than retention period
- cleanup_orphaned_redis_keys: Remove Redis keys for deleted sessions
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from bo1.config import get_settings
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Default retention period (days)
DEFAULT_RETENTION_DAYS = 365


def cleanup_expired_sessions(retention_days: int | None = None) -> dict[str, int]:
    """Delete sessions older than each user's configured retention period.

    Sessions are anonymized rather than hard-deleted to preserve
    aggregate statistics while complying with GDPR.

    Uses per-user data_retention_days from users table, falling back to
    DEFAULT_RETENTION_DAYS (365) if not set.

    Args:
        retention_days: Override retention period for all users (for testing).
                       If None, uses per-user settings.

    Returns:
        Dict with counts of deleted/anonymized records
    """
    stats = {
        "sessions_anonymized": 0,
        "actions_anonymized": 0,
        "events_deleted": 0,
        "contributions_deleted": 0,
        "errors": 0,
    }

    logger.info("Running session cleanup with per-user retention periods")

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get session IDs to clean up based on per-user retention
                # Join with users table to get each user's retention setting
                if retention_days is not None:
                    # Override mode: use fixed retention period (for testing)
                    cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)
                    logger.info(
                        f"Using override retention: {retention_days} days (cutoff: {cutoff_date.isoformat()})"
                    )
                    cur.execute(
                        """
                        SELECT id FROM sessions
                        WHERE created_at < %s
                          AND user_id IS NOT NULL
                        """,
                        (cutoff_date,),
                    )
                else:
                    # Per-user mode: use each user's data_retention_days setting
                    cur.execute(
                        """
                        SELECT s.id
                        FROM sessions s
                        JOIN users u ON s.user_id = u.id
                        WHERE s.created_at < NOW() - (COALESCE(u.data_retention_days, %s) || ' days')::interval
                          AND s.user_id IS NOT NULL
                        """,
                        (DEFAULT_RETENTION_DAYS,),
                    )
                session_ids = [row["id"] for row in cur.fetchall()]

                if not session_ids:
                    logger.info("No expired sessions to clean up")
                    return stats

                logger.info(f"Found {len(session_ids)} expired sessions to clean up")

                # Delete session events (high-volume, ok to hard delete)
                cur.execute(
                    """
                    DELETE FROM session_events
                    WHERE session_id = ANY(%s)
                    """,
                    (session_ids,),
                )
                stats["events_deleted"] = cur.rowcount

                # Delete contributions (high-volume, ok to hard delete)
                cur.execute(
                    """
                    DELETE FROM contributions
                    WHERE session_id = ANY(%s)
                    """,
                    (session_ids,),
                )
                stats["contributions_deleted"] = cur.rowcount

                # Anonymize actions (keep structure for reporting)
                cur.execute(
                    """
                    UPDATE actions
                    SET user_id = NULL,
                        title = 'Expired Action',
                        description = NULL,
                        updated_at = NOW()
                    WHERE source_session_id = ANY(%s)
                      AND user_id IS NOT NULL
                    """,
                    (session_ids,),
                )
                stats["actions_anonymized"] = cur.rowcount

                # Anonymize sessions (keep for aggregate stats)
                cur.execute(
                    """
                    UPDATE sessions
                    SET user_id = NULL,
                        problem_statement = '[EXPIRED]',
                        problem_context = NULL,
                        synthesis = NULL,
                        updated_at = NOW()
                    WHERE id = ANY(%s)
                    """,
                    (session_ids,),
                )
                stats["sessions_anonymized"] = cur.rowcount

        logger.info(f"Session cleanup complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Session cleanup failed: {e}", exc_info=True)
        stats["errors"] = 1
        return stats


def cleanup_orphaned_redis_keys() -> dict[str, int]:
    """Remove Redis keys for sessions that no longer exist.

    Cleans up:
    - Session state keys (session:{id}:*)
    - Rate limit keys for deleted users

    Returns:
        Dict with counts of deleted keys
    """
    import redis

    stats = {"keys_deleted": 0, "errors": 0}

    try:
        settings = get_settings()
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)

        # Get all session keys
        session_keys = list(r.scan_iter(match="session:*", count=1000))

        if not session_keys:
            logger.info("No Redis session keys to clean up")
            return stats

        # Extract session IDs from keys
        session_ids = set()
        for key in session_keys:
            parts = key.split(":")
            if len(parts) >= 2:
                session_ids.add(parts[1])

        # Check which sessions still exist
        existing_ids = set()
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM sessions WHERE id = ANY(%s)
                    """,
                    (list(session_ids),),
                )
                existing_ids = {row["id"] for row in cur.fetchall()}

        # Delete keys for non-existent sessions
        orphaned_ids = session_ids - existing_ids
        if orphaned_ids:
            for session_id in orphaned_ids:
                keys_to_delete = list(r.scan_iter(match=f"session:{session_id}:*", count=100))
                if keys_to_delete:
                    r.delete(*keys_to_delete)
                    stats["keys_deleted"] += len(keys_to_delete)

        logger.info(f"Redis cleanup complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Redis cleanup failed: {e}", exc_info=True)
        stats["errors"] = 1
        return stats


def run_all_cleanup(retention_days: int | None = None) -> dict[str, Any]:
    """Run all cleanup jobs.

    Args:
        retention_days: Override retention period in days. If None, uses per-user settings.

    Returns:
        Combined stats from all cleanup operations
    """
    mode = f"override: {retention_days} days" if retention_days else "per-user settings"
    logger.info(f"Starting full cleanup (mode: {mode})")

    session_stats = cleanup_expired_sessions(retention_days)
    redis_stats = cleanup_orphaned_redis_keys()

    combined = {
        "session_cleanup": session_stats,
        "redis_cleanup": redis_stats,
        "run_at": datetime.now(UTC).isoformat(),
    }

    logger.info(f"Full cleanup complete: {combined}")
    return combined


if __name__ == "__main__":
    # CLI entry point for cron jobs
    import argparse

    parser = argparse.ArgumentParser(description="Run session cleanup job")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help=f"Override retention period in days. If not set, uses per-user settings (default: {DEFAULT_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--sessions-only",
        action="store_true",
        help="Only clean up database sessions",
    )
    parser.add_argument(
        "--redis-only",
        action="store_true",
        help="Only clean up Redis keys",
    )
    args = parser.parse_args()

    if args.sessions_only:
        result = cleanup_expired_sessions(args.retention_days)
    elif args.redis_only:
        result = cleanup_orphaned_redis_keys()
    else:
        result = run_all_cleanup(args.retention_days)

    print(f"Cleanup result: {result}")
