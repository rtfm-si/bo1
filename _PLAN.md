# Plan: [ARCH][P3] Migrate Nodes to Nested State Accessors

## Summary

- Update `_TASK.md` to mark 4 already-completed P3 tasks as done
- Migrate graph nodes to use `get_problem_state()`, `get_phase_state()` helpers
- Start with highest-impact node: `rounds.py` (already partially migrated)
- Add test coverage for accessor usage patterns

## Implementation Steps

1. **Mark completed tasks in `_TASK.md`** (lines 120-122, 134)
   - `[LLM][P3]` sanitization tests - exists in `tests/test_sanitizer.py` (734 lines)
   - `[OBS][P3]` event type metric - exists as `bo1_event_type_published_total`
   - `[API][P3]` has_more pagination - exists in `backend/api/utils/pagination.py`
   - `[REL][P3]` statement_timeout - exists in `bo1/state/database.py`

2. **Audit current accessor usage**
   - `rounds.py` - already uses `get_problem_state()`, `get_phase_state()`
   - Identify nodes still using raw `state["field"]` access

3. **Migrate `synthesis.py`** (~5 raw accesses)
   - Replace `state.get("problem")` → `get_problem_state(state).get("problem")`
   - Replace `state.get("phase")` → `get_phase_state(state).get("phase")`

4. **Migrate `decomposition.py`** (~3 raw accesses)
   - Same pattern as synthesis

5. **Migrate `context.py`** (~4 raw accesses)
   - Use new `get_context_state()` accessor if needed

6. **Update test file** `tests/graph/test_state_refactor.py`
   - Add tests verifying accessor return types
   - Test default values when fields missing

## Tests

- Unit tests:
  - `tests/graph/test_state_refactor.py` - accessor coverage
- Integration tests:
  - Existing node tests should pass unchanged
- Manual validation:
  - `make test` passes
  - No regressions in deliberation flow

## Dependencies & Risks

- Dependencies:
  - Existing accessors in `bo1/graph/state.py:755-790`

- Risks:
  - Low: accessor pattern already proven in `rounds.py`
  - Type annotations may need adjustment for TypedDict access
