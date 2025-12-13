"""Create error patterns tables for AI ops self-healing.

Revision ID: ar1_create_error_patterns
Revises: aq1_add_workspace_billing
Create Date: 2025-12-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ar1_create_error_patterns"
down_revision = "aq1_add_workspace_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create error_patterns, error_fixes, and auto_remediation_log tables."""
    # Create error_patterns table
    op.create_table(
        "error_patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pattern_name", sa.String(100), nullable=False, unique=True),
        sa.Column("pattern_regex", sa.Text(), nullable=False),
        sa.Column(
            "error_type",
            sa.String(50),
            nullable=False,
            comment="Category: redis, postgres, llm, sse, memory, session",
        ),
        sa.Column(
            "severity",
            sa.String(20),
            nullable=False,
            server_default="medium",
            comment="low, medium, high, critical",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "threshold_count",
            sa.Integer(),
            server_default="3",
            nullable=False,
            comment="Errors in window before triggering remediation",
        ),
        sa.Column(
            "threshold_window_minutes",
            sa.Integer(),
            server_default="5",
            nullable=False,
            comment="Sliding window for threshold",
        ),
        sa.Column(
            "cooldown_minutes",
            sa.Integer(),
            server_default="5",
            nullable=False,
            comment="Min time between remediation attempts",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_error_patterns_error_type", "error_patterns", ["error_type"])
    op.create_index("ix_error_patterns_enabled", "error_patterns", ["enabled"])

    # Create error_fixes table
    op.create_table(
        "error_fixes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("error_pattern_id", sa.Integer(), nullable=False),
        sa.Column(
            "fix_type",
            sa.String(50),
            nullable=False,
            comment="restart_service, clear_cache, scale_pool, circuit_break, alert_only",
        ),
        sa.Column(
            "fix_config",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
            comment="Configuration for fix (service names, timeouts, etc.)",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            server_default="1",
            nullable=False,
            comment="Lower = higher priority; first match wins",
        ),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "success_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "failure_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["error_pattern_id"],
            ["error_patterns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_error_fixes_pattern_priority",
        "error_fixes",
        ["error_pattern_id", "priority"],
    )

    # Create auto_remediation_log table
    op.create_table(
        "auto_remediation_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("error_pattern_id", sa.Integer(), nullable=True),
        sa.Column("error_fix_id", sa.Integer(), nullable=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "outcome",
            sa.String(20),
            nullable=False,
            comment="success, failure, skipped, partial",
        ),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Error context, fix result, metrics",
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Fix execution time in milliseconds",
        ),
        sa.ForeignKeyConstraint(
            ["error_pattern_id"],
            ["error_patterns.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["error_fix_id"],
            ["error_fixes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auto_remediation_log_triggered_at",
        "auto_remediation_log",
        ["triggered_at"],
    )
    op.create_index(
        "ix_auto_remediation_log_pattern",
        "auto_remediation_log",
        ["error_pattern_id"],
    )
    op.create_index(
        "ix_auto_remediation_log_outcome",
        "auto_remediation_log",
        ["outcome"],
    )


def downgrade() -> None:
    """Drop error_patterns, error_fixes, and auto_remediation_log tables."""
    op.drop_table("auto_remediation_log")
    op.drop_table("error_fixes")
    op.drop_table("error_patterns")
