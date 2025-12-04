"""Add project_id column to actions table.

Links actions to their parent project.
Actions can optionally belong to a project (nullable FK).

Revision ID: a7_add_project_id_to_actions
Revises: a6_create_session_projects_table
Create Date: 2025-12-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "a7_add_project_id_to_actions"
down_revision: str | Sequence[str] | None = "a6_create_session_projects_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add project_id column to actions table."""
    # Add project_id column (nullable - actions can exist without a project)
    op.add_column(
        "actions",
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            nullable=True,
            comment="Parent project (optional)",
        ),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_actions_project_id",
        "actions",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",  # Keep action if project is deleted
    )

    # Add index for efficient project-based queries
    op.create_index("idx_actions_project_id", "actions", ["project_id"])
    op.create_index(
        "idx_actions_project_status",
        "actions",
        ["project_id", "status"],
        postgresql_where=sa.text("project_id IS NOT NULL"),
    )

    # Comments
    op.execute("""
        COMMENT ON COLUMN actions.project_id IS 'Optional parent project - actions can exist independently or belong to a project';
    """)


def downgrade() -> None:
    """Remove project_id column from actions table."""
    op.drop_index("idx_actions_project_status", table_name="actions")
    op.drop_index("idx_actions_project_id", table_name="actions")
    op.drop_constraint("fk_actions_project_id", "actions", type_="foreignkey")
    op.drop_column("actions", "project_id")
