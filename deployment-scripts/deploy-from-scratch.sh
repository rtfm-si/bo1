#!/bin/bash
set -euo pipefail

# =============================================================================
# Board of One - Automated Production Deployment
# =============================================================================
# Run this script from your LOCAL machine to deploy to a fresh DigitalOcean droplet
# Usage: ./deployment-scripts/deploy-from-scratch.sh <server-ip>
# Example: ./deployment-scripts/deploy-from-scratch.sh 139.59.201.65
#
# Prerequisites:
# - Fresh Ubuntu 24.04 droplet with SSH key authentication
# - git-crypt key at ~/bo1-git-crypt.key
# - .env.production configured with production secrets
# =============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -ne 1 ]; then
    echo -e "${RED}Error: Missing server IP address${NC}"
    echo "Usage: $0 <server-ip>"
    echo "Example: $0 139.59.201.65"
    exit 1
fi

SERVER_IP=$1
GIT_CRYPT_KEY="$HOME/bo1-git-crypt.key"
DOMAIN="boardof.one"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Board of One - Automated Production Deployment               ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo ""
echo -e "${GREEN}Target Server:${NC} $SERVER_IP"
echo -e "${GREEN}Domain:${NC} $DOMAIN"
echo ""

# Preflight checks
echo -e "${YELLOW}► Preflight checks...${NC}"

# Check git-crypt key exists
if [ ! -f "$GIT_CRYPT_KEY" ]; then
    echo -e "${RED}✗ git-crypt key not found at $GIT_CRYPT_KEY${NC}"
    exit 1
fi
echo -e "${GREEN}✓ git-crypt key found${NC}"

# Check .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}✗ .env.production not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env.production found${NC}"

# Check SSH connection
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes root@"$SERVER_IP" exit 2>/dev/null; then
    echo -e "${RED}✗ Cannot connect to $SERVER_IP via SSH${NC}"
    echo "  Make sure your SSH key is added to the droplet"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"

# Check if git-crypt is unlocked locally (files should show as "encrypted" when unlocked)
if git-crypt status .env 2>&1 | grep -q "not encrypted"; then
    echo -e "${RED}✗ Repository not unlocked with git-crypt${NC}"
    echo "  .env file is not managed by git-crypt or repository is locked"
    echo "  Run: git-crypt unlock ~/bo1-git-crypt.key"
    exit 1
fi
echo -e "${GREEN}✓ Repository unlocked${NC}"

echo ""
echo -e "${YELLOW}► Step 1/6: Copying git-crypt key to server...${NC}"
scp "$GIT_CRYPT_KEY" root@"$SERVER_IP":/tmp/bo1-git-crypt.key
echo -e "${GREEN}✓ Key copied${NC}"

echo ""
echo -e "${YELLOW}► Step 2/6: Installing dependencies (git-crypt, Docker, etc.)...${NC}"
ssh root@"$SERVER_IP" bash <<'ENDSSH'
set -euo pipefail

# Suppress interactive prompts
export DEBIAN_FRONTEND=noninteractive

# Update system
apt-get update -qq
apt-get upgrade -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# Install git-crypt
apt-get install -y -qq git-crypt

# Install Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh > /dev/null 2>&1
    rm get-docker.sh
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    curl -fsSL "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Install certbot
apt-get install -y -qq certbot python3-certbot-nginx

# Install nginx
apt-get install -y -qq nginx
ENDSSH
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${YELLOW}► Step 3/6: Configuring firewall (UFW)...${NC}"
ssh root@"$SERVER_IP" bash <<'ENDSSH'
set -euo pipefail

# Configure UFW
ufw --force reset > /dev/null 2>&1
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ENDSSH
echo -e "${GREEN}✓ Firewall configured${NC}"

echo ""
echo -e "${YELLOW}► Step 4/6: Cloning repository and setting up application...${NC}"
ssh root@"$SERVER_IP" bash <<ENDSSH
set -euo pipefail

# Create application directory
mkdir -p /opt/boardofone
cd /opt/boardofone

# Clone repository
if [ -d ".git" ]; then
    git fetch origin main
    git reset --hard origin/main
else
    git clone https://github.com/rtfm-si/bo1.git .
fi

# Unlock encrypted files
git-crypt unlock /tmp/bo1-git-crypt.key

# Copy production template to .env
cp .env.production .env

# Protect .env from git pull overwrites
git update-index --skip-worktree .env

# Clean up key file
rm -f /tmp/bo1-git-crypt.key
ENDSSH
echo -e "${GREEN}✓ Repository cloned and configured${NC}"

echo ""
echo -e "${YELLOW}► Step 5/6: Building and starting Docker containers...${NC}"
ssh root@"$SERVER_IP" bash <<'ENDSSH'
set -euo pipefail
cd /opt/boardofone

# Build images
docker-compose build --quiet

# Start services
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 10

# Check if containers are running
if ! docker ps | grep -q bo1-app; then
    echo "Error: Application container failed to start"
    docker-compose logs bo1-app
    exit 1
fi
ENDSSH
echo -e "${GREEN}✓ Docker containers running${NC}"

echo ""
echo -e "${YELLOW}► Step 6/6: Configuring nginx and SSL certificates...${NC}"
ssh root@"$SERVER_IP" bash <<ENDSSH
set -euo pipefail

# Copy nginx configuration
cp /opt/boardofone/nginx/nginx.conf /etc/nginx/sites-available/boardofone
ln -sf /etc/nginx/sites-available/boardofone /etc/nginx/sites-enabled/boardofone
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
nginx -t

# Reload nginx
systemctl reload nginx

# Obtain SSL certificates (requires DNS to be configured)
# Note: This will fail if DNS is not pointed to the server yet
echo "Attempting to obtain SSL certificates..."
certbot --nginx -d ${DOMAIN} \
    -d www.${DOMAIN} \
    -d api.${DOMAIN} \
    -d auth.${DOMAIN} \
    --non-interactive \
    --agree-tos \
    --email admin@${DOMAIN} \
    --redirect || echo "Warning: SSL certificate setup failed. DNS may not be configured yet."

# Set up auto-renewal
systemctl enable certbot.timer
ENDSSH
echo -e "${GREEN}✓ nginx and SSL configured${NC}"

echo ""
echo -e "${YELLOW}► Setting up automated backups...${NC}"
ssh root@"$SERVER_IP" bash <<'ENDSSH'
set -euo pipefail

# Make backup script executable
chmod +x /opt/boardofone/deployment-scripts/backup.sh

# Add cron job for daily backups at 2 AM
(crontab -l 2>/dev/null || echo "") | grep -v "backup.sh" | cat - <(echo "0 2 * * * /opt/boardofone/deployment-scripts/backup.sh >> /var/log/bo1-backup.log 2>&1") | crontab -
ENDSSH
echo -e "${GREEN}✓ Automated backups configured${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Complete! 🚀                                       ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo -e "1. ${YELLOW}SSH into server and configure production secrets:${NC}"
echo -e "   ${BLUE}ssh root@$SERVER_IP${NC}"
echo -e "   ${BLUE}nano /opt/boardofone/.env${NC}"
echo ""
echo -e "   ${RED}CRITICAL: Replace all 'REPLACE_WITH_PRODUCTION_KEY' placeholders!${NC}"
echo ""
echo -e "2. ${YELLOW}Generate production secrets:${NC}"
echo -e "   ${BLUE}openssl rand -base64 32${NC}  # For ADMIN_API_KEY"
echo -e "   ${BLUE}openssl rand -base64 32${NC}  # For SUPABASE_JWT_SECRET"
echo -e "   ${BLUE}openssl rand -base64 16${NC}  # For DATABASE_URL password"
echo ""
echo -e "3. ${YELLOW}Restart application:${NC}"
echo -e "   ${BLUE}docker-compose restart bo1-app${NC}"
echo ""
echo -e "4. ${YELLOW}Verify deployment:${NC}"
echo -e "   ${BLUE}curl https://api.$DOMAIN/health${NC}"
echo ""
echo -e "5. ${YELLOW}Check logs:${NC}"
echo -e "   ${BLUE}docker logs bo1-app -f${NC}"
echo ""
echo -e "${GREEN}Server IP:${NC} $SERVER_IP"
echo -e "${GREEN}Domain:${NC} https://$DOMAIN"
echo -e "${GREEN}API Docs:${NC} https://api.$DOMAIN/docs"
echo -e "${GREEN}Auth:${NC} https://auth.$DOMAIN"
echo ""
