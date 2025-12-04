"""Create session_projects link table.

Links sessions to projects they discuss/created/replanning.
A session can discuss multiple projects, and a project can have multiple sessions.

Revision ID: a6_create_session_projects_table
Revises: a5_create_projects_table
Create Date: 2025-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6_create_session_projects_table"
down_revision: str | Sequence[str] | None = "a5_create_projects_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create session_projects link table."""
    op.create_table(
        "session_projects",
        # Composite primary key
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        # Relationship type
        sa.Column(
            "relationship",
            sa.String(length=50),
            nullable=False,
            server_default="discusses",
            comment="Type of relationship: discusses, created_from, replanning",
        ),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        # Primary key
        sa.PrimaryKeyConstraint("session_id", "project_id"),
        # Foreign keys
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        # Constraints
        sa.CheckConstraint(
            "relationship IN ('discusses', 'created_from', 'replanning')",
            name="check_session_project_relationship",
        ),
    )

    # Indexes for efficient queries
    op.create_index("idx_session_projects_session", "session_projects", ["session_id"])
    op.create_index("idx_session_projects_project", "session_projects", ["project_id"])
    op.create_index("idx_session_projects_relationship", "session_projects", ["relationship"])

    # Comments
    op.execute("""
        COMMENT ON TABLE session_projects IS 'Links sessions to projects they discuss, created, or are replanning';
        COMMENT ON COLUMN session_projects.session_id IS 'FK to sessions.id';
        COMMENT ON COLUMN session_projects.project_id IS 'FK to projects.id';
        COMMENT ON COLUMN session_projects.relationship IS 'discusses: session mentions project, created_from: session created the project, replanning: session is replanning blocked project';
    """)


def downgrade() -> None:
    """Remove session_projects table."""
    op.drop_index("idx_session_projects_relationship", table_name="session_projects")
    op.drop_index("idx_session_projects_project", table_name="session_projects")
    op.drop_index("idx_session_projects_session", table_name="session_projects")
    op.drop_table("session_projects")
