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
