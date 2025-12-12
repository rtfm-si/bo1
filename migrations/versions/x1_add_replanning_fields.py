"""Add replanning tracking columns to actions table.

Enables tracking when replanning suggestion was shown and what meeting was created
in response to action failure.

Revision ID: x1_add_replanning_fields
Revises: w1_add_gantt_color_strategy
Create Date: 2025-12-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "x1_add_replanning_fields"
down_revision: str | Sequence[str] | None = "w1_add_gantt_color_strategy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add replanning tracking columns."""
    # Create enum type for failure reason category
    op.execute(
        """
        CREATE TYPE failure_reason_category AS ENUM (
            'blocker',
            'scope_creep',
            'dependency',
            'unknown'
        );
        """
    )

    op.add_column(
        "actions",
        sa.Column(
            "failure_reason_category",
            sa.Enum(
                "blocker",
                "scope_creep",
                "dependency",
                "unknown",
                name="failure_reason_category",
            ),
            nullable=True,
            comment="Category of why action failed (blocker/scope_creep/dependency/unknown)",
        ),
    )
    op.add_column(
        "actions",
        sa.Column(
            "replan_suggested_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When replanning suggestion was shown to user",
        ),
    )
    op.add_column(
        "actions",
        sa.Column(
            "replan_session_created_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to session created in response to replanning suggestion",
        ),
    )


def downgrade() -> None:
    """Remove replanning tracking columns."""
    op.drop_constraint(
        "actions_replan_session_created_id_fkey",
        "actions",
        type_="foreignkey",
    )
    op.drop_column("actions", "replan_session_created_id")
    op.drop_column("actions", "replan_suggested_at")
    op.drop_column("actions", "failure_reason_category")
    op.execute("DROP TYPE failure_reason_category;")
