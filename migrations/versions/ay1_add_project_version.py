"""Add version column to projects table for project versioning.

Completed projects cannot be reopened; instead, users create new versions.
Each version has an incrementing version number (v1, v2, etc).

Revision ID: ay1_add_project_version
Revises: ax1_add_cost_calculator_defaults
Create Date: 2025-12-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ay1_add_project_version"
down_revision: str | Sequence[str] | None = (
    "ax1_add_cost_calculator_defaults",
    "e3_clean_empty_insights",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add version column to projects table."""
    # Add version column with default 1
    op.add_column(
        "projects",
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Version number for project versioning (v1, v2, etc)",
        ),
    )

    # Add source_project_id to track lineage
    op.add_column(
        "projects",
        sa.Column(
            "source_project_id",
            sa.UUID(as_uuid=True),
            nullable=True,
            comment="ID of the project this was versioned from",
        ),
    )

    # Add foreign key for source_project_id
    op.create_foreign_key(
        "fk_projects_source_project",
        "projects",
        "projects",
        ["source_project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add unique constraint on (user_id, name, version) to prevent duplicates
    op.create_unique_constraint(
        "uq_projects_user_name_version",
        "projects",
        ["user_id", "name", "version"],
    )

    # Add index for version queries
    op.create_index("idx_projects_version", "projects", ["version"])
    op.create_index("idx_projects_source_project", "projects", ["source_project_id"])


def downgrade() -> None:
    """Remove version column from projects table."""
    op.drop_index("idx_projects_source_project", table_name="projects")
    op.drop_index("idx_projects_version", table_name="projects")
    op.drop_constraint("uq_projects_user_name_version", "projects", type_="unique")
    op.drop_constraint("fk_projects_source_project", "projects", type_="foreignkey")
    op.drop_column("projects", "source_project_id")
    op.drop_column("projects", "version")
