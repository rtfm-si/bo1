"""Add research sharing tables.

Enables cross-user research sharing with consent management.
- research_sharing_consent: tracks user opt-in/opt-out for research contribution
- Add user_id and is_shareable to research_cache for filtering

Revision ID: zg_add_research_sharing
Revises: zf_add_peer_benchmarks
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zg_add_research_sharing"
down_revision: str | Sequence[str] | None = "zf_add_peer_benchmarks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create research sharing tables and columns."""
    # Consent tracking table
    op.create_table(
        "research_sharing_consent",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "consented_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Unique constraint: one active consent record per user
    op.create_index(
        "idx_research_sharing_consent_user",
        "research_sharing_consent",
        ["user_id"],
        unique=True,
    )

    # Add user_id column to research_cache (nullable - null = shared/anonymous)
    op.add_column(
        "research_cache",
        sa.Column("user_id", sa.String(length=255), nullable=True),
    )

    # Add is_shareable column to research_cache (default true)
    op.add_column(
        "research_cache",
        sa.Column(
            "is_shareable",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    # Index for shared research lookup (industry + is_shareable)
    op.create_index(
        "idx_research_cache_shared_lookup",
        "research_cache",
        ["industry", "is_shareable"],
    )


def downgrade() -> None:
    """Drop research sharing tables and columns."""
    op.drop_index("idx_research_cache_shared_lookup", table_name="research_cache")
    op.drop_column("research_cache", "is_shareable")
    op.drop_column("research_cache", "user_id")
    op.drop_index("idx_research_sharing_consent_user", table_name="research_sharing_consent")
    op.drop_table("research_sharing_consent")
