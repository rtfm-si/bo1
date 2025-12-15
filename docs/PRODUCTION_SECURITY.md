# Production Security Checklist

## Service Exposure Summary

| Service | Port | Binding | Auth | Status |
|---------|------|---------|------|--------|
| PostgreSQL | 5432 | 127.0.0.1 | Password | ✅ Internal only |
| Redis | 6379 | 127.0.0.1 | Password | ✅ Internal only |
| SuperTokens | 3567 | 127.0.0.1 | API Key | ✅ Internal only |
| API | 8000 | 127.0.0.1 | SuperTokens + Rate limit | ✅ Via nginx |
| Frontend | 3000 | 127.0.0.1 | Public | ✅ Via nginx |
| Grafana | 3200 | 127.0.0.1 | Basic auth + Grafana login | ✅ Via nginx |
| Prometheus | 9090 | 127.0.0.1 | Basic auth | ✅ Via nginx |
| ntfy | 2586 | 127.0.0.1 | Push-only | ✅ Internal only |

## Access URLs

- **Main app:** https://boardof.one
- **Monitoring:** https://monitoring.boardof.one (requires basic auth)
  - Grafana: https://monitoring.boardof.one/
  - Prometheus: https://monitoring.boardof.one/prometheus/

## Required Credentials

### 1. Database (PostgreSQL)
```bash
# Generate password
openssl rand -hex 32
```
- Set in `.env` as `POSTGRES_PASSWORD`
- Used in `DATABASE_URL`

### 2. Redis
```bash
# Generate password (hex only, no special chars)
openssl rand -hex 32
```
- Set in `.env` as `REDIS_PASSWORD`
- Used in `REDIS_URL`

### 3. SuperTokens API Key
```bash
openssl rand -hex 32
```
- Set in `.env` as `SUPERTOKENS_API_KEY`

### 4. Admin API Key
```bash
openssl rand -hex 32
```
- Set in `.env` as `ADMIN_API_KEY`
- Used for `/api/admin/*` endpoints

### 5. Nginx Basic Auth (Monitoring)
```bash
# On production server
htpasswd -c /etc/nginx/.htpasswd bo1admin
# Enter password when prompted
```
- Protects https://monitoring.boardof.one

### 6. Grafana Admin
```bash
# Generate password
openssl rand -base64 24

# Change on running container
docker exec infrastructure-grafana-1 grafana-cli admin reset-admin-password '<password>'
```
- Or set via env: `GRAFANA_ADMIN_PASSWORD`

## Nginx Security Headers

All responses include:
- `Strict-Transport-Security` (HSTS)
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy`
- `Referrer-Policy: strict-origin-when-cross-origin`

## Reverse Proxy IP Trust

**Critical Security Setting**: `TRUSTED_PROXY_IPS`

When the API runs behind a reverse proxy (Nginx, load balancer, CDN), it must know which proxy IPs to trust for `X-Forwarded-For` headers. The `_get_client_ip()` function in `backend/api/middleware/auth.py` uses this setting.

### IP Spoofing Risk

**Danger**: If `TRUSTED_PROXY_IPS` is misconfigured:
- Attackers can spoof their IP by sending fake `X-Forwarded-For` headers
- Rate limiting becomes ineffective (attacker rotates spoofed IPs)
- Audit logs record false client IPs
- IP-based blocking/allowlisting fails

### Safe Configuration

| Scenario | TRUSTED_PROXY_IPS | Notes |
|----------|-------------------|-------|
| Direct (no proxy) | `""` (empty) | Default - ignore X-Forwarded-For |
| Single Nginx | Nginx server IP | Only trust your Nginx |
| Load balancer | LB internal IPs | Trust only your LB range |
| CDN + Origin | CDN IPs + Origin proxy | Multi-hop chain |

### Never Do

- ❌ `TRUSTED_PROXY_IPS=*` or trust all IPs
- ❌ Trust public/external IPs you don't control
- ❌ Trust 0.0.0.0/0 or overly broad CIDR ranges
- ❌ Leave empty in production when behind a proxy (rate limiting will target proxy, not clients)

### Verification

```bash
# Verify only your proxy IP is trusted
grep TRUSTED_PROXY_IPS /opt/boardofone/.env

# Test - this should NOT work (spoofed header ignored)
curl -H "X-Forwarded-For: 8.8.8.8" https://boardof.one/api/health
# Rate limiting should use your real IP, not 8.8.8.8
```

---

## Rate Limiting

| Endpoint | Limit | Burst |
|----------|-------|-------|
| `/api/*` | 10 req/s | 20 |
| `/api/v1/sessions` (POST) | 2 req/min | 1 |
| `/api/admin/*` | 10 req/min | 5 |

## SSL/TLS

- Let's Encrypt certificates (auto-renewal via certbot)
- TLS 1.2 and 1.3 only
- Strong cipher suites

## Firewall (UFW)

```bash
# Only these ports should be open externally
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (redirects to HTTPS)
ufw allow 443/tcp  # HTTPS
```

## Secrets Management

**Never commit to git:**
- `.env` files
- SSL private keys
- API keys
- Database passwords

**Stored in:**
- Production: `/root/infrastructure/.env` and `/root/boardofone-green/.env`
- Secrets should be rotated quarterly

## Monitoring Alerts

Configured via Alertmanager → ntfy.sh:
- High error rate (>1% for 5min)
- High latency (P95 >1s for 5min)
- Low availability (<99% for 10min)
- Service down (API, Redis, Postgres)
- High memory usage (>90%)

## Backup & Recovery

- PostgreSQL: Daily backups enabled
- Redis: AOF + RDB persistence
- See `docs/DISASTER_RECOVERY.md` for procedures

## Security Audit Checklist

- [ ] All default passwords changed
- [ ] UFW firewall enabled
- [ ] SSL certificates valid
- [ ] Rate limiting configured
- [ ] Admin endpoints protected
- [ ] Monitoring accessible only via basic auth
- [ ] Secrets not in git history
- [ ] Dependencies scanned for vulnerabilities
