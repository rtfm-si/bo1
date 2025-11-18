-- =============================================================================
-- PostgreSQL Initialization Script - Create Auth Schema for Supabase
-- =============================================================================
-- This script runs automatically when PostgreSQL container is first initialized
-- It creates the 'auth' schema required by Supabase GoTrue for user authentication
--
-- PostgreSQL runs all *.sql files in /docker-entrypoint-initdb.d/ on first start
-- =============================================================================

-- Create auth schema (required by Supabase GoTrue)
CREATE SCHEMA IF NOT EXISTS auth;

-- Grant necessary permissions to the application user
GRANT USAGE ON SCHEMA auth TO bo1;
GRANT CREATE ON SCHEMA auth TO bo1;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO bo1;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO bo1;

-- Set default privileges for future tables/sequences created by Supabase migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON TABLES TO bo1;
ALTER DEFAULT PRIVILEGES IN SCHEMA auth GRANT ALL ON SEQUENCES TO bo1;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Auth schema created successfully for Supabase GoTrue';
END $$;
