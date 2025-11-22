-- SuperTokens Schema Initialization
-- This schema is used by SuperTokens Core for authentication tables

-- Create supertokens schema
CREATE SCHEMA IF NOT EXISTS supertokens;

-- Grant permissions to bo1 user
GRANT ALL PRIVILEGES ON SCHEMA supertokens TO bo1;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA supertokens TO bo1;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA supertokens TO bo1;
ALTER DEFAULT PRIVILEGES IN SCHEMA supertokens GRANT ALL ON TABLES TO bo1;
ALTER DEFAULT PRIVILEGES IN SCHEMA supertokens GRANT ALL ON SEQUENCES TO bo1;

-- Enable pgvector extension for embeddings (used by research cache)
CREATE EXTENSION IF NOT EXISTS vector;

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'SuperTokens schema created successfully';
END
$$;
