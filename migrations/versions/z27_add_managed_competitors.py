"""Add managed_competitors JSONB column to user_context table.

Stores user-managed competitor entries with name, url, notes, and added_at.
These are competitors the user explicitly adds/manages, separate from:
- competitors: legacy text field with comma-separated names
- competitor_insights: AI-generated insight cards

Revision ID: z27_add_managed_competitors
Revises: z26_add_trend_insights
Create Date: 2025-12-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z27_add_managed_competitors"
down_revision: str | Sequence[str] | None = "z26_add_trend_insights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add managed_competitors JSONB column to user_context table."""
    # Add managed_competitors column
    op.add_column(
        "user_context",
        sa.Column(
            "managed_competitors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="User-managed competitor entries (name, url, notes, added_at)",
        ),
    )

    # Add GIN index for efficient JSONB array querying
    op.create_index(
        "idx_user_context_managed_competitors",
        "user_context",
        ["managed_competitors"],
        postgresql_using="gin",
    )

    # Update table comment to reflect new column
    op.execute(
        "COMMENT ON COLUMN user_context.managed_competitors IS "
        '\'User-managed competitor list. Structure: [{"name": "Company", '
        '"url": "https://...", "notes": "...", "added_at": "2025-01-01T00:00:00Z"}]\''
    )


def downgrade() -> None:
    """Remove managed_competitors column from user_context table."""
    # Drop index
    op.drop_index("idx_user_context_managed_competitors", table_name="user_context")

    # Drop column
    op.drop_column("user_context", "managed_competitors")
