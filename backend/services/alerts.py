"""Alert service for production monitoring.

Provides high-level alert functions that use ntfy.sh for delivery.
Used by monitoring service and background tasks.
Logs all alerts to database for audit trail.
"""

import logging
from typing import TYPE_CHECKING, Any

from backend.api.ntfy import notify_database_alert, send_ntfy_alert

if TYPE_CHECKING:
    from backend.services.monitoring import RunawaySessionResult

logger = logging.getLogger(__name__)


# =============================================================================
# ALERT LOGGING
# =============================================================================


async def log_alert(
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    delivered: bool,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log an alert to the database for audit trail.

    Args:
        alert_type: Type of alert (e.g., runaway_session, auth_failure_spike)
        severity: Severity level (info, warning, high, urgent, critical)
        title: Alert title
        message: Alert message body
        delivered: Whether ntfy delivery succeeded
        metadata: Optional additional context
    """
    try:
        import json

        from bo1.state.database import db_session

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO alert_history (alert_type, severity, title, message, metadata, delivered)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        alert_type,
                        severity,
                        title,
                        message,
                        json.dumps(metadata) if metadata else None,
                        delivered,
                    ),
                )
            conn.commit()
    except Exception as e:
        # Don't fail the alert if logging fails
        logger.warning(f"Failed to log alert to database: {e}")


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

    delivered = await notify_database_alert(
        alert_type="warning",
        title=title,
        message=message,
    )

    await log_alert(
        alert_type="runaway_session",
        severity="warning",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "session_id": result.session_id,
            "user_id": result.user_id,
            "reason": result.reason,
            "duration_minutes": result.duration_minutes,
            "cost_usd": result.cost_usd,
        },
    )

    return delivered


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
    by_reason: dict[str, int] = {"duration": 0, "cost": 0, "stale": 0}
    total_cost = 0.0
    session_ids = []
    for r in results:
        by_reason[r.reason] = by_reason.get(r.reason, 0) + 1
        total_cost += r.cost_usd
        session_ids.append(r.session_id)

    message = f"Found {len(results)} sessions exceeding thresholds:\n"
    if by_reason["duration"]:
        message += f"- Duration exceeded: {by_reason['duration']}\n"
    if by_reason["cost"]:
        message += f"- Cost exceeded: {by_reason['cost']}\n"
    if by_reason["stale"]:
        message += f"- Stale (no events): {by_reason['stale']}\n"
    message += f"\nTotal cost: ${total_cost:.2f}"

    severity = "critical" if len(results) > 3 else "warning"
    delivered = await notify_database_alert(
        alert_type=severity,
        title=title,
        message=message,
    )

    await log_alert(
        alert_type="runaway_sessions_batch",
        severity=severity,
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "session_count": len(results),
            "session_ids": session_ids[:10],  # Limit to first 10
            "by_reason": by_reason,
            "total_cost_usd": total_cost,
        },
    )

    return delivered


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

    severity = "high" if killed_by == "system" else "warning"
    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority=severity if severity == "high" else "default",
        tags=["skull", "warning"],
    )

    await log_alert(
        alert_type="session_killed",
        severity=severity,
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "session_id": session_id,
            "killed_by": killed_by,
            "reason": reason,
            "cost_usd": cost,
        },
    )

    return delivered


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

    title = "EMERGENCY: All Sessions Killed"
    message = f"Killed {killed_count} sessions\nBy: {killed_by}\nReason: {reason}"

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="urgent",
        tags=["rotating_light", "skull"],
    )

    await log_alert(
        alert_type="kill_all_sessions",
        severity="critical",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "killed_count": killed_count,
            "killed_by": killed_by,
            "reason": reason,
        },
    )

    return delivered


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

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )

    severity_map = {"outage": "critical", "degraded": "high", "operational": "info"}
    await log_alert(
        alert_type="service_degraded",
        severity=severity_map.get(new_status, "warning"),
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "service_name": service_name,
            "status": new_status,
            "error_rate": error_rate,
            "latency_p95": latency_p95,
            "last_error": last_error[:200] if last_error else None,
        },
    )

    return delivered


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

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="high",
        tags=["warning", "robot"],
    )

    await log_alert(
        alert_type="vendor_outage",
        severity="high",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "provider": provider,
            "error_rate": error_rate,
            "last_error": last_error[:200] if last_error else None,
        },
    )

    return delivered


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
        severity = "high"
    else:
        priority = "default"
        tags = ["chart_with_upwards_trend", "moneybag"]
        title = "User Approaching Cost Limit"
        severity = "warning"

    user_display = email or user_id[:12]
    message = (
        f"User: {user_display}\n"
        f"Cost: ${cost_usd:.2f} / ${limit_usd:.2f} ({percentage:.0f}%)\n"
        f"Status: {status}"
    )

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )

    await log_alert(
        alert_type="cost_threshold",
        severity=severity,
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "user_id": user_id,
            "email": email,
            "current_cost_cents": current_cost_cents,
            "limit_cents": limit_cents,
            "percentage": percentage,
            "status": status,
        },
    )

    return delivered


# =============================================================================
# SECURITY EVENT ALERTS
# =============================================================================


async def alert_auth_failure_spike(
    ip: str,
    count: int,
    window_minutes: int,
) -> bool:
    """Send alert for spike in authentication failures from single IP.

    Args:
        ip: Source IP address
        count: Number of failures in window
        window_minutes: Sliding window duration in minutes

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping auth failure alert")
        return False

    title = "Auth Failure Spike Detected"
    message = f"IP: {ip}\nFailures: {count} in {window_minutes} min\nPossible brute force attempt"

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="high",
        tags=["warning", "lock"],
    )

    await log_alert(
        alert_type="auth_failure_spike",
        severity="high",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "ip": ip,
            "count": count,
            "window_minutes": window_minutes,
        },
    )

    return delivered


async def alert_rate_limit_spike(
    ip: str,
    endpoint: str,
    count: int,
) -> bool:
    """Send alert for spike in rate limit hits from single IP.

    Args:
        ip: Source IP address
        endpoint: Most frequently hit endpoint
        count: Number of 429 responses in window

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping rate limit alert")
        return False

    title = "Rate Limit Spike Detected"
    message = (
        f"IP: {ip}\n"
        f"Endpoint: {endpoint or 'multiple'}\n"
        f"429 responses: {count}\n"
        "Possible abuse attempt"
    )

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="default",
        tags=["warning", "hourglass"],
    )

    await log_alert(
        alert_type="rate_limit_spike",
        severity="warning",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "ip": ip,
            "endpoint": endpoint,
            "count": count,
        },
    )

    return delivered


async def alert_rate_limiter_degraded(
    degraded_since: str,
    consecutive_failures: int,
) -> bool:
    """Send alert when rate limiter enters fail-open mode due to Redis unavailability.

    Args:
        degraded_since: ISO timestamp when degradation started
        consecutive_failures: Number of consecutive Redis failures

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping rate limiter degraded alert")
        return False

    title = "Rate Limiter Degraded (Fail-Open)"
    message = (
        f"Redis unavailable - rate limiting disabled\n"
        f"Since: {degraded_since}\n"
        f"Consecutive failures: {consecutive_failures}\n"
        "All requests passing through without rate limit checks"
    )

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="high",
        tags=["warning", "hourglass"],
    )

    await log_alert(
        alert_type="rate_limiter_degraded",
        severity="high",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "degraded_since": degraded_since,
            "consecutive_failures": consecutive_failures,
        },
    )

    return delivered


async def alert_rate_limiter_recovered() -> bool:
    """Send alert when rate limiter recovers from fail-open mode.

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping rate limiter recovery alert")
        return False

    title = "Rate Limiter Recovered"
    message = "Redis connectivity restored - rate limiting resumed"

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="default",
        tags=["white_check_mark", "hourglass"],
    )

    await log_alert(
        alert_type="rate_limiter_recovered",
        severity="info",
        title=title,
        message=message,
        delivered=delivered,
        metadata={},
    )

    return delivered


async def alert_lockout_spike(
    ip: str,
    count: int,
) -> bool:
    """Send alert for multiple lockouts from single IP.

    Args:
        ip: Source IP address
        count: Number of lockouts triggered

    Returns:
        True if alert sent successfully
    """
    topic = _get_ntfy_alerts_topic()
    if not topic:
        logger.debug("No alerts topic configured - skipping lockout alert")
        return False

    title = "Multiple Lockouts from IP"
    message = f"IP: {ip}\nLockouts: {count}\nSustained attack or compromised credentials"

    delivered = await send_ntfy_alert(
        topic=topic,
        title=title,
        message=message,
        priority="high",
        tags=["rotating_light", "lock"],
    )

    await log_alert(
        alert_type="lockout_spike",
        severity="high",
        title=title,
        message=message,
        delivered=delivered,
        metadata={
            "ip": ip,
            "count": count,
        },
    )

    return delivered
