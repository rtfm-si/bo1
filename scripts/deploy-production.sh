#!/bin/bash
# =============================================================================
# Board of One - Production Deployment Script
# =============================================================================

set -e  # Exit on error

echo "=================================="
echo "Board of One - Production Deploy"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "⚠️  Warning: Running as root. Consider using a non-root user with sudo."
fi

# Check required files
echo "📋 Checking required files..."
if [ ! -f ".env" ]; then
  echo "❌ Error: .env file not found. Copy from .env.example and configure."
  exit 1
fi

if [ ! -f "docker-compose.prod.yml" ]; then
  echo "❌ Error: docker-compose.prod.yml not found."
  exit 1
fi

if [ ! -f "nginx/nginx.conf" ]; then
  echo "❌ Error: nginx/nginx.conf not found."
  exit 1
fi

# Check SSL certificates
echo "🔒 Checking SSL certificates..."
if [ -d "nginx/ssl" ] && [ -f "nginx/ssl/boardofone.crt" ] && [ -f "nginx/ssl/boardofone.key" ]; then
  echo "✅ SSL certificates found (self-signed or custom)"
  SSL_SOURCE="./nginx/ssl:/etc/nginx/ssl:ro"
elif [ -d "/etc/letsencrypt/live/boardof.one" ]; then
  echo "✅ Let's Encrypt certificates found"
  SSL_SOURCE="/etc/letsencrypt/live/boardof.one:/etc/nginx/ssl:ro"
else
  echo "⚠️  Warning: No SSL certificates found."
  echo ""
  echo "Options:"
  echo "1. Generate self-signed (development): ./scripts/generate-ssl-cert.sh"
  echo "2. Use Let's Encrypt (production): sudo certbot certonly --standalone -d boardof.one"
  echo ""
  read -p "Continue without SSL? (y/N): " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Check Docker
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
  echo "❌ Error: Docker not installed. Install from https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker compose version &> /dev/null; then
  echo "❌ Error: Docker Compose not installed or not v2."
  exit 1
fi

echo "✅ Docker and Docker Compose available"

# Stop existing containers
echo ""
echo "🛑 Stopping existing containers..."
docker compose -f docker-compose.prod.yml down || true

# Pull base images
echo ""
echo "📦 Pulling base images..."
docker compose -f docker-compose.prod.yml pull postgres redis

# Build services
echo ""
echo "🔨 Building services (this may take 5-10 minutes)..."
docker compose -f docker-compose.prod.yml build --no-cache

# Start services
echo ""
echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be healthy (max 60s)..."
timeout=60
elapsed=0
while [ $elapsed -lt $timeout ]; do
  if docker compose -f docker-compose.prod.yml ps | grep -q "unhealthy"; then
    echo "⚠️  Some services are unhealthy, waiting..."
    sleep 5
    elapsed=$((elapsed + 5))
  else
    break
  fi
done

# Show status
echo ""
echo "📊 Service Status:"
docker compose -f docker-compose.prod.yml ps

# Test services
echo ""
echo "🧪 Testing services..."

# Test frontend
if curl -s -f -k http://localhost:3000 > /dev/null 2>&1; then
  echo "✅ Frontend: OK (http://localhost:3000)"
else
  echo "❌ Frontend: FAILED"
fi

# Test API
if curl -s -f http://localhost:8000/api/health > /dev/null 2>&1; then
  echo "✅ API: OK (http://localhost:8000/api/health)"
else
  echo "❌ API: FAILED"
fi

# Test nginx (if running)
if docker compose -f docker-compose.prod.yml ps | grep -q "bo1-nginx-prod"; then
  if curl -s -f -k https://localhost > /dev/null 2>&1; then
    echo "✅ Nginx: OK (https://localhost)"
  else
    echo "⚠️  Nginx: Check logs (docker compose -f docker-compose.prod.yml logs nginx)"
  fi
fi

# Show logs summary
echo ""
echo "📋 Recent logs (last 20 lines):"
docker compose -f docker-compose.prod.yml logs --tail=20

# Deployment complete
echo ""
echo "=================================="
echo "✅ Deployment Complete!"
echo "=================================="
echo ""
echo "🌐 Access your application:"
echo "   - Frontend:  https://boardof.one/"
echo "   - Design System: https://boardof.one/design-system-demo"
echo "   - API Health: https://boardof.one/api/health"
echo "   - API Docs (admin): https://boardof.one/admin/docs"
echo ""
echo "📊 Monitor services:"
echo "   docker compose -f docker-compose.prod.yml ps"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 Stop services:"
echo "   docker compose -f docker-compose.prod.yml down"
echo ""
echo "📖 Full guide: ./DEPLOYMENT_GUIDE.md"
echo ""
