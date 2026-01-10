"""Add dataset_objective_analyses and insight_objective_links tables.

Phase 1 of Data Analysis Reimagination: stores objective-aligned analysis
results including relevance assessment, data story, and insights linked
to user objectives.

Revision ID: zzr_dataset_objective_analyses
Revises: zzq_multi_dataset_analyses
Create Date: 2025-01-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "zzr_dataset_objective_analyses"
down_revision: str | Sequence[str] | None = "zzq_multi_dataset_analyses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dataset_objective_analyses and insight_objective_links tables."""
    # Main analysis results table
    op.create_table(
        "dataset_objective_analyses",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "dataset_id",
            UUID,
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID, nullable=False),
        # Analysis mode
        sa.Column(
            "analysis_mode", sa.String(20), nullable=False
        ),  # 'objective_focused' | 'open_exploration'
        # Relevance assessment
        sa.Column("relevance_score", sa.Integer, nullable=True),  # 0-100
        sa.Column(
            "relevance_assessment", JSONB, nullable=True
        ),  # Full assessment with objective_matches, missing_data
        # Generated content
        sa.Column(
            "data_story", JSONB, nullable=True
        ),  # Opening hook, objective sections, next steps
        sa.Column("insights", JSONB, nullable=True),  # Array of insights with objective tags
        # Context snapshot (which objectives were active)
        sa.Column("context_snapshot", JSONB, nullable=True),
        # Pre-selected objective (from "What Data Do I Need?" flow)
        sa.Column("selected_objective_id", UUID, nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        # Unique constraint - one analysis per dataset
        sa.UniqueConstraint("dataset_id", name="uq_dataset_objective_analyses_dataset"),
        # Check constraint for analysis_mode
        sa.CheckConstraint(
            "analysis_mode IN ('objective_focused', 'open_exploration')",
            name="ck_dataset_objective_analyses_mode",
        ),
    )

    # Indexes
    op.create_index(
        "idx_dataset_objective_analyses_dataset",
        "dataset_objective_analyses",
        ["dataset_id"],
    )
    op.create_index(
        "idx_dataset_objective_analyses_user",
        "dataset_objective_analyses",
        ["user_id"],
    )
    op.create_index(
        "idx_dataset_objective_analyses_created",
        "dataset_objective_analyses",
        ["user_id", "created_at"],
    )

    # Insight-objective links table
    op.create_table(
        "insight_objective_links",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("insight_id", sa.String(255), nullable=False),  # insight ID from insights JSONB
        sa.Column(
            "analysis_id",
            UUID,
            sa.ForeignKey("dataset_objective_analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("objective_id", UUID, nullable=True),  # If linked to a specific objective
        sa.Column("objective_name", sa.String(255), nullable=True),
        sa.Column("relevance_score", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    # Indexes for insight_objective_links
    op.create_index(
        "idx_insight_objective_links_analysis",
        "insight_objective_links",
        ["analysis_id"],
    )
    op.create_index(
        "idx_insight_objective_links_objective",
        "insight_objective_links",
        ["objective_id"],
    )
    op.create_index(
        "idx_insight_objective_links_insight",
        "insight_objective_links",
        ["insight_id"],
    )

    # Updated_at trigger for dataset_objective_analyses
    op.execute("""
        CREATE OR REPLACE FUNCTION update_dataset_objective_analyses_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER tr_dataset_objective_analyses_updated_at
        BEFORE UPDATE ON dataset_objective_analyses
        FOR EACH ROW
        EXECUTE FUNCTION update_dataset_objective_analyses_updated_at();
    """)

    # RLS policies for dataset_objective_analyses
    op.execute("""
        ALTER TABLE dataset_objective_analyses ENABLE ROW LEVEL SECURITY;

        CREATE POLICY dataset_objective_analyses_user_isolation ON dataset_objective_analyses
            USING (user_id = current_setting('app.current_user_id', true)::uuid);

        CREATE POLICY dataset_objective_analyses_user_insert ON dataset_objective_analyses
            FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);
    """)

    # RLS policies for insight_objective_links (via analysis ownership)
    op.execute("""
        ALTER TABLE insight_objective_links ENABLE ROW LEVEL SECURITY;

        CREATE POLICY insight_objective_links_user_isolation ON insight_objective_links
            USING (
                analysis_id IN (
                    SELECT id FROM dataset_objective_analyses
                    WHERE user_id = current_setting('app.current_user_id', true)::uuid
                )
            );

        CREATE POLICY insight_objective_links_user_insert ON insight_objective_links
            FOR INSERT WITH CHECK (
                analysis_id IN (
                    SELECT id FROM dataset_objective_analyses
                    WHERE user_id = current_setting('app.current_user_id', true)::uuid
                )
            );
    """)


def downgrade() -> None:
    """Drop dataset_objective_analyses and insight_objective_links tables."""
    # Drop RLS policies
    op.execute(
        "DROP POLICY IF EXISTS insight_objective_links_user_isolation ON insight_objective_links;"
    )
    op.execute(
        "DROP POLICY IF EXISTS insight_objective_links_user_insert ON insight_objective_links;"
    )
    op.execute(
        "DROP POLICY IF EXISTS dataset_objective_analyses_user_isolation ON dataset_objective_analyses;"
    )
    op.execute(
        "DROP POLICY IF EXISTS dataset_objective_analyses_user_insert ON dataset_objective_analyses;"
    )

    # Drop trigger and function
    op.execute(
        "DROP TRIGGER IF EXISTS tr_dataset_objective_analyses_updated_at ON dataset_objective_analyses;"
    )
    op.execute("DROP FUNCTION IF EXISTS update_dataset_objective_analyses_updated_at;")

    # Drop indexes and tables
    op.drop_index("idx_insight_objective_links_insight", table_name="insight_objective_links")
    op.drop_index("idx_insight_objective_links_objective", table_name="insight_objective_links")
    op.drop_index("idx_insight_objective_links_analysis", table_name="insight_objective_links")
    op.drop_table("insight_objective_links")

    op.drop_index("idx_dataset_objective_analyses_created", table_name="dataset_objective_analyses")
    op.drop_index("idx_dataset_objective_analyses_user", table_name="dataset_objective_analyses")
    op.drop_index("idx_dataset_objective_analyses_dataset", table_name="dataset_objective_analyses")
    op.drop_table("dataset_objective_analyses")
