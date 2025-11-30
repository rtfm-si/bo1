"""ntfy push notification service for admin alerts.

Handles:
- Waitlist signup notifications
- Meeting start notifications
"""

import logging
from typing import Literal

import httpx

from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Default ntfy server (self-hosted)
DEFAULT_NTFY_SERVER = "https://ntfy.boardof.one"


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

    settings = get_settings()
    server = settings.ntfy_server or DEFAULT_NTFY_SERVER
    url = f"{server.rstrip('/')}/{topic}"

    headers = {
        "Title": title,
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
    settings = get_settings()
    return await send_ntfy_alert(
        topic=settings.ntfy_topic_waitlist,
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
    settings = get_settings()
    # Truncate problem statement for notification
    truncated = (
        problem_statement[:100] + "..." if len(problem_statement) > 100 else problem_statement
    )

    return await send_ntfy_alert(
        topic=settings.ntfy_topic_meeting,
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
    """Send database monitoring report via ntfy.

    Args:
        report_type: Type of report (daily or weekly)
        summary: Brief summary of database health
        details: Optional detailed information
        priority: Notification priority (default: "default")

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
    settings = get_settings()

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
        topic=settings.ntfy_topic_reports,
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
    """Send urgent database alert via ntfy to dedicated alerts topic.

    Args:
        alert_type: Severity of alert
        title: Alert title
        message: Alert message

    Returns:
        True if notification sent successfully

    Example:
        >>> await notify_database_alert(
        ...     alert_type="critical",
        ...     title="Table Growth Alert",
        ...     message="api_costs table exceeded 500K rows - partitioning recommended"
        ... )
    """
    settings = get_settings()

    # Determine priority and tags based on alert type
    if alert_type == "critical":
        priority = "urgent"
        tags = ["rotating_light", "warning"]
    else:
        priority = "high"
        tags = ["warning"]

    return await send_ntfy_alert(
        topic=settings.ntfy_topic_alerts,  # Use dedicated alerts topic
        title=f"⚠️ {title}",
        message=message,
        priority=priority,
        tags=tags,
    )
