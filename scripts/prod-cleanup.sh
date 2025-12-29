#!/bin/bash
# =============================================================================
# Production Cleanup Script
# Run daily via cron to prevent disk/memory issues
# =============================================================================
set -e

LOG_FILE="/var/log/bo1-cleanup.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log "=== Starting Bo1 Production Cleanup ==="

# -----------------------------------------------------------------------------
# 1. Docker Containers & Volumes Cleanup
# -----------------------------------------------------------------------------
log "1. Docker containers/volumes cleanup..."

# Remove stopped containers
STOPPED=$(docker container prune -f 2>/dev/null | tail -1)
log "   Stopped containers: $STOPPED"

# Remove unused volumes (not attached to containers)
VOLUMES=$(docker volume prune -f 2>/dev/null | tail -1)
log "   Unused volumes: $VOLUMES"

# Remove build cache older than 7 days
BUILD_CACHE=$(docker builder prune -f --filter "until=168h" 2>/dev/null | tail -1 || echo "none")
log "   Build cache (>7d): $BUILD_CACHE"

# Remove unused networks
NETWORKS=$(docker network prune -f 2>/dev/null | tail -1)
log "   Unused networks: $NETWORKS"

# -----------------------------------------------------------------------------
# 2. Log Cleanup
# -----------------------------------------------------------------------------
log "2. Log cleanup..."

# Rotate and compress old logs
if [ -d "/var/log/bo1" ]; then
    find /var/log/bo1 -name "*.log" -mtime +7 -exec gzip {} \;
    find /var/log/bo1 -name "*.gz" -mtime +30 -delete
    log "   Bo1 logs rotated/cleaned"
fi

# Clean Docker container logs (JSON logs can grow large)
for container_id in $(docker ps -q 2>/dev/null); do
    log_path=$(docker inspect --format='{{.LogPath}}' "$container_id" 2>/dev/null)
    if [ -f "$log_path" ]; then
        size=$(stat -f%z "$log_path" 2>/dev/null || stat --printf="%s" "$log_path" 2>/dev/null)
        if [ "$size" -gt 104857600 ]; then  # > 100MB
            truncate -s 50M "$log_path" 2>/dev/null || true
            log "   Truncated large log for container: $container_id"
        fi
    fi
done

# Clean system journal logs older than 7 days
if command -v journalctl &> /dev/null; then
    journalctl --vacuum-time=7d 2>/dev/null || true
    log "   System journal vacuumed"
fi

# -----------------------------------------------------------------------------
# 3. Temp File Cleanup
# -----------------------------------------------------------------------------
log "3. Temp file cleanup..."

# Clean /tmp files older than 3 days
find /tmp -type f -mtime +3 -delete 2>/dev/null || true
find /tmp -type d -empty -mtime +3 -delete 2>/dev/null || true
log "   /tmp cleaned"

# Clean apt cache
if command -v apt-get &> /dev/null; then
    apt-get clean 2>/dev/null || true
    log "   apt cache cleaned"
fi

# -----------------------------------------------------------------------------
# 4. Zombie Process Cleanup
# -----------------------------------------------------------------------------
log "4. Checking for zombie processes..."

ZOMBIES=$(ps aux | awk '{ if ($8 == "Z") print $2 }')
if [ -n "$ZOMBIES" ]; then
    log "   Found zombie processes: $ZOMBIES"
    # Zombies can't be killed directly, but we can notify
    # They'll be cleaned when parent exits
    for pid in $ZOMBIES; do
        ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
        if [ -n "$ppid" ] && [ "$ppid" -gt 1 ]; then
            log "   Zombie PID $pid has parent $ppid"
        fi
    done
else
    log "   No zombie processes found"
fi

# -----------------------------------------------------------------------------
# 5. Static Assets Cleanup
# -----------------------------------------------------------------------------
log "5. Static assets cleanup..."

# Clean old static asset directories (keep current blue/green only)
if [ -d "/var/www/boardofone" ]; then
    # Remove old static directories (not blue or green)
    find /var/www/boardofone -maxdepth 1 -type d -name "static-*" \
        ! -name "static-blue" ! -name "static-green" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    log "   Old static directories cleaned"

    # Report sizes
    BLUE_SIZE=$(du -sh /var/www/boardofone/static-blue 2>/dev/null | cut -f1 || echo "N/A")
    GREEN_SIZE=$(du -sh /var/www/boardofone/static-green 2>/dev/null | cut -f1 || echo "N/A")
    log "   Static assets: blue=$BLUE_SIZE, green=$GREEN_SIZE"
fi

# -----------------------------------------------------------------------------
# 6. Docker Images Cleanup (aggressive for non-GHCR images)
# -----------------------------------------------------------------------------
log "6. Docker images cleanup..."

# Remove images not from GHCR (old local builds)
docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | \
    grep -v "ghcr.io" | grep -v "<none>" | \
    while read image id; do
        # Skip if image is in use
        if ! docker ps -q --filter "ancestor=$id" | grep -q .; then
            docker rmi "$id" 2>/dev/null && log "   Removed old local image: $image" || true
        fi
    done

# Prune dangling images
DANGLING=$(docker image prune -f 2>/dev/null | tail -1)
log "   Dangling images: $DANGLING"

# -----------------------------------------------------------------------------
# 7. Disk Usage Report
# -----------------------------------------------------------------------------
log "7. Disk usage report..."

DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
log "   Root disk usage: $DISK_USAGE"

DOCKER_USAGE=$(docker system df 2>/dev/null | head -5)
log "   Docker disk usage:"
echo "$DOCKER_USAGE" | while read line; do
    log "     $line"
done

# -----------------------------------------------------------------------------
# 8. Memory Report
# -----------------------------------------------------------------------------
log "8. Memory report..."

MEM_FREE=$(free -m | awk '/^Mem:/{print $7}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_PERCENT=$((100 - (MEM_FREE * 100 / MEM_TOTAL)))
log "   Memory: ${MEM_FREE}MB free of ${MEM_TOTAL}MB (${MEM_PERCENT}% used)"

# Alert if memory is critically low
if [ "$MEM_FREE" -lt 300 ]; then
    log "   WARNING: Low memory! Consider scaling up or optimizing."
fi

# -----------------------------------------------------------------------------
# 9. Disk Usage Threshold Alerts
# -----------------------------------------------------------------------------
log "9. Disk usage threshold check..."

NTFY_TOPIC="bo1-alerts"
NTFY_URL="http://ntfy:80"
DISK_WARN_THRESHOLD=70
DISK_CRIT_THRESHOLD=85

# Get disk usage percentage (strip % sign)
DISK_PCT=$(df / | tail -1 | awk '{print $5}' | tr -d '%')

if [ "$DISK_PCT" -ge "$DISK_CRIT_THRESHOLD" ]; then
    log "   CRITICAL: Disk usage at ${DISK_PCT}% (threshold: ${DISK_CRIT_THRESHOLD}%)"
    curl -s -X POST "$NTFY_URL/$NTFY_TOPIC" \
        -H "Title: 🚨 CRITICAL: Disk Usage ${DISK_PCT}%" \
        -H "Priority: urgent" \
        -H "Tags: warning,disk" \
        -d "Production server disk at ${DISK_PCT}%. Immediate action required." 2>/dev/null || true
elif [ "$DISK_PCT" -ge "$DISK_WARN_THRESHOLD" ]; then
    log "   WARNING: Disk usage at ${DISK_PCT}% (threshold: ${DISK_WARN_THRESHOLD}%)"
    curl -s -X POST "$NTFY_URL/$NTFY_TOPIC" \
        -H "Title: ⚠️ Disk Usage Warning ${DISK_PCT}%" \
        -H "Priority: high" \
        -H "Tags: warning,disk" \
        -d "Production server disk at ${DISK_PCT}%. Consider cleanup." 2>/dev/null || true
else
    log "   Disk usage OK: ${DISK_PCT}%"
fi

# -----------------------------------------------------------------------------
# 10. Disk Usage Trend Logging
# -----------------------------------------------------------------------------
log "10. Disk usage trend logging..."

TREND_LOG="/var/log/bo1-disk-trend.csv"

# Create header if file doesn't exist
if [ ! -f "$TREND_LOG" ]; then
    echo "timestamp,disk_pct,disk_used_gb,docker_images_gb,docker_volumes_mb" > "$TREND_LOG"
fi

# Get metrics
DISK_USED_GB=$(df / | tail -1 | awk '{print $3/1024/1024}')
DOCKER_IMG_GB=$(docker system df --format '{{.Size}}' 2>/dev/null | head -1 | grep -oE '[0-9.]+' || echo "0")
DOCKER_VOL_MB=$(docker system df --format '{{.Size}}' 2>/dev/null | tail -1 | grep -oE '[0-9.]+' || echo "0")

# Append to trend log
echo "$TIMESTAMP,$DISK_PCT,$DISK_USED_GB,$DOCKER_IMG_GB,$DOCKER_VOL_MB" >> "$TREND_LOG"
log "   Logged to $TREND_LOG"

# Keep only last 90 days of trend data
if [ -f "$TREND_LOG" ]; then
    tail -91 "$TREND_LOG" > "$TREND_LOG.tmp" && mv "$TREND_LOG.tmp" "$TREND_LOG"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
log "=== Cleanup Complete ==="
log ""
