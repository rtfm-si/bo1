"""Enable pg_stat_statements extension for query performance analysis.

NOTE: This extension requires `pg_stat_statements` in `shared_preload_libraries`.
- Docker: Configured via docker-compose.yml command args
- Production (DigitalOcean): May need to enable via database dashboard

If the extension is not preloaded, this migration will succeed (IF NOT EXISTS)
but the extension won't be functional until the server is restarted with
the proper configuration.

Revision ID: z16_enable_pg_stat_statements
Revises: z15_add_covering_indexes
Create Date: 2025-12-23
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "z16_enable_pg_stat_statements"
down_revision: str | Sequence[str] | None = "z15_add_covering_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pg_stat_statements extension."""
    # Create extension if not exists - safe to run even if not preloaded
    # The extension will be available once shared_preload_libraries is configured
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")


def downgrade() -> None:
    """Drop pg_stat_statements extension."""
    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements")
