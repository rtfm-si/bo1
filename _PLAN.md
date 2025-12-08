# Plan: Security Audit Remaining Items (H2, M4)

## Summary

- **H2**: Tighten CSP (remove unsafe-eval, consider nonces)
- **M4**: Enable Redis authentication for all environments

## Remaining Tasks

### H2 - CSP Hardening (HIGH)
- Current: `'unsafe-inline' 'unsafe-eval'` in script-src
- Challenge: SvelteKit may require these for hydration/SSR
- Options:
  1. Test without `'unsafe-eval'` - may break SvelteKit
  2. Implement CSP nonces (requires server-side coordination)
  3. Accept risk with documentation

### M4 - Redis Authentication (MEDIUM)
- Current: Redis exposed without password in docker-compose
- Fix: Add `requirepass` to Redis config
- Risk: Dev-only, low priority for MVP

## Status

All quick-win fixes completed:
- ✅ H5: Docker default passwords removed
- ✅ H1: DEBUG enforcement exists (`require_production_auth()`)
- ✅ H3: Prompt injection coverage verified
- ✅ M1: PII redaction in logs
- ✅ M6: Input length limits exist
- ✅ L1: Console.log removed
- ✅ L3: @html usage verified safe (DOMPurify)

Remaining items (H2, M4) require architectural decisions or are low priority.
