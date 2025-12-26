"""Add persona_count_variant column for A/B testing.

Revision ID: ab1_persona_exp
Revises: dr2_merge_heads
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ab1_persona_exp"
down_revision: str | Sequence[str] | None = "dr2_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add persona_count_variant column for A/B testing 3 vs 5 personas."""
    # Add nullable int column (3 or 5)
    op.add_column(
        "sessions",
        sa.Column(
            "persona_count_variant",
            sa.SmallInteger,
            nullable=True,
        ),
    )

    # Add CHECK constraint for valid values (3 or 5)
    op.create_check_constraint(
        "ck_sessions_persona_count_variant",
        "sessions",
        "persona_count_variant IS NULL OR persona_count_variant IN (3, 5)",
    )

    # Backfill existing sessions with 5 (control group)
    op.execute("UPDATE sessions SET persona_count_variant = 5 WHERE persona_count_variant IS NULL")

    # Add comment for documentation
    op.execute(
        "COMMENT ON COLUMN sessions.persona_count_variant IS "
        "'A/B test variant: 3 or 5 personas. NULL means pre-experiment session.'"
    )

    # Create index for efficient A/B metrics queries
    op.create_index(
        "ix_sessions_persona_count_variant",
        "sessions",
        ["persona_count_variant"],
        postgresql_where=sa.text("persona_count_variant IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove persona_count_variant column and related constraints."""
    op.drop_index("ix_sessions_persona_count_variant", table_name="sessions")
    op.drop_constraint("ck_sessions_persona_count_variant", "sessions", type_="check")
    op.drop_column("sessions", "persona_count_variant")
