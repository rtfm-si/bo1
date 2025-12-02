#!/bin/bash
# Setup database monitoring cron jobs on production server
# Run this script once on the production server to configure automated reports

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up database monitoring cron jobs...${NC}"

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER_SCRIPT="$SCRIPT_DIR/db-report.sh"

# Make sure wrapper script is executable
chmod +x "$WRAPPER_SCRIPT"

# Create the cron entries (use wrapper script that auto-detects active container)
CRON_DAILY="0 9 * * * $WRAPPER_SCRIPT daily >> /var/log/db-monitoring.log 2>&1"
CRON_WEEKLY="0 10 * * 1 $WRAPPER_SCRIPT weekly >> /var/log/db-monitoring.log 2>&1"

# Check if cron jobs already exist
EXISTING=$(crontab -l 2>/dev/null || echo "")

if echo "$EXISTING" | grep -q "send_database_report.py"; then
    echo -e "${YELLOW}Database monitoring cron jobs already exist. Replacing...${NC}"
    # Remove existing database monitoring entries
    EXISTING=$(echo "$EXISTING" | grep -v "send_database_report.py")
fi

# Add the new cron jobs
echo "$EXISTING
# Database monitoring reports (added by setup-db-monitoring-cron.sh)
$CRON_DAILY
$CRON_WEEKLY" | crontab -

echo -e "${GREEN}Cron jobs installed successfully!${NC}"
echo ""
echo "Scheduled jobs:"
echo "  - Daily report: 9:00 AM UTC"
echo "  - Weekly report: Monday 10:00 AM UTC"
echo ""
echo "Logs: /var/log/db-monitoring.log"
echo ""
echo "To test immediately, run:"
echo "  $WRAPPER_SCRIPT daily"
