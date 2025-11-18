"""Add actions table for Action Tracking Lite.

Enables post-deliberation action tracking (extract, review, save, track).
Users can extract 3-7 actions from synthesis, set target dates, and view in dashboard.

NOT included in Lite version (defer to v2.0):
- Status tracking (in_progress, blocked, completed)
- Reminders & notifications
- Replanning deliberations
- Success criteria field
- Dependencies

Revision ID: 2f7e9d4c8b1a
Revises: 8a5d2f9e1b3c
Create Date: 2025-01-18 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "2f7e9d4c8b1a"
down_revision: str | Sequence[str] | None = "8a5d2f9e1b3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - add actions table."""
    # Create actions table
    op.create_table(
        "actions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=255),  # Match users.id type (VARCHAR not UUID)
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.String(length=255),  # Match sessions.id type (VARCHAR not UUID)
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Content
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("target_date", sa.Date, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="1"),
        # Metadata
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # Constraints
        sa.CheckConstraint("length(description) <= 500", name="actions_description_max_length"),
        sa.CheckConstraint("priority >= 1 AND priority <= 10", name="actions_priority_range"),
    )

    # Create indexes for performance
    op.create_index("idx_actions_user_id", "actions", ["user_id"])
    op.create_index("idx_actions_session_id", "actions", ["session_id"])
    op.create_index("idx_actions_target_date", "actions", ["target_date"])
    op.create_index(
        "idx_actions_user_target_date",
        "actions",
        ["user_id", "target_date"],
        # Composite index for dashboard queries (user's actions sorted by date)
    )

    # Create trigger to auto-update updated_at timestamp
    # Note: update_updated_at_column() function already exists from beta_whitelist migration
    op.execute(
        """
        CREATE TRIGGER update_actions_updated_at
        BEFORE UPDATE ON actions
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
        """
    )

    # Enable Row-Level Security (RLS)
    op.execute("ALTER TABLE actions ENABLE ROW LEVEL SECURITY;")

    # Create RLS policy: users can only access their own actions
    # Note: Uses current_setting() for compatibility with non-Supabase PostgreSQL (CI, local dev)
    # The user_id in actions table directly matches users.id
    op.execute(
        """
        CREATE POLICY "users_own_actions" ON actions
            FOR ALL
            USING (user_id = current_setting('app.current_user_id', TRUE)::text);
        """
    )

    # Optional: Create policy for admins to view all actions (for support/debugging)
    # Note: subscription_tier column name, not 'tier'
    op.execute(
        """
        CREATE POLICY "admins_view_all_actions" ON actions
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1
                    FROM users
                    WHERE id = current_setting('app.current_user_id', TRUE)::text
                    AND subscription_tier = 'admin'
                )
            );
        """
    )


def downgrade() -> None:
    """Downgrade schema - remove actions table."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS admins_view_all_actions ON actions;")
    op.execute("DROP POLICY IF EXISTS users_own_actions ON actions;")

    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_actions_updated_at ON actions;")

    # Drop indexes
    op.drop_index("idx_actions_user_target_date", table_name="actions")
    op.drop_index("idx_actions_target_date", table_name="actions")
    op.drop_index("idx_actions_session_id", table_name="actions")
    op.drop_index("idx_actions_user_id", table_name="actions")

    # Drop table
    op.drop_table("actions")
