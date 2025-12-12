#!/bin/bash
# Backup Verification Script
# Validates backup integrity by testing restore to a temp database
# Usage: ./scripts/verify_backup.sh [backup_file.sql.gz]
#
# If no backup file specified, uses the most recent backup in BACKUP_DIR.
#
# Environment Variables:
#   POSTGRES_HOST       - Database host (default: localhost)
#   POSTGRES_PORT       - Database port (default: 5432)
#   POSTGRES_USER       - Database user (default: bo1)
#   POSTGRES_PASSWORD   - Database password (required)
#   BACKUP_DIR          - Backup directory (default: ./backups/postgres)
#   VERIFY_DB           - Temp database for verification (default: bo1_verify_temp)
#   BACKUP_AGE_KEY_FILE - Path to age private key file (for .age files)
#   (GPG uses default keyring automatically for .gpg files)

set -euo pipefail

# Configuration with defaults
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-bo1}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
VERIFY_DB="${VERIFY_DB:-bo1_verify_temp}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cleanup() {
    log_info "Cleaning up verification database..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d postgres \
        -c "DROP DATABASE IF EXISTS ${VERIFY_DB};" 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT

# Check required environment
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    log_error "POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

# Determine backup file
if [ $# -ge 1 ]; then
    BACKUP_FILE="$1"
else
    # Find most recent backup (encrypted or unencrypted)
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/*.sql.gz* 2>/dev/null | head -1)
    if [ -z "${BACKUP_FILE}" ]; then
        log_error "No backup files found in ${BACKUP_DIR}"
        exit 1
    fi
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Detect encryption method
DECRYPT_METHOD=""
if [[ "${BACKUP_FILE}" =~ \.sql\.gz\.age$ ]]; then
    DECRYPT_METHOD="age"
    if ! command -v age &> /dev/null; then
        log_error "age CLI required for .age files. Install with: brew install age"
        exit 1
    fi
    if [ -z "${BACKUP_AGE_KEY_FILE:-}" ]; then
        log_error "BACKUP_AGE_KEY_FILE environment variable required for .age files"
        exit 1
    fi
    if [ ! -f "${BACKUP_AGE_KEY_FILE}" ]; then
        log_error "Age key file not found: ${BACKUP_AGE_KEY_FILE}"
        exit 1
    fi
elif [[ "${BACKUP_FILE}" =~ \.sql\.gz\.gpg$ ]]; then
    DECRYPT_METHOD="gpg"
    if ! command -v gpg &> /dev/null; then
        log_error "gpg CLI required for .gpg files"
        exit 1
    fi
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
BACKUP_DATE=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "${BACKUP_FILE}" 2>/dev/null || stat -c "%y" "${BACKUP_FILE}" 2>/dev/null | cut -d. -f1)

log_info "Verifying backup: ${BACKUP_FILE}"
log_info "  Size: ${BACKUP_SIZE}"
log_info "  Date: ${BACKUP_DATE}"
if [ -n "${DECRYPT_METHOD}" ]; then
    log_info "  Encryption: ${DECRYPT_METHOD}"
fi
log_info ""

# Step 1: Create temp database
log_info "Step 1/4: Creating verification database..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS ${VERIFY_DB};"

PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "CREATE DATABASE ${VERIFY_DB} OWNER ${POSTGRES_USER};"

# Step 2: Restore backup to temp database (with decryption if needed)
log_info "Step 2/4: Restoring backup to temp database..."
if [ "${DECRYPT_METHOD}" = "age" ]; then
    log_info "  Decrypting with age..."
    age -d -i "${BACKUP_AGE_KEY_FILE}" "${BACKUP_FILE}" | gunzip | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${VERIFY_DB}" \
        --quiet 2>&1 | grep -v "^NOTICE:" || true
elif [ "${DECRYPT_METHOD}" = "gpg" ]; then
    log_info "  Decrypting with GPG..."
    gpg --decrypt "${BACKUP_FILE}" 2>/dev/null | gunzip | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${VERIFY_DB}" \
        --quiet 2>&1 | grep -v "^NOTICE:" || true
else
    gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${VERIFY_DB}" \
        --quiet 2>&1 | grep -v "^NOTICE:" || true
fi

# Step 3: Verify table structure
log_info "Step 3/4: Verifying table structure..."
TABLE_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${VERIFY_DB}" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

TABLE_COUNT=$(echo "${TABLE_COUNT}" | tr -d ' ')

if [ "${TABLE_COUNT}" -eq 0 ]; then
    log_error "Verification FAILED: No tables found in restored backup"
    exit 1
fi

log_info "  Found ${TABLE_COUNT} tables"

# List key tables
log_info "  Key tables present:"
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${VERIFY_DB}" \
    -t -c "SELECT '    - ' || table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name LIMIT 10;"

# Step 4: Verify data integrity (sample row counts)
log_info "Step 4/4: Checking data integrity..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${VERIFY_DB}" \
    -c "
    SELECT
        schemaname || '.' || relname AS table,
        n_live_tup AS rows
    FROM pg_stat_user_tables
    WHERE n_live_tup > 0
    ORDER BY n_live_tup DESC
    LIMIT 5;
    "

log_info ""
log_info "=========================================="
log_info "  BACKUP VERIFICATION: PASSED"
log_info "=========================================="
log_info "  File: $(basename ${BACKUP_FILE})"
log_info "  Tables: ${TABLE_COUNT}"
log_info "  Status: OK"

exit 0
