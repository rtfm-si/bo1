-- Create umami database for analytics
-- This runs on Postgres startup if database doesn't exist

-- Check if database exists, create if not
SELECT 'CREATE DATABASE umami'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'umami')\gexec

-- Grant privileges to bo1 user
GRANT ALL PRIVILEGES ON DATABASE umami TO bo1;
