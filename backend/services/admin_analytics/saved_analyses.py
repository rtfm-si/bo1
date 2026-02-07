"""CRUD for saved admin analytics analyses.

Stores analysis sequences (question + steps + SQL + chart configs)
for later re-execution with fresh data.
"""

import json
import logging
import uuid
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


def create_conversation(
    admin_user_id: str, title: str, model_preference: str = "sonnet"
) -> dict[str, Any]:
    """Create a new analytics conversation."""
    conv_id = str(uuid.uuid4())
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO admin_analytics_conversations
                   (id, admin_user_id, title, model_preference, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, NOW(), NOW())
                   RETURNING id, admin_user_id, title, model_preference, created_at""",
                (conv_id, admin_user_id, title, model_preference),
            )
            row = cur.fetchone()
            conn.commit()
            return {
                "id": row[0],
                "admin_user_id": row[1],
                "title": row[2],
                "model_preference": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            }


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    steps: list[dict] | None = None,
    suggestions: list[str] | None = None,
    llm_cost: float = 0.0,
) -> dict[str, Any]:
    """Save a message to a conversation."""
    msg_id = str(uuid.uuid4())
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO admin_analytics_messages
                   (id, conversation_id, role, content, steps, suggestions, llm_cost, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                   RETURNING id, created_at""",
                (
                    msg_id,
                    conversation_id,
                    role,
                    content,
                    json.dumps(steps) if steps else None,
                    suggestions,
                    llm_cost,
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return {"id": row[0], "created_at": row[1].isoformat() if row[1] else None}


def list_conversations(admin_user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """List recent conversations for an admin."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, model_preference, created_at, updated_at
                   FROM admin_analytics_conversations
                   WHERE admin_user_id = %s
                   ORDER BY updated_at DESC
                   LIMIT %s""",
                (admin_user_id, limit),
            )
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "model_preference": r[2],
                    "created_at": r[3].isoformat() if r[3] else None,
                    "updated_at": r[4].isoformat() if r[4] else None,
                }
                for r in cur.fetchall()
            ]


def get_conversation_messages(conversation_id: str) -> list[dict[str, Any]]:
    """Get all messages in a conversation."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, role, content, steps, suggestions, llm_cost, created_at
                   FROM admin_analytics_messages
                   WHERE conversation_id = %s
                   ORDER BY created_at ASC""",
                (conversation_id,),
            )
            return [
                {
                    "id": r[0],
                    "role": r[1],
                    "content": r[2],
                    "steps": r[3],
                    "suggestions": r[4],
                    "llm_cost": float(r[5]) if r[5] else 0.0,
                    "created_at": r[6].isoformat() if r[6] else None,
                }
                for r in cur.fetchall()
            ]


# ============================================================================
# Saved analyses CRUD
# ============================================================================


def save_analysis(
    admin_user_id: str,
    title: str,
    description: str,
    original_question: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Save an analysis for later re-running."""
    analysis_id = str(uuid.uuid4())
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO admin_saved_analyses
                   (id, admin_user_id, title, description, original_question, steps, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                   RETURNING id, created_at""",
                (
                    analysis_id,
                    admin_user_id,
                    title,
                    description,
                    original_question,
                    json.dumps(steps),
                ),
            )
            row = cur.fetchone()
            conn.commit()
            return {
                "id": row[0],
                "title": title,
                "created_at": row[1].isoformat() if row[1] else None,
            }


def list_saved_analyses(admin_user_id: str | None = None) -> list[dict[str, Any]]:
    """List saved analyses, optionally filtered by admin."""
    with db_session() as conn:
        with conn.cursor() as cur:
            if admin_user_id:
                cur.execute(
                    """SELECT id, admin_user_id, title, description, original_question,
                              last_run_at, created_at
                       FROM admin_saved_analyses
                       WHERE admin_user_id = %s
                       ORDER BY updated_at DESC""",
                    (admin_user_id,),
                )
            else:
                cur.execute(
                    """SELECT id, admin_user_id, title, description, original_question,
                              last_run_at, created_at
                       FROM admin_saved_analyses
                       ORDER BY updated_at DESC""",
                )
            return [
                {
                    "id": r[0],
                    "admin_user_id": r[1],
                    "title": r[2],
                    "description": r[3],
                    "original_question": r[4],
                    "last_run_at": r[5].isoformat() if r[5] else None,
                    "created_at": r[6].isoformat() if r[6] else None,
                }
                for r in cur.fetchall()
            ]


def get_saved_analysis(analysis_id: str) -> dict[str, Any] | None:
    """Get a saved analysis by ID."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, admin_user_id, title, description, original_question,
                          steps, last_run_at, last_run_result, created_at, updated_at
                   FROM admin_saved_analyses
                   WHERE id = %s""",
                (analysis_id,),
            )
            r = cur.fetchone()
            if not r:
                return None
            return {
                "id": r[0],
                "admin_user_id": r[1],
                "title": r[2],
                "description": r[3],
                "original_question": r[4],
                "steps": r[5],
                "last_run_at": r[6].isoformat() if r[6] else None,
                "last_run_result": r[7],
                "created_at": r[8].isoformat() if r[8] else None,
                "updated_at": r[9].isoformat() if r[9] else None,
            }


def update_saved_analysis_result(
    analysis_id: str,
    result: dict[str, Any],
) -> None:
    """Update a saved analysis with fresh run results."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE admin_saved_analyses
                   SET last_run_at = NOW(), last_run_result = %s, updated_at = NOW()
                   WHERE id = %s""",
                (json.dumps(result, default=str), analysis_id),
            )
            conn.commit()


def delete_saved_analysis(analysis_id: str) -> bool:
    """Delete a saved analysis."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM admin_saved_analyses WHERE id = %s",
                (analysis_id,),
            )
            conn.commit()
            return cur.rowcount > 0
