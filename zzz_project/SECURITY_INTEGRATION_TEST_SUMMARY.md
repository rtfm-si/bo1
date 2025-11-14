# Security & Integration Testing Summary

## Overview

This document summarizes the comprehensive security and integration testing requirements added to the MVP Implementation Roadmap.

**Last Updated**: 2025-11-14

---

## Key Principle: NEVER TRUST USER INPUT

All user input is considered **hostile** until proven otherwise. Every incomplete day in the roadmap now includes:

1. **Input validation requirements** (Pydantic models, min/max constraints)
2. **Integration tests** (malicious input, authorization, rate limiting)
3. **Security guardrails** (sanitization, parameterized queries, audit logging)

---

## Integration Tests Added

The following integration test suites have been added as REQUIRED deliverables:

### Week 4 (LangGraph Migration)
- `tests/integration/test_console_adapter_integration.py`
  - Invalid session_id handling
  - Corrupted checkpoint recovery
  - Malicious problem statements

### Week 6 (Web API)
- `tests/integration/test_session_api_integration.py`
  - XSS, SQL injection in problem statements
  - Authorization bypass attempts (RLS)
  - Rate limiting enforcement
  - Pagination attacks

- `tests/integration/test_sse_streaming_integration.py`
  - Invalid session_id, authorization checks
  - Connection limits, malformed events
  - Memory leak detection

- `tests/integration/test_deliberation_control_integration.py`
  - Authorization enforcement (pause/kill/resume)
  - Invalid state transitions
  - Race condition handling
  - Audit trail validation

### Week 7 (Web UI)
- `tests/integration/test_session_creation_form_integration.py`
  - XSS prevention in form submissions
  - SQL injection attempts
  - CSRF protection
  - Rate limiting on form submissions

### Week 8 (Payments + GDPR)
- `tests/integration/test_gdpr_compliance_integration.py`
  - Data export completeness
  - Anonymization verification (PII truly unrecoverable)
  - Authorization (User A cannot export User B's data)
  - Rate limiting (1 export/hour)
  - Deletion cascade verification

- `tests/integration/test_stripe_webhooks_integration.py` (CRITICAL)
  - Signature validation (reject invalid signatures)
  - Replay attack prevention
  - Idempotency testing
  - Malicious payload handling

### Week 10-11 (Admin Dashboard)
- `tests/integration/test_admin_user_management_integration.py`
  - Admin authentication required
  - Search injection prevention
  - Tier change authorization
  - Ban cascade effects
  - Audit trail validation

- `tests/integration/test_admin_kill_switches_integration.py`
  - API key validation
  - Kill reason required
  - Double confirmation for "kill all"
  - Checkpoint preservation

### Week 12 (Email)
- `tests/integration/test_email_preferences_integration.py`
  - JWT token validation (unsubscribe links)
  - Token tampering detection
  - Replay attack prevention
  - GDPR compliance (unsubscribe respected)

---

## Mandatory Test Coverage (Every Integration Test)

Each integration test suite MUST cover:

### 1. Input Validation
- [ ] Malicious input: XSS (`<script>alert('xss')</script>`)
- [ ] SQL injection: `'; DROP TABLE users; --`
- [ ] Path traversal: `../../etc/passwd`
- [ ] Boundary conditions: Empty string, max length +1, special chars
- [ ] Unicode, emojis, newlines, null bytes

### 2. Authorization
- [ ] User A CANNOT access User B's data (RLS enforced)
- [ ] Non-admin CANNOT access admin endpoints (403)
- [ ] Invalid API keys rejected (403)

### 3. Authentication
- [ ] Protected endpoints return 401 without token
- [ ] Expired tokens rejected
- [ ] Token tampering detected

### 4. Rate Limiting
- [ ] Tier limits enforced (free, pro, enterprise)
- [ ] 429 status + Retry-After header present
- [ ] Per-IP limits (DDoS protection)

### 5. Audit Logging
- [ ] Security events logged (auth, access, modifications)
- [ ] Log entries include: user_id, timestamp, IP, action

### 6. Error Handling
- [ ] Network failures handled gracefully
- [ ] API timeouts don't crash system
- [ ] Database unavailable handled

---

## Security Audit Checklist (Day 87)

On Day 87, run ALL integration tests and verify:

```bash
# Run all integration tests
pytest tests/integration/ -v --tb=short

# Generate coverage report
pytest tests/integration/ --cov=backend --cov-report=html

# Target: >90% coverage for security-critical modules
```

**Expected Integration Test Suites (9 total)**:
1. ✅ `test_session_api_integration.py`
2. ✅ `test_sse_streaming_integration.py`
3. ✅ `test_deliberation_control_integration.py`
4. ✅ `test_gdpr_compliance_integration.py`
5. ✅ `test_stripe_webhooks_integration.py` (CRITICAL - signature validation)
6. ✅ `test_session_creation_form_integration.py`
7. ✅ `test_email_preferences_integration.py`
8. ✅ `test_admin_kill_switches_integration.py`
9. ✅ `test_admin_user_management_integration.py`

**Go/No-Go Criteria**:
- [ ] All 9 integration test suites pass (0 failures)
- [ ] Coverage >90% for security-critical modules
- [ ] Manual penetration tests pass (OWASP ZAP scan)

---

## Common Vulnerabilities Prevented

### OWASP Top 10 (2021)

| Vulnerability | Prevention | Integration Test |
|---------------|-----------|------------------|
| **A01: Broken Access Control** | RLS + auth middleware | `test_session_api_integration.py` |
| **A02: Cryptographic Failures** | JWT tokens, bcrypt passwords | `test_email_preferences_integration.py` |
| **A03: Injection** | Pydantic validation, parameterized queries | ALL tests |
| **A04: Insecure Design** | Security by design (defense in depth) | Architecture review |
| **A05: Security Misconfiguration** | Security headers, HSTS, CSP | `test_security_headers.py` |
| **A06: Vulnerable Components** | `safety check`, `npm audit` | CI/CD pipeline |
| **A07: Auth Failures** | Supabase auth, rate limiting | `test_deliberation_control_integration.py` |
| **A08: Data Integrity** | Webhook signature validation | `test_stripe_webhooks_integration.py` |
| **A09: Security Logging** | Audit logs, Sentry | `test_admin_kill_switches_integration.py` |
| **A10: SSRF** | No external URL fetching in MVP | N/A |

---

## Input Validation Rules (Enforced Everywhere)

### Problem Statements
- **Min length**: 10 characters
- **Max length**: 10,000 characters
- **Sanitization**: Strip script tags, HTML entities encoded
- **Validation**: Pydantic `Field(min_length=10, max_length=10000)`

### Session IDs
- **Format**: UUID v4 only
- **Validation**: `UUID(session_id)` raises ValueError if invalid
- **SQL injection**: Parameterized queries only

### Email Addresses
- **Format**: RFC 5322 compliant
- **Validation**: Pydantic `EmailStr`
- **Sanitization**: Lowercase, strip whitespace

### JSON Payloads (Webhooks)
- **Max size**: 1MB (Stripe, Supabase)
- **Signature**: HMAC-SHA256 validation (CRITICAL)
- **Timestamp**: Reject if >5 minutes old (replay attack prevention)

### Admin API Keys
- **Format**: 64-character hex string
- **Storage**: Environment variable only (not in code/DB)
- **Rotation**: Quarterly (document in runbook)

---

## Defense in Depth Strategy

Board of One implements multiple security layers:

```
Layer 1: Client-side validation (UX only, NOT security)
         ↓
Layer 2: Pydantic models (API boundary, strict validation)
         ↓
Layer 3: Row-level security (PostgreSQL, user isolation)
         ↓
Layer 4: Rate limiting (per-user, per-IP, per-endpoint)
         ↓
Layer 5: Audit logging (all security events tracked)
```

**If one layer fails, others still protect the system.**

---

## Example Integration Test (Template)

See `zzz_project/INTEGRATION_TEST_TEMPLATE.md` for full template.

**Minimal example**:

```python
import pytest
from fastapi.testclient import TestClient

def test_sql_injection_blocked(client: TestClient):
    """Verify SQL injection attempts are blocked."""
    response = client.post("/api/v1/sessions", json={
        "problem_statement": "'; DROP TABLE sessions; --"
    })
    # Should succeed (parameterized queries prevent injection)
    assert response.status_code == 200

    # Verify no SQL injection occurred
    # (table still exists, session created normally)
    sessions = client.get("/api/v1/sessions").json()
    assert len(sessions) == 1

def test_xss_sanitized(client: TestClient):
    """Verify XSS attempts are sanitized."""
    response = client.post("/api/v1/sessions", json={
        "problem_statement": "<script>alert('xss')</script>"
    })
    assert response.status_code == 200

    # Verify script tag not stored/returned
    session = response.json()
    assert "<script>" not in session["problem_statement"]

def test_authorization_enforced(client: TestClient, user_a_token: str, user_b_session_id: str):
    """Verify User A cannot access User B's sessions."""
    response = client.get(
        f"/api/v1/sessions/{user_b_session_id}",
        headers={"Authorization": f"Bearer {user_a_token}"}
    )
    assert response.status_code == 403  # Forbidden (RLS)
```

---

## Go/No-Go Criteria for Launch (Week 14)

Before launch, ALL of the following MUST be true:

- [ ] **All 9 integration test suites pass** (100% pass rate)
- [ ] **Integration test coverage >90%** for security-critical modules
- [ ] **Manual penetration tests pass** (OWASP ZAP, no high/critical findings)
- [ ] **GDPR compliance verified** (data export, deletion, unsubscribe work)
- [ ] **Stripe webhook signature validation tested** (CRITICAL - prevents fraud)
- [ ] **Admin kill switches tested** (authorization, audit trail)
- [ ] **Rate limiting enforced** (tier limits, 429 responses)
- [ ] **Audit logs complete** (all security events logged)

**If any of these fail, DO NOT LAUNCH.**

---

## Continuous Monitoring (Post-Launch)

After launch, monitor:

1. **Integration test CI/CD**: Run on every PR, must pass to merge
2. **Dependency scanning**: `safety check`, `npm audit` (weekly)
3. **OWASP ZAP**: Automated scans (monthly)
4. **Penetration testing**: Manual (quarterly)
5. **Audit log review**: Weekly review of anomalies
6. **Rate limit violations**: Alert on >100/day (potential attack)

---

## References

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **GDPR Compliance**: https://gdpr.eu/
- **Stripe Webhook Security**: https://stripe.com/docs/webhooks/signatures
- **Supabase RLS**: https://supabase.com/docs/guides/auth/row-level-security
- **Pydantic Validation**: https://docs.pydantic.dev/latest/

---

## Conclusion

The MVP Implementation Roadmap now includes:

- **9 integration test suites** covering ALL user input surfaces
- **Mandatory security checklist** for every incomplete day
- **Input validation requirements** (Pydantic, sanitization, parameterized queries)
- **Authorization tests** (RLS, admin auth, token validation)
- **Rate limiting tests** (tier limits, DDoS protection)
- **Audit logging requirements** (all security events tracked)

**No day is complete without integration tests. Security is not optional.**
