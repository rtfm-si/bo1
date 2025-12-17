"""Seed beta whitelist with founder and initial beta testers.

Revision ID: z10_seed_beta_whitelist
Revises: z9_add_email_log
Create Date: 2025-12-17

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z10_seed_beta_whitelist"
down_revision: str | Sequence[str] | None = "z9_add_email_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Core beta whitelist - these users should always have access
BETA_WHITELIST = [
    ("si@boardof.one", "founder"),
    ("siperiea@gmail.com", "founder"),
    ("info@seilich.co.uk", "beta tester"),
    ("peter.eaton1@gmail.com", "beta tester"),
    ("stuart@umberandochre.co.uk", "beta tester"),
]

# Admin users - these users get is_admin=true
ADMIN_EMAILS = ["si@boardof.one"]


def upgrade() -> None:
    """Seed beta whitelist and set admin users."""
    # Insert whitelist entries (idempotent - ON CONFLICT DO NOTHING)
    for email, notes in BETA_WHITELIST:
        op.execute(
            f"""
            INSERT INTO beta_whitelist (email, notes)
            VALUES ('{email}', '{notes}')
            ON CONFLICT (email) DO NOTHING
            """
        )

    # Set admin flag for admin users
    for email in ADMIN_EMAILS:
        op.execute(
            f"""
            UPDATE users SET is_admin = true WHERE email = '{email}'
            """
        )


def downgrade() -> None:
    """Remove seeded whitelist entries (optional - usually not needed)."""
    # Note: We don't remove admin status on downgrade to avoid locking out admins
    # Only remove whitelist entries that were added by this migration
    emails = [email for email, _ in BETA_WHITELIST]
    email_list = ", ".join(f"'{e}'" for e in emails)
    op.execute(f"DELETE FROM beta_whitelist WHERE email IN ({email_list})")
