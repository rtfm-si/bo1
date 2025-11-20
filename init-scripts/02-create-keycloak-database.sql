-- =============================================================================
-- Keycloak Database Initialization Script
-- =============================================================================
-- Creates the 'keycloak' database for Keycloak authentication server
-- This runs automatically when PostgreSQL container starts for the first time
--
-- NOTE: PostgreSQL init scripts run as postgres superuser
-- =============================================================================

-- Create keycloak database (only if it doesn't exist)
SELECT 'CREATE DATABASE keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec

-- Grant all privileges to bo1 user (used by Keycloak)
GRANT ALL PRIVILEGES ON DATABASE keycloak TO bo1;

-- Connect to keycloak database to set up schema
\c keycloak

-- Grant schema creation privileges
GRANT CREATE ON SCHEMA public TO bo1;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bo1;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO bo1;

-- Log completion
\echo 'Keycloak database created successfully'
