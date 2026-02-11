# Bo1 Decision Gate Roadmap

## Principle

AI deliberates, human decides. Constraints define the box. Every decision is traceable — what was chosen, why, and what happened next.

---

## Layer 1: Structured Options (P0)

The deliberation produces recommendations but never structures them into comparable options. The human gets a synthesis wall-of-text and no clear "pick one" moment.

### Option Extraction

Cluster persona recommendations into 3-5 distinct options with a comparison matrix.

**What exists:**

- `Recommendation` model — has `confidence`, `conditions`, `alternatives_considered`, `risk_assessment`
- `RecommendationAggregation` — has `consensus_level`, `dissenting_views`, `alternative_approaches`
- `collect_recommendations()` in `bo1/orchestration/voting.py` — returns `list[Recommendation]`

**What to build:**

- `OptionCard` model: `{label, description, supporting_personas, confidence_range, conditions, tradeoffs, risk_summary}`
- Clustering step between `collect_recommendations()` and synthesis — group by approach similarity, extract distinct options
- `OptionComparison.svelte` — side-by-side cards with criteria scoring, integrated into `SynthesisComplete.svelte`

### Decision Matrix

User-weighted criteria with auto-scoring from deliberation evidence.

**What to build:**

- `DecisionMatrix.svelte` — interactive weight sliders per criterion, auto-populated from constraint types + user criteria
- Sensitivity analysis: "if you weight X higher, Option B wins" — computed client-side from existing scores
- Constraint model types (BUDGET, TIME, RESOURCE, REGULATORY, TECHNICAL, ETHICAL) seed the default criteria list

---

## Layer 2: Constraint Enforcement (P1)

Constraints exist (`Constraint` model with typed `ConstraintType` enum + optional `value`) but are only injected at decomposition. Personas and facilitator don't see them.

### Active Constraint Injection

**What exists:**

- `Constraint` model in `bo1/models/problem.py` — type, description, value
- Constraints passed to decomposer prompt only

**What to build:**

- Inject constraints into persona round prompts and facilitator moderation prompts
- Constraint violation flags in synthesis output — "Option A violates BUDGET constraint ($15k > $10k limit)"
- Visual constraint badges on `OptionCard` components (green/yellow/red)

### Dynamic Constraints

Allow constraint updates mid-meeting via the existing interjection mechanism.

**What exists:**

- `POST /{session_id}/raise-hand` endpoint in `backend/api/control.py`
- `user_interjection` / `needs_interjection_response` state fields
- SSE event `user_interjection_raised`

**What to build:**

- Constraint editor panel — add/modify/remove constraints during deliberation
- Route constraint changes through interjection pipeline (reuse `raise-hand` with structured payload)
- Constraint change triggers re-evaluation note in next round's facilitator prompt

---

## Layer 3: Human Choice Capture (P0)

**This is THE missing piece.** Currently no record of what the human actually decided. The meeting ends at synthesis — the most critical moment (the choice) is unrecorded.

### Option Selection

Post-synthesis "I choose Option X because..." interface.

**What exists:**

- `SynthesisComplete.svelte` — the UI integration point where the decision gate lives
- `Action` model — has `lessons_learned`, `went_well`, outcome tracking fields

**What to build:**

- `Decision` DB table: `{id, session_id, user_id, chosen_option, rationale, criteria_weights, tradeoffs_accepted, concerns_overridden, created_at}`
- `DecisionGate.svelte` — appears after synthesis, presents extracted options, captures selection + structured rationale
- API endpoint: `POST /{session_id}/decision` — validates session has completed synthesis, stores decision
- Link `Decision` → `Action` items generated from it

### Rationale Capture

Structured form, not free-text only.

**What to build:**

- Form fields: which criteria mattered most (rank), which tradeoffs accepted (checklist from options), which dissenting views overridden (from `RecommendationAggregation.dissenting_views`), confidence level (slider)
- Optional free-text "additional context"
- Stored as structured JSON on `Decision` record

---

## Layer 4: Decision Memory (P2-P3)

### Outcome Tracking (P2)

Link decisions to real-world outcomes.

**What exists:**

- `Action` model lifecycle: status tracking, `actual_start_date`, `actual_end_date`, `failure_reason_category`
- Post-mortem fields: `lessons_learned`, `went_well`
- `context_ids` on `CreateSessionRequest` — cross-meeting context already works (`{meetings: [...], actions: [...]}`)

**What to build:**

- `DecisionOutcome` model: `{decision_id, outcome_status, outcome_notes, surprise_factor, updated_at}`
- 30-day follow-up prompt — nudge user to record what happened
- Decision → Action → Outcome chain visualization

### Pattern Detection (P3)

Aggregate analysis across decisions.

**What to build:**

- Confidence calibration: user's stated confidence vs actual outcomes over time
- Constraint accuracy: were constraints realistic? (budget estimates vs actuals)
- Bias pattern flags: consistent overweighting of certain criteria, systematic overconfidence
- Dashboard widget on user home — "Your decision patterns" summary

---

## Layer 5: Edge Cases (P3)

### Deadlock Resolution

When `RecommendationAggregation.consensus_level` is `WEAK` or `NO_CONSENSUS`:

**What to build:**

- Structured resolution UI: forced ranking, pairwise comparison, or "what would need to be true for you to pick X?"
- Option to request additional deliberation round focused on the split
- Deadlock flag visible in meeting history

### Groupthink Warning

When consensus is `UNANIMOUS` + high average confidence:

**What to build:**

- Automatic flag: "All experts agree with high confidence — consider what they might be missing"
- Prompt user to identify one assumption that could be wrong
- Pre-mortem exercise: "Imagine this decision failed. Why?"

---

## Priority Table

| Feature                        | Priority | Effort | Impact   | Dependencies                        |
| ------------------------------ | -------- | ------ | -------- | ----------------------------------- |
| Option Extraction + OptionCard | P0       | M      | High     | Clustering logic, new model         |
| Decision Gate + Choice Capture | P0       | M      | Critical | Decision table, DecisionGate.svelte |
| Rationale Capture (structured) | P0       | S      | High     | Decision Gate                       |
| Decision Matrix (weighted)     | P0       | M      | High     | OptionCard                          |
| Active Constraint Injection    | P1       | S      | Medium   | Prompt template changes             |
| Dynamic Constraints            | P1       | M      | Medium   | Interjection pipeline               |
| Outcome Tracking               | P2       | M      | High     | Decision table, follow-up system    |
| Deadlock Resolution UI         | P3       | M      | Medium   | Consensus level detection           |
| Groupthink Warning             | P3       | S      | Medium   | Consensus + confidence thresholds   |
| Pattern Detection Dashboard    | P3       | L      | High     | Outcome data accumulation           |

**Effort:** S = < 1 week, M = 1-2 weeks, L = 3+ weeks

**Recommended build order:** Decision Gate → Option Extraction → Rationale Capture → Decision Matrix → Constraint Injection → Dynamic Constraints → Outcome Tracking → Edge Cases → Pattern Detection
