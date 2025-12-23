"""Add meeting_templates table for decision delivery templates.

Creates table to store predefined meeting templates that help users
start meetings faster with pre-populated problem statements, context hints,
and suggested personas.

Revision ID: z21_add_meeting_templates
Revises: z20_add_file_quarantine
Create Date: 2025-12-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z21_add_meeting_templates"
down_revision: str | Sequence[str] | None = "z20_add_file_quarantine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create meeting_templates table and seed built-in templates."""
    op.create_table(
        "meeting_templates",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, comment="Display name for the template"),
        sa.Column(
            "slug", sa.String(50), nullable=False, unique=True, comment="URL-friendly identifier"
        ),
        sa.Column(
            "description", sa.String(500), nullable=False, comment="Short description for gallery"
        ),
        sa.Column(
            "category",
            sa.String(50),
            nullable=False,
            comment="Template category (strategy, pricing, etc.)",
        ),
        sa.Column(
            "problem_statement_template",
            sa.Text(),
            nullable=False,
            comment="Pre-filled problem statement",
        ),
        sa.Column(
            "context_hints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Suggested context fields to fill",
        ),
        sa.Column(
            "suggested_persona_traits",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Traits for persona generation hints",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft delete flag",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True for system templates, false for admin-created",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
            comment="Template version for update tracking",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes
    op.create_index("idx_meeting_templates_slug", "meeting_templates", ["slug"], unique=True)
    op.create_index("idx_meeting_templates_category", "meeting_templates", ["category"])
    op.create_index("idx_meeting_templates_active", "meeting_templates", ["is_active"])

    # Table comment
    op.execute(
        "COMMENT ON TABLE meeting_templates IS "
        "'Predefined meeting templates for common decision scenarios. "
        "Helps users start meetings with pre-populated problem statements and context.'"
    )

    # Add template_id column to sessions table for tracking template usage
    op.add_column(
        "sessions",
        sa.Column(
            "template_id", sa.UUID(), nullable=True, comment="Template used to create this session"
        ),
    )
    op.create_foreign_key(
        "fk_sessions_template_id",
        "sessions",
        "meeting_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_sessions_template_id", "sessions", ["template_id"])

    # Seed built-in templates
    op.execute("""
        INSERT INTO meeting_templates (name, slug, description, category, problem_statement_template, context_hints, suggested_persona_traits, is_builtin)
        VALUES
        (
            'Product Launch',
            'launch',
            'Plan and execute a successful product or feature launch with go-to-market strategy.',
            'strategy',
            'Should we launch [product/feature name] in [target market/segment]? Consider timing, positioning, and resource allocation.',
            '["product_name", "target_market", "launch_timeline", "budget", "competitors", "unique_value_proposition"]'::jsonb,
            '["analytical", "risk_averse", "market_focused", "customer_centric"]'::jsonb,
            true
        ),
        (
            'Pricing Changes',
            'pricing_changes',
            'Evaluate pricing strategy changes including increases, new tiers, or bundling options.',
            'pricing',
            'Should we change our pricing from [current pricing] to [proposed pricing]? Consider customer impact, revenue goals, and competitive positioning.',
            '["current_pricing", "proposed_pricing", "customer_segments", "competitor_pricing", "cost_structure", "churn_risk"]'::jsonb,
            '["analytical", "data_driven", "customer_centric", "revenue_focused"]'::jsonb,
            true
        ),
        (
            'Onboarding Revamp',
            'onboarding_revamp',
            'Redesign user onboarding to improve activation, reduce time-to-value, and decrease churn.',
            'product',
            'How should we redesign our onboarding experience to improve [key metric]? Consider user personas, key aha moments, and resource constraints.',
            '["current_activation_rate", "target_activation_rate", "user_personas", "key_aha_moments", "onboarding_steps", "drop_off_points"]'::jsonb,
            '["user_experience_focused", "data_driven", "empathetic", "growth_minded"]'::jsonb,
            true
        ),
        (
            'Outreach Sprint',
            'outreach_sprint',
            'Plan a focused sales or marketing outreach campaign with clear targets and messaging.',
            'growth',
            'How should we approach our outreach to [target audience] to achieve [goal]? Consider messaging, channels, and success metrics.',
            '["target_audience", "campaign_goal", "available_channels", "budget", "timeline", "success_metrics"]'::jsonb,
            '["sales_focused", "creative", "data_driven", "customer_centric"]'::jsonb,
            true
        )
    """)


def downgrade() -> None:
    """Drop meeting_templates table and sessions.template_id column."""
    # Drop sessions.template_id
    op.drop_index("idx_sessions_template_id", table_name="sessions")
    op.drop_constraint("fk_sessions_template_id", "sessions", type_="foreignkey")
    op.drop_column("sessions", "template_id")

    # Drop meeting_templates table
    op.drop_index("idx_meeting_templates_active", table_name="meeting_templates")
    op.drop_index("idx_meeting_templates_category", table_name="meeting_templates")
    op.drop_index("idx_meeting_templates_slug", table_name="meeting_templates")
    op.drop_table("meeting_templates")
