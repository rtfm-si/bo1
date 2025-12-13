"""Add analysis column to feedback table.

This migration adds:
- analysis JSONB column to store sentiment and theme extraction results
- Index on analysis->'sentiment' for filtering by sentiment

Revision ID: am1_add_feedback_analysis
Revises: al1_add_calendar_integration
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "am1_add_feedback_analysis"
down_revision: str | Sequence[str] | None = "al1_calendar_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add analysis column to feedback table."""
    # Add analysis JSONB column
    # Structure: {
    #   sentiment: string (positive/negative/neutral/mixed),
    #   sentiment_confidence: float (0.0-1.0),
    #   themes: string[] (1-5 tags),
    #   analyzed_at: string (ISO timestamp)
    # }
    op.add_column(
        "feedback",
        sa.Column(
            "analysis",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
    )

    # Index on sentiment for filtering
    op.execute(
        """
        CREATE INDEX ix_feedback_analysis_sentiment
        ON feedback ((analysis->>'sentiment'))
        WHERE analysis IS NOT NULL
        """
    )


def downgrade() -> None:
    """Remove analysis column from feedback table."""
    op.execute("DROP INDEX IF EXISTS ix_feedback_analysis_sentiment")
    op.drop_column("feedback", "analysis")
