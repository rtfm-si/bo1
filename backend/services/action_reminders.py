"""Action reminder calculation and management service.

Provides:
- Reminder calculation based on anticipated start and deadline dates
- Frequency-aware reminder scheduling
- Snooze functionality
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from pydantic import BaseModel

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Default reminder settings
DEFAULT_REMINDER_FREQUENCY_DAYS = 3
MIN_REMINDER_FREQUENCY_DAYS = 1
MAX_REMINDER_FREQUENCY_DAYS = 14
DEFAULT_DEADLINE_WARNING_DAYS = 3  # Warn N days before deadline


class ActionReminder(BaseModel):
    """Reminder info for an action."""

    action_id: str
    action_title: str
    reminder_type: str  # 'start_overdue' or 'deadline_approaching'
    due_date: datetime | None
    days_overdue: int | None = None  # For start_overdue
    days_until_deadline: int | None = None  # For deadline_approaching
    session_id: str
    problem_statement: str


class ReminderSettings(BaseModel):
    """Reminder settings for an action."""

    action_id: str
    reminders_enabled: bool
    reminder_frequency_days: int
    snoozed_until: datetime | None
    last_reminder_sent_at: datetime | None


def _to_datetime(value: Any) -> datetime | None:
    """Convert date or datetime to naive datetime (for comparison with utcnow)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        # Strip timezone info to make naive (for comparison with utcnow)
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    # It's a date object
    return datetime.combine(value, datetime.min.time())


def calculate_start_reminder(action: dict[str, Any]) -> datetime | None:
    """Calculate when to send a start reminder.

    Returns a reminder date if:
    - Action has a target_start_date or estimated_start_date
    - That date has passed
    - Action is still in 'todo' status (not started)
    - Reminders are enabled

    Args:
        action: Action dict from database

    Returns:
        Reminder datetime if applicable, None otherwise
    """
    if action.get("status") not in ("todo",):
        return None

    if not action.get("reminders_enabled", True):
        return None

    # Check for start date
    start_date = action.get("target_start_date") or action.get("estimated_start_date")
    if not start_date:
        return None

    start_datetime = _to_datetime(start_date)
    if not start_datetime:
        return None

    now = datetime.utcnow()

    # If start date has passed, reminder is due
    if start_datetime < now:
        return start_datetime

    return None


def calculate_deadline_reminder(
    action: dict[str, Any],
    warning_days: int = DEFAULT_DEADLINE_WARNING_DAYS,
) -> datetime | None:
    """Calculate when to send a deadline reminder.

    Returns a reminder date if:
    - Action has a target_end_date or estimated_end_date
    - Deadline is within warning_days
    - Action is not done/cancelled
    - Reminders are enabled
    - Action has not been updated recently (>2 days ago)

    Args:
        action: Action dict from database
        warning_days: Days before deadline to start warning

    Returns:
        Reminder datetime if applicable, None otherwise
    """
    if action.get("status") in ("done", "cancelled"):
        return None

    if not action.get("reminders_enabled", True):
        return None

    # Check for deadline
    deadline = action.get("target_end_date") or action.get("estimated_end_date")
    if not deadline:
        return None

    deadline_datetime = _to_datetime(deadline)
    if not deadline_datetime:
        return None

    now = datetime.utcnow()

    # Check if deadline is within warning window
    days_until = (deadline_datetime - now).days
    if days_until > warning_days:
        return None

    # Check if action was updated recently (indicates activity)
    updated_at = _to_datetime(action.get("updated_at"))
    if updated_at:
        days_since_update = (now - updated_at).days
        if days_since_update < 2:
            # Recent activity, don't remind yet
            return None

    return deadline_datetime


def should_send_reminder(action: dict[str, Any]) -> bool:
    """Check if a reminder should be sent based on frequency.

    Args:
        action: Action dict from database

    Returns:
        True if enough time has passed since last reminder
    """
    if not action.get("reminders_enabled", True):
        return False

    # Check snooze
    snoozed_until = action.get("snoozed_until")
    if snoozed_until:
        if datetime.utcnow() < snoozed_until:
            return False

    # Check frequency
    frequency_days = action.get("reminder_frequency_days") or DEFAULT_REMINDER_FREQUENCY_DAYS
    last_sent = action.get("last_reminder_sent_at")

    if not last_sent:
        return True

    days_since = (datetime.utcnow() - last_sent).days
    return days_since >= frequency_days


def get_pending_reminders(user_id: str, limit: int = 50) -> list[ActionReminder]:
    """Get all actions needing reminders for a user.

    Returns actions that:
    - Have overdue start dates (todo status with passed anticipated start)
    - Have approaching deadlines (within 3 days)
    - Respect reminder frequency (not sent too recently)
    - Are not snoozed

    Args:
        user_id: User ID
        limit: Maximum reminders to return

    Returns:
        List of ActionReminder objects
    """
    reminders: list[ActionReminder] = []
    now = datetime.utcnow()

    with db_session(user_id=user_id) as conn:
        with conn.cursor() as cur:
            # Query for pending actions that might need reminders
            cur.execute(
                """
                SELECT
                    a.id, a.title, a.status,
                    a.target_start_date, a.estimated_start_date,
                    a.target_end_date, a.estimated_end_date,
                    a.reminders_enabled, a.reminder_frequency_days,
                    a.last_reminder_sent_at, a.snoozed_until,
                    a.updated_at, a.source_session_id,
                    s.problem_statement
                FROM actions a
                LEFT JOIN sessions s ON a.source_session_id = s.id
                WHERE a.user_id = %s
                  AND a.status NOT IN ('done', 'cancelled')
                  AND a.deleted_at IS NULL
                  AND a.reminders_enabled = true
                  AND (a.snoozed_until IS NULL OR a.snoozed_until <= NOW())
                ORDER BY COALESCE(a.target_end_date, a.estimated_end_date) ASC NULLS LAST
                LIMIT %s
                """,
                (user_id, limit * 2),  # Fetch extra since we'll filter
            )

            rows = cur.fetchall()

            for row in rows:
                action = dict(row)

                # Check if reminder should be sent
                if not should_send_reminder(action):
                    continue

                # Check for start overdue
                start_reminder = calculate_start_reminder(action)
                if start_reminder and action.get("status") == "todo":
                    days_overdue = (now - start_reminder).days
                    reminders.append(
                        ActionReminder(
                            action_id=str(action["id"]),
                            action_title=action["title"],
                            reminder_type="start_overdue",
                            due_date=start_reminder,
                            days_overdue=days_overdue,
                            session_id=action["source_session_id"] or "",
                            problem_statement=action.get("problem_statement") or "",
                        )
                    )
                    continue  # Don't also send deadline reminder

                # Check for deadline approaching
                deadline_reminder = calculate_deadline_reminder(action)
                if deadline_reminder:
                    days_until = (deadline_reminder - now).days
                    reminders.append(
                        ActionReminder(
                            action_id=str(action["id"]),
                            action_title=action["title"],
                            reminder_type="deadline_approaching",
                            due_date=deadline_reminder,
                            days_until_deadline=max(0, days_until),
                            session_id=action["source_session_id"] or "",
                            problem_statement=action.get("problem_statement") or "",
                        )
                    )

                if len(reminders) >= limit:
                    break

    return reminders


def snooze_reminder(
    action_id: str,
    user_id: str,
    snooze_days: int = 1,
) -> bool:
    """Snooze reminders for an action.

    Args:
        action_id: Action UUID
        user_id: User ID (for ownership check)
        snooze_days: Days to snooze (1-14)

    Returns:
        True if successful
    """
    snooze_days = max(1, min(14, snooze_days))
    snooze_until = datetime.utcnow() + timedelta(days=snooze_days)

    with db_session(user_id=user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE actions
                SET snoozed_until = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING id
                """,
                (snooze_until, action_id, user_id),
            )
            result = cur.fetchone()
            return result is not None


def update_reminder_settings(
    action_id: str,
    user_id: str,
    reminders_enabled: bool | None = None,
    reminder_frequency_days: int | None = None,
) -> ReminderSettings | None:
    """Update reminder settings for an action.

    Args:
        action_id: Action UUID
        user_id: User ID (for ownership check)
        reminders_enabled: Enable/disable reminders
        reminder_frequency_days: Days between reminders (1-14)

    Returns:
        Updated ReminderSettings or None if action not found
    """
    updates = []
    params: list[Any] = []

    if reminders_enabled is not None:
        updates.append("reminders_enabled = %s")
        params.append(reminders_enabled)

    if reminder_frequency_days is not None:
        # Validate range
        freq = max(
            MIN_REMINDER_FREQUENCY_DAYS, min(MAX_REMINDER_FREQUENCY_DAYS, reminder_frequency_days)
        )
        updates.append("reminder_frequency_days = %s")
        params.append(freq)

    if not updates:
        # No changes, just return current settings
        return get_reminder_settings(action_id, user_id)

    updates.append("updated_at = NOW()")
    params.extend([action_id, user_id])

    with db_session(user_id=user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE actions
                SET {", ".join(updates)}
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                RETURNING id, reminders_enabled, reminder_frequency_days, snoozed_until, last_reminder_sent_at
                """,
                params,
            )
            row = cur.fetchone()
            if not row:
                return None

            return ReminderSettings(
                action_id=str(row["id"]),
                reminders_enabled=row["reminders_enabled"],
                reminder_frequency_days=row["reminder_frequency_days"]
                or DEFAULT_REMINDER_FREQUENCY_DAYS,
                snoozed_until=row["snoozed_until"],
                last_reminder_sent_at=row["last_reminder_sent_at"],
            )


def get_reminder_settings(action_id: str, user_id: str) -> ReminderSettings | None:
    """Get reminder settings for an action.

    Args:
        action_id: Action UUID
        user_id: User ID (for ownership check)

    Returns:
        ReminderSettings or None if not found
    """
    with db_session(user_id=user_id) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, reminders_enabled, reminder_frequency_days, snoozed_until, last_reminder_sent_at
                FROM actions
                WHERE id = %s AND user_id = %s AND deleted_at IS NULL
                """,
                (action_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None

            return ReminderSettings(
                action_id=str(row["id"]),
                reminders_enabled=row["reminders_enabled"]
                if row["reminders_enabled"] is not None
                else True,
                reminder_frequency_days=row["reminder_frequency_days"]
                or DEFAULT_REMINDER_FREQUENCY_DAYS,
                snoozed_until=row["snoozed_until"],
                last_reminder_sent_at=row["last_reminder_sent_at"],
            )


def mark_reminder_sent(action_id: str) -> bool:
    """Mark that a reminder was sent for an action.

    Args:
        action_id: Action UUID

    Returns:
        True if successful
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE actions
                SET last_reminder_sent_at = NOW(), snoozed_until = NULL
                WHERE id = %s AND deleted_at IS NULL
                RETURNING id
                """,
                (action_id,),
            )
            return cur.fetchone() is not None


def get_user_default_frequency(user_id: str) -> int:
    """Get user's default reminder frequency.

    Args:
        user_id: User ID

    Returns:
        Default frequency in days
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT default_reminder_frequency_days
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if row and row["default_reminder_frequency_days"]:
                return row["default_reminder_frequency_days"]
            return DEFAULT_REMINDER_FREQUENCY_DAYS


def set_user_default_frequency(user_id: str, frequency_days: int) -> int:
    """Set user's default reminder frequency.

    Args:
        user_id: User ID
        frequency_days: Days between reminders (1-14)

    Returns:
        Actual frequency set (clamped to valid range)
    """
    freq = max(MIN_REMINDER_FREQUENCY_DAYS, min(MAX_REMINDER_FREQUENCY_DAYS, frequency_days))

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET default_reminder_frequency_days = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING default_reminder_frequency_days
                """,
                (freq, user_id),
            )
            row = cur.fetchone()
            return row["default_reminder_frequency_days"] if row else freq
