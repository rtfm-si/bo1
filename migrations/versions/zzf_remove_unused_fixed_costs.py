"""Remove unused fixed costs (Managed Redis 2GB, PostgreSQL Pro).

Revision ID: zzf_remove_unused_fixed_costs
Revises: zze_add_industry_benchmark_cache
Create Date: 2025-01-04

These services are no longer used:
- Managed Redis: Using local Redis on droplet
- PostgreSQL Pro: Using Neon free tier
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "zzf_remove_unused_fixed_costs"
down_revision = "zze_add_industry_benchmark_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Deactivate unused fixed cost entries."""
    op.execute("""
        UPDATE fixed_costs
        SET active = FALSE, updated_at = NOW()
        WHERE description IN ('Managed Redis 2GB', 'PostgreSQL Pro')
          AND active = TRUE
    """)


def downgrade() -> None:
    """Re-activate fixed cost entries."""
    op.execute("""
        UPDATE fixed_costs
        SET active = TRUE, updated_at = NOW()
        WHERE description IN ('Managed Redis 2GB', 'PostgreSQL Pro')
    """)
