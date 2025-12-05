#!/usr/bin/env python3
"""Check if daily database report has run recently.

This script should be run hourly via cron to detect if the daily report
hasn't run in the last 25 hours (meaning it missed its 9 AM UTC window).

Usage:
    python scripts/check_report_heartbeat.py

The heartbeat is tracked via a file at /tmp/bo1_report_heartbeat.
The daily report should update this file when it runs successfully.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

HEARTBEAT_FILE = Path("/tmp/bo1_report_heartbeat")  # noqa: S108
ALERT_THRESHOLD_HOURS = 25  # Alert if no heartbeat in 25 hours


def check_heartbeat() -> bool:
    """Check if the heartbeat is recent enough.

    Returns:
        True if heartbeat is healthy, False if stale/missing
    """
    if not HEARTBEAT_FILE.exists():
        print(f"Heartbeat file not found: {HEARTBEAT_FILE}")
        return False

    try:
        content = HEARTBEAT_FILE.read_text().strip()
        last_beat = datetime.fromisoformat(content)

        # Ensure timezone-aware comparison
        if last_beat.tzinfo is None:
            last_beat = last_beat.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        age_hours = (now - last_beat).total_seconds() / 3600

        print(f"Last heartbeat: {last_beat.isoformat()}")
        print(f"Age: {age_hours:.1f} hours")

        if age_hours > ALERT_THRESHOLD_HOURS:
            print(f"STALE: Heartbeat is older than {ALERT_THRESHOLD_HOURS} hours!")
            return False

        print("Heartbeat is healthy")
        return True

    except Exception as e:
        print(f"Error reading heartbeat: {e}")
        return False


def update_heartbeat():
    """Update the heartbeat file with current timestamp."""
    now = datetime.now(UTC).isoformat()
    HEARTBEAT_FILE.write_text(now)
    print(f"Updated heartbeat: {now}")


def send_alert():
    """Send alert that daily report hasn't run."""
    try:
        import asyncio

        from backend.api.ntfy import notify_database_alert

        asyncio.run(
            notify_database_alert(
                title="Daily Report Missing!",
                message=(
                    f"The daily database report hasn't run in over {ALERT_THRESHOLD_HOURS} hours.\n"
                    f"Last expected: 9:00 AM UTC\n"
                    f"Check cron job and server health."
                ),
                priority="high",
            )
        )
        print("Alert sent via ntfy")
    except Exception as e:
        print(f"Failed to send alert: {e}")
        # Also try to log to stderr for cron email
        sys.stderr.write(
            f"ALERT: Daily database report hasn't run in {ALERT_THRESHOLD_HOURS}+ hours!\n"
        )


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        # Called by the daily report to update heartbeat
        update_heartbeat()
        return

    # Check heartbeat and alert if stale
    if not check_heartbeat():
        send_alert()
        sys.exit(1)


if __name__ == "__main__":
    main()
