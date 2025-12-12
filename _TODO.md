# Auth Security Audit Report

**Date:** 2025-12-12
**Auditor:** Claude Code (automated)
**Scope:** Authentication, OAuth, rate limiting, admin access

---

## Executive Summary

The authentication implementation follows security best practices with SuperTokens session management, proper OAuth token handling, and tiered rate limiting. **No critical vulnerabilities found.**

### Risk Summary

| Severity | Count |
| -------- | ----- |
| Critical | 0     |
| High     | 0     |
| Medium   | 2     |
| Low      | 3     |
| Info     | 2     |

---

## 1. SuperTokens Session Configuration

**File:** `backend/api/supertokens_config.py`

### Findings

| Status | Item             | Details                                                     |
| ------ | ---------------- | ----------------------------------------------------------- |
| PASS   | HttpOnly cookies | Sessions use httpOnly cookies (XSS-proof)                   |
| PASS   | Secure flag      | Configurable via `COOKIE_SECURE` env var                    |
| PASS   | SameSite         | Set to `lax` (CSRF protection)                              |
| PASS   | Token rotation   | SuperTokens handles automatic refresh token rotation        |
| PASS   | Session expiry   | Managed by SuperTokens Core                                 |
| PASS   | BFF pattern      | Tokens never reach frontend (server-side exchange)          |
| PASS   | Production guard | `require_production_auth()` prevents MVP mode in production |

### Security Controls

- httpOnly cookies prevent JavaScript access (XSS mitigation)
- SameSite=lax prevents CSRF on cross-origin POST requests
- Cookie domain configurable for production deployment
- Session handles are opaque tokens (no sensitive data embedded)

---

## 2. Auth Middleware

**File:** `backend/api/middleware/auth.py`

### Findings

| Status | Item                | Details                                                        |
| ------ | ------------------- | -------------------------------------------------------------- |
| PASS   | Session validation  | Uses `verify_session()` dependency from SuperTokens            |
| PASS   | MVP mode protection | MVP mode blocked when `DEBUG=false`                            |
| PASS   | Error handling      | Returns generic "Authentication failed" (no info leakage)      |
| PASS   | Startup validation  | `require_production_auth()` fails app startup if misconfigured |
| INFO   | Logging             | User IDs logged on auth (consider PII implications)            |

### Security Controls

- Module-level check logs CRITICAL if auth disabled in non-DEBUG mode
- `require_production_auth()` raises RuntimeError if auth misconfigured in production
- Admin endpoints require `is_admin=True` from database

---

## 3. OAuth Flow (Google Sheets)

**File:** `backend/services/sheets.py`, `backend/api/supertokens_config.py`

### Findings

| Status | Item               | Details                                                |
| ------ | ------------------ | ------------------------------------------------------ |
| PASS   | State parameter    | SuperTokens handles OAuth state (CSRF protection)      |
| PASS   | Token storage      | Tokens stored in PostgreSQL (not cookies/localStorage) |
| PASS   | Token refresh      | Auto-refresh with persistence to database              |
| PASS   | Scope minimization | Uses `spreadsheets.readonly` (read-only access)        |
| MEDIUM | Token encryption   | OAuth tokens stored in plaintext in database           |
| LOW    | Error messages     | Some error messages reveal internal OAuth flow state   |

### Recommendations

**[MEDIUM] OAuth Token Encryption**

- **Issue:** Google OAuth tokens stored in plaintext in `users.google_tokens` column
- **Risk:** Database breach exposes user Google access
- **Recommendation:** Encrypt tokens at rest using application-level encryption

**[LOW] Error Message Sanitization**

- **Issue:** `SheetsError` messages may reveal OAuth token state
- **Recommendation:** Ensure production error messages are user-friendly

---

## 4. Rate Limiting

**File:** `backend/api/middleware/rate_limit.py`, `bo1/constants.py`

### Current Limits

| Endpoint Type       | Limit                   | Key  |
| ------------------- | ----------------------- | ---- |
| Auth (/api/auth/\*) | 10/minute               | IP   |
| Session creation    | 5/minute (free)         | User |
| Session creation    | 20/minute (pro)         | User |
| Session creation    | 100/minute (enterprise) | User |
| Streaming (SSE)     | 5/minute                | IP   |
| General API         | 60/minute               | IP   |
| Control endpoints   | 20/minute               | IP   |

### Findings

| Status | Item                     | Details                                              |
| ------ | ------------------------ | ---------------------------------------------------- |
| PASS   | Auth endpoint protection | 10 req/min per IP                                    |
| PASS   | User-based limiting      | Session creation uses user_id key                    |
| PASS   | Tiered limits            | Different limits by subscription tier                |
| PASS   | Redis-backed             | Multi-instance safe with Redis storage               |
| PASS   | Graceful degradation     | Falls back to in-memory if Redis unavailable         |
| MEDIUM | No lockout               | No progressive lockout after failed attempts         |
| LOW    | Fail-open                | UserRateLimiter allows requests if Redis unavailable |

### Recommendations

**[MEDIUM] Account Lockout**

- **Issue:** No progressive lockout after multiple failed auth attempts
- **Risk:** Brute force attacks can continue indefinitely at 10/min rate
- **Recommendation:** Implement exponential backoff after 5 failed attempts

**[LOW] Fail-Open Risk**

- **Issue:** Rate limiter allows requests when Redis is down
- **Mitigation:** Redis should be monitored for availability

---

## 5. Admin Authentication

**File:** `backend/api/middleware/admin.py`

### Findings

| Status | Item                     | Details                                             |
| ------ | ------------------------ | --------------------------------------------------- |
| PASS   | Constant-time comparison | Uses `secrets.compare_digest()` for API key         |
| PASS   | Dual auth methods        | Session-based OR API key supported                  |
| PASS   | Database validation      | `is_admin` flag checked from PostgreSQL             |
| PASS   | Audit logging            | Admin access attempts logged                        |
| INFO   | API key storage          | API key in environment variable (standard practice) |

### Security Controls

- Timing attack prevention with `secrets.compare_digest()`
- Session auth checks `is_admin` flag in database (not just token claims)
- API key auth requires explicit configuration
- Failed admin attempts logged with warnings

---

## 6. Additional Observations

### Production Checklist

- [ ] Set `COOKIE_SECURE=true` in production
- [ ] Set `COOKIE_DOMAIN` to production domain
- [ ] Set `ENABLE_SUPERTOKENS_AUTH=true` in production
- [ ] Configure `ADMIN_API_KEY` with strong random value
- [ ] Disable `DEBUG` mode in production

### Positive Security Patterns Observed

1. **Defense in depth:** Multiple auth checks at different layers
2. **Fail-secure:** Production guard prevents auth bypass
3. **Minimal scope:** OAuth scopes limited to what's needed
4. **Audit trail:** Auth events logged for forensics
5. **Secure defaults:** MVP mode only available in DEBUG

---

## Remediation Summary

### Priority Actions

| Priority | Issue                                     | Effort    |
| -------- | ----------------------------------------- | --------- |
| Medium   | Encrypt OAuth tokens at rest              | 4-8 hours |
| Medium   | Add account lockout after failed attempts | 2-4 hours |
| Low      | Sanitize OAuth error messages             | 1-2 hours |
| Low      | Add Redis availability monitoring         | 1-2 hours |

### Implementation Notes

**OAuth Token Encryption:**

```python
# Recommended: Use Fernet symmetric encryption
from cryptography.fernet import Fernet
key = os.getenv("TOKEN_ENCRYPTION_KEY")
fernet = Fernet(key)
encrypted_token = fernet.encrypt(access_token.encode())
```

**Account Lockout:**

```python
# Track failed attempts in Redis with exponential backoff
# After 5 failures: 30s lockout
# After 10 failures: 5min lockout
# After 15 failures: 1hour lockout + admin alert
```

---

## Conclusion

The authentication system is well-designed with appropriate security controls for a production application. The identified issues are moderate in severity and have clear remediation paths. The use of SuperTokens provides a solid foundation with built-in protections against common session attacks.

**Overall Risk Level: LOW**
