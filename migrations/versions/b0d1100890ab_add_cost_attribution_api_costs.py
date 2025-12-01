"""add_cost_attribution_api_costs.

Add cost attribution columns to api_costs table.
Enables tracking which contribution or recommendation incurred each cost.

This provides granular cost analytics per persona, per contribution type,
and enables identifying expensive operations for optimization.

Revision ID: b0d1100890ab
Revises: 688378ba7cfa
Create Date: 2025-11-30 21:30:00.986144

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b0d1100890ab"
down_revision: str | Sequence[str] | None = "688378ba7cfa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add foreign key columns for cost attribution (idempotent)
    # These are nullable because not all API costs map to contributions/recommendations
    # (e.g., facilitator decisions, summarization, research)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'api_costs' AND column_name = 'contribution_id'
            ) THEN
                ALTER TABLE api_costs ADD COLUMN contribution_id INTEGER;
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'api_costs' AND column_name = 'recommendation_id'
            ) THEN
                ALTER TABLE api_costs ADD COLUMN recommendation_id INTEGER;
            END IF;
        END $$;
    """)

    # Add foreign key constraints (idempotent - only if tables exist)
    op.execute("""
        DO $$
        BEGIN
            -- Drop existing constraint if it exists
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_api_costs_contribution_id'
                AND table_name = 'api_costs'
            ) THEN
                ALTER TABLE api_costs DROP CONSTRAINT fk_api_costs_contribution_id;
            END IF;

            -- Add constraint (contributions table always exists)
            ALTER TABLE api_costs
            ADD CONSTRAINT fk_api_costs_contribution_id
            FOREIGN KEY (contribution_id) REFERENCES contributions(id) ON DELETE SET NULL;
        END $$;
    """)

    # Only create recommendations FK if table exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'recommendations') THEN
                -- Drop existing constraint if it exists
                IF EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_api_costs_recommendation_id'
                    AND table_name = 'api_costs'
                ) THEN
                    ALTER TABLE api_costs DROP CONSTRAINT fk_api_costs_recommendation_id;
                END IF;

                -- Add constraint
                ALTER TABLE api_costs
                ADD CONSTRAINT fk_api_costs_recommendation_id
                FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # Create indexes for cost analytics queries (idempotent)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_api_costs_contribution ON api_costs (contribution_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_api_costs_recommendation ON api_costs (recommendation_id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index("idx_api_costs_recommendation", table_name="api_costs")
    op.drop_index("idx_api_costs_contribution", table_name="api_costs")

    # Drop foreign keys
    op.drop_constraint("fk_api_costs_recommendation_id", "api_costs", type_="foreignkey")
    op.drop_constraint("fk_api_costs_contribution_id", "api_costs", type_="foreignkey")

    # Drop columns
    op.drop_column("api_costs", "recommendation_id")
    op.drop_column("api_costs", "contribution_id")
