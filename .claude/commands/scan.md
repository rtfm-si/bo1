Bo1 Supply-Chain + Web Security Risk Investigation (npm + app)

GOAL
Investigate our current exposure to modern supply-chain attacks (npm/ecosystem) and common web-app security failures. Identify risks and gaps, then record them as clear, high-level tasks for later planning and implementation.

IMPORTANT
This prompt is INVESTIGATION ONLY.

- Do NOT create a plan.
- Do NOT implement fixes.
- Do NOT modify application code or CI.
- ONLY write findings as tasks to `_TASK.md`.

_PLANNING AND IMPLEMENTATION WILL HAPPEN IN A SEPARATE PASS._

CONSTRAINTS

- Follow all repo governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
- Keep reasoning shallow and outputs concise.
- Treat all data as sensitive; do not dump secrets, tokens, or raw configs.
- Prefer high-signal tasks over exhaustive lists.

SCOPE
A) Supply-chain hardening (npm / JS ecosystem)
B) CI policy & dependency controls
C) Browser / app security basics
D) Cookies, sessions, CSRF
E) Rate limiting, WAF, logging & abuse resistance

---

## STEP 1 — SUPPLY-CHAIN INVENTORY (npm)

Inspect the repository for:

- Package manager(s): npm / pnpm / yarn
- Lockfiles: presence, consistency, and enforcement
- Version ranges (`^`, `~`, `latest`, git/url deps)
- Multiple package.json files / workspaces
- Postinstall / prepare scripts
- Transitive dependency sprawl

Identify risks such as:

- Missing or ignored lockfiles
- Non-pinned dependencies
- High dependency count for low value
- Git or URL-based dependencies
- Install scripts with elevated risk

---

## STEP 2 — CI & DEPENDENCY POLICY GAPS

Inspect CI configuration and workflows:

- Are lockfiles enforced (`npm ci` vs `npm install`)?
- Are new dependencies reviewed or gated?
- Is `npm audit` or equivalent run?
- Any SCA, OSV, or malware scanning?
- Are failures blocking or advisory only?

Identify gaps where:

- New deps can be added silently
- Vulnerabilities would go unnoticed
- Malware or typosquatting risks are unchecked

---

## STEP 3 — PACKAGE TRUST & MAINTENANCE SIGNALS

Spot-check dependency health:

- Abandoned or low-maintenance packages
- Single-maintainer, low-activity packages
- High-risk categories (build tooling, bundlers, auth, crypto)

Identify opportunities to:

- Reduce dependency surface
- Replace risky packages
- Prefer better-maintained alternatives

---

## STEP 4 — BROWSER / APP SECURITY BASELINE

Inspect app/server setup for:

- CSP and security headers:
  - CSP
  - HSTS (prod)
  - X-Content-Type-Options
  - Referrer-Policy
  - Permissions-Policy
- Unsafe rendering patterns:
  - Rendering untrusted HTML
  - Weak input validation
- Framework-specific footguns (e.g. SvelteKit hooks, actions, SSR boundaries)

Identify missing or weak protections.

---

## STEP 5 — COOKIES, SESSIONS & CSRF

Inspect auth/session handling:

- Cookie flags:
  - HttpOnly
  - Secure
  - SameSite
- CSRF protections on state-changing routes
- Token storage patterns (cookies vs localStorage)

Identify:

- Missing flags
- Over-permissive settings
- Routes lacking CSRF protection

---

## STEP 6 — RATE LIMITING, WAF & LOGGING

Inspect:

- Rate limiting (auth, meeting creation, SSE, heavy endpoints)
- Edge/WAF protections (if applicable)
- Structured logging:
  - Request IDs
  - Correlation / meeting IDs
  - Secret/PII masking

Identify:

- Abuse-prone endpoints
- Missing limits
- Logs that may leak sensitive data

---

## STEP 7 — WRITE FINDINGS AS TASKS (\_TASKS.md)

Update `_TASK.md` ONLY.

For each identified issue:

- Write a **single-purpose, high-level task**
- Do NOT include implementation details
- Do NOT include configs or code
- Do NOT reference `_PLAN.md`

Task format (follow TASK_PATTERNS.md):

- [SEC][SUPPLY][P0|P1|P2] Short, outcome-focused description
- [SEC][CI][P0|P1|P2] ...
- [SEC][WEB][P0|P1|P2] ...

Examples:

- `[SEC][SUPPLY][P0] Enforce lockfile-only installs and block non-pinned dependency ranges`
- `[SEC][CI][P1] Add automated supply-chain and malware scanning to CI`
- `[SEC][WEB][P1] Define and enforce a production CSP and security header baseline`
- `[SEC][AUTH][P0] Harden session cookies and ensure CSRF protection on all state-changing routes`
- `[SEC][ABUSE][P1] Add rate limiting and abuse protection for meeting creation and SSE endpoints`

De-duplicate:

- Merge with existing tasks if already present
- Prefer strengthening existing tasks over creating near-duplicates

---

## STEP 8 — FINAL CHECK

Before finishing:

- Confirm no `_PLAN.md` was created or modified
- Confirm only `_TASK.md` was updated
- Confirm tasks are high-level, scoped, and prioritised
- Confirm no fixes were implemented

In chat output:

- Brief summary only:
  - Number of P0 / P1 / P2 tasks added
  - One-line description of the most serious risk

Now perform the investigation and update `_TASK.md` accordingly.
