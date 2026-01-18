"""Add inferred cognitive dimensions to user_cognition.

These dimensions are computed from behavioral patterns, not asked directly.
Part of the hybrid personalization approach:
- Core dimensions: Asked once (Tier 1-2)
- Inferred dimensions: Computed from behavior
- Calibration: Occasional feedback prompts

Revision ID: zzw_cognition_inferred
Revises: zzv_user_cognition
Create Date: 2026-01-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "zzw_cognition_inferred"
down_revision: str | Sequence[str] | None = "zzv_user_cognition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add inferred dimension columns."""
    # Inferred Work Execution Style
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_planning_depth",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=minimal planning, 1=exhaustive (inferred from behavior)",
        ),
    )
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_iteration_style",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=ship fast/iterate, 1=perfect first time (inferred)",
        ),
    )
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_deadline_response",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=energized by deadlines, 1=stressed by deadlines (inferred)",
        ),
    )

    # Inferred Motivation & Energy
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_accountability_pref",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=self-accountable, 1=needs external (inferred)",
        ),
    )
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_challenge_appetite",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=comfort zone, 1=stretch goals (inferred)",
        ),
    )

    # Inferred Communication Preferences
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_format_preference",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=prose/narrative, 1=structured/bullets (inferred)",
        ),
    )
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_example_preference",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=principles/abstract, 1=examples/concrete (inferred)",
        ),
    )

    # Calibration tracking
    op.add_column(
        "user_cognition",
        sa.Column(
            "calibration_responses",
            JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Array of calibration prompt responses for refinement",
        ),
    )
    op.add_column(
        "user_cognition",
        sa.Column(
            "last_calibration_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When user last answered a calibration prompt",
        ),
    )
    op.add_column(
        "user_cognition",
        sa.Column(
            "inferred_dimensions_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When inferred dimensions were last recomputed",
        ),
    )

    # Inference confidence scores (how confident are we in inferences)
    op.add_column(
        "user_cognition",
        sa.Column(
            "inference_confidence",
            JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Confidence scores for each inferred dimension (0-1)",
        ),
    )


def downgrade() -> None:
    """Remove inferred dimension columns."""
    op.drop_column("user_cognition", "inference_confidence")
    op.drop_column("user_cognition", "inferred_dimensions_updated_at")
    op.drop_column("user_cognition", "last_calibration_at")
    op.drop_column("user_cognition", "calibration_responses")
    op.drop_column("user_cognition", "inferred_example_preference")
    op.drop_column("user_cognition", "inferred_format_preference")
    op.drop_column("user_cognition", "inferred_challenge_appetite")
    op.drop_column("user_cognition", "inferred_accountability_pref")
    op.drop_column("user_cognition", "inferred_deadline_response")
    op.drop_column("user_cognition", "inferred_iteration_style")
    op.drop_column("user_cognition", "inferred_planning_depth")
