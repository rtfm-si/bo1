"""Create actions table for comprehensive action management.

Replaces JSONB session_tasks with proper relational table for actions.
Includes status tracking, dependencies, dates, and blocking mechanisms.

Revision ID: a1_create_actions_table
Revises: b1c2d3e4f5g6
Create Date: 2025-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "a1_create_actions_table"
down_revision: str | Sequence[str] | None = "f5g6h7i8j9k0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create actions table with comprehensive action management fields."""
    # Drop existing lightweight actions table (from 2f7e9d4c8b1a_add_actions_lite.py)
    # This is safe since user confirmed no live customers and breaking changes are OK
    op.execute("""
        DROP POLICY IF EXISTS admins_view_all_actions ON actions;
        DROP POLICY IF EXISTS users_own_actions ON actions;
        DROP TRIGGER IF EXISTS update_actions_updated_at ON actions;
        DROP TABLE IF EXISTS actions CASCADE;
    """)

    # Note: Using VARCHAR with CHECK constraint instead of ENUM for simpler migrations

    # Create actions table
    op.create_table(
        "actions",
        # Identity
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("source_session_id", sa.String(length=255), nullable=False),
        # Core fields from ExtractedTask
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("what_and_how", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("success_criteria", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("kill_criteria", sa.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        # Status and tracking (VARCHAR with CHECK instead of ENUM for simpler migrations)
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column(
            "category", sa.String(length=50), nullable=False, server_default="implementation"
        ),
        # Timeline fields
        sa.Column(
            "timeline",
            sa.Text(),
            nullable=True,
            comment="Human-readable timeline (e.g., '2 weeks')",
        ),
        sa.Column(
            "estimated_duration_days",
            sa.Integer(),
            nullable=True,
            comment="Parsed duration in business days",
        ),
        # Date fields (DATE for target/estimated, TIMESTAMPTZ for actual)
        sa.Column(
            "target_start_date", sa.Date(), nullable=True, comment="User-set target start date"
        ),
        sa.Column("target_end_date", sa.Date(), nullable=True, comment="User-set target end date"),
        sa.Column(
            "estimated_start_date",
            sa.Date(),
            nullable=True,
            comment="Auto-calculated from dependencies",
        ),
        sa.Column(
            "estimated_end_date",
            sa.Date(),
            nullable=True,
            comment="Auto-calculated from start + duration",
        ),
        sa.Column(
            "actual_start_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Actual start timestamp",
        ),
        sa.Column(
            "actual_end_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Actual completion timestamp",
        ),
        # Blocking mechanism
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "auto_unblock",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Auto-unblock when dependencies complete",
        ),
        # Source metadata
        sa.Column(
            "confidence", sa.Numeric(precision=3, scale=2), nullable=False, server_default="0.0"
        ),
        sa.Column("source_section", sa.Text(), nullable=True),
        sa.Column("sub_problem_index", sa.Integer(), nullable=True),
        # Ordering
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_session_id"], ["sessions.id"], ondelete="CASCADE"),
        # Constraints
        sa.CheckConstraint(
            "status IN ('todo', 'in_progress', 'blocked', 'in_review', 'done', 'cancelled')",
            name="check_valid_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0", name="check_action_confidence"
        ),
        sa.CheckConstraint(
            "estimated_duration_days IS NULL OR estimated_duration_days > 0",
            name="check_estimated_duration_positive",
        ),
        sa.CheckConstraint(
            "(status = 'blocked' AND blocking_reason IS NOT NULL) OR (status != 'blocked')",
            name="check_blocked_requires_reason",
        ),
        sa.CheckConstraint(
            "target_end_date IS NULL OR target_start_date IS NULL OR target_end_date >= target_start_date",
            name="check_target_dates_logical",
        ),
    )

    # Indexes for efficient queries
    op.create_index("idx_actions_user_id", "actions", ["user_id"])
    op.create_index("idx_actions_session_id", "actions", ["source_session_id"])
    op.create_index("idx_actions_status", "actions", ["status"])
    op.create_index("idx_actions_user_status", "actions", ["user_id", "status"])
    op.create_index("idx_actions_priority", "actions", ["priority"])
    op.create_index("idx_actions_created_at", "actions", ["created_at"], postgresql_using="btree")
    op.create_index("idx_actions_updated_at", "actions", ["updated_at"], postgresql_using="btree")
    op.create_index("idx_actions_target_start", "actions", ["target_start_date"])
    op.create_index("idx_actions_estimated_start", "actions", ["estimated_start_date"])

    # Composite indexes for common queries
    op.create_index(
        "idx_actions_user_status_priority",
        "actions",
        ["user_id", "status", "priority"],
    )
    op.create_index(
        "idx_actions_user_dates",
        "actions",
        ["user_id", "estimated_start_date", "estimated_end_date"],
    )

    # Comments
    op.execute("""
        COMMENT ON TABLE actions IS 'Comprehensive action tracking table - replaces session_tasks JSONB with proper relational schema';
        COMMENT ON COLUMN actions.id IS 'UUID primary key';
        COMMENT ON COLUMN actions.user_id IS 'Owner of the action (FK to users.user_id)';
        COMMENT ON COLUMN actions.source_session_id IS 'Session this action came from (FK to sessions.id)';
        COMMENT ON COLUMN actions.title IS 'Short action title (5-10 words)';
        COMMENT ON COLUMN actions.description IS 'Full action description';
        COMMENT ON COLUMN actions.what_and_how IS 'Array of steps to complete the action';
        COMMENT ON COLUMN actions.success_criteria IS 'Array of success measures';
        COMMENT ON COLUMN actions.kill_criteria IS 'Array of abandonment conditions';
        COMMENT ON COLUMN actions.status IS 'Current status: todo, in_progress, blocked, in_review, done, cancelled';
        COMMENT ON COLUMN actions.priority IS 'Priority: high, medium, low';
        COMMENT ON COLUMN actions.category IS 'Category: implementation, research, decision, communication';
        COMMENT ON COLUMN actions.sort_order IS 'User-defined sort order within status column';
        COMMENT ON COLUMN actions.confidence IS 'AI extraction confidence (0.0-1.0)';
        COMMENT ON COLUMN actions.source_section IS 'Which synthesis section this came from';
        COMMENT ON COLUMN actions.sub_problem_index IS 'Which sub-problem/focus area this belongs to';
    """)


def downgrade() -> None:
    """Remove actions table."""
    op.drop_index("idx_actions_user_dates", table_name="actions")
    op.drop_index("idx_actions_user_status_priority", table_name="actions")
    op.drop_index("idx_actions_estimated_start", table_name="actions")
    op.drop_index("idx_actions_target_start", table_name="actions")
    op.drop_index("idx_actions_updated_at", table_name="actions")
    op.drop_index("idx_actions_created_at", table_name="actions")
    op.drop_index("idx_actions_priority", table_name="actions")
    op.drop_index("idx_actions_user_status", table_name="actions")
    op.drop_index("idx_actions_status", table_name="actions")
    op.drop_index("idx_actions_session_id", table_name="actions")
    op.drop_index("idx_actions_user_id", table_name="actions")
    op.drop_table("actions")
