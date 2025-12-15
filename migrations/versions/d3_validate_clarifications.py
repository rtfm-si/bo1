"""Validate and normalize legacy clarification data.

Data migration to convert legacy string-format clarifications to the new
ClarificationStorageEntry structure. Logs warnings for invalid entries
but does not fail the migration.

Revision ID: d3_clarifications
Revises: d2_updated_at
Create Date: 2025-12-14

"""

import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "d3_clarifications"
down_revision: str | None = "d2_updated_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Normalize legacy clarification entries to new structure."""
    conn = op.get_bind()

    # Fetch all user_context rows with clarifications (direct jsonb column)
    result = conn.execute(
        text(
            """
            SELECT id, user_id, clarifications
            FROM user_context
            WHERE clarifications IS NOT NULL
            AND jsonb_typeof(clarifications) = 'object'
            """
        )
    )

    updated = 0
    skipped = 0

    for row in result:
        context_id = row[0]
        user_id = row[1]
        clarifications = row[2]

        if not isinstance(clarifications, dict) or not clarifications:
            continue

        modified = False
        normalized: dict[str, dict] = {}

        for question, entry in clarifications.items():
            try:
                if isinstance(entry, str):
                    # Legacy string format: convert to dict
                    normalized[question] = {
                        "answer": entry,
                        "source": "migration",
                        "answered_at": datetime.now(UTC).isoformat(),
                    }
                    modified = True
                elif isinstance(entry, dict):
                    # Ensure required 'answer' field exists
                    if "answer" not in entry or not entry["answer"]:
                        logger.warning(
                            f"User {user_id}: skipping clarification without answer: "
                            f"{question[:50]}..."
                        )
                        skipped += 1
                        continue

                    # Normalize: add source if missing
                    if "source" not in entry:
                        entry["source"] = "meeting"
                        modified = True

                    # Handle legacy 'timestamp' field -> 'answered_at'
                    if "timestamp" in entry and "answered_at" not in entry:
                        entry["answered_at"] = entry.pop("timestamp")
                        modified = True

                    # Remove deprecated 'round_number' field
                    if "round_number" in entry:
                        del entry["round_number"]
                        modified = True

                    normalized[question] = entry
                else:
                    logger.warning(
                        f"User {user_id}: invalid clarification type "
                        f"{type(entry).__name__}: {question[:50]}..."
                    )
                    skipped += 1
                    continue

            except Exception as e:
                logger.warning(f"User {user_id}: failed to normalize clarification: {e}")
                skipped += 1
                continue

        if modified:
            conn.execute(
                text(
                    """
                    UPDATE user_context
                    SET clarifications = :data, updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {"data": json.dumps(normalized), "id": context_id},
            )
            updated += 1

    logger.info(
        f"Clarification migration complete: {updated} users updated, {skipped} entries skipped"
    )


def downgrade() -> None:
    """No downgrade - data migration is forward-only."""
    # We don't convert back to legacy format as the new format is backward compatible
    pass
