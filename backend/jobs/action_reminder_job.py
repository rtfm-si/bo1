"""Action reminder background job.

Runs hourly to:
- Query actions with pending reminders (start overdue, deadline approaching)
- Respect reminder frequency settings
- Send emails via Resend
- Update last_reminder_sent_at
"""

import logging

from backend.jobs.shared import get_frontend_url, get_user_data, should_send_email
from backend.services.action_reminders import get_pending_reminders, mark_reminder_sent
from backend.services.email import send_email_async
from backend.services.email_templates import (
    render_action_deadline_reminder_email,
    render_action_start_reminder_email,
)
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


def run_action_reminder_job() -> dict[str, int]:
    """Run the action reminder job.

    Queries all users with pending reminders and sends batched emails.

    Returns:
        Dict with stats: {sent, skipped, failed, users_processed}
    """
    stats = {"sent": 0, "skipped": 0, "failed": 0, "users_processed": 0}

    try:
        # Get all users with pending actions
        users = _get_users_with_pending_actions()
        logger.info(f"Processing reminders for {len(users)} users")

        for user_id in users:
            try:
                user_stats = _process_user_reminders(user_id)
                stats["sent"] += user_stats["sent"]
                stats["skipped"] += user_stats["skipped"]
                stats["failed"] += user_stats["failed"]
                stats["users_processed"] += 1
            except Exception as e:
                logger.error(f"Failed to process reminders for user {user_id}: {e}")
                stats["failed"] += 1

    except Exception as e:
        logger.error(f"Action reminder job failed: {e}", exc_info=True)

    logger.info(f"Action reminder job complete: {stats}")
    return stats


def _get_users_with_pending_actions() -> list[str]:
    """Get list of user IDs with pending action reminders."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT user_id
                FROM actions
                WHERE status NOT IN ('done', 'cancelled')
                  AND deleted_at IS NULL
                  AND reminders_enabled = true
                  AND (snoozed_until IS NULL OR snoozed_until <= NOW())
                  AND (
                      (target_start_date IS NOT NULL AND target_start_date < CURRENT_DATE AND status = 'todo')
                      OR (estimated_start_date IS NOT NULL AND estimated_start_date < CURRENT_DATE AND status = 'todo')
                      OR (target_end_date IS NOT NULL AND target_end_date <= CURRENT_DATE + INTERVAL '3 days')
                      OR (estimated_end_date IS NOT NULL AND estimated_end_date <= CURRENT_DATE + INTERVAL '3 days')
                  )
                """
            )
            return [row["user_id"] for row in cur.fetchall()]


def _process_user_reminders(user_id: str) -> dict[str, int]:
    """Process reminders for a single user.

    Batches reminders to avoid email spam - sends max 5 per user per run.

    Args:
        user_id: User ID

    Returns:
        Stats dict
    """
    stats = {"sent": 0, "skipped": 0, "failed": 0}

    can_send, email = should_send_email(get_user_data(user_id), "reminder_emails")
    if not can_send:
        stats["skipped"] += 1
        return stats

    # Get pending reminders (max 5 per user per run)
    reminders = get_pending_reminders(user_id, limit=5)

    for reminder in reminders:
        try:
            action_url = get_frontend_url(f"/actions/{reminder.action_id}")

            if reminder.reminder_type == "start_overdue":
                html, text = render_action_start_reminder_email(
                    user_id=user_id,
                    action_title=reminder.action_title,
                    action_url=action_url,
                    days_overdue=reminder.days_overdue or 0,
                    session_id=reminder.session_id,
                )
                subject = f"[Start Overdue] {reminder.action_title[:50]}"
            else:  # deadline_approaching
                html, text = render_action_deadline_reminder_email(
                    user_id=user_id,
                    action_title=reminder.action_title,
                    action_url=action_url,
                    days_until=reminder.days_until_deadline or 0,
                    session_id=reminder.session_id,
                )
                subject = f"[Deadline Soon] {reminder.action_title[:50]}"

            send_email_async(
                to=email,
                subject=subject,
                html=html,
                text=text,
            )

            # Mark reminder sent
            mark_reminder_sent(reminder.action_id)
            stats["sent"] += 1

        except Exception as e:
            logger.error(f"Failed to send reminder for action {reminder.action_id}: {e}")
            stats["failed"] += 1

    return stats


# CLI entrypoint for manual/cron execution
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    result = run_action_reminder_job()
    print(f"Reminder job complete: {result}")
    sys.exit(0 if result["failed"] == 0 else 1)
