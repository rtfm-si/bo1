#!/bin/bash
# =============================================================================
# Board of One - Application Deployment Script
# =============================================================================
# Use this script to manually deploy both API and frontend together.
# For production deployments, prefer GitHub Actions workflow.
#
# Usage:
#   ./scripts/deploy-app.sh              # Deploy to current environment
#   ./scripts/deploy-app.sh --no-cache   # Force full rebuild
# =============================================================================

set -e

NO_CACHE=""
if [ "$1" = "--no-cache" ]; then
    NO_CACHE="--no-cache"
    echo "🔄 Force rebuild enabled (--no-cache)"
fi

echo "=================================="
echo "Board of One - App Deployment"
echo "=================================="
echo ""

# Check we're in the right directory
if [ ! -f "docker-compose.app.yml" ]; then
    echo "❌ Error: docker-compose.app.yml not found."
    echo "   Run this script from /opt/boardofone"
    exit 1
fi

# Check .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found."
    exit 1
fi

# =============================================================================
# Pre-deployment health checks (prevent resource exhaustion)
# =============================================================================
echo "🔍 Running pre-deployment health checks..."

# Check memory availability (require at least 500MB free)
FREE_MEM=$(free -m | awk '/^Mem:/{print $7}')
echo "   Available memory: ${FREE_MEM}MB"
if [ "$FREE_MEM" -lt 500 ]; then
    echo "⚠️  Low memory warning: ${FREE_MEM}MB available (minimum 500MB recommended)"
    read -p "   Run docker prune to free memory? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -f
        FREE_MEM=$(free -m | awk '/^Mem:/{print $7}')
        echo "   Available memory after cleanup: ${FREE_MEM}MB"
    fi
    if [ "$FREE_MEM" -lt 300 ]; then
        echo "❌ Critical: Insufficient memory (${FREE_MEM}MB). Cannot proceed safely."
        exit 1
    fi
fi

# Check for stale containers from deprecated docker-compose.prod.yml
STALE_CONTAINERS=$(docker ps -a --format '{{.Names}}' | grep -E '^boardofone-(postgres|redis|supertokens|umami|uptime-kuma|bo1)-1$' || true)
if [ -n "$STALE_CONTAINERS" ]; then
    echo "⚠️  Found stale containers from deprecated docker-compose.prod.yml:"
    echo "$STALE_CONTAINERS" | sed 's/^/      - /'
    read -p "   Remove stale containers to prevent port conflicts? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo "$STALE_CONTAINERS" | xargs -r docker rm -f 2>/dev/null || true
        echo "✅ Stale containers removed"
    fi
fi

# Check if both blue AND green API are running (shouldn't happen)
BLUE_RUNNING=$(docker ps --format '{{.Names}}' | grep -c '^boardofone-api-1$' || echo "0")
GREEN_RUNNING=$(docker ps --format '{{.Names}}' | grep -c '^boardofone-green-api-1$' || echo "0")
if [ "$BLUE_RUNNING" -gt 0 ] && [ "$GREEN_RUNNING" -gt 0 ]; then
    echo "⚠️  Both blue AND green environments running simultaneously!"
    echo "   This wastes ~1GB RAM per environment."
    read -p "   Stop the inactive environment now? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Determine which is serving traffic by checking nginx config
        if grep -q "8001" /etc/nginx/sites-enabled/boardofone 2>/dev/null; then
            echo "   nginx pointing to green (8001), stopping blue..."
            docker-compose -f docker-compose.app.yml -p boardofone stop
        else
            echo "   nginx pointing to blue (8000), stopping green..."
            docker-compose -f docker-compose.app.yml -p boardofone-green stop
        fi
        echo "✅ Inactive environment stopped"
    fi
fi

# Check disk space (require at least 5GB free)
FREE_DISK=$(df -BG /var/lib/docker 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G' || echo "999")
if [ "$FREE_DISK" != "999" ] && [ "$FREE_DISK" -lt 5 ]; then
    echo "⚠️  Low disk space warning: ${FREE_DISK}GB available"
    read -p "   Run docker prune to free space? [Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        docker system prune -af --filter "until=168h"
        FREE_DISK=$(df -BG /var/lib/docker | tail -1 | awk '{print $4}' | tr -d 'G')
        echo "   Available disk space after cleanup: ${FREE_DISK}GB"
    fi
fi

echo "✅ Pre-deployment health checks complete"
echo ""

# Detect current environment
CURRENT_ENV="none"
TARGET_PROJECT="boardofone"
TARGET_API_PORT=8000
TARGET_FRONTEND_PORT=3000

if docker ps --format '{{.Names}}' | grep -q "^boardofone-green-api-1$"; then
    CURRENT_ENV="green"
    TARGET_PROJECT="boardofone"
    TARGET_API_PORT=8000
    TARGET_FRONTEND_PORT=3000
elif docker ps --format '{{.Names}}' | grep -q "^boardofone-api-1$"; then
    CURRENT_ENV="blue"
    TARGET_PROJECT="boardofone"  # Update in place for simplicity
fi

echo "📍 Current environment: ${CURRENT_ENV}"
echo "🎯 Target project: ${TARGET_PROJECT}"
echo ""

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# Show what will be deployed
echo ""
echo "📋 Latest commit:"
git log --oneline -1
echo ""

# Build BOTH services with build metadata
echo "🔨 Building API and Frontend (this may take a few minutes)..."
BUILD_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

API_PORT=${TARGET_API_PORT} FRONTEND_PORT=${TARGET_FRONTEND_PORT} \
    docker-compose -f docker-compose.app.yml -p ${TARGET_PROJECT} build ${NO_CACHE} \
    --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
    --build-arg GIT_COMMIT="${GIT_COMMIT}" \
    api frontend

echo "📋 Build metadata: timestamp=${BUILD_TIMESTAMP}, commit=${GIT_COMMIT}"

# Deploy both services
echo ""
echo "🚀 Deploying services..."
API_PORT=${TARGET_API_PORT} FRONTEND_PORT=${TARGET_FRONTEND_PORT} \
    docker-compose -f docker-compose.app.yml -p ${TARGET_PROJECT} up -d api frontend

# Wait for services
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# ---------------------------------------------------------------------------
# Copy static files from frontend container to host for nginx
# ---------------------------------------------------------------------------
echo ""
echo "📦 Syncing static files for nginx..."

# Determine static directory based on environment
if [ "$TARGET_PROJECT" = "boardofone-green" ]; then
    STATIC_DIR="/var/www/boardofone/static-green"
    CONTAINER_NAME="${TARGET_PROJECT}-frontend-1"
else
    STATIC_DIR="/var/www/boardofone/static-blue"
    CONTAINER_NAME="${TARGET_PROJECT}-frontend-1"
fi

TEMP_STATIC_DIR="${STATIC_DIR}.tmp"
OLD_STATIC_DIR="${STATIC_DIR}.old"

# Wait for frontend container to be healthy
echo "   Waiting for frontend container to be ready..."
for i in {1..12}; do
    if docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null | grep -q "healthy"; then
        echo "   ✅ Frontend container healthy"
        break
    fi
    if [ $i -eq 12 ]; then
        echo "   ⚠️  Frontend not healthy after 60s, attempting static copy anyway..."
    fi
    sleep 5
done

# Create base directory if needed
sudo mkdir -p /var/www/boardofone

# Remove any stale temp/old directories
sudo rm -rf "$TEMP_STATIC_DIR" "$OLD_STATIC_DIR"

# Copy static files to temp directory (atomic preparation)
echo "   Copying static files from container..."
sudo mkdir -p "$TEMP_STATIC_DIR"
if docker cp "${CONTAINER_NAME}:/app/build/client/." "$TEMP_STATIC_DIR/"; then
    # Set ownership
    sudo chown -R www-data:www-data "$TEMP_STATIC_DIR"

    # Atomic swap: move current to old, temp to current
    if [ -d "$STATIC_DIR" ]; then
        sudo mv "$STATIC_DIR" "$OLD_STATIC_DIR"
    fi
    sudo mv "$TEMP_STATIC_DIR" "$STATIC_DIR"

    # Clean up old directory
    sudo rm -rf "$OLD_STATIC_DIR"

    echo "   ✅ Static files synced to $STATIC_DIR"

    # Show what was copied
    FILE_COUNT=$(find "$STATIC_DIR" -type f | wc -l)
    echo "   📊 Copied $FILE_COUNT files"
else
    echo "   ❌ Failed to copy static files from container"
    sudo rm -rf "$TEMP_STATIC_DIR"
fi

# Health checks
echo ""
echo "🏥 Running health checks..."

API_HEALTHY=false
FRONTEND_HEALTHY=false

for i in {1..12}; do
    if curl --fail --silent --max-time 5 http://localhost:${TARGET_API_PORT}/api/health > /dev/null 2>&1; then
        echo "✅ API is healthy"
        API_HEALTHY=true
        break
    fi
    echo "   Waiting for API... ($i/12)"
    sleep 5
done

if curl --fail --silent --max-time 5 http://localhost:${TARGET_FRONTEND_PORT}/ > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
    FRONTEND_HEALTHY=true
else
    echo "⚠️  Frontend may still be starting..."
fi

# Show image timestamps
echo ""
echo "📊 Image timestamps:"
docker images --format "{{.Repository}}:{{.Tag}} - {{.CreatedAt}}" | grep -E "^boardofone-(api|frontend)" | head -4

# Check ntfy health (if running)
echo ""
echo "🔔 Checking ntfy health..."
if docker ps --format '{{.Names}}' | grep -q "infrastructure-ntfy-1"; then
    if docker exec infrastructure-ntfy-1 wget -q --spider http://localhost:80/v1/health 2>/dev/null; then
        echo "✅ ntfy is healthy"
    else
        echo "⚠️  ntfy is unhealthy, restarting..."
        docker-compose -f docker-compose.infrastructure.yml -p infrastructure up -d --force-recreate ntfy
        sleep 5
        if docker exec infrastructure-ntfy-1 wget -q --spider http://localhost:80/v1/health 2>/dev/null; then
            echo "✅ ntfy restarted and healthy"
        else
            echo "⚠️  ntfy still unhealthy (check logs with: docker logs infrastructure-ntfy-1)"
        fi
    fi
else
    echo "⚠️  ntfy container not running - run: docker-compose -f docker-compose.infrastructure.yml -p infrastructure up -d ntfy"
fi

# Summary
echo ""
echo "=================================="
if [ "$API_HEALTHY" = true ]; then
    echo "✅ Deployment Complete!"
else
    echo "⚠️  Deployment finished but API health check failed"
    echo "   Check logs: docker-compose -f docker-compose.app.yml -p ${TARGET_PROJECT} logs api"
fi
echo "=================================="
echo ""
echo "🔗 API:      http://localhost:${TARGET_API_PORT}/api/health"
echo "🔗 Frontend: http://localhost:${TARGET_FRONTEND_PORT}/"
echo ""
