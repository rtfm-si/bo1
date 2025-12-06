# Context Sufficiency Implementation Plan (Option D+E Hybrid)

## Executive Summary

This plan implements a "Context Sufficiency" feature that:
1. Detects when user answers to clarification questions are incomplete, flagging `limited_context_mode`
2. Monitors contributions for meta-discussion (>50% in rounds 1-2 = context insufficient)
3. Emits `context_insufficient` SSE event with 3 user choices
4. Injects "best effort" prompts to force engagement when user continues or times out
5. Prevents research loops (2+ consecutive without improvement = force continue)
6. Ensures synthesis includes "Assumptions & Limitations" section in limited_context_mode

## Architecture Overview

```
    User submits problem
           │
           ▼
    [decompose_node] ──► [identify_gaps_node] ──► clarification_required event
           │                     │
           │              user answers (partial?)
           │                     │
           ▼                     ▼
    limited_context_mode = true if partial answers
           │
           ▼
    [initial_round_node] ──► [parallel_round_node]
           │                     │
           ▼                     ▼
    [meta_discussion_detector] (after round 1-2)
           │
           │ >50% meta-discussion?
           ▼
    emit context_insufficient event ──► 3 choices
           │
    [user choice: continue | provide more | end]
           │
           ▼
    inject best_effort_prompt ──► [continue rounds]
           │
           ▼
    [facilitator_decide] ──► research_loop_guard
           │
           ▼
    [synthesis_node] ──► include "Assumptions & Limitations"
```

## Implementation Phases

### Phase 1: State Schema Updates
- Add `limited_context_mode`, `context_insufficient_emitted`, `user_context_choice`,
  `best_effort_prompt_injected`, `consecutive_research_without_improvement`,
  `meta_discussion_count`, `total_contributions_count` to state

### Phase 2: Partial Answer Detection
- Modify `identify_gaps_node` to detect incomplete/short answers
- Set `limited_context_mode = True` when answers are partial

### Phase 3: Meta-Discussion Detection
- Add `INSUFFICIENT_CONTEXT_PATTERNS` to ResponseParser
- Add `is_context_insufficient_discussion()` method
- Count meta-discussion in `parallel_round_node`

### Phase 4: Context Insufficient Event
- Add `check_context_insufficiency()` to loop_prevention
- Create `context_insufficient` SSE event
- Extract expert questions from meta-discussion

### Phase 5: User Choice Handling
- Add `/context-choice` endpoint to control.py
- Handle "provide_more", "continue", "end" choices

### Phase 6: Best Effort Prompt Injection
- Add `BEST_EFFORT_PROMPT` template
- Inject into persona execution when in limited context mode

### Phase 7: Research Loop Prevention
- Add `_check_research_loop()` to FacilitatorAgent
- Track `consecutive_research_without_improvement`

### Phase 8: Synthesis with Assumptions
- Add `_generate_assumptions_section()` for limited context synthesis
- Include "Assumptions & Limitations" section

### Phase 9: Frontend Changes
- Create `ContextInsufficientModal.svelte`
- Handle `context_insufficient` event in meeting page

### Phase 10: Timeout Handling
- Auto-continue after 2 minutes if no response

## Files to Modify

| File | Changes |
|------|---------|
| `bo1/graph/state.py` | Add new state fields |
| `bo1/graph/nodes/context.py` | Partial answer detection |
| `bo1/llm/response_parser.py` | Context insufficiency patterns |
| `bo1/graph/nodes/rounds.py` | Meta-discussion counting |
| `bo1/graph/safety/loop_prevention.py` | Context insufficiency check |
| `backend/api/events.py` | New SSE event |
| `backend/api/control.py` | Context choice endpoint |
| `bo1/prompts/reusable_prompts.py` | Best effort prompt |
| `bo1/orchestration/persona_executor.py` | Prompt injection |
| `bo1/agents/facilitator.py` | Research loop guard |
| `bo1/graph/nodes/synthesis.py` | Assumptions section |
| Frontend components | Modal and event handling |

## Estimated Time: 7-8 hours
