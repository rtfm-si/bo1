"""Add context_metric_history and pending_updates columns to user_context.

This migration adds:
1. context_metric_history JSONB - stores last 10 values per field for trend analysis
   Schema: {field_name: [{value, recorded_at, source_type, source_id}]}
2. pending_updates JSONB - stores low-confidence update suggestions for user review
   Schema: [{id, field_name, new_value, confidence, source_type, source_text, extracted_at}]

Revision ID: ad1_add_context_metric_history
Revises: ac1_extend_retention_range
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ad1_add_context_metric_history"
down_revision: str | Sequence[str] | None = "ac1_extend_retention_range"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add context_metric_history and pending_updates columns."""
    # Add context_metric_history JSONB column with default empty object
    op.add_column(
        "user_context",
        sa.Column(
            "context_metric_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )

    # Add pending_updates JSONB column with default empty array
    op.add_column(
        "user_context",
        sa.Column(
            "pending_updates",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """Remove context_metric_history and pending_updates columns."""
    op.drop_column("user_context", "pending_updates")
    op.drop_column("user_context", "context_metric_history")
