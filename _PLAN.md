# Plan: Fix [BUG] Items

## Summary

- **[BUG-CONTEXT]** Clarifications not persisted - missing DB column + CONTEXT_FIELDS entry
- **[BUG-DELIB]** Expert repetition - novelty detection works but needs "productive disagreement" handling
- **[BUG-OUTPUT]** Add actions to PDF report export

## Investigation Findings

### BUG-DELIB: Novelty Detection Analysis (Session bo1_b28e3e62)

**Metrics from logs:**
| Round | Novelty | Convergence | Conflict | Semantic Dedup |
|-------|---------|-------------|----------|----------------|
| 2 | 0.50 | 0.27 | - | - |
| 3 | 0.34 | 0.16 | 0.92 | - |
| 4 | 0.37 | 0.00 | 0.88 | - |
| 5 | 0.35 | 0.08 | 0.76 | - |
| 6 | 0.34 | 0.16 | 0.63 | **1 of 2 filtered (50%)** |

**Observations:**

1. **Novelty IS dropping** (0.50 → 0.34)
2. **Semantic dedup fired** in Round 6
3. **Conflict is HIGH** (0.92 → 0.63) = experts genuinely disagree
4. **Convergence stays LOW** (<0.27) = no consensus emerging
5. **Meeting hit hard cap** of 6 rounds

**The real problem:** When experts DISAGREE, the system keeps them debating hoping for convergence. But if they're repeating arguments (low novelty) while still disagreeing (high conflict, low convergence), they should be guided to:

- Acknowledge disagreement explicitly
- Find partial common ground
- "Disagree and commit" to a recommendation
- Present conditional recommendations ("If X, do A; if Y, do B")

**Current state:**

- Synthesis prompts handle this well (dissenting_views section)
- Facilitator prompt mentions disagreements but doesn't have explicit guidance for **persistent disagreement**
- No mechanism to detect "stalled disagreement" (high conflict + low novelty for 2+ rounds)

### Proposed Enhancement: "Productive Disagreement" Mode

When detected: `conflict > 0.7 AND novelty < 0.40 AND novelty_delta < 0.05 for 2+ rounds`

**Options:**

1. **Add facilitator guidance** for "stalled disagreement" - prompt experts to find common ground
2. **Add new Facilitator Option F** - "Acknowledge Impasse" that explicitly asks experts to:
   - State what they agree on
   - State what they disagree on and why
   - Propose a conditional recommendation
3. **Trigger early synthesis** with explicit "disagreement detected" flag for synthesis prompt

**Recommendation:** Park for now, fix priority bugs first. This is an enhancement, not a bug.

---

## Implementation Steps

### BUG-CONTEXT: Fix Clarification Persistence (PRIORITY)

**Root cause**: `save_context()` filters to `CONTEXT_FIELDS` only, and `clarifications` is not in that list. Also no DB column exists.

1. **Create migration**: Add `clarifications` JSONB column to `user_context`

   ```sql
   ALTER TABLE user_context ADD COLUMN clarifications JSONB DEFAULT '{}';
   ```

2. **Update `bo1/state/repositories/user_repository.py`**:

   - Add `"clarifications"` to `CONTEXT_FIELDS` list (line ~178)
   - Add `"clarifications"` to `jsonb_fields` set (line ~263)

3. **Verify flow**:
   - `control.py:1366-1392` already tries to save clarifications
   - `context.py:76-89` already tries to load and inject them

### BUG-OUTPUT: Add Actions to PDF Report

1. **Update `frontend/src/lib/utils/pdf-report-generator.ts`**

   - Add `actions` to `ReportGeneratorParams` interface
   - Create `renderActionsSection()` function
   - Insert after synthesis sections

2. **Update results page** to pass actions to generator

3. **Add CSS** for `.actions-section`, `.action-item`

---

## Tests

- Manual validation:
  - Answer clarifying questions → Check `/settings/context/insights`
  - Export PDF → Verify actions appear

## Dependencies & Risks

- Migration requires `uv run alembic upgrade head`
- Need to handle existing rows (default `'{}'`)
