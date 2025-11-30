-- Production Deployment Script: Data Persistence Security Fixes
-- Date: 2025-11-30
-- Purpose: Apply all pending migrations from c7d8e9f0a1b2 to b0d1100890ab (head)
--
-- CRITICAL: This script is fully idempotent and safe to run multiple times.
-- It handles existing columns, indexes, and constraints gracefully.
--
-- ========================================================================
-- PRE-DEPLOYMENT CHECKLIST
-- ========================================================================
-- [ ] Database backup completed
-- [ ] Current migration version verified (SELECT version_num FROM alembic_version)
-- [ ] No active deliberations running (SELECT COUNT(*) FROM sessions WHERE status = 'active')
-- [ ] Disk space check (>1GB free recommended)
--
-- ========================================================================
-- BACKUP COMMAND (RUN FIRST!)
-- ========================================================================
-- pg_dump -U bo1 -d boardofone -F c -f /tmp/backup_before_migration_$(date +%Y%m%d_%H%M%S).dump
--
-- ========================================================================
-- MIGRATIONS
-- ========================================================================

-- Begin transaction (for safety)
BEGIN;

-- ========================================================================
-- Migration 1: RLS Policies for api_costs (9a51aef9277a)
-- ========================================================================

-- Enable RLS on api_costs
ALTER TABLE api_costs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (idempotent)
DROP POLICY IF EXISTS api_costs_user_isolation ON api_costs;
CREATE POLICY api_costs_user_isolation ON api_costs
FOR ALL
USING (user_id = current_setting('app.current_user_id', TRUE)::text);

DROP POLICY IF EXISTS api_costs_admin_access ON api_costs;
CREATE POLICY api_costs_admin_access ON api_costs
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = current_setting('app.current_user_id', TRUE)::text
        AND is_admin = true
    )
);

-- ========================================================================
-- Migration 2: user_id and RLS for session_events and session_tasks (6ed4a804bd2b)
-- ========================================================================

-- Add user_id to session_events (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_events' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE session_events ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- Backfill user_id from sessions
UPDATE session_events e
SET user_id = s.user_id
FROM sessions s
WHERE e.session_id = s.id
AND e.user_id IS NULL;

-- Add foreign key (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_session_events_user_id'
        AND table_name = 'session_events'
    ) THEN
        ALTER TABLE session_events DROP CONSTRAINT fk_session_events_user_id;
    END IF;

    ALTER TABLE session_events
    ADD CONSTRAINT fk_session_events_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
END $$;

-- Create index (idempotent)
CREATE INDEX IF NOT EXISTS idx_session_events_user ON session_events (user_id, created_at DESC);

-- Enable RLS and create policies
ALTER TABLE session_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS session_events_user_isolation ON session_events;
CREATE POLICY session_events_user_isolation ON session_events
FOR ALL
USING (user_id = current_setting('app.current_user_id', TRUE)::text);

DROP POLICY IF EXISTS session_events_admin_access ON session_events;
CREATE POLICY session_events_admin_access ON session_events
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = current_setting('app.current_user_id', TRUE)::text
        AND is_admin = true
    )
);

-- Repeat for session_tasks
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'session_tasks' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE session_tasks ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

UPDATE session_tasks t
SET user_id = s.user_id
FROM sessions s
WHERE t.session_id = s.id
AND t.user_id IS NULL;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_session_tasks_user_id'
        AND table_name = 'session_tasks'
    ) THEN
        ALTER TABLE session_tasks DROP CONSTRAINT fk_session_tasks_user_id;
    END IF;

    ALTER TABLE session_tasks
    ADD CONSTRAINT fk_session_tasks_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
END $$;

CREATE INDEX IF NOT EXISTS idx_session_tasks_user ON session_tasks (user_id, created_at DESC);

ALTER TABLE session_tasks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS session_tasks_user_isolation ON session_tasks;
CREATE POLICY session_tasks_user_isolation ON session_tasks
FOR ALL
USING (user_id = current_setting('app.current_user_id', TRUE)::text);

DROP POLICY IF EXISTS session_tasks_admin_access ON session_tasks;
CREATE POLICY session_tasks_admin_access ON session_tasks
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = current_setting('app.current_user_id', TRUE)::text
        AND is_admin = true
    )
);

-- ========================================================================
-- Migration 3: Waitlist RLS (1a74c9a84037)
-- ========================================================================

ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS waitlist_admin_only ON waitlist;
CREATE POLICY waitlist_admin_only ON waitlist
FOR ALL
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = current_setting('app.current_user_id', TRUE)::text
        AND is_admin = true
    )
);

-- ========================================================================
-- Migration 4: user_id and RLS for contributions (074cc4d875b0)
-- ========================================================================

-- Add user_id to contributions (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contributions' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE contributions ADD COLUMN user_id VARCHAR(255);
    END IF;
END $$;

-- Backfill user_id from sessions
UPDATE contributions c
SET user_id = s.user_id
FROM sessions s
WHERE c.session_id = s.id
AND c.user_id IS NULL;

-- Add foreign key (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_contributions_user_id'
        AND table_name = 'contributions'
    ) THEN
        ALTER TABLE contributions DROP CONSTRAINT fk_contributions_user_id;
    END IF;

    ALTER TABLE contributions
    ADD CONSTRAINT fk_contributions_user_id
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
END $$;

-- Create index
CREATE INDEX IF NOT EXISTS idx_contributions_user_id ON contributions (user_id);

-- Enable RLS and create policies
ALTER TABLE contributions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS contributions_user_isolation ON contributions;
CREATE POLICY contributions_user_isolation ON contributions
FOR ALL
USING (user_id = current_setting('app.current_user_id', TRUE)::text);

DROP POLICY IF EXISTS contributions_admin_access ON contributions;
CREATE POLICY contributions_admin_access ON contributions
FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM users
        WHERE id = current_setting('app.current_user_id', TRUE)::text
        AND is_admin = true
    )
);

-- ========================================================================
-- Migration 5: Composite Indexes for Performance (b233c4ff7a14)
-- ========================================================================

-- api_costs indexes
CREATE INDEX IF NOT EXISTS idx_api_costs_user_created ON api_costs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_costs_session_node ON api_costs (session_id, node_name);

-- contributions indexes
CREATE INDEX IF NOT EXISTS idx_contributions_persona_code ON contributions (persona_code);
CREATE INDEX IF NOT EXISTS idx_contributions_session_persona ON contributions (session_id, persona_code);
CREATE INDEX IF NOT EXISTS idx_contributions_created_at ON contributions (created_at DESC);

-- recommendations indexes (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'recommendations') THEN
        CREATE INDEX IF NOT EXISTS idx_recommendations_persona_code ON recommendations (persona_code);
        CREATE INDEX IF NOT EXISTS idx_recommendations_session_persona ON recommendations (session_id, persona_code);
    END IF;
END $$;

-- research_cache indexes (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'research_cache') THEN
        CREATE INDEX IF NOT EXISTS idx_research_cache_category_date ON research_cache (category, research_date DESC);
    END IF;
END $$;

-- research_metrics indexes (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'research_metrics') THEN
        CREATE INDEX IF NOT EXISTS idx_research_metrics_depth_success ON research_metrics (research_depth, success);
    END IF;
END $$;

-- sub_problem_results indexes (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sub_problem_results') THEN
        CREATE INDEX IF NOT EXISTS idx_sub_problem_results_created_at ON sub_problem_results (session_id, created_at DESC);
    END IF;
END $$;

-- ========================================================================
-- Migration 6: Embedding Column for Contributions (688378ba7cfa)
-- ========================================================================

-- Add embedding column (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contributions' AND column_name = 'embedding'
    ) THEN
        ALTER TABLE contributions ADD COLUMN embedding vector(1024);
    END IF;
END $$;

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_contributions_embedding
ON contributions
USING hnsw (embedding vector_cosine_ops);

-- ========================================================================
-- Migration 7: Cost Attribution Columns for api_costs (b0d1100890ab)
-- ========================================================================

-- Add cost attribution columns (idempotent)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'api_costs' AND column_name = 'contribution_id'
    ) THEN
        ALTER TABLE api_costs ADD COLUMN contribution_id INTEGER;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'api_costs' AND column_name = 'recommendation_id'
    ) THEN
        ALTER TABLE api_costs ADD COLUMN recommendation_id INTEGER;
    END IF;
END $$;

-- Add foreign key for contributions (idempotent)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_api_costs_contribution_id'
        AND table_name = 'api_costs'
    ) THEN
        ALTER TABLE api_costs DROP CONSTRAINT fk_api_costs_contribution_id;
    END IF;

    ALTER TABLE api_costs
    ADD CONSTRAINT fk_api_costs_contribution_id
    FOREIGN KEY (contribution_id) REFERENCES contributions(id) ON DELETE SET NULL;
END $$;

-- Add foreign key for recommendations (only if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'recommendations') THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_api_costs_recommendation_id'
            AND table_name = 'api_costs'
        ) THEN
            ALTER TABLE api_costs DROP CONSTRAINT fk_api_costs_recommendation_id;
        END IF;

        ALTER TABLE api_costs
        ADD CONSTRAINT fk_api_costs_recommendation_id
        FOREIGN KEY (recommendation_id) REFERENCES recommendations(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Create indexes for cost analytics
CREATE INDEX IF NOT EXISTS idx_api_costs_contribution ON api_costs (contribution_id);
CREATE INDEX IF NOT EXISTS idx_api_costs_recommendation ON api_costs (recommendation_id);

-- ========================================================================
-- Update Alembic Version Tracking
-- ========================================================================

DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('b0d1100890ab');

-- ========================================================================
-- COMMIT TRANSACTION
-- ========================================================================

COMMIT;

-- ========================================================================
-- POST-DEPLOYMENT VERIFICATION
-- ========================================================================
-- Run these queries after deployment to verify success:
--
-- 1. Check migration version:
--    SELECT version_num FROM alembic_version;
--    -- Expected: b0d1100890ab
--
-- 2. Verify contributions table schema:
--    \d contributions
--    -- Should have: user_id, embedding columns
--
-- 3. Verify RLS policies:
--    SELECT tablename, policyname FROM pg_policies
--    WHERE tablename IN ('contributions', 'api_costs', 'session_events', 'session_tasks', 'waitlist');
--    -- Should have user_isolation and admin_access policies
--
-- 4. Verify indexes:
--    SELECT tablename, indexname FROM pg_indexes
--    WHERE schemaname = 'public'
--    AND tablename IN ('contributions', 'api_costs', 'session_events', 'session_tasks')
--    ORDER BY tablename, indexname;
--
-- 5. Test contribution persistence (after code deployment):
--    -- Run a test deliberation
--    -- Check: SELECT COUNT(*) FROM contributions;
--    -- Should be > 0 after first deliberation
--
-- ========================================================================
-- ROLLBACK PROCEDURE (IF NEEDED)
-- ========================================================================
-- If deployment fails or issues arise:
--
-- 1. Restore from backup:
--    pg_restore -U bo1 -d boardofone -c /tmp/backup_before_migration_<timestamp>.dump
--
-- 2. Verify data integrity:
--    SELECT COUNT(*) FROM sessions;
--    SELECT COUNT(*) FROM api_costs;
--    -- Counts should match pre-deployment state
--
-- 3. Check application logs for errors
-- 4. Report issues to development team
--
-- ========================================================================
