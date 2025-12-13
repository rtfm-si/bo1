"""Create feedback table.

This migration adds:
- feedback table: stores feature requests and problem reports
- Indexes for efficient querying by user, type, status, created_at

Revision ID: ak1_create_feedback
Revises: aj1_add_session_promo_tracking
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ak1_create_feedback"
down_revision: str | Sequence[str] | None = "aj1_add_session_promo_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create feedback table."""
    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            sa.String(length=20),
            nullable=False,
        ),  # feature_request, problem_report
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "context",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),  # Auto-attached context for problem reports
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="new",
        ),  # new, reviewing, resolved, closed
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Check constraint for valid feedback types
        sa.CheckConstraint(
            "type IN ('feature_request', 'problem_report')",
            name="ck_feedback_type",
        ),
        # Check constraint for valid status
        sa.CheckConstraint(
            "status IN ('new', 'reviewing', 'resolved', 'closed')",
            name="ck_feedback_status",
        ),
    )

    # Index on user_id for querying user's feedback
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])

    # Index on type for filtering by type
    op.create_index("ix_feedback_type", "feedback", ["type"])

    # Index on status for filtering by status
    op.create_index("ix_feedback_status", "feedback", ["status"])

    # Index on created_at for sorting
    op.create_index("ix_feedback_created_at", "feedback", ["created_at"])


def downgrade() -> None:
    """Remove feedback table."""
    op.drop_index("ix_feedback_created_at", table_name="feedback")
    op.drop_index("ix_feedback_status", table_name="feedback")
    op.drop_index("ix_feedback_type", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
