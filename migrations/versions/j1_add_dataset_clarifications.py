"""Add clarifications column to datasets table.

Stores user clarifications from Q&A sessions for context persistence
across conversations.

Revision ID: j1_dataset_clarifications
Revises: i2_session_subproblem_idx
Create Date: 2025-12-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "j1_dataset_clarifications"
down_revision: str | Sequence[str] | None = "i2_session_subproblem_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add clarifications JSONB column to datasets table."""
    op.add_column(
        "datasets",
        sa.Column(
            "clarifications",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="Array of {question, answer, timestamp} from Q&A sessions",
        ),
    )


def downgrade() -> None:
    """Remove clarifications column."""
    op.drop_column("datasets", "clarifications")
