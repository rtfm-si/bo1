"""drop_unused_votes_and_schema_migrations_tables

Revision ID: 9626a52fd9bf
Revises: b3_user_id_fac_decisions
Create Date: 2025-12-08 16:01:07.982180

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9626a52fd9bf"
down_revision: str | Sequence[str] | None = "b3_user_id_fac_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop unused tables.

    - votes: Never written to; code uses in-memory state for recommendations
    - schema_migrations: Legacy migration tracker; now using Alembic
    """
    # Drop votes table if exists (has FK to sessions and personas, but nothing references it)
    op.execute("DROP INDEX IF EXISTS idx_votes_session_id")
    op.execute("DROP TABLE IF EXISTS votes")

    # Drop legacy schema_migrations table if exists
    op.execute("DROP TABLE IF EXISTS schema_migrations")


def downgrade() -> None:
    """Recreate dropped tables."""
    # Recreate schema_migrations (empty, legacy)
    op.create_table(
        "schema_migrations",
        sa.Column("version", sa.String(255), primary_key=True),
    )

    # Recreate votes table
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("persona_code", sa.String(50), sa.ForeignKey("personas.code"), nullable=False),
        sa.Column("vote_choice", sa.String(100), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_votes_session_id", "votes", ["session_id"])
