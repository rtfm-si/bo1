"""Shared helpers for background jobs."""

import logging
from typing import Any

from bo1.config import get_settings
from bo1.state.database import db_session

logger = logging.getLogger(__name__)


def get_user_data(user_id: str) -> dict[str, Any] | None:
    """Fetch user data (id, email, email_preferences) from database."""
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, email, email_preferences
                    FROM users
                    WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
    except Exception as e:
        logger.error(f"Failed to get user data: {e}")
        return None


def get_frontend_url(path: str) -> str:
    """Build full frontend URL from path."""
    return f"{get_settings().supertokens_website_domain}{path}"


def should_send_email(
    user_data: dict[str, Any] | None,
    pref_key: str,
) -> tuple[bool, str | None]:
    """Check if user should receive email.

    Returns (can_send, email).
    """
    if not user_data:
        return False, None

    email = user_data.get("email")
    if not email or email.endswith("@placeholder.local"):
        return False, None

    prefs = user_data.get("email_preferences") or {}
    if prefs.get(pref_key) is False:
        return False, None

    return True, email
