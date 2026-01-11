"""Add competitor intelligence columns for deep research.

Adds new JSONB columns to competitor_profiles for:
- product_updates: Product launches/updates timeline
- key_signals: Notable signals (Raised Series B, etc.)
- funding_rounds: Structured funding data
- intel_gathered_at: Timestamp for freshness tracking

Pro tier only feature for deeper competitor research.

Revision ID: zzu_competitor_intel
Revises: zzt_dataset_folders
Create Date: 2026-01-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "zzu_competitor_intel"
down_revision: str | Sequence[str] | None = "zzt_dataset_folders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add competitor intelligence columns."""
    # Product updates: [{title, date, description, source_url}]
    op.add_column(
        "competitor_profiles",
        sa.Column(
            "product_updates",
            JSONB,
            nullable=True,
            comment="Product launches/updates: [{title, date, description, source_url}]",
        ),
    )

    # Key signals: ["Raised Series B", "Launched AI feature"]
    op.add_column(
        "competitor_profiles",
        sa.Column(
            "key_signals",
            JSONB,
            nullable=True,
            comment="Notable signals: ['Raised Series B', 'Launched AI feature']",
        ),
    )

    # Funding rounds: [{round_type, amount, date, investors[]}]
    op.add_column(
        "competitor_profiles",
        sa.Column(
            "funding_rounds",
            JSONB,
            nullable=True,
            comment="Funding rounds: [{round_type, amount, date, investors[]}]",
        ),
    )

    # Intel gathered timestamp for freshness
    op.add_column(
        "competitor_profiles",
        sa.Column(
            "intel_gathered_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When deep intelligence was last gathered",
        ),
    )

    # Index on intel_gathered_at for freshness queries
    op.create_index(
        "idx_competitor_profiles_intel_gathered",
        "competitor_profiles",
        ["intel_gathered_at"],
    )


def downgrade() -> None:
    """Remove competitor intelligence columns."""
    op.drop_index("idx_competitor_profiles_intel_gathered", table_name="competitor_profiles")
    op.drop_column("competitor_profiles", "intel_gathered_at")
    op.drop_column("competitor_profiles", "funding_rounds")
    op.drop_column("competitor_profiles", "key_signals")
    op.drop_column("competitor_profiles", "product_updates")
