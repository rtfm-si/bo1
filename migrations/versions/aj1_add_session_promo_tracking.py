"""Add used_promo_credit column to sessions table.

Tracks whether a session consumed a promo credit vs tier allowance.
This enables:
- Correct promo credit consumption on session completion
- Separation of billing paths (promo vs tier)
- Audit trail for promo usage

Revision ID: aj1_add_session_promo_tracking
Revises: ai1_create_promotions
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aj1_add_session_promo_tracking"
down_revision: str | Sequence[str] | None = "ai1_create_promotions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add used_promo_credit column to sessions table."""
    op.add_column(
        "sessions",
        sa.Column(
            "used_promo_credit",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="True if session used promo credit instead of tier allowance",
        ),
    )

    # Index for analytics queries (find all promo-funded sessions)
    op.create_index(
        "ix_sessions_used_promo_credit",
        "sessions",
        ["used_promo_credit"],
        postgresql_where=sa.text("used_promo_credit = true"),
    )


def downgrade() -> None:
    """Remove used_promo_credit column from sessions table."""
    op.drop_index("ix_sessions_used_promo_credit", table_name="sessions")
    op.drop_column("sessions", "used_promo_credit")
