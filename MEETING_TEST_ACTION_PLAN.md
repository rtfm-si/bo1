# Meeting System Test Report & Action Plan

**Test Date:** 2025-12-06
**Test Problem:** "Should we raise a Series A round now or wait 6 months to improve metrics?"
**Session ID (Test 2):** `bo1_e1bd3e44-0191-4cfa-986c-a30ff0220584`
**Session ID (Test 1):** `bo1_b3a8697a-7c54-4b3a-b549-7dc07a54965f`
**Outcome:** **FAILED** - Sub-problems lost after checkpoint resume

---

## Update (2025-12-06 - Test 2)

After fixing issues from Test 1, a second test was run. A **NEW CRITICAL BUG** was discovered:

### P0-CRITICAL: Sub-Problems Lost After Checkpoint Resume

**Status:** BLOCKING ALL MEETINGS WITH CLARIFICATION FLOW

**Evidence:**
```
17:32:11 decompose_node: Created 3 sub-problems (target: 1-3, max: 4)
17:34:44 analyze_dependencies_node: Sequential mode (feature_flag=True, sub_problems=0)
17:34:44 Recommending personas for sub-problem: ['bo1', 'models', 'problem', 'SubProblem']
17:34:46 Recommended 0 personas (selection: 6,371 tokens, $0.0071, 2.7s)
```

**Timeline (Test 2):**
| Phase | Duration | Cost | Status |
|-------|----------|------|--------|
| Session Create | 1.37s | - | OK |
| Decomposition LLM | 12.9s | $0.0099 | OK - 3 sub-problems |
| Complexity Assessment | 6.44s | $0.0062 | OK |
| Gap Analysis LLM | 13.0s | $0.0069 | OK - 6 CRITICAL questions |
| **Total to Clarification** | **~33s** | **$0.023** | OK |
| Submit 6 Answers | 8.76s | - | OK |
| **Resume from Checkpoint** | - | - | **BUG - sub_problems=0** |
| Persona Selection | 2.7s | $0.0071 | FAILED (0 personas) |

**Root Cause:** LangGraph's AsyncRedisSaver fails to properly serialize/deserialize Pydantic models with nested complex types. When `Problem` (containing `list[SubProblem]`) is restored from checkpoint, the `sub_problems` field defaults to empty `[]` because `default_factory=list` in the Pydantic model.

Additionally, `current_sub_problem` contains corrupted data - the SubProblem TYPE path `['bo1', 'models', 'problem', 'SubProblem']` instead of actual instance data.

**Fix Required:**

**Option A (Quick Fix):** Add validation in `control.py:load_state_from_checkpoint`:
```python
if checkpoint_state and checkpoint_state.values:
    state = dict(checkpoint_state.values)
    problem = state.get("problem")
    if problem:
        sub_problems = problem.get("sub_problems", []) if isinstance(problem, dict) else problem.sub_problems
        if not sub_problems:
            logger.warning("Checkpoint has empty sub_problems, reconstructing from PostgreSQL")
            return _reconstruct_state_from_postgres(session_id)
    return state
```

**Option B (Permanent Fix):** Add custom Pydantic serialization hooks in `bo1/graph/state.py`:
```python
def serialize_state(state: DeliberationGraphState) -> dict:
    result = dict(state)
    if "problem" in result and result["problem"]:
        if hasattr(result["problem"], "model_dump"):
            result["problem"] = result["problem"].model_dump()
    return result
```

**Option C:** Modify `analyze_dependencies_node` to set `current_sub_problem`:
```python
if not ENABLE_PARALLEL_SUBPROBLEMS or len(sub_problems) <= 1:
    return {
        "execution_batches": [[i] for i in range(len(sub_problems))],
        "parallel_mode": False,
        "current_sub_problem": sub_problems[0] if sub_problems else None,  # ADD THIS
        "current_node": "analyze_dependencies",
    }
```

**Estimated Fix Time:** 2-4 hours

---

## Original Test 1 Summary

The original test **failed** during the vote phase with a type error. Multiple additional issues were identified that degrade quality even when meetings don't crash. The most critical issues were:

1. **FATAL:** Problem object is a dict, not a Pydantic model (crashes vote_node) - **FIXED**
2. **CRITICAL:** Every contribution fails to save to database (KeyError) - **FIXED**
3. **HIGH:** Persona selection falls back to defaults due to JSON parsing errors - **FIXED**
4. **HIGH:** Research API rate limiting (Brave 429s) provides 0 sources

---

## Timeline & Timing Data

| Phase | Start Time | Duration | Cost | Notes |
|-------|-----------|----------|------|-------|
| Session Create | 16:56:51 | - | $0.002 | Prompt injection audit |
| Graph Start | 16:56:59 | - | - | |
| Decomposition | 16:56:59 | **21.2s** | $0.015 | 3 sub-problems created |
| Complexity Assessment | 16:57:21 | 6.1s | $0.006 | Score: 0.76, 6 rounds, 5 experts |
| Gap Analysis | 16:57:27 | 10.8s | $0.006 | 8 internal, 4 external gaps |
| **Clarification Pause** | 16:57:37 | - | - | 6 critical questions |
| Clarification Submit | 16:58:27 | - | $0.008 | 4 answers submitted |
| Resume | 16:58:41 | - | - | |
| Persona Selection | 16:58:42 | 4.5s | $0.008 | **FALLBACK** - JSON parse error |
| Initial Round | 16:58:46 | ~7s | $0.009 | 2 experts (should be 5) |
| Research (Tavily) | 16:59:00 | ~5s | $0.004 | 2 consolidated queries |
| Round 1-5 | 16:59:05 | ~4 min | ~$0.05 | Multiple rounds, rate limits |
| **CRASH** | 17:03:54 | - | - | vote_node failed |

**Total Duration:** ~7 minutes
**Total Cost:** ~$0.10

---

## Issues Found (Prioritized)

### P0: FATAL - Causes Crash

#### 1. Problem Object Type Mismatch
**Location:** `bo1/graph/nodes/synthesis.py:76`
**Error:** `'dict' object has no attribute 'description'`
**Root Cause:** `state['problem']` is a dict, but code expects `Problem` pydantic model
**Impact:** **CRASHES ALL MEETINGS** at vote phase
**Fix:**
```python
# In vote_node, ensure problem is properly typed:
if isinstance(state['problem'], dict):
    problem = Problem(**state['problem'])
else:
    problem = state['problem']
```

---

### P1: CRITICAL - Data Loss

#### 2. Contribution Database Save Failure
**Location:** `bo1/orchestration/persona_executor.py`
**Error:** `KeyError(0)` on every contribution save
**Impact:** All contributions lost from database (only kept in state)
**Frequency:** 100% of contributions (every round, every expert)
**Fix:** Debug the database save logic - likely `sub_problem_index` or `round_number` lookup issue

#### 3. User Context SQL Syntax Error
**Location:** `backend/api/control.py`
**Error:** `syntax error at or near ")": INSERT INTO user_context (user_id, )`
**Impact:** Clarification answers not persisted to user's business context
**Fix:** Fix SQL query construction for empty/null context fields

---

### P2: HIGH - Degraded Quality

#### 4. Persona Selection JSON Parsing Error
**Location:** `bo1/agents/selector.py`
**Error:** `Extra data: line 7 column 1 (char 663)`
**Impact:** Falls back to hardcoded defaults: `['product_strategist', 'finance_strategist', 'growth_hacker']`
**Result:** Wrong experts selected for problem domain
**Fix:** Review LLM response format, improve JSON parsing

#### 5. Missing Persona: `product_strategist`
**Location:** `bo1/data/personas.json`
**Error:** `Persona not found: product_strategist`
**Impact:** Only 2 of 3 fallback personas loaded (33% expert reduction)
**Fix:** Either add `product_strategist` to catalog OR change fallback defaults to existing personas

#### 6. Brave Search API Rate Limiting - **FIXED** (2025-12-06)
**Location:** `bo1/agents/researcher.py`, `bo1/agents/research_rate_limiter.py`
**Error:** `429 Too Many Requests` (5/6 queries failed)
**Impact:** Research returns 0 sources for most queries
**Fix Applied:**
- Updated `brave_free` rate limit to 1 req/sec (was incorrectly 10/min)
- Changed from parallel to sequential batch processing
- Added `_process_batch_with_retry()` with exponential backoff (1s, 2s, 4s)
- Don't cache rate-limited/failed results (prevents poisoning cache)

#### 7. Prompt Injection Audit JSON Parsing
**Location:** `bo1/security/prompt_injection.py`
**Error:** `Extra data: line 14 column 1 (char 520)`
**Impact:** Security check fails silently (continues without audit)
**Frequency:** Every clarification answer (4x in test)
**Fix:** Update expected response format or LLM prompt

---

### P3: MEDIUM - Poor UX

#### 8. Summary Generation Failures - **FIXED** (2025-12-06)
**Location:** `backend/api/event_collector.py`
**Error:** `Extra data: line 8 column 1 (char 1019)`
**Impact:** Some contributions missing concise summaries for UI
**Fix Applied:**
- Added `_extract_first_json_object()` with brace counting for multi-JSON responses
- Added `_validate_summary_schema()` to fill defaults for missing fields
- Added `_create_fallback_summary()` for graceful degradation (uses first sentence)

#### 9. Session Status Inconsistency - **FIXED** (2025-12-06)
**Symptom:** `status: "completed"` but `phase: "clarification_needed"`
**Impact:** Confusing UI state during clarification flow
**Fix Applied:**
- Added phase validation in `_update_session_status_with_retry()`
- Checks both `stop_reason` and database `phase` before setting "completed"
- Prevents race conditions between clarification flow and completion

#### 10. Only 2 Experts Instead of 5 Recommended
**Root Cause:** Combination of issues #4 + #5
**Impact:** Less diverse perspectives, lower quality deliberation
**Fix:** Fix upstream issues

---

## Research Query Analysis

### Good Patterns
- Comparison detection worked: timing comparison with 2 options
- Proactive research triggered at right times
- Tavily queries succeeded when consolidation worked

### Issues
- **Query consolidation insufficient:** 3 → 2 batches (33% reduction) not enough
- **Brave rate limit:** 1 req/second limit with 6+ concurrent requests = 5 failures
- **Caching empty results:** Rate-limited queries (0 sources) cached as successful

### Recommendations
1. Serialize Brave requests with 1.1s delay between calls
2. Don't cache failed/empty research results
3. Prefer Tavily for deep research (higher limits)
4. Implement query deduplication before dispatch

---

## Clarification Question Quality

The 6 critical questions were **appropriate**:
1. Current key metrics (MRR, churn, CAC, LTV) - Essential
2. Weakest metrics vs investor expectations - Relevant
3. Cash runway and burn rate - Critical for timing decision
4. Planned initiatives and confidence - Good for risk assessment

**Issue:** Only 4 of 6 questions answered (API allowed partial submission)
**Recommendation:** Consider requiring all CRITICAL questions answered before resume

---

## Sub-Problem Decomposition Quality

3 sub-problems created (appropriate for problem):
1. Investor appetite + metrics improvement impact on terms
2. Realistic 6-month improvement + execution risk
3. Go/no-go recommendation

**Issues:**
- Dependencies correct (sp_003 depends on sp_001, sp_002)
- But only 1 sub-problem deliberated (others may not have run)

---

## Recommended Fix Priority

### Completed (All P0, P1, P2, and P3 fixes)
- ~~**Fix sub-problem checkpoint serialization**~~ - **FIXED** (2025-12-06)
  - Added `serialize_state_for_checkpoint()` and `deserialize_state_from_checkpoint()` in `bo1/graph/state.py`
  - Added validation with PostgreSQL fallback in `backend/api/control.py`
  - Set `current_sub_problem` in sequential mode in `bo1/graph/nodes/subproblems.py`
- ~~Fix Problem type mismatch~~ - **FIXED** via `_get_problem_attr()` helper
- ~~Fix contribution save KeyError~~ - **FIXED** via `result["user_id"]` access
- ~~Fix user context SQL~~ - **FIXED** via empty valid_fields handling
- ~~Add missing persona or fix fallback~~ - **FIXED** changed to `product_manager`
- ~~Fix JSON parsing~~ - **FIXED** via `parse_json_with_fallback()`
- ~~**Fix Brave rate limiting**~~ - **FIXED** (2025-12-06)
  - Updated `brave_free` config to 1 req/sec (was incorrectly 10/min)
  - Changed from parallel to sequential batch processing
  - Added `_process_batch_with_retry()` with exponential backoff
  - Don't cache rate-limited/failed results
- ~~Improve session status tracking consistency~~ - **FIXED** (2025-12-06)
  - Added phase validation in `_update_session_status_with_retry()`
  - Checks both `stop_reason` and database `phase` before setting "completed"
  - Prevents race conditions between clarification flow and completion
- ~~Fix summary generation JSON parsing~~ - **FIXED** (2025-12-06)
  - Added `_extract_first_json_object()` with brace counting for multi-JSON responses
  - Added `_validate_summary_schema()` to fill defaults for missing fields
  - Added `_create_fallback_summary()` for graceful degradation

### All Issues Resolved ✅
No remaining P0-P3 issues from the original test report.

---

## Test Reproducibility

To reproduce this test:
```bash
# Create session
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"problem_statement": "Should we raise a Series A round now or wait 6 months to improve metrics?", "problem_context": {"company_name": "TechStartup Inc", "business_model": "B2B SaaS", "monthly_revenue": "$45,000 MRR"}}'

# Start session
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/start

# Submit clarifications when paused
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/clarifications \
  -H "Content-Type: application/json" \
  -d '{"answers": {...}}'

# Resume
curl -X POST http://localhost:8000/api/v1/sessions/{session_id}/resume
```

---

## Files to Investigate

| File | Issue |
|------|-------|
| `bo1/graph/nodes/synthesis.py:76` | Problem type mismatch |
| `bo1/orchestration/persona_executor.py` | KeyError(0) contribution save |
| `bo1/agents/selector.py` | JSON parsing fallback |
| `bo1/data/personas.json` | Missing product_strategist |
| `bo1/agents/researcher.py` | Rate limiting handling |
| `bo1/security/prompt_injection.py` | JSON parsing |
| `backend/api/control.py` | SQL syntax error |
| `backend/api/event_collector.py` | Summary generation |

---

## Conclusion

### Status After All Fixes (2025-12-06)

**ALL P0, P1, P2, and P3 issues have been FIXED.** The meeting system should now work correctly with:
- Clarification flow (checkpoint serialization)
- Rate-limited research APIs (sequential + backoff)
- Consistent session status/phase states
- Robust contribution summary parsing

#### P0-CRITICAL Checkpoint Fix Details

Three-layer fix implemented:
1. **Custom Serialization** (`bo1/graph/state.py`): Added `serialize_state_for_checkpoint()` and `deserialize_state_from_checkpoint()` to properly convert Pydantic models to/from dicts
2. **Validation with Fallback** (`backend/api/control.py`): Added check for empty sub_problems with PostgreSQL reconstruction fallback
3. **Sequential Mode Fix** (`bo1/graph/nodes/subproblems.py`): Set `current_sub_problem` when in sequential mode

**Root Cause (resolved):** LangGraph's AsyncRedisSaver checkpoint serialization failed to properly handle nested Pydantic models. Custom serialization ensures all models are converted to dicts before storage.

### Positive Observations (Test 2)

1. **Decomposition Quality**: 3 well-structured sub-problems with appropriate dependencies
2. **Clarification Questions**: 6 CRITICAL questions, all highly relevant to the decision
3. **Comparison Detection**: Correctly identified "timing" comparison
4. **Performance**: Initial phase completes in ~33s with good cost efficiency ($0.023)
5. **PostgreSQL Reconstruction**: Fallback code exists and appears correct

### Files to Modify for P0 Fix

1. `backend/api/control.py` - Add sub_problem verification in `load_state_from_checkpoint`
2. `bo1/graph/nodes/subproblems.py` - Set `current_sub_problem` in sequential mode
3. `bo1/graph/state.py` - Add custom serialization/deserialization (Option B)
