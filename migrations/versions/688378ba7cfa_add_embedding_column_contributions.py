"""add_embedding_column_contributions.

Add embedding column to contributions table for semantic deduplication.
Persisting embeddings saves ~$0.0001 per contribution on repeat analysis.

With 1000s of contributions, this saves significant compute and enables
fast similarity search for contribution analysis.

Revision ID: 688378ba7cfa
Revises: b233c4ff7a14
Create Date: 2025-11-30 21:30:00.748738

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "688378ba7cfa"
down_revision: str | Sequence[str] | None = "b233c4ff7a14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add embedding column (1024 dimensions for Voyage AI embeddings)
    # Idempotent - only add if doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'contributions' AND column_name = 'embedding'
            ) THEN
                ALTER TABLE contributions ADD COLUMN embedding vector(1024);
            END IF;
        END $$;
    """)

    # Create HNSW index for fast similarity search
    # Using cosine distance operator for semantic similarity
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_contributions_embedding
        ON contributions
        USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index first
    op.execute("DROP INDEX IF EXISTS idx_contributions_embedding")

    # Drop column
    op.drop_column("contributions", "embedding")
