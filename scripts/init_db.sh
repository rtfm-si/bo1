#!/bin/bash
# Initialize database for new deployments using consolidated baseline
#
# Usage:
#   ./scripts/init_db.sh [--fresh]
#
# Options:
#   --fresh   Drop existing database and recreate (DANGEROUS - dev only)
#
# For existing deployments, use: alembic upgrade head

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if --fresh flag is passed
if [ "$1" = "--fresh" ]; then
    echo "WARNING: This will drop and recreate the database!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborted."
        exit 1
    fi

    echo "Dropping existing database..."
    docker compose exec postgres psql -U bo1 -d postgres -c "DROP DATABASE IF EXISTS boardofone"
    docker compose exec postgres psql -U bo1 -d postgres -c "CREATE DATABASE boardofone"
fi

# Check current alembic state
echo "Checking database state..."
CURRENT=$(docker compose exec bo1 uv run alembic current 2>/dev/null | grep -E '^[a-f0-9]' || echo "")

if [ -n "$CURRENT" ]; then
    echo "Database already has migrations applied: $CURRENT"
    echo "Use 'alembic upgrade head' for incremental updates."
    exit 0
fi

# Apply consolidated baseline for fresh database
echo "Applying consolidated baseline schema..."
docker compose exec bo1 uv run alembic upgrade 0001_consolidated_baseline@consolidated

# Stamp as if all incremental migrations were applied
echo "Stamping to current head..."
docker compose exec bo1 uv run alembic stamp d1_add_session_counts

echo "Database initialized successfully!"
echo "Current version:"
docker compose exec bo1 uv run alembic current
