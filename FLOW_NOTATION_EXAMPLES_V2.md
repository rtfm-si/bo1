# Board of One: Flow Notation Examples v2.0

**Using**: BO1-FDL v2.0.0 (see FLOW_DESIGN_LANGUAGE_V2.md)
**Current Flow**: Board of One v2 (production)

---

## Current Production Flow (All Detail Levels)

### L0: Phase Names Only
```
setup -> discussion ->loop-> voting -> complete
```

**30-second pitch**: "Setup selects experts, discussion loops until convergence, voting collects recommendations, synthesis produces output."

---

### L1: Phase Structure with Cardinality
```
setup[4 nodes] -> discussion[loop: 5-10 iterations] -> voting[3 nodes] -> complete

Multi-sub-problem:
  decompose -> [
    sp1: select -> discuss[loop] -> vote -> synth,
    sp2: select -> discuss[loop] -> vote -> synth,
    sp3: select -> discuss[loop] -> vote -> synth
  ] -> meta_synth -> complete
```

**5-minute overview**: Shows phase counts, loop iterations, multi-sub-problem structure

---

### L2: Standard Detail (Working Level)

```
# ===== SETUP PHASE =====
setup:
  START -> decompose(problem) -> sub_problems[1-5]

  decompose -> context_collection(sub_problems, user_id) -> enriched_context

  context_collection -> select_personas(current_sub_problem, enriched_context) -> personas[3-5]

  select_personas -> fork -> initial_round(persona) || 5 -> join -> contributions[5]


# ===== DISCUSSION PHASE (Multi-Round Loop) =====
discussion: DISCUSSION_LOOP_START

  initial_round -> facilitator_decide(contributions[5], round_number)

  facilitator_decide ? {
    action=vote: vote,
    action=moderator: moderator_intervene,
    action=continue: persona_contribute,
    action=clarify: clarification
  }

  persona_contribute(decision, round_context)
    after: {round_number: +1}
    -> contribution

  moderator_intervene(decision, contributions)
    -> moderator_guidance

  clarification(facilitator_question) ? {
    user_action=answered: persona_contribute,
    user_action=skipped: persona_contribute,
    user_action=paused: PAUSE_STATE
  }

  persona_contribute -> check_convergence(contribution, round_number, max_rounds)
  moderator_intervene -> check_convergence(moderator_guidance, round_number, max_rounds)

  check_convergence ? {
    should_stop=false AND round<max_rounds: ->loop(DISCUSSION_LOOP_START)-> facilitator_decide,
    should_stop=true: vote,
    error(cost_exceeded): ->force-> vote,
    error(round_limit): ->force-> vote
  }


# ===== VOTING PHASE =====
voting:
  vote: fork -> persona_recommend(persona) || 5 -> join -> recommendations[5]

  vote -> synthesize(recommendations[5], all_contributions) -> synthesis

  synthesize -> check_next_subproblem(sub_problem_index, total_sub_problems)

  check_next_subproblem ? {
    is_atomic: END,
    has_more: next_subproblem,
    all_complete: meta_synthesis
  }


# ===== MULTI-SUB-PROBLEM LOOP =====
subproblem_handling: SUBPROBLEM_LOOP_START

  next_subproblem(current_synthesis, sub_problem_index)
    after: {
      sub_problem_index: +1,
      sub_problem_results: append(current_synthesis),
      expert_memories: generate_summaries(personas, contributions)
    }
    ->loop(SUBPROBLEM_LOOP_START)-> select_personas


# ===== META-SYNTHESIS =====
meta:
  meta_synthesis(sub_problem_results[]) ∑ -> final_synthesis

  meta_synthesis -> END


# ===== PAUSE/RESUME =====
pause: PAUSE_STATE
  checkpoint: redis
  ttl: 604800
  resume_target: discussion.DISCUSSION_LOOP_START
  resume_trigger: user_action=resume
```

---

### L3: Full Detail with Metadata

```
# ===== DISCUSSION LOOP (Complete Detail) =====

DISCUSSION_LOOP_START:

# Facilitator Decision Node
facilitator_decide(contributions[], round_number, convergence_metrics)
  cost: {
    phase: "facilitator_orchestration",
    estimate: "$0.010",
    model: "sonnet-4.5",
    cache_hit_rate: "0%"
  }
  guards: {
    valid_round: round_number >= 1,
    has_contributions: len(contributions) > 0
  }
  ? {
    action=vote: vote,
    action=moderator: moderator_intervene,
    action=continue: persona_contribute,
    action=clarify: clarification,
    default: END
  }
  -> decision{action, reasoning, next_speaker?, moderator_type?, question?}

# Persona Contribution Node
persona_contribute(decision, round_context, persona_code)
  cost: {
    phase: "persona_contribution",
    estimate: "$0.003-0.015",
    model: "sonnet-4.5",
    cache_hit_rate: "90% (rounds 2+)",
    notes: "Round 1: $0.015 (no cache), Rounds 2+: $0.003 (90% cached)"
  }
  before: {
    current_speaker: decision.next_speaker,
    metrics.phase_costs: start_tracking("persona_contribution")
  }
  guards: {
    valid_speaker: decision.next_speaker in personas,
    cost_check: metrics.total_cost < config.cost_limit
  }
  after: {
    round_number: +1,
    contributions: append(new_contribution),
    metrics.phase_costs: end_tracking("persona_contribution")
  }
  ? {
    success: check_convergence,
    error(cost_exceeded): ->force-> vote
  }
  -> contribution{persona_code, text, round_number, timestamp}

# Convergence Check Node
check_convergence(contribution, round_number, max_rounds)
  cost: {
    phase: "convergence_check",
    estimate: "$0.001",
    model: "haiku-4.5",
    cache_hit_rate: "0%"
  }
  guards: {
    max_rounds_hard_cap: round_number <= 15,
    min_rounds_for_convergence: round_number >= 3 (if checking convergence)
  }
  before: {
    convergence_score: calculate_semantic_similarity(contributions),
    novelty_score: calculate_novelty(current, previous)
  }
  after: {
    should_stop: evaluate_stop_conditions(),
    stop_reason: determine_reason(),
    metrics.convergence_score: convergence_score
  }
  ? {
    should_stop=false AND round<max_rounds AND cost<limit:
      ->loop(DISCUSSION_LOOP_START)-> facilitator_decide,

    should_stop=true OR round>=max_rounds:
      vote,

    error(cost_exceeded):
      ->force-> vote,

    error(hard_cap_reached):
      ->force-> vote
  }
  -> {should_stop, stop_reason, convergence_score}
```

---

## Config Variations & Flow Impact

### Variation 1: Speed Mode (3-5 min target)

**Config changes**:
```
@config.max_rounds: 10 -> 5
  impact: discussion loop runs 50% fewer iterations (-2 min)

@config.convergence_threshold: 0.85 -> 0.75
  impact: easier to converge (exit early more often)

@config.enable_moderator: true -> false
  impact: removes moderator branch from facilitator_decide

@config.min_rounds_before_convergence: 3 -> 2
  impact: can exit after round 2 instead of round 3
```

**Flow impact (L2)**:
```
Before:
  discussion: LOOP_START
    facilitator_decide ? {vote, moderator, continue, clarify}
    contribute -> converge ? {
      should_stop=false AND round<10: ->loop(LOOP_START)->,
      should_stop=true: vote
    }

After:
  discussion: LOOP_START
    facilitator_decide ? {vote, continue, clarify}  # No moderator
    contribute -> converge ? {
      should_stop=false AND round<5: ->loop(LOOP_START)->,  # Max 5
      should_stop=true: vote  # Threshold 0.75
    }
```

**Metrics**:
- Duration: 8-12 min → 3-5 min (-60%)
- Cost: $0.12 → $0.06 (-50%)
- Quality: 85/100 → 70/100 (-15 points)
- Loop iterations: 5-10 → 3-5

---

### Variation 2: Thorough Mode (15-25 min target)

**Config changes**:
```
@config.max_rounds: 10 -> 15
  impact: allows 50% more discussion rounds

@config.convergence_threshold: 0.85 -> 0.90
  impact: stricter convergence (harder to exit early)

@config.min_rounds_before_convergence: 3 -> 5
  impact: forces minimum 5 rounds before convergence check
```

**Flow impact (L2)**:
```
check_convergence ? {
  should_stop=false AND round<15 AND round>=5: ->loop(LOOP_START)->,
  should_stop=true AND convergence_score>=0.90: vote
}
```

**Metrics**:
- Duration: 8-12 min → 15-25 min (+90%)
- Cost: $0.12 → $0.18 (+50%)
- Quality: 85/100 → 92/100 (+7 points)
- Loop iterations: 5-10 → 7-15

---

### Variation 3: Sequential Mode (for debugging)

**Config changes**:
```
@initial_round.type: parallel -> sequential
  impact: changes fork/join to sequential iteration

@voting.vote.type: parallel -> sequential
  impact: changes fork/join to sequential iteration
```

**Flow impact (L2)**:
```
Before (Parallel):
  select_personas -> fork -> initial_round(persona) || 5 -> join -> contributions[5]
  facilitator_decide

After (Sequential):
  select_personas -> contributions[]

  INITIAL_LOOP: FOR EACH persona IN personas[5]:
    initial_round(persona) -> contribution
    after: {contributions: append(contribution)}
    ->loop(INITIAL_LOOP)-> next_persona

  contributions[5] -> facilitator_decide
```

**Metrics**:
- Duration: 8-12 min → 12-18 min (+50%)
- Cost: Same ($0.12)
- Concurrency: 5 parallel → 1 at a time
- Use case: Debugging, rate limit avoidance

---

### Variation 4: Research-Enhanced Mode (NEW)

**Config changes** (requires new nodes):
```
@states.research = {
  type: task,
  agent: ResearchAgent,
  inputs: [sub_problem, information_gaps],
  outputs: [research_results]
}

@setup.edge_after_select = "research"  # Was: initial_round

@facilitator_decide.routes += {
  action=research: research_mid_discussion
}
```

**Flow impact (L2)**:
```
Before:
  setup:
    select_personas -> fork -> initial_round || 5 -> join

After:
  setup:
    select_personas -> research(sub_problem, information_gaps)
    research -> fork -> initial_round || 5 -> join

  discussion:
    facilitator_decide ? {
      action=vote: vote,
      action=research: research_mid_discussion,  # NEW
      action=continue: persona_contribute
    }

    research_mid_discussion(facilitator_question) -> research_results
    research_mid_discussion -> persona_contribute
```

**Metrics**:
- Duration: 8-12 min → 10-15 min (+30%)
- Cost: $0.12 → $0.20 (+$0.08)
- Quality: 85/100 → 90/100 (+5 points)
- New nodes: 2 (research, research_mid_discussion)

---

### Variation 5: Atomic-Only Mode (no sub-problem splitting)

**Config changes**:
```
@config.max_sub_problems: unlimited -> 1
  impact: forces decomposer to create single atomic problem

@decompose.outputs.sub_problems: [1-5] -> [1]
  impact: always returns array of length 1
```

**Flow impact (L1)**:
```
Before (Multi-sub-problem):
  decompose -> SUBPROBLEM_LOOP:
    [sp1: select -> discuss[loop] -> vote -> synth ->loop->]
    [sp2: select -> discuss[loop] -> vote -> synth ->loop->]
    [sp3: select -> discuss[loop] -> vote -> synth]
  -> meta_synth -> END

After (Atomic):
  decompose -> sub_problems[1]
  select -> discuss[loop] -> vote -> synth -> END
  # No meta-synthesis, no sub-problem loop
```

**Flow impact (L2)**:
```
check_next_subproblem(1, 1) ? {
  is_atomic: END  # Always true
}

# next_subproblem node never reached
# meta_synthesis node never reached
```

**Metrics**:
- Duration: 20-40 min (3 SPs) → 8-12 min (1 SP) (-70%)
- Cost: $0.30 (3 SPs) → $0.12 (1 SP) (-60%)
- Nodes executed: ~85 → ~13 (-85%)

---

## Communication Examples

### Example 1: Proposing Flow Change

**Me**: "I propose adding a research phase before discussion for complex problems."

**Current (L2)**:
```
setup:
  select_personas -> fork -> initial_round || 5 -> join -> contributions[5]

discussion: LOOP_START
  initial_round -> facilitator_decide(contributions)
```

**Proposed (L2)**:
```
setup:
  select_personas -> research(sub_problem, information_gaps) -> research_results

  research -> fork -> initial_round || 5 -> join -> contributions[5]

discussion: LOOP_START
  initial_round -> facilitator_decide(contributions, research_results)  # NEW input
```

**Config**:
```yaml
@states.research = {
  type: task,
  agent: ResearchAgent,
  inputs: [sub_problem, information_gaps],
  outputs: [research_results],
  cost: {phase: "external_research", estimate: "$0.08"}
}

@select_personas.edges.COMPLETE = "research"  # Was: initial_round
@research.edges.COMPLETE = "initial_round"

@facilitator_decide.inputs += [research_results]
```

**Impact**:
- Cost: +$0.08 (5-10 web searches)
- Duration: +60-90s
- Quality: +5-10 points (better context)
- Tradeoff: Higher cost/time vs fewer clarification interruptions

**You**: "Approved for complexity≥moderate. Skip for simple."

**Revised (L2 with guard)**:
```
select_personas -> research_router ? {
  complexity>=moderate: research,
  complexity=simple: fork -> initial_round || 5 -> join
}

research -> fork -> initial_round || 5 -> join
```

**Config**:
```yaml
@states.research_router = {
  type: router,
  guards: {
    needs_research: "complexity >= 'moderate'",
    skip_research: "complexity == 'simple'"
  },
  routes: [
    {condition: "needs_research", target: "research"},
    {condition: "skip_research", target: "initial_round"}
  ]
}
```

---

### Example 2: Debugging Loop Exit

**You**: "Session bo1_abc123 stopped at round 2. Why?"

**Me** (trace with L3 detail):
```
Execution trace:

round 1:
  persona_contribute(maria)
    after: {round_number: 2}  # Incremented to 2
    -> contribution

  check_convergence(contribution, round_number=2, max_rounds=10)
    before: {
      convergence_score: calculate() = 0.62
    }
    ? {
      should_stop=false AND round<10: ->loop(LOOP_START)->  # Taken
    }

round 2:
  persona_contribute(zara)
    after: {round_number: 3}  # Incremented to 3
    -> contribution

  check_convergence(contribution, round_number=3, max_rounds=10)
    before: {
      convergence_score: calculate() = 0.89
    }
    guards: {
      min_rounds_for_convergence: round_number >= 3  # TRUE (3 >= 3)
    }
    after: {
      should_stop: evaluate() = true,  # 0.89 > 0.85 AND round >= 3
      stop_reason: "convergence"
    }
    ? {
      should_stop=true: vote  # TAKEN - exit to voting
    }

Issue: Convergence detected at round 3 (score=0.89 > 0.85)
Root cause: Working as designed (min_rounds=3 guard passed)
```

**To require more rounds**:
```
@config.min_rounds_before_convergence: 3 -> 5
  impact: check_convergence guards.min_rounds: round >= 5

OR

@config.convergence_threshold: 0.85 -> 0.95
  impact: requires 0.95 similarity to exit (vs 0.85)
```

---

### Example 3: Cost Optimization

**You**: "How can we reduce cost for simple problems?"

**Me** (analysis with L3 cost metadata):
```
Current cost breakdown (simple problem, L3 detail):

decompose()
  cost: {phase: "decomposition", estimate: "$0.005"}
  actual: $0.005 (4%)

select_personas()
  cost: {phase: "persona_selection", estimate: "$0.008"}
  actual: $0.008 (7%)

fork -> initial_round() || 5 -> join
  cost: {phase: "initial_round", estimate: "$0.045"}
  actual: $0.045 (38%)  ← EXPENSIVE

discussion[3 rounds]:
  facilitator_decide() × 3: $0.030 (25%)
  persona_contribute() × 3: $0.006 (5%)  # Cache hits
  actual: $0.036 (30%)

fork -> vote() || 5 -> join
  cost: {phase: "voting", estimate: "$0.015"}
  actual: $0.015 (13%)

synthesize()
  cost: {phase: "synthesis", estimate: "$0.010"}
  actual: $0.010 (8%)

TOTAL: $0.119

Options:

Option 1: Skip initial round for simple problems
  @initial_round.guards.skip_if_simple = true

  Flow change:
    select_personas -> skip_initial_router ? {
      complexity=simple: facilitator_decide,  # Skip parallel round
      complexity>=moderate: fork -> initial_round || 5 -> join
    }

  Savings: -$0.045 (-38%)
  Impact: Cold start (no opening positions)
  Quality: -5 points

Option 2: Reduce to 3 personas (from 5)
  @select_personas.outputs.personas: [3-5] -> [3]

  Flow change:
    fork -> initial_round() || 3 -> join  # Was: || 5

  Savings: -$0.018 (-15%, 2 fewer persona calls)
  Impact: Fewer perspectives
  Quality: -2 points

Option 3: Use Haiku for facilitator
  @facilitator_decide.cost.model: "sonnet-4.5" -> "haiku-4.5"

  Savings: -$0.007 per call × 3 = -$0.021 (-18% of facilitator cost)
  Impact: Slightly simpler orchestration
  Quality: -1 point

Recommendation: Option 2 (3 personas for simple)
  Best cost/quality tradeoff
```

**Config**:
```yaml
@select_personas.config.persona_count = {
  simple: 3,
  moderate: 4,
  complex: 5
}
```

---

## Quick Reference: Config Changes

| Change | Notation | Flow Impact |
|--------|----------|-------------|
| **Increase max rounds** | `@config.max_rounds: 10 -> 15` | `check_convergence ? {round<15: ->loop->}` |
| **Stricter convergence** | `@config.convergence_threshold: 0.85 -> 0.90` | Harder to exit early (+15% avg rounds) |
| **Disable moderator** | `@config.enable_moderator: false` | Remove moderator branch from `facilitator_decide ?` |
| **Sequential initial** | `@initial_round.type: parallel -> sequential` | `fork -> || 5 -> join` becomes `FOR EACH loop` |
| **Add research phase** | `+ @states.research = {...}` | `select -> research -> initial` |
| **Skip initial if simple** | `+ @initial_round.guards.skip = "simple"` | `router ? {simple: skip, moderate: initial}` |
| **Force atomic** | `@config.max_sub_problems: unlimited -> 1` | `check_next ? {is_atomic: END}` always true |
| **Add cost limit** | `@config.cost_limit_usd: null -> 2.00` | `error(cost_exceeded): ->force-> vote` |
| **Use Haiku** | `@facilitator.cost.model: "sonnet" -> "haiku"` | Same flow, lower cost per call |
| **Reduce personas** | `@select.outputs.personas: [3-5] -> [3]` | `fork -> || 3 -> join` (was `|| 5`) |

---

## Validation Against Real Code

### Validation 1: Discussion Loop

**Code** (`bo1/graph/config.py` lines 127-167):
```python
workflow.add_conditional_edges(
    "facilitator_decide",
    route_facilitator_decision,
    {
        "persona_contribute": "persona_contribute",
        "moderator_intervene": "moderator_intervene",
        "vote": "vote",
        "clarification": "clarification",
        "END": END,
    },
)

workflow.add_edge("persona_contribute", "check_convergence")
workflow.add_edge("moderator_intervene", "check_convergence")

workflow.add_conditional_edges(
    "check_convergence",
    route_convergence_check,
    {
        "facilitator_decide": "facilitator_decide",  # Loop back
        "vote": "vote",
    },
)
```

**v2 Notation**:
```
discussion: LOOP_START

facilitator_decide ? {
  action=vote: vote,
  action=moderator: moderator_intervene,
  action=continue: persona_contribute,
  action=clarify: clarification,
  default: END
}

persona_contribute -> check_convergence
moderator_intervene -> check_convergence

check_convergence ? {
  should_stop=false: ->loop(LOOP_START)-> facilitator_decide,
  should_stop=true: vote
}
```

✅ **Perfect 1:1 mapping**

---

### Validation 2: Multi-Sub-Problem Handling

**Code** (`bo1/graph/config.py` lines 172-184):
```python
workflow.add_conditional_edges(
    "synthesize",
    route_after_synthesis,
    {
        "next_subproblem": "next_subproblem",
        "meta_synthesis": "meta_synthesis",
        "END": END,
    },
)

workflow.add_edge("next_subproblem", "select_personas")
workflow.add_edge("meta_synthesis", END)
```

**Code** (`bo1/graph/routers.py` lines 130-179):
```python
def route_after_synthesis(state) -> Literal["next_subproblem", "meta_synthesis", "END"]:
    total_sub_problems = len(problem.sub_problems)

    if total_sub_problems == 1:
        return "END"  # Atomic

    if sub_problem_index + 1 < total_sub_problems:
        return "next_subproblem"  # More exist
    else:
        return "meta_synthesis"  # All complete
```

**v2 Notation**:
```
synthesize -> check_next_subproblem(sub_problem_index, total_sub_problems)

check_next_subproblem ? {
  total_sub_problems=1: END,
  sub_problem_index+1 < total_sub_problems: next_subproblem,
  sub_problem_index+1 >= total_sub_problems: meta_synthesis
}

next_subproblem ->loop(SUBPROBLEM_LOOP_START)-> select_personas

meta_synthesis -> END
```

✅ **Perfect 1:1 mapping** (with explicit loop label)

---

## Symbol Quick Reference

```
Nodes:
  TaskNode(in) -> out              Single execution
  RouterNode ? {cases}             Decision point (explicit cases)
  fork -> Node || N -> join        Parallel with explicit join
  AggregateNode(in[]) ∑            Collect multiple inputs

Edges:
  A -> B                           Linear flow
  A ->|label| B                    Labeled flow (clarity)
  A ? {case: B}                    Conditional (explicit)
  A ->loop(LABEL)-> B              Loop back (explicit target)
  A ->force-> B                    Forced transition (error)

Data:
  (inputs)                         Node inputs (always show)
  -> outputs                       Node outputs (always show)
  [N]                              Array of N elements
  [N-M]                            Array range
  []                               Variable array
  ?                                Optional

Guards:
  ? (condition)                    Guard on node
  ->|(condition)| target           Guard on edge
  ? {condition: target}            Guard in case

State:
  before: {updates}                Pre-execution state
  after: {updates}                 Post-execution state

Cost:
  cost: {phase, estimate, model}   Cost metadata block

Labels:
  LABEL_NAME:                      Flow label (for loops)
  ->loop(LABEL)->                  Loop to label
```

---

**End of Examples v2.0**

Use v2 notation for all future flow communication - it's explicit, unambiguous, and maps 1:1 to code!
