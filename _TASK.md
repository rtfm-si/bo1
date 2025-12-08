# Bo1 Task List – 2025-12-08

## Active Issues (from meeting bo1_4eefdf7e)

### ~~1. AttributeError: 'dict' object has no attribute 'sub_problems'~~ ✅
- **Status**: ✅ Fixed 2025-12-08
- **Fix**: Added dict/object handling in `bo1/graph/routers.py` and `backend/api/event_extractors.py`
- **Tests**: 4 new tests in `tests/graph/test_routers.py`

### ~~2. Discussion quality label overwritten incorrectly~~ ✅
- **Status**: ✅ Fixed 2025-12-08
- **Fix**: Preserved actual quality metrics when meeting completes in `DecisionMetrics.svelte`
- **Change**: Label shows actual quality (e.g., "Thorough Discussion"), badge shows "✓ Complete"

### ~~3. ntfy alert shows 0 saved contributions~~ ✅
- **Status**: ✅ Fixed 2025-12-08
- **Fix**: Added `notify_meeting_completed()` to ntfy.py, `count_by_session()` to contribution_repository
- **Integration**: Called from `event_collector.py` when session marked complete

### ~~4. Meeting page refresh shows masked events~~ ✅
- **Status**: ✅ Fixed 2025-12-08
- **Fix**: Added `subproblem_started` and `research_results` to `HIDDEN_EVENT_TYPES` in `constants.ts`
- **Note**: Historical events already filtered through `addEvent()` which uses HIDDEN_EVENT_TYPES

### ~~5. Research results caching/indexing verification~~ ✅
- **Status**: ✅ Complete 2025-12-08
- **Audit Findings**: Infrastructure properly implemented
  - Storage: `research_cache` table with vector(1024) embeddings
  - HNSW index: `idx_research_cache_embedding_hnsw` (m=16, ef_construction=64)
  - Reuse: `find_by_embedding()` with 0.85 similarity threshold
- **Tests**: 15 passing (4 in test_research_node.py, 11 in test_researcher_cache.py)

### ~~6. Prompts conciseness for meetings~~ ✅
- **Status**: ✅ Complete 2025-12-08
- **Changes**:
  - COMMUNICATION_PROTOCOL: 100-150 words (was 150-250), added brevity directive
  - BEHAVIORAL_GUIDELINES: Added "NEVER write long contributions" + verbose/concise example pair
  - persona.py: 1-2 paragraphs max (was 2-4)
  - synthesis.py: 400-600 words (was 600-800)

---

## Completed (from previous audit)

- ✅ Test suite audit complete
- ✅ 6 coverage gaps addressed
- ✅ Auth middleware tests (15 tests)
- ✅ Meta-synthesis tests (4 tests)
- ✅ Research node tests (4 tests)
- ✅ Parallel subproblems tests (14 tests)
- ✅ Frontend SSE tests (11 tests)
- ✅ Context API tests enabled (7 tests)
