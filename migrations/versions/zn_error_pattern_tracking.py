"""Add unclassified error pattern and match_count tracking.

Revision ID: zn_error_pattern_tracking
Revises: zm_add_fair_usage_tracking
Create Date: 2025-12-29

Adds:
- match_count column to error_patterns for tracking pattern matches
- unclassified_error catch-all pattern for errors that don't match existing patterns
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "zn_error_pattern_tracking"
down_revision = "zm_add_fair_usage_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add match_count column and unclassified_error pattern."""
    # Add match_count column to error_patterns
    op.add_column(
        "error_patterns",
        sa.Column(
            "match_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
            comment="Total number of times this pattern has matched",
        ),
    )

    # Add last_match_at column for tracking when pattern last matched
    op.add_column(
        "error_patterns",
        sa.Column(
            "last_match_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last pattern match",
        ),
    )

    # Insert catch-all unclassified_error pattern
    conn = op.get_bind()
    import json

    # Check if pattern already exists
    result = conn.execute(
        sa.text("SELECT id FROM error_patterns WHERE pattern_name = 'unclassified_error'")
    )
    if result.fetchone() is None:
        # Insert the catch-all pattern
        result = conn.execute(
            sa.text("""
            INSERT INTO error_patterns (
                pattern_name, pattern_regex, error_type, severity,
                description, threshold_count, threshold_window_minutes,
                cooldown_minutes
            ) VALUES (
                'unclassified_error',
                '.*',
                'unclassified',
                'low',
                'Catch-all pattern for errors that do not match any specific pattern. Used for visibility and tracking.',
                10,
                5,
                10
            )
            RETURNING id
            """)
        )
        pattern_id = result.fetchone()[0]

        # Add an alert_only fix for the catch-all pattern (no automated remediation)
        conn.execute(
            sa.text("""
            INSERT INTO error_fixes (error_pattern_id, fix_type, fix_config, priority)
            VALUES (:pattern_id, 'alert_only', :fix_config, 1)
            """),
            {
                "pattern_id": pattern_id,
                "fix_config": json.dumps(
                    {
                        "severity": "low",
                        "escalate": False,
                        "message": "Unclassified error detected - review for potential new pattern",
                    }
                ),
            },
        )


def downgrade() -> None:
    """Remove match_count column and unclassified_error pattern."""
    # Remove the pattern and its fixes
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM error_patterns WHERE pattern_name = 'unclassified_error'"))

    # Remove columns
    op.drop_column("error_patterns", "last_match_at")
    op.drop_column("error_patterns", "match_count")
