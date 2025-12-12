"""Action context extraction for replanning suggestions.

Provides functions to extract context from failed/cancelled actions to pre-fill
new meeting creation dialogs with relevant information.
"""

import logging
from typing import Any
from uuid import UUID

from bo1.state.database import db_session
from bo1.state.repositories.action_repository import action_repository
from bo1.state.repositories.session_repository import session_repository

logger = logging.getLogger(__name__)


def extract_replan_context(action_id: str | UUID) -> dict[str, Any]:
    """Extract context from a cancelled action for replanning.

    Gathers parent session's problem statement, related actions, failure reason,
    and insights to pre-fill new meeting creation.

    Args:
        action_id: UUID of the cancelled action

    Returns:
        Dict with keys:
        - problem_statement: From parent session
        - failure_reason_category: blocker/scope_creep/dependency/unknown
        - failure_reason_text: Original cancellation_reason
        - related_actions: List of related actions (same session, same project)
        - parent_session_id: UUID of parent session
        - business_context: User's business context if available
    """
    action = action_repository.get(str(action_id))
    if not action:
        return {}

    result: dict[str, Any] = {
        "action_id": str(action_id),
        "action_title": action.get("title", ""),
        "failure_reason_text": action.get("cancellation_reason", ""),
        "failure_reason_category": action.get("failure_reason_category", "unknown"),
        "related_actions": [],
        "parent_session_id": None,
        "problem_statement": "",
        "business_context": None,
    }

    session_id = action.get("session_id")
    user_id = action.get("user_id")
    project_id = action.get("project_id")

    # Get parent session's problem statement
    if session_id:
        session = session_repository.get(str(session_id))
        if session:
            result["parent_session_id"] = str(session_id)
            result["problem_statement"] = session.get("problem_statement", "")

            # Get related actions from same session
            try:
                related = action_repository.get_by_session(str(session_id))
                # Filter to show incomplete actions that might be affected (limit to 5)
                result["related_actions"] = [
                    {
                        "id": str(a.get("id", "")),
                        "title": a.get("title", ""),
                        "status": a.get("status", ""),
                    }
                    for a in related[:5]
                    if a.get("id") != action_id and a.get("status") != "done"
                ]
            except Exception as e:
                logger.warning(f"Failed to fetch related actions for session {session_id}: {e}")

    # Get related actions from same project
    if project_id and user_id:
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, title, status
                        FROM actions
                        WHERE project_id = %s
                            AND user_id = %s
                            AND id != %s
                            AND status != 'done'
                        ORDER BY created_at DESC
                        LIMIT 10
                        """,
                        (str(project_id), str(user_id), str(action_id)),
                    )
                    rows = cur.fetchall()
                    if rows:
                        result["related_actions"].extend(
                            [
                                {
                                    "id": str(r["id"]),
                                    "title": r["title"],
                                    "status": r["status"],
                                }
                                for r in rows
                            ]
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch project-related actions: {e}")

    # Get user's business context for context injection
    if user_id:
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT business_context FROM users WHERE id = %s",
                        (str(user_id),),
                    )
                    row = cur.fetchone()
                    if row:
                        result["business_context"] = row["business_context"]
        except Exception as e:
            logger.warning(f"Failed to fetch user business context: {e}")

    return result
