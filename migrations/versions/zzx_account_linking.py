"""Add account linking tables.

Revision ID: zzx_account_linking
Revises: zzw_cognition_inferred
Create Date: 2025-01-19

Implements account linking without SuperTokens paid features:
- user_auth_providers: Links multiple auth methods to a primary user
- email_verifications: Tracks email verification tokens
- email_verified_at column on users table
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "zzx_account_linking"
down_revision = "zzw_cognition_inferred"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add account linking tables and email verification support."""
    # Add email_verified_at column to users table
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create user_auth_providers table
    op.create_table(
        "user_auth_providers",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("primary_user_id", sa.String(255), nullable=False),
        sa.Column("supertokens_user_id", sa.String(255), nullable=False),
        sa.Column(
            "provider", sa.String(50), nullable=False
        ),  # google, linkedin, github, email, passwordless
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "linked_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["primary_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("supertokens_user_id", name="uq_uap_supertokens_user_id"),
    )

    # Create indexes for user_auth_providers
    op.create_index("idx_uap_email", "user_auth_providers", [sa.text("LOWER(email)")])
    op.create_index("idx_uap_primary", "user_auth_providers", ["primary_user_id"])
    op.create_index("idx_uap_provider", "user_auth_providers", ["provider"])

    # Create email_verifications table
    op.create_table(
        "email_verifications",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supertokens_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_ev_token"),
    )

    # Create indexes for email_verifications
    op.create_index("idx_ev_token", "email_verifications", ["token"])
    op.create_index("idx_ev_email", "email_verifications", [sa.text("LOWER(email)")])
    op.create_index("idx_ev_st_user_id", "email_verifications", ["supertokens_user_id"])

    # Enable RLS on both tables
    op.execute("ALTER TABLE user_auth_providers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE email_verifications ENABLE ROW LEVEL SECURITY")

    # RLS policy for user_auth_providers - users can only see their own linked providers
    op.execute("""
        CREATE POLICY user_auth_providers_user_policy ON user_auth_providers
        FOR ALL
        USING (
            primary_user_id = current_setting('app.current_user_id', true)
            OR current_setting('app.current_user_id', true) IS NULL
        )
    """)

    # RLS policy for email_verifications - service role only (internal use)
    # Users should not directly query this table
    op.execute("""
        CREATE POLICY email_verifications_service_policy ON email_verifications
        FOR ALL
        USING (current_setting('app.current_user_id', true) IS NULL)
    """)


def downgrade() -> None:
    """Remove account linking tables and email verification support."""
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS user_auth_providers_user_policy ON user_auth_providers")
    op.execute("DROP POLICY IF EXISTS email_verifications_service_policy ON email_verifications")

    # Drop tables
    op.drop_table("email_verifications")
    op.drop_table("user_auth_providers")

    # Drop column from users
    op.drop_column("users", "email_verified_at")
