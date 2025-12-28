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
# 1. Docker Cleanup
# -----------------------------------------------------------------------------
log "1. Docker cleanup..."

# Remove stopped containers
STOPPED=$(docker container prune -f 2>/dev/null | tail -1)
log "   Stopped containers: $STOPPED"

# Remove dangling images (not tagged, not in use)
DANGLING=$(docker image prune -f 2>/dev/null | tail -1)
log "   Dangling images: $DANGLING"

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
# 5. Disk Usage Report
# -----------------------------------------------------------------------------
log "5. Disk usage report..."

DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}')
log "   Root disk usage: $DISK_USAGE"

DOCKER_USAGE=$(docker system df 2>/dev/null | head -5)
log "   Docker disk usage:"
echo "$DOCKER_USAGE" | while read line; do
    log "     $line"
done

# -----------------------------------------------------------------------------
# 6. Memory Report
# -----------------------------------------------------------------------------
log "6. Memory report..."

MEM_FREE=$(free -m | awk '/^Mem:/{print $7}')
MEM_TOTAL=$(free -m | awk '/^Mem:/{print $2}')
MEM_PERCENT=$((100 - (MEM_FREE * 100 / MEM_TOTAL)))
log "   Memory: ${MEM_FREE}MB free of ${MEM_TOTAL}MB (${MEM_PERCENT}% used)"

# Alert if memory is critically low
if [ "$MEM_FREE" -lt 300 ]; then
    log "   WARNING: Low memory! Consider scaling up or optimizing."
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
log "=== Cleanup Complete ==="
log ""
