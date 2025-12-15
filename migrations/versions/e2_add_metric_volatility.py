"""Add metric volatility tracking columns to user_context.

Adds columns to support volatile metric staleness detection:
- metric_volatility_cache: JSONB mapping field_name → VolatilityLevel
- last_refresh_prompted_at: Timestamp of last stale metric prompt
- refresh_prompted_fields: Array of fields user was prompted about

Revision ID: e2_add_metric_volatility
Revises: d3_clarifications
Create Date: 2025-12-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e2_add_metric_volatility"
down_revision: str | None = "d3_clarifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add metric volatility tracking columns."""
    # Cache for computed volatility levels to avoid recalculation
    # Schema: {field_name: {"level": "volatile"|"moderate"|"stable", "computed_at": ISO timestamp}}
    op.add_column(
        "user_context",
        sa.Column(
            "metric_volatility_cache",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )

    # Track when user was last prompted about stale metrics
    op.add_column(
        "user_context",
        sa.Column(
            "last_refresh_prompted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # Track which fields user was prompted about (to avoid re-prompting)
    # Schema: ["field1", "field2", ...]
    op.add_column(
        "user_context",
        sa.Column(
            "refresh_prompted_fields",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Remove metric volatility tracking columns."""
    op.drop_column("user_context", "refresh_prompted_fields")
    op.drop_column("user_context", "last_refresh_prompted_at")
    op.drop_column("user_context", "metric_volatility_cache")
