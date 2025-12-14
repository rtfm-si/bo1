"""Add workspace_id to projects table with same-workspace constraint for session_projects.

Ensures projects belong to a workspace and meetings can only link to projects in the same workspace.

Revision ID: av1_add_workspace_to_projects
Revises: au1_add_workspace_role_audit
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "av1_add_workspace_to_projects"
down_revision: str | Sequence[str] | None = "au1_add_workspace_role_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add workspace_id to projects and enforce workspace match in session_projects."""
    # Add workspace_id column to projects (nullable initially for existing data)
    op.add_column(
        "projects",
        sa.Column(
            "workspace_id",
            sa.UUID(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
            comment="Workspace this project belongs to (NULL for personal projects)",
        ),
    )

    # Index for workspace filtering
    op.create_index(
        "ix_projects_workspace_id",
        "projects",
        ["workspace_id"],
    )

    # Create a function to validate workspace match between session and project
    op.execute("""
        CREATE OR REPLACE FUNCTION validate_session_project_workspace()
        RETURNS TRIGGER AS $$
        DECLARE
            session_workspace_id UUID;
            project_workspace_id UUID;
        BEGIN
            -- Get workspace IDs
            SELECT workspace_id INTO session_workspace_id
            FROM sessions WHERE id = NEW.session_id;

            SELECT workspace_id INTO project_workspace_id
            FROM projects WHERE id = NEW.project_id;

            -- Allow if both are NULL (personal) or both match
            IF session_workspace_id IS NULL AND project_workspace_id IS NULL THEN
                RETURN NEW;
            ELSIF session_workspace_id = project_workspace_id THEN
                RETURN NEW;
            ELSE
                RAISE EXCEPTION 'Session and project must belong to the same workspace';
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger to enforce workspace match on session_projects
    op.execute("""
        CREATE TRIGGER trg_session_project_workspace_check
        BEFORE INSERT OR UPDATE ON session_projects
        FOR EACH ROW
        EXECUTE FUNCTION validate_session_project_workspace();
    """)

    # Add comment
    op.execute("""
        COMMENT ON COLUMN projects.workspace_id IS 'FK to workspaces.id - projects must match session workspace for linking';
    """)


def downgrade() -> None:
    """Remove workspace_id from projects and associated trigger."""
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS trg_session_project_workspace_check ON session_projects;")
    op.execute("DROP FUNCTION IF EXISTS validate_session_project_workspace();")

    # Drop index and column
    op.drop_index("ix_projects_workspace_id", table_name="projects")
    op.drop_column("projects", "workspace_id")
