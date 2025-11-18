# Quick Deploy Reference

## TL;DR - Deploy in 3 Commands

```bash
make generate-ssl  # Generate SSL cert (if needed)
make deploy        # Deploy everything
make prod-status   # Verify all services running
```

---

## What Was Fixed

**Problem**: `boardof.one/design-system-demo` → 404 Not Found

**Cause**: Frontend service missing from production deployment

**Fix**: Added frontend + nginx services to `docker-compose.prod.yml`

---

## Verify It Works

```bash
# After deployment, test these URLs:
curl -k https://localhost/                    # Landing page
curl -k https://localhost/design-system-demo  # Design system
curl -k https://localhost/api/health          # API health check
```

---

## Production Deployment (On Server)

```bash
# 1. Pull latest code
git pull origin main

# 2. Deploy
make deploy

# 3. Verify
make prod-status
```

---

## Services Running After Deploy

```
✅ bo1-nginx-prod         (port 80, 443)   - Reverse proxy
✅ bo1-frontend-prod      (internal 3000)  - SvelteKit web UI
✅ bo1-api-prod           (internal 8000)  - FastAPI backend
✅ bo1-postgres-prod      (internal 5432)  - Database
✅ bo1-redis-prod         (internal 6379)  - Cache/sessions
✅ bo1-supabase-auth-prod (internal 9999)  - Authentication
```

---

## Useful Commands

```bash
# Check status
make prod-status

# View logs
make prod-logs

# Restart everything
make prod-restart

# Stop everything
make prod-down
```

---

## Documentation

- **Full deployment guide**: `DEPLOYMENT_GUIDE.md`
- **Frontend fix details**: `FRONTEND_DEPLOYMENT_FIX.md`
- **Makefile help**: `make help`

---

## Production URLs

After DNS is configured:

- Landing: `https://boardof.one/`
- Design System: `https://boardof.one/design-system-demo`
- API Health: `https://boardof.one/api/health`
- API Docs (admin): `https://boardof.one/admin/docs`
