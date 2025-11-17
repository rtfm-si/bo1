#!/bin/bash
# Manual deployment script for Board of One
# Use this for local testing or manual deployments

set -e

echo "🚀 Deploying Board of One to DigitalOcean"

# Configuration
DROPLET_IP="${DROPLET_IP:-your-droplet-ip}"
DROPLET_USER="${DROPLET_USER:-root}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we have required env vars
if [ "$DROPLET_IP" == "your-droplet-ip" ]; then
    echo -e "${RED}❌ Error: Set DROPLET_IP environment variable${NC}"
    echo "Usage: DROPLET_IP=123.456.789.0 ./deploy-manual.sh"
    exit 1
fi

echo -e "${GREEN}📦 Building Docker images locally...${NC}"
docker-compose -f docker-compose.prod.yml build

echo -e "${GREEN}💾 Saving Docker images...${NC}"
docker save -o /tmp/boardofone-api.tar boardofone-api:latest
docker save -o /tmp/boardofone-frontend.tar boardofone-frontend:latest

echo -e "${GREEN}📤 Copying images to droplet...${NC}"
scp -i "$SSH_KEY" /tmp/boardofone-api.tar "${DROPLET_USER}@${DROPLET_IP}:/tmp/"
scp -i "$SSH_KEY" /tmp/boardofone-frontend.tar "${DROPLET_USER}@${DROPLET_IP}:/tmp/"

echo -e "${GREEN}📤 Copying docker-compose.prod.yml...${NC}"
scp -i "$SSH_KEY" docker-compose.prod.yml "${DROPLET_USER}@${DROPLET_IP}:/opt/boardofone/"

echo -e "${GREEN}🚀 Deploying on droplet...${NC}"
ssh -i "$SSH_KEY" "${DROPLET_USER}@${DROPLET_IP}" << 'ENDSSH'
cd /opt/boardofone

# Load images
echo "Loading Docker images..."
docker load -i /tmp/boardofone-api.tar
docker load -i /tmp/boardofone-frontend.tar

# Tag images
docker tag boardofone-api:latest ghcr.io/si/bo1/api:production-latest
docker tag boardofone-frontend:latest ghcr.io/si/bo1/frontend:production-latest

# Stop old containers
echo "Stopping old containers..."
docker-compose -f docker-compose.prod.yml down

# Start new containers
echo "Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services
echo "Waiting for services to start..."
sleep 15

# Run migrations
echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T api alembic upgrade head

# Health checks
echo "Running health checks..."
for i in {1..10}; do
    if curl --fail --silent http://localhost:8000/api/health; then
        echo "✅ API is healthy"
        break
    fi
    echo "Waiting for API... ($i/10)"
    sleep 3
    if [ $i -eq 10 ]; then
        echo "❌ API health check failed"
        docker-compose -f docker-compose.prod.yml logs api
        exit 1
    fi
done

# Cleanup
rm -f /tmp/boardofone-api.tar /tmp/boardofone-frontend.tar

echo "✅ Deployment successful!"
docker-compose -f docker-compose.prod.yml ps

ENDSSH

# Cleanup local files
rm -f /tmp/boardofone-api.tar /tmp/boardofone-frontend.tar

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${YELLOW}📊 Check status:${NC}"
echo "   ssh -i $SSH_KEY ${DROPLET_USER}@${DROPLET_IP} 'cd /opt/boardofone && docker-compose -f docker-compose.prod.yml ps'"
echo ""
echo -e "${YELLOW}📝 View logs:${NC}"
echo "   ssh -i $SSH_KEY ${DROPLET_USER}@${DROPLET_IP} 'cd /opt/boardofone && docker-compose -f docker-compose.prod.yml logs -f'"
echo ""
