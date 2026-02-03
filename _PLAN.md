# Plan: Cache Sub-Problem Context Across Personas

## Summary

- Cache dependency context string per sub-problem (avoid rebuilding for each persona)
- Cache extracted recommendations from synthesis (avoid repeated XML parsing)
- Store partial context formatting in PartialContextProvider (avoid string rebuilds)
- Estimated savings: $0.10-0.30/session from reduced redundant computation + better Anthropic prompt cache hits

## Implementation Steps

- Step 1: Add `_cached_dependency_context: str | None` field to `SubProblemGraphState` in `bo1/graph/deliberation/subgraph/state.py`
  - Initialize as `None` in `create_subproblem_graph_state()`

- Step 2: Update `parallel_round_sp_node()` in `bo1/graph/deliberation/subgraph/nodes.py`:
  - Before persona loop (line ~218), check if `state.cached_dependency_context` is None
  - If None and has dependencies: call `build_dependency_context()` once, store in `state.cached_dependency_context`
  - In persona loop, reuse cached value instead of rebuilding per-persona

- Step 3: Cache extracted recommendations in `SubProblemResult`:
  - Add `extracted_recommendation: str | None` field to `SubProblemResult` in `bo1/graph/deliberation/subgraph/state.py`
  - In `synthesize_sp_node()`, after calling `extract_recommendation_from_synthesis()`, store result in `SubProblemResult.extracted_recommendation`
  - Update `build_dependency_context()` to check for pre-extracted recommendation before parsing

- Step 4: Cache formatted partial context in `PartialContextProvider`:
  - Add `_cached_formatted: str | None` field to `SubProblemProgress` dataclass in `bo1/graph/deliberation/partial_context.py`
  - In `_format_partial_context()`, check cache before rebuilding
  - Invalidate cache in `update_round_context()` when progress changes

- Step 5: Add cache hit metrics to deliberation flow:
  - Add counter in `parallel_round_sp_node()` for dependency context cache hits
  - Log cache stats at sub-problem completion

## Tests

- Unit tests:
  - `tests/graph/deliberation/test_context_caching.py`:
    - Test dependency context cached and reused across personas
    - Test extracted recommendation stored in SubProblemResult
    - Test partial context cache invalidation on update
- Integration/flow tests:
  - Run existing deliberation tests: `pytest tests/graph/ -k deliberation -v`
  - Verify no regression in synthesis output
- Manual validation:
  - `make test` passes
  - Run local deliberation, check logs for cache hit metrics

## Dependencies & Risks

- Dependencies:
  - None - pure optimization on existing data structures
- Risks/edge cases:
  - Cache invalidation: ensure `update_round_context()` clears partial context cache
  - Thread safety: PartialContextProvider already uses asyncio.Lock, extend to cache
  - State serialization: new fields must be checkpoint-compatible (use Optional with default None)
