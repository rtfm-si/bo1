-- Migration 009: Ensure sessions table exists with proper schema
-- Date: 2025-01-27
-- Purpose: Create or update sessions table to enable persistent storage beyond Redis TTL

-- ============================================================================
-- 1. Create sessions table if it doesn't exist
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    problem_statement TEXT NOT NULL,
    problem_context JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    phase VARCHAR(50),
    total_cost NUMERIC(10,4) DEFAULT 0.0,
    round_number INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    synthesis_text TEXT,
    final_recommendation TEXT
);

-- ============================================================================
-- 2. Create indexes for fast queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_user_status ON sessions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON sessions(user_id, created_at DESC);

-- ============================================================================
-- 3. Add helpful columns if they don't exist
-- ============================================================================

DO $$
BEGIN
    -- Add synthesis_text column if it doesn't exist (for backwards compatibility)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'sessions'
        AND column_name = 'synthesis_text'
    ) THEN
        ALTER TABLE sessions ADD COLUMN synthesis_text TEXT;
        COMMENT ON COLUMN sessions.synthesis_text IS 'Final synthesis XML from synthesize or meta_synthesize node';
    END IF;

    -- Add final_recommendation column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'sessions'
        AND column_name = 'final_recommendation'
    ) THEN
        ALTER TABLE sessions ADD COLUMN final_recommendation TEXT;
        COMMENT ON COLUMN sessions.final_recommendation IS 'Final recommendation from deliberation';
    END IF;

    -- Ensure problem_context is JSONB for better querying
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'sessions'
        AND column_name = 'problem_context'
        AND data_type = 'json'
    ) THEN
        -- Convert json to jsonb for better performance
        ALTER TABLE sessions ALTER COLUMN problem_context TYPE JSONB USING problem_context::jsonb;
    END IF;

    -- Ensure status has a default value
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'sessions'
        AND column_name = 'status'
        AND column_default IS NULL
    ) THEN
        ALTER TABLE sessions ALTER COLUMN status SET DEFAULT 'created';
    END IF;
END
$$;

-- ============================================================================
-- 4. Add comments for documentation
-- ============================================================================

COMMENT ON TABLE sessions IS 'Deliberation sessions - primary source of truth (Redis is cache only)';
COMMENT ON COLUMN sessions.id IS 'Session identifier (e.g., bo1_uuid)';
COMMENT ON COLUMN sessions.user_id IS 'User who created the session (from SuperTokens)';
COMMENT ON COLUMN sessions.problem_statement IS 'Original problem statement';
COMMENT ON COLUMN sessions.problem_context IS 'Additional context as JSONB';
COMMENT ON COLUMN sessions.status IS 'Session status: created, running, completed, failed, killed, deleted';
COMMENT ON COLUMN sessions.phase IS 'Current deliberation phase';
COMMENT ON COLUMN sessions.total_cost IS 'Total cost in USD';
COMMENT ON COLUMN sessions.round_number IS 'Current round number';
COMMENT ON COLUMN sessions.created_at IS 'When session was created';
COMMENT ON COLUMN sessions.updated_at IS 'When session was last updated';

-- ============================================================================
-- Migration success confirmation
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 009: sessions table ready for persistent storage';
    RAISE NOTICE '✅ Indexes created: user_id, created_at, status';
    RAISE NOTICE '✅ Sessions will now persist beyond Redis 24-hour TTL';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Update sessions.py to save to PostgreSQL on creation';
    RAISE NOTICE '  2. Update sessions.py to query PostgreSQL for listing';
    RAISE NOTICE '  3. Update event_collector.py to update session status on completion';
END
$$;
