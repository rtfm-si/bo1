#!/bin/bash
# DigitalOcean Droplet Setup Script for Board of One
# Run this script on a fresh Ubuntu 22.04 droplet

set -e

echo "🚀 Setting up Board of One on DigitalOcean Droplet"

# Update system
echo "📦 Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
apt-get install -y docker-compose-plugin

# Install nginx
echo "🌐 Installing nginx..."
apt-get install -y nginx certbot python3-certbot-nginx

# Create app user
echo "👤 Creating application user..."
useradd -m -s /bin/bash -G docker boardofone || true

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p /opt/boardofone
mkdir -p /opt/boardofone/backups/postgres
mkdir -p /opt/boardofone/backups/redis
mkdir -p /var/log/boardofone
chown -R boardofone:boardofone /opt/boardofone
chown -R boardofone:boardofone /var/log/boardofone

# Clone repository (you'll need to set this up)
echo "📥 Cloning repository..."
cd /opt/boardofone
# Option 1: Clone from GitHub (preferred)
# git clone https://github.com/yourusername/bo1.git .
# Option 2: Manual copy (for initial setup)
echo "⚠️  You need to manually copy your code to /opt/boardofone"
echo "    or set up git clone in this script"

# Create .env.production file
echo "⚙️  Creating .env.production template..."
cat > /opt/boardofone/.env.production.template <<'EOF'
# Database
POSTGRES_USER=boardofone
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=boardofone
DATABASE_URL=postgresql://boardofone:CHANGE_ME_STRONG_PASSWORD@postgres:5432/boardofone

# Redis
REDIS_URL=redis://redis:6379

# API Keys (REQUIRED)
ANTHROPIC_API_KEY=sk-ant-your-key-here
VOYAGE_API_KEY=your-voyage-key-here

# Admin
ADMIN_API_KEY=CHANGE_ME_ADMIN_KEY
ADMIN_USER_ID=admin

# Auth (disabled for MVP)
ENABLE_SUPABASE_AUTH=false

# CORS
CORS_ORIGINS=https://boardofone.com,https://www.boardofone.com

# Rate Limiting
RATE_LIMIT_ENABLED=true

# Docker Images (set by GitHub Actions)
API_IMAGE=ghcr.io/yourusername/bo1/api:production-latest
FRONTEND_IMAGE=ghcr.io/yourusername/bo1/frontend:production-latest

# Frontend
PUBLIC_API_URL=https://boardofone.com

# Environment
ENVIRONMENT=production
LOG_LEVEL=info
EOF

echo "⚠️  IMPORTANT: Edit /opt/boardofone/.env.production and set your secrets!"
echo "    Then copy it to .env: cp .env.production .env"

# Setup nginx
echo "🌐 Setting up nginx..."
rm -f /etc/nginx/sites-enabled/default

# Copy nginx config (you'll customize this)
cat > /etc/nginx/sites-available/boardofone <<'EOF'
# Placeholder nginx config
# The real config will be copied from /opt/boardofone/nginx/nginx.conf
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/boardofone /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Setup SSL with Let's Encrypt
echo "🔒 Setting up SSL (you'll need to configure your domain first)..."
echo "    Run: certbot --nginx -d boardofone.com -d www.boardofone.com"
echo "    This will be done manually after DNS is configured"

# Setup firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw status

# Setup log rotation
echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/boardofone <<'EOF'
/var/log/boardofone/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 boardofone boardofone
    sharedscripts
    postrotate
        docker-compose -f /opt/boardofone/docker-compose.prod.yml kill -s USR1 api
    endscript
}
EOF

# Setup backup cron job
echo "💾 Setting up backup cron job..."
cat > /opt/boardofone/deployment-scripts/backup.sh <<'EOF'
#!/bin/bash
# Backup script for Board of One

BACKUP_DIR="/opt/boardofone/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup PostgreSQL
docker exec boardofone-postgres pg_dump -U boardofone boardofone | gzip > "${BACKUP_DIR}/postgres/backup_${DATE}.sql.gz"

# Backup Redis
docker exec boardofone-redis redis-cli --rdb /data/dump.rdb
docker cp boardofone-redis:/data/dump.rdb "${BACKUP_DIR}/redis/backup_${DATE}.rdb"

# Remove backups older than 7 days
find "${BACKUP_DIR}/postgres" -name "backup_*.sql.gz" -mtime +7 -delete
find "${BACKUP_DIR}/redis" -name "backup_*.rdb" -mtime +7 -delete

echo "✅ Backup completed: ${DATE}"
EOF

chmod +x /opt/boardofone/deployment-scripts/backup.sh

# Add to crontab (run daily at 2 AM)
(crontab -u boardofone -l 2>/dev/null; echo "0 2 * * * /opt/boardofone/deployment-scripts/backup.sh >> /var/log/boardofone/backup.log 2>&1") | crontab -u boardofone -

# Setup monitoring (optional - basic health check)
echo "📊 Setting up basic monitoring..."
cat > /opt/boardofone/deployment-scripts/healthcheck.sh <<'EOF'
#!/bin/bash
# Basic health check script

if ! curl -f -s http://localhost:8000/api/health > /dev/null; then
    echo "❌ API health check failed at $(date)" >> /var/log/boardofone/healthcheck.log
    # Send alert (implement ntfy.sh or email)
    curl -H "Title: ⚠️ Board of One API Down" \
         -H "Priority: urgent" \
         -d "API health check failed on production server" \
         https://ntfy.sh/your-topic || true
fi
EOF

chmod +x /opt/boardofone/deployment-scripts/healthcheck.sh

# Add to crontab (run every 5 minutes)
(crontab -u boardofone -l 2>/dev/null; echo "*/5 * * * * /opt/boardofone/deployment-scripts/healthcheck.sh") | crontab -u boardofone -

# Print setup summary
echo ""
echo "✅ DigitalOcean Droplet setup complete!"
echo ""
echo "📋 Next Steps:"
echo "   1. Configure DNS: Point boardofone.com to this droplet's IP"
echo "   2. Edit /opt/boardofone/.env.production with your secrets"
echo "   3. Copy to .env: cp .env.production .env"
echo "   4. Setup SSL: certbot --nginx -d boardofone.com -d www.boardofone.com"
echo "   5. Login to GitHub Container Registry:"
echo "      docker login ghcr.io -u YOUR_GITHUB_USERNAME"
echo "   6. Pull and start services:"
echo "      cd /opt/boardofone"
echo "      docker-compose -f docker-compose.prod.yml pull"
echo "      docker-compose -f docker-compose.prod.yml up -d"
echo "   7. Run migrations:"
echo "      docker-compose -f docker-compose.prod.yml exec api alembic upgrade head"
echo "   8. Check logs:"
echo "      docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🔒 Security Reminders:"
echo "   - Change all passwords in .env"
echo "   - Disable root SSH login"
echo "   - Setup SSH key authentication only"
echo "   - Configure fail2ban"
echo "   - Review firewall rules"
echo ""
echo "📊 Monitoring:"
echo "   - Health checks run every 5 minutes"
echo "   - Backups run daily at 2 AM"
echo "   - Logs in /var/log/boardofone/"
echo ""
