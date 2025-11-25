"""Fix research_cache vector type and index.

Revision ID: f23423398b2a
Revises: 2dda9a3a5df2
Create Date: 2025-11-25 15:36:07.875399

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f23423398b2a"
down_revision: str | Sequence[str] | None = "2dda9a3a5df2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - convert question_embedding to vector type and add HNSW index.

    Changes:
    1. Convert question_embedding from double precision[] to vector(1024)
    2. Add HNSW index for fast cosine similarity search
    3. HNSW provides better performance than IVFFlat for small-to-medium datasets (<1M vectors)

    Performance:
    - HNSW: O(log N) approximate search, better recall at high speed
    - IVFFlat: O(N/lists) scan, requires tuning of list count
    - For research cache (<100K entries), HNSW is optimal
    """
    # Step 1: Add new vector column (can't ALTER TYPE directly with data)
    op.execute("""
        ALTER TABLE research_cache
        ADD COLUMN question_embedding_vector vector(1024)
    """)

    # Step 2: Copy data from array to vector
    # Cast double precision[] to vector - pgvector handles this conversion
    op.execute("""
        UPDATE research_cache
        SET question_embedding_vector = question_embedding::vector(1024)
        WHERE question_embedding IS NOT NULL
    """)

    # Step 3: Drop old column
    op.execute("""
        ALTER TABLE research_cache
        DROP COLUMN question_embedding
    """)

    # Step 4: Rename new column to original name
    op.execute("""
        ALTER TABLE research_cache
        RENAME COLUMN question_embedding_vector TO question_embedding
    """)

    # Step 5: Create HNSW index for cosine similarity search
    # HNSW parameters:
    # - m=16: number of connections per layer (default, good balance)
    # - ef_construction=64: search quality during build (default)
    # Higher values = better recall but slower build
    op.execute("""
        CREATE INDEX idx_research_cache_embedding_hnsw
        ON research_cache
        USING hnsw (question_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Downgrade schema - revert vector type back to array."""
    # Drop HNSW index
    op.execute("""
        DROP INDEX IF EXISTS idx_research_cache_embedding_hnsw
    """)

    # Add temporary array column
    op.execute("""
        ALTER TABLE research_cache
        ADD COLUMN question_embedding_array double precision[]
    """)

    # Convert vector back to array
    op.execute("""
        UPDATE research_cache
        SET question_embedding_array = question_embedding::double precision[]
        WHERE question_embedding IS NOT NULL
    """)

    # Drop vector column
    op.execute("""
        ALTER TABLE research_cache
        DROP COLUMN question_embedding
    """)

    # Rename array column back
    op.execute("""
        ALTER TABLE research_cache
        RENAME COLUMN question_embedding_array TO question_embedding
    """)
