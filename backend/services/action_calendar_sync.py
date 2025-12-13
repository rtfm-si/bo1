"""Action-to-Google Calendar sync service.

Syncs action due dates to user's Google Calendar:
- Creates calendar events when actions have due dates
- Updates events when due dates change
- Deletes events when actions are deleted/completed
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from bo1.config import get_settings
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


class CalendarSyncError(Exception):
    """Error during calendar sync operation."""

    pass


def sync_action_to_calendar(
    action_id: str,
    user_id: str,
    force: bool = False,
) -> dict[str, Any] | None:
    """Sync an action's due date to the user's Google Calendar.

    Creates or updates a calendar event based on action due date.
    Skips if:
    - Calendar not enabled/connected
    - Action has no due date
    - Action's calendar_sync_enabled is False

    Args:
        action_id: Action UUID
        user_id: User who owns the action
        force: Force sync even if sync disabled on action

    Returns:
        Dict with event_id, html_link on success, None if skipped
    """
    settings = get_settings()

    # Check feature flag
    if not settings.google_calendar_enabled:
        logger.debug("Calendar sync skipped: feature disabled")
        return None

    # Get action details
    action = _get_action_details(action_id, user_id)
    if not action:
        logger.warning(f"Action {action_id} not found for user {user_id}")
        return None

    # Check if sync enabled for this action
    if not force and not action.get("calendar_sync_enabled", True):
        logger.debug(f"Calendar sync skipped for action {action_id}: sync disabled")
        return None

    # Get due date (target_end_date or estimated_end_date)
    due_date = action.get("target_end_date") or action.get("estimated_end_date")
    if not due_date:
        logger.debug(f"Calendar sync skipped for action {action_id}: no due date")
        return None

    # Get user's calendar client
    from backend.services.google_calendar import get_calendar_client

    client = get_calendar_client(user_id)
    if not client:
        logger.debug(f"Calendar sync skipped for user {user_id}: not connected")
        return None

    # Build event details
    title = f"[Bo1] {action.get('title', 'Action')}"
    description = _build_event_description(action)

    # Convert date to datetime (all-day event for due date)
    if isinstance(due_date, datetime):
        start_dt = due_date.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # date object - assume 9am UTC
        start_dt = datetime.combine(due_date, datetime.min.time().replace(hour=9))

    end_dt = start_dt + timedelta(hours=1)

    try:
        existing_event_id = action.get("calendar_event_id")

        if existing_event_id:
            # Update existing event
            event = client.update_event(
                event_id=existing_event_id,
                summary=title,
                start=start_dt,
                end=end_dt,
                description=description,
            )
            logger.info(f"Updated calendar event {event.event_id} for action {action_id}")
        else:
            # Create new event
            event = client.create_event(
                summary=title,
                start=start_dt,
                end=end_dt,
                description=description,
            )
            logger.info(f"Created calendar event {event.event_id} for action {action_id}")

        # Store event reference on action
        _update_action_calendar_fields(
            action_id=action_id,
            event_id=event.event_id,
            event_link=event.html_link,
        )

        return {
            "event_id": event.event_id,
            "html_link": event.html_link,
        }

    except Exception as e:
        logger.error(f"Failed to sync action {action_id} to calendar: {e}")
        return None


def remove_action_from_calendar(
    action_id: str,
    user_id: str,
) -> bool:
    """Remove an action's calendar event.

    Called when:
    - Action is deleted
    - Action is completed
    - User disables calendar sync for action

    Args:
        action_id: Action UUID
        user_id: User who owns the action

    Returns:
        True if event was deleted, False otherwise
    """
    settings = get_settings()

    if not settings.google_calendar_enabled:
        return False

    # Get action to find event ID
    action = _get_action_details(action_id, user_id)
    if not action:
        return False

    event_id = action.get("calendar_event_id")
    if not event_id:
        logger.debug(f"No calendar event for action {action_id}")
        return False

    # Get user's calendar client
    from backend.services.google_calendar import CalendarError, get_calendar_client

    client = get_calendar_client(user_id)
    if not client:
        return False

    try:
        client.delete_event(event_id)
        logger.info(f"Deleted calendar event {event_id} for action {action_id}")

        # Clear event reference on action
        _update_action_calendar_fields(
            action_id=action_id,
            event_id=None,
            event_link=None,
        )
        return True

    except CalendarError as e:
        # Event may have been manually deleted
        logger.warning(f"Failed to delete calendar event {event_id}: {e}")
        # Clear stale reference
        _update_action_calendar_fields(
            action_id=action_id,
            event_id=None,
            event_link=None,
        )
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting calendar event: {e}")
        return False


def set_action_calendar_sync(
    action_id: str,
    user_id: str,
    enabled: bool,
) -> bool:
    """Enable or disable calendar sync for a specific action.

    Args:
        action_id: Action UUID
        user_id: User who owns the action
        enabled: Whether to sync this action to calendar

    Returns:
        True if updated successfully
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET calendar_sync_enabled = %s, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    """,
                    (enabled, action_id, user_id),
                )
                updated = cur.rowcount and cur.rowcount > 0

        if updated:
            if enabled:
                # Sync the action now
                sync_action_to_calendar(action_id, user_id, force=True)
            else:
                # Remove from calendar
                remove_action_from_calendar(action_id, user_id)

        return bool(updated)

    except Exception as e:
        logger.error(f"Failed to set calendar sync for action {action_id}: {e}")
        return False


def _get_action_details(action_id: str, user_id: str) -> dict[str, Any] | None:
    """Get action details for calendar sync.

    Args:
        action_id: Action UUID
        user_id: User who owns the action

    Returns:
        Action dict or None if not found
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, description, status, priority,
                           target_end_date, estimated_end_date,
                           calendar_event_id, calendar_event_link, calendar_sync_enabled
                    FROM actions
                    WHERE id = %s AND user_id = %s AND is_deleted = false
                    """,
                    (action_id, user_id),
                )
                result = cur.fetchone()
                return dict(result) if result else None
    except Exception as e:
        logger.error(f"Failed to get action details: {e}")
        return None


def _update_action_calendar_fields(
    action_id: str,
    event_id: str | None,
    event_link: str | None,
) -> None:
    """Update action's calendar fields.

    Args:
        action_id: Action UUID
        event_id: Google Calendar event ID (or None to clear)
        event_link: Google Calendar event link (or None to clear)
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET calendar_event_id = %s,
                        calendar_event_link = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (event_id, event_link, action_id),
                )
    except Exception as e:
        logger.error(f"Failed to update action calendar fields: {e}")


def _build_event_description(action: dict[str, Any]) -> str:
    """Build calendar event description from action details.

    Args:
        action: Action dict

    Returns:
        Formatted description string
    """
    parts = []

    # Add main description
    desc = action.get("description")
    if desc:
        parts.append(desc)

    # Add priority
    priority = action.get("priority", "medium")
    parts.append(f"Priority: {priority.title()}")

    # Add status
    status = action.get("status", "todo")
    parts.append(f"Status: {status.replace('_', ' ').title()}")

    parts.append("\n---")
    parts.append("Managed by Board of One")

    return "\n".join(parts)
