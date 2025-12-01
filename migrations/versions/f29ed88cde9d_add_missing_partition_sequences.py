"""add_missing_partition_sequences

Revision ID: f29ed88cde9d
Revises: f3b5a664a3ff
Create Date: 2025-12-01 19:41:19.025356

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f29ed88cde9d"
down_revision: str | Sequence[str] | None = "f3b5a664a3ff"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create missing sequences for partitioned tables and set defaults."""
    op.execute("""
        -- Create sequences for partitioned tables
        CREATE SEQUENCE IF NOT EXISTS api_costs_id_seq;
        CREATE SEQUENCE IF NOT EXISTS session_events_id_seq;
        CREATE SEQUENCE IF NOT EXISTS contributions_id_seq;

        -- Set the sequences to start from max existing ID + 1
        SELECT setval('api_costs_id_seq', COALESCE((SELECT MAX(id) FROM api_costs), 0) + 1, false);
        SELECT setval('session_events_id_seq', COALESCE((SELECT MAX(id) FROM session_events), 0) + 1, false);
        SELECT setval('contributions_id_seq', COALESCE((SELECT MAX(id) FROM contributions), 0) + 1, false);

        -- Attach sequences as default values for the partitioned tables
        ALTER TABLE api_costs ALTER COLUMN id SET DEFAULT nextval('api_costs_id_seq');
        ALTER TABLE session_events ALTER COLUMN id SET DEFAULT nextval('session_events_id_seq');
        ALTER TABLE contributions ALTER COLUMN id SET DEFAULT nextval('contributions_id_seq');

        -- Mark sequences as owned by the columns (for DROP TABLE CASCADE)
        ALTER SEQUENCE api_costs_id_seq OWNED BY api_costs.id;
        ALTER SEQUENCE session_events_id_seq OWNED BY session_events.id;
        ALTER SEQUENCE contributions_id_seq OWNED BY contributions.id;
    """)


def downgrade() -> None:
    """Remove sequences (they will be auto-dropped via OWNED BY)."""
    op.execute("""
        -- Remove default values (sequences will be dropped automatically via OWNED BY)
        ALTER TABLE api_costs ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE session_events ALTER COLUMN id DROP DEFAULT;
        ALTER TABLE contributions ALTER COLUMN id DROP DEFAULT;

        -- Drop sequences
        DROP SEQUENCE IF EXISTS api_costs_id_seq CASCADE;
        DROP SEQUENCE IF EXISTS session_events_id_seq CASCADE;
        DROP SEQUENCE IF EXISTS contributions_id_seq CASCADE;
    """)
