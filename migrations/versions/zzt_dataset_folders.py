"""Add dataset folders for hierarchical organization.

Creates:
- dataset_folders table: id, user_id, name, description, color, icon, parent_folder_id, timestamps
- dataset_folder_tags table: folder_id, tag_name
- dataset_folder_memberships junction: folder_id, dataset_id

Revision ID: zzt_dataset_folders
Revises: zzs_last_analysis_id
Create Date: 2026-01-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "zzt_dataset_folders"
down_revision: str | Sequence[str] | None = "zzs_last_analysis_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset folder tables."""
    # Create dataset_folders table
    op.create_table(
        "dataset_folders",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("color", sa.String(7), nullable=True),  # hex color e.g. #FF5733
        sa.Column("icon", sa.String(50), nullable=True),  # icon name
        sa.Column("parent_folder_id", UUID, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_folder_id"],
            ["dataset_folders.id"],
            name="fk_dataset_folders_parent",
            ondelete="CASCADE",
        ),
    )

    # Indexes for dataset_folders
    op.create_index(
        "idx_dataset_folders_user_id",
        "dataset_folders",
        ["user_id"],
    )
    op.create_index(
        "idx_dataset_folders_parent",
        "dataset_folders",
        ["parent_folder_id"],
        postgresql_where=sa.text("parent_folder_id IS NOT NULL"),
    )

    # Create dataset_folder_tags table
    op.create_table(
        "dataset_folder_tags",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("folder_id", UUID, nullable=False),
        sa.Column("tag_name", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["dataset_folders.id"],
            name="fk_dataset_folder_tags_folder",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("folder_id", "tag_name", name="uq_dataset_folder_tags"),
    )

    op.create_index(
        "idx_dataset_folder_tags_folder_id",
        "dataset_folder_tags",
        ["folder_id"],
    )
    op.create_index(
        "idx_dataset_folder_tags_tag_name",
        "dataset_folder_tags",
        ["tag_name"],
    )

    # Create dataset_folder_memberships junction table
    op.create_table(
        "dataset_folder_memberships",
        sa.Column("folder_id", UUID, nullable=False),
        sa.Column("dataset_id", UUID, nullable=False),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("folder_id", "dataset_id", name="pk_dataset_folder_memberships"),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["dataset_folders.id"],
            name="fk_memberships_folder",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_memberships_dataset",
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "idx_dataset_folder_memberships_dataset",
        "dataset_folder_memberships",
        ["dataset_id"],
    )


def downgrade() -> None:
    """Drop dataset folder tables."""
    op.drop_table("dataset_folder_memberships")
    op.drop_table("dataset_folder_tags")
    op.drop_index("idx_dataset_folders_parent", table_name="dataset_folders")
    op.drop_index("idx_dataset_folders_user_id", table_name="dataset_folders")
    op.drop_table("dataset_folders")
