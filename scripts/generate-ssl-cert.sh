#!/bin/bash
# =============================================================================
# Generate Self-Signed SSL Certificate for Development/Testing
# =============================================================================

set -e

echo "🔒 Generating self-signed SSL certificate..."
echo ""
echo "⚠️  WARNING: Self-signed certificates are for DEVELOPMENT/TESTING only!"
echo "    For production, use Let's Encrypt: sudo certbot certonly --standalone -d boardof.one"
echo ""

# Create SSL directory
mkdir -p nginx/ssl

# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/boardofone.key \
  -out nginx/ssl/boardofone.crt \
  -subj "/C=US/ST=California/L=San Francisco/O=Board of One/CN=boardof.one"

# Set permissions
chmod 600 nginx/ssl/boardofone.key
chmod 644 nginx/ssl/boardofone.crt

echo ""
echo "✅ SSL certificate generated:"
echo "   Certificate: nginx/ssl/boardofone.crt"
echo "   Private Key: nginx/ssl/boardofone.key"
echo "   Valid for: 365 days"
echo ""
echo "⚠️  Browsers will show security warnings for self-signed certificates."
echo "    Click 'Advanced' → 'Proceed to site' to continue."
echo ""
