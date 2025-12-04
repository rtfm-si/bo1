"""Create action_dependencies table for dependency tracking.

Enables actions to depend on other actions with different dependency types.
Supports automatic date cascading and blocking/unblocking.

Revision ID: a2_create_action_dependencies
Revises: a1_create_actions_table
Create Date: 2025-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2_create_action_dependencies"
down_revision: str | Sequence[str] | None = "a1_create_actions_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create action_dependencies table."""
    # Create action_dependencies table (using VARCHAR with CHECK instead of ENUM)
    op.create_table(
        "action_dependencies",
        sa.Column(
            "action_id",
            sa.UUID(),
            nullable=False,
            comment="Action that has a dependency",
        ),
        sa.Column(
            "depends_on_action_id",
            sa.UUID(),
            nullable=False,
            comment="Action that must complete first",
        ),
        sa.Column(
            "dependency_type",
            sa.String(length=30),
            nullable=False,
            server_default="finish_to_start",
            comment="Type of dependency relationship",
        ),
        sa.Column(
            "lag_days",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Lag in business days (can be negative for lead)",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_action_id"], ["actions.id"], ondelete="CASCADE"),
        # Constraints
        sa.CheckConstraint(
            "dependency_type IN ('finish_to_start', 'start_to_start', 'finish_to_finish')",
            name="check_valid_dependency_type",
        ),
        sa.CheckConstraint(
            "action_id != depends_on_action_id",
            name="check_no_self_dependency",
        ),
        sa.UniqueConstraint("action_id", "depends_on_action_id", name="unique_action_dependency"),
        sa.PrimaryKeyConstraint("action_id", "depends_on_action_id"),
    )

    # Indexes for efficient dependency queries
    op.create_index("idx_action_deps_action_id", "action_dependencies", ["action_id"])
    op.create_index("idx_action_deps_depends_on", "action_dependencies", ["depends_on_action_id"])

    # Comments
    op.execute("""
        COMMENT ON TABLE action_dependencies IS 'Action dependency relationships for automatic scheduling and blocking';
        COMMENT ON COLUMN action_dependencies.dependency_type IS 'finish_to_start: predecessor must finish before successor starts, start_to_start: both start together, finish_to_finish: both finish together';
        COMMENT ON COLUMN action_dependencies.lag_days IS 'Business days offset (positive = delay, negative = lead time). Example: finish_to_start with lag_days=2 means wait 2 days after predecessor finishes';
    """)


def downgrade() -> None:
    """Remove action_dependencies table."""
    op.drop_index("idx_action_deps_depends_on", table_name="action_dependencies")
    op.drop_index("idx_action_deps_action_id", table_name="action_dependencies")
    op.drop_table("action_dependencies")
