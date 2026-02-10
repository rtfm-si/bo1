"""Create user_decisions table for Decision Gate feature.

Revision ID: zzzg_user_decisions
Revises: zzzf_decision_topic_bank
Create Date: 2026-02-09

Tables:
- user_decisions: Records user's final decision after deliberation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "zzzg_user_decisions"
down_revision: str | Sequence[str] | None = "zzzf_decision_topic_bank"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_decisions table with RLS."""
    op.create_table(
        "user_decisions",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("session_id", sa.String(255), nullable=False, unique=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("chosen_option_id", sa.String(50), nullable=False),
        sa.Column("chosen_option_label", sa.Text(), nullable=False),
        sa.Column("chosen_option_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("rationale", JSONB(), nullable=True),
        sa.Column("matrix_snapshot", JSONB(), nullable=True),
        sa.Column("decision_source", sa.String(20), nullable=False, server_default="direct"),
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
    )

    # Indexes
    op.create_index("ix_user_decisions_session_id", "user_decisions", ["session_id"])
    op.create_index("ix_user_decisions_user_id", "user_decisions", ["user_id"])

    # Enable RLS
    op.execute("ALTER TABLE user_decisions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE user_decisions FORCE ROW LEVEL SECURITY")

    # User isolation policy
    op.execute("""
        CREATE POLICY user_decisions_user_isolation ON user_decisions
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', TRUE)::text)
    """)

    # Admin read access
    op.execute("""
        CREATE POLICY user_decisions_admin_access ON user_decisions
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
        CREATE TRIGGER set_user_decisions_updated_at
        BEFORE UPDATE ON user_decisions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop user_decisions table."""
    op.execute("DROP TRIGGER IF EXISTS set_user_decisions_updated_at ON user_decisions")
    op.execute("DROP POLICY IF EXISTS user_decisions_admin_access ON user_decisions")
    op.execute("DROP POLICY IF EXISTS user_decisions_user_isolation ON user_decisions")
    op.drop_index("ix_user_decisions_user_id", table_name="user_decisions")
    op.drop_index("ix_user_decisions_session_id", table_name="user_decisions")
    op.drop_table("user_decisions")
