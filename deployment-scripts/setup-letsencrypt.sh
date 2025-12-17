#!/bin/bash
# =============================================================================
# Setup Let's Encrypt SSL Certificate for Board of One
# =============================================================================
# Run this script on the production server to obtain a Let's Encrypt certificate
# and configure nginx to use it.
#
# Usage:
#   sudo bash deployment-scripts/setup-letsencrypt.sh
#
# Prerequisites:
#   - nginx installed and running
#   - certbot installed
#   - Domain boardof.one pointing to this server
# =============================================================================

set -e

echo "🔒 Setting up Let's Encrypt SSL certificate for boardof.one..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: This script must be run as root (use sudo)"
  exit 1
fi

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
  echo "❌ Error: certbot is not installed"
  echo "Install with: sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx"
  exit 1
fi

# Check if nginx is running
if ! systemctl is-active --quiet nginx; then
  echo "❌ Error: nginx is not running"
  echo "Start with: sudo systemctl start nginx"
  exit 1
fi

# Obtain certificate using nginx plugin
echo "📋 Obtaining Let's Encrypt certificate for boardof.one..."
echo "   This will:"
echo "   - Verify domain ownership via HTTP challenge"
echo "   - Obtain certificate from Let's Encrypt"
echo "   - Auto-renew every 60 days"
echo ""

# All subdomains that need SSL coverage
DOMAINS=(
  "boardof.one"
  "www.boardof.one"
  "staging.boardof.one"
  "analytics.boardof.one"
  "status.boardof.one"
  "monitoring.boardof.one"
)

# Build domain arguments
DOMAIN_ARGS=""
for domain in "${DOMAINS[@]}"; do
  DOMAIN_ARGS="$DOMAIN_ARGS -d $domain"
done

# Run certbot with nginx plugin
certbot --nginx \
  $DOMAIN_ARGS \
  --non-interactive \
  --agree-tos \
  --email siperiea@gmail.com \
  --redirect \
  --cert-name boardof.one

echo ""
echo "✅ Let's Encrypt certificate obtained successfully!"
echo ""
echo "📋 Certificate details:"
certbot certificates

echo ""
echo "🔄 Certificate will auto-renew via certbot timer"
systemctl status certbot.timer --no-pager || echo "⚠️  Certbot timer not active - manual renewal needed"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📌 Next steps:"
echo "   1. Update nginx configs in repo to use Let's Encrypt paths:"
echo "      ssl_certificate /etc/letsencrypt/live/boardof.one/fullchain.pem;"
echo "      ssl_certificate_key /etc/letsencrypt/live/boardof.one/privkey.pem;"
echo "   2. Verify HTTPS: https://boardof.one"
echo "   3. Test auto-renewal: sudo certbot renew --dry-run"
echo ""
