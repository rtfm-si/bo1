# Board of One - Production Deployment Guide

**Status**: Frontend service added to `docker-compose.prod.yml` ✅

## Issue Resolved

The design system demo (and all frontend pages) were not accessible on `boardof.one/design-system-demo` because:

1. **Missing frontend service** in `docker-compose.prod.yml`
2. **Missing nginx service** to handle routing and SSL termination

**Fix Applied**: Added both `frontend` and `nginx` services to production compose file.

---

## Prerequisites

### 1. SSL Certificates

You need SSL certificates for HTTPS. Two options:

#### Option A: Let's Encrypt (Recommended - Free)

```bash
# On your production server
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Generate certificates
sudo certbot certonly --standalone -d boardof.one -d www.boardof.one

# Certificates will be in /etc/letsencrypt/live/boardof.one/
```

#### Option B: Self-Signed (Development/Testing Only)

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/boardofone.key \
  -out nginx/ssl/boardofone.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=boardof.one"

# Set permissions
chmod 600 nginx/ssl/boardofone.key
chmod 644 nginx/ssl/boardofone.crt
```

### 2. Environment Variables

Ensure your `.env` file has all required variables:

```bash
# Required for frontend
PUBLIC_API_URL=https://boardof.one/api
ORIGIN=https://boardof.one

# Required for SSL in docker-compose
SITE_URL=https://boardof.one

# All other variables from .env.example
```

---

## Deployment Steps

### Step 1: Update SSL Certificate Paths (if using Let's Encrypt)

Edit `docker-compose.prod.yml` nginx volumes section:

```yaml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt/live/boardof.one:/etc/nginx/ssl:ro  # Let's Encrypt path
    - nginx-logs:/var/log/nginx
    - nginx-cache:/var/cache/nginx
```

### Step 2: Build and Deploy

```bash
# Stop any running containers
docker-compose -f docker-compose.prod.yml down

# Build all services (including frontend)
docker-compose -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

Expected output:
```
NAME                    STATUS              PORTS
bo1-api-prod           Up (healthy)         127.0.0.1:8000->8000/tcp
bo1-frontend-prod      Up (healthy)         127.0.0.1:3000->3000/tcp
bo1-nginx-prod         Up                   0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
bo1-postgres-prod      Up (healthy)         127.0.0.1:5432->5432/tcp
bo1-redis-prod         Up (healthy)         127.0.0.1:6379->6379/tcp
bo1-supabase-auth-prod Up                   127.0.0.1:9999->9999/tcp
```

### Step 3: Verify Services

```bash
# Check frontend is accessible
curl -k https://localhost/

# Check design system demo
curl -k https://localhost/design-system-demo

# Check API health
curl -k https://localhost/api/health

# View logs
docker-compose -f docker-compose.prod.yml logs frontend
docker-compose -f docker-compose.prod.yml logs nginx
```

### Step 4: DNS Configuration

Ensure your domain DNS points to your server:

```
A Record:     boardof.one        → YOUR_SERVER_IP
A Record:     www.boardof.one    → YOUR_SERVER_IP
```

Wait for DNS propagation (5-30 minutes), then test:

```bash
# From your local machine
curl https://boardof.one/
curl https://boardof.one/design-system-demo
curl https://boardof.one/api/health
```

---

## Service Architecture

```
Internet (443/80)
       ↓
    Nginx (reverse proxy)
       ↓
  ┌────┴────┐
  ↓         ↓
Frontend  API
(3000)   (8000)
  ↓         ↓
  └─────────┴───→ PostgreSQL (5432)
      ↓          └→ Redis (6379)
      └→ Supabase Auth (9999)
```

### Port Mapping (Production)

- **80, 443** → Nginx (public, SSL termination)
- **3000** → Frontend (internal only, proxied by nginx)
- **8000** → API (internal only, proxied by nginx)
- **5432** → PostgreSQL (internal only, localhost bind)
- **6379** → Redis (internal only, localhost bind)
- **9999** → Supabase Auth (internal only, localhost bind)

**Security**: Only ports 80 and 443 are exposed to the internet. All other services are internal or localhost-only.

---

## Troubleshooting

### Frontend Not Building

```bash
# Check frontend build logs
docker-compose -f docker-compose.prod.yml logs frontend

# Common issue: missing dependencies
docker-compose -f docker-compose.prod.yml exec frontend npm install
docker-compose -f docker-compose.prod.yml restart frontend
```

### 502 Bad Gateway

```bash
# Check if frontend is running
docker-compose -f docker-compose.prod.yml ps frontend

# Check frontend health
docker-compose -f docker-compose.prod.yml exec frontend wget -O- http://localhost:3000

# Restart frontend
docker-compose -f docker-compose.prod.yml restart frontend
```

### SSL Certificate Issues

```bash
# Check nginx SSL configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Check certificate paths
docker-compose -f docker-compose.prod.yml exec nginx ls -la /etc/nginx/ssl/

# View nginx logs
docker-compose -f docker-compose.prod.yml logs nginx
```

### Design System Demo 404

If `/design-system-demo` returns 404:

1. **Check route exists**:
   ```bash
   ls frontend/src/routes/design-system-demo/+page.svelte
   ```

2. **Rebuild frontend**:
   ```bash
   docker-compose -f docker-compose.prod.yml build frontend
   docker-compose -f docker-compose.prod.yml up -d frontend
   ```

3. **Check nginx routing**:
   ```bash
   # Should proxy all non-/api requests to frontend
   docker-compose -f docker-compose.prod.yml exec nginx cat /etc/nginx/nginx.conf | grep "location /"
   ```

---

## Rollback Plan

If deployment fails:

```bash
# Stop production containers
docker-compose -f docker-compose.prod.yml down

# Remove new images
docker image rm bo1-frontend-prod

# Restart with previous configuration
git checkout HEAD~1 docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d
```

---

## Performance Tuning

### Frontend Response Time

Expected: <200ms for static pages, <500ms for API calls

Monitor with:
```bash
curl -w "@curl-format.txt" -o /dev/null -s https://boardof.one/design-system-demo

# curl-format.txt:
# time_namelookup:  %{time_namelookup}\n
# time_connect:     %{time_connect}\n
# time_starttransfer: %{time_starttransfer}\n
# time_total:       %{time_total}\n
```

### Resource Usage

```bash
# Check container resource usage
docker stats bo1-frontend-prod bo1-nginx-prod

# Expected:
# Frontend: ~100-200MB RAM, <5% CPU (idle)
# Nginx: ~10-20MB RAM, <2% CPU
```

---

## Next Steps After Deployment

1. **Enable monitoring** (Week 10-11):
   - Uptime monitoring (UptimeRobot, Pingdom)
   - Error tracking (Sentry)
   - Performance monitoring (Grafana)

2. **Set up automated backups**:
   ```bash
   # Add to crontab
   0 2 * * * docker-compose -f /path/to/docker-compose.prod.yml exec -T postgres pg_dump -U bo1 boardofone > /backups/postgres_$(date +\%Y\%m\%d).sql
   ```

3. **Configure log rotation**:
   ```bash
   # nginx logs rotation (systemd-journald handles docker logs)
   docker-compose -f docker-compose.prod.yml exec nginx sh -c "find /var/log/nginx -name '*.log' -mtime +7 -delete"
   ```

4. **Enable CI/CD** (optional):
   - GitHub Actions for automated deployments
   - Blue-green deployment for zero downtime

---

## Testing Checklist

Before considering deployment complete:

- [ ] HTTPS works: `https://boardof.one/`
- [ ] Landing page loads: `https://boardof.one/`
- [ ] Design system demo accessible: `https://boardof.one/design-system-demo`
- [ ] API health check works: `https://boardof.one/api/health`
- [ ] API docs accessible (admin only): `https://boardof.one/admin/docs`
- [ ] No SSL certificate warnings
- [ ] All containers healthy: `docker-compose -f docker-compose.prod.yml ps`
- [ ] Logs show no errors: `docker-compose -f docker-compose.prod.yml logs --tail=100`
- [ ] Response time <500ms for all pages
- [ ] Resource usage within limits (see Performance Tuning)

---

## Support

If issues persist:

1. **Check logs**: `docker-compose -f docker-compose.prod.yml logs --tail=200 --follow`
2. **Check service health**: `docker-compose -f docker-compose.prod.yml ps`
3. **Restart specific service**: `docker-compose -f docker-compose.prod.yml restart <service>`
4. **Full restart**: `docker-compose -f docker-compose.prod.yml restart`

**Note**: The frontend and nginx services are now part of the production stack. If you were previously deploying without them, this explains why the design system demo was not accessible.
