"""Audit log cleanup job for data retention compliance.

Provides:
- cleanup_api_audit_logs: Delete audit logs older than retention period
- run_cleanup: CLI entry point for cron jobs

Default retention: 30 days (configurable via AUDIT_LOG_RETENTION_DAYS env var)
"""

import logging
import os
from datetime import UTC, datetime

from backend.services.api_audit import cleanup_old_logs

logger = logging.getLogger(__name__)

# Default retention from env or fallback
DEFAULT_RETENTION_DAYS = int(os.environ.get("AUDIT_LOG_RETENTION_DAYS", "30"))


def run_cleanup(retention_days: int | None = None) -> dict[str, int]:
    """Run the audit log cleanup job.

    Args:
        retention_days: Override retention period (uses env default if None)

    Returns:
        Dict with cleanup statistics
    """
    days = retention_days if retention_days is not None else DEFAULT_RETENTION_DAYS
    logger.info(f"Starting API audit log cleanup (retention: {days} days)")

    stats = cleanup_old_logs(days)
    stats["run_at"] = datetime.now(UTC).isoformat()
    stats["retention_days"] = days

    logger.info(f"Audit log cleanup complete: {stats}")
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run API audit log cleanup job")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help=f"Retention period in days (default: {DEFAULT_RETENTION_DAYS} from env)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting",
    )
    args = parser.parse_args()

    if args.dry_run:
        from datetime import timedelta

        from bo1.state.database import db_session

        days = args.retention_days or DEFAULT_RETENTION_DAYS
        cutoff = datetime.now(UTC) - timedelta(days=days)

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) as count FROM api_audit_log WHERE timestamp < %s",
                    (cutoff,),
                )
                row = cur.fetchone()
                count = row["count"] if row else 0

        print(f"Dry run: would delete {count} audit log entries older than {cutoff}")
    else:
        result = run_cleanup(args.retention_days)
        print(f"Cleanup result: {result}")
