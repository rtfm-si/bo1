Fix Prod: E2E → Triage → Fix → Document → Ship (Iterative)

Automated production fix workflow with iteration support. Runs E2E, fixes issues, deploys, then repeats until clean or max iterations reached.

GOAL
Iterative cycle: /e2e → fix → ship → verify deploy → repeat
Each iteration builds on previous fixes, progressively improving production.

USAGE
```
/fix-prod           # Single iteration (default)
/fix-prod 3         # Run 3 iterations
/fix-prod 5         # Run 5 iterations (recommended for thorough cleanup)
```

CONSTRAINTS
- Follow CLAUDE.md governance (diffs only, minimal changes)
- Fix Critical + Major + any issue blocking feature functionality
- Defer cosmetic, performance suggestions, third-party issues
- Document ALL deferred issues in _TASK.md
- Auto-continue between steps (no confirmations)
- Wait for deployment health before next iteration

---

## ITERATION CONTROL

### Parameters

```yaml
max_iterations: {N from args, default 1}
current_iteration: 1
issues_fixed_total: 0
issues_deferred_total: 0
iteration_results: []
```

### Iteration Flow

```
FOR iteration = 1 TO max_iterations:
  1. Log: "=== ITERATION {iteration}/{max_iterations} ==="

  2. IF iteration > 1:
     - Wait for previous deploy to be healthy (Step 7.1)
     - Log: "Previous deploy verified, starting next E2E run"

  3. Run Steps 1-7 (full cycle)

  4. Record iteration result:
     - issues_found: {count from E2E}
     - issues_fixed: {count fixed this iteration}
     - issues_deferred: {count deferred}
     - deploy_status: success/failed

  5. EXIT EARLY if:
     - E2E passes with 0 issues → "Production is clean!"
     - Deploy failed → "Deploy failed, stopping iterations"
     - Same issues found as previous iteration → "Plateau detected"
     - All remaining issues are deferred → "Only deferred issues remain"

  6. CONTINUE to next iteration
```

### Plateau Detection

Track issue IDs across iterations. If iteration N finds the same issues as iteration N-1:
- Log: "Plateau detected - same issues persisting"
- These are likely complex issues requiring manual investigation
- Move all to _TASK.md as deferred with "persisted across {N} fix attempts"
- Exit iterations

### Deploy Verification (Between Iterations)

Before starting iteration N+1, verify iteration N's deploy is live:

```bash
# 1. Check GitHub Actions deploy completed
gh run list --workflow=deploy-production.yml --limit=1 --json status,conclusion

# 2. Wait if still running (poll every 30s, max 10 min)
while status == "in_progress":
  sleep 30
  check again

# 3. Verify health endpoint
curl -f https://boardof.one/api/health

# 4. Verify recent commit is deployed
curl -s https://boardof.one/api/health | jq -r '.version'
# Compare with local git rev-parse HEAD
```

If deploy verification fails after 10 minutes:
- Log error
- Exit iterations
- Report partial progress

---

## STEP 1: RUN E2E ON PRODUCTION

Execute E2E explorer on production via SSH:

```bash
# Access prod via SSH tunnel for SuperTokens API
ssh root@139.59.201.65
```

Run the `/e2e` skill with prod configuration:
- base_url: https://boardof.one
- ssh_target: root@139.59.201.65

Wait for `_E2E_RUN_REPORT.md` generation.

**If E2E PASS with 0 issues**: Skip to Step 6 (ship pending changes or exit clean).

---

## STEP 2: PARSE & TRIAGE ISSUES

Read `_E2E_RUN_REPORT.md` and categorize each issue:

### FIX NOW (implement this run)

| Criteria | Examples |
|----------|----------|
| Critical severity | Auth failures, data loss, core flow blocked |
| Major severity | Broken UI, repeated errors, confusing UX |
| Feature-blocking Minor | Feature exists but doesn't work as intended |

### DEFER (document in _TASK.md)

| Criteria | Examples |
|----------|----------|
| Cosmetic Minor | Visual polish, copy improvements |
| Performance only | Slow but functional |
| Third-party | External API issues |
| Complex/unclear | Needs investigation, arch decision |
| Requires migration | Data backfill needed |

### Triage Output

For each issue, determine:
```
ISS-XXX: {title}
  fix_now: true/false
  category: BUG | UX | PERF | SECURITY | DATA | INFRA
  priority: P0 | P1 | P2 | P3
  complexity: trivial | simple | moderate | complex
  defer_reason: {if deferred, why}
```

---

## STEP 3: PLAN FIXES

For each `fix_now=true` issue, create mini-plan:

```markdown
### ISS-XXX: {title}
- Root cause: {analysis}
- Fix: {approach}
- Files: {list with change description}
- Verify: {how to confirm fix}
```

Order by:
1. Dependencies (unblocking fixes first)
2. Risk (lower risk first)
3. Complexity (quick wins first)

---

## STEP 4: IMPLEMENT FIXES

For each planned fix:

1. **Read** relevant files (mandatory)
2. **Edit** with minimal diffs
3. **Add resolution** to `_E2E_RUN_REPORT.md`:
   ```markdown
   - **Resolution**: {brief description of fix}
   ```

### Fix Rules

- Backend: Match existing patterns
- Frontend: Svelte 5 patterns, existing components
- No migrations unless critical
- No refactoring beyond fix scope
- No new features disguised as fixes

---

## STEP 5: DOCUMENT DEFERRED ISSUES

For each `fix_now=false` issue, add to `_TASK.md`:

### Format

```markdown
- [ ] [{CATEGORY}][{PRIORITY}] {Title} - {brief description}
  - Source: E2E run {run_id} ISS-XXX
  - Deferred: {reason}
  - Lead: {any preliminary analysis}
```

### Section Mapping

| Category | _TASK.md Section |
|----------|------------------|
| BUG | Production Bugs [BUG] |
| UX | UX Improvements [UX] |
| PERF | Performance [PERF] |
| SECURITY | Security [SECURITY] |
| DATA | Data Model [DATA] |
| INFRA | Infrastructure [INFRA] |

Add under `## E2E Findings ({date})` section if exists, or create it.

---

## STEP 6: SHIP

Execute `/ship` workflow:

1. Pre-commit checks (Docker)
2. Run tests
3. Commit with message:
   ```
   fix(e2e): resolve {ISS-XXX, ...} from E2E run

   Fixed:
   - ISS-XXX: {one-line}
   - ISS-YYY: {one-line}

   Deferred ({count} issues documented in _TASK.md):
   - ISS-ZZZ: {reason}
   ```
4. Push to main
5. Wait for CI
6. Deploy to production

### Auto-Confirm

Skip confirmations for: commit, push, deploy.
Only stop on: test failures, CI failures, deploy failures.

---

## STEP 7: VERIFY & SUMMARIZE

After deploy:

1. Quick health check: `curl https://boardof.one/api/health`
2. Verify Critical fixes work

### Output Summary

```markdown
## Fix Prod Summary

**E2E Run**: {run_id}
**Duration**: {start} → {end}

### Fixed ({count})
| Issue | Severity | Description |
|-------|----------|-------------|
| ISS-XXX | Critical | ... |

### Deferred ({count})
| Issue | Severity | Reason | _TASK.md |
|-------|----------|--------|----------|
| ISS-YYY | Minor | Cosmetic | [UX][P3] |

### Deployment
- Commit: {hash}
- CI: pass
- Deploy: success
- Health: ok
```

---

## ERROR HANDLING

### E2E Incomplete
- Document as P0 blocker in _TASK.md
- Do NOT proceed to fixes

### Fix Causes New Error
- Revert that specific fix
- Add to deferred with "fix attempt failed"
- Continue with remaining fixes

### CI Fails
- If fix-related: revert problematic fix
- If pre-existing: proceed if core checks pass

### Deploy Fails
- Do NOT retry
- Document and alert for manual intervention

---

## EXECUTION

Default (full cycle):
```
/fix-prod
```

With explicit SSH target:
```
/fix-prod ssh user@host
```

Fixes only (no deploy):
```
/fix-prod --no-ship
```

Skip E2E (use existing report):
```
/fix-prod --skip-e2e
```
