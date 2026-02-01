"""Create published_decisions table.

Revision ID: zzy_published_decisions
Revises: zzx_account_linking
Create Date: 2025-02-01

Implements SEO decision library:
- published_decisions: Stores admin-curated decision pages from real meetings
- Includes session_id FK, SEO fields, founder context, FAQs
- Indexes for category, status, slug lookups
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "zzy_published_decisions"
down_revision: str | Sequence[str] | None = "zzx_account_linking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create published_decisions table."""
    op.create_table(
        "published_decisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("meta_description", sa.Text, nullable=True),
        sa.Column(
            "founder_context",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "expert_perspectives",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column("synthesis", sa.Text, nullable=True),
        sa.Column(
            "faqs",
            sa.dialects.postgresql.JSONB,
            nullable=True,
        ),
        sa.Column(
            "related_decision_ids",
            sa.dialects.postgresql.ARRAY(sa.String(length=36)),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        # Analytics
        sa.Column("view_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("click_through_count", sa.Integer, nullable=False, server_default="0"),
        # Check constraint for valid status
        sa.CheckConstraint(
            "status IN ('draft', 'published')",
            name="ck_published_decisions_status",
        ),
    )

    # Index on category for category listing pages
    op.create_index("ix_published_decisions_category", "published_decisions", ["category"])

    # Index on status for filtering published vs draft
    op.create_index("ix_published_decisions_status", "published_decisions", ["status"])

    # Index on published_at for ordering
    op.create_index("ix_published_decisions_published_at", "published_decisions", ["published_at"])

    # Composite index for public listing queries
    op.create_index(
        "ix_published_decisions_status_category",
        "published_decisions",
        ["status", "category"],
    )


def downgrade() -> None:
    """Remove published_decisions table."""
    op.drop_index("ix_published_decisions_status_category", table_name="published_decisions")
    op.drop_index("ix_published_decisions_published_at", table_name="published_decisions")
    op.drop_index("ix_published_decisions_status", table_name="published_decisions")
    op.drop_index("ix_published_decisions_category", table_name="published_decisions")
    op.drop_table("published_decisions")
