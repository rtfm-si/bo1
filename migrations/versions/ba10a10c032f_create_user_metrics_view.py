"""Create user_metrics_view.

Revision ID: ba10a10c032f
Revises: aad568d2f04d
Create Date: 2025-11-28 21:07:09.881235

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ba10a10c032f"
down_revision: str | Sequence[str] | None = "aad568d2f04d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_metrics view for admin dashboard
    op.execute(
        """
        CREATE OR REPLACE VIEW user_metrics AS
        SELECT
            u.id,
            u.email,
            u.subscription_tier,
            u.is_admin,
            u.created_at as user_created_at,
            COUNT(s.id) as total_meetings,
            COALESCE(SUM(s.total_cost), 0) as total_cost,
            MAX(s.created_at) as last_meeting_at,
            (SELECT id FROM sessions WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_meeting_id
        FROM users u
        LEFT JOIN sessions s ON u.id = s.user_id
        GROUP BY u.id, u.email, u.subscription_tier, u.is_admin, u.created_at
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop user_metrics view
    op.execute("DROP VIEW IF EXISTS user_metrics")
