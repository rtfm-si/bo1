"""Add competitor_insights JSONB column to user_context table.

Stores AI-generated competitor insight cards with structured analysis.
Data is tier-gated: Free (1), Starter (3), Pro (unlimited).

Revision ID: z25_add_competitor_insights
Revises: z24_add_mentor_conversations
Create Date: 2025-12-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z25_add_competitor_insights"
down_revision: str | Sequence[str] | None = "z24_add_mentor_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add competitor_insights JSONB column to user_context table."""
    # Add competitor_insights column
    op.add_column(
        "user_context",
        sa.Column(
            "competitor_insights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment="AI-generated competitor insight cards keyed by competitor name",
        ),
    )

    # Add GIN index for efficient JSONB querying
    op.create_index(
        "idx_user_context_competitor_insights",
        "user_context",
        ["competitor_insights"],
        postgresql_using="gin",
    )

    # Update table comment to reflect new column
    op.execute(
        "COMMENT ON COLUMN user_context.competitor_insights IS "
        '\'AI-generated competitor insight cards. Structure: {"CompanyName": {"name": ..., '
        '"tagline": ..., "size_estimate": ..., "revenue_estimate": ..., '
        '"strengths": [...], "weaknesses": [...], "market_gaps": [...], "last_updated": ...}}\''
    )


def downgrade() -> None:
    """Remove competitor_insights column from user_context table."""
    # Drop index
    op.drop_index("idx_user_context_competitor_insights", table_name="user_context")

    # Drop column
    op.drop_column("user_context", "competitor_insights")
