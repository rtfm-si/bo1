"""Add working_pattern column to user_context.

Stores user's regular working days (Mon-Fri default).
Schema: {"working_days": [1,2,3,4,5], "working_hours": null}

Revision ID: zp_add_working_pattern
Revises: zo_performance_thresholds
Create Date: 2025-12-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "zp_add_working_pattern"
down_revision: str = "zo_performance_thresholds"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Add working_pattern JSONB column to user_context."""
    op.add_column(
        "user_context",
        sa.Column(
            "working_pattern",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="User's working pattern: {working_days: [1-7], working_hours: null}",
        ),
    )


def downgrade() -> None:
    """Remove working_pattern column."""
    op.drop_column("user_context", "working_pattern")
