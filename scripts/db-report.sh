#!/bin/bash
# Database monitoring report wrapper
# Automatically finds the active API container in blue-green deployments
#
# Usage: ./db-report.sh [daily|weekly]

set -e

REPORT_TYPE="${1:-daily}"

# Find the active API container (works with blue-green deployment)
find_api_container() {
    # Try common patterns in order of likelihood
    for pattern in "boardofone-api-1" "boardofone-api-blue-1" "boardofone-api-green-1"; do
        if docker ps --format '{{.Names}}' | grep -q "^${pattern}$"; then
            echo "$pattern"
            return 0
        fi
    done

    # Fallback: find any running container with "api" in the name
    docker ps --format '{{.Names}}' | grep -E "boardofone.*api" | head -1
}

CONTAINER=$(find_api_container)

if [ -z "$CONTAINER" ]; then
    echo "$(date): ERROR - Could not find API container" >&2
    exit 1
fi

echo "$(date): Running $REPORT_TYPE report via $CONTAINER"
docker exec "$CONTAINER" python scripts/send_database_report.py "$REPORT_TYPE"
