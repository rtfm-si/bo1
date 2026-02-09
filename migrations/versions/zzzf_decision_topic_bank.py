"""Create decision_topic_bank table.

Revision ID: zzzf_decision_topic_bank
Revises: zzze_admin_analytics
Create Date: 2026-02-08

Tables:
- decision_topic_bank: Banked decision topics from research
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "zzzf_decision_topic_bank"
down_revision: str | Sequence[str] | None = "zzze_admin_analytics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VALID_CATEGORIES = [
    "hiring",
    "pricing",
    "fundraising",
    "marketing",
    "strategy",
    "product",
    "operations",
    "growth",
]

VALID_STATUSES = ["banked", "used", "dismissed"]


def upgrade() -> None:
    op.create_table(
        "decision_topic_bank",
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("keywords", ARRAY(sa.Text()), server_default="{}"),
        sa.Column("seo_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("bo1_alignment", sa.Text(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="llm-generated"),
        sa.Column("status", sa.String(20), nullable=False, server_default="banked"),
        sa.Column("researched_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            f"status IN ({','.join(repr(s) for s in VALID_STATUSES)})", name="ck_topic_bank_status"
        ),
        sa.CheckConstraint("seo_score >= 0 AND seo_score <= 1", name="ck_topic_bank_seo_score"),
        sa.CheckConstraint(
            f"category IN ({','.join(repr(c) for c in VALID_CATEGORIES)})",
            name="ck_topic_bank_category",
        ),
    )

    op.create_index("ix_topic_bank_status", "decision_topic_bank", ["status"])
    op.create_index("ix_topic_bank_category", "decision_topic_bank", ["category"])
    op.create_index("ix_topic_bank_seo_score", "decision_topic_bank", [sa.text("seo_score DESC")])


def downgrade() -> None:
    op.drop_index("ix_topic_bank_seo_score", table_name="decision_topic_bank")
    op.drop_index("ix_topic_bank_category", table_name="decision_topic_bank")
    op.drop_index("ix_topic_bank_status", table_name="decision_topic_bank")
    op.drop_table("decision_topic_bank")
