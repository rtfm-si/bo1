-- Migration 008: Create session_events and session_tasks tables for persistent storage
-- Date: 2025-01-26
-- Purpose: Enable long-term storage of session events and extracted tasks beyond Redis TTL

-- ============================================================================
-- 1. session_events: Store all deliberation events for historical replay
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_events (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    sequence INTEGER NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Foreign key to sessions table
    CONSTRAINT fk_session_events_session
        FOREIGN KEY (session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE,

    -- Ensure events are unique per session + sequence
    CONSTRAINT unique_session_sequence UNIQUE (session_id, sequence)
);

-- Indexes for fast event retrieval
CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id);
CREATE INDEX IF NOT EXISTS idx_session_events_event_type ON session_events(event_type);
CREATE INDEX IF NOT EXISTS idx_session_events_created_at ON session_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_events_session_sequence ON session_events(session_id, sequence);

-- GIN index for efficient JSONB queries
CREATE INDEX IF NOT EXISTS idx_session_events_data ON session_events USING GIN (data);

-- Comments
COMMENT ON TABLE session_events IS 'Historical event log for all deliberation sessions (replaces Redis-only storage)';
COMMENT ON COLUMN session_events.session_id IS 'Session identifier (matches sessions.id)';
COMMENT ON COLUMN session_events.event_type IS 'Event type (e.g., contribution, synthesis_complete, persona_selected)';
COMMENT ON COLUMN session_events.sequence IS 'Event sequence number within session (for ordering)';
COMMENT ON COLUMN session_events.data IS 'Event payload as JSONB (flexible schema for different event types)';
COMMENT ON COLUMN session_events.created_at IS 'When event occurred';

-- ============================================================================
-- 2. session_tasks: Store extracted tasks from synthesis
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_tasks (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL UNIQUE,
    tasks JSONB NOT NULL,
    total_tasks INTEGER NOT NULL DEFAULT 0,
    extraction_confidence NUMERIC(3,2) NOT NULL DEFAULT 0.0,
    synthesis_sections_analyzed TEXT[] DEFAULT ARRAY[]::TEXT[],
    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    -- Foreign key to sessions table
    CONSTRAINT fk_session_tasks_session
        FOREIGN KEY (session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE,

    -- Validation constraints
    CONSTRAINT check_extraction_confidence CHECK (extraction_confidence >= 0.0 AND extraction_confidence <= 1.0),
    CONSTRAINT check_total_tasks CHECK (total_tasks >= 0)
);

-- Indexes for task retrieval
CREATE INDEX IF NOT EXISTS idx_session_tasks_session_id ON session_tasks(session_id);
CREATE INDEX IF NOT EXISTS idx_session_tasks_extracted_at ON session_tasks(extracted_at DESC);

-- GIN index for JSONB task searches
CREATE INDEX IF NOT EXISTS idx_session_tasks_tasks ON session_tasks USING GIN (tasks);

-- Comments
COMMENT ON TABLE session_tasks IS 'Extracted actionable tasks from session synthesis (cached in Redis, persisted here)';
COMMENT ON COLUMN session_tasks.session_id IS 'Session identifier (matches sessions.id, unique - one extraction per session)';
COMMENT ON COLUMN session_tasks.tasks IS 'Array of ExtractedTask objects as JSONB';
COMMENT ON COLUMN session_tasks.total_tasks IS 'Total number of tasks extracted';
COMMENT ON COLUMN session_tasks.extraction_confidence IS 'AI confidence in task extraction (0.0-1.0)';
COMMENT ON COLUMN session_tasks.synthesis_sections_analyzed IS 'Which synthesis sections were analyzed';
COMMENT ON COLUMN session_tasks.extracted_at IS 'When tasks were extracted';

-- ============================================================================
-- 3. Add synthesis_text column to sessions table
-- ============================================================================

-- Add synthesis_text column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'sessions'
        AND column_name = 'synthesis_text'
    ) THEN
        ALTER TABLE sessions ADD COLUMN synthesis_text TEXT;
        COMMENT ON COLUMN sessions.synthesis_text IS 'Final synthesis XML from synthesize or meta_synthesize node';
    END IF;
END
$$;

-- ============================================================================
-- Migration success confirmation
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✅ Migration 008: session_events, session_tasks tables created successfully';
    RAISE NOTICE '✅ synthesis_text column added to sessions table';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Update event_publisher.py to save events to PostgreSQL';
    RAISE NOTICE '  2. Update extract_tasks endpoint to save/load from PostgreSQL';
    RAISE NOTICE '  3. Update synthesis handlers to save synthesis_text to sessions table';
END
$$;
