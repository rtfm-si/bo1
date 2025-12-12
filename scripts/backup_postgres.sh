#!/bin/bash
# PostgreSQL Backup Script
# Creates compressed backups with tiered retention:
#   - Daily backups: retained 7 days (default)
#   - Weekly backups (Sunday): retained 30 days
#   - Monthly backups (1st of month): retained 90 days
#
# Usage: ./scripts/backup_postgres.sh [--upload]
#
# Environment Variables:
#   POSTGRES_HOST            - Database host (default: localhost)
#   POSTGRES_PORT            - Database port (default: 5432)
#   POSTGRES_DB              - Database name (default: boardofone)
#   POSTGRES_USER            - Database user (default: bo1)
#   POSTGRES_PASSWORD        - Database password (required)
#   BACKUP_DIR               - Local backup directory (default: ./backups/postgres)
#   BACKUP_RETENTION_DAILY   - Days to retain daily backups (default: 7)
#   BACKUP_RETENTION_WEEKLY  - Days to retain weekly backups (default: 30)
#   BACKUP_RETENTION_MONTHLY - Days to retain monthly backups (default: 90)
#   DO_SPACES_KEY            - DigitalOcean Spaces access key (for --upload)
#   DO_SPACES_SECRET         - DigitalOcean Spaces secret key (for --upload)
#   DO_SPACES_BUCKET         - DigitalOcean Spaces bucket name (for --upload)
#   DO_SPACES_REGION         - DigitalOcean Spaces region (for --upload)
#   BACKUP_AGE_RECIPIENT     - age public key for encryption (optional)
#   BACKUP_GPG_RECIPIENT     - GPG key ID for encryption (optional, fallback)

set -euo pipefail

# Configuration with defaults
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-boardofone}"
POSTGRES_USER="${POSTGRES_USER:-bo1}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"

# Tiered retention configuration
BACKUP_RETENTION_DAILY="${BACKUP_RETENTION_DAILY:-7}"
BACKUP_RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-30}"
BACKUP_RETENTION_MONTHLY="${BACKUP_RETENTION_MONTHLY:-90}"

# Timestamp for backup file
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Determine backup tier based on day
get_backup_tier() {
    local day_of_week=$(date +%u)  # 1=Mon, 7=Sun
    local day_of_month=$(date +%d)

    if [ "$day_of_month" = "01" ]; then
        echo "monthly"
    elif [ "$day_of_week" = "7" ]; then
        echo "weekly"
    else
        echo "daily"
    fi
}

BACKUP_TIER=$(get_backup_tier)
BACKUP_FILE_BASE="${BACKUP_DIR}/${POSTGRES_DB}-${TIMESTAMP}"

# Add tier suffix for weekly/monthly backups
if [ "${BACKUP_TIER}" != "daily" ]; then
    BACKUP_FILE_BASE="${BACKUP_FILE_BASE}-${BACKUP_TIER}"
fi

# Determine encryption method
ENCRYPT_METHOD=""
if [ -n "${BACKUP_AGE_RECIPIENT:-}" ]; then
    if command -v age &> /dev/null; then
        ENCRYPT_METHOD="age"
        BACKUP_FILE="${BACKUP_FILE_BASE}.sql.gz.age"
    else
        log_warn "age CLI not found but BACKUP_AGE_RECIPIENT set - skipping encryption"
        log_warn "Install with: brew install age"
        BACKUP_FILE="${BACKUP_FILE_BASE}.sql.gz"
    fi
elif [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
    if command -v gpg &> /dev/null; then
        ENCRYPT_METHOD="gpg"
        BACKUP_FILE="${BACKUP_FILE_BASE}.sql.gz.gpg"
    else
        log_warn "gpg CLI not found but BACKUP_GPG_RECIPIENT set - skipping encryption"
        BACKUP_FILE="${BACKUP_FILE_BASE}.sql.gz"
    fi
else
    BACKUP_FILE="${BACKUP_FILE_BASE}.sql.gz"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check required environment
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    log_error "POSTGRES_PASSWORD environment variable is required"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

log_info "Starting PostgreSQL backup..."
log_info "  Database: ${POSTGRES_DB}"
log_info "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
log_info "  Tier: ${BACKUP_TIER}"
log_info "  Output: ${BACKUP_FILE}"
if [ -n "${ENCRYPT_METHOD}" ]; then
    log_info "  Encryption: ${ENCRYPT_METHOD}"
fi

# Perform backup with pg_dump, optionally encrypted
# Uses streaming to handle large databases efficiently
if [ "${ENCRYPT_METHOD}" = "age" ]; then
    log_info "Encrypting backup with age..."
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --format=plain \
        --verbose \
        2>&1 | gzip | age -r "${BACKUP_AGE_RECIPIENT}" > "${BACKUP_FILE}"
elif [ "${ENCRYPT_METHOD}" = "gpg" ]; then
    log_info "Encrypting backup with GPG..."
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --format=plain \
        --verbose \
        2>&1 | gzip | gpg --encrypt --recipient "${BACKUP_GPG_RECIPIENT}" > "${BACKUP_FILE}"
else
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST}" \
        -p "${POSTGRES_PORT}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --no-owner \
        --no-privileges \
        --format=plain \
        --verbose \
        2>&1 | gzip > "${BACKUP_FILE}"
fi

# Check if backup was successful
if [ ! -f "${BACKUP_FILE}" ] || [ ! -s "${BACKUP_FILE}" ]; then
    log_error "Backup failed - output file is empty or missing"
    exit 1
fi

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log_info "Backup completed successfully"
log_info "  Size: ${BACKUP_SIZE}"

# Upload to DO Spaces if --upload flag is provided
if [ "${1:-}" = "--upload" ]; then
    if [ -z "${DO_SPACES_KEY:-}" ] || [ -z "${DO_SPACES_SECRET:-}" ] || \
       [ -z "${DO_SPACES_BUCKET:-}" ] || [ -z "${DO_SPACES_REGION:-}" ]; then
        log_warn "DO Spaces credentials not configured - skipping upload"
    else
        log_info "Uploading to DigitalOcean Spaces..."

        SPACES_ENDPOINT="https://${DO_SPACES_REGION}.digitaloceanspaces.com"
        REMOTE_PATH="backups/postgres/$(basename ${BACKUP_FILE})"

        # Use s3cmd or aws cli for upload
        if command -v aws &> /dev/null; then
            AWS_ACCESS_KEY_ID="${DO_SPACES_KEY}" \
            AWS_SECRET_ACCESS_KEY="${DO_SPACES_SECRET}" \
            aws s3 cp "${BACKUP_FILE}" "s3://${DO_SPACES_BUCKET}/${REMOTE_PATH}" \
                --endpoint-url "${SPACES_ENDPOINT}"
            log_info "Uploaded to: ${SPACES_ENDPOINT}/${DO_SPACES_BUCKET}/${REMOTE_PATH}"

            # Remote cleanup (DO Spaces) - tiered retention
            log_info "Cleaning up old remote backups..."
            REMOTE_PREFIX="backups/postgres/${POSTGRES_DB}-"

            # Function to clean remote backups by tier
            cleanup_remote_tier() {
                local tier_pattern="$1"
                local retention_days="$2"
                local tier_name="$3"
                local cutoff_date=$(date -v-${retention_days}d +%Y%m%d 2>/dev/null || date -d "-${retention_days} days" +%Y%m%d)

                # List remote backups matching pattern
                local remote_files=$(AWS_ACCESS_KEY_ID="${DO_SPACES_KEY}" \
                    AWS_SECRET_ACCESS_KEY="${DO_SPACES_SECRET}" \
                    aws s3 ls "s3://${DO_SPACES_BUCKET}/backups/postgres/" \
                    --endpoint-url "${SPACES_ENDPOINT}" 2>/dev/null | \
                    grep "${tier_pattern}" | awk '{print $4}' || true)

                local deleted=0
                for file in ${remote_files}; do
                    # Extract date from filename (format: dbname-YYYYMMDD-HHMMSS...)
                    local file_date=$(echo "$file" | sed -E 's/.*-([0-9]{8})-[0-9]{6}.*/\1/')
                    if [ -n "${file_date}" ] && [ "${file_date}" -lt "${cutoff_date}" ] 2>/dev/null; then
                        AWS_ACCESS_KEY_ID="${DO_SPACES_KEY}" \
                        AWS_SECRET_ACCESS_KEY="${DO_SPACES_SECRET}" \
                        aws s3 rm "s3://${DO_SPACES_BUCKET}/backups/postgres/${file}" \
                            --endpoint-url "${SPACES_ENDPOINT}" 2>/dev/null && deleted=$((deleted + 1))
                    fi
                done
                if [ "${deleted}" -gt 0 ]; then
                    log_info "  Deleted ${deleted} remote ${tier_name} backup(s) older than ${retention_days} days"
                fi
            }

            # Clean daily backups (no tier suffix)
            cleanup_remote_tier "\.sql\.gz" "${BACKUP_RETENTION_DAILY}" "daily"
            # Clean weekly backups
            cleanup_remote_tier "-weekly\.sql\.gz" "${BACKUP_RETENTION_WEEKLY}" "weekly"
            # Clean monthly backups
            cleanup_remote_tier "-monthly\.sql\.gz" "${BACKUP_RETENTION_MONTHLY}" "monthly"
        else
            log_warn "aws CLI not found - skipping upload (install with: pip install awscli)"
        fi
    fi
fi

# Clean up old backups (local) - tiered retention
log_info "Cleaning up old backups (tiered retention)..."
TOTAL_DELETED=0

# Clean daily backups (no tier suffix) older than BACKUP_RETENTION_DAILY days
# Match files without -weekly or -monthly suffix
DAILY_DELETED=$(find "${BACKUP_DIR}" \( -name "${POSTGRES_DB}-*.sql.gz" -o -name "${POSTGRES_DB}-*.sql.gz.age" -o -name "${POSTGRES_DB}-*.sql.gz.gpg" \) \
    ! -name "*-weekly*" ! -name "*-monthly*" -type f -mtime +${BACKUP_RETENTION_DAILY} -delete -print 2>/dev/null | wc -l)
if [ "${DAILY_DELETED}" -gt 0 ]; then
    log_info "  Deleted ${DAILY_DELETED} daily backup(s) older than ${BACKUP_RETENTION_DAILY} days"
    TOTAL_DELETED=$((TOTAL_DELETED + DAILY_DELETED))
fi

# Clean weekly backups older than BACKUP_RETENTION_WEEKLY days
WEEKLY_DELETED=$(find "${BACKUP_DIR}" \( -name "*-weekly.sql.gz" -o -name "*-weekly.sql.gz.age" -o -name "*-weekly.sql.gz.gpg" \) \
    -type f -mtime +${BACKUP_RETENTION_WEEKLY} -delete -print 2>/dev/null | wc -l)
if [ "${WEEKLY_DELETED}" -gt 0 ]; then
    log_info "  Deleted ${WEEKLY_DELETED} weekly backup(s) older than ${BACKUP_RETENTION_WEEKLY} days"
    TOTAL_DELETED=$((TOTAL_DELETED + WEEKLY_DELETED))
fi

# Clean monthly backups older than BACKUP_RETENTION_MONTHLY days
MONTHLY_DELETED=$(find "${BACKUP_DIR}" \( -name "*-monthly.sql.gz" -o -name "*-monthly.sql.gz.age" -o -name "*-monthly.sql.gz.gpg" \) \
    -type f -mtime +${BACKUP_RETENTION_MONTHLY} -delete -print 2>/dev/null | wc -l)
if [ "${MONTHLY_DELETED}" -gt 0 ]; then
    log_info "  Deleted ${MONTHLY_DELETED} monthly backup(s) older than ${BACKUP_RETENTION_MONTHLY} days"
    TOTAL_DELETED=$((TOTAL_DELETED + MONTHLY_DELETED))
fi

if [ "${TOTAL_DELETED}" -eq 0 ]; then
    log_info "  No old backups to delete"
fi

# List current backups (encrypted and unencrypted)
log_info "Current backups:"
ls -lh "${BACKUP_DIR}"/*.sql.gz* 2>/dev/null || log_info "  (none)"

log_info "Backup process complete"
