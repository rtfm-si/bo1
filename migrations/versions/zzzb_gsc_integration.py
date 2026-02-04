"""Add Google Search Console integration tables.

Revision ID: zzzb_gsc_integration
Revises: zzza_decision_seo_fields
Create Date: 2025-02-04

Adds:
- gsc_connection: Admin-level OAuth tokens for GSC
- gsc_snapshots: Per-decision search analytics time series
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "zzzb_gsc_integration"
down_revision: str | Sequence[str] | None = "zzza_decision_seo_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create GSC integration tables."""
    # gsc_connection: Admin-level OAuth tokens (single row)
    op.create_table(
        "gsc_connection",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("access_token", sa.Text, nullable=False),  # Encrypted
        sa.Column("refresh_token", sa.Text, nullable=True),  # Encrypted
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("site_url", sa.String(255), nullable=False),  # Selected property
        sa.Column(
            "connected_by",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # gsc_snapshots: Per-decision search analytics
    op.create_table(
        "gsc_snapshots",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "decision_id",
            sa.String(36),
            sa.ForeignKey("published_decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_url", sa.String(500), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("impressions", sa.Integer, server_default="0"),
        sa.Column("clicks", sa.Integer, server_default="0"),
        sa.Column("ctr", sa.Float, nullable=True),
        sa.Column("position", sa.Float, nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Unique constraint: one row per decision per date
        sa.UniqueConstraint("decision_id", "date", name="uq_gsc_snapshots_decision_date"),
    )

    # Index for efficient decision+date lookups
    op.create_index(
        "ix_gsc_snapshots_decision_date",
        "gsc_snapshots",
        ["decision_id", "date"],
    )


def downgrade() -> None:
    """Remove GSC integration tables."""
    op.drop_index("ix_gsc_snapshots_decision_date", "gsc_snapshots")
    op.drop_table("gsc_snapshots")
    op.drop_table("gsc_connection")
