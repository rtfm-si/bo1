"""Add policy_type column to terms_consents for multi-policy consent tracking.

Supports T&C, GDPR, and Privacy Policy consents independently.

Revision ID: tc3_add_policy_type_consent
Revises: tc2_seed_initial_terms
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "tc3_add_policy_type_consent"
down_revision: str | Sequence[str] | None = "z25_expand_benchmark_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add policy_type column with default 'tc' and composite index."""
    # Add policy_type column with default 'tc' for existing records
    op.add_column(
        "terms_consents",
        sa.Column(
            "policy_type",
            sa.String(20),
            nullable=False,
            server_default="tc",
        ),
    )

    # Add composite index for user + policy lookups
    op.create_index(
        "ix_terms_consents_user_policy",
        "terms_consents",
        ["user_id", "policy_type"],
    )


def downgrade() -> None:
    """Remove policy_type column."""
    op.drop_index("ix_terms_consents_user_policy", table_name="terms_consents")
    op.drop_column("terms_consents", "policy_type")
