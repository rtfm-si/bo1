"""Create admin analytics chat tables.

Revision ID: zzze_admin_analytics
Revises: zzzd_impersonation_index
Create Date: 2026-02-06

Tables:
- admin_analytics_conversations: Chat sessions
- admin_analytics_messages: Messages with steps/charts
- admin_saved_analyses: Saved analyses for re-running
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "zzze_admin_analytics"
down_revision: str | Sequence[str] | None = "zzzd_impersonation_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create admin analytics tables."""
    # 1. Conversations
    op.create_table(
        "admin_analytics_conversations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("admin_user_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("model_preference", sa.Text(), server_default="sonnet"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_analytics_conv_admin", "admin_analytics_conversations", ["admin_user_id"])
    op.create_index(
        "idx_analytics_conv_updated",
        "admin_analytics_conversations",
        ["updated_at"],
        postgresql_ops={"updated_at": "DESC"},
    )

    # 2. Messages
    op.create_table(
        "admin_analytics_messages",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.UUID(),
            sa.ForeignKey("admin_analytics_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("steps", JSONB),
        sa.Column("suggestions", sa.ARRAY(sa.Text())),
        sa.Column("llm_cost", sa.Numeric(10, 6), server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_analytics_msg_conv", "admin_analytics_messages", ["conversation_id"])

    # 3. Saved analyses
    op.create_table(
        "admin_saved_analyses",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("admin_user_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("original_question", sa.Text(), nullable=False),
        sa.Column("steps", JSONB, nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_result", JSONB),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("idx_saved_analyses_admin", "admin_saved_analyses", ["admin_user_id"])


def downgrade() -> None:
    """Drop admin analytics tables."""
    op.drop_table("admin_analytics_messages")
    op.drop_table("admin_saved_analyses")
    op.drop_table("admin_analytics_conversations")
