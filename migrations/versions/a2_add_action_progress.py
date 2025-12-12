"""Add progress tracking fields to actions table.

Adds columns for:
- progress_type: track progress as percentage, points, or status only
- progress_value: numeric value for percentage/points
- estimated_effort_points: for velocity tracking
- actual_finish_date: when work completed (already exists in table)
- scheduled_start_date: original plan date

Revision ID: a2_add_action_progress
Revises: z1_add_storage_path
Create Date: 2025-12-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2_add_action_progress"
down_revision: str | Sequence[str] | None = "z1_add_storage_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add progress tracking columns to actions table."""
    # Add progress_type column (percentage, points, status_only)
    op.add_column(
        "actions",
        sa.Column(
            "progress_type",
            sa.String(length=20),
            nullable=False,
            server_default="status_only",
            comment="Progress tracking method: percentage, points, or status_only",
        ),
    )

    # Add progress_value column (0-100 for %, 0-* for points, null for status_only)
    op.add_column(
        "actions",
        sa.Column(
            "progress_value",
            sa.Integer(),
            nullable=True,
            comment="Progress value: 0-100 for percentage, 0+ for points",
        ),
    )

    # Add estimated_effort_points column (for velocity tracking)
    op.add_column(
        "actions",
        sa.Column(
            "estimated_effort_points",
            sa.Integer(),
            nullable=True,
            comment="Estimated effort in story points or custom units",
        ),
    )

    # Add scheduled_start_date column (original plan, defaults to created_at if not set)
    op.add_column(
        "actions",
        sa.Column(
            "scheduled_start_date",
            sa.Date(),
            nullable=True,
            comment="Original planned start date (inferred from created_at if not set)",
        ),
    )

    # Add check constraint for progress_value bounds
    op.create_check_constraint(
        "check_progress_value_valid",
        "actions",
        "(progress_value IS NULL OR progress_value >= 0)",
    )

    # Add check constraint for progress_type values
    op.create_check_constraint(
        "check_progress_type_valid",
        "actions",
        "progress_type IN ('percentage', 'points', 'status_only')",
    )

    # Add check constraint: percentage must be 0-100
    op.create_check_constraint(
        "check_percentage_range",
        "actions",
        "(progress_type != 'percentage' OR (progress_value >= 0 AND progress_value <= 100))",
    )

    # Add index for progress queries
    op.create_index("idx_actions_progress_type", "actions", ["progress_type"])
    op.create_index("idx_actions_progress_value", "actions", ["progress_value"])


def downgrade() -> None:
    """Remove progress tracking columns from actions table."""
    op.drop_index("idx_actions_progress_value", table_name="actions")
    op.drop_index("idx_actions_progress_type", table_name="actions")
    op.drop_constraint("check_percentage_range", "actions", type_="check")
    op.drop_constraint("check_progress_type_valid", "actions", type_="check")
    op.drop_constraint("check_progress_value_valid", "actions", type_="check")
    op.drop_column("actions", "scheduled_start_date")
    op.drop_column("actions", "estimated_effort_points")
    op.drop_column("actions", "progress_value")
    op.drop_column("actions", "progress_type")
