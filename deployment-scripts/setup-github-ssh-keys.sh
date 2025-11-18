#!/bin/bash
# =============================================================================
# Board of One - GitHub Actions SSH Key Setup
# =============================================================================
# This script generates SSH keys for GitHub Actions deployment and provides
# instructions for adding them to your production server and GitHub secrets.
#
# Usage:
#   bash deployment-scripts/setup-github-ssh-keys.sh
#
# What this script does:
# 1. Generates ED25519 SSH key pair (modern, secure)
# 2. Saves private key (for GitHub secrets)
# 3. Saves public key (for production server)
# 4. Provides step-by-step instructions for setup
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
KEY_DIR="$HOME/.ssh/boardofone-deploy"
PRIVATE_KEY_FILE="$KEY_DIR/id_ed25519"
PUBLIC_KEY_FILE="$KEY_DIR/id_ed25519.pub"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}GitHub Actions SSH Key Generator${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Create directory
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"

# Check if keys already exist
if [ -f "$PRIVATE_KEY_FILE" ]; then
    echo -e "${YELLOW}⚠ SSH keys already exist at $KEY_DIR${NC}"
    read -p "Overwrite existing keys? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing keys."
    else
        rm -f "$PRIVATE_KEY_FILE" "$PUBLIC_KEY_FILE"
    fi
fi

# Generate SSH key pair
if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    echo -e "\n${YELLOW}Generating SSH key pair...${NC}"
    ssh-keygen -t ed25519 -C "github-actions-boardofone" -f "$PRIVATE_KEY_FILE" -N ""
    echo -e "${GREEN}✓ SSH keys generated${NC}"
fi

chmod 600 "$PRIVATE_KEY_FILE"
chmod 644 "$PUBLIC_KEY_FILE"

# =============================================================================
# Display Instructions
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ SSH Keys Generated Successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Keys saved to:${NC}"
echo -e "  Private: ${BLUE}$PRIVATE_KEY_FILE${NC}"
echo -e "  Public:  ${BLUE}$PUBLIC_KEY_FILE${NC}"
echo ""

# =============================================================================
# Step 1: Add public key to production server
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}STEP 1: Add Public Key to Server${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Copy this PUBLIC KEY to your production server:${NC}"
echo ""
echo -e "${BLUE}---BEGIN PUBLIC KEY---${NC}"
cat "$PUBLIC_KEY_FILE"
echo -e "${BLUE}---END PUBLIC KEY---${NC}"
echo ""
echo -e "${YELLOW}On your production server, run:${NC}"
echo ""
echo -e "  ${BLUE}# SSH into your server${NC}"
echo -e "  ssh root@YOUR_SERVER_IP"
echo ""
echo -e "  ${BLUE}# Add public key to deploy user's authorized_keys${NC}"
echo -e "  echo \"$(cat $PUBLIC_KEY_FILE)\" >> /home/deploy/.ssh/authorized_keys"
echo ""
echo -e "  ${BLUE}# Set correct permissions${NC}"
echo -e "  chown deploy:deploy /home/deploy/.ssh/authorized_keys"
echo -e "  chmod 600 /home/deploy/.ssh/authorized_keys"
echo ""

# =============================================================================
# Step 2: Test SSH connection
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}STEP 2: Test SSH Connection${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}After adding the public key, test the connection:${NC}"
echo ""
echo -e "  ${BLUE}ssh -i $PRIVATE_KEY_FILE deploy@YOUR_SERVER_IP${NC}"
echo ""
echo -e "You should be able to SSH without a password."
echo ""

# =============================================================================
# Step 3: Add private key to GitHub secrets
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}STEP 3: Add to GitHub Secrets${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}1. Go to your GitHub repository${NC}"
echo -e "2. Click Settings → Secrets and variables → Actions"
echo -e "3. Click 'New repository secret'"
echo -e "4. Add the following secrets:"
echo ""

# Display private key for GitHub secret
echo -e "${YELLOW}Secret Name: ${GREEN}PRODUCTION_SSH_KEY${NC}"
echo -e "${YELLOW}Secret Value (copy everything below):${NC}"
echo ""
echo -e "${BLUE}---BEGIN PRIVATE KEY---${NC}"
cat "$PRIVATE_KEY_FILE"
echo -e "${BLUE}---END PRIVATE KEY---${NC}"
echo ""

# Display other required secrets
echo -e "${YELLOW}Also add these secrets:${NC}"
echo ""
echo -e "  ${GREEN}PRODUCTION_HOST${NC}"
echo -e "  Value: ${BLUE}YOUR_SERVER_IP${NC} (e.g., 123.45.67.89 or boardof.one)"
echo ""
echo -e "  ${GREEN}PRODUCTION_USER${NC}"
echo -e "  Value: ${BLUE}deploy${NC}"
echo ""
echo -e "  ${GREEN}PRODUCTION_SSH_PORT${NC}"
echo -e "  Value: ${BLUE}22${NC} (or your custom SSH port)"
echo ""

# =============================================================================
# Step 4: Quick copy commands
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Quick Copy Commands${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Public key (for server):${NC}"
echo -e "  cat $PUBLIC_KEY_FILE | pbcopy  ${BLUE}# macOS${NC}"
echo -e "  cat $PUBLIC_KEY_FILE | xclip -selection clipboard  ${BLUE}# Linux${NC}"
echo ""
echo -e "${YELLOW}Private key (for GitHub):${NC}"
echo -e "  cat $PRIVATE_KEY_FILE | pbcopy  ${BLUE}# macOS${NC}"
echo -e "  cat $PRIVATE_KEY_FILE | xclip -selection clipboard  ${BLUE}# Linux${NC}"
echo ""

# =============================================================================
# Security Reminder
# =============================================================================
echo -e "${RED}========================================${NC}"
echo -e "${RED}⚠ SECURITY REMINDER${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}NEVER commit the private key to git!${NC}"
echo -e "${YELLOW}Keep $PRIVATE_KEY_FILE secure.${NC}"
echo ""
echo -e "The private key is only for GitHub Secrets."
echo -e "Only the public key goes on the server."
echo ""

# =============================================================================
# Test command
# =============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Your Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "After completing all steps, test your deployment:"
echo ""
echo -e "  ${BLUE}1. Go to GitHub Actions tab${NC}"
echo -e "  ${BLUE}2. Select 'Deploy to Production' workflow${NC}"
echo -e "  ${BLUE}3. Click 'Run workflow'${NC}"
echo -e "  ${BLUE}4. Type 'deploy-to-production'${NC}"
echo -e "  ${BLUE}5. Watch the deployment logs${NC}"
echo ""
echo -e "${GREEN}Setup complete! 🚀${NC}"
echo ""
