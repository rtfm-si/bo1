"""Add persistence tables.

Add tables for complete deliberation output persistence:
- recommendations: Expert recommendations during voting phase
- sub_problem_results: Per-sub-problem synthesis and expert summaries
- facilitator_decisions: Facilitator routing decisions

Revision ID: 80cf34f1b577
Revises: 622dbc22743e
Create Date: 2025-11-27 23:16:08.042882
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80cf34f1b577"
down_revision: str | Sequence[str] | None = "622dbc22743e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Recommendations table (replaces votes for free-form recommendations)
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sub_problem_index", sa.Integer, nullable=True),
        sa.Column("persona_code", sa.String(length=50), nullable=False),
        sa.Column("persona_name", sa.String(length=255), nullable=True),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("conditions", sa.JSON, nullable=True),
        sa.Column("weight", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Sub-problem results table
    op.create_table(
        "sub_problem_results",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sub_problem_index", sa.Integer, nullable=False),
        sa.Column("goal", sa.Text, nullable=False),
        sa.Column("synthesis", sa.Text, nullable=True),
        sa.Column("expert_summaries", sa.JSON, nullable=True),
        sa.Column("cost", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("contribution_count", sa.Integer, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Facilitator decisions table
    op.create_table(
        "facilitator_decisions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("sub_problem_index", sa.Integer, nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("next_speaker", sa.String(length=50), nullable=True),
        sa.Column("moderator_type", sa.String(length=50), nullable=True),
        sa.Column("research_query", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Create indexes
    op.create_index("idx_recommendations_session_id", "recommendations", ["session_id"])
    op.create_index("idx_sub_problem_results_session_id", "sub_problem_results", ["session_id"])
    op.create_index(
        "idx_sub_problem_results_session_subproblem",
        "sub_problem_results",
        ["session_id", "sub_problem_index"],
        unique=True,
    )
    op.create_index("idx_facilitator_decisions_session_id", "facilitator_decisions", ["session_id"])

    # Enable RLS
    op.execute("ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sub_problem_results ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE facilitator_decisions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_facilitator_decisions_session_id")
    op.drop_index("idx_sub_problem_results_session_subproblem")
    op.drop_index("idx_sub_problem_results_session_id")
    op.drop_index("idx_recommendations_session_id")

    # Drop tables
    op.drop_table("facilitator_decisions")
    op.drop_table("sub_problem_results")
    op.drop_table("recommendations")
