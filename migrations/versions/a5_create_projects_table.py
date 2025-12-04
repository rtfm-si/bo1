"""Create projects table for grouping related actions.

Projects are value-delivery containers that group related actions.
Sessions can discuss/create projects, and actions belong to projects.

Revision ID: a5_create_projects_table
Revises: a4_migrate_session_tasks_data
Create Date: 2025-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "a5_create_projects_table"
down_revision: str | Sequence[str] | None = "a4_migrate_session_tasks_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create projects table with comprehensive project management fields."""
    # Note: Using VARCHAR with CHECK constraint instead of ENUM for simpler migrations

    op.create_table(
        "projects",
        # Identity
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        # Core fields
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Status (VARCHAR with CHECK instead of ENUM for simpler migrations)
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
        # Date fields
        sa.Column(
            "target_start_date", sa.Date(), nullable=True, comment="User-set target start date"
        ),
        sa.Column("target_end_date", sa.Date(), nullable=True, comment="User-set target end date"),
        sa.Column(
            "estimated_start_date",
            sa.Date(),
            nullable=True,
            comment="Calculated: min(actions.estimated_start_date)",
        ),
        sa.Column(
            "estimated_end_date",
            sa.Date(),
            nullable=True,
            comment="Calculated: max(actions.estimated_end_date)",
        ),
        sa.Column(
            "actual_start_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When first action started",
        ),
        sa.Column(
            "actual_end_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When all actions completed",
        ),
        # Progress tracking
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Calculated from completed actions",
        ),
        sa.Column(
            "total_actions",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Total number of actions in project",
        ),
        sa.Column(
            "completed_actions",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of completed actions",
        ),
        # Visual customization
        sa.Column(
            "color",
            sa.String(length=7),
            nullable=True,
            comment="Hex color for Gantt visualization",
        ),
        sa.Column(
            "icon",
            sa.String(length=50),
            nullable=True,
            comment="Emoji or icon name",
        ),
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
        # Constraints
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'completed', 'archived')",
            name="check_project_valid_status",
        ),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="check_project_progress_range",
        ),
        sa.CheckConstraint(
            "target_end_date IS NULL OR target_start_date IS NULL OR target_end_date >= target_start_date",
            name="check_project_target_dates_logical",
        ),
        sa.CheckConstraint("total_actions >= 0", name="check_project_total_actions_non_negative"),
        sa.CheckConstraint(
            "completed_actions >= 0 AND completed_actions <= total_actions",
            name="check_project_completed_actions_valid",
        ),
    )

    # Indexes for efficient queries
    op.create_index("idx_projects_user_id", "projects", ["user_id"])
    op.create_index("idx_projects_status", "projects", ["status"])
    op.create_index("idx_projects_user_status", "projects", ["user_id", "status"])
    op.create_index("idx_projects_created_at", "projects", ["created_at"], postgresql_using="btree")
    op.create_index("idx_projects_updated_at", "projects", ["updated_at"], postgresql_using="btree")
    op.create_index("idx_projects_target_end", "projects", ["target_end_date"])
    op.create_index("idx_projects_estimated_end", "projects", ["estimated_end_date"])

    # Comments
    op.execute("""
        COMMENT ON TABLE projects IS 'Projects are value-delivery containers that group related actions';
        COMMENT ON COLUMN projects.id IS 'UUID primary key';
        COMMENT ON COLUMN projects.user_id IS 'Owner of the project (FK to users.id)';
        COMMENT ON COLUMN projects.name IS 'Project name';
        COMMENT ON COLUMN projects.description IS 'Project description and goals';
        COMMENT ON COLUMN projects.status IS 'Current status: active, paused, completed, archived';
    """)


def downgrade() -> None:
    """Remove projects table."""
    op.drop_index("idx_projects_estimated_end", table_name="projects")
    op.drop_index("idx_projects_target_end", table_name="projects")
    op.drop_index("idx_projects_updated_at", table_name="projects")
    op.drop_index("idx_projects_created_at", table_name="projects")
    op.drop_index("idx_projects_user_status", table_name="projects")
    op.drop_index("idx_projects_status", table_name="projects")
    op.drop_index("idx_projects_user_id", table_name="projects")
    op.drop_table("projects")
