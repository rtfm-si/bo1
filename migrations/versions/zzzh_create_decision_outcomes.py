"""Create decision_outcomes table for Outcome Tracking.

Revision ID: zzzh_decision_outcomes
Revises: zzzg_user_decisions
Create Date: 2026-02-09

Tables:
- decision_outcomes: Records what actually happened after a decision
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "zzzh_decision_outcomes"
down_revision: str | Sequence[str] | None = "zzzg_user_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create decision_outcomes table with RLS."""
    op.create_table(
        "decision_outcomes",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "decision_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user_decisions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("outcome_status", sa.String(30), nullable=False),
        sa.Column("outcome_notes", sa.Text(), nullable=True),
        sa.Column("surprise_factor", sa.Integer(), nullable=True),
        sa.Column("lessons_learned", sa.Text(), nullable=True),
        sa.Column("what_would_change", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "surprise_factor BETWEEN 1 AND 5",
            name="ck_decision_outcomes_surprise_factor",
        ),
    )

    # Indexes
    op.create_index("ix_decision_outcomes_decision_id", "decision_outcomes", ["decision_id"])
    op.create_index("ix_decision_outcomes_user_id", "decision_outcomes", ["user_id"])

    # Enable RLS
    op.execute("ALTER TABLE decision_outcomes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE decision_outcomes FORCE ROW LEVEL SECURITY")

    # User isolation policy
    op.execute("""
        CREATE POLICY decision_outcomes_user_isolation ON decision_outcomes
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    # Admin read access
    op.execute("""
        CREATE POLICY decision_outcomes_admin_access ON decision_outcomes
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM users
                WHERE id = current_setting('app.current_user_id', TRUE)::text
                AND is_admin = true
            )
        )
    """)

    # Auto-update updated_at trigger
    op.execute("""
        CREATE TRIGGER set_decision_outcomes_updated_at
        BEFORE UPDATE ON decision_outcomes
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop decision_outcomes table."""
    op.execute("DROP TRIGGER IF EXISTS set_decision_outcomes_updated_at ON decision_outcomes")
    op.execute("DROP POLICY IF EXISTS decision_outcomes_admin_access ON decision_outcomes")
    op.execute("DROP POLICY IF EXISTS decision_outcomes_user_isolation ON decision_outcomes")
    op.drop_index("ix_decision_outcomes_user_id", table_name="decision_outcomes")
    op.drop_index("ix_decision_outcomes_decision_id", table_name="decision_outcomes")
    op.drop_table("decision_outcomes")
