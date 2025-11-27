"""Add session_events and session_tasks tables.

Create session_events and session_tasks tables for persistent storage.
Enables long-term storage of session events and extracted tasks beyond Redis TTL.

Replaces SQL migration: 008_create_events_and_tasks_tables.sql

Revision ID: 622dbc22743e
Revises: 001_research_metrics
Create Date: 2025-11-27 09:59:19.814397

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "622dbc22743e"
down_revision: str | Sequence[str] | None = "001_research_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ============================================================================
    # 1. session_events: Store all deliberation events for historical replay
    # ============================================================================

    op.create_table(
        "session_events",
        sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "sequence", name="unique_session_sequence"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for fast event retrieval
    op.create_index("idx_session_events_session_id", "session_events", ["session_id"])
    op.create_index("idx_session_events_event_type", "session_events", ["event_type"])
    op.create_index(
        "idx_session_events_created_at",
        "session_events",
        ["created_at"],
        postgresql_using="btree",
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "idx_session_events_session_sequence", "session_events", ["session_id", "sequence"]
    )

    # GIN index for efficient JSONB queries
    op.create_index("idx_session_events_data", "session_events", ["data"], postgresql_using="gin")

    # Add comments
    op.execute("""
        COMMENT ON TABLE session_events IS 'Historical event log for all deliberation sessions (replaces Redis-only storage)';
        COMMENT ON COLUMN session_events.session_id IS 'Session identifier (matches sessions.id)';
        COMMENT ON COLUMN session_events.event_type IS 'Event type (e.g., contribution, synthesis_complete, persona_selected)';
        COMMENT ON COLUMN session_events.sequence IS 'Event sequence number within session (for ordering)';
        COMMENT ON COLUMN session_events.data IS 'Event payload as JSONB (flexible schema for different event types)';
        COMMENT ON COLUMN session_events.created_at IS 'When event occurred';
    """)

    # ============================================================================
    # 2. session_tasks: Store extracted tasks from synthesis
    # ============================================================================

    op.create_table(
        "session_tasks",
        sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("tasks", JSONB, nullable=False),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "extraction_confidence",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column("synthesis_sections_analyzed", sa.ARRAY(sa.Text()), server_default="{}"),
        sa.Column(
            "extracted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "extraction_confidence >= 0.0 AND extraction_confidence <= 1.0",
            name="check_extraction_confidence",
        ),
        sa.CheckConstraint("total_tasks >= 0", name="check_total_tasks"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for task retrieval
    op.create_index("idx_session_tasks_session_id", "session_tasks", ["session_id"])
    op.create_index(
        "idx_session_tasks_extracted_at",
        "session_tasks",
        ["extracted_at"],
        postgresql_using="btree",
        postgresql_ops={"extracted_at": "DESC"},
    )

    # GIN index for JSONB task searches
    op.create_index("idx_session_tasks_tasks", "session_tasks", ["tasks"], postgresql_using="gin")

    # Add comments
    op.execute("""
        COMMENT ON TABLE session_tasks IS 'Extracted actionable tasks from session synthesis (cached in Redis, persisted here)';
        COMMENT ON COLUMN session_tasks.session_id IS 'Session identifier (matches sessions.id, unique - one extraction per session)';
        COMMENT ON COLUMN session_tasks.tasks IS 'Array of ExtractedTask objects as JSONB';
        COMMENT ON COLUMN session_tasks.total_tasks IS 'Total number of tasks extracted';
        COMMENT ON COLUMN session_tasks.extraction_confidence IS 'AI confidence in task extraction (0.0-1.0)';
        COMMENT ON COLUMN session_tasks.synthesis_sections_analyzed IS 'Which synthesis sections were analyzed';
        COMMENT ON COLUMN session_tasks.extracted_at IS 'When tasks were extracted';
    """)

    # ============================================================================
    # 3. Add synthesis_text column to sessions table (if not exists)
    # ============================================================================

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'sessions'
                AND column_name = 'synthesis_text'
            ) THEN
                ALTER TABLE sessions ADD COLUMN synthesis_text TEXT;
                COMMENT ON COLUMN sessions.synthesis_text IS 'Final synthesis XML from synthesize or meta_synthesize node';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove synthesis_text column from sessions table
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'sessions'
                AND column_name = 'synthesis_text'
            ) THEN
                ALTER TABLE sessions DROP COLUMN synthesis_text;
            END IF;
        END
        $$;
    """)

    # Drop session_tasks table
    op.drop_index("idx_session_tasks_tasks", table_name="session_tasks")
    op.drop_index("idx_session_tasks_extracted_at", table_name="session_tasks")
    op.drop_index("idx_session_tasks_session_id", table_name="session_tasks")
    op.drop_table("session_tasks")

    # Drop session_events table
    op.drop_index("idx_session_events_data", table_name="session_events")
    op.drop_index("idx_session_events_session_sequence", table_name="session_events")
    op.drop_index("idx_session_events_created_at", table_name="session_events")
    op.drop_index("idx_session_events_event_type", table_name="session_events")
    op.drop_index("idx_session_events_session_id", table_name="session_events")
    op.drop_table("session_events")
