"""Alert service for production monitoring.

Provides high-level alert functions that use ntfy.sh for delivery.
Used by monitoring service and background tasks.
"""

import logging
from typing import TYPE_CHECKING

from backend.api.ntfy import notify_database_alert, send_ntfy_alert

if TYPE_CHECKING:
    from backend.services.monitoring import RunawaySessionResult

logger = logging.getLogger(__name__)


def _get_ntfy_alerts_topic() -> str:
    """Get the alerts topic from settings."""
    try:
        from bo1.config import get_settings

        return get_settings().ntfy_topic_alerts
    except ImportError:
        import os

        return os.environ.get("NTFY_TOPIC_ALERTS", "")


async def alert_runaway_session(result: "RunawaySessionResult") -> bool:
    """Send alert for a runaway session.

    Args:
        result: RunawaySessionResult from monitoring detection

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping runaway alert")
        return False

    title = f"Runaway Session: {result.reason}"
    message = (
        f"Session: {result.session_id[:12]}...\n"
        f"User: {result.user_id}\n"
        f"Reason: {result.reason_description}\n"
        f"Duration: {result.duration_minutes:.1f} mins\n"
        f"Cost: ${result.cost_usd:.2f}"
    )

    return await notify_database_alert(
        alert_type="warning",
        title=title,
        message=message,
    )


async def alert_runaway_sessions_batch(
    results: list["RunawaySessionResult"],
) -> bool:
    """Send batch alert for multiple runaway sessions.

    Args:
        results: List of RunawaySessionResult from monitoring

    Returns:
        True if alert sent successfully
    """
    if not results:
        return True

    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping batch runaway alert")
        return False

    # Single alert vs batch
    if len(results) == 1:
        return await alert_runaway_session(results[0])

    # Batch alert
    title = f"{len(results)} Runaway Sessions Detected"

    # Summarize by reason
    by_reason = {"duration": 0, "cost": 0, "stale": 0}
    total_cost = 0.0
    for r in results:
        by_reason[r.reason] = by_reason.get(r.reason, 0) + 1
        total_cost += r.cost_usd

    message = f"Found {len(results)} sessions exceeding thresholds:\n"
    if by_reason["duration"]:
        message += f"- Duration exceeded: {by_reason['duration']}\n"
    if by_reason["cost"]:
        message += f"- Cost exceeded: {by_reason['cost']}\n"
    if by_reason["stale"]:
        message += f"- Stale (no events): {by_reason['stale']}\n"
    message += f"\nTotal cost: ${total_cost:.2f}"

    return await notify_database_alert(
        alert_type="critical" if len(results) > 3 else "warning",
        title=title,
        message=message,
    )


async def alert_session_killed(
    session_id: str,
    killed_by: str,
    reason: str,
    cost: float | None = None,
) -> bool:
    """Send alert when a session is killed.

    Args:
        session_id: Session that was killed
        killed_by: Who killed it (user ID or 'system')
        reason: Reason for kill
        cost: Session cost at time of kill

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        return False

    title = "Session Killed"
    message = f"Session: {session_id[:12]}...\nKilled by: {killed_by}\nReason: {reason}"
    if cost is not None:
        message += f"\nCost at kill: ${cost:.2f}"

    return await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="high" if killed_by == "system" else "default",
        tags=["skull", "warning"],
    )


async def alert_kill_all_sessions(
    killed_count: int,
    killed_by: str,
    reason: str,
) -> bool:
    """Send urgent alert when all sessions are killed.

    Args:
        killed_count: Number of sessions killed
        killed_by: Who performed the kill-all
        reason: Reason for emergency shutdown

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        return False

    return await send_ntfy_alert(
        topic=topic,
        title="EMERGENCY: All Sessions Killed",
        message=(f"Killed {killed_count} sessions\nBy: {killed_by}\nReason: {reason}"),
        priority="urgent",
        tags=["rotating_light", "skull"],
    )


async def alert_service_degraded(
    service_name: str,
    new_status: str,
    details: dict,
) -> bool:
    """Send alert when a service status changes.

    Args:
        service_name: Name of affected service
        new_status: New status (degraded, outage, operational)
        details: Dict with error_rate, latency_p95, last_error

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping service alert")
        return False

    # Determine priority and tags based on status
    if new_status == "outage":
        priority = "urgent"
        tags = ["rotating_light", "x"]
        title = f"SERVICE OUTAGE: {service_name}"
    elif new_status == "degraded":
        priority = "high"
        tags = ["warning", "chart_with_downwards_trend"]
        title = f"Service Degraded: {service_name}"
    else:
        # Recovery
        priority = "default"
        tags = ["white_check_mark", "chart_with_upwards_trend"]
        title = f"Service Recovered: {service_name}"

    error_rate = details.get("error_rate", 0)
    latency_p95 = details.get("latency_p95")
    last_error = details.get("last_error")

    message = f"Service: {service_name}\nStatus: {new_status}\nError rate: {error_rate:.1%}"
    if latency_p95:
        message += f"\nLatency p95: {latency_p95:.0f}ms"
    if last_error and new_status != "operational":
        message += f"\nLast error: {last_error[:100]}"

    return await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )


async def alert_vendor_outage(
    provider: str,
    error_rate: float,
    last_error: str | None = None,
) -> bool:
    """Send alert when an LLM provider is experiencing issues.

    Args:
        provider: Provider name (anthropic, openai)
        error_rate: Current error rate (0-1)
        last_error: Most recent error message

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        return False

    title = f"LLM Provider Issues: {provider.upper()}"
    message = f"Provider: {provider}\nError rate: {error_rate:.1%}"
    if last_error:
        message += f"\nLast error: {last_error[:150]}"

    return await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="high",
        tags=["warning", "robot"],
    )


async def alert_user_cost_threshold(
    user_id: str,
    email: str | None,
    current_cost_cents: int,
    limit_cents: int,
    status: str,
) -> bool:
    """Send alert when a user exceeds cost threshold (admin monitoring).

    Args:
        user_id: User ID
        email: User email (if available)
        current_cost_cents: Current period cost in cents
        limit_cents: Configured limit in cents
        status: Budget status (warning, exceeded)

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping user cost alert")
        return False

    percentage = (current_cost_cents / limit_cents) * 100 if limit_cents > 0 else 0
    cost_usd = current_cost_cents / 100
    limit_usd = limit_cents / 100

    if status == "exceeded":
        priority = "high"
        tags = ["warning", "moneybag"]
        title = "User Cost Limit Exceeded"
    else:
        priority = "default"
        tags = ["chart_with_upwards_trend", "moneybag"]
        title = "User Approaching Cost Limit"

    user_display = email or user_id[:12]
    message = (
        f"User: {user_display}\n"
        f"Cost: ${cost_usd:.2f} / ${limit_usd:.2f} ({percentage:.0f}%)\n"
        f"Status: {status}"
    )

    return await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )
