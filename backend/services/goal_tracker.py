"""Goal tracking service for north star goal history.

Tracks changes to north_star_goal over time, enabling:
- Goal history timeline display
- Staleness prompts when goal unchanged for extended period
- Progress tracking visualization
"""

from datetime import UTC, datetime

from backend.api.utils.db_helpers import execute_query


def record_goal_change(
    user_id: str,
    new_goal: str,
    previous_goal: str | None,
) -> int | None:
    """Record a goal change in history.

    Args:
        user_id: User ID
        new_goal: New goal text
        previous_goal: Previous goal text (None if first goal)

    Returns:
        ID of created history entry, or None if duplicate (same as previous)
    """
    # Don't record if goal text unchanged
    if new_goal == previous_goal:
        return None

    result = execute_query(
        """
        INSERT INTO goal_history (user_id, goal_text, previous_goal, changed_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (user_id, new_goal, previous_goal, datetime.now(UTC)),
        fetch="one",
        user_id=user_id,
    )
    return result.get("id") if result else None


def get_goal_history(
    user_id: str,
    limit: int = 10,
) -> list[dict]:
    """Retrieve recent goal changes for a user.

    Args:
        user_id: User ID
        limit: Maximum entries to return (default 10)

    Returns:
        List of goal history entries, newest first
    """
    result = execute_query(
        """
        SELECT id, goal_text, previous_goal, changed_at
        FROM goal_history
        WHERE user_id = %s
        ORDER BY changed_at DESC
        LIMIT %s
        """,
        (user_id, limit),
        fetch="all",
        user_id=user_id,
    )
    return result or []


def get_days_since_last_change(
    user_id: str,
) -> int | None:
    """Get number of days since the user's last goal change.

    Args:
        user_id: User ID

    Returns:
        Days since last change, or None if no history
    """
    result = execute_query(
        """
        SELECT changed_at
        FROM goal_history
        WHERE user_id = %s
        ORDER BY changed_at DESC
        LIMIT 1
        """,
        (user_id,),
        fetch="one",
        user_id=user_id,
    )
    if not result:
        return None

    last_changed: datetime = result.get("changed_at")
    if not last_changed:
        return None

    now = datetime.now(UTC)
    # Ensure last_changed is timezone-aware
    if last_changed.tzinfo is None:
        last_changed = last_changed.replace(tzinfo=UTC)
    delta = now - last_changed
    return delta.days
