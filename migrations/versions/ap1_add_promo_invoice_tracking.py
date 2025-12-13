"""Add promo_invoice_applications table for tracking promo discounts on Stripe invoices.

Revision ID: ap1_add_promo_invoice_tracking
Revises: ao2_add_stripe_events
Create Date: 2025-12-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ap1_add_promo_invoice_tracking"
down_revision: str | None = "ao2_add_stripe_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create promo_invoice_applications table."""
    op.create_table(
        "promo_invoice_applications",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Primary key",
        ),
        sa.Column(
            "user_promotion_id",
            sa.String(36),
            nullable=False,
            comment="FK to user_promotions",
        ),
        sa.Column(
            "stripe_invoice_id",
            sa.String(255),
            nullable=False,
            comment="Stripe invoice ID (in_...)",
        ),
        sa.Column(
            "stripe_invoice_item_id",
            sa.String(255),
            nullable=False,
            comment="Stripe invoice item ID (ii_...)",
        ),
        sa.Column(
            "discount_amount_cents",
            sa.Integer(),
            nullable=False,
            comment="Discount amount in cents (positive value)",
        ),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_promotion_id"],
            ["user_promotions.id"],
            name="fk_promo_invoice_user_promo",
            ondelete="CASCADE",
        ),
    )
    # Index for looking up applications by invoice
    op.create_index(
        "ix_promo_invoice_stripe_invoice_id",
        "promo_invoice_applications",
        ["stripe_invoice_id"],
    )
    # Index for looking up applications by user_promotion
    op.create_index(
        "ix_promo_invoice_user_promotion_id",
        "promo_invoice_applications",
        ["user_promotion_id"],
    )
    # Unique constraint to prevent double application to same invoice
    op.create_index(
        "ix_promo_invoice_unique_application",
        "promo_invoice_applications",
        ["user_promotion_id", "stripe_invoice_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop promo_invoice_applications table."""
    op.drop_index("ix_promo_invoice_unique_application", table_name="promo_invoice_applications")
    op.drop_index("ix_promo_invoice_user_promotion_id", table_name="promo_invoice_applications")
    op.drop_index("ix_promo_invoice_stripe_invoice_id", table_name="promo_invoice_applications")
    op.drop_table("promo_invoice_applications")
