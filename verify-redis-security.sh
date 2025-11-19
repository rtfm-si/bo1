#!/bin/bash
# =============================================================================
# Redis Security Verification Script
# =============================================================================
# Run this on your DigitalOcean Droplet to verify Redis is not exposed
#
# Usage: bash verify-redis-security.sh
# =============================================================================

echo "========================================="
echo "Redis Security Verification"
echo "========================================="
echo ""

# Test 1: Check if Redis is listening on 0.0.0.0 (bad) or 127.0.0.1 (good)
echo "[1/4] Checking Redis listening address..."
REDIS_LISTEN=$(docker exec boardofone-redis-1 redis-cli --pass "${REDIS_PASSWORD:-your_redis_password}" CONFIG GET bind)
echo "Redis bind configuration: $REDIS_LISTEN"

# Test 2: Check netstat for Redis port binding
echo ""
echo "[2/4] Checking port bindings (netstat)..."
netstat -tulpn | grep 6379 || echo "Redis not found in netstat (may require sudo)"

# Test 3: Try connecting from localhost (should work)
echo ""
echo "[3/4] Testing localhost connection (should succeed)..."
timeout 2 bash -c 'cat < /dev/null > /dev/tcp/127.0.0.1/6379' 2>/dev/null && \
  echo "✓ Localhost connection successful (expected)" || \
  echo "✗ Localhost connection failed (unexpected)"

# Test 4: Check UFW firewall status
echo ""
echo "[4/4] Checking firewall rules..."
sudo ufw status | grep 6379 || echo "✓ Port 6379 not exposed in firewall (good)"

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo "Redis should be:"
echo "  - Bound to 127.0.0.1 (not 0.0.0.0)"
echo "  - Accessible from localhost"
echo "  - NOT in UFW allowed rules"
echo "  - Password protected"
echo ""
echo "If all checks pass, your Redis is secure."
echo "========================================="
