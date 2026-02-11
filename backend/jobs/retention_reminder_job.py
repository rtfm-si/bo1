"""Retention reminder job for data deletion notifications.

Sends reminder emails at 28 days and 1 day before scheduled data deletion.
Respects user's suppression preference and avoids duplicate emails.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from backend.jobs.shared import get_frontend_url
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Reminder windows (days before deletion)
REMINDER_WINDOWS = [28, 1]

# Minimum days between reminder emails (to prevent spam)
MIN_REMINDER_INTERVAL_DAYS = 7


def get_users_approaching_deletion() -> list[dict[str, Any]]:
    """Find users with data approaching their retention threshold.

    Returns users where:
    - data_retention_days != -1 (not forever)
    - deletion_reminder_suppressed = false
    - Has sessions old enough to be within reminder windows
    - Last reminder not sent within MIN_REMINDER_INTERVAL_DAYS

    Returns:
        List of dicts with user info and days until deletion
    """
    users_to_notify = []

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Find users with retention settings and unsuppressed
                # Calculate their oldest session age and days until deletion
                cur.execute(
                    """
                    WITH user_oldest_session AS (
                        SELECT
                            u.id AS user_id,
                            u.email,
                            u.data_retention_days,
                            u.deletion_reminder_suppressed,
                            u.last_deletion_reminder_sent_at,
                            MIN(s.created_at) AS oldest_session
                        FROM users u
                        LEFT JOIN sessions s ON s.user_id = u.id
                        WHERE u.data_retention_days != -1
                          AND u.deletion_reminder_suppressed = false
                          AND u.email IS NOT NULL
                          AND u.email NOT LIKE '%%@placeholder.local'
                        GROUP BY u.id
                    )
                    SELECT
                        user_id,
                        email,
                        data_retention_days,
                        last_deletion_reminder_sent_at,
                        oldest_session,
                        -- Calculate days until oldest session hits retention limit
                        data_retention_days - EXTRACT(
                            DAY FROM (NOW() - oldest_session)
                        )::INTEGER AS days_until_deletion
                    FROM user_oldest_session
                    WHERE oldest_session IS NOT NULL
                      -- Only users with data old enough to be in reminder windows
                      AND data_retention_days - EXTRACT(
                          DAY FROM (NOW() - oldest_session)
                      )::INTEGER <= 28
                      AND data_retention_days - EXTRACT(
                          DAY FROM (NOW() - oldest_session)
                      )::INTEGER >= 0
                    """
                )
                rows = cur.fetchall()

                for row in rows:
                    # Check if we've sent a reminder recently
                    last_sent = row.get("last_deletion_reminder_sent_at")
                    if last_sent:
                        days_since_last = (datetime.now(UTC) - last_sent).days
                        if days_since_last < MIN_REMINDER_INTERVAL_DAYS:
                            continue

                    days_until = row.get("days_until_deletion", 0)

                    # Only notify for specific windows (28 days or 1 day)
                    should_notify = False
                    for window in REMINDER_WINDOWS:
                        if days_until <= window and days_until >= (window - 1):
                            should_notify = True
                            break

                    if should_notify:
                        users_to_notify.append(
                            {
                                "user_id": row["user_id"],
                                "email": row["email"],
                                "days_until_deletion": days_until,
                                "retention_days": row["data_retention_days"],
                            }
                        )

        logger.info(f"Found {len(users_to_notify)} users approaching deletion threshold")
        return users_to_notify

    except Exception as e:
        logger.error(f"Failed to query users for retention reminders: {e}", exc_info=True)
        return []


def send_retention_reminder(
    user_id: str,
    email: str,
    days_until_deletion: int,
) -> bool:
    """Send retention reminder email to a user.

    Args:
        user_id: User identifier
        email: User's email address
        days_until_deletion: Days until data deletion

    Returns:
        True if email sent successfully, False otherwise
    """
    from backend.services.email import send_email_async
    from backend.services.email_templates import render_data_retention_reminder_email

    try:
        settings_url = get_frontend_url("/settings/privacy")
        suppress_url = get_frontend_url(
            f"/api/v1/user/retention-reminder/suppress?token={_generate_suppress_token(user_id)}"
        )

        # Render email
        html, text = render_data_retention_reminder_email(
            user_id=user_id,
            days_until_deletion=days_until_deletion,
            settings_url=settings_url,
            suppress_url=suppress_url,
        )

        # Determine subject based on urgency
        if days_until_deletion <= 1:
            subject = "[Final Notice] Your Board of One data will be deleted"
        else:
            subject = (
                f"[Reminder] Your Board of One data will be deleted in {days_until_deletion} days"
            )

        # Send email
        send_email_async(
            to=email,
            subject=subject,
            html=html,
            text=text,
        )

        # Update last sent timestamp
        _update_last_reminder_sent(user_id)

        logger.info(f"Sent retention reminder: user={user_id}, days_until={days_until_deletion}")
        return True

    except Exception as e:
        logger.error(f"Failed to send retention reminder to {user_id}: {e}", exc_info=True)
        return False


def _generate_suppress_token(user_id: str) -> str:
    """Generate a signed token for suppressing reminders.

    Uses the same mechanism as unsubscribe tokens for consistency.
    """
    from backend.services.email import generate_unsubscribe_token

    return generate_unsubscribe_token(user_id, "retention_reminder")


def _update_last_reminder_sent(user_id: str) -> None:
    """Update the last_deletion_reminder_sent_at timestamp."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET last_deletion_reminder_sent_at = NOW()
                    WHERE id = %s
                    """,
                    (user_id,),
                )
    except Exception as e:
        logger.warning(f"Failed to update last reminder timestamp for {user_id}: {e}")


def run_retention_reminder_job() -> dict[str, int]:
    """Run the retention reminder job.

    Finds users approaching deletion and sends appropriate reminder emails.

    Returns:
        Dict with job statistics
    """
    logger.info("Starting retention reminder job")
    stats = {
        "users_checked": 0,
        "emails_sent": 0,
        "emails_failed": 0,
    }

    users = get_users_approaching_deletion()
    stats["users_checked"] = len(users)

    for user in users:
        success = send_retention_reminder(
            user_id=user["user_id"],
            email=user["email"],
            days_until_deletion=user["days_until_deletion"],
        )
        if success:
            stats["emails_sent"] += 1
        else:
            stats["emails_failed"] += 1

    logger.info(f"Retention reminder job complete: {stats}")
    return stats


if __name__ == "__main__":
    # CLI entry point for cron jobs
    import argparse

    parser = argparse.ArgumentParser(description="Run retention reminder job")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report users to notify without sending emails",
    )
    args = parser.parse_args()

    if args.dry_run:
        users = get_users_approaching_deletion()
        print(f"Would notify {len(users)} users:")
        for u in users:
            print(f"  - {u['email']}: {u['days_until_deletion']} days until deletion")
    else:
        result = run_retention_reminder_job()
        print(f"Job result: {result}")
