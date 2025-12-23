# SSE Event Schema Contracts

This document defines the Server-Sent Events (SSE) schema contracts for Board of One.

## Overview

All SSE events follow a standard envelope format and are published via Redis PubSub for real-time streaming.

**Source files:**
- Python schemas: `bo1/events/schemas.py`
- TypeScript interfaces: `frontend/src/lib/api/sse-events.ts`
- Event formatters: `backend/api/events.py`

## Base Envelope

Every SSE event has this structure:

```json
{
  "event_type": "string",
  "session_id": "string",
  "sequence": 1,
  "timestamp": "2025-01-01T00:00:00.000000+00:00",
  "data": { ... },
  "event_version": 1
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | Yes | Event type identifier |
| `session_id` | string | Yes | Session identifier (e.g., `bo1_abc123`) |
| `sequence` | integer | Yes | Monotonic sequence number for ordering |
| `timestamp` | string | Yes | ISO 8601 timestamp with timezone |
| `data` | object | Yes | Event-specific payload |
| `event_version` | integer | Yes | Schema version (currently `1`) |

## Event Lifecycle

```
session_started
    │
    ▼
decomposition_started → decomposition_complete
    │
    ▼
persona_selection_started → persona_selected (×N) → persona_selection_complete
    │
    ▼
subproblem_started (×N parallel)
    │
    ├─► initial_round_started
    │       │
    │       ▼
    │   contribution (×experts)
    │       │
    │       ▼
    │   convergence
    │       │
    │       ▼
    │   round_started → contribution (×experts) → convergence (loop)
    │       │
    │       ▼
    │   voting_started → persona_vote (×experts) → voting_complete
    │       │
    │       ▼
    │   synthesis_started → synthesis_complete
    │       │
    │       ▼
    └─► subproblem_complete
            │
            ▼
meta_synthesis_started → meta_synthesis_complete
            │
            ▼
        complete
```

## Event Types Reference

### Session Events

#### `session_started`
Emitted when a deliberation session starts.

```json
{
  "session_id": "bo1_abc123",
  "problem_statement": "Should we expand into European markets?",
  "max_rounds": 6,
  "user_id": "user_xyz"
}
```

### Decomposition Events

#### `decomposition_started`
Emitted when problem decomposition begins.

```json
{
  "session_id": "bo1_abc123"
}
```

#### `decomposition_complete`
Emitted when problem decomposition completes.

```json
{
  "session_id": "bo1_abc123",
  "sub_problems": [
    {
      "id": "sp1",
      "goal": "Analyze market opportunity",
      "rationale": "Understanding market size is critical",
      "complexity_score": 7,
      "dependencies": []
    }
  ],
  "count": 3
}
```

### Persona Selection Events

#### `persona_selection_started`
Emitted when expert selection begins.

```json
{
  "session_id": "bo1_abc123"
}
```

#### `persona_selected`
Emitted for each expert selected.

```json
{
  "session_id": "bo1_abc123",
  "persona": {
    "code": "CFO",
    "name": "Zara Kim",
    "display_name": "Zara Kim (CFO)",
    "archetype": "Financial Strategy Advisor",
    "domain_expertise": ["financial modeling", "risk assessment"]
  },
  "rationale": "Financial expertise crucial for market expansion analysis",
  "order": 1,
  "sub_problem_index": 0
}
```

#### `persona_selection_complete`
Emitted when all experts are selected.

```json
{
  "session_id": "bo1_abc123",
  "personas": ["CFO", "CMO", "CTO"],
  "count": 3,
  "sub_problem_index": 0
}
```

### Sub-Problem Events

#### `subproblem_started`
Emitted when a sub-problem deliberation begins.

```json
{
  "session_id": "bo1_abc123",
  "sub_problem_index": 0,
  "sub_problem_id": "sp1",
  "goal": "Analyze market opportunity",
  "total_sub_problems": 3
}
```

#### `subproblem_complete`
Emitted when a sub-problem deliberation completes.

```json
{
  "session_id": "bo1_abc123",
  "sub_problem_index": 0,
  "sub_problem_id": "sp1",
  "goal": "Analyze market opportunity",
  "synthesis": "The analysis indicates...",
  "cost": 0.42,
  "duration_seconds": 45.2,
  "expert_panel": ["CFO", "CMO"],
  "contribution_count": 8,
  "expert_summaries": {
    "CFO": "Focused on financial viability...",
    "CMO": "Emphasized brand positioning..."
  }
}
```

### Round Events

#### `initial_round_started`
Emitted when the first round of a sub-problem begins.

```json
{
  "session_id": "bo1_abc123",
  "round_number": 1,
  "experts": ["CFO", "CMO", "CTO"]
}
```

#### `round_started`
Emitted when a subsequent round begins.

```json
{
  "session_id": "bo1_abc123",
  "round_number": 2
}
```

#### `contribution`
Emitted when an expert makes a contribution.

```json
{
  "session_id": "bo1_abc123",
  "persona_code": "CFO",
  "persona_name": "Zara Kim",
  "content": "From a financial perspective, we need to consider...",
  "round": 1,
  "contribution_type": "initial",
  "archetype": "Financial Strategy Advisor",
  "domain_expertise": ["financial modeling"],
  "sub_problem_index": 0,
  "summary": {
    "concise": "CFO recommends phased market entry",
    "looking_for": "ROI projections and risk assessment",
    "value_added": "Financial framework for decision",
    "concerns": ["Currency volatility", "Regulatory compliance"],
    "questions": ["What is the expected payback period?"]
  }
}
```

#### `moderator_intervention`
Emitted when a moderator intervenes in the discussion.

```json
{
  "session_id": "bo1_abc123",
  "moderator_type": "contrarian",
  "content": "Let me challenge the assumption that...",
  "trigger_reason": "Discussion becoming too one-sided",
  "round": 2
}
```

### Convergence Events

#### `convergence`
Emitted after each round to report convergence status.

```json
{
  "session_id": "bo1_abc123",
  "score": 0.72,
  "converged": false,
  "round": 2,
  "threshold": 0.85,
  "should_stop": false,
  "stop_reason": null,
  "max_rounds": 6,
  "sub_problem_index": 0,
  "novelty_score": 0.45,
  "conflict_score": 0.20,
  "drift_events": 0
}
```

### Voting Events

#### `voting_started`
Emitted when the voting phase begins.

```json
{
  "session_id": "bo1_abc123",
  "experts": ["CFO", "CMO", "CTO"],
  "count": 3
}
```

#### `persona_vote`
Emitted for each expert's recommendation.

```json
{
  "session_id": "bo1_abc123",
  "persona_code": "CFO",
  "persona_name": "Zara Kim",
  "recommendation": "Proceed with phased market entry starting Q2",
  "confidence": 0.85,
  "reasoning": "The financial analysis supports a cautious approach...",
  "conditions": ["Secure local partnerships", "Hedge currency exposure"]
}
```

#### `voting_complete`
Emitted when all votes are collected.

```json
{
  "session_id": "bo1_abc123",
  "votes_count": 3,
  "consensus_level": "moderate"
}
```

### Synthesis Events

#### `synthesis_started`
Emitted when synthesis begins.

```json
{
  "session_id": "bo1_abc123"
}
```

#### `synthesis_complete`
Emitted when sub-problem synthesis completes.

```json
{
  "session_id": "bo1_abc123",
  "synthesis": "## Summary\n\nThe expert panel recommends...",
  "word_count": 450,
  "sub_problem_index": 0
}
```

#### `meta_synthesis_started`
Emitted when meta-synthesis across all sub-problems begins.

```json
{
  "session_id": "bo1_abc123",
  "sub_problem_count": 3,
  "total_contributions": 24,
  "total_cost": 1.26
}
```

#### `meta_synthesis_complete`
Emitted when the final meta-synthesis completes.

```json
{
  "session_id": "bo1_abc123",
  "synthesis": "# Executive Summary\n\nAfter comprehensive deliberation...",
  "word_count": 850
}
```

### Completion Events

#### `complete`
Emitted when the entire deliberation completes.

```json
{
  "session_id": "bo1_abc123",
  "final_output": "# Executive Summary\n\n...",
  "total_cost": 1.54,
  "total_rounds": 4
}
```

### Error Events

#### `error`
Emitted when an error occurs.

```json
{
  "session_id": "bo1_abc123",
  "error": "LLM rate limit exceeded",
  "error_type": "RateLimitError"
}
```

### Clarification Events

#### `clarification_required`
Emitted when clarification is needed before deliberation.

```json
{
  "session_id": "bo1_abc123",
  "questions": [
    {
      "question": "What is your target market size?",
      "reason": "Needed for financial projections",
      "priority": "high"
    }
  ],
  "phase": "pre_deliberation",
  "reason": "Critical information gaps identified",
  "question_count": 2
}
```

#### `clarification_requested`
Emitted when clarification is requested mid-deliberation.

```json
{
  "session_id": "bo1_abc123",
  "question": "What is your timeline for implementation?",
  "reason": "Experts need timeline for recommendations",
  "round": 2
}
```

#### `clarification_answered`
Emitted when user provides clarification.

```json
{
  "session_id": "bo1_abc123",
  "question": "What is your timeline for implementation?",
  "answer": "We aim to launch within 18 months",
  "round": 2
}
```

### Context Events

#### `context_insufficient`
Emitted when experts lack sufficient context.

```json
{
  "session_id": "bo1_abc123",
  "meta_ratio": 0.65,
  "expert_questions": [
    "What is the current market share?",
    "What are the competitive dynamics?"
  ],
  "reason": "Experts unable to provide substantive analysis",
  "round_number": 2,
  "sub_problem_index": 0,
  "choices": [
    {
      "id": "provide_more",
      "label": "Provide Additional Details",
      "description": "Answer the questions our experts have raised"
    },
    {
      "id": "continue",
      "label": "Continue with Available Information",
      "description": "Proceed with best-effort analysis"
    },
    {
      "id": "end",
      "label": "End Meeting",
      "description": "Generate summary with current insights"
    }
  ],
  "timeout_seconds": 120,
  "timeout_default": "continue"
}
```

### Quality Events

#### `quality_metrics_update`
Emitted with meeting quality metrics after each round.

```json
{
  "session_id": "bo1_abc123",
  "round_number": 2,
  "exploration_score": 0.75,
  "convergence_score": 0.60,
  "focus_score": 0.90,
  "novelty_score": 0.45,
  "meeting_completeness_index": 0.68,
  "missing_aspects": ["risk assessment", "timeline"],
  "facilitator_guidance": "Consider exploring risk factors"
}
```

### Cost Events

#### `phase_cost_breakdown`
Emitted with per-phase cost breakdown.

```json
{
  "session_id": "bo1_abc123",
  "phase_costs": {
    "decomposition": 0.05,
    "persona_selection": 0.08,
    "deliberation": 1.20,
    "synthesis": 0.15
  },
  "total_cost": 1.48
}
```

### Node Events

#### `node_start`
Emitted when a graph node starts execution.

```json
{
  "node": "decompose_node",
  "session_id": "bo1_abc123"
}
```

#### `node_end`
Emitted when a graph node completes.

```json
{
  "node": "decompose_node",
  "session_id": "bo1_abc123",
  "duration_ms": 2450.5
}
```

### Facilitator Events

#### `facilitator_decision`
Emitted when the facilitator makes a decision.

```json
{
  "session_id": "bo1_abc123",
  "action": "continue",
  "reasoning": "Discussion still generating novel insights",
  "round": 2
}
```

### Expert Event Buffering

The SSE stream implements micro-batching optimization for expert contribution events to reduce frame volume and network overhead.

#### Buffer Behavior

- **Buffer window:** 50ms per-expert
- **Per-expert queuing:** Events are grouped by `expert_id`
- **Merge pattern:** `expert_started` → `expert_reasoning` → `expert_conclusion` → `expert_contribution_complete`

When three consecutive events from the same expert follow the standard contribution sequence, they are merged into a single `expert_contribution_complete` event.

#### Merged Event Schema

#### `expert_contribution_complete`
Emitted when buffered expert events are merged (optimization).

```json
{
  "session_id": "bo1_abc123",
  "expert_id": "CFO",
  "round": 2,
  "phase": "thinking",
  "reasoning": "From a financial perspective, we need to consider ROI timelines...",
  "confidence_score": 0.85,
  "recommendation": "Proceed with phased market entry",
  "merged": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| `expert_id` | string | Expert identifier (persona code) |
| `round` | integer | Current deliberation round |
| `phase` | string | Expert's processing phase |
| `reasoning` | string | Expert's reasoning/analysis |
| `confidence_score` | float | Expert's confidence (0.0-1.0) |
| `recommendation` | string | Expert's recommendation |
| `merged` | boolean | Always `true` for merged events |

#### Critical Event Bypass

The following event types **flush the buffer immediately** and bypass buffering:

- `round_start` / `round_end` - Round boundaries
- `subproblem_waiting` - Sub-problem state changes
- `synthesis_complete` / `meta_synthesis_complete` - Synthesis events
- `meeting_complete` / `complete` - Session completion
- `facilitator_decision` - Facilitator actions
- `error` - Error events

These events cannot be buffered because they represent state transitions that clients must receive immediately.

#### Client Handling Guidance

Clients may receive **either** merged or unmerged event sequences depending on timing:

**Unmerged sequence (3 events):**
```
expert_started → expert_reasoning → expert_conclusion
```

**Merged sequence (1 event):**
```
expert_contribution_complete
```

**Recommended client implementation:**
1. Handle both `expert_contribution_complete` and the individual events (`expert_started`, `expert_reasoning`, `expert_conclusion`)
2. Check for the `merged: true` field to identify merged events
3. For UI updates, treat `expert_contribution_complete` as equivalent to receiving all three individual events
4. If building a replay mechanism, account for both patterns

## Event Count Summary

| Category | Events |
|----------|--------|
| Session | 1 |
| Decomposition | 2 |
| Persona Selection | 3 |
| Sub-Problem | 2 |
| Round | 3 |
| Convergence | 1 |
| Voting | 3 |
| Synthesis | 4 |
| Completion | 1 |
| Error | 1 |
| Clarification | 3 |
| Context | 1 |
| Quality | 1 |
| Cost | 1 |
| Node | 2 |
| Facilitator | 1 |
| Expert Buffering | 1 |
| **Total** | **31** |

## JSON Schema Export

Use `bo1.events.schemas.get_event_json_schemas()` to get JSON Schema definitions for all typed events:

```python
from bo1.events.schemas import get_event_json_schemas

schemas = get_event_json_schemas()
# Returns: {"session_started": {...}, "contribution": {...}, ...}
```

## Schema Evolution

### Overview

SSE events include an `event_version` field for forward compatibility. Clients should check this field and handle version mismatches gracefully.

### Version Negotiation

**Request Header:** `Accept-SSE-Version`
- Clients can request a specific version via this header
- Format: integer (e.g., `Accept-SSE-Version: 1`)
- If omitted, defaults to current version

**Response Header:** `X-SSE-Schema-Version`
- Server returns current schema version in response headers
- Clients should check this on stream connect

### Breaking vs Non-Breaking Changes

**Non-Breaking (additive):**
- New event types
- New optional fields in existing events
- New enum values (if client handles unknown values)

**Breaking (requires version bump):**
- Removing event types
- Removing required fields
- Changing field types
- Renaming fields

### Deprecation Lifecycle

1. **Announce** - Field/event marked deprecated in docs, `SSE_DEPRECATED_FIELDS` updated
2. **Warn** - 90 days: Events include `_deprecated` metadata, console warnings in clients
3. **Sunset** - 180 days: Field/event removed, version incremented

### Version Compatibility Matrix

| Client Version | Server Version | Behavior |
|----------------|----------------|----------|
| 1 | 1 | Full compatibility |
| 1 | 2+ | Works (additive changes only), client logs warnings for unknown fields |
| 2+ | 1 | Client should handle gracefully (missing new fields) |

### Migration Guide Template

When bumping versions:

1. Document all changes in Version History
2. Update `SSE_SCHEMA_VERSION` in `backend/api/constants.py`
3. Update `EXPECTED_SSE_VERSION` in `frontend/src/lib/api/sse-events.ts`
4. Add deprecated field mappings to `SSE_DEPRECATED_FIELDS`
5. Update TypeScript interfaces for new/changed fields
6. Run test suite to verify backwards compatibility

## Grafana Queries for Cost Analysis

The `api_costs` table stores per-call cost data with `prompt_type` in the JSONB `metadata` column.

### Cache Hit Rate by Prompt Type

```sql
SELECT
  metadata->>'prompt_type' AS prompt_type,
  COUNT(*) AS total_calls,
  SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits,
  AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) AS cache_hit_rate,
  SUM(total_cost) AS total_cost,
  SUM(COALESCE(cost_without_optimization, total_cost) - total_cost) AS cost_saved
FROM api_costs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND metadata->>'prompt_type' IS NOT NULL
GROUP BY 1
ORDER BY total_calls DESC;
```

### Valid prompt_type Values

| Value | Description |
|-------|-------------|
| `persona_contribution` | Expert persona deliberation responses |
| `facilitator_decision` | Facilitator round decisions |
| `synthesis` | Final synthesis generation |
| `decomposition` | Problem decomposition |
| `context_collection` | Context gathering |
| `clarification` | Clarification handling |
| `research_summary` | Research result summarization |
| `research_detection` | Proactive research detection |
| `task_extraction` | Task extraction from synthesis |
| `embedding` | Voyage AI embeddings |
| `search` | Brave/Tavily web search |
| `contribution_summary` | Contribution summarization |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2025-01 | Initial schema contract |
