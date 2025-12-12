# GDPR Compliance Audit Report

**Audit Date:** 2025-12-12
**Manifest:** audits/manifests/gdpr-compliance.manifest.xml
**Auditor:** Claude (automated)
**Scope:** UK GDPR / Data Protection Act 2018 compliance

---

## Executive Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 4 |
| Low | 3 |

**Overall Status:** Substantially compliant with key gaps requiring remediation before production launch.

The application has solid technical foundations for GDPR compliance including:
- Functional data export (Art. 15) and deletion (Art. 17) endpoints
- Comprehensive privacy policy with all required disclosures
- Cookie consent mechanism with granular options
- GDPR audit logging for data subject requests
- Automated session cleanup job

Key gaps requiring attention:
- No consent tracking during signup (HIGH)
- DPAs not signed with processors (MEDIUM)
- Missing dataset clarifications in data export (MEDIUM)
- OAuth token encryption at rest (cross-ref from security audit)

---

## Detailed Findings

### Art. 12-14 Transparency

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| T1 | Privacy policy accessible | ✅ PASS | `/legal/privacy` page, last updated 2025-01-19 |
| T2 | Data controller identity | ✅ PASS | "Board of One" identified in privacy policy |
| T3 | Processing purposes documented | ✅ PASS | Section 3 lists all purposes |
| T4 | Legal basis stated | ✅ PASS | Section 4 covers contract, legitimate interest, consent, legal obligation |
| T5 | Data recipients disclosed | ✅ PASS | Section 5.1 lists Anthropic, Voyage AI, Supabase, Stripe |
| T6 | Retention periods disclosed | ✅ PASS | Section 6 specifies 1 year default, configurable |
| T7 | User rights documented | ✅ PASS | Section 7 covers all Art. 15-22 rights with links |
| T8 | DPO contact provided | ✅ PASS | dpo@boardof.one listed in Section 13 |
| T9 | International transfers | ✅ PASS | Section 9 mentions SCCs and adequacy decisions |

**Finding T-1: Privacy policy references non-existent settings page**

- **Severity:** LOW
- **Location:** `frontend/src/routes/legal/privacy/+page.svelte:157-165`
- **Issue:** Links to `/settings/privacy` for data export/deletion, but this page doesn't exist
- **Evidence:** Grep shows no `settings/privacy` route
- **Remediation:** Create settings page or update links to actual implementation location

---

### Art. 15 Right of Access (Data Export)

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| A1 | Export endpoint exists | ✅ PASS | `GET /api/v1/user/export` |
| A2 | Export includes all PII | ⚠️ PARTIAL | Missing: dataset clarifications, conversation history |
| A3 | Machine-readable format | ✅ PASS | JSON with ISO timestamps |
| A4 | Rate limiting | ✅ PASS | 1 request per 24h via audit log check |
| A5 | Audit trail | ✅ PASS | `gdpr_audit_log` table with export_requested/completed |

**Finding A-1: Data export missing dataset clarifications**

- **Severity:** MEDIUM
- **Location:** `backend/services/gdpr.py:103-113`
- **Issue:** Export includes datasets table but not the `clarifications` JSONB column
- **Evidence:** SELECT statement excludes clarifications field
- **Remediation:** Add `clarifications` to dataset export query

**Finding A-2: Data export missing dataset Q&A conversation history**

- **Severity:** MEDIUM
- **Location:** `backend/services/gdpr.py:29-146`
- **Issue:** Redis-backed dataset conversation history (`backend/services/conversation_repo.py`) not exported
- **Evidence:** No conversation_history in collect_user_data()
- **Remediation:** Export user's dataset Q&A conversation history from Redis

---

### Art. 17 Right to Erasure (Data Deletion)

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| E1 | Deletion endpoint exists | ✅ PASS | `DELETE /api/v1/user/delete` |
| E2 | All data categories covered | ⚠️ PARTIAL | Missing: Redis conversation history |
| E3 | Storage files deleted | ✅ PASS | DO Spaces files deleted via SpacesClient |
| E4 | Sessions invalidated | ✅ PASS | SuperTokens `revoke_all_sessions_for_user()` called |
| E5 | Redis cache cleared | ⚠️ PARTIAL | Session keys not explicitly cleared |
| E6 | Audit trail | ✅ PASS | deletion_requested/completed logged |

**Finding E-1: Redis data not cleared on deletion**

- **Severity:** MEDIUM
- **Location:** `backend/services/gdpr.py:149-286`
- **Issue:** Dataset conversation history stored in Redis not deleted
- **Evidence:** delete_user_data() doesn't call Redis cleanup
- **Remediation:** Add Redis key deletion for user's conversation history

---

### Art. 6/7 Consent

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| C1 | Cookie consent mechanism | ✅ PASS | CookieConsent.svelte with banner |
| C2 | Consent timestamp recorded | ⚠️ PARTIAL | Cookie consent in browser, not server; no GDPR consent at signup |
| C3 | Granular consent options | ✅ PASS | Essential vs Analytics separation |
| C4 | Consent withdrawal | ✅ PASS | Email unsubscribe endpoint + email preferences |
| C5 | Third-party sharing consent | ⚠️ GAP | No explicit consent for LLM processing |

**Finding C-1: GDPR consent not captured during signup (HIGH)**

- **Severity:** HIGH
- **Location:** SuperTokens OAuth flow
- **Issue:** `gdpr_consent_at` column exists in users table but is never populated
- **Evidence:** Grep shows column defined but no code sets it
- **Context:** Users sign in via Google OAuth without explicit GDPR consent checkbox
- **Remediation:**
  1. Add GDPR consent checkbox to signup flow
  2. Record timestamp in `gdpr_consent_at` column
  3. Block account creation until consent given

**Finding C-2: No explicit consent for LLM data processing**

- **Severity:** LOW
- **Location:** Privacy policy only
- **Issue:** Third-party LLM processing (Anthropic, Voyage) disclosed in privacy policy but not explicitly consented to during signup
- **Mitigation:** Could argue contract performance basis (Art. 6(1)(b)) since LLM is core service
- **Remediation:** Consider adding explicit notice during onboarding about AI processing

---

### Art. 30 Processing Records

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| P1 | Processing activities documented | ✅ PASS | Privacy policy documents all processing |
| P2 | Sub-processors listed | ✅ PASS | Anthropic, Voyage, Supabase, Stripe, Resend listed |
| P3 | DPAs in place | ❌ FAIL | No DPAs signed yet |

**Finding P-1: DPAs not signed with data processors**

- **Severity:** MEDIUM (blocks production launch)
- **Location:** Operational (not code)
- **Issue:** Privacy policy lists processors but DPAs not signed
- **Evidence:** _TASK.md shows "Sign DPAs with data processors" still pending
- **Processors requiring DPA:**
  - Supabase (hosting, auth)
  - Resend (email)
  - Anthropic (LLM)
  - DigitalOcean (Spaces storage)
- **Remediation:** Sign DPAs before production launch

---

### Art. 32 Security of Processing

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| S1 | Encryption at rest | ⚠️ PARTIAL | Postgres/Redis via provider; OAuth tokens NOT encrypted |
| S2 | Encryption in transit | ✅ PASS | TLS required for all external connections |
| S3 | Access controls | ✅ PASS | Session-based auth, rate limiting |
| S4 | Security audit | ✅ PASS | auth-security.report.md and infra-security.report.md completed |

**Finding S-1: OAuth tokens stored unencrypted (cross-reference)**

- **Severity:** MEDIUM (cross-ref from auth-security.report.md)
- **Location:** `bo1/state/repositories/user_repository.py` (google_tokens column)
- **Issue:** Google OAuth refresh tokens stored in plaintext
- **Remediation:** Encrypt with Fernet before storage (already in _TASK.md)

---

### Data Retention

| ID | Check | Status | Notes |
|----|-------|--------|-------|
| R1 | Retention periods defined | ✅ PASS | 365 days default in session_cleanup.py |
| R2 | Automated cleanup job | ✅ PASS | `backend/jobs/session_cleanup.py` exists |
| R3 | Retention configurable | ⚠️ PARTIAL | CLI arg only, not per-user setting |

**Finding R-1: Retention period not user-configurable**

- **Severity:** LOW
- **Location:** `backend/jobs/session_cleanup.py`
- **Issue:** Privacy policy mentions "configurable in settings" but no user-facing setting exists
- **Remediation:** Add retention period setting to user preferences (already noted in _TASK.md)

---

## Checklist Summary

| Category | Pass | Partial | Fail | Total |
|----------|------|---------|------|-------|
| Transparency (T) | 9 | 0 | 0 | 9 |
| Right of Access (A) | 4 | 1 | 0 | 5 |
| Right to Erasure (E) | 4 | 2 | 0 | 6 |
| Consent (C) | 3 | 2 | 0 | 5 |
| Processing Records (P) | 2 | 0 | 1 | 3 |
| Security (S) | 3 | 1 | 0 | 4 |
| Data Retention (R) | 2 | 1 | 0 | 3 |
| **Total** | **27** | **7** | **1** | **35** |

---

## Remediation Priority

### Before Production Launch (Required)

1. **[HIGH] C-1:** Implement GDPR consent capture during signup
2. **[MEDIUM] P-1:** Sign DPAs with Supabase, Resend, Anthropic, DigitalOcean

### Within 30 Days

3. **[MEDIUM] A-1:** Add dataset clarifications to data export
4. **[MEDIUM] A-2:** Add conversation history to data export
5. **[MEDIUM] E-1:** Clear Redis data on account deletion
6. **[MEDIUM] S-1:** Encrypt OAuth tokens at rest (cross-ref)

### Backlog

7. **[LOW] T-1:** Fix privacy policy settings page links
8. **[LOW] C-2:** Add explicit LLM processing notice during onboarding
9. **[LOW] R-1:** Add user-configurable retention period setting

---

## Appendix: Files Reviewed

- `backend/api/user.py` - GDPR endpoints
- `backend/services/gdpr.py` - Data export/deletion logic
- `backend/services/audit.py` - GDPR audit logging
- `backend/jobs/session_cleanup.py` - Data retention job
- `frontend/src/routes/legal/privacy/+page.svelte` - Privacy policy
- `frontend/src/lib/components/CookieConsent.svelte` - Cookie consent
- `migrations/versions/l1_add_gdpr_audit_log.py` - Audit log schema
- `migrations/versions/ced8f3f148bb_initial_schema.py` - Users table schema
