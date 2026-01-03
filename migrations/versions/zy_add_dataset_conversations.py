"""Add dataset_conversations and dataset_messages tables.

Creates PostgreSQL storage for dataset Q&A conversations to persist beyond Redis TTL.
Enables conversation history resume and GDPR data export.
Mirrors mentor_conversations pattern (z24).

Revision ID: zy_add_dataset_conversations
Revises: zx_add_password_upgrade_needed
Create Date: 2026-01-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "zy_add_dataset_conversations"
down_revision: str | Sequence[str] | None = "zx_add_password_upgrade_needed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset_conversations and dataset_messages tables with RLS."""
    # Create dataset_conversations table
    op.create_table(
        "dataset_conversations",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("dataset_id", sa.UUID(), nullable=False),
        sa.Column(
            "label",
            sa.String(255),
            nullable=True,
            comment="Auto-generated or user-provided conversation label",
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_dataset_conversations_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.id"],
            name="fk_dataset_conversations_dataset_id",
            ondelete="CASCADE",
        ),
    )

    # Create dataset_messages table
    op.create_table(
        "dataset_messages",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            comment="Message role: user or assistant",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "query_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="SQL query specification (columns, filters, etc.)",
        ),
        sa.Column(
            "chart_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Chart specification (type, axes, etc.)",
        ),
        sa.Column(
            "query_result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Query result summary (truncated for storage)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["dataset_conversations.id"],
            name="fk_dataset_messages_conversation_id",
            ondelete="CASCADE",
        ),
    )

    # Indexes
    op.create_index(
        "idx_dataset_conversations_user_id",
        "dataset_conversations",
        ["user_id"],
    )
    op.create_index(
        "idx_dataset_conversations_dataset_id",
        "dataset_conversations",
        ["dataset_id"],
    )
    op.create_index(
        "idx_dataset_conversations_user_updated",
        "dataset_conversations",
        ["user_id", sa.text("updated_at DESC")],
    )
    op.create_index(
        "idx_dataset_messages_conversation_id",
        "dataset_messages",
        ["conversation_id"],
    )

    # Table comments
    op.execute(
        "COMMENT ON TABLE dataset_conversations IS "
        "'Dataset Q&A conversations with multi-turn history. "
        "Redis caches hot conversations, PostgreSQL is source of truth.'"
    )
    op.execute(
        "COMMENT ON TABLE dataset_messages IS "
        "'Individual messages within dataset Q&A conversations.'"
    )

    # Enable RLS
    op.execute("ALTER TABLE dataset_conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dataset_messages ENABLE ROW LEVEL SECURITY")

    # RLS policy for dataset_conversations - user isolation
    op.execute("""
        CREATE POLICY dataset_conversations_user_isolation ON dataset_conversations
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
    """)

    # RLS policy for dataset_messages - user isolation via conversation
    op.execute("""
        CREATE POLICY dataset_messages_user_isolation ON dataset_messages
        FOR ALL
        USING (
            conversation_id IN (
                SELECT id FROM dataset_conversations
                WHERE user_id = current_setting('app.current_user_id', true)
            )
        )
    """)

    # Admin access policies
    op.execute("""
        CREATE POLICY dataset_conversations_admin_access ON dataset_conversations
        FOR SELECT
        USING (current_setting('app.is_admin', true)::boolean = true)
    """)
    op.execute("""
        CREATE POLICY dataset_messages_admin_access ON dataset_messages
        FOR SELECT
        USING (current_setting('app.is_admin', true)::boolean = true)
    """)


def downgrade() -> None:
    """Drop dataset_conversations and dataset_messages tables."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS dataset_messages_admin_access ON dataset_messages")
    op.execute("DROP POLICY IF EXISTS dataset_messages_user_isolation ON dataset_messages")
    op.execute("DROP POLICY IF EXISTS dataset_conversations_admin_access ON dataset_conversations")
    op.execute(
        "DROP POLICY IF EXISTS dataset_conversations_user_isolation ON dataset_conversations"
    )

    # Disable RLS
    op.execute("ALTER TABLE dataset_messages DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE dataset_conversations DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.drop_index("idx_dataset_messages_conversation_id", table_name="dataset_messages")
    op.drop_index("idx_dataset_conversations_user_updated", table_name="dataset_conversations")
    op.drop_index("idx_dataset_conversations_dataset_id", table_name="dataset_conversations")
    op.drop_index("idx_dataset_conversations_user_id", table_name="dataset_conversations")

    # Drop tables (order matters due to FK)
    op.drop_table("dataset_messages")
    op.drop_table("dataset_conversations")
