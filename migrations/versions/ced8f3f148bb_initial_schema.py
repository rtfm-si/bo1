"""Initial schema.

Revision ID: ced8f3f148bb
Revises:
Create Date: 2025-11-14 17:03:10.631601
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ced8f3f148bb"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "auth_provider", sa.String(length=50), nullable=False
        ),  # supabase, google, linkedin, github
        sa.Column(
            "subscription_tier", sa.String(length=50), nullable=False, server_default="free"
        ),  # free, pro, enterprise
        sa.Column("gdpr_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Personas table (static data, seeded from personas.json)
    op.create_table(
        "personas",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), unique=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("expertise", sa.String(length=500), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("problem_statement", sa.Text, nullable=False),
        sa.Column("problem_context", sa.JSON, nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="active"
        ),  # active, paused, completed, failed, killed
        sa.Column(
            "phase", sa.String(length=50), nullable=False, server_default="problem_decomposition"
        ),  # problem_decomposition, persona_selection, deliberation, voting, synthesis
        sa.Column(
            "total_cost", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0.0"
        ),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("round_number", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_rounds", sa.Integer, nullable=False, server_default="10"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("killed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("killed_by", sa.String(length=255), nullable=True),  # user_id or 'admin'
        sa.Column("kill_reason", sa.String(length=500), nullable=True),
    )

    # Contributions table (persona deliberation contributions)
    op.create_table(
        "contributions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "persona_code", sa.String(length=50), sa.ForeignKey("personas.code"), nullable=False
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column(
            "phase", sa.String(length=50), nullable=False
        ),  # initial_round, deliberation, moderator_intervention
        sa.Column("cost", sa.Numeric(precision=10, scale=4), nullable=False, server_default="0.0"),
        sa.Column("tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Votes table
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.String(length=255),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "persona_code", sa.String(length=50), sa.ForeignKey("personas.code"), nullable=False
        ),
        sa.Column("vote_choice", sa.String(length=100), nullable=False),  # sub-problem ID or option
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),  # 0.0 to 1.0
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Audit log table (for compliance, security, debugging)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(length=255),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "action", sa.String(length=100), nullable=False
        ),  # session_created, session_killed, user_login, etc.
        sa.Column("resource_type", sa.String(length=50), nullable=False),  # session, user, persona
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),  # IPv6 support
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # Create indexes for performance
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_status", "sessions", ["status"])
    op.create_index("idx_sessions_created_at", "sessions", ["created_at"])
    op.create_index("idx_contributions_session_id", "contributions", ["session_id"])
    op.create_index("idx_contributions_round_number", "contributions", ["round_number"])
    op.create_index("idx_votes_session_id", "votes", ["session_id"])
    op.create_index("idx_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("idx_audit_log_timestamp", "audit_log", ["timestamp"])
    op.create_index("idx_audit_log_resource", "audit_log", ["resource_type", "resource_id"])

    # Enable Row Level Security (RLS) for multi-tenancy
    # Note: RLS policies will be created in a separate migration/script
    # since they require PostgreSQL-specific syntax
    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE contributions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE votes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_audit_log_resource")
    op.drop_index("idx_audit_log_timestamp")
    op.drop_index("idx_audit_log_user_id")
    op.drop_index("idx_votes_session_id")
    op.drop_index("idx_contributions_round_number")
    op.drop_index("idx_contributions_session_id")
    op.drop_index("idx_sessions_created_at")
    op.drop_index("idx_sessions_status")
    op.drop_index("idx_sessions_user_id")

    # Drop tables
    op.drop_table("audit_log")
    op.drop_table("votes")
    op.drop_table("contributions")
    op.drop_table("sessions")
    op.drop_table("personas")
    op.drop_table("users")

    # Drop extensions
    op.execute("DROP EXTENSION IF EXISTS vector")
