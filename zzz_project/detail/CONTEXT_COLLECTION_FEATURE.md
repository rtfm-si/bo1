# Business Context & Information Gap Collection - Feature Specification

**Status**: Planned for Week 6
**Dependencies**: Database schema (Day 21), LangGraph migration (Days 22-31)

---

## Executive Summary

Add human-in-the-loop context collection at 3 strategic points:
1. **Business Context** (pre-decomposition, persistent, optional) - "Tell us about your business"
2. **Information Gaps** (post-decomposition, problem-specific, CRITICAL only) - "We need to know X to proceed"
3. **Expert Clarification** (during deliberation, blocking questions) - "Pause → gather info → resume"

---

## User Experience Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ START SESSION                                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. BUSINESS CONTEXT (Optional, Persistent)                      │
│                                                                  │
│  "📊 Business Context Collection"                               │
│  "Providing business context helps personas make better          │
│   recommendations. This is optional but recommended."            │
│                                                                  │
│  Would you like to:                                              │
│  • Load saved context (last updated: 2 weeks ago)               │
│  • Update saved context                                          │
│  • Skip (proceed without context)                               │
│                                                                  │
│  Fields: business_model, target_market, revenue, growth_rate,   │
│          competitors, website                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. PROBLEM DECOMPOSITION (uses business context if provided)    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. INFORMATION GAP IDENTIFICATION (AI identifies CRITICAL gaps) │
│                                                                  │
│  "📋 Information Needed for Deliberation"                       │
│  "The following information would help personas provide better   │
│   recommendations."                                              │
│                                                                  │
│  CRITICAL Information:                                           │
│  1. What is your current monthly churn rate?                     │
│     Why: Essential for retention strategy evaluation            │
│     Answer (or 'skip'): _____                                    │
│                                                                  │
│  2. How many employees do you have?                              │
│     Why: Affects implementation feasibility                      │
│     Answer (or 'skip'): _____                                    │
│                                                                  │
│  EXTERNAL gaps (auto-researched via web search):                │
│  • Average SaaS churn rate in your industry                     │
│  • Competitor pricing strategies                                │
│                                                                  │
│  ✓ Collected 2 answers, researching 2 external questions...     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. PERSONA SELECTION + INITIAL ROUND                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. DELIBERATION LOOP (with mid-flight clarification)            │
│                                                                  │
│  Round 3: Maria (CFO Expert) contributes...                     │
│  "I need critical information to proceed with ROI analysis."    │
│                                                                  │
│  ⚠️  CLARIFICATION NEEDED:                                       │
│  Question: What is your current CAC (Customer Acquisition Cost)?│
│  Why: Cannot calculate payback period without CAC               │
│                                                                  │
│  Options:                                                        │
│  • Answer now: _____                                             │
│  • Pause session (gather info, resume later)                    │
│  • Skip (deliberation continues with lower confidence)          │
│                                                                  │
│  [User chooses "Pause"]                                          │
│  ✓ Session paused. Resume with: bo1 --resume sess_abc123       │
│                                                                  │
│  [Later: User runs --resume sess_abc123]                        │
│  📄 Resuming session from Round 3 (paused 2 hours ago)          │
│  Provide answer to Maria's question:                             │
│  CAC: $450                                                       │
│  ✓ Continuing deliberation...                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. VOTE + SYNTHESIS                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Changes

### New Table: `user_context`

```sql
CREATE TABLE user_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Business Info (from BusinessContextCollector)
    business_model TEXT,
    target_market TEXT,
    product_description TEXT,
    revenue TEXT,
    customers TEXT,
    growth_rate TEXT,
    competitors TEXT,
    website TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT user_context_unique_user UNIQUE (user_id)
);

CREATE INDEX idx_user_context_user_id ON user_context(user_id);

-- RLS Policy
ALTER TABLE user_context ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_context_policy ON user_context
    FOR ALL USING (auth.uid() = user_id);
```

### New Table: `session_clarifications`

Track mid-deliberation clarification questions:

```sql
CREATE TABLE session_clarifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,

    -- Question details
    question TEXT NOT NULL,
    asked_by_persona TEXT,  -- Persona code who asked
    priority TEXT CHECK (priority IN ('CRITICAL', 'NICE_TO_HAVE')),
    reason TEXT,

    -- Answer
    answer TEXT,
    answered_at TIMESTAMP,

    -- Timing
    asked_at_round INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clarifications_session ON session_clarifications(session_id);
```

---

## LangGraph Node Changes

### New Node: `context_collection_node()`

**Position**: After `decompose_node`, before `select_personas_node`

```python
# bo1/graph/nodes.py

async def context_collection_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Collect business context and identify/fill information gaps.

    Flow:
    1. Load or collect business context (persistent, optional)
    2. Identify information gaps based on sub-problems
    3. Collect CRITICAL internal answers (user prompts)
    4. Auto-research EXTERNAL gaps (web search)
    5. Inject all context into problem.context
    """
    from bo1.agents.context_collector import BusinessContextCollector
    from bo1.agents.decomposer import DecomposerAgent
    from bo1.agents.researcher import ResearcherAgent
    from bo1.state.postgres_manager import load_user_context, save_user_context

    console = Console()
    user_id = state.get("user_id")  # From auth (Week 7+), None for console

    # === 1. Business Context (Persistent) ===
    business_context = None

    if user_id:
        # Try loading saved context
        business_context = await load_user_context(user_id)

        if business_context:
            console.print("[green]✓ Loaded saved business context[/green]")
            console.print(f"  Last updated: {business_context['updated_at']}")

            # Ask if user wants to update
            update = console.input("Update business context? (y/n): ").strip().lower()
            if update == "y":
                collector = BusinessContextCollector(console)
                business_context = collector.collect_context()
                await save_user_context(user_id, business_context)
        else:
            # No saved context, offer to collect
            collector = BusinessContextCollector(console)
            business_context = collector.collect_context(skip_prompt=False)
            if business_context:
                await save_user_context(user_id, business_context)
    else:
        # Console mode (no user_id) - collect per-session
        collector = BusinessContextCollector(console)
        business_context = collector.collect_context(skip_prompt=False)

    # === 2. Identify Information Gaps (based on sub-problems) ===
    decomposer = DecomposerAgent()
    sub_problems = [sp.model_dump() for sp in state.get("problem").sub_problems or []]

    gap_response = await decomposer.identify_information_gaps(
        problem_description=state["problem"].description,
        sub_problems=sub_problems,
        business_context=business_context,
    )

    gaps = json.loads(gap_response.content)
    internal_gaps = gaps.get("internal", [])
    external_gaps = gaps.get("external", [])

    # === 3. Collect Internal Answers (CRITICAL only) ===
    internal_answers = {}
    if internal_gaps:
        collector = BusinessContextCollector(console)
        internal_answers = collector.collect_internal_answers(internal_gaps)

    # === 4. Auto-Research External Gaps (Week 4+ when ResearcherAgent implemented) ===
    external_research = []
    if external_gaps:
        researcher = ResearcherAgent()
        external_research = await researcher.research_questions(external_gaps)

    # === 5. Inject Context into Problem ===
    # Build combined context string
    context_parts = []

    if business_context:
        collector = BusinessContextCollector(console)
        context_parts.append(collector.format_context_for_prompt(business_context))

    if internal_answers:
        collector = BusinessContextCollector(console)
        context_parts.append(collector.format_internal_context(internal_answers))

    if external_research:
        researcher = ResearcherAgent()
        context_parts.append(researcher.format_research_context(external_research))

    # Update problem context
    if context_parts:
        enriched_context = "\n\n".join(context_parts)
        state["problem"].context = (state["problem"].context or "") + "\n\n" + enriched_context

    # Track metrics
    state["metrics"].phase_costs["context_collection"] = (
        gap_response.cost_total + sum(r.get("cost", 0) for r in external_research)
    )

    console.print("[green]✓ Context collection complete[/green]")

    return state
```

### New Facilitator Action: `"clarify"`

Update `FacilitatorAgent` to support clarification requests:

```python
# bo1/agents/facilitator.py

class FacilitatorDecision:
    action: str  # "continue" | "vote" | "moderator" | "research" | "clarify"
    clarification_question: str | None  # NEW: For action="clarify"
    clarification_reason: str | None
    # ... existing fields
```

### New Router: `route_clarification()`

```python
# bo1/graph/routers.py

def route_clarification(state: DeliberationGraphState) -> str:
    """Route based on clarification status.

    If facilitator action="clarify":
    - In console mode: Prompt user immediately OR pause session
    - In web mode: Pause session, wait for user to submit answer

    Returns:
        "wait_for_clarification" -> clarification_node (handles pause/resume)
        "continue" -> persona_contribute_node (if user answered)
    """
    decision = state.get("facilitator_decision")

    if decision and decision.action == "clarify":
        # Check if user has provided an answer
        if state.get("clarification_answer"):
            return "continue"  # Answer provided, continue
        else:
            return "wait_for_clarification"  # Pause for answer

    # Not a clarification request
    return "continue"
```

### New Node: `clarification_node()`

```python
# bo1/graph/nodes.py

async def clarification_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Handle mid-deliberation clarification requests.

    In console mode:
    - Prompts user for answer OR offers pause
    - If pause: saves checkpoint, exits with instructions
    - If answer: injects into state, continues

    In web mode:
    - Sets session status="waiting_for_clarification"
    - Frontend shows question, user submits via API
    - Session resumes when answer provided
    """
    decision = state.get("facilitator_decision")
    question = decision.clarification_question
    reason = decision.clarification_reason

    console = Console()
    console.print("\n[bold red]⚠️  CLARIFICATION NEEDED[/bold red]")
    console.print(f"Question: {question}")
    console.print(f"Why: {reason}\n")

    console.print("Options:")
    console.print("  1. Answer now")
    console.print("  2. Pause session (gather info, resume later)")
    console.print("  3. Skip (deliberation continues with lower confidence)")

    choice = console.input("\nChoose (1/2/3): ").strip()

    if choice == "1":
        # Answer now
        answer = console.input(f"\n{question}\nAnswer: ").strip()

        # Inject answer into problem context
        clarification_context = f"\n\n<clarification>\n  <question>{question}</question>\n  <answer>{answer}</answer>\n</clarification>"
        state["problem"].context += clarification_context

        # Save to database (for audit trail)
        await save_clarification(
            session_id=state["session_id"],
            question=question,
            answer=answer,
            asked_by_persona=decision.next_speaker,
            round_number=state["round_number"],
        )

        console.print("[green]✓ Answer recorded, continuing deliberation...[/green]")

    elif choice == "2":
        # Pause session
        console.print("\n[yellow]Session paused.[/yellow]")
        console.print(f"Resume with: bo1 --resume {state['session_id']}")
        console.print(f"\nWhen you resume, provide answer to: {question}")

        # Mark session as paused (checkpoint auto-saved by LangGraph)
        state["should_stop"] = True
        state["stop_reason"] = "user_requested_pause_for_clarification"

        # Store clarification question in state for resume
        state["pending_clarification"] = {
            "question": question,
            "reason": reason,
            "asked_by": decision.next_speaker,
        }

    else:
        # Skip
        console.print("[yellow]⚠ Skipped - deliberation quality may be reduced[/yellow]")

        # Log skip (for deliberation quality analysis)
        await save_clarification(
            session_id=state["session_id"],
            question=question,
            answer="[SKIPPED]",
            asked_by_persona=decision.next_speaker,
            round_number=state["round_number"],
        )

    return state
```

---

## Graph Structure Changes

```python
# bo1/graph/config.py

def create_deliberation_graph():
    """Create LangGraph with context collection + clarification."""

    workflow = StateGraph(DeliberationGraphState)

    # Nodes
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("context_collection", context_collection_node)  # NEW
    workflow.add_node("select_personas", select_personas_node)
    workflow.add_node("initial_round", initial_round_node)
    workflow.add_node("facilitator_decide", facilitator_decide_node)
    workflow.add_node("clarification", clarification_node)  # NEW
    workflow.add_node("persona_contribute", persona_contribute_node)
    workflow.add_node("moderator_intervene", moderator_intervene_node)
    workflow.add_node("check_convergence", check_convergence_node)
    workflow.add_node("vote", vote_node)
    workflow.add_node("synthesize", synthesize_node)

    # Edges
    workflow.set_entry_point("decompose")
    workflow.add_edge("decompose", "context_collection")  # NEW
    workflow.add_edge("context_collection", "select_personas")  # CHANGED (was: decompose → select)
    workflow.add_edge("select_personas", "initial_round")
    workflow.add_edge("initial_round", "facilitator_decide")

    # Conditional routing from facilitator
    workflow.add_conditional_edges(
        "facilitator_decide",
        route_facilitator_decision,
        {
            "vote": "vote",
            "moderator": "moderator_intervene",
            "continue": "persona_contribute",
            "clarify": "clarification",  # NEW
        },
    )

    # Clarification routing
    workflow.add_conditional_edges(
        "clarification",
        route_clarification,
        {
            "continue": "persona_contribute",
            "wait_for_clarification": END,  # Pause session
        },
    )

    # ... rest of edges

    return workflow.compile(checkpointer=checkpointer, recursion_limit=55)
```

---

## API Endpoints (Week 6)

### User Context Management

```python
# backend/api/context.py

@router.get("/api/v1/context")
async def get_user_context(user_id: str = Depends(get_current_user)):
    """Get user's saved business context."""
    context = await load_user_context(user_id)
    if not context:
        return {"exists": False}
    return {"exists": True, "context": context, "updated_at": context["updated_at"]}

@router.put("/api/v1/context")
async def update_user_context(
    context: BusinessContextUpdate,
    user_id: str = Depends(get_current_user),
):
    """Update user's business context."""
    await save_user_context(user_id, context.model_dump())
    return {"status": "updated"}

@router.delete("/api/v1/context")
async def delete_user_context(user_id: str = Depends(get_current_user)):
    """Delete user's saved context."""
    await delete_user_context(user_id)
    return {"status": "deleted"}
```

### Clarification Handling

```python
# backend/api/deliberation.py

@router.post("/api/v1/sessions/{session_id}/clarify")
async def submit_clarification(
    session_id: str,
    answer: ClarificationAnswer,
    user_id: str = Depends(get_current_user),
):
    """Submit answer to clarification question and resume session.

    Injects answer into problem context and resumes graph execution.
    """
    # Load session state
    state = await load_session_state(session_id)

    # Verify ownership
    if state["user_id"] != user_id:
        raise HTTPException(403, "Not your session")

    # Inject answer
    question = state["pending_clarification"]["question"]
    clarification_context = f"<clarification><question>{question}</question><answer>{answer.text}</answer></clarification>"
    state["problem"].context += clarification_context

    # Clear pending clarification
    state["pending_clarification"] = None
    state["should_stop"] = False

    # Resume execution (background task)
    asyncio.create_task(resume_session(session_id, state))

    return {"status": "resumed"}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/graph/test_context_collection_node.py

async def test_context_collection_with_saved_context():
    """User has saved context, loads it successfully."""
    # Mock user_context table
    # Verify context loaded from DB
    # Verify no prompt to user

async def test_context_collection_identifies_gaps():
    """AI identifies CRITICAL vs NICE_TO_HAVE gaps."""
    # Verify gap identification works
    # Verify internal vs external categorization

async def test_clarification_node_answer_now():
    """User answers clarification immediately."""
    # Mock user input
    # Verify answer injected into context
    # Verify deliberation continues

async def test_clarification_node_pause():
    """User pauses session to gather info."""
    # Mock user choosing "pause"
    # Verify should_stop=True
    # Verify pending_clarification saved
```

### Integration Tests

```python
# tests/integration/test_context_collection_flow.py

async def test_full_context_collection_flow():
    """End-to-end: business context → gap identification → research → deliberation."""
    # Create session with no saved context
    # Collect business context
    # Decompose problem
    # Identify gaps
    # Collect internal answers
    # Research external gaps
    # Verify all context injected
    # Verify deliberation uses context

async def test_clarification_pause_resume():
    """User pauses for clarification, then resumes."""
    # Start deliberation
    # Trigger clarification request
    # User chooses pause
    # Resume session
    # Provide answer
    # Verify deliberation continues
```

---

## Week 6 Task Breakdown

Add these tasks to **Day 36** (Database changes) and **Day 37** (Graph nodes):

### Day 36 Additions:

- [ ] Create `user_context` table migration
- [ ] Create `session_clarifications` table migration
- [ ] Add `bo1/state/postgres_manager.py` functions:
  - [ ] `load_user_context(user_id)`
  - [ ] `save_user_context(user_id, context)`
  - [ ] `delete_user_context(user_id)`
  - [ ] `save_clarification(session_id, question, answer, ...)`
- [ ] Write tests for user_context CRUD operations

### Day 37 Additions:

- [ ] Implement `context_collection_node()` in `bo1/graph/nodes.py`
- [ ] Implement `clarification_node()` in `bo1/graph/nodes.py`
- [ ] Add `"clarify"` action to `FacilitatorDecision`
- [ ] Update `route_facilitator_decision()` to handle "clarify"
- [ ] Add `route_clarification()` router
- [ ] Update graph structure in `bo1/graph/config.py`
- [ ] Write unit tests for context collection node
- [ ] Write unit tests for clarification node
- [ ] Write integration test for full flow

### Day 38 Additions:

- [ ] Add SSE events for clarification requests:
  - [ ] `clarification_requested` - Frontend shows question form
  - [ ] `clarification_answered` - Deliberation resumes
- [ ] Add API endpoints:
  - [ ] `GET /api/v1/context` - Get saved context
  - [ ] `PUT /api/v1/context` - Update context
  - [ ] `POST /api/v1/sessions/{id}/clarify` - Submit answer

---

## Success Metrics

- [ ] Users can save/load business context across sessions
- [ ] Business context reduces repetitive questions by 80%+
- [ ] AI identifies 2-5 CRITICAL gaps per complex problem
- [ ] EXTERNAL gaps auto-filled via web research (90% accuracy)
- [ ] Clarification pause/resume works flawlessly (0 data loss)
- [ ] Users can update saved context anytime (profile page)

---

## Future Enhancements (Post-MVP)

1. **Smart Context Invalidation**: Detect stale context (revenue hasn't been updated in 6 months)
2. **Context Suggestions**: AI suggests what context to add based on problem type
3. **Batch Clarifications**: Group multiple clarification questions together
4. **Context Sharing**: Share anonymized context with other users (benchmarking)
5. **Web Scraping**: Auto-fill context from user's website (website field)

---

## Open Questions

1. **Should business context be optional or required?**
   - Recommendation: Optional (some problems don't need it)
   - Show impact: "Adding context improves recommendations by 40%"

2. **How many CRITICAL gaps before warning user?**
   - Recommendation: 5+ gaps → "This is a complex problem, may take extra time"

3. **Should we auto-pause on CRITICAL gap with no answer?**
   - Recommendation: No, allow skip (user sovereignty)
   - Track skip rate → surface in admin dashboard

4. **Context expiration policy?**
   - Recommendation: Never expire, but flag as "stale" after 6 months
   - Prompt user to update on next session

---

**End of Specification**
