"""Add marketing_assets table for collateral bank.

Revision ID: zl_add_marketing_assets
Revises: zk_add_seo_autopilot_config
Create Date: 2025-12-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "zl_add_marketing_assets"
down_revision: str | Sequence[str] | None = "zk_add_seo_autopilot_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create marketing_assets table.

    Stores marketing collateral (images, animations, concepts, templates) for
    AI content generation. Assets are stored in DO Spaces with CDN URLs.

    Fields:
    - id: Primary key
    - user_id: Owner
    - workspace_id: Optional workspace association
    - filename: Original filename
    - storage_key: Key in DO Spaces
    - cdn_url: Full CDN URL for embedding
    - asset_type: image, animation, concept, template
    - title: User-friendly title
    - description: Optional description
    - tags: Text array for tag-based search
    - metadata: JSONB for additional info (dimensions, duration, etc.)
    - file_size: Size in bytes
    - mime_type: MIME type
    - created_at, updated_at: Timestamps
    """
    op.create_table(
        "marketing_assets",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("workspace_id", sa.String(255), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("cdn_url", sa.String(1024), nullable=False),
        sa.Column(
            "asset_type",
            sa.String(50),
            nullable=False,
            comment="image, animation, concept, template",
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
            comment="Tags for search and suggestion matching",
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=True,
            comment="Additional metadata (dimensions, duration, etc.)",
        ),
        sa.Column("file_size", sa.Integer(), nullable=False, comment="File size in bytes"),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index on tags for fast GIN array search
    op.create_index(
        "ix_marketing_assets_tags",
        "marketing_assets",
        ["tags"],
        postgresql_using="gin",
    )

    # Index on asset_type for filtering
    op.create_index(
        "ix_marketing_assets_asset_type",
        "marketing_assets",
        ["asset_type"],
    )

    # Index on user_id for ownership queries
    op.create_index(
        "ix_marketing_assets_user_id",
        "marketing_assets",
        ["user_id"],
    )

    # Compound index for user + type filtering
    op.create_index(
        "ix_marketing_assets_user_type",
        "marketing_assets",
        ["user_id", "asset_type"],
    )


def downgrade() -> None:
    """Drop marketing_assets table."""
    op.drop_index("ix_marketing_assets_user_type", table_name="marketing_assets")
    op.drop_index("ix_marketing_assets_user_id", table_name="marketing_assets")
    op.drop_index("ix_marketing_assets_asset_type", table_name="marketing_assets")
    op.drop_index("ix_marketing_assets_tags", table_name="marketing_assets")
    op.drop_table("marketing_assets")
