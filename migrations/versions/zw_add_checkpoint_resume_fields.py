"""Add checkpoint resume fields for sub-problem recovery.

Adds fields to sessions table for tracking last completed sub-problem index
and checkpoint timestamp, enabling resume from last successful SP boundary.

Revision ID: zw_add_checkpoint_resume_fields
Revises: zv_seed_billing_products
Create Date: 2025-12-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "zw_add_checkpoint_resume_fields"
down_revision: str | Sequence[str] | None = "zv_seed_billing_products"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add checkpoint resume fields to sessions table."""
    # Last completed sub-problem index for resume
    op.add_column(
        "sessions",
        sa.Column(
            "last_completed_sp_index",
            sa.Integer,
            nullable=True,
            comment="Index of last successfully completed sub-problem (0-based)",
        ),
    )

    # Timestamp of last SP boundary checkpoint
    op.add_column(
        "sessions",
        sa.Column(
            "sp_checkpoint_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When last SP boundary checkpoint was saved",
        ),
    )

    # Total sub-problems count (for progress display)
    op.add_column(
        "sessions",
        sa.Column(
            "total_sub_problems",
            sa.Integer,
            nullable=True,
            comment="Total number of sub-problems in decomposition",
        ),
    )


def downgrade() -> None:
    """Remove checkpoint resume fields."""
    op.drop_column("sessions", "total_sub_problems")
    op.drop_column("sessions", "sp_checkpoint_at")
    op.drop_column("sessions", "last_completed_sp_index")
