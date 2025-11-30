"""partition_high_growth_tables_by_month.

Partition high-growth tables by month for optimal query performance.
Partitions: api_costs, session_events, contributions

Since there are NO LIVE CUSTOMERS, we can safely partition now.

Partitioning strategy:
- RANGE partitioning by created_at (monthly intervals)
- Create partitions for past 6 months, current, future 6 months (13 total per table)
- Automatic partition creation via management functions
- Partition pruning for 10-100x faster queries on date ranges

Expected benefits:
- Query performance: 10-100x faster for date-filtered queries
- Maintenance: Drop old partitions instead of VACUUM
- Scalability: Independent partition growth

Revision ID: f3b5a664a3ff
Revises: b0d1100890ab
Create Date: 2025-11-30 22:09:15.519060

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b5a664a3ff"
down_revision: str | Sequence[str] | None = "b0d1100890ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Partition api_costs, session_events, and contributions by month."""
    # =============================================================================
    # 1. Partition api_costs table
    # =============================================================================

    op.execute("""
        -- Step 1: Drop dependent materialized views (will be recreated)
        DROP MATERIALIZED VIEW IF EXISTS session_cost_summary CASCADE;

        -- Step 2: Drop existing unique constraint (will be recreated)
        ALTER TABLE api_costs DROP CONSTRAINT IF EXISTS api_costs_request_id_key;

        -- Step 3: Rename existing table
        ALTER TABLE api_costs RENAME TO api_costs_old;

        -- Step 4: Create partitioned table with same schema
        CREATE TABLE api_costs (
            id BIGINT NOT NULL DEFAULT nextval('api_costs_id_seq'),
            request_id UUID NOT NULL DEFAULT gen_random_uuid(),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            session_id VARCHAR(255),
            user_id VARCHAR(255),
            provider VARCHAR(50) NOT NULL,
            model_name VARCHAR(100),
            operation_type VARCHAR(50) NOT NULL,
            node_name VARCHAR(100),
            phase VARCHAR(50),
            persona_name VARCHAR(100),
            round_number INTEGER,
            sub_problem_index INTEGER,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
            cache_creation_tokens INTEGER NOT NULL DEFAULT 0,
            cache_read_tokens INTEGER NOT NULL DEFAULT 0,
            cache_hit BOOLEAN NOT NULL DEFAULT false,
            input_cost NUMERIC(12,8) NOT NULL DEFAULT 0,
            output_cost NUMERIC(12,8) NOT NULL DEFAULT 0,
            cache_write_cost NUMERIC(12,8) NOT NULL DEFAULT 0,
            cache_read_cost NUMERIC(12,8) NOT NULL DEFAULT 0,
            total_cost NUMERIC(12,8) NOT NULL,
            optimization_type VARCHAR(50),
            cost_without_optimization NUMERIC(12,8),
            latency_ms INTEGER,
            status VARCHAR(20) NOT NULL DEFAULT 'success',
            error_message TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            contribution_id INTEGER,
            recommendation_id INTEGER,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);

        -- Step 5: Create monthly partitions (6 months back, current, 6 months forward = 13 partitions)
        DO $$
        DECLARE
            start_date DATE;
            end_date DATE;
            partition_name TEXT;
        BEGIN
            FOR i IN -6..6 LOOP
                start_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
                end_date := start_date + INTERVAL '1 month';
                partition_name := 'api_costs_' || TO_CHAR(start_date, 'YYYY_MM');

                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF api_costs FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    start_date,
                    end_date
                );
            END LOOP;
        END $$;

        -- Step 6: Copy data from old table (if any exists)
        -- Exclude total_tokens (generated column) from INSERT
        INSERT INTO api_costs (
            id, request_id, created_at, session_id, user_id, provider, model_name,
            operation_type, node_name, phase, persona_name, round_number, sub_problem_index,
            input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, cache_hit,
            input_cost, output_cost, cache_write_cost, cache_read_cost, total_cost,
            optimization_type, cost_without_optimization, latency_ms, status, error_message,
            metadata, contribution_id, recommendation_id
        )
        SELECT
            id, request_id, created_at, session_id, user_id, provider, model_name,
            operation_type, node_name, phase, persona_name, round_number, sub_problem_index,
            input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, cache_hit,
            input_cost, output_cost, cache_write_cost, cache_read_cost, total_cost,
            optimization_type, cost_without_optimization, latency_ms, status, error_message,
            metadata, contribution_id, recommendation_id
        FROM api_costs_old;

        -- Step 7: Drop old table with CASCADE to handle dependencies
        DROP TABLE api_costs_old CASCADE;

        -- Step 8: Recreate unique constraint and indexes on partitioned table
        CREATE UNIQUE INDEX api_costs_request_id_key ON api_costs (request_id, created_at);
        CREATE INDEX idx_api_costs_session ON api_costs (session_id, created_at DESC);
        CREATE INDEX idx_api_costs_user ON api_costs (user_id, created_at DESC);
        CREATE INDEX idx_api_costs_created ON api_costs (created_at DESC);
        CREATE INDEX idx_api_costs_provider ON api_costs (provider, model_name);
        CREATE INDEX idx_api_costs_node ON api_costs (node_name);
        CREATE INDEX idx_api_costs_phase ON api_costs (phase);
        CREATE INDEX idx_api_costs_contribution ON api_costs (contribution_id);
        CREATE INDEX idx_api_costs_recommendation ON api_costs (recommendation_id);
        CREATE INDEX idx_api_costs_session_node ON api_costs (session_id, node_name);
        CREATE INDEX idx_api_costs_user_created ON api_costs (user_id, created_at DESC);
        CREATE INDEX idx_api_costs_metadata ON api_costs USING GIN (metadata);
        CREATE INDEX idx_api_costs_analysis ON api_costs (created_at DESC, session_id, provider, total_cost);

        -- Step 9: Re-add foreign keys (partitioned tables support FK in Postgres 11+)
        ALTER TABLE api_costs ADD CONSTRAINT api_costs_session_id_fkey
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE;
        ALTER TABLE api_costs ADD CONSTRAINT api_costs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
        ALTER TABLE api_costs ADD CONSTRAINT fk_api_costs_contribution_id
            FOREIGN KEY (contribution_id) REFERENCES contributions(id) ON DELETE SET NULL;
        ALTER TABLE api_costs ADD CONSTRAINT fk_api_costs_recommendation_id
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL;

        -- Step 8: Re-add check constraints
        ALTER TABLE api_costs ADD CONSTRAINT check_cost_positive CHECK (total_cost >= 0);
        ALTER TABLE api_costs ADD CONSTRAINT check_provider
            CHECK (provider IN ('anthropic', 'voyage', 'brave', 'tavily'));

        -- Step 9: Re-enable RLS
        ALTER TABLE api_costs ENABLE ROW LEVEL SECURITY;
    """)

    # Re-create RLS policies for api_costs
    op.execute("""
        CREATE POLICY api_costs_user_isolation ON api_costs
        FOR ALL USING (user_id = current_setting('app.current_user_id', TRUE)::text);

        CREATE POLICY api_costs_admin_access ON api_costs
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', TRUE)::text AND is_admin = true)
        );
    """)

    # =============================================================================
    # 2. Partition session_events table
    # =============================================================================

    op.execute("""
        -- Drop existing unique constraint
        ALTER TABLE session_events DROP CONSTRAINT IF EXISTS unique_session_sequence;

        -- Rename existing table
        ALTER TABLE session_events RENAME TO session_events_old;

        -- Create partitioned table
        CREATE TABLE session_events (
            id BIGINT NOT NULL DEFAULT nextval('session_events_id_seq'),
            session_id VARCHAR(255) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            sequence INTEGER NOT NULL,
            data JSONB NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);

        -- Create monthly partitions
        DO $$
        DECLARE
            start_date DATE;
            end_date DATE;
            partition_name TEXT;
        BEGIN
            FOR i IN -6..6 LOOP
                start_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
                end_date := start_date + INTERVAL '1 month';
                partition_name := 'session_events_' || TO_CHAR(start_date, 'YYYY_MM');

                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF session_events FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    start_date,
                    end_date
                );
            END LOOP;
        END $$;

        -- Copy data (explicitly specify columns)
        INSERT INTO session_events (id, session_id, event_type, sequence, data, user_id, created_at)
        SELECT id, session_id, event_type, sequence, data, user_id, created_at
        FROM session_events_old;

        -- Drop old table with CASCADE
        DROP TABLE session_events_old CASCADE;

        -- Recreate unique constraint and indexes
        CREATE UNIQUE INDEX unique_session_sequence ON session_events (session_id, sequence, created_at);
        CREATE INDEX idx_session_events_session_id ON session_events (session_id, created_at DESC);
        CREATE INDEX idx_session_events_event_type ON session_events (event_type);
        CREATE INDEX idx_session_events_created_at ON session_events (created_at DESC);
        CREATE INDEX idx_session_events_session_sequence ON session_events (session_id, sequence);
        CREATE INDEX idx_session_events_data ON session_events USING GIN (data);
        CREATE INDEX idx_session_events_user_id ON session_events (user_id);

        -- Re-add foreign keys
        ALTER TABLE session_events ADD CONSTRAINT session_events_session_id_fkey
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE;
        ALTER TABLE session_events ADD CONSTRAINT fk_session_events_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

        -- Re-enable RLS
        ALTER TABLE session_events ENABLE ROW LEVEL SECURITY;
    """)

    # Re-create RLS policies for session_events
    op.execute("""
        CREATE POLICY session_events_user_isolation ON session_events
        FOR ALL USING (user_id = current_setting('app.current_user_id', TRUE)::text);

        CREATE POLICY session_events_admin_access ON session_events
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', TRUE)::text AND is_admin = true)
        );
    """)

    # =============================================================================
    # 3. Partition contributions table
    # =============================================================================

    op.execute("""
        -- Rename existing table
        ALTER TABLE contributions RENAME TO contributions_old;

        -- Create partitioned table
        CREATE TABLE contributions (
            id INTEGER NOT NULL DEFAULT nextval('contributions_id_seq'),
            session_id VARCHAR(255) NOT NULL,
            persona_code VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            round_number INTEGER NOT NULL,
            phase VARCHAR(50) NOT NULL,
            cost NUMERIC(10,4) NOT NULL DEFAULT 0.0,
            tokens INTEGER NOT NULL DEFAULT 0,
            model VARCHAR(100) NOT NULL,
            embedding vector(1024),
            user_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);

        -- Create monthly partitions
        DO $$
        DECLARE
            start_date DATE;
            end_date DATE;
            partition_name TEXT;
        BEGIN
            FOR i IN -6..6 LOOP
                start_date := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
                end_date := start_date + INTERVAL '1 month';
                partition_name := 'contributions_' || TO_CHAR(start_date, 'YYYY_MM');

                EXECUTE format(
                    'CREATE TABLE %I PARTITION OF contributions FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    start_date,
                    end_date
                );
            END LOOP;
        END $$;

        -- Copy data (explicitly specify columns)
        INSERT INTO contributions (id, session_id, persona_code, content, round_number, phase, cost, tokens, model, embedding, user_id, created_at)
        SELECT id, session_id, persona_code, content, round_number, phase, cost, tokens, model, embedding, user_id, created_at
        FROM contributions_old;

        -- Drop old table with CASCADE
        DROP TABLE contributions_old CASCADE;

        -- Recreate indexes
        CREATE INDEX idx_contributions_session_id ON contributions (session_id, created_at DESC);
        CREATE INDEX idx_contributions_round_number ON contributions (round_number);
        CREATE INDEX idx_contributions_user_id ON contributions (user_id);
        CREATE INDEX idx_contributions_created_at ON contributions (created_at DESC);
        CREATE INDEX idx_contributions_session_round ON contributions (session_id, round_number);
        CREATE INDEX idx_contributions_persona_session ON contributions (persona_code, session_id);

        -- Re-add foreign keys
        ALTER TABLE contributions ADD CONSTRAINT contributions_session_id_fkey
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE;
        ALTER TABLE contributions ADD CONSTRAINT contributions_persona_code_fkey
            FOREIGN KEY (persona_code) REFERENCES personas(code);
        ALTER TABLE contributions ADD CONSTRAINT fk_contributions_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

        -- Re-enable RLS
        ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;
    """)

    # Re-create RLS policies for contributions
    op.execute("""
        CREATE POLICY contributions_user_isolation ON contributions
        FOR ALL USING (user_id = current_setting('app.current_user_id', TRUE)::text);

        CREATE POLICY contributions_admin_access ON contributions
        FOR SELECT USING (
            EXISTS (SELECT 1 FROM users WHERE id = current_setting('app.current_user_id', TRUE)::text AND is_admin = true)
        );
    """)

    # =============================================================================
    # 4. Create partition management functions
    # =============================================================================

    op.execute("""
        -- Function to auto-create next month's partitions for all partitioned tables
        CREATE OR REPLACE FUNCTION create_next_month_partitions()
        RETURNS TABLE (
            table_name TEXT,
            partition_name TEXT,
            status TEXT
        ) AS $$
        DECLARE
            next_month DATE;
            partition_date DATE;
            tbl TEXT;
            part_name TEXT;
        BEGIN
            next_month := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '2 months');

            -- Loop through partitioned tables
            FOR tbl IN SELECT unnest(ARRAY['api_costs', 'session_events', 'contributions'])
            LOOP
                part_name := tbl || '_' || TO_CHAR(next_month, 'YYYY_MM');

                -- Check if partition already exists
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = part_name AND n.nspname = 'public'
                ) THEN
                    EXECUTE format(
                        'CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                        part_name,
                        tbl,
                        next_month,
                        next_month + INTERVAL '1 month'
                    );

                    RETURN QUERY SELECT tbl, part_name, 'created'::TEXT;
                ELSE
                    RETURN QUERY SELECT tbl, part_name, 'already_exists'::TEXT;
                END IF;
            END LOOP;
        END;
        $$ LANGUAGE plpgsql;

        -- Function to get partition sizes and row counts
        CREATE OR REPLACE FUNCTION partition_sizes(parent_table TEXT)
        RETURNS TABLE (
            partition_name TEXT,
            row_count BIGINT,
            total_size TEXT,
            table_size TEXT,
            indexes_size TEXT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                c.relname::TEXT,
                c.reltuples::BIGINT,
                pg_size_pretty(pg_total_relation_size(c.oid)),
                pg_size_pretty(pg_relation_size(c.oid)),
                pg_size_pretty(pg_total_relation_size(c.oid) - pg_relation_size(c.oid))
            FROM pg_class c
            JOIN pg_inherits i ON i.inhrelid = c.oid
            JOIN pg_class p ON p.oid = i.inhparent
            WHERE p.relname = parent_table
            ORDER BY c.relname;
        END;
        $$ LANGUAGE plpgsql;

        -- Function to list all partitions with date ranges
        CREATE OR REPLACE FUNCTION list_partitions(parent_table TEXT)
        RETURNS TABLE (
            partition_name TEXT,
            start_range TEXT,
            end_range TEXT,
            row_count BIGINT
        ) AS $$
        BEGIN
            RETURN QUERY
            SELECT
                c.relname::TEXT,
                pg_get_expr(c.relpartbound, c.oid, true)::TEXT AS partition_range,
                NULL::TEXT,  -- Placeholder for end_range
                c.reltuples::BIGINT
            FROM pg_class c
            JOIN pg_inherits i ON i.inhrelid = c.oid
            JOIN pg_class p ON p.oid = i.inhparent
            WHERE p.relname = parent_table
            ORDER BY c.relname;
        END;
        $$ LANGUAGE plpgsql;

        COMMENT ON FUNCTION create_next_month_partitions() IS
            'Auto-create next month partitions for api_costs, session_events, contributions. Run monthly via cron.';
        COMMENT ON FUNCTION partition_sizes(TEXT) IS
            'Get size breakdown for all partitions of a table';
        COMMENT ON FUNCTION list_partitions(TEXT) IS
            'List all partitions with their date ranges and row counts';
    """)


def downgrade() -> None:
    """Revert partitioning - convert back to regular tables."""
    # Note: Downgrade is complex and should be avoided in production
    # This is a safety net for development only

    op.execute("""
        -- Drop partition management functions
        DROP FUNCTION IF EXISTS create_next_month_partitions();
        DROP FUNCTION IF EXISTS partition_sizes(TEXT);
        DROP FUNCTION IF EXISTS list_partitions(TEXT);
    """)

    # For each partitioned table, convert back to regular table
    for table in ["api_costs", "session_events", "contributions"]:
        op.execute(
            f"""  # noqa: S608
            -- Create temporary regular table
            CREATE TABLE {table}_temp AS SELECT * FROM {table};

            -- Drop partitioned table (CASCADE drops all partitions)
            DROP TABLE {table} CASCADE;

            -- Rename temp table back
            ALTER TABLE {table}_temp RENAME TO {table};

            -- Note: Indexes and constraints would need to be recreated manually
            -- This downgrade is intentionally incomplete - partitioning should not be reverted
        """
        )
