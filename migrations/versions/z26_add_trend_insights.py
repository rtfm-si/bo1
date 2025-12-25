"""Add trend_insights JSONB column to user_context table.

Stores AI-generated trend insights keyed by URL.
Cost: ~$0.003/request (Haiku rates).

Revision ID: z26_add_trend_insights
Revises: z25_add_competitor_insights
Create Date: 2025-12-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z26_add_trend_insights"
down_revision: str | Sequence[str] | None = "z25_add_competitor_insights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add trend_insights JSONB column to user_context table."""
    # Add trend_insights column
    op.add_column(
        "user_context",
        sa.Column(
            "trend_insights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment="AI-generated trend insights keyed by URL",
        ),
    )

    # Add GIN index for efficient JSONB querying
    op.create_index(
        "idx_user_context_trend_insights",
        "user_context",
        ["trend_insights"],
        postgresql_using="gin",
    )

    # Update column comment with schema documentation
    op.execute(
        "COMMENT ON COLUMN user_context.trend_insights IS "
        '\'AI-generated trend insights. Structure: {"https://...": {"url": ..., '
        '"title": ..., "key_takeaway": ..., "relevance": ..., '
        '"actions": [...], "timeframe": ..., "confidence": ..., "analyzed_at": ...}}\''
    )


def downgrade() -> None:
    """Remove trend_insights column from user_context table."""
    # Drop index
    op.drop_index("idx_user_context_trend_insights", table_name="user_context")

    # Drop column
    op.drop_column("user_context", "trend_insights")
