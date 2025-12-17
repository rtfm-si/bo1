"""Beta meeting cap enforcement service.

Enforces a rolling 24-hour cap on meetings during beta:
- Max 4 meetings per rolling 24-hour window
- Check on meeting start and resume
- Provides cap status endpoint for UI
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from bo1.constants import BetaMeetingCap
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


@dataclass
class MeetingCapStatus:
    """Result of meeting cap check."""

    allowed: bool
    remaining: int
    limit: int
    reset_time: datetime | None
    exceeded: bool
    recent_count: int

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
            "reset_time": self.reset_time.isoformat() if self.reset_time else None,
            "exceeded": self.exceeded,
            "recent_count": self.recent_count,
        }


def get_recent_meeting_count(user_id: str, hours: int = 24) -> int:
    """Count meetings created by user in rolling window.

    Only counts sessions that were successfully started (status != 'created').
    Failed meetings do not count toward the cap.

    Args:
        user_id: User identifier
        hours: Rolling window in hours (default: 24)

    Returns:
        Number of meetings in the window
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM sessions
                    WHERE user_id = %s
                      AND created_at > %s
                      AND status NOT IN ('created', 'failed', 'deleted')
                    """,
                    (user_id, cutoff),
                )
                row = cur.fetchone()
                return row[0] if row else 0
    except Exception as e:
        logger.error(f"Failed to count meetings for user {user_id}: {e}")
        # Fail open to avoid blocking users on DB errors
        return 0


def get_oldest_meeting_time(user_id: str, hours: int = 24) -> datetime | None:
    """Get the creation time of the oldest meeting in the window.

    Used to calculate when a slot will free up.

    Args:
        user_id: User identifier
        hours: Rolling window in hours

    Returns:
        Creation time of oldest meeting, or None if no meetings
    """
    cutoff = datetime.now(UTC) - timedelta(hours=hours)

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT MIN(created_at)
                    FROM sessions
                    WHERE user_id = %s
                      AND created_at > %s
                      AND status NOT IN ('created', 'failed', 'deleted')
                    """,
                    (user_id, cutoff),
                )
                row = cur.fetchone()
                return row[0] if row and row[0] else None
    except Exception as e:
        logger.error(f"Failed to get oldest meeting time for user {user_id}: {e}")
        return None


def check_meeting_cap(user_id: str) -> MeetingCapStatus:
    """Check if user can start a new meeting under beta cap.

    Args:
        user_id: User identifier

    Returns:
        MeetingCapStatus with allowed status and details
    """
    # If cap is disabled, always allow
    if not BetaMeetingCap.is_enabled():
        return MeetingCapStatus(
            allowed=True,
            remaining=-1,
            limit=-1,
            reset_time=None,
            exceeded=False,
            recent_count=0,
        )

    limit = BetaMeetingCap.MAX_MEETINGS
    window_hours = BetaMeetingCap.WINDOW_HOURS

    recent_count = get_recent_meeting_count(user_id, window_hours)
    remaining = max(0, limit - recent_count)
    exceeded = recent_count >= limit
    allowed = not exceeded

    # Calculate reset time (when oldest meeting falls out of window)
    reset_time = None
    if exceeded:
        oldest_time = get_oldest_meeting_time(user_id, window_hours)
        if oldest_time:
            reset_time = oldest_time + timedelta(hours=window_hours)

    return MeetingCapStatus(
        allowed=allowed,
        remaining=remaining,
        limit=limit,
        reset_time=reset_time,
        exceeded=exceeded,
        recent_count=recent_count,
    )


def require_meeting_cap(user_id: str) -> MeetingCapStatus:
    """Check meeting cap and raise exception if exceeded.

    For use in endpoints that need to block on cap.

    Args:
        user_id: User identifier

    Returns:
        MeetingCapStatus if allowed

    Raises:
        MeetingCapExceededError: If cap is exceeded
    """
    status = check_meeting_cap(user_id)

    if not status.allowed:
        raise MeetingCapExceededError(status)

    return status


class MeetingCapExceededError(Exception):
    """Raised when meeting cap is exceeded."""

    def __init__(self, status: MeetingCapStatus) -> None:
        """Initialize with cap status for error message generation."""
        self.status = status
        reset_msg = ""
        if status.reset_time:
            # Format as human-readable relative time
            delta = status.reset_time - datetime.now(UTC)
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            if hours > 0:
                reset_msg = f" Try again in {hours}h {minutes}m."
            else:
                reset_msg = f" Try again in {minutes} minutes."

        super().__init__(
            f"Meeting limit reached ({status.limit} per {BetaMeetingCap.WINDOW_HOURS} hours).{reset_msg}"
        )
