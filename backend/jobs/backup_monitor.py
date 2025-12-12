"""Backup health monitoring job.

Checks backup freshness and alerts if backups are too old.
Runs periodically to ensure backups are being created successfully.

Can be run as:
- Standalone script via cron
- Background task in FastAPI via APScheduler
"""

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.api.ntfy import send_ntfy_alert

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_BACKUP_DIR = "./backups/postgres"
DEFAULT_MAX_BACKUP_AGE_HOURS = 26  # Alert if backup older than 26 hours
DEFAULT_CRITICAL_AGE_HOURS = 48  # Critical if backup older than 48 hours


def get_latest_backup(backup_dir: str = DEFAULT_BACKUP_DIR) -> Path | None:
    """Find the most recent backup file.

    Args:
        backup_dir: Directory containing backup files

    Returns:
        Path to most recent backup or None if no backups found
    """
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return None

    # Find all .sql.gz files
    backups = list(backup_path.glob("*.sql.gz"))
    if not backups:
        return None

    # Return most recent by modification time
    return max(backups, key=lambda p: p.stat().st_mtime)


def get_backup_age_hours(backup_path: Path) -> float:
    """Get age of backup file in hours.

    Args:
        backup_path: Path to backup file

    Returns:
        Age in hours
    """
    mtime = datetime.fromtimestamp(backup_path.stat().st_mtime, tz=UTC)
    age = datetime.now(UTC) - mtime
    return age.total_seconds() / 3600


def check_backup_health(
    backup_dir: str = DEFAULT_BACKUP_DIR,
    max_age_hours: float = DEFAULT_MAX_BACKUP_AGE_HOURS,
    critical_age_hours: float = DEFAULT_CRITICAL_AGE_HOURS,
) -> dict[str, Any]:
    """Check backup health status.

    Args:
        backup_dir: Directory containing backup files
        max_age_hours: Warning threshold in hours
        critical_age_hours: Critical threshold in hours

    Returns:
        Dict with backup health status
    """
    result: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "backup_dir": backup_dir,
        "status": "ok",
        "latest_backup": None,
        "age_hours": None,
        "message": "",
    }

    latest = get_latest_backup(backup_dir)

    if latest is None:
        result["status"] = "critical"
        result["message"] = f"No backups found in {backup_dir}"
        return result

    result["latest_backup"] = str(latest.name)
    age_hours = get_backup_age_hours(latest)
    result["age_hours"] = round(age_hours, 1)

    if age_hours > critical_age_hours:
        result["status"] = "critical"
        result["message"] = (
            f"Backup is {age_hours:.1f}h old (critical threshold: {critical_age_hours}h)"
        )
    elif age_hours > max_age_hours:
        result["status"] = "warning"
        result["message"] = f"Backup is {age_hours:.1f}h old (warning threshold: {max_age_hours}h)"
    else:
        result["message"] = f"Backup is {age_hours:.1f}h old (healthy)"

    return result


async def alert_backup_status(status: dict[str, Any]) -> bool:
    """Send alert for backup health issue.

    Args:
        status: Result from check_backup_health()

    Returns:
        True if alert sent successfully
    """
    # Get ntfy topic from environment
    topic = os.environ.get("NTFY_TOPIC_ALERTS", "")
    if not topic:
        logger.debug("No NTFY_TOPIC_ALERTS configured - skipping backup alert")
        return False

    if status["status"] == "ok":
        return True  # No alert needed

    severity = status["status"]
    priority = "urgent" if severity == "critical" else "high"
    tags = (
        ["warning", "floppy_disk"] if severity == "warning" else ["rotating_light", "floppy_disk"]
    )

    title = f"Backup {severity.upper()}: PostgreSQL"
    message = status["message"]
    if status["latest_backup"]:
        message += f"\nLast backup: {status['latest_backup']}"
    if status["age_hours"]:
        message += f"\nAge: {status['age_hours']}h"

    return await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )


async def monitor_backups(
    backup_dir: str = DEFAULT_BACKUP_DIR,
    max_age_hours: float = DEFAULT_MAX_BACKUP_AGE_HOURS,
    critical_age_hours: float = DEFAULT_CRITICAL_AGE_HOURS,
    send_alerts: bool = True,
) -> dict[str, Any]:
    """Run backup monitoring check.

    Args:
        backup_dir: Directory containing backup files
        max_age_hours: Warning threshold in hours
        critical_age_hours: Critical threshold in hours
        send_alerts: Whether to send ntfy alerts

    Returns:
        Dict with monitoring results
    """
    status = check_backup_health(
        backup_dir=backup_dir,
        max_age_hours=max_age_hours,
        critical_age_hours=critical_age_hours,
    )

    if send_alerts and status["status"] != "ok":
        status["alert_sent"] = await alert_backup_status(status)
    else:
        status["alert_sent"] = False

    logger.info(
        "Backup monitor check: status=%s age=%sh alert=%s",
        status["status"],
        status.get("age_hours"),
        status.get("alert_sent", False),
    )

    return status


# CLI entrypoint for cron
def main() -> None:
    """CLI entrypoint for backup monitoring."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor backup health")
    parser.add_argument(
        "--backup-dir",
        default=os.environ.get("BACKUP_DIR", DEFAULT_BACKUP_DIR),
        help="Backup directory path",
    )
    parser.add_argument(
        "--max-age",
        type=float,
        default=DEFAULT_MAX_BACKUP_AGE_HOURS,
        help="Warning threshold in hours",
    )
    parser.add_argument(
        "--critical-age",
        type=float,
        default=DEFAULT_CRITICAL_AGE_HOURS,
        help="Critical threshold in hours",
    )
    parser.add_argument(
        "--no-alert",
        action="store_true",
        help="Skip sending alerts",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

    result = asyncio.run(
        monitor_backups(
            backup_dir=args.backup_dir,
            max_age_hours=args.max_age,
            critical_age_hours=args.critical_age,
            send_alerts=not args.no_alert,
        )
    )

    if args.json:
        import json

        print(json.dumps(result, indent=2))
    else:
        print(f"Status: {result['status']}")
        print(f"Latest: {result.get('latest_backup', 'None')}")
        print(f"Age: {result.get('age_hours', 'N/A')}h")
        print(f"Message: {result['message']}")
        if result.get("alert_sent"):
            print("Alert: Sent")

    # Exit with appropriate code
    if result["status"] == "critical":
        exit(2)
    elif result["status"] == "warning":
        exit(1)
    exit(0)


if __name__ == "__main__":
    main()
