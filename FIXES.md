## REFACTORING AUDIT (2025-12-02) - COMPLETED

### CRITICAL PRIORITY (God Files)

#### Backend - Split immediately

1. **`backend/api/admin.py`** (1858 lines) → Split into 5 services + 6 routers

   - [x] ✅ ALREADY DONE - The `admin/` package already exists with split modules!
   - [x] Deleted obsolete `admin.py` file (Python was using the package)
   - [x] `admin/users.py` (467 lines) - User management
   - [x] `admin/sessions.py` (325 lines) - Session management
   - [x] `admin/research_cache.py` (174 lines) - Cache management
   - [x] `admin/beta_whitelist.py` (252 lines) - Whitelist management
   - [x] `admin/waitlist.py` (237 lines) - Waitlist management
   - [x] `admin/metrics.py` (112 lines) - Metrics
   - [x] `admin/models.py` (420 lines) - Pydantic models
   - [x] Extract service layer from routers
     - [x] Applied `@handle_api_errors` decorator to all 16 admin endpoints
     - [x] Created `AdminQueryService` (user queries with metrics)
     - [x] Created `AdminValidationService` (email/tier validation)
     - [x] Created `AdminApprovalService` (waitlist approval workflow)
   - [x] Fill `admin/helpers.py` with shared utilities
     - [x] `_row_to_user_info()`, `_row_to_whitelist_entry()`, `_row_to_waitlist_entry()`
     - [x] `USER_WITH_METRICS_SELECT`, `USER_WITH_METRICS_GROUP_BY` SQL constants
     - [x] `_to_iso()`, `_to_iso_or_none()` datetime helpers
   - ✅ COMPLETE | Line reductions: users.py 467→201 (57%), waitlist.py 237→116 (51%), beta_whitelist.py 252→173 (31%)

2. **`bo1/state/postgres_manager.py`** (1758 lines) → Implement Repository Pattern

   - [x] Created `bo1/state/database.py` - Connection pool infrastructure
   - [x] Created `bo1/state/repositories/base.py` - BaseRepository class
   - [x] Created `bo1/state/repositories/user_repository.py` - UserRepository
   - [x] Created `bo1/state/repositories/session_repository.py` - SessionRepository (+ get_metadata, clarifications)
   - [x] Created `bo1/state/repositories/cache_repository.py` - CacheRepository (+ get_stale)
   - [x] Created `bo1/state/repositories/contribution_repository.py` - ContributionRepository
   - [x] Updated postgres_manager.py to be backward-compatibility shim (1758 → 314 lines, -82%)
   - [x] All 30+ consumers continue working with no changes required
   - ✅ COMPLETE | 127 tests passing | Impact: Critical

3. **`bo1/orchestration/deliberation.py`** (988 lines) → Split DeliberationEngine
   - [x] Created `bo1/orchestration/persona_executor.py` - PersonaExecutor class (274 lines)
   - [x] Created `bo1/orchestration/prompt_builder.py` - PromptBuilder class (376 lines)
   - [x] Created `bo1/orchestration/metrics_calculator.py` - MetricsCalculator class (273 lines)
   - [x] Updated deliberation.py: 988 → 582 lines (41% reduction)
   - [x] `_call_persona_async()`: 303 → 48 lines (84% reduction)
   - ✅ All 79 deliberation tests passing | Impact: High

#### Frontend - Split immediately

4. **`frontend/src/routes/(app)/meeting/[id]/+page.svelte`** (1789 lines) → Split into 5-7 components
   - [x] Created `useTimer.svelte.ts` hooks (useElapsedTimer, useStalenessTimer, useCarouselTimer, usePhaseTimer)
   - [x] Created `<MeetingHeader>` component
   - [x] Created `<WorkingStatusBanner>` component
   - [x] Created `<MeetingProgress>` component
   - [x] Created `<SubProblemTabs>` component
   - [x] Created `<EventStream>` component
   - [x] Created `index.ts` barrel file
   - [x] Updated +page.svelte to use new components (~200 lines removed)
   - ✅ COMPLETE | Impact: Critical

### HIGH PRIORITY

5. **`backend/api/event_collector.py`** (1137 lines → 1037 lines, -9%)

   - [x] Extracted 98-line prompt to `bo1/prompts/contribution_summary_prompts.py`
   - [x] Consolidated duplicate error handling into `_mark_session_failed()` helper
   - [~] Split into `EventEmitter`, `EventHandlers`, `SynthesisProcessor` (DEFERRED - not worth effort)
     - File already well-organized with clear NODE_HANDLERS dispatch table
     - Further splitting would create circular dependencies
     - Revisit only if file exceeds 1200 lines
   - **Quick wins complete**: 1137 → 1037 lines | All tests passing

6. **`backend/api/sessions.py`** (852 lines)

   - [ ] Extract `SessionService` class (complex Redis/Postgres fallback logic)
   - **Note**: Tightly coupled to Redis + Postgres dual-source pattern; lower priority
   - Effort: 15-20 hours (defer until Redis removal)

7. **`frontend/src/routes/+page.svelte`** (1032 lines) - Landing page
   - [x] Created `useIntersectionObserver.svelte.ts` hook with `useSectionObservers`
   - [x] Created `<HeroSection>` component (waitlist form, trust badges)
   - [x] Created `<MetricsGrid>` component (quantified value metrics)
   - [x] Created `<FAQAccordion>` component (expandable FAQ)
   - [x] Created `<SampleDecisionModal>` component
   - [x] Created `index.ts` barrel file for landing components
   - [x] Updated +page.svelte to use new components
   - ✅ COMPLETE | 1032 → 905 lines (12% reduction + 4 new reusable components)

### MEDIUM PRIORITY

8. **`frontend/src/lib/utils/pdf-report-generator.ts`** (882 lines)

   - [x] Extracted CSS to `frontend/src/lib/styles/pdf-report.css` (447 lines)
   - [x] Created `markdown-formatter.ts` utility (formatMarkdownToHtml, extractMarkdownSection, parseSynthesisSections)
   - [x] Created `report-data-extractor.ts` utility (extractExperts, countContributionsByExpert, calculateRounds, etc.)
   - [x] Refactored pdf-report-generator.ts with composable render functions
   - ✅ COMPLETE | 882 → 287 lines (67% reduction)

9. **`frontend/src/lib/components/events/ActionableTasks.svelte`** (415 lines)

   - [x] Created `<TaskStatusSelect>` component (status dropdown)
   - [x] Created `<TaskDetails>` component (What & How, Success/Kill Criteria, Dependencies)
   - [x] Created `index.ts` barrel file for tasks components
   - [x] Updated ActionableTasks.svelte to use new components
   - ✅ COMPLETE | 415 → 269 lines (35% reduction)

10. **`frontend/src/lib/api/client.ts`** (411 lines)
    - [x] Created `buildQueryString()` and `withQueryString()` utilities
    - [x] Created `mergeHeaders()` utility for flexible header handling
    - [x] Added generic request helpers (`post`, `put`, `patch`, `delete`)
    - [x] Moved admin types to `types.ts` (AdminUser, WhitelistEntry, WaitlistEntry, etc.)
    - ✅ COMPLETE | 411 → 348 lines (15% reduction + better type safety)

### CROSS-CUTTING FIXES (Quick Wins)

- [x] Create `useTimer.svelte.ts` reusable hook (fix 3 duplicate implementations) ✅ DONE
- [x] Create color mapping utilities (duplicated in 5+ components) ✅ DONE
- [x] Convert `quality-labels.ts` switch statements to object lookups ✅ DONE
- [x] Extract database boilerplate into decorator/context manager ✅ DONE
  - [x] Added `_execute_paginated()` to BaseRepository (pagination helper)
  - [x] Added `_to_iso_string()` and `_to_iso_string_or_none()` to BaseRepository

### ESTIMATED TOTALS

| Area              | Files  | Hours       | Weeks    |
| ----------------- | ------ | ----------- | -------- |
| Backend Critical  | 3      | 125-155     | 3-4      |
| Frontend Critical | 1      | 24-40       | 1        |
| High Priority     | 4      | 83-114      | 2-3      |
| Medium Priority   | 3      | 48-56       | 1-2      |
| **TOTAL**         | **11** | **280-365** | **7-10** |

### EXPECTED OUTCOMES

- Average file size: 980 → 250-350 lines (-65%)
- Code duplication: 20%+ → <5%
- Cyclomatic complexity: 8-15 → 4-8
- Onboarding time: 2+ weeks → 3-5 days

---
