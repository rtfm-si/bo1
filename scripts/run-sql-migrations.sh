#!/bin/bash
# =============================================================================
# SQL Migration Runner - Apply standalone SQL migrations safely
# =============================================================================
# Purpose: Run SQL migration files in bo1/database/migrations/ directory
# Usage: ./scripts/run-sql-migrations.sh [--dry-run]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MIGRATIONS_DIR="$PROJECT_ROOT/bo1/database/migrations"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Dry run flag
DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}\n"
fi

echo "==============================================="
echo "SQL Migration Runner"
echo "==============================================="
echo ""

# Check if migrations directory exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}Error: Migrations directory not found: $MIGRATIONS_DIR${NC}"
    exit 1
fi

# Check DATABASE_URL environment variable
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL environment variable not set${NC}"
    echo "Example: postgresql://bo1:password@localhost:5432/boardofone"
    exit 1
fi

echo -e "${BLUE}Database URL: ${DATABASE_URL%@*}@***${NC}"
echo ""

# Create migration tracking table if it doesn't exist
create_tracking_table() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would create sql_migrations table${NC}"
        return
    fi

    echo -e "${BLUE}Ensuring migration tracking table exists...${NC}"

    psql "$DATABASE_URL" <<EOF
-- Create tracking table for SQL migrations (separate from Alembic)
CREATE TABLE IF NOT EXISTS sql_migrations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_sql_migrations_filename ON sql_migrations(filename);
CREATE INDEX IF NOT EXISTS idx_sql_migrations_applied_at ON sql_migrations(applied_at DESC);

COMMENT ON TABLE sql_migrations IS 'Tracking table for standalone SQL migrations (not managed by Alembic)';
COMMENT ON COLUMN sql_migrations.filename IS 'Migration filename (e.g., 007_create_waitlist_table.sql)';
COMMENT ON COLUMN sql_migrations.checksum IS 'SHA-256 checksum of migration file for integrity verification';
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Migration tracking table ready${NC}\n"
    else
        echo -e "${RED}Failed to create tracking table${NC}"
        exit 1
    fi
}

# Check if migration has been applied
is_migration_applied() {
    local filename=$1

    if [ "$DRY_RUN" = true ]; then
        return 1  # Pretend not applied in dry run
    fi

    local count=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM sql_migrations WHERE filename = '$filename' AND success = true;")

    if [ "$count" -gt 0 ]; then
        return 0  # Already applied
    else
        return 1  # Not applied
    fi
}

# Calculate file checksum
calculate_checksum() {
    local file=$1

    if command -v sha256sum &> /dev/null; then
        sha256sum "$file" | awk '{print $1}'
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$file" | awk '{print $1}'
    else
        echo "NOCHECKSUM"
    fi
}

# Apply a single migration
apply_migration() {
    local filepath=$1
    local filename=$(basename "$filepath")

    echo -e "${BLUE}Processing: $filename${NC}"

    # Check if already applied
    if is_migration_applied "$filename"; then
        echo -e "${GREEN}  Already applied${NC}"
        return 0
    fi

    # Calculate checksum
    local checksum=$(calculate_checksum "$filepath")
    echo -e "  Checksum: $checksum"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}  [DRY RUN] Would apply migration${NC}"
        echo -e "${YELLOW}  SQL Preview:${NC}"
        head -20 "$filepath" | sed 's/^/    /'
        echo -e "    ..."
        return 0
    fi

    # Apply migration
    echo -e "  ${YELLOW}Applying migration...${NC}"

    if psql "$DATABASE_URL" -f "$filepath" 2>&1 | tee /tmp/migration.log; then
        # Record success
        psql "$DATABASE_URL" -c "INSERT INTO sql_migrations (filename, checksum, success) VALUES ('$filename', '$checksum', true);" > /dev/null
        echo -e "${GREEN}  Successfully applied${NC}\n"
        return 0
    else
        # Record failure
        psql "$DATABASE_URL" -c "INSERT INTO sql_migrations (filename, checksum, success) VALUES ('$filename', '$checksum', false);" > /dev/null 2>&1 || true
        echo -e "${RED}  Failed to apply migration${NC}"
        echo -e "${RED}  See /tmp/migration.log for details${NC}\n"
        return 1
    fi
}

# Main execution
main() {
    # Create tracking table
    create_tracking_table

    # Find all SQL migration files
    migration_files=$(find "$MIGRATIONS_DIR" -name "*.sql" -type f | sort)

    if [ -z "$migration_files" ]; then
        echo -e "${YELLOW}No SQL migration files found in $MIGRATIONS_DIR${NC}"
        exit 0
    fi

    echo -e "${BLUE}Found $(echo "$migration_files" | wc -l) SQL migration file(s)${NC}\n"

    # Apply each migration
    failed_count=0
    applied_count=0
    skipped_count=0

    for migration in $migration_files; do
        if apply_migration "$migration"; then
            if is_migration_applied "$(basename "$migration")"; then
                skipped_count=$((skipped_count + 1))
            else
                applied_count=$((applied_count + 1))
            fi
        else
            failed_count=$((failed_count + 1))
            echo -e "${RED}Migration failed: $(basename "$migration")${NC}"
            echo -e "${RED}Aborting remaining migrations${NC}\n"
            exit 1
        fi
    done

    # Summary
    echo "==============================================="
    echo "Migration Summary"
    echo "==============================================="
    echo -e "${GREEN}Applied: $applied_count${NC}"
    echo -e "${BLUE}Skipped (already applied): $skipped_count${NC}"
    echo -e "${RED}Failed: $failed_count${NC}"

    if [ $failed_count -eq 0 ]; then
        echo -e "\n${GREEN}All migrations completed successfully${NC}"
        exit 0
    else
        echo -e "\n${RED}Some migrations failed${NC}"
        exit 1
    fi
}

# Run main function
main
