"""Add peer benchmarking tables.

Enables anonymous comparison of user metrics against industry peers.
- peer_benchmark_consent: tracks user opt-in/opt-out for data sharing
- peer_benchmark_aggregates: cached industry-level percentile data

Revision ID: zf_add_peer_benchmarks
Revises: ze_add_seo_article_events
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zf_add_peer_benchmarks"
down_revision: str | Sequence[str] | None = "ze_add_seo_article_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create peer benchmarking tables."""
    # Consent tracking table
    op.create_table(
        "peer_benchmark_consent",
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
        "idx_peer_benchmark_consent_user",
        "peer_benchmark_consent",
        ["user_id"],
        unique=True,
    )

    # Aggregated industry metrics table
    op.create_table(
        "peer_benchmark_aggregates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("industry", sa.String(length=100), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("p10", sa.Float(), nullable=True),
        sa.Column("p25", sa.Float(), nullable=True),
        sa.Column("p50", sa.Float(), nullable=True),
        sa.Column("p75", sa.Float(), nullable=True),
        sa.Column("p90", sa.Float(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Unique constraint and index for fast lookups
    op.create_index(
        "idx_peer_benchmark_aggregates_lookup",
        "peer_benchmark_aggregates",
        ["industry", "metric_name"],
        unique=True,
    )


def downgrade() -> None:
    """Drop peer benchmarking tables."""
    op.drop_index("idx_peer_benchmark_aggregates_lookup", table_name="peer_benchmark_aggregates")
    op.drop_table("peer_benchmark_aggregates")
    op.drop_index("idx_peer_benchmark_consent_user", table_name="peer_benchmark_consent")
    op.drop_table("peer_benchmark_consent")
