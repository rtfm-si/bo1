"""Session monitoring background job.

Detects and alerts on runaway sessions:
- Duration exceeded (stuck sessions)
- Cost exceeded (runaway costs)
- Stale sessions (no recent events)

Can be run as:
- Standalone script via cron
- Background task in FastAPI via APScheduler
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from backend.services.alerts import alert_runaway_sessions_batch
from backend.services.monitoring import (
    DEFAULT_MAX_COST_USD,
    DEFAULT_MAX_DURATION_MINS,
    DEFAULT_STALE_MINS,
    detect_runaway_sessions,
)

logger = logging.getLogger(__name__)


async def check_runaway_sessions(
    max_duration_mins: float = DEFAULT_MAX_DURATION_MINS,
    max_cost_usd: float = DEFAULT_MAX_COST_USD,
    stale_mins: float = DEFAULT_STALE_MINS,
    send_alerts: bool = True,
) -> dict[str, Any]:
    """Check for runaway sessions and optionally send alerts.

    Args:
        max_duration_mins: Max session duration before flagged
        max_cost_usd: Max session cost before flagged
        stale_mins: Minutes since last event to consider stale
        send_alerts: Whether to send ntfy alerts

    Returns:
        Dict with detection results and alert status
    """
    result: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "runaway_count": 0,
        "by_reason": {"duration": 0, "cost": 0, "stale": 0},
        "sessions": [],
        "alert_sent": False,
    }

    try:
        # Detect runaway sessions
        runaways = detect_runaway_sessions(
            max_duration_mins=max_duration_mins,
            max_cost_usd=max_cost_usd,
            stale_mins=stale_mins,
        )

        result["runaway_count"] = len(runaways)

        for r in runaways:
            result["by_reason"][r.reason] = result["by_reason"].get(r.reason, 0) + 1
            result["sessions"].append(
                {
                    "session_id": r.session_id,
                    "user_id": r.user_id,
                    "reason": r.reason,
                    "duration_mins": round(r.duration_minutes, 1),
                    "cost_usd": round(r.cost_usd, 2),
                }
            )

        # Send alerts if runaway sessions found
        if runaways and send_alerts:
            alert_sent = await alert_runaway_sessions_batch(runaways)
            result["alert_sent"] = alert_sent
            if alert_sent:
                logger.info(f"Sent alert for {len(runaways)} runaway sessions")
            else:
                logger.warning("Failed to send runaway sessions alert")

        logger.info(f"Runaway check complete: {result['runaway_count']} sessions flagged")

    except Exception as e:
        logger.error(f"Runaway session check failed: {e}", exc_info=True)
        result["error"] = str(e)

    return result


def run_check_sync(
    max_duration_mins: float = DEFAULT_MAX_DURATION_MINS,
    max_cost_usd: float = DEFAULT_MAX_COST_USD,
    stale_mins: float = DEFAULT_STALE_MINS,
    send_alerts: bool = True,
) -> dict[str, Any]:
    """Synchronous wrapper for check_runaway_sessions.

    For use in schedulers that don't support async.
    """
    return asyncio.run(
        check_runaway_sessions(
            max_duration_mins=max_duration_mins,
            max_cost_usd=max_cost_usd,
            stale_mins=stale_mins,
            send_alerts=send_alerts,
        )
    )


if __name__ == "__main__":
    # CLI entry point for cron jobs or manual runs
    import argparse

    parser = argparse.ArgumentParser(description="Check for runaway sessions")
    parser.add_argument(
        "--max-duration",
        type=float,
        default=DEFAULT_MAX_DURATION_MINS,
        help=f"Max duration in minutes (default: {DEFAULT_MAX_DURATION_MINS})",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=DEFAULT_MAX_COST_USD,
        help=f"Max cost in USD (default: {DEFAULT_MAX_COST_USD})",
    )
    parser.add_argument(
        "--stale-mins",
        type=float,
        default=DEFAULT_STALE_MINS,
        help=f"Stale threshold in minutes (default: {DEFAULT_STALE_MINS})",
    )
    parser.add_argument(
        "--no-alerts",
        action="store_true",
        help="Don't send ntfy alerts",
    )
    args = parser.parse_args()

    result = run_check_sync(
        max_duration_mins=args.max_duration,
        max_cost_usd=args.max_cost,
        stale_mins=args.stale_mins,
        send_alerts=not args.no_alerts,
    )

    print(f"Check result: {result}")
