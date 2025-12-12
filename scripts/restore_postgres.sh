#!/bin/bash
# PostgreSQL Restore Script
# Restores a database from a compressed backup file
# Usage: ./scripts/restore_postgres.sh <backup_file.sql.gz> [--force]
#
# Environment Variables:
#   POSTGRES_HOST       - Database host (default: localhost)
#   POSTGRES_PORT       - Database port (default: 5432)
#   POSTGRES_DB         - Database name (default: boardofone)
#   POSTGRES_USER       - Database user (default: bo1)
#   POSTGRES_PASSWORD   - Database password (required)
#   BACKUP_AGE_KEY_FILE - Path to age private key file (for .age files)
#   (GPG uses default keyring automatically for .gpg files)

set -euo pipefail

# Configuration with defaults
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-boardofone}"
POSTGRES_USER="${POSTGRES_USER:-bo1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check arguments
if [ $# -lt 1 ]; then
    log_error "Usage: $0 <backup_file.sql.gz> [--force]"
    log_info "  backup_file.sql.gz  - Path to the compressed backup file"
    log_info "  --force             - Skip confirmation prompt"
    exit 1
fi

BACKUP_FILE="$1"
FORCE="${2:-}"

# Validate backup file
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Detect encryption and validate file extension
DECRYPT_METHOD=""
if [[ "${BACKUP_FILE}" =~ \.sql\.gz\.age$ ]]; then
    DECRYPT_METHOD="age"
    if ! command -v age &> /dev/null; then
        log_error "age CLI required for .age files. Install with: brew install age"
        exit 1
    fi
    if [ -z "${BACKUP_AGE_KEY_FILE:-}" ]; then
        log_error "BACKUP_AGE_KEY_FILE environment variable required for .age files"
        log_info "  Set to path of your age private key file"
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
elif [[ "${BACKUP_FILE}" =~ \.sql\.gz$ ]]; then
    DECRYPT_METHOD=""
else
    log_error "Backup file must be .sql.gz, .sql.gz.age, or .sql.gz.gpg"
    exit 1
fi

# Check required environment
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    log_error "POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

log_warn "This will restore the database from backup."
log_warn "  Database: ${POSTGRES_DB}"
log_warn "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
log_warn "  Backup: ${BACKUP_FILE}"
if [ -n "${DECRYPT_METHOD}" ]; then
    log_warn "  Decryption: ${DECRYPT_METHOD}"
fi
log_warn ""
log_warn "WARNING: This operation will overwrite the current database!"

if [ "${FORCE}" != "--force" ]; then
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm
    if [ "${confirm}" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
fi

log_info "Starting restore..."

# Drop and recreate database
log_info "Dropping existing database..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"

log_info "Creating fresh database..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d postgres \
    -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

# Restore from backup (with decryption if needed)
log_info "Restoring from backup..."
if [ "${DECRYPT_METHOD}" = "age" ]; then
    log_info "Decrypting with age..."
    age -d -i "${BACKUP_AGE_KEY_FILE}" "${BACKUP_FILE}" | gunzip | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --quiet
elif [ "${DECRYPT_METHOD}" = "gpg" ]; then
    log_info "Decrypting with GPG..."
    gpg --decrypt "${BACKUP_FILE}" 2>/dev/null | gunzip | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --quiet
else
    gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --quiet
fi

log_info "Restore completed successfully"

# Verify restore
TABLE_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

log_info "Verification: ${TABLE_COUNT} tables restored"
