# Terminology Standardization Plan

**Created**: 2024-12-02
**Status**: Ready for Implementation
**Estimated Effort**: 4-6 hours

---

## Executive Summary

This plan standardizes terminology across Board of One to create a consistent user experience. The main changes are:

| Current Term | New User-Facing Term | Internal Term (unchanged) |
|--------------|---------------------|---------------------------|
| problem, problem statement | **decision** | `problem_statement` (API/DB) |
| sub-problem | **focus area** | `sub_problem` (code) |
| deliberation | **meeting** (UI) | `deliberation` (backend) |
| persona | **expert** (already done) | `persona` (code) |

**Scope**: User-facing text only. No API/database schema changes.

---

## Guiding Principles

1. **User-facing vs Internal**: Only change what users see. Keep internal variable names, API fields, and database columns as-is.
2. **Consistency**: Use the same term everywhere in the same context.
3. **No Breaking Changes**: API contracts remain unchanged (`problem_statement`, `sub_problem_index`, etc.)
4. **Backward Compatibility**: Old SSE event types stay the same; only display labels change.

---

## Phase 1: "Problem" → "Decision" (HIGH PRIORITY)

### 1.1 Frontend Event Humanization
**File**: `frontend/src/lib/utils/event-humanization.ts`

| Line | Current | Replacement |
|------|---------|-------------|
| 14 | `"Analyzing Your Problem"` | `"Analyzing Your Decision"` |
| 15 | `"Problem Breakdown Complete"` | `"Decision Breakdown Complete"` |
| 66 | `"The board is reviewing your problem..."` | `"The board is reviewing your decision..."` |
| 74 | `"Breaking down your problem into..."` | `"Breaking down your decision into key areas..."` |
| 81 | `"Identifying the best experts for this problem..."` | `"Identifying the best experts for this decision..."` |

### 1.2 New Meeting Form
**File**: `frontend/src/routes/(app)/meeting/new/+page.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 23 | `'Please enter a problem statement'` | `'Please describe your decision'` |
| 28 | `'Problem statement should be at least 20 characters'` | `'Please provide at least 20 characters describing your decision'` |
| 216 | `'Your problem will be analyzed and broken down into sub-problems'` | `'Your decision will be analyzed and broken down into key focus areas'` |

### 1.3 Dashboard Empty State
**File**: `frontend/src/routes/(app)/dashboard/+page.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 120 | `'...analyze your problem from multiple expert perspectives.'` | `'...analyze your decision from multiple expert perspectives.'` |

### 1.4 Decomposition Component
**File**: `frontend/src/lib/components/events/DecompositionComplete.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 19 | `"Problem Decomposition Complete"` | `"Decision Breakdown Complete"` |

### 1.5 Landing Page FAQ
**File**: `frontend/src/routes/+page.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 207 | `"...If you can type your problem, you can use..."` | `"...If you can describe your decision, you can use..."` |

### 1.6 Legal/Privacy Page
**File**: `frontend/src/routes/legal/privacy/+page.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 47 | `<strong>Problem Statements:</strong>` | `<strong>Decision Submissions:</strong>` |
| 123 | `'Your problem statements with other users...'` | `'Your decision submissions with other users...'` |

### 1.7 API Documentation
**File**: `backend/api/main.py`

| Line | Current | Replacement |
|------|---------|-------------|
| 73 | `"...personas debate your problem"` | `"...personas debate your decision"` |
| 267 | `"If the problem persists..."` | `"If this issue persists..."` |

**Total Phase 1 Changes: 14 occurrences**

---

## Phase 2: "Sub-Problem" → "Focus Area" (HIGH PRIORITY)

### 2.1 Event Humanization
**File**: `frontend/src/lib/utils/event-humanization.ts`

| Line | Current | Replacement |
|------|---------|-------------|
| 23 | `"Starting Sub-Problem"` | `"Starting Focus Area"` |
| 24 | `"Sub-Problem Resolved"` | `"Focus Area Complete"` |
| 95 | `"Addressing sub-problem ${index} of ${total}."` | `"Addressing focus area ${index} of ${total}."` |

### 2.2 Progress Components
**File**: `frontend/src/lib/components/ui/DualProgress.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 72 | `Sub-problem {currentSubProblem} of {totalSubProblems}` | `Focus area {currentSubProblem} of {totalSubProblems}` |

**File**: `frontend/src/lib/components/ui/MeetingStatusBar.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 74 | `Sub-problem {current}/{total}` | `Focus area {current}/{total}` |

### 2.3 Event Components
**File**: `frontend/src/lib/components/events/SubProblemProgress.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 120 | `"Sub-Problem Complete"` | `"Focus Area Complete"` |
| 4 | Comment: `sub-problem` | Comment: `focus area` |

### 2.4 Meeting Page
**File**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 1129 | `Sub-problem complete` | `Focus area complete` |
| 1261 | `aria-label="Sub-problem tabs"` | `aria-label="Focus area tabs"` |
| 1560 | `{count} of {total} sub-problems completed` | `{count} of {total} focus areas completed` |
| 1654 | `Preparing next sub-problem...` | `Preparing next focus area...` |

### 2.5 Tab Labels
**File**: `frontend/src/routes/(app)/meeting/[id]/lib/subProblemTabs.ts`

| Line | Current | Replacement |
|------|---------|-------------|
| 146 | `label: \`Sub-problem ${index + 1}\`` | `label: \`Focus Area ${index + 1}\`` |

### 2.6 Action Plan Component
**File**: `frontend/src/lib/components/events/ActionPlan.svelte`

| Line | Current | Replacement |
|------|---------|-------------|
| 111 | `for this sub-problem` | `for this focus area` |
| 188 | `sub-problem{s} deliberated` | `focus area{s} deliberated` |

### 2.7 Console UI (CLI)
**File**: `bo1/interfaces/console.py`

| Line | Current | Replacement |
|------|---------|-------------|
| 245 | `Sub-Problem {n} of {total}` | `Focus Area {n} of {total}` |
| 329 | `Decomposed into {n} sub-problems` | `Decomposed into {n} focus areas` |
| 529 | `Sub-problem {n} complete` | `Focus area {n} complete` |

**File**: `bo1/ui/console.py`

| Line | Current | Replacement |
|------|---------|-------------|
| 158 | `title=f"Sub-Problem: {id}"` | `title=f"Focus Area: {id}"` |
| 487 | `decomposed into {n} sub-problems` | `decomposed into {n} focus areas` |
| 500 | `Table(title="Sub-Problems"...)` | `Table(title="Focus Areas"...)` |
| 552 | `Edit a sub-problem goal` | `Edit a focus area goal` |
| 555 | `Add new sub-problem` | `Add new focus area` |
| 556 | `Remove sub-problem` | `Remove focus area` |
| 574-577 | `Updated sub-problem {n}` | `Updated focus area {n}` |
| 612 | `Added sub-problem {id}` | `Added focus area {id}` |
| 619 | `Removed sub-problem {id}` | `Removed focus area {id}` |

**File**: `bo1/demo.py`

| Line | Current | Replacement |
|------|---------|-------------|
| 123 | `Decomposed into {n} sub-problems` | `Decomposed into {n} focus areas` |

**Total Phase 2 Changes: 29 occurrences**

---

## Phase 3: Terminology Documentation (MEDIUM PRIORITY)

### 3.1 Update CLAUDE.md
Add a terminology section:

```markdown
## Terminology Standards

| User-Facing | Internal Code | Notes |
|-------------|---------------|-------|
| Meeting | session, deliberation | UI says "Meeting", API uses "session" |
| Decision | problem_statement | Form asks about "decision", DB stores as problem_statement |
| Focus Area | sub_problem | UI shows "Focus Area 1", code uses sub_problem_index |
| Expert | persona | UI shows "Expert Panel", code uses PersonaProfile |
| Recommendation | vote, synthesis | Final output terminology |
```

### 3.2 Update Design Tokens
**File**: `frontend/src/lib/design/tokens.ts`

Update phase labels for consistency:

| Current | Replacement |
|---------|-------------|
| `decomposition: { label: 'Analysis' }` | Keep (already good) |
| `discussion: { label: 'Discussion' }` | `discussion: { label: 'Expert Discussion' }` |

---

## Phase 4: Quality Labels & Status Messages (LOW PRIORITY)

### 4.1 Quality Labels
**File**: `frontend/src/lib/utils/quality-labels.ts`

Consider updating metaphor descriptions for consistency, but these are already well-written and may not need changes.

---

## Implementation Checklist

### Pre-Implementation
- [ ] Create feature branch: `feat/terminology-standardization`
- [ ] Run existing tests to establish baseline
- [ ] Take screenshots of current UI for comparison

### Phase 1: Problem → Decision (2 hours)
- [ ] `event-humanization.ts` - 5 changes
- [ ] `meeting/new/+page.svelte` - 3 changes
- [ ] `dashboard/+page.svelte` - 1 change
- [ ] `DecompositionComplete.svelte` - 1 change
- [ ] `+page.svelte` (landing) - 1 change
- [ ] `privacy/+page.svelte` - 2 changes
- [ ] `main.py` - 2 changes
- [ ] Run frontend tests

### Phase 2: Sub-Problem → Focus Area (2 hours)
- [ ] `event-humanization.ts` - 3 changes
- [ ] `DualProgress.svelte` - 1 change
- [ ] `MeetingStatusBar.svelte` - 1 change
- [ ] `SubProblemProgress.svelte` - 2 changes
- [ ] `meeting/[id]/+page.svelte` - 4 changes
- [ ] `subProblemTabs.ts` - 1 change
- [ ] `ActionPlan.svelte` - 2 changes
- [ ] `console.py` (interfaces) - 3 changes
- [ ] `console.py` (ui) - 9 changes
- [ ] `demo.py` - 1 change
- [ ] Run all tests

### Phase 3: Documentation (30 min)
- [ ] Update CLAUDE.md with terminology section
- [ ] Update design tokens if needed

### Post-Implementation
- [ ] Run full test suite: `make test`
- [ ] Manual UI review of all affected screens
- [ ] Run pre-commit hooks: `make pre-commit`
- [ ] Create PR with before/after screenshots

---

## Files Changed Summary

| File | Changes | Priority |
|------|---------|----------|
| `frontend/src/lib/utils/event-humanization.ts` | 8 | HIGH |
| `frontend/src/routes/(app)/meeting/new/+page.svelte` | 3 | HIGH |
| `frontend/src/routes/(app)/meeting/[id]/+page.svelte` | 4 | HIGH |
| `frontend/src/lib/components/events/DecompositionComplete.svelte` | 1 | HIGH |
| `frontend/src/lib/components/events/SubProblemProgress.svelte` | 2 | HIGH |
| `frontend/src/lib/components/events/ActionPlan.svelte` | 2 | HIGH |
| `frontend/src/lib/components/ui/DualProgress.svelte` | 1 | HIGH |
| `frontend/src/lib/components/ui/MeetingStatusBar.svelte` | 1 | HIGH |
| `frontend/src/routes/(app)/meeting/[id]/lib/subProblemTabs.ts` | 1 | HIGH |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | 1 | HIGH |
| `frontend/src/routes/+page.svelte` | 1 | MEDIUM |
| `frontend/src/routes/legal/privacy/+page.svelte` | 2 | MEDIUM |
| `bo1/interfaces/console.py` | 3 | MEDIUM |
| `bo1/ui/console.py` | 9 | MEDIUM |
| `bo1/demo.py` | 1 | LOW |
| `backend/api/main.py` | 2 | MEDIUM |
| `CLAUDE.md` | 1 | LOW |

**Total: 43 changes across 17 files**

---

## Testing Strategy

### Automated Tests
```bash
# Frontend tests
cd frontend && npm run test

# Backend tests
pytest tests/ -v

# Full suite
make test
```

### Manual Testing Checklist
- [ ] Create new meeting - verify form labels
- [ ] View meeting in progress - verify focus area labels
- [ ] View completed meeting - verify all terminology
- [ ] Check dashboard empty state
- [ ] Check dashboard with meetings
- [ ] Review privacy policy page
- [ ] Run CLI demo and verify console output

---

## Rollback Plan

If issues arise:
1. All changes are string replacements only
2. Git revert the commit
3. No database migrations needed
4. No API changes needed

---

## Future Considerations

### Not Included in This Plan (Breaking Changes)
These would require API versioning and are NOT recommended:

1. **Rename API field**: `problem_statement` → `decision_statement`
   - Would break all existing clients
   - Requires database migration
   - Not worth the effort for internal field names

2. **Rename event types**: `subproblem_started` → `focus_area_started`
   - Would break SSE parsing
   - Frontend already handles translation via humanization

3. **Rename database columns**
   - Migration complexity
   - No user impact

### Recommended for Future
1. Consider adding a `TERMINOLOGY.md` or glossary to the docs
2. Add linting rules to catch inconsistent terminology in new code
3. Consider i18n support if terminology needs to vary by locale
