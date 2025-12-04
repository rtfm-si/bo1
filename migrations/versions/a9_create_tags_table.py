"""Create tags and action_tags tables for user-generated tagging.

Revision ID: a9_create_tags_table
Revises: a8_add_replanning_fields
Create Date: 2025-12-04

Adds user-generated tags system:
- tags: User-created tags with colors
- action_tags: Junction table linking actions to tags
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a9_create_tags_table"
down_revision = "a8_add_replanning_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tags and action_tags tables."""
    # Create tags table
    op.create_table(
        "tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(7), server_default="#6366F1", nullable=False),  # hex color
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )
    op.create_index("idx_tags_user", "tags", ["user_id"])
    op.create_index("idx_tags_name", "tags", ["name"])

    # Create action_tags junction table
    op.create_table(
        "action_tags",
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("action_id", "tag_id"),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_action_tags_action", "action_tags", ["action_id"])
    op.create_index("idx_action_tags_tag", "action_tags", ["tag_id"])


def downgrade() -> None:
    """Drop tags and action_tags tables."""
    # Drop action_tags table
    op.drop_index("idx_action_tags_tag", table_name="action_tags")
    op.drop_index("idx_action_tags_action", table_name="action_tags")
    op.drop_table("action_tags")

    # Drop tags table
    op.drop_index("idx_tags_name", table_name="tags")
    op.drop_index("idx_tags_user", table_name="tags")
    op.drop_table("tags")
