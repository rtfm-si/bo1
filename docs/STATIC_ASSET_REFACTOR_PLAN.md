# Static Asset Serving & API URL Fix - Implementation Plan

**Status**: Planning
**Priority**: High - Production Performance Issue
**Created**: 2025-11-22
**Estimated Time**: 4-6 hours implementation + testing

---

## Executive Summary

### Current Problems

1. **Static assets proxied through Node.js**: All requests (including static JS/CSS/images) go through the SvelteKit Node.js server, causing unnecessary latency and load
2. **PUBLIC_API_URL inconsistency**: Mixed build-time and runtime resolution causes localhost:8000 to appear in production builds
3. **CSS preload warnings**: Browser complains about unused preloaded resources

### Root Causes (Research Findings)

**Problem 1: HTTP/2 + Connection Limits**
- nginx `limit_conn` counts each HTTP/2 stream as a separate connection
- SvelteKit loads ~25+ assets in parallel → exceeds limit → 503 errors
- Current "fix": Removed connection limit (band-aid solution)

**Problem 2: Environment Variable Resolution**
- **Build-time**: `import.meta.env.PUBLIC_API_URL` embeds value during `npm run build`
- **Runtime**: `$env/dynamic/public` reads from Node.js process.env
- Files using build-time resolution: `auth.ts`, `supertokens.ts`, `login.svelte`
- Files using runtime resolution: `client.ts`, `sse.ts`
- If runtime env var missing → falls back to `'http://localhost:8000'`

**Problem 3: Asset Serving Flow**
```
Browser → nginx (proxy_pass) → Node.js:3000 → build/client/* → response
```
Should be:
```
Static:  Browser → nginx → build/client/* (direct file serve)
Dynamic: Browser → nginx → Node.js:3000 (SSR/API)
```

---

## Phase 1: Architecture Design (30 minutes)

### Option Analysis

#### **Option A: Shared Volume Between Containers** ⭐ **RECOMMENDED**

**Approach**:
- Frontend container writes `build/client/` to shared volume during startup
- nginx mounts same volume and serves files directly
- Node.js continues serving SSR routes

**Pros**:
- Simplest for blue-green deployments (each environment has own volume)
- No nginx image rebuild needed
- Easy rollback (just swap nginx config)

**Cons**:
- Requires volume management
- Slight complexity in docker-compose

**Implementation**:
```yaml
# docker-compose.app.yml
volumes:
  frontend-static-blue:
  frontend-static-green:

services:
  frontend:
    volumes:
      - frontend-static-${ENV}:/app/build/client:ro  # Read-only for nginx
    command: >
      sh -c "cp -r /app/build/client/* /app/static-volume/ && node build"

  # Host nginx (via deployment script)
  # Mount: /var/lib/docker/volumes/frontend-static-${ENV}/_data → /var/www/boardofone/static
```

```nginx
# nginx config
location /_app/ {
    alias /var/www/boardofone/static/_app/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location ~* \.(svg|png|jpg|jpeg|gif|ico)$ {
    root /var/www/boardofone/static;
    expires 1y;
}

location / {
    proxy_pass http://frontend_backend;  # SSR routes
}
```

---

#### **Option B: Multi-stage Build with nginx Image**

**Approach**:
- Build frontend in Docker stage 1
- Copy `build/client/` to nginx image in stage 2
- Run two containers: nginx (static) + Node.js (SSR)

**Pros**:
- Cleanest separation of concerns
- nginx optimized for static serving
- Smaller Node.js container (no static files)

**Cons**:
- Requires nginx container management
- More complex blue-green switching
- SSL/proxy config duplication

**Implementation**:
```dockerfile
# Dockerfile.frontend-nginx
FROM nginx:1.25-alpine
COPY --from=frontend-builder /app/build/client /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
```

**Decision**: Defer to Phase 2+ (too complex for immediate fix)

---

#### **Option C: Single Container (nginx + Node.js)**

**Approach**:
- Install nginx in frontend container
- nginx:80 serves static files locally
- nginx proxies SSR to localhost:3000 (Node.js)
- External nginx proxies to frontend:80

**Pros**:
- No volume sharing needed
- Single container deployment

**Cons**:
- Heavier container image
- Mixing web server and app server
- Non-standard architecture

**Decision**: Reject (anti-pattern)

---

### Recommended Solution: **Option A (Shared Volume)**

**Rationale**:
1. Minimal changes to existing blue-green deployment
2. nginx on host already configured (just add static paths)
3. Easy rollback (unmount volume)
4. Clear separation: nginx=static, Node.js=dynamic

---

## Phase 2: Implementation - Static Asset Serving (2-3 hours)

### Step 2.1: Update Docker Configuration

**File**: `docker-compose.app.yml`

```yaml
volumes:
  # Define named volumes for blue/green static assets
  frontend-static:
    driver: local

services:
  frontend:
    volumes:
      # Mount build/client as read-only for nginx consumption
      - frontend-static:/app/build/client:ro

    # Copy static files to volume on startup (before starting server)
    entrypoint: /bin/sh
    command: >
      -c "
        echo 'Copying static assets to shared volume...' &&
        cp -r /app/build/client/* /static-volume/ &&
        echo 'Static assets ready. Starting Node.js server...' &&
        exec node build
      "
```

**Issue**: `build/client` is inside the container, not easily mountable.

**Better Approach**: Use deployment script to extract and mount.

---

### Step 2.2: Update Deployment Script

**File**: `deployment-scripts/deploy-blue-green.sh`

Add after container startup:

```bash
# Extract static assets from container to host filesystem
echo "📦 Extracting static assets..."

# Create static asset directory for this deployment
STATIC_DIR="/var/www/boardofone/static-${TARGET_ENV}"
mkdir -p "$STATIC_DIR"

# Copy static files from container
docker cp "${TARGET_PROJECT}-frontend-1:/app/build/client/." "$STATIC_DIR/"

# Set permissions
chown -R www-data:www-data "$STATIC_DIR"
chmod -R 755 "$STATIC_DIR"

echo "✅ Static assets extracted to $STATIC_DIR"
```

---

### Step 2.3: Update nginx Configuration

**File**: `nginx/nginx-blue.conf` and `nginx/nginx-green.conf`

```nginx
# Add above 'location /' block

# Serve SvelteKit static assets directly (immutable, versioned)
location /_app/immutable/ {
    alias /var/www/boardofone/static-ENV/_app/immutable/;  # Replace ENV with blue/green

    # Aggressive caching for immutable assets
    expires 1y;
    add_header Cache-Control "public, immutable";
    add_header X-Served-By "nginx-direct";

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;

    # Enable gzip
    gzip_static on;

    # Disable access logs for performance
    access_log off;
}

# Serve version manifest
location /_app/version.json {
    alias /var/www/boardofone/static-ENV/_app/version.json;
    expires 5m;  # Short cache for version checks
    add_header Cache-Control "public, max-age=300";
}

# Serve static images (logo, favicon, etc.)
location ~* ^/(logo\.svg|logo\.png|favicon\.svg|demo_meeting\.jpg)$ {
    root /var/www/boardofone/static-ENV;
    expires 1d;
    add_header Cache-Control "public, max-age=86400";
    add_header X-Served-By "nginx-direct";
    access_log off;
}

# Remove the nested location block for static assets (no longer needed)
# Frontend (SvelteKit) - SSR routes only
location / {
    proxy_pass http://frontend_backend_blue;  # or green
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection "";

    # NO nested location block here anymore
}
```

**Changes**:
1. Added `location /_app/immutable/` - serves versioned chunks directly
2. Added `location /_app/version.json` - serves SvelteKit manifest
3. Added `location ~* ^/(logo\.svg|...)` - serves root-level images
4. Removed nested `location ~* \.(js|css|...)` - no longer needed

---

### Step 2.4: Update Deployment Script for nginx Config

**File**: `deployment-scripts/deploy-blue-green.sh`

Replace `ENV` placeholder in nginx config:

```bash
# After copying nginx config to /etc/nginx/sites-available/

# Replace ENV placeholder with actual environment
sed -i "s/static-ENV/static-${TARGET_ENV}/g" /etc/nginx/sites-available/boardofone

# Test and reload nginx
nginx -t && systemctl reload nginx
```

---

### Step 2.5: Testing Plan

**Test Cases**:
1. ✅ Static JS chunks load with `X-Served-By: nginx-direct` header
2. ✅ Images load directly from nginx (not proxied)
3. ✅ SSR routes still work (dynamic pages)
4. ✅ Blue-green swap maintains static asset serving
5. ✅ Cache headers correct (`immutable` for chunks, `max-age` for images)

**Commands**:
```bash
# Verify static asset headers
curl -I https://boardof.one/_app/immutable/chunks/xxx.js | grep "X-Served-By"
# Should show: X-Served-By: nginx-direct

# Verify SSR still works
curl https://boardof.one/ | grep "<!DOCTYPE html>"
# Should return HTML

# Check access logs (should NOT log static asset requests)
tail -f /var/log/nginx/boardofone-blue-access.log
# Refresh page - should only see / request, not _app/* requests
```

---

## Phase 3: Fix PUBLIC_API_URL Resolution (1-2 hours)

### Problem Analysis

**Current State** (from research):
- `auth.ts:21` → `import.meta.env.PUBLIC_API_URL` (build-time)
- `supertokens.ts:26` → `import.meta.env.PUBLIC_API_URL` (build-time)
- `login.svelte:61` → `import.meta.env.PUBLIC_API_URL` (build-time)
- `client.ts:42` → `env.PUBLIC_API_URL` from `$env/dynamic/public` (runtime) ✅
- `sse.ts:161` → `env.PUBLIC_API_URL` from `$env/dynamic/public` (runtime) ✅

**Issue**: Build-time resolution embeds `https://boardof.one` into the bundle. If the runtime env var is missing or different, it doesn't update.

**Evidence**: Browser console shows `localhost:8000` → means runtime env var is undefined/missing.

---

### Step 3.1: Standardize on Runtime Resolution

**Approach**: Change all `import.meta.env.PUBLIC_API_URL` to use `$env/dynamic/public`

**File**: `frontend/src/lib/stores/auth.ts`

```typescript
// BEFORE (line 21)
const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

// AFTER
import { env } from '$env/dynamic/public';

const API_BASE_URL = env.PUBLIC_API_URL || (() => {
  if (import.meta.env.DEV) return 'http://localhost:8000';
  throw new Error('PUBLIC_API_URL environment variable is required in production');
})();
```

**File**: `frontend/src/lib/supertokens.ts`

```typescript
// BEFORE (line 26)
Session.init({
  apiDomain: import.meta.env.PUBLIC_API_URL || "http://localhost:8000",
  // ...
});

// AFTER
import { env } from '$env/dynamic/public';

Session.init({
  apiDomain: env.PUBLIC_API_URL || (() => {
    if (import.meta.env.DEV) return 'http://localhost:8000';
    console.error('PUBLIC_API_URL not set, falling back to localhost');
    return 'http://localhost:8000';
  })(),
  // ...
});
```

**File**: `frontend/src/routes/(auth)/login/+page.svelte`

```typescript
// BEFORE (line 61)
const apiUrl = import.meta.env.PUBLIC_API_URL || "http://localhost:8000";

// AFTER
import { env } from '$env/dynamic/public';

const apiUrl = env.PUBLIC_API_URL || (import.meta.env.DEV
  ? "http://localhost:8000"
  : (() => { throw new Error('PUBLIC_API_URL required'); })()
);
```

**File**: `frontend/src/routes/waitlist/+page.svelte`

```typescript
// BEFORE (lines 22-24)
const API_BASE_URL = browser
  ? import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
  : 'http://api:8000';

// AFTER
import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';

const API_BASE_URL = browser
  ? env.PUBLIC_API_URL || 'http://localhost:8000'  // Runtime resolution
  : 'http://api:8000';  // SSR: use Docker service name
```

**Rationale**:
- **Development**: Fallback to localhost is fine
- **Production**: Strict mode - fail fast if env var missing
- **Runtime resolution**: Works with blue-green deployments

---

### Step 3.2: Verify Environment Variable Propagation

**Check**: Ensure docker-compose passes env vars correctly

**File**: `docker-compose.app.yml` (already correct)

```yaml
frontend:
  environment:
    - PUBLIC_API_URL=https://boardof.one  # ✅ Correct
```

**Test on server**:
```bash
# SSH into server
docker exec boardofone-frontend-1 printenv PUBLIC_API_URL
# Should output: https://boardof.one
```

---

### Step 3.3: Debugging - Why is it still localhost?

**Hypothesis**: SvelteKit's `$env/dynamic/public` requires the env var to be:
1. Prefixed with `PUBLIC_`
2. Available in Node.js process environment
3. Explicitly exposed via adapter config

**Check**: `frontend/svelte.config.js` (line 16)

```javascript
adapter: adapter({
  out: 'build',
  precompress: false,
  envPrefix: ''  // ⚠️ Empty string - might be the issue!
})
```

**Fix**:
```javascript
adapter: adapter({
  out: 'build',
  precompress: false,
  envPrefix: 'PUBLIC_'  // Explicitly set prefix
})
```

**Alternative**: Use SvelteKit's built-in env handling

```javascript
// svelte.config.js - add to kit section
kit: {
  adapter: adapter({...}),
  env: {
    publicPrefix: 'PUBLIC_'  // Default, but make it explicit
  }
}
```

---

### Step 3.4: Test Runtime Resolution

**Local test**:
```bash
cd frontend
PUBLIC_API_URL=https://test.example.com npm run build
node build
# Open browser, check Network tab → API calls should go to test.example.com
```

**Production test after deployment**:
```bash
# Change env var
docker exec boardofone-frontend-1 sh -c 'export PUBLIC_API_URL=https://newdomain.com && node build' &

# Test in browser
# Should see API calls to newdomain.com
```

---

## Phase 4: Fix CSS Preload Warnings (30 minutes)

### Problem

Browser warning:
```
The resource at "https://boardof.one/_app/immutable/assets/0.SNZOPoCQ.css"
preloaded with link preload was not used within a few seconds.
```

**Cause**: SvelteKit generates `<link rel="preload">` for CSS, but:
1. CSS might not be used on initial route
2. Dynamic imports delay CSS usage
3. Vite over-optimizes preload hints

---

### Step 4.1: Disable Aggressive Preloading

**File**: `frontend/vite.config.ts`

```typescript
export default defineConfig({
  plugins: [sveltekit(), tailwindcss()],

  build: {
    // Reduce preload aggressiveness
    modulePreload: {
      polyfill: false,  // Disable polyfill (modern browsers only)
    },
  },

  server: {
    port: 5173,
    strictPort: false,
    host: true
  }
});
```

---

### Step 4.2: Optimize CSS Splitting

**File**: `frontend/vite.config.ts`

```typescript
export default defineConfig({
  plugins: [sveltekit(), tailwindcss()],

  build: {
    cssCodeSplit: true,  // Split CSS per route
    rollupOptions: {
      output: {
        manualChunks: {
          // Group vendor CSS separately
          vendor: ['svelte', '@sveltejs/kit'],
        },
      },
    },
  },
});
```

---

### Step 4.3: Alternative - Remove Preload Hints

**File**: Custom hook `frontend/src/hooks.server.ts`

```typescript
import type { Handle } from '@sveltejs/kit';

export const handle: Handle = async ({ event, resolve }) => {
  const response = await resolve(event, {
    transformPageChunk: ({ html }) => {
      // Remove CSS preload hints (keep modulepreload for JS)
      return html.replace(
        /<link[^>]*rel="preload"[^>]*as="style"[^>]*>/g,
        ''
      );
    },
  });

  return response;
};
```

**Note**: This is a workaround. Better to fix Vite config.

---

### Step 4.4: Verify CSS Loading

**Test**:
1. Open DevTools → Network tab
2. Filter by CSS
3. Check if CSS files load without warnings
4. Verify no duplicate CSS requests

---

## Phase 5: Testing & Validation (1 hour)

### Test Matrix

| Test Case | Expected Result | Verification |
|-----------|----------------|--------------|
| Static JS chunks served by nginx | ✅ `X-Served-By: nginx-direct` header | `curl -I https://boardof.one/_app/immutable/chunks/xxx.js` |
| Images served by nginx | ✅ `X-Served-By: nginx-direct` header | `curl -I https://boardof.one/logo.svg` |
| SSR routes work | ✅ HTML returned | `curl https://boardof.one/` |
| API calls use production URL | ✅ `https://boardof.one/api/*` | Browser DevTools → Network |
| No localhost:8000 in console | ✅ No CSP errors | Browser Console → no errors |
| CSS loads without warnings | ✅ No preload warnings | Browser Console → no warnings |
| Blue-green swap works | ✅ Static assets switch correctly | Deploy to green, test assets |

---

### Acceptance Criteria

**Must Have**:
- [ ] No 503 errors on page load
- [ ] Static assets served directly by nginx (not proxied)
- [ ] All API calls use `https://boardof.one` (no localhost)
- [ ] No CSP violations in browser console
- [ ] Blue-green deployment swaps static assets correctly

**Nice to Have**:
- [ ] No CSS preload warnings
- [ ] Sub-100ms TTFB for static assets
- [ ] nginx access logs show reduced traffic (static assets not logged)

---

## Rollback Plan

If issues occur after deployment:

```bash
# 1. Revert nginx config
cp /etc/nginx/sites-available/boardofone.backup /etc/nginx/sites-available/boardofone
nginx -t && systemctl reload nginx

# 2. Remove static asset directory
rm -rf /var/www/boardofone/static-blue
rm -rf /var/www/boardofone/static-green

# 3. Restart containers (will serve via Node.js again)
docker restart boardofone-frontend-1 boardofone-green-frontend-1
```

---

## Implementation Order

**Day 1** (2-3 hours):
1. ✅ Create this plan document
2. ✅ Update nginx config with static asset locations (nginx-blue.conf, nginx-green.conf)
3. ✅ Update deployment script to extract static assets (deploy-production.yml)
4. ⏸️ Test locally with volume mounts
5. ⏸️ Deploy to staging/green environment

**Day 2** (1-2 hours):
6. ✅ Fix PUBLIC_API_URL in frontend code (all files - auth.ts, supertokens.ts, login.svelte, waitlist.svelte)
7. ✅ Update svelte.config.js env prefix (set envPrefix: 'PUBLIC_')
8. ⏸️ Rebuild frontend with correct env var handling
9. ⏸️ Test in browser (no localhost in console)

**Day 3** (1 hour):
10. ⏸️ Fix CSS preload warnings (vite.config.ts)
11. ⏸️ Run full test suite
12. ⏸️ Deploy to production (blue-green)
13. ⏸️ Monitor for issues

---

## Success Metrics

**Performance**:
- Static asset TTFB: < 50ms (currently ~100-200ms via Node.js)
- Page load time: < 2s (currently ~3-5s)
- Reduced Node.js CPU usage: -30%

**Correctness**:
- Zero CSP violations
- Zero 503 errors
- Zero localhost:8000 references in production

**Maintainability**:
- Clear separation: nginx=static, Node.js=SSR
- Easy blue-green deployments
- Documented rollback procedure

---

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Create feature branch**: `git checkout -b fix/static-asset-serving`
3. **Implement Phase 2** (static asset serving)
4. **Test locally** with docker-compose
5. **Deploy to green** environment
6. **Validate** all test cases
7. **Implement Phase 3** (PUBLIC_API_URL)
8. **Deploy to production** (blue swap)
9. **Monitor** for 24 hours
10. **Document** findings in postmortem

---

## Questions to Answer Before Implementation

1. ❓ Do we need to serve `build/prerendered/` pages? (Check if any routes are prerendered)
2. ❓ Should we version the static asset directory? (`static-blue-v1`, `static-blue-v2`)
3. ❓ What's the disk space impact? (`du -sh /var/www/boardofone/static-*`)
4. ❓ Do we need to clean up old static asset directories? (Cron job?)
5. ❓ Should we add monitoring for nginx static asset serving? (Prometheus metrics?)

---

## References

- [SvelteKit Adapter Node Docs](https://kit.svelte.dev/docs/adapter-node)
- [nginx Static File Serving](https://nginx.org/en/docs/http/ngx_http_core_module.html#location)
- [nginx HTTP/2 Module](https://nginx.org/en/docs/http/ngx_http_v2_module.html)
- [SvelteKit Environment Variables](https://kit.svelte.dev/docs/modules#$env-dynamic-public)
- [Vite Build Optimization](https://vitejs.dev/guide/build.html)

---

**Document Status**: ✅ Complete - Ready for Review
**Last Updated**: 2025-11-22 12:30 UTC
**Next Action**: Review plan → Implement Phase 2
