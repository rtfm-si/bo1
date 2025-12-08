Bo1 Test Suite Audit & Cleanup

GOAL
Review all current tests and:

- Ensure they are relevant to the current codebase and product.
- Remove or update tests for old / redundant features.
- Identify gaps where important behaviour has no coverage.
- Keep the test suite focused, maintainable, and comprehensive enough for core flows.

Produce:

- Minimal diffs to test files (fix/update/remove where appropriate).
- A summary report written to `tests_audit.md` in the repo root.

CONSTRAINTS

- Follow all governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any folder-level CLAUDE/manifest files (e.g. /backend, /frontend).
- Run pre-flight enforcement and runtime self-audit before making changes.
- Keep reasoning shallow and outputs concise.
- Use minimal diffs; do NOT rewrite whole test files unless necessary.
- Do NOT modify governance or business requirements docs.
- If there is genuine ambiguity about whether a test is obsolete, prefer:
  - Marking it as “suspect” in the report rather than deleting it silently.

---

## STEP 1 – DISCOVER TEST LANDSCAPE

1. Detect test locations and patterns, for example:
   - Backend tests (e.g. `/backend/tests`, `/backend/src/**/__tests__`, etc.).
   - Frontend tests (e.g. `/frontend/tests`, `/frontend/src/**/__tests__`, etc.).
   - Any e2e or integration tests (e.g. `/e2e`, `/playwright`, `/cypress`, etc.).
2. Build a SHORT internal map:
   - Test group → paths → frameworks (pytest, Vitest, Playwright, etc.).
   - Key naming conventions (e.g. `*.test.ts`, `test_*.py`).

Do NOT dump this map to the chat; use it to guide the rest of the audit.

---

## STEP 2 – MAP TESTS TO CURRENT FEATURES

For each major test group:

1. Infer which part of the product each test file targets:
   - APIs, services, agents, meeting flows, DB logic, UI views, etc.
   - Use imports, route paths, and filenames to map tests to features/modules.
2. Cross-check against the current code:
   - Flag tests that reference:
     - Removed files/modules.
     - Deprecated APIs or routes.
     - Old flags or feature names no longer present.
   - Flag tests that clearly encode old behaviour that no longer matches the current UX / API.

Tag each file internally as:

- `keep` (relevant)
- `update` (behaviour changed / needs refresh)
- `remove` (obsolete / dead feature)
- `suspect` (unclear, but likely stale)

---

## STEP 3 – CLEAN UP OBSOLETE / REDUNDANT TESTS

1. For tests tagged `remove`:

   - Verify:
     - The corresponding code/feature has truly been removed or is explicitly deprecated.
   - If confirmed:
     - Remove the test file or specific test cases with minimal diffs.
     - Note the removal in the report.

2. For tests tagged `suspect`:

   - Do NOT delete.
   - Add a **brief, clear comment** at the top or above the test block:
     - E.g. `// TODO: Review – behaviour may no longer match current feature spec (Bo1 test audit).`
   - Note these in the report under “Suspect tests”.

3. For duplicate or near-duplicate tests:
   - Consolidate where obvious:
     - Prefer the clearer, more maintainable variant.
   - Avoid deleting non-obvious differences without strong evidence.

---

## STEP 4 – UPDATE OUTDATED BUT STILL-VALUABLE TESTS

For tests tagged `update`:

1. Compare current expected behaviour in the test vs:
   - Current code.
   - Any clear product behaviour from routes/handlers/components.
2. Adjust:
   - Inputs, outputs, messages, status codes, or UI expectations to match current reality.
   - Names/descriptions to reflect current terminology.
3. Preserve:
   - The test’s **intent** (what behaviour it is trying to guard), not the old implementation details.

Apply small, focused edits that keep tests meaningful and aligned with reality.

---

## STEP 5 – IDENTIFY COVERAGE GAPS (AT A HIGH LEVEL)

Without trying to build a full coverage tool:

1. From your map of tests vs features, note:
   - Key modules / flows with **little or no test coverage**, especially:
     - Critical backend flows (meeting lifecycle, agents, decisions, DB persistence).
     - Critical frontend flows (core UX for running a meeting, reviewing decisions).
     - Security-sensitive paths (auth, permissions, data access).
2. For each gap:
   - Describe the missing test at a **high level**:
     - E.g. “No test ensuring meeting retries on transient LLM failure.”
     - “No UI test verifying user can resume an interrupted meeting.”

Do NOT implement new tests in this prompt unless the change is tiny and obviously needed; focus on review and cleanup.

---

## STEP 6 – OPTIONAL: RUN TESTS/SPOT-CHECKS

If allowed and feasible in this environment:

1. Run the appropriate test commands (per suite) after cleanup:
   - E.g. `pytest`, `npm test`, `pnpm test`, `vitest`, `playwright test`, etc.
2. If failures occur:
   - Quickly identify if they are due to the audit changes.
   - Prefer fixing small, local issues; if not obvious, note them in the report.

If actual command execution is not possible, specify the commands that SHOULD be run.

---

## STEP 7 – WRITE `tests_audit.md` REPORT

Create or overwrite `tests_audit.md` in the repo root with a concise report:

Structure:

# Bo1 Test Suite Audit – {{DATE}}

## Summary

- 3–7 bullets summarising:
  - Files removed.
  - Files updated.
  - Suspect tests left for human review.
  - Main coverage gaps.

## Changes

### Removed

- List of files/tests removed with brief reason.

### Updated

- List of files with behaviour expectations updated.

### Suspect (Needs Review)

- List of tests marked with TODOs and why.

## Coverage Gaps (High Level)

- Bullet list of key flows/modules that lack tests.
- For each: a one-line suggestion for what test should exist.

## Suggested Next Steps

- 5–10 bullets with concrete next actions:
  - “Add tests for X flow.”
  - “Refine or remove suspect tests once product spec is clarified.”
  - “Adopt standard pattern for Y tests.”

Keep this file short, readable, and implementation-oriented.

---

## STEP 8 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finishing:

1. Confirm you:
   - Only touched test-related files and `tests_audit.md`.
   - Did not change governance or core application logic except where required for tests to compile.
2. Confirm:
   - No clearly valid tests were removed.
   - All removals/changes are recorded in `tests_audit.md`.
3. If any decision about test removal felt risky, ensure it is:
   - Tagged as suspect instead, and
   - Clearly documented in the report.

---

## OUTPUT REQUIREMENTS

- Apply changes directly to test files and `tests_audit.md`.
- Do NOT dump whole test files in the chat.
- In the chat, provide only:
  - A short bullet list of:
    - Number of files removed.
    - Number of files updated.
    - Number of suspect tests.
    - Count of major coverage gaps identified.
- Do not restate this prompt.

Now perform the full test suite audit and cleanup.
