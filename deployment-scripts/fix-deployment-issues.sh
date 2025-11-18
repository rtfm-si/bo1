#!/bin/bash
# =============================================================================
# Emergency Fix for Production Deployment Issues
# =============================================================================
# This script fixes the two deployment issues:
# 1. Missing POSTGRES_PASSWORD (creates .env from template)
# 2. nginx port conflict (removes nginx from override file)
#
# Run this on the production server:
#   ssh root@139.59.201.65
#   cd /opt/boardofone
#   bash deployment-scripts/fix-deployment-issues.sh
# =============================================================================

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Board of One - Emergency Deployment Fix${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running in correct directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ Error: docker-compose.prod.yml not found${NC}"
    echo "Please run this script from /opt/boardofone"
    exit 1
fi

# Confirm before proceeding
echo -e "${YELLOW}This script will:${NC}"
echo "1. Stop all running containers"
echo "2. Create/update .env file (will prompt for API keys if missing)"
echo "3. Remove nginx from docker-compose.prod.override.yml"
echo "4. Restart services"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# =============================================================================
# Step 1: Stop containers
# =============================================================================
echo -e "\n${YELLOW}[1/6] Stopping containers...${NC}"
docker-compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml down 2>/dev/null || true
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
echo -e "${GREEN}✓ Containers stopped${NC}"

# =============================================================================
# Step 2: Backup existing .env (if exists)
# =============================================================================
echo -e "\n${YELLOW}[2/6] Backing up existing files...${NC}"
if [ -f ".env" ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ Backed up existing .env${NC}"
fi
if [ -f "docker-compose.prod.override.yml" ]; then
    cp docker-compose.prod.override.yml docker-compose.prod.override.yml.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✓ Backed up existing override file${NC}"
fi

# =============================================================================
# Step 3: Verify .env file exists (don't overwrite!)
# =============================================================================
echo -e "\n${YELLOW}[3/6] Checking existing .env file...${NC}"

if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file already exists${NC}"

    # Verify required variables are set
    echo -e "${YELLOW}Verifying required variables...${NC}"
    MISSING_VARS=0

    source .env 2>/dev/null || true

    if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "REPLACE_WITH"* ]; then
        echo -e "${RED}❌ POSTGRES_PASSWORD not set or placeholder${NC}"
        MISSING_VARS=1
    fi

    if [ -z "$REDIS_PASSWORD" ] || [ "$REDIS_PASSWORD" = "REPLACE_WITH"* ]; then
        echo -e "${RED}❌ REDIS_PASSWORD not set or placeholder${NC}"
        MISSING_VARS=1
    fi

    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "REPLACE_WITH"* ]; then
        echo -e "${RED}❌ ANTHROPIC_API_KEY not set or placeholder${NC}"
        MISSING_VARS=1
    fi

    if [ $MISSING_VARS -eq 1 ]; then
        echo -e "${YELLOW}⚠ Some variables are missing or have placeholders${NC}"
        echo -e "Do you want to:"
        echo -e "  1) Use .env.production (git-crypt encrypted) as source"
        echo -e "  2) Keep existing .env and fix manually"
        echo -e "  3) Exit and fix manually"
        read -p "Choice (1/2/3): " -n 1 -r
        echo

        if [[ $REPLY == "1" ]]; then
            if [ -f ".env.production" ]; then
                if head -n 1 .env.production 2>/dev/null | grep -q "GCRPT"; then
                    echo -e "${RED}❌ .env.production is encrypted (git-crypt not unlocked)${NC}"
                    exit 1
                fi
                cp .env.production .env
                chmod 600 .env
                echo -e "${GREEN}✓ Copied .env.production to .env${NC}"
            else
                echo -e "${RED}❌ .env.production not found${NC}"
                exit 1
            fi
        elif [[ $REPLY == "3" ]]; then
            exit 0
        fi
        # Choice 2: continue with existing .env
    else
        echo -e "${GREEN}✓ All required variables are set${NC}"
    fi
else
    # No .env exists - try to use .env.production
    echo -e "${YELLOW}⚠ No .env file found${NC}"

    if [ -f ".env.production" ]; then
        if head -n 1 .env.production 2>/dev/null | grep -q "GCRPT"; then
            echo -e "${RED}❌ .env.production is encrypted (git-crypt not unlocked)${NC}"
            echo "Run: git-crypt unlock /path/to/key"
            exit 1
        fi

        echo -e "${GREEN}✓ Using .env.production as source${NC}"
        cp .env.production .env
        chmod 600 .env
    else
        echo -e "${RED}❌ No .env or .env.production found${NC}"
        echo "Please create .env manually or unlock git-crypt"
        exit 1
    fi
fi

echo -e "${GREEN}✓ .env file ready${NC}"

# =============================================================================
# Step 4: Create override file (no nginx)
# =============================================================================
echo -e "\n${YELLOW}[4/4] Creating override file (nginx excluded)...${NC}"

cat > docker-compose.prod.override.yml <<'OVERRIDE_EOF'
# Production-specific overrides (not tracked in git)
# NOTE: nginx runs standalone on host (not containerized)
# Containers expose ports only to localhost for host nginx to proxy
version: '3.8'
services: {}
OVERRIDE_EOF

echo -e "${GREEN}✓ Override file created${NC}"

# =============================================================================
# Print summary
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Fix Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Configuration Status:${NC}"
echo -e "  ✅ .env file verified"
echo -e "  ✅ Override file created (nginx excluded)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Start services: ${GREEN}docker-compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d${NC}"
echo "2. Check logs: ${GREEN}docker-compose -f docker-compose.prod.yml logs -f${NC}"
echo "3. Test health: ${GREEN}curl http://localhost:8000/api/health${NC}"
echo "4. Reload nginx: ${GREEN}sudo systemctl reload nginx${NC}"
echo ""

# Ask if user wants to start services now
read -p "Start services now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Starting services...${NC}"
    docker-compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d

    echo -e "\n${YELLOW}Waiting for services to start...${NC}"
    sleep 10

    echo -e "\n${YELLOW}Checking health...${NC}"
    if curl --fail --silent http://localhost:8000/api/health > /dev/null; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
    else
        echo -e "${RED}⚠ API health check failed - check logs${NC}"
    fi

    echo -e "\n${YELLOW}Container status:${NC}"
    docker ps --filter "name=bo1-"

    echo -e "\n${GREEN}Services started! Monitor logs with:${NC}"
    echo "docker-compose -f docker-compose.prod.yml logs -f"
fi

echo ""
echo -e "${GREEN}Done!${NC}"
