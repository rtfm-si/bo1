# Cleanup Audit Report

**Date:** Dec 8, 2025

## Changes Made

### 1. Consolidated archived/moderation.py
- Merged `bo1/graph/nodes/archived/moderation.py` into `bo1/graph/nodes/moderation.py`
- The "archived" folder was a misnomer - `facilitator_decide_node` was actively used
- Now both `facilitator_decide_node` and `moderator_intervene_node` live in single file
- Deleted `bo1/graph/nodes/archived/` directory
- Updated `__init__.py` imports
- All 20 related tests pass

---

## Analyzed & Kept (By Design)

| Item | Reason Kept |
|------|-------------|
| `bo1/demo.py` | Used by `make demo` / `make demo-interactive` |
| `backend/api/waitlist.py` | Pre-launch feature, user requested keep |
| `backend/api/admin/beta_whitelist.py` | Pre-launch feature, user requested keep |
| `backend/api/industry_insights.py` | Future feature for aggregate insights |
| `frontend/src/lib/components/ui/Bo*.svelte` | Intentional wrapper pattern per UI_GOVERNANCE.md |
| `frontend/src/lib/stores/theme.ts` | Used in +layout.svelte |

---

## Database Schema Status

| Table | Status |
|-------|--------|
| `votes` | DROPPED (Dec 8 migration 9626a52) |
| `schema_migrations` | DROPPED (Dec 8 migration 9626a52) |
| `industry_insights` | KEEP - future feature |
| `beta_whitelist` | KEEP - pre-launch feature |
| `waitlist` | KEEP - pre-launch feature |
| `metric_templates` | KEEP - actively used by MetricsRepository |

---

## Conclusion

**Codebase is clean:**
- No truly unused Python files found (all apparent orphans are test utilities or Makefile targets)
- No unused frontend components (all are either in design-system or intentional wrappers)
- Database schema is current after Dec 8 migrations
- All tests pass
