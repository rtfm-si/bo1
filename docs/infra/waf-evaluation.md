# WAF Evaluation Report

**Date:** 2025-12-18
**Task:** [INFRA][P3] Evaluate WAF (Web Application Firewall)

## Executive Summary

**Recommendation: No additional WAF needed.** Board of One already has comprehensive protection via a custom nginx WAF implementation plus multi-layer application-level security. Adding an external WAF would provide marginal benefit at significant cost/complexity.

---

## 1. Current Protection Layers

### 1.1 Nginx WAF (Custom Implementation)

**Files:** `nginx/waf-rules.conf`, `nginx/waf-allowlist.conf`

| Attack Vector | Coverage |
|--------------|----------|
| SQL Injection | UNION, keyword-based, comment-based, OR-bypass, encoded variants |
| XSS | Script tags, event handlers, javascript: protocol, data URIs, encoded |
| Path Traversal | ../, encoded variants, null bytes, Windows paths |
| Scanner/Probes | .env, .git, WordPress, phpMyAdmin, AWS metadata |
| Malicious Agents | sqlmap, nikto, nmap, acunetix, dirbuster, wpscan |

**Features:**
- Pattern-based blocking in request URI, query args, and user-agent
- Allowlist for legitimate endpoints (dataset Q&A, OAuth callbacks)
- Dedicated WAF blocked log (`waf-blocked.log`) for monitoring

### 1.2 Rate Limiting (Multi-Layer)

| Layer | Limit | Scope |
|-------|-------|-------|
| Nginx | 10r/s burst=20 | API endpoints |
| Nginx | 2r/m | Session creation |
| Global IP | 500/min | All requests |
| Auth endpoints | 10/min | Per IP |
| User sessions | Tiered | Free=5, Pro=20, Enterprise=100 |
| SSE connections | 5/min | Per IP |
| Dataset uploads | Configured | Per user |

**Redis-backed** with fail-open degraded mode and health monitoring.

### 1.3 Security Headers (nginx + FastAPI)

| Header | Value |
|--------|-------|
| HSTS | max-age=31536000; includeSubDomains; preload |
| X-Frame-Options | SAMEORIGIN (nginx), DENY (API) |
| X-Content-Type-Options | nosniff |
| X-XSS-Protection | 1; mode=block |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | geolocation=(), microphone=(), camera=() |
| CSP | Nonce-based (SvelteKit), minimal for API |

### 1.4 CSRF Protection

- Double-submit cookie pattern (`csrf_token` cookie + `X-CSRF-Token` header)
- Constant-time comparison (secrets.compare_digest)
- Token rotation on auth state change
- SameSite=Lax as baseline

### 1.5 Application-Level Security

| Feature | Implementation |
|---------|----------------|
| SQL Injection | Parameterized queries (SQLAlchemy), SQL validation layer |
| Prompt Injection | Detection + blocking, honeypot fields, configurable block mode |
| Input Validation | Pydantic models on all endpoints |
| Authentication | SuperTokens with anti-csrf header |
| Authorization | Workspace-scoped, admin role checks |

---

## 2. WAF Options Analysis

### 2.1 Cloudflare (Managed WAF)

| Factor | Assessment |
|--------|------------|
| Cost | Free tier: basic WAF, DDoS. Pro ($25/mo): custom rules. Enterprise: full WAF |
| Deployment | DNS change, minimal code changes |
| Rule Management | Managed rulesets + custom rules via dashboard |
| Logging | Real-time analytics, detailed event logs |
| Latency | +10-30ms (edge routing) |

**Pros:** Easy setup, DDoS protection, managed updates, CDN included
**Cons:** Requires proxying traffic through Cloudflare, adds external dependency, may conflict with existing nginx setup

### 2.2 ModSecurity + OWASP CRS

| Factor | Assessment |
|--------|------------|
| Cost | Free (open source) |
| Deployment | Compile nginx module, configure CRS |
| Rule Management | Manual, OWASP Core Rule Set (CRS) |
| Logging | File-based, needs log aggregation |
| Latency | +1-5ms (local) |

**Pros:** Industry-standard rules, customizable, no external dependency
**Cons:** Complex setup, high false-positive rate without tuning, maintenance burden, redundant with existing WAF

### 2.3 AWS WAF

| Factor | Assessment |
|--------|------------|
| Cost | $5/mo per web ACL + $1/mo per rule + $0.60/million requests |
| Deployment | ALB/CloudFront integration required |
| Rule Management | Managed rules (AWS, F5) + custom |
| Logging | CloudWatch, S3, Kinesis |
| Latency | Minimal (integrated with AWS) |

**Pros:** Deep AWS integration, managed rule groups
**Cons:** Not on AWS (DigitalOcean), would require architecture change

### 2.4 Fail2ban

| Factor | Assessment |
|--------|------------|
| Cost | Free (open source) |
| Deployment | Package install, jail configuration |
| Rule Management | Regex patterns on log files |
| Logging | syslog integration |
| Latency | None (reactive, not inline) |

**Pros:** Lightweight, effective for brute-force
**Cons:** Reactive (blocks after pattern detected), limited scope

---

## 3. Threat Coverage Gap Analysis

| OWASP Top 10 (2021) | Current Coverage | Gap? |
|---------------------|------------------|------|
| A01: Broken Access Control | Workspace authz, role checks | No |
| A02: Cryptographic Failures | TLS 1.2+, secure cookies | No |
| A03: Injection | Parameterized SQL, WAF rules, prompt injection detection | No |
| A04: Insecure Design | Code review, testing | No |
| A05: Security Misconfiguration | Security headers, minimal exposure | No |
| A06: Vulnerable Components | Dependabot, Trivy, pip-audit, npm audit | No |
| A07: Auth Failures | SuperTokens, rate limiting | No |
| A08: Data Integrity Failures | Input validation, Pydantic | No |
| A09: Logging & Monitoring | Prometheus, Loki, WAF logs, audit logs | No |
| A10: SSRF | URL validation (not user-controlled URLs) | Minimal risk |

**Bot/DDoS Protection:**
- Current: 500 req/min global IP limit, nginx rate limiting
- Gap: No L3/L4 DDoS protection (would require upstream protection like Cloudflare)

---

## 4. Recommendation

### Do NOT add external WAF

**Rationale:**
1. **Existing coverage is comprehensive** - Custom nginx WAF covers OWASP Top 10 web attack vectors
2. **Low marginal benefit** - Adding ModSecurity/CRS would duplicate existing patterns
3. **Operational burden** - External WAF adds another system to maintain, monitor, and debug
4. **Latency concern** - Cloudflare adds network hops; local nginx WAF is near-zero latency
5. **Cost-benefit** - Current self-hosted stack on DigitalOcean; adding Cloudflare Pro ($25/mo+) for marginal improvement isn't justified

### Potential Enhancements (If Future Needs Arise)

| Trigger | Action |
|---------|--------|
| DDoS attack | Add Cloudflare (free tier) for L3/L4 protection only |
| Compliance requirement (PCI-DSS, SOC2) | Document existing controls; consider managed WAF if auditor requires it |
| Significant bot traffic | Add bot management (Cloudflare, hCaptcha) |
| Geographic targeting | Add nginx geo-blocking or Cloudflare country rules |

### Recommended: Add Fail2ban (Low Effort)

For additional brute-force protection, consider adding Fail2ban with jails for:
- Repeated 403 from WAF blocks
- Repeated 429 from rate limits
- SSH brute-force (if applicable)

**Effort:** ~1 hour
**Benefit:** Auto-bans IPs after repeated violations (defense-in-depth)

---

## 5. Decision

| Option | Decision |
|--------|----------|
| External managed WAF (Cloudflare/AWS) | **Not recommended** - overkill for current scale |
| ModSecurity + OWASP CRS | **Not recommended** - redundant with existing nginx WAF |
| Fail2ban | **Optional** - low-effort enhancement if desired |
| Current setup | **Sufficient** - maintain and monitor existing protections |

**Action:** Mark task complete. No code changes required. Revisit if security posture changes (compliance audit, DDoS incident, significant scale increase).
