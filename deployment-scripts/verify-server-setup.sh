#!/bin/bash
# =============================================================================
# Board of One - Production Server Verification Script
# =============================================================================
# This script verifies that the production server is correctly configured
# for blue-green deployments. Run this AFTER setup-production-server.sh.
#
# Usage:
#   bash deployment-scripts/verify-server-setup.sh
#
# What this script checks:
# 1. Docker installation and permissions
# 2. Nginx installation and configuration
# 3. Deploy user exists with correct permissions
# 4. Deployment directory structure
# 5. SSH key setup
# 6. Firewall configuration
# 7. SSL certificate directory
# =============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
DEPLOY_USER="deploy"
DEPLOY_DIR="/opt/boardofone"

CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Production Server Verification${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# =============================================================================
# Helper Functions
# =============================================================================
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((CHECKS_WARNING++))
}

# =============================================================================
# 1. Docker Installation
# =============================================================================
echo -e "${YELLOW}[1] Checking Docker installation...${NC}"

if command -v docker &> /dev/null; then
    check_pass "Docker is installed ($(docker --version))"
else
    check_fail "Docker is not installed"
fi

if command -v docker compose &> /dev/null; then
    check_pass "Docker Compose is installed ($(docker compose version))"
else
    check_fail "Docker Compose is not installed"
fi

if systemctl is-active --quiet docker; then
    check_pass "Docker service is running"
else
    check_fail "Docker service is not running"
fi

# =============================================================================
# 2. Nginx Installation
# =============================================================================
echo -e "\n${YELLOW}[2] Checking nginx installation...${NC}"

if command -v nginx &> /dev/null; then
    check_pass "Nginx is installed ($(nginx -v 2>&1 | cut -d'/' -f2))"
else
    check_fail "Nginx is not installed"
fi

if systemctl is-active --quiet nginx; then
    check_pass "Nginx service is running"
else
    check_fail "Nginx service is not running"
fi

if nginx -t &> /dev/null; then
    check_pass "Nginx configuration is valid"
else
    check_fail "Nginx configuration has errors"
fi

if [ -d "/etc/nginx/sites-enabled" ]; then
    check_pass "Nginx sites-enabled directory exists"
else
    check_fail "Nginx sites-enabled directory missing"
fi

if grep -q "include /etc/nginx/sites-enabled/\*" /etc/nginx/nginx.conf; then
    check_pass "Nginx includes sites-enabled in config"
else
    check_warn "Nginx does not include sites-enabled (may not be needed)"
fi

# =============================================================================
# 3. Deploy User
# =============================================================================
echo -e "\n${YELLOW}[3] Checking deploy user...${NC}"

if id "$DEPLOY_USER" &>/dev/null; then
    check_pass "User '$DEPLOY_USER' exists"
else
    check_fail "User '$DEPLOY_USER' does not exist"
fi

if groups "$DEPLOY_USER" | grep -q docker; then
    check_pass "User '$DEPLOY_USER' is in docker group"
else
    check_fail "User '$DEPLOY_USER' is not in docker group"
fi

if [ -d "/home/$DEPLOY_USER/.ssh" ]; then
    check_pass "SSH directory exists for $DEPLOY_USER"

    # Check permissions
    SSH_DIR_PERMS=$(stat -c %a "/home/$DEPLOY_USER/.ssh" 2>/dev/null || stat -f %A "/home/$DEPLOY_USER/.ssh" 2>/dev/null)
    if [ "$SSH_DIR_PERMS" = "700" ]; then
        check_pass "SSH directory has correct permissions (700)"
    else
        check_warn "SSH directory permissions are $SSH_DIR_PERMS (should be 700)"
    fi
else
    check_fail "SSH directory missing for $DEPLOY_USER"
fi

if [ -f "/home/$DEPLOY_USER/.ssh/authorized_keys" ]; then
    KEY_COUNT=$(wc -l < "/home/$DEPLOY_USER/.ssh/authorized_keys")
    check_pass "authorized_keys file exists ($KEY_COUNT keys)"
else
    check_warn "authorized_keys file missing (needed for GitHub Actions)"
fi

# =============================================================================
# 4. Sudo Permissions
# =============================================================================
echo -e "\n${YELLOW}[4] Checking sudo permissions...${NC}"

if [ -f "/etc/sudoers.d/deploy-nginx" ]; then
    check_pass "Sudo config file exists for nginx commands"

    # Verify it contains the right permissions
    if grep -q "NOPASSWD.*nginx" /etc/sudoers.d/deploy-nginx; then
        check_pass "Nginx sudo permissions configured correctly"
    else
        check_warn "Nginx sudo permissions may be incomplete"
    fi
else
    check_fail "Sudo config file missing (/etc/sudoers.d/deploy-nginx)"
fi

# =============================================================================
# 5. Deployment Directory
# =============================================================================
echo -e "\n${YELLOW}[5] Checking deployment directory...${NC}"

if [ -d "$DEPLOY_DIR" ]; then
    check_pass "Deployment directory exists ($DEPLOY_DIR)"

    # Check ownership
    OWNER=$(stat -c %U "$DEPLOY_DIR" 2>/dev/null || stat -f %Su "$DEPLOY_DIR" 2>/dev/null)
    if [ "$OWNER" = "$DEPLOY_USER" ]; then
        check_pass "Deployment directory owned by $DEPLOY_USER"
    else
        check_warn "Deployment directory owned by $OWNER (should be $DEPLOY_USER)"
    fi
else
    check_fail "Deployment directory missing ($DEPLOY_DIR)"
fi

if [ -d "$DEPLOY_DIR/.git" ]; then
    check_pass "Git repository cloned"
else
    check_warn "Git repository not cloned yet"
fi

# Check required subdirectories
for dir in nginx exports backups logs; do
    if [ -d "$DEPLOY_DIR/$dir" ]; then
        check_pass "Directory exists: $dir"
    else
        check_warn "Directory missing: $dir"
    fi
done

# =============================================================================
# 6. Nginx Blue-Green Configuration
# =============================================================================
echo -e "\n${YELLOW}[6] Checking nginx blue-green config...${NC}"

if [ -f "$DEPLOY_DIR/nginx/nginx-blue.conf" ]; then
    check_pass "nginx-blue.conf exists"
else
    check_fail "nginx-blue.conf missing (needed for blue-green)"
fi

if [ -f "$DEPLOY_DIR/nginx/nginx-green.conf" ]; then
    check_pass "nginx-green.conf exists"
else
    check_fail "nginx-green.conf missing (needed for blue-green)"
fi

if [ -f "/etc/nginx/sites-enabled/boardofone.conf" ]; then
    check_pass "Active nginx config exists"

    # Check which environment is active
    if grep -q "api_backend_blue" /etc/nginx/sites-enabled/boardofone.conf; then
        check_pass "Currently using BLUE environment"
    elif grep -q "api_backend_green" /etc/nginx/sites-enabled/boardofone.conf; then
        check_pass "Currently using GREEN environment"
    else
        check_warn "Cannot determine active environment"
    fi
else
    check_warn "Active nginx config missing (/etc/nginx/sites-enabled/boardofone.conf)"
fi

# =============================================================================
# 7. SSL Certificates
# =============================================================================
echo -e "\n${YELLOW}[7] Checking SSL certificates...${NC}"

if [ -d "/etc/nginx/ssl" ]; then
    check_pass "SSL directory exists"
else
    check_fail "SSL directory missing (/etc/nginx/ssl)"
fi

if [ -f "/etc/nginx/ssl/boardofone.crt" ] && [ -f "/etc/nginx/ssl/boardofone.key" ]; then
    check_pass "SSL certificate and key exist"

    # Check expiration
    EXPIRY=$(openssl x509 -enddate -noout -in /etc/nginx/ssl/boardofone.crt 2>/dev/null | cut -d= -f2)
    if [ -n "$EXPIRY" ]; then
        check_pass "Certificate expires: $EXPIRY"
    fi
else
    check_warn "SSL certificate not generated yet (run: make generate-ssl)"
fi

# =============================================================================
# 8. Firewall Configuration
# =============================================================================
echo -e "\n${YELLOW}[8] Checking firewall...${NC}"

if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        check_pass "UFW firewall is active"

        # Check required ports
        if ufw status | grep -q "80.*ALLOW"; then
            check_pass "Port 80 (HTTP) is open"
        else
            check_warn "Port 80 (HTTP) is not open"
        fi

        if ufw status | grep -q "443.*ALLOW"; then
            check_pass "Port 443 (HTTPS) is open"
        else
            check_warn "Port 443 (HTTPS) is not open"
        fi

        if ufw status | grep -qE "22.*ALLOW|ssh.*ALLOW"; then
            check_pass "Port 22 (SSH) is open"
        else
            check_fail "Port 22 (SSH) is not open (you may be locked out!)"
        fi
    else
        check_warn "UFW firewall is not active"
    fi
else
    check_warn "UFW is not installed"
fi

# =============================================================================
# 9. Docker Test
# =============================================================================
echo -e "\n${YELLOW}[9] Testing Docker access for $DEPLOY_USER...${NC}"

if sudo -u $DEPLOY_USER docker ps &> /dev/null; then
    check_pass "$DEPLOY_USER can run Docker commands"
else
    check_warn "$DEPLOY_USER cannot run Docker (may need logout/login)"
fi

# =============================================================================
# 10. Environment File
# =============================================================================
echo -e "\n${YELLOW}[10] Checking environment configuration...${NC}"

if [ -f "$DEPLOY_DIR/.env" ]; then
    check_pass ".env file exists"

    # Check for required variables (without revealing values)
    REQUIRED_VARS=(
        "ANTHROPIC_API_KEY"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "SUPABASE_JWT_SECRET"
        "ADMIN_API_KEY"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^$var=" "$DEPLOY_DIR/.env"; then
            check_pass "$var is set"
        else
            check_warn "$var is missing from .env"
        fi
    done
else
    check_warn ".env file missing (copy from .env.example)"
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Verification Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Passed:${NC}   $CHECKS_PASSED"
echo -e "${YELLOW}Warnings:${NC} $CHECKS_WARNING"
echo -e "${RED}Failed:${NC}   $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Server is ready for deployment!${NC}"
    echo ""
    echo -e "Next steps:"
    echo -e "1. Generate SSH keys: ${YELLOW}bash deployment-scripts/setup-github-ssh-keys.sh${NC}"
    echo -e "2. Add public key to server: ${YELLOW}/home/$DEPLOY_USER/.ssh/authorized_keys${NC}"
    echo -e "3. Add secrets to GitHub repository"
    echo -e "4. Run deployment from GitHub Actions"
    exit 0
else
    echo -e "${RED}✗ Server setup is incomplete${NC}"
    echo ""
    echo -e "Please fix the failed checks above before deploying."
    echo -e "Re-run this script after making changes: ${YELLOW}bash deployment-scripts/verify-server-setup.sh${NC}"
    exit 1
fi
