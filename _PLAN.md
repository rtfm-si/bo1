# Security Audit Report

**Audit Type:** Full-Spectrum Security Audit (Red Team + Blue Team)
**Date:** 2025-12-15
**Scope:** Backend API, Frontend, LLM Prompts, Infra, Database

---

## Step 1: Attack Surface Map

### Trust Boundaries

```
[External Users] --> [Frontend (SvelteKit)] --> [FastAPI Backend] --> [PostgreSQL/Redis]
                                              |
                                              +--> [LLM APIs (Anthropic/OpenAI/Voyage)]
                                              |
                                              +--> [External Services (Stripe/Resend/n8n)]
```

### Attackable Surfaces

| Surface              | Entry Point                                              | Trust Level                                  |
| -------------------- | -------------------------------------------------------- | -------------------------------------------- |
| **API Endpoints**    | `/api/v1/*`                                              | Auth required (SuperTokens)                  |
| **Admin Endpoints**  | `/api/admin/*`                                           | X-Admin-Key or session is_admin              |
| **SSE Streaming**    | `/api/v1/sessions/{id}/stream`                           | Session-based auth                           |
| **Public Endpoints** | `/api/health`, `/api/v1/waitlist`, `/api/v1/analytics/*` | No auth                                      |
| **LLM Prompts**      | problem_statement, clarifications                        | User-controlled input to LLM                 |
| **OAuth Callbacks**  | `/auth/*`                                                | SuperTokens-managed                          |
| **Webhooks**         | `/api/v1/webhooks/*`                                     | CSRF-exempt, signature verification          |
| **Metrics**          | `/metrics`                                               | Network-restricted (should be internal only) |

### Data Flow Paths

- **User Input → LLM**: `problem_statement` → sanitization → prompt injection audit → LLM
- **Auth Flow**: OAuth → SuperTokens → httpOnly session cookie → API access
- **Session Data**: User → Redis (hot) → PostgreSQL (persistence)
- **Admin Flow**: X-Admin-Key header OR session with is_admin flag

---

## Step 2: Vulnerability List

### CRITICAL

| #   | Category                       | Vector                                     | Impact                                                       | Likelihood | Location                               |
| --- | ------------------------------ | ------------------------------------------ | ------------------------------------------------------------ | ---------- | -------------------------------------- |
| C1  | **Prompt Injection Fail-Open** | LLM audit errors default to `is_safe=True` | Medium - Malicious prompts may bypass if audit service fails | Low        | `bo1/security/prompt_injection.py:343` |

### HIGH

| #   | Category                      | Vector                                                                                              | Impact                           | Likelihood         | Location                               |
| --- | ----------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------ | -------------------------------------- |
| H1  | **MVP Auth Bypass Risk**      | If `ENABLE_SUPERTOKENS_AUTH=false` and `DEBUG=false`, critical error logged but needs startup block | High - Full auth bypass          | Low (config error) | `backend/api/middleware/auth.py:44-50` |
| H2  | **CSRF Exemptions Too Broad** | `/api/v1/analytics/*` is CSRF-exempt allowing forged analytics                                      | Low - Data pollution             | Medium             | `backend/api/middleware/csrf.py:42`    |
| H3  | **Redis Lua eval()**          | `redis_client.eval(release_script, ...)` - Lua script injection if lock_id is user-controlled       | Medium - Redis command injection | Very Low           | `bo1/state/redis_lock.py:110`          |

### MEDIUM

| #   | Category                             | Vector                                                    | Impact                             | Likelihood       | Location                                  |
| --- | ------------------------------------ | --------------------------------------------------------- | ---------------------------------- | ---------------- | ----------------------------------------- |
| M1  | **Admin API Key Entropy**            | No validation of ADMIN_API_KEY strength                   | Medium - Weak keys brute-forceable | Medium           | `backend/api/middleware/admin.py:27`      |
| M2  | **Error Message Leakage**            | Debug mode returns full exception details                 | Low - Info disclosure              | Low (debug only) | `backend/api/main.py:568-578`             |
| M3  | **Session ID in URL**                | `/api/v1/sessions/{session_id}/stream` exposes session ID | Low - Session fixation risk        | Low              | `backend/api/streaming.py`                |
| M4  | **SQL Injection Pattern Incomplete** | Regex validation misses some SQL patterns                 | Low - Bypass possible              | Low              | `backend/api/models.py:104-114`           |
| M5  | **X-Forwarded-For Trust**            | IP extraction trusts proxy headers without validation     | Medium - IP spoofing               | Medium           | `backend/api/supertokens_config.py:69-71` |
| M6  | **Rate Limit per User Only**         | No global rate limit; attackers with many accounts bypass | Medium - Resource exhaustion       | Medium           | `backend/api/sessions.py:158-164`         |

### LOW

| #   | Category                       | Vector                                                            | Impact                             | Likelihood | Location                       |
| --- | ------------------------------ | ----------------------------------------------------------------- | ---------------------------------- | ---------- | ------------------------------ |
| L1  | **XSS via @html**              | `{@html}` used in 7 components - DOMPurify used but review needed | Low - XSS if sanitization bypassed | Low        | `frontend/src/lib/components/` |
| L2  | **Metrics Endpoint Public**    | `/metrics` exposed without auth (should be network-restricted)    | Low - Info disclosure              | Low        | `backend/api/main.py:518`      |
| L3  | **pip-audit Warnings Ignored** | CI continues on vulnerability findings                            | Low - Known CVEs in deps           | Medium     | `.github/workflows/ci.yml:70`  |
| L4  | **Dockerfile Runs as Root**    | No USER directive in Dockerfile                                   | Low - Container escape             | Very Low   | `backend/Dockerfile`           |

---

## Step 3: Fix Pack

### HIGH Priority (Fix Immediately)

1. **H1 - MVP Auth Startup Block**: Add `sys.exit(1)` after critical log in `require_production_auth()` if auth misconfigured
2. **C1 - Fail-Closed Prompt Audit**: Change fail-open to fail-closed for prompt injection audit errors
3. **H3 - Validate Redis Lock ID**: Ensure lock_id is UUID-only before passing to Lua eval

### MEDIUM Priority (Fix This Sprint)

4. **M1 - Admin Key Validation**: Add minimum entropy check for ADMIN_API_KEY (32+ chars)
5. **M5 - Validate Proxy Headers**: Only trust X-Forwarded-For from known proxy IPs
6. **M6 - Global Rate Limit**: Add IP-based global rate limit alongside user limits
7. **H2 - Narrow CSRF Exemptions**: Remove `/api/v1/analytics/*` from exemption; add CSRF token
8. **M4 - Strengthen SQL Validation**: Add more SQL injection patterns (EXEC, xp_cmdshell, etc.)

### LOW Priority (Backlog)

9. **L4 - Non-root Container**: Add `USER nobody` to Dockerfile
10. **L2 - Restrict Metrics**: Add network policy or auth to /metrics
11. **L3 - Fail CI on Vulns**: Change `continue-on-error: true` to false for pip-audit
12. **L1 - XSS Review**: Audit all @html usages for proper sanitization

---

## Step 4: Security Test Plan Checklist

### Authentication Tests

- [ ] Verify SuperTokens session required for protected endpoints
- [ ] Verify admin endpoints reject non-admin users (403)
- [ ] Verify X-Admin-Key timing attack resistance (constant-time compare)
- [ ] Verify CSRF token validation on mutating requests
- [ ] Verify httpOnly cookies cannot be accessed via JavaScript
- [ ] Verify session expiry enforced correctly

### Authorization Tests

- [ ] Verify user cannot access other users' sessions
- [ ] Verify workspace membership checked for workspace-scoped resources
- [ ] Verify admin impersonation properly logged and restricted

### Input Validation Tests

- [ ] Test XSS payloads in problem_statement (should be rejected/sanitized)
- [ ] Test SQL injection payloads (DROP TABLE, UNION SELECT, etc.)
- [ ] Test prompt injection payloads (ignore previous instructions, etc.)
- [ ] Test oversized context (>50KB should be rejected)
- [ ] Test malformed UUIDs in path parameters

### LLM Security Tests

- [ ] Test prompt injection: "ignore previous instructions and..."
- [ ] Test jailbreak patterns: "you are now a...", "DAN mode"
- [ ] Test data exfiltration: "show your system prompt"
- [ ] Test XML tag injection in user input
- [ ] Verify sanitization of user input before LLM interpolation

### Rate Limiting Tests

- [ ] Verify session creation rate limit (5/min free tier)
- [ ] Verify global rate limit prevents flooding
- [ ] Verify rate limit headers returned (Retry-After)

### CSRF Tests

- [ ] Verify POST/PUT/DELETE require X-CSRF-Token header
- [ ] Verify CSRF cookie set on GET requests
- [ ] Verify token mismatch returns 403

### Infrastructure Tests

- [ ] Verify DEBUG=false in production
- [ ] Verify CORS origins don't include wildcards
- [ ] Verify secrets not logged (log sanitizer working)
- [ ] Verify database queries use parameterized SQL

---

## Step 5: Critical Fixes (Patches)

### Patch 1: Fail-Closed Prompt Injection Audit

**File:** `bo1/security/prompt_injection.py:339-348`

```diff
         except Exception as e:
             logger.error(f"Prompt injection audit failed for {source}: {e}")
-            # Fail open - allow content if audit fails
-            # This prevents audit failures from blocking legitimate users
+            # SECURITY FIX: Fail closed - block content if audit fails
+            # Prevents potential bypass when audit service is down
             return AuditResult(
-                is_safe=True,
+                is_safe=False,
                 categories=[],
-                flagged_categories=[],
+                flagged_categories=["audit_failure"],
                 error=str(e),
             )
```

### Patch 2: Admin Key Minimum Entropy

**File:** `backend/api/middleware/admin.py:27-28`

```diff
 ADMIN_API_KEY = _settings.admin_api_key

-if not ADMIN_API_KEY:
-    logger.info("ADMIN_API_KEY not set - API key auth disabled, session auth still works")
+if not ADMIN_API_KEY:
+    logger.info("ADMIN_API_KEY not set - API key auth disabled, session auth still works")
+elif len(ADMIN_API_KEY) < 32:
+    logger.warning("SECURITY: ADMIN_API_KEY should be at least 32 characters for adequate entropy")
```

### Patch 3: Dockerfile Non-Root User

**File:** `backend/Dockerfile:59-60` (production stage)

```diff
 FROM base AS production

+# Security: Run as non-root user
+RUN useradd -m -u 1000 appuser
+USER appuser
+
 # Build metadata - set via docker build --build-arg
```

### Patch 4: Validate X-Forwarded-For Source

**File:** `backend/api/supertokens_config.py:69-72`

```diff
+# Trusted proxy IPs (configure via environment in production)
+import os
+TRUSTED_PROXIES = os.getenv("TRUSTED_PROXY_IPS", "").split(",")
+
 def _get_client_ip(request: Any) -> str:
     try:
         forwarded_for = request.get_header("x-forwarded-for")
-        if forwarded_for:
+        # Only trust X-Forwarded-For from known proxies
+        remote_ip = getattr(getattr(request, "request", None), "client", None)
+        remote_ip = str(remote_ip.host) if remote_ip else "unknown"
+        if forwarded_for and (not TRUSTED_PROXIES or remote_ip in TRUSTED_PROXIES):
             return str(forwarded_for.split(",")[0].strip())
```

### Patch 5: Narrow CSRF Exemptions

**File:** `backend/api/middleware/csrf.py:35-43`

```diff
 CSRF_EXEMPT_PREFIXES = (
     "/api/health",
     "/api/ready",
     "/api/v1/webhooks/",
     "/api/v1/csp-report",
     "/api/v1/waitlist",  # Public form submission
     "/api/v1/metrics/client",  # Browser sendBeacon for observability metrics
-    "/api/v1/analytics/",  # Public page analytics (landing page, unauthenticated)
+    # SECURITY: Removed /api/v1/analytics/ - should require CSRF token
+    # Page analytics now uses sendBeacon with csrf token
 )
```

---

## Step 6: Summary & Recommendations

### Security Posture: **GOOD** (with noted gaps)

**Strengths Observed:**

- SuperTokens BFF pattern (tokens never reach frontend)
- httpOnly session cookies (XSS-resistant)
- CSRF double-submit cookie pattern implemented
- Prompt injection detection (LLM-based + regex patterns)
- Input sanitization for LLM interpolation
- Constant-time comparison for admin keys
- DOMPurify for markdown rendering
- Parameterized SQL queries throughout
- Rate limiting on session creation
- Audit logging middleware
- pip-audit in CI pipeline

**Gaps Requiring Action:**

1. Prompt injection audit fails open (should fail closed) - **CRITICAL**
2. CSRF exemptions too broad for analytics endpoints - **HIGH**
3. No validation of admin API key entropy - **MEDIUM**
4. X-Forwarded-For trusted without proxy validation - **MEDIUM**
5. Container runs as root - **LOW**

### Recommended Next Steps

1. Apply Patch 1 (fail-closed) immediately
2. Apply Patches 2-5 before next production deployment
3. Schedule penetration test focusing on LLM injection vectors
4. Review and document TRUSTED_PROXY_IPS for production
5. Add security-focused integration tests per checklist above

---

_Report generated by security audit manifest v1.0_
