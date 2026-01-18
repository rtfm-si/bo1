"""Create user_cognition table for cognitive profiling.

Captures users' decision-making patterns, strengths, and blindspots.
Used to shape meeting outputs for resonance (cognitive language matching)
and compensation (blindspot countering).

Tier 1 (Lite - Onboarding): 9 questions across 3 instruments
- Cognitive Gravity Map: where mind falls under pressure
- Decision Friction Profile: what slows/unlocks decisions
- Uncertainty Posture Matrix: emotional response to unknown

Tier 2 (After 3+ meetings):
- Leverage Instinct Index: natural power creation style
- Value Tension Scan: competing priorities
- Strategic Time Bias: short vs long-term orientation

Revision ID: zzv_user_cognition
Revises: zzu_competitor_intel
Create Date: 2026-01-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "zzv_user_cognition"
down_revision: str | Sequence[str] | None = "zzu_competitor_intel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_cognition table."""
    op.create_table(
        "user_cognition",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # Tier 1: Cognitive Gravity Map (where mind falls under pressure)
        # 0 = one pole, 1 = opposite pole
        sa.Column(
            "gravity_time_horizon",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=immediate, 1=long-term",
        ),
        sa.Column(
            "gravity_information_density",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=summary, 1=detail",
        ),
        sa.Column(
            "gravity_control_style",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=delegate, 1=hands-on",
        ),
        sa.Column(
            "gravity_assessed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Tier 1: Decision Friction Profile (what slows/unlocks decisions)
        sa.Column(
            "friction_risk_sensitivity",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=risk-tolerant, 1=risk-averse",
        ),
        sa.Column(
            "friction_cognitive_load",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=thrives on complexity, 1=needs simplicity",
        ),
        sa.Column(
            "friction_ambiguity_tolerance",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=tolerant of ambiguity, 1=needs clarity",
        ),
        sa.Column(
            "friction_assessed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Tier 1: Uncertainty Posture Matrix (emotional response to unknown)
        sa.Column(
            "uncertainty_threat_lens",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=sees opportunity, 1=sees threat",
        ),
        sa.Column(
            "uncertainty_control_need",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=comfortable with flow, 1=needs control",
        ),
        sa.Column(
            "uncertainty_exploration_drive",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=cautious/known, 1=explorer/unknown",
        ),
        sa.Column(
            "uncertainty_assessed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Tier 2 unlock tracking
        sa.Column(
            "tier2_unlocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "tier2_unlocked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_meetings_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        # Tier 2: Leverage Instinct Index (natural power creation style)
        sa.Column(
            "leverage_structural",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Preference for systems/processes",
        ),
        sa.Column(
            "leverage_informational",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Preference for data/research",
        ),
        sa.Column(
            "leverage_relational",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Preference for people/networks",
        ),
        sa.Column(
            "leverage_temporal",
            sa.Numeric(3, 2),
            nullable=True,
            comment="Preference for timing/patience",
        ),
        sa.Column(
            "leverage_assessed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Tier 2: Value Tension Scan (competing priorities)
        # -1 to +1 scale: -1 = first value, +1 = second value
        sa.Column(
            "tension_autonomy_security",
            sa.Numeric(3, 2),
            nullable=True,
            comment="-1=autonomy, +1=security",
        ),
        sa.Column(
            "tension_mastery_speed",
            sa.Numeric(3, 2),
            nullable=True,
            comment="-1=mastery, +1=speed",
        ),
        sa.Column(
            "tension_growth_stability",
            sa.Numeric(3, 2),
            nullable=True,
            comment="-1=growth, +1=stability",
        ),
        sa.Column(
            "tension_assessed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Tier 2: Strategic Time Bias
        sa.Column(
            "time_bias_score",
            sa.Numeric(3, 2),
            nullable=True,
            comment="0=short-term optimizer, 1=long-term hoarder",
        ),
        sa.Column(
            "time_bias_assessed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Behavioral observations (passive tracking over time)
        sa.Column(
            "behavioral_observations",
            JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Passive metrics: decision_speed, clarification_skip_rate, etc.",
        ),
        # Computed insights
        sa.Column(
            "primary_blindspots",
            JSONB,
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment="Array of identified blindspot labels",
        ),
        sa.Column(
            "cognitive_style_summary",
            sa.Text(),
            nullable=True,
            comment="AI-generated one-liner describing cognitive style",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Index for user lookup
    op.create_index(
        "idx_user_cognition_user_id",
        "user_cognition",
        ["user_id"],
    )

    # Enable RLS
    op.execute("ALTER TABLE user_cognition ENABLE ROW LEVEL SECURITY")

    # RLS policy for user's own data
    op.execute("""
        CREATE POLICY user_cognition_own_data ON user_cognition
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
        WITH CHECK (user_id = current_setting('app.current_user_id', true))
    """)


def downgrade() -> None:
    """Drop user_cognition table."""
    op.execute("DROP POLICY IF EXISTS user_cognition_own_data ON user_cognition")
    op.drop_index("idx_user_cognition_user_id", table_name="user_cognition")
    op.drop_table("user_cognition")
