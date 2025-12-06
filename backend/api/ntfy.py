"""ntfy push notification service for admin notifications.

Topics:
- Waitlist: User acquisition events
- Meetings: Meeting start notifications
- Reports: Standard performance updates (daily/weekly metrics)
- Alerts: Warnings and abnormal events requiring attention
"""

import logging
import os
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# Default ntfy server (self-hosted)
DEFAULT_NTFY_SERVER = "https://ntfy.boardof.one"


def _get_ntfy_settings() -> dict:
    """Get ntfy settings from bo1.config or environment variables.

    Falls back to environment variables when bo1.config is not available
    (e.g., in lightweight CI workflows without full dependencies).
    """
    try:
        from bo1.config import get_settings

        settings = get_settings()
        return {
            "ntfy_server": settings.ntfy_server,
            "ntfy_topic_waitlist": settings.ntfy_topic_waitlist,
            "ntfy_topic_meeting": settings.ntfy_topic_meeting,
            "ntfy_topic_reports": settings.ntfy_topic_reports,
            "ntfy_topic_alerts": settings.ntfy_topic_alerts,
        }
    except ImportError:
        # Fallback to environment variables (for CI workflows)
        return {
            "ntfy_server": os.environ.get("NTFY_SERVER"),
            "ntfy_topic_waitlist": os.environ.get("NTFY_TOPIC_WAITLIST"),
            "ntfy_topic_meeting": os.environ.get("NTFY_TOPIC_MEETING"),
            "ntfy_topic_reports": os.environ.get("NTFY_TOPIC_REPORTS"),
            "ntfy_topic_alerts": os.environ.get("NTFY_TOPIC_ALERTS"),
        }


async def send_ntfy_alert(
    topic: str,
    title: str,
    message: str,
    priority: Literal["min", "low", "default", "high", "urgent"] = "default",
    tags: list[str] | None = None,
) -> bool:
    """Send a push notification via ntfy.

    Args:
        topic: ntfy topic to publish to
        title: Notification title
        message: Notification body
        priority: Priority level (affects sound/vibration)
        tags: List of emoji tags (e.g., ["tada", "wave"])

    Returns:
        True if notification sent successfully, False otherwise

    Example:
        >>> await send_ntfy_alert(
        ...     topic="bo1-waitlist",
        ...     title="New Waitlist Signup",
        ...     message="alice@example.com joined the waitlist",
        ...     tags=["wave"]
        ... )
    """
    if not topic:
        logger.debug("No ntfy topic provided - skipping notification")
        return False

    settings = _get_ntfy_settings()
    server = settings["ntfy_server"] or DEFAULT_NTFY_SERVER
    url = f"{server.rstrip('/')}/{topic}"

    # Encode title for HTTP header (ntfy requires ASCII-safe encoding for headers)
    # Strip non-ASCII characters and any resulting leading/trailing whitespace
    safe_title = title.encode("ascii", "ignore").decode("ascii").strip()
    if not safe_title:
        safe_title = "Notification"

    headers = {
        "Title": safe_title,
        "Priority": priority,
    }

    if tags:
        headers["Tags"] = ",".join(tags)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, content=message, headers=headers)
            response.raise_for_status()

        logger.info(f"ntfy alert sent: {title}")
        return True

    except httpx.HTTPError as e:
        logger.error(f"Failed to send ntfy alert: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending ntfy alert: {e}")
        return False


async def notify_waitlist_signup(email: str) -> bool:
    """Send notification for new waitlist signup.

    Args:
        email: Email address that signed up

    Returns:
        True if notification sent successfully
    """
    settings = _get_ntfy_settings()
    return await send_ntfy_alert(
        topic=settings["ntfy_topic_waitlist"],
        title="New Waitlist Signup",
        message=f"{email} joined the Board of One waitlist",
        priority="default",
        tags=["wave", "email"],
    )


async def notify_meeting_started(session_id: str, problem_statement: str) -> bool:
    """Send notification when a meeting starts.

    Args:
        session_id: The session/meeting ID
        problem_statement: The problem being deliberated

    Returns:
        True if notification sent successfully
    """
    settings = _get_ntfy_settings()
    # Truncate problem statement for notification
    truncated = (
        problem_statement[:100] + "..." if len(problem_statement) > 100 else problem_statement
    )

    return await send_ntfy_alert(
        topic=settings["ntfy_topic_meeting"],
        title="Meeting Started",
        message=f"Session {session_id[:8]}...\n\n{truncated}",
        priority="default",
        tags=["rocket", "brain"],
    )


async def notify_database_report(
    report_type: Literal["daily", "weekly"],
    summary: str,
    details: str | None = None,
    priority: Literal["min", "low", "default", "high", "urgent"] = "default",
) -> bool:
    r"""Send standard database performance report via ntfy.

    Use this for routine, scheduled updates - NOT for warnings or issues.
    For abnormal events, use notify_database_alert() instead.

    Args:
        report_type: Type of report (daily or weekly)
        summary: Brief summary of database metrics
        details: Optional detailed performance information
        priority: Notification priority (typically "low" or "default")

    Returns:
        True if notification sent successfully

    Example:
        >>> await notify_database_report(
        ...     report_type="daily",
        ...     summary="✅ All systems healthy",
        ...     details="api_costs: 3,048 rows\\nsession_events: 445 rows",
        ...     priority="low"
        ... )
    """
    settings = _get_ntfy_settings()

    # Determine tags and title based on report type
    if report_type == "daily":
        title = "📊 Daily Database Report"
        tags = ["bar_chart", "calendar"]
    else:
        title = "📈 Weekly Database Report"
        tags = ["chart_with_upwards_trend", "calendar"]

    # Build message
    message = summary
    if details:
        message += f"\n\n{details}"

    return await send_ntfy_alert(
        topic=settings["ntfy_topic_reports"],
        title=title,
        message=message,
        priority=priority,
        tags=tags,
    )


async def notify_database_alert(
    alert_type: Literal["warning", "critical"],
    title: str,
    message: str,
) -> bool:
    """Send alert for warnings and abnormal events via ntfy.

    Use this for issues requiring attention - NOT for routine updates.
    For standard performance reports, use notify_database_report() instead.

    Args:
        alert_type: Severity - "warning" for attention needed, "critical" for urgent
        title: Alert title (will be prefixed with ⚠️)
        message: Alert details

    Returns:
        True if notification sent successfully

    Example:
        >>> await notify_database_alert(
        ...     alert_type="warning",
        ...     title="High Table Growth",
        ...     message="api_costs grew 50% this week - monitor closely"
        ... )
        >>> await notify_database_alert(
        ...     alert_type="critical",
        ...     title="Database Connection Failed",
        ...     message="Cannot connect to PostgreSQL - immediate action required"
        ... )
    """
    settings = _get_ntfy_settings()

    # Determine priority and tags based on alert type
    if alert_type == "critical":
        priority = "urgent"
        tags = ["rotating_light", "warning"]
    else:
        priority = "high"
        tags = ["warning"]

    return await send_ntfy_alert(
        topic=settings["ntfy_topic_alerts"],  # Use dedicated alerts topic
        title=f"⚠️ {title}",
        message=message,
        priority=priority,
        tags=tags,
    )
