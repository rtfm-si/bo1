"""Create promotions and user_promotions tables.

This migration adds:
- promotions table: stores promo codes with type, value, limits, expiry
- user_promotions table: tracks which users have applied which promos
- Indexes for fast lookup by code and user
- Seed data for common promotion templates

Revision ID: ai1_create_promotions
Revises: af2_change_retention_default
Create Date: 2025-12-13

"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ai1_create_promotions"
down_revision: str | Sequence[str] | None = "af2_change_retention_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create promotions schema and seed data."""
    # Create promotions table
    op.create_table(
        "promotions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False, unique=True),
        sa.Column(
            "type",
            sa.String(length=30),
            nullable=False,
        ),  # goodwill_credits, percentage_discount, flat_discount, extra_deliberations
        sa.Column("value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("max_uses", sa.Integer, nullable=True),  # NULL = unlimited
        sa.Column("uses_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        # Check constraint for valid promotion types
        sa.CheckConstraint(
            "type IN ('goodwill_credits', 'percentage_discount', 'flat_discount', 'extra_deliberations')",
            name="ck_promotions_type",
        ),
        # Check constraint for positive value
        sa.CheckConstraint("value > 0", name="ck_promotions_value_positive"),
        # Check constraint for uses_count <= max_uses (when max_uses is set)
        sa.CheckConstraint(
            "max_uses IS NULL OR uses_count <= max_uses",
            name="ck_promotions_uses_within_max",
        ),
    )

    # Index on code for fast lookup
    op.create_index("ix_promotions_code", "promotions", ["code"], unique=True)

    # Index on is_active for filtering active promos
    op.create_index("ix_promotions_is_active", "promotions", ["is_active"])

    # Create user_promotions table
    op.create_table(
        "user_promotions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "promotion_id",
            sa.String(length=36),
            sa.ForeignKey("promotions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deliberations_remaining", sa.Integer, nullable=True),  # For credit-type promos
        sa.Column(
            "discount_applied", sa.Numeric(precision=10, scale=2), nullable=True
        ),  # For discount-type promos
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="'active'",
        ),  # active, exhausted, expired
        # Check constraint for valid status
        sa.CheckConstraint(
            "status IN ('active', 'exhausted', 'expired')",
            name="ck_user_promotions_status",
        ),
    )

    # Index on user_id for fast lookup of user's promos
    op.create_index("ix_user_promotions_user_id", "user_promotions", ["user_id"])

    # Index on status for filtering active promos
    op.create_index("ix_user_promotions_status", "user_promotions", ["status"])

    # Unique constraint: user can only apply each promo once
    op.create_unique_constraint(
        "uq_user_promotions_user_promotion",
        "user_promotions",
        ["user_id", "promotion_id"],
    )

    # Seed common promotion templates
    now = datetime.now(UTC).isoformat()
    promotions_data = [
        {
            "id": str(uuid4()),
            "code": "WELCOME10",
            "type": "percentage_discount",
            "value": 10.00,
            "max_uses": 1000,
            "uses_count": 0,
            "expires_at": None,
            "created_at": now,
            "is_active": True,
        },
        {
            "id": str(uuid4()),
            "code": "GOODWILL5",
            "type": "extra_deliberations",
            "value": 5.00,
            "max_uses": None,  # Unlimited
            "uses_count": 0,
            "expires_at": None,
            "created_at": now,
            "is_active": True,
        },
        {
            "id": str(uuid4()),
            "code": "LAUNCH2025",
            "type": "percentage_discount",
            "value": 25.00,
            "max_uses": 500,
            "uses_count": 0,
            "expires_at": "2025-03-31T23:59:59+00:00",
            "created_at": now,
            "is_active": True,
        },
    ]

    op.bulk_insert(
        sa.table(
            "promotions",
            sa.column("id", sa.String),
            sa.column("code", sa.String),
            sa.column("type", sa.String),
            sa.column("value", sa.Numeric),
            sa.column("max_uses", sa.Integer),
            sa.column("uses_count", sa.Integer),
            sa.column("expires_at", sa.DateTime),
            sa.column("created_at", sa.DateTime),
            sa.column("is_active", sa.Boolean),
        ),
        promotions_data,
    )


def downgrade() -> None:
    """Remove promotions schema."""
    # Drop user_promotions table
    op.drop_constraint("uq_user_promotions_user_promotion", "user_promotions", type_="unique")
    op.drop_index("ix_user_promotions_status", table_name="user_promotions")
    op.drop_index("ix_user_promotions_user_id", table_name="user_promotions")
    op.drop_table("user_promotions")

    # Drop promotions table
    op.drop_index("ix_promotions_is_active", table_name="promotions")
    op.drop_index("ix_promotions_code", table_name="promotions")
    op.drop_table("promotions")
