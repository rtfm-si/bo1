"""Add mentor_conversations and mentor_messages tables.

Creates PostgreSQL storage for mentor chat sessions to persist beyond Redis TTL.
Enables conversation history resume and GDPR data export.

Revision ID: z24_add_mentor_conversations
Revises: z23_add_strategic_objectives
Create Date: 2025-12-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "z24_add_mentor_conversations"
down_revision: str | Sequence[str] | None = "z23_add_strategic_objectives"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create mentor_conversations and mentor_messages tables with RLS."""
    # Create mentor_conversations table
    op.create_table(
        "mentor_conversations",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "persona",
            sa.String(50),
            nullable=False,
            server_default="general",
            comment="Mentor persona: general, action_coach, data_analyst",
        ),
        sa.Column(
            "label",
            sa.String(255),
            nullable=True,
            comment="Auto-generated or user-provided conversation label",
        ),
        sa.Column(
            "context_sources",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
            comment="Context sources used in this conversation",
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
            name="fk_mentor_conversations_user_id",
            ondelete="CASCADE",
        ),
    )

    # Create mentor_messages table
    op.create_table(
        "mentor_messages",
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
            "persona",
            sa.String(50),
            nullable=True,
            comment="Persona used for this message (if assistant)",
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
            ["mentor_conversations.id"],
            name="fk_mentor_messages_conversation_id",
            ondelete="CASCADE",
        ),
    )

    # Indexes
    op.create_index(
        "idx_mentor_conversations_user_id",
        "mentor_conversations",
        ["user_id"],
    )
    op.create_index(
        "idx_mentor_conversations_user_updated",
        "mentor_conversations",
        ["user_id", sa.text("updated_at DESC")],
    )
    op.create_index(
        "idx_mentor_messages_conversation_id",
        "mentor_messages",
        ["conversation_id"],
    )

    # Table comments
    op.execute(
        "COMMENT ON TABLE mentor_conversations IS "
        "'Mentor chat conversations with multi-turn history. "
        "Redis caches hot conversations, PostgreSQL is source of truth.'"
    )
    op.execute(
        "COMMENT ON TABLE mentor_messages IS 'Individual messages within mentor conversations.'"
    )

    # Enable RLS
    op.execute("ALTER TABLE mentor_conversations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE mentor_messages ENABLE ROW LEVEL SECURITY")

    # RLS policy for mentor_conversations - user isolation
    op.execute("""
        CREATE POLICY mentor_conversations_user_isolation ON mentor_conversations
        FOR ALL
        USING (user_id = current_setting('app.current_user_id', true))
    """)

    # RLS policy for mentor_messages - user isolation via conversation
    op.execute("""
        CREATE POLICY mentor_messages_user_isolation ON mentor_messages
        FOR ALL
        USING (
            conversation_id IN (
                SELECT id FROM mentor_conversations
                WHERE user_id = current_setting('app.current_user_id', true)
            )
        )
    """)

    # Admin access policies
    op.execute("""
        CREATE POLICY mentor_conversations_admin_access ON mentor_conversations
        FOR SELECT
        USING (current_setting('app.is_admin', true)::boolean = true)
    """)
    op.execute("""
        CREATE POLICY mentor_messages_admin_access ON mentor_messages
        FOR SELECT
        USING (current_setting('app.is_admin', true)::boolean = true)
    """)


def downgrade() -> None:
    """Drop mentor_conversations and mentor_messages tables."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS mentor_messages_admin_access ON mentor_messages")
    op.execute("DROP POLICY IF EXISTS mentor_messages_user_isolation ON mentor_messages")
    op.execute("DROP POLICY IF EXISTS mentor_conversations_admin_access ON mentor_conversations")
    op.execute("DROP POLICY IF EXISTS mentor_conversations_user_isolation ON mentor_conversations")

    # Disable RLS
    op.execute("ALTER TABLE mentor_messages DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE mentor_conversations DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.drop_index("idx_mentor_messages_conversation_id", table_name="mentor_messages")
    op.drop_index("idx_mentor_conversations_user_updated", table_name="mentor_conversations")
    op.drop_index("idx_mentor_conversations_user_id", table_name="mentor_conversations")

    # Drop tables (order matters due to FK)
    op.drop_table("mentor_messages")
    op.drop_table("mentor_conversations")
