"""Add indexes for clarification-sourced metrics queries.

Revision ID: zzd_add_clarification_idx
Revises: zzc_add_totp_2fa_fields
Create Date: 2026-01-04
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "zzd_add_clarification_idx"
down_revision = "zzc_add_totp_2fa_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes for clarification metric queries."""
    # Index on source for filtering clarification-sourced metrics
    op.create_index(
        "idx_business_metrics_source",
        "business_metrics",
        ["source"],
        postgresql_where="source = 'clarification'",
    )

    # Index on captured_at for time-range queries
    op.create_index(
        "idx_business_metrics_captured_at",
        "business_metrics",
        ["captured_at"],
    )


def downgrade() -> None:
    """Remove indexes."""
    op.drop_index("idx_business_metrics_captured_at", table_name="business_metrics")
    op.drop_index("idx_business_metrics_source", table_name="business_metrics")
