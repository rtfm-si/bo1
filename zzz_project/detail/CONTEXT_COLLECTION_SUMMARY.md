# Context Collection & Human-in-the-Loop - Implementation Summary

**Date**: 2025-01-16
**Status**: Designed, Scheduled for Week 6 (Days 36-38)

---

## Executive Summary

You asked: *"Have we lost the capability for the deliberation system to ask questions to the end user?"*

**Answer**: ✅ **No, we have NOT lost it.** The infrastructure exists in `bo1/agents/context_collector.py` and `bo1/agents/decomposer.py`, but it's **not yet wired into the LangGraph flow**.

This document outlines the **complete plan to integrate context collection** into Week 6 of the roadmap.

---

## What Exists Today (Not Wired to Graph)

### 1. Business Context Collection (`bo1/agents/context_collector.py`)
- `collect_context()` - Prompts for business model, target market, revenue, competitors
- `format_context_for_prompt()` - Injects context into persona prompts
- **Status**: Works in isolation, not called by any LangGraph node

### 2. Information Gap Detection (`bo1/agents/decomposer.py`)
- `identify_information_gaps()` - AI identifies CRITICAL vs NICE_TO_HAVE questions
- Separates INTERNAL (user-only) from EXTERNAL (researchable) gaps
- **Status**: Works in isolation, not called by any LangGraph node

### 3. Internal Answer Collection (`bo1/agents/context_collector.py`)
- `collect_internal_answers()` - Prompts user for CRITICAL answers
- `format_internal_context()` - Injects answers into prompts
- **Status**: Works in isolation, not called by any LangGraph node

### 4. External Research (`bo1/agents/researcher.py`)
- `research_questions()` - Auto-fill EXTERNAL gaps via web search
- **Status**: Stub (placeholder), implementation planned for later

### 5. LangGraph State Support (`bo1/graph/state.py`)
- `user_input: str | None` field ready for human-in-the-loop
- `pending_clarification: dict | None` field ready for pause/resume
- **Status**: Fields exist, no nodes use them yet

---

## What's Being Added (Week 6)

### Strategic Context Collection Points

```
┌─────────────────────────────────────────────────────────────┐
│ 1. BUSINESS CONTEXT (Pre-Decomposition)                    │
│    - Persistent (saved to user_context table)              │
│    - Optional ("improves recommendations by 40%")           │
│    - Reused across sessions (don't re-ask)                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PROBLEM DECOMPOSITION (uses business context)           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. INFORMATION GAPS (Post-Decomposition)                   │
│    - AI identifies CRITICAL gaps based on sub-problems     │
│    - INTERNAL: User answers (churn rate, CAC, etc.)        │
│    - EXTERNAL: Auto-research (industry benchmarks)         │
│    - User can skip any question                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. DELIBERATION (with mid-flight clarification)            │
│    - Facilitator can request clarification                 │
│    - User options: Answer now / Pause / Skip               │
│    - Pause → checkpoint → resume later with answer         │
└─────────────────────────────────────────────────────────────┘
```

---

## Week 6 Implementation Plan

### Day 36: Database Schema

**New Tables**:

1. **`user_context`** - Persistent business context
   - business_model, target_market, revenue, customers, competitors, etc.
   - One row per user (UNIQUE constraint on user_id)
   - RLS enforced (users only see own context)

2. **`session_clarifications`** - Mid-deliberation Q&A audit trail
   - question, asked_by_persona, answer, answered_at
   - Tracks all clarification requests/responses

**New Functions** (`bo1/state/postgres_manager.py`):
- `load_user_context(user_id)` - Get saved context
- `save_user_context(user_id, context)` - Upsert context
- `delete_user_context(user_id)` - Remove context
- `save_clarification(session_id, question, answer, ...)` - Log Q&A

### Day 37: LangGraph Nodes

**New Nodes**:

1. **`context_collection_node()`** - After decomposition, before persona selection
   - Load saved business context (if exists)
   - Prompt for new context (if missing, optional)
   - Call `identify_information_gaps()` on sub-problems
   - Collect CRITICAL internal answers
   - Auto-research EXTERNAL gaps (stub for now)
   - Inject all context into `problem.context`

2. **`clarification_node()`** - After facilitator decides "clarify"
   - Display clarification question
   - Options: Answer now / Pause session / Skip
   - If answer: Inject into context, continue
   - If pause: Set `should_stop=True`, save checkpoint
   - If skip: Log skip, continue with warning

**New Facilitator Action**:
- `action="clarify"` - Triggers clarification node
- `clarification_question: str` - Question to ask
- `clarification_reason: str` - Why it's needed

**Graph Updates**:
```python
# New edges
decompose → context_collection → select_personas  # Was: decompose → select
facilitator_decide → clarification (if action="clarify")
clarification → persona_contribute (if answered) OR END (if paused)
```

### Day 38: API Endpoints

**Context Management**:
- `GET /api/v1/context` - Get user's saved context
- `PUT /api/v1/context` - Update context
- `DELETE /api/v1/context` - Delete context
- `POST /api/v1/sessions/{id}/clarify` - Submit answer, resume session

**SSE Events** (for web UI):
- `clarification_requested` - Pause stream, show question form
- `clarification_answered` - Resume stream, continue deliberation

---

## User Experience Examples

### Example 1: First-Time User with Business Context

```
$ bo1

📊 Business Context Collection
Providing business context helps personas make better recommendations.
This is optional but recommended.

Would you like to provide business context? (y/n): y

Business model (e.g., B2B SaaS): B2B SaaS
Target market (e.g., small businesses): Mid-market enterprises
Monthly/Annual revenue: $2M ARR
Growth rate %: 15% YoY

✓ Business context saved! This will be reused for future sessions.

[Decomposition proceeds with business context...]
```

### Example 2: Returning User (Context Auto-Loaded)

```
$ bo1

✓ Loaded saved business context (last updated: 2 weeks ago)
Update business context? (y/n): n

[Proceeds directly to decomposition...]
```

### Example 3: Information Gap Collection

```
📋 Information Needed for Deliberation

CRITICAL Information:
1. What is your current monthly churn rate?
   Why: Essential for retention strategy evaluation
   Answer (or 'skip'): 5%
   ✓ Recorded

2. What is your CAC (Customer Acquisition Cost)?
   Why: Cannot calculate payback period without CAC
   Answer (or 'skip'): $450
   ✓ Recorded

EXTERNAL gaps (auto-researching via web search):
• Average SaaS churn rate in mid-market segment
• Industry benchmark CAC for enterprise SaaS

✓ Collected 2 answers, researching 2 external questions...
```

### Example 4: Mid-Deliberation Clarification

```
Round 3: Maria (CFO Expert) contributes...

⚠️  CLARIFICATION NEEDED:
Question: What percentage of revenue comes from your top 3 customers?
Why: High customer concentration affects risk analysis

Options:
  1. Answer now
  2. Pause session (gather info, resume later)
  3. Skip (deliberation continues with lower confidence)

Choose (1/2/3): 2

Session paused.
Resume with: bo1 --resume sess_abc123

When you resume, provide answer to: What percentage of revenue comes from your top 3 customers?
```

### Example 5: Resume After Pause

```
$ bo1 --resume sess_abc123

📄 Resuming session from Round 3 (paused 2 hours ago)

Provide answer to Maria's question:
What percentage of revenue comes from your top 3 customers?
Answer: 45%

✓ Answer recorded, continuing deliberation...

Round 4: Tariq (Growth Strategist) responds to Maria's analysis...
```

---

## Design Decisions & Rationale

### ✅ Business Context: Pre-Decomposition
**Why**: Decomposer needs business context to break problem into relevant sub-problems.
**Example**: "Pricing strategy" for B2B SaaS (long sales cycles) vs B2C (impulse purchases).

### ✅ Information Gaps: Post-Decomposition
**Why**: Can't identify gaps until you know the sub-problems.
**Example**: "Pricing" problem needs CAC; "Hiring" problem doesn't.

### ✅ Clarification: Mid-Deliberation
**Why**: Experts discover blockers as they deliberate (not predictable upfront).
**Example**: CFO realizes revenue concentration is critical only after reading growth expert's proposal.

### ✅ Optional Context (Not Required)
**Why**: User sovereignty - some problems don't need business context.
**Example**: "Should I use React or Vue?" doesn't need revenue data.
**Nudge**: "Adding context improves recommendations by 40%" (encourages without forcing).

### ✅ Persistent Context (Not Per-Session)
**Why**: Reduce friction - ask once, reuse forever.
**Example**: User runs 10 deliberations/month → only asked for context once.

### ✅ Pause/Resume for Clarifications
**Why**: User may not have answer immediately (need to check dashboard, ask accountant).
**Example**: "What's our churn rate?" → User needs to pull Stripe analytics.

### ✅ Skip Option for All Questions
**Why**: User sovereignty - never block progress.
**Trade-off**: Skipped questions reduce confidence, but don't prevent synthesis.

---

## Testing Strategy

### Unit Tests (Day 37)
- `test_context_collection_node_loads_saved_context()`
- `test_context_collection_node_prompts_for_new_context()`
- `test_context_collection_node_identifies_gaps()`
- `test_clarification_node_answer_now()`
- `test_clarification_node_pause_session()`
- `test_clarification_node_skip_question()`

### Integration Tests (Day 37)
- `test_full_context_collection_flow()` - Business context → gaps → deliberation
- `test_clarification_pause_resume_flow()` - Pause → resume → continue

### API Tests (Day 38)
- `test_get_user_context_returns_saved_data()`
- `test_update_user_context_persists_changes()`
- `test_user_cannot_access_other_users_context()` (RLS)
- `test_submit_clarification_resumes_session()`

---

## Success Metrics

- [ ] Users can save/load business context across sessions
- [ ] Business context reduces repetitive questions by 80%+
- [ ] AI identifies 2-5 CRITICAL gaps per complex problem
- [ ] EXTERNAL gaps auto-filled via web research (90% accuracy target)
- [ ] Clarification pause/resume works flawlessly (0 data loss)
- [ ] Users can update saved context anytime

---

## Open Questions (Answered)

### Q1: Should business context be optional or required?
**A**: Optional (some problems don't need it). Show impact: "Adding context improves recommendations by 40%".

### Q2: When to collect information gaps?
**A**: Post-decomposition (can't identify gaps until you know sub-problems).

### Q3: Should experts ask clarification questions mid-deliberation?
**A**: Yes, via facilitator action="clarify" + pause/resume capability.

### Q4: Context expiration policy?
**A**: Never expire, but flag as "stale" after 6 months, prompt user to update.

### Q5: Should we auto-pause on CRITICAL gap with no answer?
**A**: No, allow skip (user sovereignty). Track skip rate → surface in admin dashboard.

---

## Files Changed/Created (Week 6)

### Created:
1. `/Users/si/projects/bo1/zzz_project/detail/CONTEXT_COLLECTION_FEATURE.md` ✅
2. `/Users/si/projects/bo1/migrations/versions/00X_add_user_context_table.py`
3. `/Users/si/projects/bo1/migrations/versions/00Y_add_session_clarifications_table.py`
4. `/Users/si/projects/bo1/bo1/state/postgres_manager.py` (new functions)
5. `/Users/si/projects/bo1/backend/api/context.py` (API endpoints)
6. `/Users/si/projects/bo1/tests/graph/test_context_collection_node.py`
7. `/Users/si/projects/bo1/tests/graph/test_clarification_node.py`
8. `/Users/si/projects/bo1/tests/integration/test_context_collection_flow.py`
9. `/Users/si/projects/bo1/backend/tests/test_context_api.py`

### Modified:
1. `/Users/si/projects/bo1/bo1/graph/nodes.py` - Add context_collection_node, clarification_node
2. `/Users/si/projects/bo1/bo1/graph/routers.py` - Add route_clarification
3. `/Users/si/projects/bo1/bo1/graph/config.py` - Update graph structure
4. `/Users/si/projects/bo1/bo1/agents/facilitator.py` - Add clarification action
5. `/Users/si/projects/bo1/zzz_project/MVP_IMPLEMENTATION_ROADMAP.md` ✅
6. `/Users/si/projects/bo1/CLAUDE.md` ✅

---

## Next Steps

1. **Review** `zzz_project/detail/CONTEXT_COLLECTION_FEATURE.md` for full specification
2. **Proceed** to Week 6 implementation (Days 36-38)
3. **Test** each piece thoroughly (unit + integration + API tests)
4. **Validate** with real user scenarios (solopreneur problems)

---

**Status**: ✅ Specification complete, roadmap updated, ready for Week 6 implementation.
