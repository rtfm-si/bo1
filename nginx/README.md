# Nginx Configuration for Blue-Green Deployment

This directory contains nginx configurations for Board of One's blue-green deployment system.

## Files

### `nginx.conf` (Development/Docker)
**Purpose:** Development environment nginx configuration
**Used in:** Docker Compose (`docker-compose.yml`, `docker-compose.prod.yml`)
**Container:** `bo1-nginx-prod`

**Upstreams:**
- `api:8000` - FastAPI backend container
- `frontend:3000` - SvelteKit frontend container

**Use case:** When nginx runs inside Docker (dev/local testing)

---

### `nginx-blue.conf` (Production - Blue Environment)
**Purpose:** Production nginx config pointing to **blue** environment containers
**Used in:** Blue-green deployments (active/stable environment)
**Location on server:** `/etc/nginx/sites-enabled/boardofone.conf` (copied during deployment)

**Upstreams:**
- `boardofone-api-1:8000` - Blue API container
- `boardofone-frontend-1:3000` - Blue frontend container

**Header:** `X-Environment: blue`

**When active:**
- Normal production operation (99% of the time)
- After successful green promotion
- During green environment testing (blue handles live traffic)

---

### `nginx-green.conf` (Production - Green Environment)
**Purpose:** Production nginx config pointing to **green** environment containers
**Used in:** Blue-green deployments (new/testing environment)
**Location on server:** `/etc/nginx/sites-enabled/boardofone.conf` (copied during deployment)

**Upstreams:**
- `boardofone-green-api-1:8000` - Green API container
- `boardofone-green-frontend-1:3000` - Green frontend container

**Header:** `X-Environment: green`

**When active:**
- During deployment (testing new version)
- 2-minute monitoring period after traffic cutover
- Temporary state before promotion to blue

---

## Blue-Green Deployment Flow

### Normal State (Blue Active)

```
nginx (blue config) → boardofone-api-1 → Live traffic
                   → boardofone-frontend-1
```

### Deployment State (Testing Green)

```
nginx (blue config) → boardofone-api-1 → Live traffic (existing users)
                   → boardofone-frontend-1

# Green starts (new version)
                      boardofone-green-api-1 (health checks)
                      boardofone-green-frontend-1
```

### Cutover State (Green Active, Blue Draining)

```
nginx (green config) → boardofone-green-api-1 → New traffic
                    → boardofone-green-frontend-1

# Blue still running (active SSE connections finish)
                       boardofone-api-1 (draining)
                       boardofone-frontend-1
```

### Final State (Green Promoted to Blue)

```
nginx (blue config) → boardofone-api-1 → Live traffic (promoted from green)
                   → boardofone-frontend-1

# Green stopped, ready for next deployment
```

---

## Configuration Differences

### Key Differences Between Blue and Green Configs

Both configs are **identical** except for:

1. **Upstream names:**
   - Blue: `api_backend_blue` / `frontend_backend_blue`
   - Green: `api_backend_green` / `frontend_backend_green`

2. **Container targets:**
   - Blue: `boardofone-api-1` / `boardofone-frontend-1`
   - Green: `boardofone-green-api-1` / `boardofone-green-frontend-1`

3. **Environment header:**
   - Blue: `X-Environment: blue`
   - Green: `X-Environment: green`

4. **Log files:**
   - Blue: `/var/log/nginx/boardofone-blue-access.log`
   - Green: `/var/log/nginx/boardofone-green-access.log`

### Shared Configuration

Both configs include:
- ✅ SSL/TLS (HTTPS)
- ✅ Rate limiting (10 req/s API, 2 req/min sessions)
- ✅ Security headers (HSTS, CSP, etc.)
- ✅ SSE streaming support (no buffering)
- ✅ Static asset caching
- ✅ Health check endpoints
- ✅ Connection limits (10 per IP)
- ✅ WAF rules (SQLi, XSS, path traversal, scanner blocking)

---

## Usage on Production Server

### Initial Setup

```bash
# Copy blue config as initial active config
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### During Deployment (Automated by GitHub Actions)

```bash
# 1. Start green environment
docker-compose -f docker-compose.prod.yml -p boardofone-green up -d

# 2. Health checks pass

# 3. Switch to green config
sudo cp /opt/boardofone/nginx/nginx-green.conf /etc/nginx/sites-enabled/boardofone.conf
sudo nginx -t && sudo systemctl reload nginx

# 4. Monitor for 2 minutes

# 5. If successful, promote green to blue
docker-compose -f docker-compose.prod.yml -p boardofone down  # Stop old blue
docker-compose -f docker-compose.prod.yml -p boardofone-green down  # Stop green
docker-compose -f docker-compose.prod.yml up -d  # Start new blue

# 6. Switch back to blue config (now pointing to promoted containers)
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
sudo nginx -t && sudo systemctl reload nginx
```

### Manual Rollback

```bash
# If green deployment fails, rollback to blue
sudo cp /opt/boardofone/nginx/nginx-blue.conf /etc/nginx/sites-enabled/boardofone.conf
sudo nginx -t && sudo systemctl reload nginx

# Stop green environment
docker-compose -f docker-compose.prod.yml -p boardofone-green down
```

---

## Checking Active Environment

### From Server

```bash
# Check which config is active
cat /etc/nginx/sites-enabled/boardofone.conf | grep "upstream.*backend"

# Expected output:
# Blue active:  upstream api_backend_blue
# Green active: upstream api_backend_green
```

### From Client

```bash
# Check environment header
curl -I https://boardof.one/api/health

# Look for:
# X-Environment: blue   (normal)
# X-Environment: green  (during deployment testing)
```

---

## SSL Certificates

All configs expect SSL certificates at:
- Certificate: `/etc/nginx/ssl/boardofone.crt`
- Private key: `/etc/nginx/ssl/boardofone.key`

**Generate certificates:**

```bash
# Option 1: Let's Encrypt (recommended)
sudo certbot --nginx -d boardof.one -d www.boardof.one
sudo ln -s /etc/letsencrypt/live/boardof.one/fullchain.pem /etc/nginx/ssl/boardofone.crt
sudo ln -s /etc/letsencrypt/live/boardof.one/privkey.pem /etc/nginx/ssl/boardofone.key

# Option 2: Self-signed (testing only)
cd /opt/boardofone
make generate-ssl
```

---

## Rate Limiting

### API Endpoints
- **General API:** 10 requests/second, burst 20
- **Session creation:** 2 requests/minute, burst 1
- **SSE streaming:** No rate limit (long-lived connections)

### Configuration Zones

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=session_limit:10m rate=2r/m;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
```

### Per-Client Limits
- **Concurrent connections:** 10 per IP
- **Session creation:** 2 per minute per IP
- **API calls:** 10 per second per IP (burst up to 20)

---

## Debugging

### Test nginx configuration

```bash
# Syntax check
sudo nginx -t

# Verbose test
sudo nginx -T | less
```

### View active configuration

```bash
# Show which upstreams are defined
sudo nginx -T | grep "upstream.*backend"

# Show SSL configuration
sudo nginx -T | grep ssl_certificate
```

### Monitor logs

```bash
# Blue environment logs
sudo tail -f /var/log/nginx/boardofone-blue-access.log
sudo tail -f /var/log/nginx/boardofone-blue-error.log

# Green environment logs (during deployment)
sudo tail -f /var/log/nginx/boardofone-green-access.log
sudo tail -f /var/log/nginx/boardofone-green-error.log

# All nginx logs
sudo tail -f /var/log/nginx/*.log
```

### Test upstream connectivity

```bash
# From inside API container
docker exec boardofone-api-1 curl http://localhost:8000/api/health

# From nginx container (if running in Docker)
docker exec bo1-nginx-prod curl http://api:8000/api/health

# From host (through nginx)
curl http://localhost/api/health
curl https://boardof.one/api/health
```

---

## Security Considerations

### Enabled Headers

```nginx
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: (set by SvelteKit with nonce-based scripts)
```

### Disabled Sensitive Information

```nginx
server_tokens off;  # Don't reveal nginx version
access_log off;     # For health check endpoints only
```

### WAF (Web Application Firewall)

Both blue and green configs include WAF rules that block:

**SQL Injection:**
- UNION SELECT attacks
- OR-based bypass (`' OR '1'='1`)
- SQL keywords in suspicious context
- Comment-based injection (`--`, `/* */`)

**XSS (Cross-Site Scripting):**
- Script tags (`<script>`, `</script>`)
- Event handlers (`onerror=`, `onload=`, etc.)
- JavaScript protocol (`javascript:`)
- Base64 data URIs

**Path Traversal:**
- Directory traversal (`../`, `..%2f`)
- Null byte injection (`%00`)
- Windows path variants

**Scanner/Probe Detection:**
- Sensitive files (`.env`, `.git/`, `.htaccess`)
- WordPress/PHP probes (`wp-admin`, `phpmyadmin`)
- AWS metadata endpoint
- Known malicious user agents (sqlmap, nikto, etc.)

**Allowlisted Endpoints (bypass WAF):**
- `/api/v1/datasets/*/ask` - Dataset Q&A can contain SQL/code
- `/api/v1/sessions/*/stream` - SSE streaming
- `/api/health`, `/api/ready` - Health checks
- OAuth callback endpoints

**WAF Logs:**
Blocked requests are logged to `/var/log/nginx/waf-blocked.log` with attack type indicators.

```bash
# View WAF blocked requests
sudo tail -f /var/log/nginx/waf-blocked.log

# Example log entry:
# 192.168.1.1 - [12/Dec/2025:10:00:00 +0000] "GET /.env HTTP/1.1" sqli=00 xss=00 traversal=0 probe=1 agent=0 ua="curl/7.68.0"
```

### SSL Configuration

- **Protocols:** TLSv1.2, TLSv1.3 only (no SSLv3, TLSv1.0, TLSv1.1)
- **Ciphers:** Modern, secure cipher suites only
- **HSTS:** Enabled with 1-year max-age, includeSubDomains, and preload directive

---

## HSTS Preload

### Current Configuration

All nginx configs include HSTS with preload support:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

### Preload Requirements (all met)

✅ Valid HTTPS certificate
✅ HTTP→HTTPS redirect (301) on port 80
✅ max-age >= 31536000 (1 year)
✅ includeSubDomains directive
✅ preload directive

### Submitting to HSTS Preload List

**⚠️ WARNING: HSTS preload is IRREVERSIBLE for ~3 months minimum. Once preloaded:**
- The domain MUST serve HTTPS forever
- ALL subdomains must support HTTPS
- Removal from the preload list takes months to propagate

**Manual Submission Steps:**

1. Verify eligibility: `GET /api/health/hsts` returns `preload_eligible: true`
2. Visit https://hstspreload.org
3. Enter domain: `boardof.one`
4. Review and acknowledge requirements
5. Submit for preload

**Verification After Submission:**

```bash
# Check preload status
curl https://hstspreload.org/api/v2/status?domain=boardof.one

# Expected states:
# - "status": "pending" (submitted, awaiting processing)
# - "status": "preloaded" (in Chrome preload list)
# - "status": "unknown" (not submitted)
```

### Health Check Endpoint

The API provides an HSTS compliance check:

```bash
curl https://boardof.one/api/health/hsts
```

Response:
```json
{
  "status": "compliant",
  "preload_eligible": true,
  "header_value": "max-age=31536000; includeSubDomains; preload",
  "checks": {
    "max_age_sufficient": true,
    "include_subdomains": true,
    "preload_directive": true
  },
  "message": "HSTS configuration meets all preload requirements",
  "submission_url": "https://hstspreload.org"
}
```

---

## Documentation

- **Blue-Green Deployment Flow:** [../docs/BLUE_GREEN_DEPLOYMENT.md](../docs/BLUE_GREEN_DEPLOYMENT.md)
- **Deployment Quickstart:** [../docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md](../docs/PRODUCTION_DEPLOYMENT_QUICKSTART.md)
- **Deployment Scripts:** [../deployment-scripts/README.md](../deployment-scripts/README.md)

---

## Troubleshooting

### Nginx won't start

```bash
# Check configuration
sudo nginx -t

# Check if port 80/443 already in use
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443

# View error log
sudo tail -50 /var/log/nginx/error.log
```

### 502 Bad Gateway

**Causes:**
- Upstream containers not running
- Wrong upstream container names
- Containers not on same Docker network

**Fix:**
```bash
# Check containers are running
docker ps | grep boardofone

# Check container names match nginx config
docker ps --format "{{.Names}}"

# Restart containers
docker-compose -f /opt/boardofone/docker-compose.prod.yml restart
```

### SSL Certificate Errors

```bash
# Check certificate exists
ls -l /etc/nginx/ssl/

# Check certificate expiration
openssl x509 -enddate -noout -in /etc/nginx/ssl/boardofone.crt

# Renew Let's Encrypt certificate
sudo certbot renew --nginx
```

### Rate Limiting Too Strict

**Edit configs and increase limits:**
```nginx
# Change from:
limit_req zone=api_limit burst=20 nodelay;

# To:
limit_req zone=api_limit burst=50 nodelay;
```

**Then reload:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Support

For issues related to:
- **Blue-green deployment:** See [BLUE_GREEN_DEPLOYMENT.md](../docs/BLUE_GREEN_DEPLOYMENT.md)
- **Server setup:** See [deployment-scripts/README.md](../deployment-scripts/README.md)
- **Nginx configuration:** Check logs in `/var/log/nginx/`
