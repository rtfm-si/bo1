# Plan: Enable Resume from Last Successful Sub-Problem Checkpoint

## Summary

- Add checkpoint recovery that skips already-completed sub-problems
- Persist expert memory (summaries) between sub-problems for sequential flow
- Add `/sessions/{id}/resume` endpoint with sub-problem state visibility
- Frontend recovery UI showing resumable sub-problem index

## Implementation Steps

### Step 1: Extend Session Model for Checkpoint Metadata

**File:** `backend/api/models.py`

- Add `last_completed_sp_index: int | None` to Session model
- Add `sp_checkpoint_at: datetime | None` timestamp
- Update `sessions.py` to persist these on SP completion

### Step 2: Save SP Boundary Checkpoints

**File:** `bo1/graph/nodes/synthesis.py` (`next_subproblem_node`)

- After saving result to `sub_problem_results`, emit checkpoint marker event
- Call session update with `last_completed_sp_index = sub_problem_index`
- Persist `expert_summaries` from current SP to state for next SP

### Step 3: Add Expert Memory Propagation (Sequential Mode)

**File:** `bo1/graph/nodes/subproblems.py`

- In `analyze_dependencies_node`, check for `expert_summaries` from prior SP
- Pass summaries to `select_personas` node via state
- Ensure `SummarizerAgent` outputs are stored in checkpoint

### Step 4: Add Resume Router Logic

**File:** `bo1/graph/routers.py`

- Add `route_on_resume()` function
- If `sub_problem_results` length > 0 AND `current_sub_problem` is None:
  - Restore `current_sub_problem` from `problem.sub_problems[sub_problem_index]`
  - Route to `select_personas` (skip decomposition/dependency analysis)

### Step 5: Add Resume Endpoint

**File:** `backend/api/sessions.py`

- Add `GET /sessions/{session_id}/checkpoint-state` returning:
  - `completed_sub_problems: int`
  - `total_sub_problems: int`
  - `last_checkpoint_at: datetime`
  - `can_resume: bool`
- Add `POST /sessions/{session_id}/resume` that:
  - Loads checkpoint from Redis
  - Verifies SP boundary checkpoint exists
  - Triggers graph with resume entry point

### Step 6: Frontend Recovery UI

**File:** `frontend/src/lib/components/meeting/`

- Add `SessionRecoveryBanner.svelte` component
- Show when session has incomplete SPs with valid checkpoint
- Display: "Resume from sub-problem N of M?" with Resume/Start Over buttons
- Integrate into meeting view on reconnect

## Tests

### Unit Tests
- `tests/graph/test_sp_checkpoint_resume.py`:
  - Test checkpoint save at SP boundary
  - Test resume skips completed SPs
  - Test expert memory propagation
  - Test duplicate SP result guard

### Integration Tests
- `tests/api/test_session_resume.py`:
  - Test `/checkpoint-state` returns correct counts
  - Test `/resume` loads correct checkpoint
  - Test resume triggers graph at correct entry point

### Manual Validation
- Start multi-SP session → complete SP 1 → kill process → resume → verify SP 2 starts
- Verify expert memory from SP 1 available in SP 2 (sequential mode)

## Dependencies & Risks

### Dependencies
- Existing checkpoint infrastructure (Redis + LangGraph)
- `serialize_state_for_checkpoint()` already handles sub_problem_results
- `next_subproblem_node` already tracks completion

### Risks/Edge Cases
- Corrupted checkpoint → fallback to fresh start (existing repair logic helps)
- Parallel mode may have different resume semantics (batch boundaries)
- Expert summary size growth with many SPs (consider pruning old summaries)
