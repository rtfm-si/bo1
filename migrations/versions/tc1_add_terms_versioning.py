"""Create terms_versions and terms_consents tables.

T&C versioning: stores T&C versions with content, version number, published_at, active status.
Consent capture: records user agreement with timestamp, version, IP address.

Revision ID: tc1_add_terms_versioning
Revises: z32_add_email_log_events
Create Date: 2025-12-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "tc1_add_terms_versioning"
down_revision: str | Sequence[str] | None = "z32_add_email_log_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create terms_versions and terms_consents tables."""
    # Create terms_versions table
    op.create_table(
        "terms_versions",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "published_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_terms_versions_version"),
    )

    # Create index for active version lookup
    op.create_index(
        "ix_terms_versions_is_active",
        "terms_versions",
        ["is_active"],
        postgresql_where=sa.text("is_active = true"),
    )

    # Create terms_consents table
    op.create_table(
        "terms_consents",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(255), nullable=False),  # Match users.id type
        sa.Column("terms_version_id", sa.UUID(), nullable=False),
        sa.Column(
            "consented_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv6 max length
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["terms_version_id"], ["terms_versions.id"], ondelete="RESTRICT"),
    )

    # Index for user consent lookup
    op.create_index("ix_terms_consents_user_id", "terms_consents", ["user_id"])
    op.create_index(
        "ix_terms_consents_user_consented", "terms_consents", ["user_id", "consented_at"]
    )

    # Enable RLS on terms_consents
    op.execute("ALTER TABLE terms_consents ENABLE ROW LEVEL SECURITY")

    # RLS policy: users can read own consents
    op.execute("""
        CREATE POLICY terms_consents_user_read ON terms_consents
        FOR SELECT
        USING (
            user_id::text = current_setting('app.current_user_id', true)
            OR current_setting('app.is_admin', true) = 'true'
        )
    """)

    # RLS policy: users can insert own consents
    op.execute("""
        CREATE POLICY terms_consents_user_insert ON terms_consents
        FOR INSERT
        WITH CHECK (
            user_id::text = current_setting('app.current_user_id', true)
        )
    """)


def downgrade() -> None:
    """Drop terms tables."""
    op.execute("DROP POLICY IF EXISTS terms_consents_user_insert ON terms_consents")
    op.execute("DROP POLICY IF EXISTS terms_consents_user_read ON terms_consents")
    op.drop_index("ix_terms_consents_user_consented", table_name="terms_consents")
    op.drop_index("ix_terms_consents_user_id", table_name="terms_consents")
    op.drop_table("terms_consents")
    op.drop_index("ix_terms_versions_is_active", table_name="terms_versions")
    op.drop_table("terms_versions")
