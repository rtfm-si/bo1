"""Add TOTP 2FA fields to users table.

Revision ID: zzc_add_totp_2fa_fields
Revises: zzb_add_last_magic_link_at
Create Date: 2026-01-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "zzc_add_totp_2fa_fields"
down_revision = "zzb_add_last_magic_link_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 2FA-related columns to users table."""
    # Flag to track if user has enabled 2FA
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether TOTP 2FA is enabled for this user",
        ),
    )

    # Encrypted backup codes (JSON array of hashed codes)
    # Using TEXT for encrypted blob since actual codes are hashed
    op.add_column(
        "users",
        sa.Column(
            "totp_backup_codes",
            postgresql.ARRAY(sa.Text()),
            nullable=True,
            comment="Hashed backup codes for 2FA recovery (bcrypt hashed)",
        ),
    )

    # Track when 2FA was enabled (for audit)
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When 2FA was enabled",
        ),
    )

    # Rate limiting for 2FA verification attempts
    op.add_column(
        "users",
        sa.Column(
            "totp_failed_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
            comment="Failed 2FA verification attempts (reset on success)",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "totp_lockout_until",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="2FA verification locked out until this time",
        ),
    )


def downgrade() -> None:
    """Remove 2FA-related columns."""
    op.drop_column("users", "totp_lockout_until")
    op.drop_column("users", "totp_failed_attempts")
    op.drop_column("users", "totp_enabled_at")
    op.drop_column("users", "totp_backup_codes")
    op.drop_column("users", "totp_enabled")
