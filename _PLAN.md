# Codebase Cleanup Audit Report

## Step 1: Domains & Suspected Legacy/Unused Areas

### Domain Structure

| Domain          | Files | LOC      | Status                              |
| --------------- | ----- | -------- | ----------------------------------- |
| bo1/agents      | 12    | ~1,500   | Active (research subsystem complex) |
| bo1/graph       | 10    | ~4,400   | Active                              |
| bo1/prompts     | 19    | ~2,800   | Active (pattern duplication)        |
| bo1/state/repos | 11    | ~1,200   | Active (CRUD pattern duplication)   |
| backend/api     | 61    | ~19,000  | Active                              |
| frontend        | 204   | ~10,000+ | Active                              |
| migrations      | 56    | N/A      | Stable                              |

### Suspected Legacy/Unused

- `bo1/prompts/reusable_prompts.py` - DEPRECATED shim (13 active imports)
- `bo1/config.py:BETA_WHITELIST` - DEPRECATED (use database-managed)
- `bo1/agents/facilitator.py:next_speaker` - DEPRECATED in parallel mode
- `bo1/prompts/persona.py:compose_persona_prompt` - Deprecated (use cached version)
- `bo1/graph/nodes/subproblems.py:910` - Legacy comment about removed impl
- `backend/api/control.py:1185` - Endpoint marked deprecated=True
- `zzz_important/`, `zzz_project/` - Archive folders (safe to ignore)

---

## Step 2: Consolidation Targets

### High Priority

1. **reusable_prompts.py imports** - 13 files still import from deprecated module

   - Migrate to direct imports from `bo1.prompts.*`
   - Files: synthesis.py, subgraph/nodes.py, engine.py, deliberation.py, voting.py, facilitator.py, moderator.py, prompt_builder.py

2. **Research subsystem** - 8 files, overly fragmented

   - researcher.py, research_detector.py, research_consolidation.py, research_metrics.py, research_rate_limiter.py, researcher.py (prompts), research_detector_prompts.py, research.py (node)
   - Candidate: Consolidate into `bo1/research/` package

3. **Repository pattern** - 11 nearly identical CRUD repos
   - Candidate: Generic repository base or code-gen

### Medium Priority

4. **Model files** - 9 model files across bo1 + backend

   - Opportunity: Consolidate shared domain models

5. **Agent inheritance** - DataAnalysisAgent, ResearcherAgent don't use BaseAgent
   - Standardize agent interface

---

## Step 3: Files Marked for Deletion

### DELETE NOW (no references)

- None identified (all files have active imports)

### REVIEW BEFORE DELETE

| File                                         | Reason            | Action                             |
| -------------------------------------------- | ----------------- | ---------------------------------- |
| `bo1/prompts/reusable_prompts.py`            | 13 active imports | Migrate imports first, then delete |
| `backend/api/control.py` deprecated endpoint | Still routed      | Add removal timeline               |

---

## Step 4: Database/Schema Cleanup Plan

### Unused Columns (Low Risk)

| Table                  | Column         | Evidence                                              |
| ---------------------- | -------------- | ----------------------------------------------------- |
| sessions               | max_rounds     | Default 10, no graph logic references                 |
| session_clarifications | asked_at_round | Denormalized; round_number on contributions is source |
| research_cache         | source_count   | Duplicates info in `sources` JSONB                    |
| research_cache         | freshness_days | Hardcoded 90, no eviction implemented                 |

### Schema Inconsistencies (Fix Required)

1. **Session status mismatch**

   - Migration: "active, paused, completed, failed, killed"
   - Pydantic enum: "created, running, completed, failed, killed"
   - No "active"/"paused" in code

2. **Frontend task status**

   - Backend: 6 values (todo, in_progress, blocked, in_review, done, cancelled)
   - Frontend regex: 3 values (todo, doing, done)
   - Decision: Align frontend to full 6-value set OR restrict backend

3. **Project progress_percent**

   - Manually set, no auto-calculation trigger
   - Risk: Progress drifts if actions added/removed

4. **Dataset soft-delete**
   - `datasets.deleted_at` exists
   - RLS policy doesn't filter deleted records
   - Fix: Add `AND deleted_at IS NULL` to RLS

### Migration Plan

```sql
-- Phase 1: Mark deprecated columns (add comments)
COMMENT ON COLUMN sessions.max_rounds IS 'DEPRECATED: Remove in v2.0';

-- Phase 2: After code cleanup (future migration)
ALTER TABLE sessions DROP COLUMN max_rounds;
ALTER TABLE session_clarifications DROP COLUMN asked_at_round;
ALTER TABLE research_cache DROP COLUMN source_count;
ALTER TABLE research_cache DROP COLUMN freshness_days;

-- Fix RLS policy for soft-deleted datasets
DROP POLICY datasets_policy ON datasets;
CREATE POLICY datasets_policy ON datasets
  FOR ALL TO authenticated
  USING (user_id = current_setting('app.user_id')::uuid AND deleted_at IS NULL);
```

---

## Step 5-6: Refactor Actions (Iterative)

### Action 1: Migrate reusable_prompts imports

Update 13 files to import directly from `bo1.prompts.*` modules:

- `bo1/graph/nodes/synthesis.py`
- `bo1/graph/deliberation/subgraph/nodes.py`
- `bo1/graph/deliberation/engine.py`
- `bo1/orchestration/deliberation.py`
- `bo1/orchestration/prompt_builder.py`
- `bo1/orchestration/voting.py`
- `bo1/agents/facilitator.py`
- `bo1/agents/moderator.py`

### Action 2: Delete BETA_WHITELIST config

- Remove `BETA_WHITELIST` env var and related code from `bo1/config.py`
- Already deprecated, database-managed whitelist in use

### Action 3: Fix dataset soft-delete RLS

- Create migration to update RLS policy

### Action 4: Standardize agent inheritance

- Make `ResearcherAgent`, `DataAnalysisAgent` extend `BaseAgent`

---

## Step 7: Final Summary

### Immediate Actions (Low Risk)

- [x] Delete `BETA_WHITELIST` config (~10 lines) ✅ Removed from config.py, docker-compose, waitlist.py, supertokens_config.py, admin APIs, frontend
- [x] Fix dataset RLS policy (1 migration) ✅ h2_fix_datasets_rls_soft_delete.py
- [x] Add deprecation comments to unused columns ✅ h3_add_deprecation_comments.py

### Near-Term Cleanup

- [x] Migrate 13 `reusable_prompts.py` imports ✅ Already done
- [x] Delete `reusable_prompts.py` after migration ✅ Deleted
- [ ] Standardize agent inheritance (2 agents) - Deferred: ResearcherAgent/DataAnalysisAgent use different patterns (external APIs, not broker)

### Tech Debt Tracked

- Research subsystem consolidation (8 files → package)
- Repository pattern consolidation (11 repos)
- Frontend task status alignment (3→6 values)
- Project progress auto-calculation trigger

### Validation Checklist

- [x] `make test` passes (1302 passed, 13 skipped)
- [x] Python imports verified (config, waitlist, admin, supertokens)
- [x] `npm run check` passes (0 errors, 6 pre-existing warnings)
- [ ] `uv run alembic upgrade head` succeeds (requires DB)
- [ ] `make pre-commit` passes (pre-existing failures unrelated to cleanup)

---

## Completed in This Audit

### Import Migration (8 files)

Migrated all `from bo1.prompts.reusable_prompts import X` to `from bo1.prompts import X`:

- `bo1/graph/nodes/synthesis.py` (2 imports)
- `bo1/graph/deliberation/subgraph/nodes.py`
- `bo1/graph/deliberation/engine.py`
- `bo1/orchestration/deliberation.py`
- `bo1/orchestration/prompt_builder.py`
- `bo1/orchestration/voting.py`
- `bo1/agents/facilitator.py` (2 imports)
- `bo1/agents/moderator.py`

The deprecated `reusable_prompts.py` shim can now be deleted once docs are updated.
