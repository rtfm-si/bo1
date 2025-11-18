#!/bin/bash
# =============================================================================
# Board of One - Production Server Setup Script
# =============================================================================
# This script configures a fresh Ubuntu server for blue-green deployments.
# Run this ONCE on your production server as root or with sudo.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/deployment-scripts/setup-production-server.sh | sudo bash
#   OR
#   sudo bash setup-production-server.sh
#
# What this script does:
# 1. Updates system packages
# 2. Installs Docker + Docker Compose
# 3. Installs nginx (host-level)
# 4. Creates deploy user with proper permissions
# 5. Sets up deployment directory structure
# 6. Configures nginx for blue-green deployment
# 7. Sets up SSL certificate directory
# 8. Configures firewall (ufw)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_USER="deploy"
DEPLOY_DIR="/opt/boardofone"
GITHUB_REPO_URL="https://github.com/YOUR_USERNAME/bo1.git"  # UPDATE THIS!

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Board of One - Production Server Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Please run as root or with sudo${NC}"
    exit 1
fi

# Confirm before proceeding
read -p "This will install Docker, nginx, and configure the system. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

# =============================================================================
# 1. Update System Packages
# =============================================================================
echo -e "\n${YELLOW}[1/9] Updating system packages...${NC}"
apt update
apt upgrade -y

# =============================================================================
# 2. Install Docker
# =============================================================================
echo -e "\n${YELLOW}[2/9] Installing Docker...${NC}"

# Check if Docker is already installed
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker already installed ($(docker --version))${NC}"
else
    # Install dependencies
    apt install -y ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    echo -e "${GREEN}✓ Docker installed successfully${NC}"
fi

# Verify Docker installation
docker --version
docker compose version

# =============================================================================
# 3. Install nginx
# =============================================================================
echo -e "\n${YELLOW}[3/9] Installing nginx...${NC}"

if command -v nginx &> /dev/null; then
    echo -e "${GREEN}✓ Nginx already installed ($(nginx -v 2>&1))${NC}"
else
    apt install -y nginx

    # Enable and start nginx
    systemctl enable nginx
    systemctl start nginx

    echo -e "${GREEN}✓ Nginx installed successfully${NC}"
fi

# =============================================================================
# 4. Create Deploy User
# =============================================================================
echo -e "\n${YELLOW}[4/9] Creating deploy user...${NC}"

# Check if user exists
if id "$DEPLOY_USER" &>/dev/null; then
    echo -e "${GREEN}✓ User '$DEPLOY_USER' already exists${NC}"
else
    # Create user with home directory
    useradd -m -s /bin/bash "$DEPLOY_USER"

    # Set a random password (will use SSH keys for login)
    TEMP_PASSWORD=$(openssl rand -base64 32)
    echo "$DEPLOY_USER:$TEMP_PASSWORD" | chpasswd

    echo -e "${GREEN}✓ User '$DEPLOY_USER' created${NC}"
fi

# Add deploy user to docker group (no sudo needed for docker commands)
usermod -aG docker "$DEPLOY_USER"
echo -e "${GREEN}✓ Added '$DEPLOY_USER' to docker group${NC}"

# Create .ssh directory for deploy user
mkdir -p /home/$DEPLOY_USER/.ssh
chown $DEPLOY_USER:$DEPLOY_USER /home/$DEPLOY_USER/.ssh
chmod 700 /home/$DEPLOY_USER/.ssh

# =============================================================================
# 5. Configure sudo permissions for nginx commands
# =============================================================================
echo -e "\n${YELLOW}[5/9] Configuring sudo permissions...${NC}"

# Allow deploy user to run nginx commands without password
cat > /etc/sudoers.d/deploy-nginx << 'EOF'
# Allow deploy user to manage nginx for blue-green deployments
deploy ALL=(ALL) NOPASSWD: /usr/sbin/nginx
deploy ALL=(ALL) NOPASSWD: /bin/systemctl reload nginx
deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart nginx
deploy ALL=(ALL) NOPASSWD: /bin/systemctl status nginx
deploy ALL=(ALL) NOPASSWD: /bin/cp /opt/boardofone/nginx/nginx-*.conf /etc/nginx/sites-enabled/*
EOF

chmod 0440 /etc/sudoers.d/deploy-nginx
echo -e "${GREEN}✓ Sudo permissions configured${NC}"

# =============================================================================
# 6. Create Deployment Directory Structure
# =============================================================================
echo -e "\n${YELLOW}[6/9] Creating deployment directory structure...${NC}"

# Create main deployment directory
mkdir -p $DEPLOY_DIR
chown $DEPLOY_USER:$DEPLOY_USER $DEPLOY_DIR

# Clone repository (if not exists)
if [ -d "$DEPLOY_DIR/.git" ]; then
    echo -e "${GREEN}✓ Repository already cloned at $DEPLOY_DIR${NC}"
else
    echo "Enter your GitHub repository URL (e.g., https://github.com/username/bo1.git):"
    read GITHUB_REPO_URL

    # Clone as deploy user
    su - $DEPLOY_USER -c "git clone $GITHUB_REPO_URL $DEPLOY_DIR"
    echo -e "${GREEN}✓ Repository cloned to $DEPLOY_DIR${NC}"
fi

# Create required directories
mkdir -p $DEPLOY_DIR/exports
mkdir -p $DEPLOY_DIR/backups
mkdir -p $DEPLOY_DIR/logs
mkdir -p $DEPLOY_DIR/nginx/ssl

chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_DIR

echo -e "${GREEN}✓ Directory structure created${NC}"

# =============================================================================
# 7. Configure nginx
# =============================================================================
echo -e "\n${YELLOW}[7/9] Configuring nginx...${NC}"

# Create sites-enabled directory
mkdir -p /etc/nginx/sites-enabled

# Remove default nginx config
rm -f /etc/nginx/sites-enabled/default

# Update main nginx.conf to include sites-enabled
if ! grep -q "include /etc/nginx/sites-enabled/\*" /etc/nginx/nginx.conf; then
    # Backup original config
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup

    # Add include directive in http block
    sed -i '/http {/a \    include /etc/nginx/sites-enabled/*;' /etc/nginx/nginx.conf
    echo -e "${GREEN}✓ Updated nginx.conf to include sites-enabled${NC}"
fi

# Copy blue config as initial active config
if [ -f "$DEPLOY_DIR/nginx/nginx-blue.conf" ]; then
    cp $DEPLOY_DIR/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
    echo -e "${GREEN}✓ Copied blue config to sites-enabled${NC}"
else
    echo -e "${YELLOW}⚠ nginx-blue.conf not found. You'll need to copy it manually after cloning the repo.${NC}"
fi

# Test nginx configuration
nginx -t && echo -e "${GREEN}✓ Nginx configuration is valid${NC}"

# =============================================================================
# 8. Set up SSL Certificate Directory
# =============================================================================
echo -e "\n${YELLOW}[8/9] Setting up SSL certificate directory...${NC}"

mkdir -p /etc/nginx/ssl
chown root:root /etc/nginx/ssl
chmod 755 /etc/nginx/ssl

echo -e "${GREEN}✓ SSL directory created at /etc/nginx/ssl${NC}"
echo -e "${YELLOW}⚠ You need to generate SSL certificates before deployment.${NC}"
echo -e "${YELLOW}  Run: cd $DEPLOY_DIR && make generate-ssl${NC}"

# =============================================================================
# 9. Configure Firewall (UFW)
# =============================================================================
echo -e "\n${YELLOW}[9/9] Configuring firewall...${NC}"

# Install ufw if not installed
if ! command -v ufw &> /dev/null; then
    apt install -y ufw
fi

# Configure firewall rules
ufw --force enable
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (IMPORTANT: Don't lock yourself out!)
ufw allow ssh
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Reload firewall
ufw reload

echo -e "${GREEN}✓ Firewall configured${NC}"
ufw status

# =============================================================================
# Setup Complete
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Production Server Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. Add GitHub Actions SSH public key:"
echo -e "   ${YELLOW}sudo nano /home/$DEPLOY_USER/.ssh/authorized_keys${NC}"
echo -e "   (Paste the public key from your GitHub secrets setup)"
echo ""
echo -e "2. Generate SSL certificates:"
echo -e "   ${YELLOW}cd $DEPLOY_DIR && make generate-ssl${NC}"
echo ""
echo -e "3. Create .env file with production secrets:"
echo -e "   ${YELLOW}sudo -u $DEPLOY_USER nano $DEPLOY_DIR/.env${NC}"
echo -e "   (Copy from .env.example and fill in production values)"
echo ""
echo -e "4. Set up GitHub repository secrets:"
echo -e "   - PRODUCTION_HOST (this server's IP/domain)"
echo -e "   - PRODUCTION_USER (deploy)"
echo -e "   - PRODUCTION_SSH_KEY (private key matching the public key above)"
echo -e "   - PRODUCTION_SSH_PORT (22)"
echo ""
echo -e "5. Test SSH connection from GitHub Actions:"
echo -e "   ${YELLOW}ssh -i /path/to/private_key $DEPLOY_USER@$(hostname -I | awk '{print $1}')${NC}"
echo ""
echo -e "6. Run first deployment:"
echo -e "   - Go to GitHub Actions"
echo -e "   - Run 'Deploy to Production' workflow"
echo -e "   - Type 'deploy-to-production' to confirm"
echo ""
echo -e "${GREEN}Server is ready for blue-green deployments!${NC}"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo -e "- Docker group changes require logout/login for $DEPLOY_USER"
echo -e "- Test Docker access: ${YELLOW}sudo -u $DEPLOY_USER docker ps${NC}"
echo -e "- View nginx config: ${YELLOW}cat /etc/nginx/sites-enabled/boardofone.conf${NC}"
echo ""
