# Deferred Cleanup Plan

## 1. ~~Remove `postgres_manager.py` Shim Layer~~ COMPLETED

**Status:** COMPLETED

**What was done:**
- Updated 34 files with direct repository imports
- Deleted `bo1/state/postgres_manager.py`
- Fixed malformed imports introduced by bulk replacement

---

## 2. ~~Consolidate Console Implementations~~ NOT NEEDED

**Analysis:** These are NOT duplicates - they're different layers:
- `bo1/ui/console.py` - Low-level Rich UI wrapper (presentation layer)
- `bo1/interfaces/console.py` - High-level adapter for running deliberations (orchestration layer)

`interfaces/console.py` imports from `ui/console.py` - this is proper separation of concerns.

**Status:** SKIPPED - architecture is correct

---

## 3. ~~Consolidate Duplicate `get_user_info()` Endpoints~~ COMPLETED

**Status:** COMPLETED

**What was done:**
- Analyzed all 4 implementations
- Found `/api/auth/user` (supertokens_routes.py) was UNUSED by frontend
- Frontend only uses `/api/auth/me` from auth.py
- Removed entire `supertokens_routes.py` file (71 lines)
- Updated main.py to remove the router

**Note:** admin/users.py and admin/helpers.py serve different purposes (admin-only endpoints) and were kept.

---

## 4. ~~Consolidate Event Extractors~~ ALREADY OPTIMIZED

**Status:** SKIPPED - architecture is already well-structured

**Analysis:**
- File uses declarative `FieldExtractor` config pattern
- `EventExtractorRegistry` provides centralized registration
- 16 extract functions are semantically distinct (not duplicates)
- Each handles different event types with different data shapes
- No actual redundancy to consolidate

---

## Summary

| Task | Status |
|------|--------|
| postgres_manager.py removal | COMPLETED |
| Console consolidation | SKIPPED (not duplicates) |
| get_user_info() consolidation | COMPLETED |
| Event extractors refactor | SKIPPED (already optimized) |

**All planned tasks completed or analyzed. No further refactoring needed.**
