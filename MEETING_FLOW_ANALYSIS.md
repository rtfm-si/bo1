# Board of One: Visual Meeting Flow Analysis

**Generated**: 2025-01-22
**Purpose**: Complete visual map of deliberation flow, contributors, and decision points

---

## 🎯 Quick Summary

Board of One orchestrates multi-agent deliberations using LangGraph with:
- **13 nodes** (processing steps)
- **5 routers** (decision points)
- **2 main loops** (discussion rounds, multi-sub-problem)
- **25+ event types** (real-time streaming)
- **7 system agents** (decomposer, selector, facilitator, moderator, personas, summarizer, synthesizer)

**Average flow**: 8-12 nodes executed per sub-problem, 15-40 total nodes for complete session

---

## 📊 Complete Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            START DELIBERATION                                    │
│                                    ↓                                             │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 1: INTAKE & DECOMPOSITION                                          ║  │
│  ║ Actor: System (DecomposerAgent)                                          ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  decompose_node                          │                        │
│              │  • Analyzes problem                      │                        │
│              │  • Creates 1-5 sub-problems              │                        │
│              │  • Assigns complexity scores             │                        │
│              │  Events: decomposition_started/complete  │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  context_collection_node                 │                        │
│              │  • Loads saved business context from DB  │                        │
│              │  • Injects into problem statement        │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
│                        [route_phase: decomposition → selection]                  │
│                                    ↓                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 2: PERSONA SELECTION (Per Sub-Problem)                             ║  │
│  ║ Actor: System (PersonaSelectorAgent)                                     ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  select_personas_node                    │                        │
│              │  • Selects 3-5 best-fit experts          │                        │
│              │  • From library of 45 personas           │                        │
│              │  • Based on sub-problem domain           │                        │
│              │  Events: persona_selection_started,      │                        │
│              │          persona_selected (×N),          │                        │
│              │          persona_selection_complete      │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
│                        [route_phase: selection → discussion]                     │
│                                    ↓                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 3: INITIAL ROUND (Parallel)                                        ║  │
│  ║ Actors: All Selected Personas (3-5 experts)                              ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  initial_round_node                      │                        │
│              │  • All personas contribute in parallel   │                        │
│              │  • Opening positions on sub-problem      │                        │
│              │  • Round number = 1                      │                        │
│              │  Events: initial_round_started,          │                        │
│              │          contribution (×N personas)      │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 4: MULTI-ROUND DISCUSSION LOOP (2-15 rounds)                       ║  │
│  ║ Actors: FacilitatorAgent, Selected Personas, ModeratorAgent              ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ╔════════════════════════════════════════════════════╗              │
│              ║                  LOOP START                        ║              │
│              ╚════════════════════════════════════════════════════╝              │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  facilitator_decide_node                 │                        │
│              │  • Analyzes discussion state             │                        │
│              │  • Makes strategic decision              │                        │
│              │  Decision: continue / vote / moderator / │                        │
│              │            clarify / research            │                        │
│              │  Events: facilitator_decision            │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
│           [route_facilitator_decision: action → execution node]                  │
│              ↓           ↓          ↓          ↓          ↓                      │
│         continue      vote      moderator  clarify    research                   │
│              ↓           ↓          ↓          ↓          ↓                      │
│  ┌────────────────┐  ┌────────┐ ┌─────────┐ ┌─────────┐ [future]               │
│  │ persona_       │  │ vote   │ │moderator│ │clarify  │                         │
│  │ contribute     │  │ node   │ │intervene│ │node     │                         │
│  │ node           │  └────────┘ │node     │ └─────────┘                         │
│  │                │      ↓       └─────────┘      ↓                              │
│  │ • Specific     │   [SKIP TO    ↓          [User answers                      │
│  │   persona      │    VOTING]  [Back to     OR pauses                          │
│  │   contributes  │              check]      session]                            │
│  │ • Round n      │                ↓              ↓                              │
│  │ • Full context │         ┌──────────────────────────┐                        │
│  │ Events:        │         │  check_convergence_node  │                        │
│  │  contribution  │         │  • Evaluates stop        │                        │
│  └────────────────┘         │    conditions            │                        │
│              ↓              │  • Checks: max rounds,   │                        │
│              │              │    convergence score,    │                        │
│              │              │    cost exceeded         │                        │
│              │              │  Events: convergence     │                        │
│              │              └──────────────────────────┘                        │
│              │                         ↓                                         │
│              │         [route_convergence_check: should_stop?]                  │
│              │                  ↓              ↓                                 │
│              │             should_stop=False   should_stop=True                 │
│              │                  ↓              ↓                                 │
│              └──────[LOOP BACK]─┘           [EXIT TO VOTING]                    │
│                                                ↓                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 5: RECOMMENDATION COLLECTION                                       ║  │
│  ║ Actors: All Personas (parallel) + System                                 ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  vote_node                               │                        │
│              │  • All personas give recommendations     │                        │
│              │  • Free-form text (NOT binary yes/no)    │                        │
│              │  • Includes: recommendation, reasoning,  │                        │
│              │    confidence, conditions                │                        │
│              │  • AI aggregates into consensus          │                        │
│              │  Events: voting_started,                 │                        │
│              │          persona_vote (×N),              │                        │
│              │          voting_complete                 │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 6: SYNTHESIS (Per Sub-Problem)                                     ║  │
│  ║ Actor: System (Synthesis LLM - Sonnet 4.5)                               ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  synthesize_node                         │                        │
│              │  • AI synthesizes discussion +           │                        │
│              │    recommendations                       │                        │
│              │  • Generates 1-3K token report           │                        │
│              │  • Includes thinking + analysis          │                        │
│              │  • AI-generated disclaimer               │                        │
│              │  Events: synthesis_started,              │                        │
│              │          synthesis_complete              │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
│                  [route_after_synthesis: more sub-problems?]                     │
│                       ↓               ↓                ↓                         │
│              If more exist    If all done (>1)   If atomic (1 only)             │
│                       ↓               ↓                ↓                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 7: NEXT SUB-PROBLEM (If Applicable)                                ║  │
│  ║ Actor: System                                                            ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  next_subproblem_node                    │                        │
│              │  • Saves current sub-problem result      │                        │
│              │  • Generates expert memory summaries     │                        │
│              │    (75 tokens each)                      │                        │
│              │  • Increments sub_problem_index          │                        │
│              │  • Resets state for next problem         │                        │
│              │  Events: subproblem_complete,            │                        │
│              │          subproblem_started (next)       │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
│                  [LOOP BACK TO select_personas_node]                             │
│                          (Process next sub-problem)                              │
│                                    ↓                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 8: META-SYNTHESIS (If 2+ Sub-Problems)                             ║  │
│  ║ Actor: System (Meta-Synthesis LLM - Sonnet 4.5)                          ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  meta_synthesize_node                    │                        │
│              │  • Integrates ALL sub-problem syntheses  │                        │
│              │  • Cross-references recommendations      │                        │
│              │  • Creates holistic decision framework   │                        │
│              │  • 3-4K token unified report             │                        │
│              │  Events: meta_synthesis_started,         │                        │
│              │          meta_synthesis_complete         │                        │
│              └──────────────────────────────────────────┘                        │
│                                    ↓                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ PHASE 9: COMPLETION                                                      ║  │
│  ║ Actor: System                                                            ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                    ↓                                             │
│              ┌──────────────────────────────────────────┐                        │
│              │  END                                     │                        │
│              │  • Session marked complete               │                        │
│              │  • Total cost & token breakdown          │                        │
│              │  • Results available on results page     │                        │
│              │  Events: phase_cost_breakdown,           │                        │
│              │          complete                        │                        │
│              └──────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Loop Prevention System (5 Layers)

Board of One guarantees deliberations **cannot loop indefinitely** through five defensive layers:

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 1: LangGraph Recursion Limit (compile-time)           │
│ • Hard cap: 55 steps max                                    │
│ • Throws: GraphRecursionError                               │
├──────────────────────────────────────────────────────────────┤
│ Layer 2: Cycle Detection (compile-time)                     │
│ • Rejects graphs with uncontrolled cycles                   │
│ • Validates conditional edges                               │
├──────────────────────────────────────────────────────────────┤
│ Layer 3: Round Counter (domain logic)                       │
│ • Hard cap: 15 rounds absolute max                          │
│ • User config: max_rounds (default 10)                      │
│ • Checked in: check_convergence_node                        │
├──────────────────────────────────────────────────────────────┤
│ Layer 4: Timeout Watchdog (runtime)                         │
│ • Max execution: 1 hour (3600 seconds)                      │
│ • Kills long-running sessions                               │
├──────────────────────────────────────────────────────────────┤
│ Layer 5: Cost Kill Switch (budget enforcement)              │
│ • Tier-based limits: $1.00-$100.00                          │
│ • Forces early synthesis when exceeded                      │
└──────────────────────────────────────────────────────────────┘
```

**Guarantee**: Even if 4 layers fail, the 5th will stop the loop.

---

## 🎭 Contributors & Their Roles

### System Agents (LLM-Powered)

| Agent | Role | Called When | Output |
|-------|------|-------------|--------|
| **DecomposerAgent** | Problem analyzer | Once per session (start) | 1-5 sub-problems with complexity scores |
| **PersonaSelectorAgent** | Expert curator | Once per sub-problem | 3-5 best-fit personas from 45-expert library |
| **FacilitatorAgent** | Orchestrator | Every discussion round | Decision: continue/vote/moderator/clarify/research |
| **ModeratorAgent** | Contrarian/Skeptic/Optimist | When facilitator requests | Redirect conversation, challenge consensus |
| **Personas (Expert Panel)** | Domain experts | Initial round (parallel), Discussion (sequential), Voting (parallel) | Contributions, recommendations |
| **SummarizerAgent** | Context compressor | Per expert per sub-problem | 75-token memory summary |
| **Synthesis LLM** | Report generator | Per sub-problem + meta-synthesis | 1-4K token structured report |

### Persona Library (45 Experts)

Experts are selected from `bo1/data/personas.json` based on domain expertise:

**Examples**:
- **Financial Analysis**: Maria (Private Equity), Zara (VC Investor), Tariq (Financial Analyst)
- **Product Strategy**: Jamie (Product Manager), Alex (UX Designer), Cameron (Growth PM)
- **Operations**: Jordan (Operations), Morgan (Supply Chain), Riley (Process Engineer)
- **Marketing**: Avery (Brand Strategy), Taylor (Digital Marketing), Quinn (Content)

Each persona has:
- `code`: Unique identifier (e.g., "maria_private_equity")
- `name`: Display name
- `domain_expertise`: Tags (e.g., "finance", "saas", "pricing")
- `system_prompt`: Bespoke ~879 char identity (what makes them unique)

---

## 🔀 Decision Points Matrix

| # | Decision Point | Made By | Trigger | Options | Impact |
|---|----------------|---------|---------|---------|--------|
| **1** | **Proceed to Selection?** | `route_phase` | Decomposition complete | Auto-proceed | Moves to persona selection |
| **2** | **Which Experts?** | PersonaSelectorAgent | Sub-problem assigned | 3-5 personas from 45 | Determines who participates |
| **3** | **Proceed to Discussion?** | `route_phase` | Personas selected | Auto-proceed | Moves to initial round |
| **4** | **What's Next?** | FacilitatorAgent | After each round | **continue** (pick speaker)<br>**vote** (stop discussing)<br>**moderator** (intervene)<br>**clarify** (ask user)<br>**research** (web search) | Controls discussion flow |
| **5** | **Which Speaker?** | FacilitatorAgent | If action=continue | Specific persona code | Determines who speaks next |
| **6** | **Should Stop?** | check_convergence_node | After contribution | **Yes** (max rounds / convergence / cost)<br>**No** (continue) | Exit loop or continue discussing |
| **7** | **Need Clarification?** | FacilitatorAgent | If action=clarify | User answers / pauses / skips | Blocks until resolved or skipped |
| **8** | **More Sub-Problems?** | `route_after_synthesis` | Synthesis complete | **next_subproblem** (more exist)<br>**meta_synthesis** (all done, >1)<br>**END** (atomic, 1 only) | Determines completion path |

---

## 📡 Event Publishing & Frontend Display

### Backend Event Flow (Redis PubSub)

```
LangGraph Node → EventCollector.publish_event() → Redis PubSub Channel
                                                        ↓
                                              Redis List (history)
                                                        ↓
                                          FastAPI SSE Endpoint (/stream)
                                                        ↓
                                              Frontend EventSource
```

### Event Categories (25+ Types)

| Category | Events | Display In Frontend |
|----------|--------|---------------------|
| **Session** | session_started, complete | Header (status badge) |
| **Decomposition** | decomposition_started, decomposition_complete | Timeline phase, main panel |
| **Personas** | persona_selection_started, persona_selected (×N), persona_selection_complete, subproblem_started | Timeline phase, expert cards |
| **Discussion** | initial_round_started, contribution, facilitator_decision, moderator_intervention, convergence, round_started | Main panel (grouped by round) |
| **Voting** | voting_started, persona_vote (×N), voting_complete | Progress overlay, vote cards |
| **Synthesis** | synthesis_started, synthesis_complete, subproblem_complete, meta_synthesis_started, meta_synthesis_complete | Progress overlay, results panel |
| **Metadata** | phase_cost_breakdown, node_start, node_end | Sidebar dashboard |
| **Special** | clarification_requested, error | Modal dialogs |

### Frontend Event Deduplication

Events are deduplicated by composite key:
```javascript
`${timestamp}-${event_type}-${persona_code || sub_problem_id || ''}`
```

Prevents duplicate display when:
- Historical events loaded via REST API
- Same events received via SSE stream
- Page refresh during active deliberation

---

## 📐 Complexity Examples

### Simple Problem (1 sub-problem, 5 rounds)

```
decompose → context → select_personas → initial_round
  → facilitator_decide → persona_contribute × 4 rounds
  → check_convergence (should_stop=True)
  → vote → synthesize → END

Total Nodes: 13
Total Rounds: 5 (initial + 4 discussion)
Total Contributions: ~20 (4 personas × 5 rounds)
Cost: ~$0.10
Duration: ~5-8 minutes
```

### Complex Problem (3 sub-problems, 10 rounds each)

```
decompose → context →
  [SUB-PROBLEM 1]
  select_personas → initial_round → facilitator_decide
    → [9 discussion rounds with persona_contribute + check_convergence]
    → vote → synthesize → next_subproblem
  [SUB-PROBLEM 2]
  select_personas → initial_round → facilitator_decide
    → [9 discussion rounds]
    → vote → synthesize → next_subproblem
  [SUB-PROBLEM 3]
  select_personas → initial_round → facilitator_decide
    → [9 discussion rounds]
    → vote → synthesize
  → meta_synthesize → END

Total Nodes: ~85
Total Rounds: 30 (3 × 10)
Total Contributions: ~150 (5 personas × 30 rounds)
Cost: ~$0.30-0.45
Duration: ~15-25 minutes
```

---

## 🧮 State Tracking

### Core State Variables (DeliberationGraphState TypedDict)

```python
{
    # Session Identity
    "session_id": "bo1_abc123...",
    "problem": Problem,  # Original problem + context
    "current_sub_problem": SubProblem,  # Active sub-problem

    # Participants
    "personas": [Persona × 3-5],  # Selected experts

    # Discussion State
    "contributions": [
        {"round": 1, "persona_code": "maria", "text": "...", "timestamp": ...},
        ...
    ],
    "round_number": 5,  # Current round (1-15)
    "max_rounds": 10,  # User-configured limit

    # Phase Control
    "phase": "discussion",  # decomposition | selection | discussion | voting | synthesis

    # Facilitator Decisions
    "facilitator_decision": {
        "action": "continue",  # continue | vote | moderator | clarify | research
        "reasoning": "Maria raised a key point...",
        "next_speaker": "zara_vc_investor",
        "moderator_type": None,  # contrarian | skeptic | optimist
        ...
    },

    # Convergence Control
    "should_stop": False,
    "stop_reason": None,  # "max_rounds" | "convergence" | "cost_exceeded"

    # Recommendations
    "votes": [  # Legacy name, actually recommendations
        {
            "persona_code": "maria",
            "recommendation": "Invest $300K initially...",
            "reasoning": "...",
            "confidence": 0.85,
            "conditions": ["Market validation", ...],
        },
        ...
    ],

    # Output
    "synthesis": "# Final Recommendation\n\n...",  # Report text

    # Multi-Sub-Problem State
    "sub_problem_results": [
        {
            "sub_problem": SubProblem,
            "synthesis": "...",
            "votes": [...],
            "expert_memories": {  # 75 tokens each
                "maria": "Maria emphasized ROI...",
                ...
            },
            "metrics": {...},
        },
        ...
    ],
    "sub_problem_index": 0,  # Current index (0-based)

    # Cost & Metrics
    "metrics": {
        "total_cost": 0.1234,
        "convergence_score": 0.92,
        "phase_costs": {
            "decomposition": 0.005,
            "persona_selection": 0.008,
            "initial_round": 0.045,
            "discussion_round_2": 0.015,
            ...
        },
    },

    # Human-in-the-Loop
    "pending_clarification": {
        "question": "What is your current churn rate?",
        "category": "CRITICAL",
        "asked_at": timestamp,
    },
    "business_context": {
        "business_model": "B2B SaaS",
        "target_market": "Enterprise",
        ...
    },
}
```

---

## 🎨 Frontend UI Structure

### Page Layout (`/meeting/[id]`)

```
┌───────────────────────────────────────────────────────────────┐
│ HEADER                                                        │
│ • Session title                                               │
│ • Progress: "Sub-problem 2/3 • Discussion Round 5 • Voting"  │
│ • Controls: [Pause] [Resume] [Stop]                          │
├───────────────────────────────────────────────────────────────┤
│ TIMELINE                                                      │
│ [✓ Decompose] → [✓ Select] → [● Discuss] → [ Vote] → [ Done] │
├─────────────────────────────────────┬─────────────────────────┤
│ MAIN PANEL                          │ SIDEBAR                 │
│                                     │                         │
│ ┌─────────────────────────────────┐ │ ┌─────────────────────┐ │
│ │ EVENT STREAM                    │ │ │ PROBLEM STATEMENT   │ │
│ │                                 │ │ │ (collapsible)       │ │
│ │ [Round 1]                       │ │ └─────────────────────┘ │
│ │  • Maria: "I recommend..."      │ │                         │
│ │  • Zara: "Considering the..."   │ │ ┌─────────────────────┐ │
│ │                                 │ │ │ METRICS DASHBOARD   │ │
│ │ [Round 2]                       │ │ │ • Cost: $0.15       │ │
│ │  • Facilitator: "Zara to speak" │ │ │ • Rounds: 5/10      │ │
│ │  • Zara: "Building on Maria..." │ │ │ • Convergence: 0.72 │ │
│ │                                 │ │ └─────────────────────┘ │
│ │ [Synthesizing...]               │ │                         │
│ │  Progress overlay shown         │ │ ┌─────────────────────┐ │
│ └─────────────────────────────────┘ │ │ RESULTS LINK        │ │
│                                     │ │ (after completion)  │ │
└─────────────────────────────────────┴─────────────────────────┘
```

### Event Display Priority

```javascript
// Major events (blue gradient, shadow)
['complete', 'synthesis_complete', 'meta_synthesis_complete']

// Meta events (slate, subtle)
['node_start', 'node_end', 'phase_cost_breakdown']

// Standard events (default styling)
[all other event types]
```

---

## 🚀 Performance Characteristics

### Typical Session Metrics

| Metric | Simple (1 sub, 5 rounds) | Moderate (2 subs, 7 rounds) | Complex (3 subs, 10 rounds) |
|--------|--------------------------|-----------------------------|-----------------------------|
| **Total Nodes** | ~13 | ~45 | ~85 |
| **LLM Calls** | ~25 | ~60 | ~120 |
| **Total Contributions** | ~20 | ~70 | ~150 |
| **Cost** | $0.08-0.12 | $0.20-0.30 | $0.30-0.50 |
| **Duration** | 5-8 min | 10-15 min | 15-25 min |
| **Events Published** | ~40 | ~120 | ~220 |

### Cost Breakdown (Typical Complex Session)

```
Decomposition:        $0.005  (  1%)
Persona Selection:    $0.024  (  5%) - 3 sub-problems
Initial Rounds:       $0.135  ( 27%) - 3 × 5 personas
Discussion Rounds:    $0.225  ( 45%) - 3 × 10 rounds × 1 persona/round
Voting:              $0.045  (  9%) - 3 × 5 personas
Synthesis:           $0.036  (  7%) - 3 sub-problems
Meta-Synthesis:      $0.024  (  5%)
Summaries:           $0.006  (  1%) - Background task
─────────────────────────────
TOTAL:               $0.500  (100%)
```

**Cost Optimization**:
- Prompt caching: 90% reduction for persona calls (initial round → discussion rounds)
- Haiku for summaries: 75% cheaper than Sonnet
- Hierarchical context: Prevents quadratic growth

---

## 🔧 Control Parameters

### User-Configurable

| Parameter | Default | Range | Impact |
|-----------|---------|-------|--------|
| `max_rounds` | 10 | 1-15 | Max discussion rounds per sub-problem |
| `complexity_threshold` | Auto | Low/Med/High | Affects max_rounds selection |
| `cost_limit` | $1.00 | Tier-based | Max spend per session |

### System Constants

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `convergence_threshold` | 0.85 | Semantic similarity to trigger early stop |
| `min_rounds_for_convergence` | 3 | Can't converge before round 3 |
| `recursion_limit` | 55 | LangGraph recursion safety |
| `timeout_seconds` | 3600 | 1-hour max execution |
| `checkpoint_ttl` | 604800 | 7-day checkpoint persistence |

---

## 🎯 Key Design Principles

### 1. User Sovereignty
- System provides **recommendations**, not directives
- Language: "We recommend..." not "You must..."
- User makes final decision

### 2. Flexible Recommendations (NOT Binary Voting)
- **Old system** (removed): Binary yes/no votes with `VoteDecision` enum
- **New system**: Free-form recommendation strings
  - "Invest $300K initially, then $200K after validation"
  - "Prioritize pricing model B with modifications"
  - "No, pivot to strategy C instead"

### 3. Cost-Aware Execution
- Phase-based cost tracking
- Budget limits prevent runaway costs
- Prompt caching reduces costs by 90%

### 4. Loop Prevention Guarantee
- Five defensive layers ensure no infinite loops
- Worst case: 15 rounds × 5 personas × 3 subs = ~$0.50 max

### 5. Context Efficiency
- Hierarchical summarization (old rounds = 100 tokens, current = full)
- Expert memory (75 tokens per expert per sub-problem)
- Linear growth, not quadratic

### 6. Human-in-the-Loop Balance
- Optional context collection (encouraged, not required)
- Pause/resume for blocking questions
- User can skip any question (system adapts)

---

## 📚 Related Documentation

- **LangGraph Structure**: `bo1/graph/` (nodes, routers, state, config)
- **Prompt Engineering**: `zzz_important/` (framework docs)
- **Recommendation System**: `bo1/models/recommendations.py`
- **Event Streaming**: `backend/api/streaming.py`, `backend/api/event_collector.py`
- **Frontend Meeting UI**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte`
- **Loop Prevention**: `bo1/graph/safety/loop_prevention.py`
- **Cost Analytics**: `bo1/graph/analytics.py`

---

**End of Analysis**

This document provides a complete visual map of Board of One's deliberation flow, from problem intake to final recommendation. The system orchestrates multi-agent discussions through a sophisticated LangGraph state machine with guaranteed loop prevention, cost controls, and real-time event streaming to the frontend.
