"""Email notification jobs for meetings and actions.

Provides:
- send_meeting_completed_email: Send email when a meeting finishes
- send_action_reminders: Send reminders for actions due soon
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.jobs.shared import get_frontend_url, get_user_data, should_send_email
from backend.services.email import send_email_async
from backend.services.email_templates import (
    render_action_reminder_email,
    render_meeting_completed_email,
)
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


def send_meeting_completed_email(session_id: str) -> bool:
    """Send meeting completed email to the session owner.

    Fetches session details, synthesis, recommendations, and actions
    from the database and sends a summary email.

    Args:
        session_id: Session identifier

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Fetch session details
        session_data = _get_session_data(session_id)
        if not session_data:
            logger.warning(f"Session not found for email: {session_id}")
            return False

        user_id = session_data.get("user_id")
        if not user_id:
            logger.warning(f"No user_id for session: {session_id}")
            return False

        can_send, email = should_send_email(get_user_data(user_id), "meeting_emails")
        if not can_send:
            logger.info(f"Skipping meeting email for user: {user_id}")
            return False

        # Extract email content
        problem_statement = session_data.get("problem_statement", "")[:300]
        synthesis = session_data.get("synthesis") or session_data.get("meta_synthesis") or ""

        # Parse synthesis for summary (first paragraph or first 500 chars)
        summary = _extract_summary(synthesis)

        # Get recommendations (from synthesis or actions)
        recommendations = _extract_recommendations(synthesis)

        # Get actions
        actions = _get_session_actions(session_id)

        meeting_url = get_frontend_url(f"/meeting/{session_id}")

        # Render and send email
        html, text = render_meeting_completed_email(
            user_id=user_id,
            problem_statement=problem_statement,
            summary=summary,
            recommendations=recommendations,
            actions=actions,
            meeting_url=meeting_url,
        )

        send_email_async(
            to=email,
            subject=f"Meeting Complete: {problem_statement[:50]}{'...' if len(problem_statement) > 50 else ''}",
            html=html,
            text=text,
        )

        logger.info(f"Meeting completed email sent for session: {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send meeting completed email: {e}", exc_info=True)
        return False


def send_action_reminders() -> dict[str, int]:
    """Send reminder emails for actions due tomorrow.

    Queries actions with due dates in the next 24 hours that haven't
    been reminded yet, and sends reminder emails.

    Returns:
        Dict with counts: {"sent": N, "skipped": M, "failed": P}
    """
    stats = {"sent": 0, "skipped": 0, "failed": 0}

    try:
        # Get actions due in next 24-48 hours without reminder
        actions = _get_actions_due_soon()

        for action in actions:
            try:
                user_id = action.get("user_id")
                if not user_id:
                    stats["skipped"] += 1
                    continue

                can_send, email = should_send_email(get_user_data(user_id), "reminder_emails")
                if not can_send:
                    stats["skipped"] += 1
                    continue

                action_url = get_frontend_url(f"/actions/{action['id']}")

                # Determine if overdue
                due_date = action.get("target_end_date") or action.get("estimated_end_date")
                is_overdue = False
                if due_date:
                    if isinstance(due_date, str):
                        from datetime import date

                        due_date = date.fromisoformat(due_date)
                    is_overdue = due_date < datetime.now(UTC).date()

                # Render and send email
                html, text = render_action_reminder_email(
                    user_id=user_id,
                    action_title=action.get("title", "Action"),
                    action_description=action.get("description", ""),
                    due_date=due_date,
                    action_url=action_url,
                    is_overdue=is_overdue,
                )

                subject_prefix = "[Overdue]" if is_overdue else "[Reminder]"
                send_email_async(
                    to=email,
                    subject=f"{subject_prefix} {action.get('title', 'Action')[:50]}",
                    html=html,
                    text=text,
                )

                # Mark reminder sent
                _mark_reminder_sent(action["id"])
                stats["sent"] += 1

            except Exception as e:
                logger.error(f"Failed to send reminder for action {action.get('id')}: {e}")
                stats["failed"] += 1

    except Exception as e:
        logger.error(f"Failed to query actions for reminders: {e}", exc_info=True)

    logger.info(f"Action reminders complete: {stats}")
    return stats


# =============================================================================
# Helper Functions
# =============================================================================


def _get_session_data(session_id: str) -> dict[str, Any] | None:
    """Fetch session data from database."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, problem_statement, synthesis, status, created_at
                    FROM sessions
                    WHERE id = %s
                    """,
                    (session_id,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
        return None
    except Exception as e:
        logger.error(f"Failed to get session data: {e}")
        return None


def _get_session_actions(session_id: str) -> list[dict[str, Any]]:
    """Fetch actions for a session."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, description, status, priority,
                           target_end_date, estimated_end_date
                    FROM actions
                    WHERE source_session_id = %s
                    ORDER BY sort_order, created_at
                    LIMIT 10
                    """,
                    (session_id,),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get session actions: {e}")
        return []


def _get_actions_due_soon() -> list[dict[str, Any]]:
    """Get actions due in the next 24-48 hours without reminder sent."""
    try:
        tomorrow = datetime.now(UTC).date() + timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, title, description, status,
                           target_end_date, estimated_end_date, reminder_sent_at
                    FROM actions
                    WHERE status NOT IN ('done', 'cancelled')
                      AND (
                          (target_end_date >= %s AND target_end_date < %s)
                          OR (estimated_end_date >= %s AND estimated_end_date < %s)
                      )
                      AND reminder_sent_at IS NULL
                    ORDER BY COALESCE(target_end_date, estimated_end_date)
                    LIMIT 100
                    """,
                    (tomorrow, day_after, tomorrow, day_after),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to get actions due soon: {e}")
        return []


def _mark_reminder_sent(action_id: str) -> bool:
    """Mark an action as having had a reminder sent."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET reminder_sent_at = NOW()
                    WHERE id = %s
                    """,
                    (action_id,),
                )
                return True
    except Exception as e:
        logger.error(f"Failed to mark reminder sent: {e}")
        return False


def _extract_summary(synthesis: str) -> str:
    """Extract summary from synthesis text."""
    if not synthesis:
        return "Meeting completed. View full details in the meeting page."

    # Try to find executive summary section
    synthesis_lower = synthesis.lower()
    if "executive summary" in synthesis_lower:
        start = synthesis_lower.find("executive summary")
        # Find end of section (next heading or 500 chars)
        end = min(start + 800, len(synthesis))
        for marker in ["##", "\n\n\n", "key recommendation", "action"]:
            idx = synthesis_lower.find(marker, start + 20)
            if idx > start and idx < end:
                end = idx
        return synthesis[start:end].strip()[:500]

    # Fall back to first 500 chars
    return synthesis[:500].strip()


def _extract_recommendations(synthesis: str) -> list[str]:
    """Extract key recommendations from synthesis text."""
    if not synthesis:
        return []

    recommendations = []
    synthesis_lower = synthesis.lower()

    # Look for recommendation patterns
    if "recommend" in synthesis_lower:
        lines = synthesis.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith(("-", "*", "•")) and "recommend" in line.lower():
                recommendations.append(line_stripped.lstrip("-*• "))
            elif line_stripped.lower().startswith("recommend"):
                recommendations.append(line_stripped)
            if len(recommendations) >= 5:
                break

    # If no explicit recommendations, extract bullet points
    if not recommendations:
        lines = synthesis.split("\n")
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith(("-", "*", "•")) and len(line_stripped) > 20:
                recommendations.append(line_stripped.lstrip("-*• "))
            if len(recommendations) >= 5:
                break

    return recommendations[:5]
