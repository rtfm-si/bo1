# Voting → Recommendations Migration Plan

**Date**: 2025-01-15
**Status**: Planning
**Goal**: Replace binary voting (approve/reject) with flexible expert recommendations

---

## Problem Statement

Current voting system forces experts into binary YES/NO/CONDITIONAL/ABSTAIN choices, losing rich information:

**Current behavior** (with director compensation problem):

- Expert provides detailed recommendation in `<reasoning>`: "Use 60% salary, 40% dividends hybrid"
- Parser looks for "approve/reject" keywords in `<decision>` tag
- Finds neither → defaults to ABSTAIN
- Result: 4 experts, 4 abstains, but synthesis says "no dissenting views" (contradiction!)

**Root cause**: Mismatch between:

- **Strategy problems**: "What compensation structure?" → needs recommendation
- **Binary problems**: "Should we invest in X?" → needs yes/no
- **Current model**: Only supports binary (VoteDecision enum)

---

## Solution: Flexible Recommendation Model

Support BOTH problem types by treating everything as recommendations:

### User Question → Internal Representation

| User asks                      | Deliberation explores               | Expert recommends                                                 |
| ------------------------------ | ----------------------------------- | ----------------------------------------------------------------- |
| "Should we invest in X?"       | X, alternatives, timing, conditions | "Yes, invest in X" OR "No, invest in Y instead" OR "50/50 hybrid" |
| "What compensation structure?" | Salary, dividends, hybrids, timing  | "60% salary, 40% dividends" OR "Pure salary until profitable"     |
| "SEO or paid ads?"             | SEO, paid ads, hybrid, neither      | "Start with SEO, add paid later" OR "70/30 split"                 |

**Key insight**: Even binary questions should allow non-binary answers. An expert might recommend "Neither - do Z first."

---

## Architecture Changes

### 1. Data Model (bo1/models/votes.py)

**Before (Vote model with enum)**:

```python
class VoteDecision(str, Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"
    CONDITIONAL = "conditional"

class Vote(BaseModel):
    persona_code: str
    persona_name: str
    decision: VoteDecision  # ← Restrictive enum
    reasoning: str
    confidence: float
    conditions: list[str]
    weight: float
```

**After (Recommendation model - flexible)**:

```python
class Recommendation(BaseModel):
    """Expert recommendation with full flexibility.

    Supports both binary decisions ("Approve X") and strategy
    recommendations ("60% X, 40% Y hybrid").
    """
    persona_code: str
    persona_name: str
    recommendation: str  # ← Free-form recommendation
    reasoning: str  # Full explanation (2-3 paragraphs)
    confidence: float  # 0.0-1.0
    conditions: list[str]  # Conditions/caveats
    weight: float = 1.0

    # Optional fields for richer recommendations
    alternatives_considered: list[str] | None = None  # Other options discussed
    risk_assessment: str | None = None  # Key risks identified

class RecommendationAggregation(BaseModel):
    """Aggregated recommendations (AI-synthesized)."""
    total_recommendations: int
    consensus_recommendation: str  # AI-synthesized from all recommendations
    confidence_level: str  # "high" | "medium" | "low"
    alternative_approaches: list[str]  # Distinct alternatives proposed
    critical_conditions: list[str]  # Conditions mentioned by multiple experts
    dissenting_views: list[str]  # Minority perspectives to preserve
    confidence_weighted_score: float  # For metrics
    average_confidence: float
```

**Migration**:

- ✅ Delete `VoteDecision` enum entirely
- ✅ Rename `Vote` → `Recommendation`
- ✅ Rename `VoteAggregation` → `RecommendationAggregation`
- ✅ Delete `aggregate_votes()` mechanical function
- ✅ Keep only `aggregate_votes_ai()` (rename to `aggregate_recommendations_ai()`)

---

### 2. Voting Prompts (bo1/prompts/reusable_prompts.py)

**Before (forcing approve/reject)**:

```python
<decision>approve | reject | conditional | abstain</decision>
```

**After (flexible recommendation)**:

```python
<recommendation>
Your specific recommendation (be concrete and actionable):
- For binary questions: "Approve X" or "Reject X, pursue Y instead"
- For strategy questions: "60% salary, 40% dividends" or "Hybrid approach: ..."
- Always consider alternatives, not just yes/no to the stated option
</recommendation>

<reasoning>
2-3 paragraphs explaining your recommendation:
- Why this approach is best from your expert perspective
- What alternatives you considered and why you ruled them out
- Key risks, opportunities, and trade-offs
- How the deliberation shaped your thinking
</reasoning>

<confidence>high | medium | low</confidence>

<conditions>
Critical conditions or caveats (one per line):
- Condition 1
- Condition 2

If none, write "No conditions."
</conditions>
```

**Key changes**:

- `<decision>` → `<recommendation>` (semantic clarity)
- Explicitly encourage considering alternatives
- No forced keywords - experts speak naturally

---

### 3. Response Parser (bo1/llm/response_parser.py)

**Before (keyword matching)**:

```python
def parse_vote_decision(decision_str: str | None) -> VoteDecision:
    if "approve" in decision_lower or "yes" in decision_lower:
        return VoteDecision.YES
    elif "reject" in decision_lower or "no" in decision_lower:
        return VoteDecision.NO
    # ... falls through to ABSTAIN
```

**After (extract text directly)**:

```python
def parse_recommendation_from_response(response_content: str, persona: Any) -> Recommendation:
    """Parse recommendation from LLM response.

    No keyword matching - just extract structured fields.
    """
    # Extract recommendation text
    recommendation = extract_xml_tag(response_content, "recommendation")
    if not recommendation:
        logger.error(f"Missing <recommendation> tag from {persona.name}")
        recommendation = "[No recommendation provided]"

    # Extract reasoning
    reasoning = extract_xml_tag(response_content, "reasoning")
    if not reasoning:
        reasoning = "[No reasoning provided]"

    # Extract confidence
    confidence_str = extract_xml_tag(response_content, "confidence")
    confidence = parse_confidence_level(confidence_str)  # high/medium/low → 0.85/0.6/0.3

    # Extract conditions
    conditions_str = extract_xml_tag(response_content, "conditions")
    conditions = parse_conditions(conditions_str)

    return Recommendation(
        persona_code=persona.code,
        persona_name=persona.name,
        recommendation=recommendation,  # ← Store as-is, no parsing
        reasoning=reasoning,
        confidence=confidence,
        conditions=conditions,
        weight=1.0,
    )
```

**Key changes**:

- No keyword matching logic (source of bugs)
- Trust the LLM to provide the recommendation
- Validation happens in AI aggregator, not parser

---

### 4. Voting Orchestration (bo1/orchestration/voting.py)

**Before**:

- `collect_votes()` → returns list[Vote]
- `aggregate_votes()` → mechanical counting (yes/no/conditional)
- `aggregate_votes_ai()` → AI synthesis (exists but not used in graph!)

**After**:

- Rename `collect_votes()` → `collect_recommendations()`
- Delete `aggregate_votes()` entirely
- Rename `aggregate_votes_ai()` → `aggregate_recommendations_ai()`
- **Wire into graph** (currently only in demo.py!)

```python
async def collect_recommendations(
    state: DeliberationState,
    broker: PromptBroker,
) -> tuple[list[Recommendation], list[LLMResponse]]:
    """Collect recommendations from all personas (parallel)."""
    # ... existing logic, just rename Vote → Recommendation
    pass

async def aggregate_recommendations_ai(
    recommendations: list[Recommendation],
    discussion_context: str,
    broker: PromptBroker,
) -> tuple[RecommendationAggregation, LLMResponse]:
    """Aggregate recommendations using AI synthesis (Haiku).

    This understands:
    - Binary recommendations: "Approve X" vs "Reject X"
    - Strategy recommendations: "60/40 hybrid" vs "Pure salary"
    - Complex recommendations: "Not yet, do Y first, then X"
    """
    # Format recommendations for AI
    formatted = _format_recommendations_for_ai(recommendations)

    # AI synthesis prompt (updated for flexibility)
    system_prompt = """Synthesize expert recommendations into a consensus.

    Recommendations may be:
    - Binary: "Approve X" or "Reject X, do Y instead"
    - Strategy: "60% salary, 40% dividends"
    - Complex: "Not yet - do A first, then B"

    Your job:
    1. Identify the consensus recommendation (what most experts agree on)
    2. List alternative approaches (minority views worth preserving)
    3. Extract critical conditions (mentioned by multiple experts)
    4. Assess confidence level (high if >80% agreement, medium if >60%, low otherwise)

    Output JSON:
    {
      "consensus_recommendation": "...",
      "confidence_level": "high" | "medium" | "low",
      "alternative_approaches": ["...", "..."],
      "critical_conditions": ["...", "..."],
      "dissenting_views": ["PersonaName: reasoning", ...]
    }
    """

    # ... existing AI call logic
    pass
```

---

### 5. Graph Nodes (bo1/graph/nodes.py)

**Update vote_node → recommendation_node**:

```python
async def recommendation_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect recommendations from all personas."""
    from bo1.orchestration.voting import collect_recommendations

    v1_state = graph_state_to_deliberation_state(state)
    broker = PromptBroker()

    # Collect recommendations (not votes)
    recommendations, llm_responses = await collect_recommendations(
        state=v1_state,
        broker=broker
    )

    # Track cost
    # ... existing cost tracking logic

    # Store recommendations (not votes)
    return {
        "recommendations": [r.model_dump() for r in recommendations],
        "phase": DeliberationPhase.VOTING,  # Keep enum name for now
        "metrics": metrics,
    }
```

**Update synthesize_node to use AI aggregation**:

```python
async def synthesize_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Synthesize final recommendation using AI aggregation."""
    from bo1.orchestration.voting import aggregate_recommendations_ai

    problem = state.get("problem")
    contributions = state.get("contributions", [])
    recommendations_dicts = state.get("recommendations", [])

    # Convert dicts back to Recommendation objects
    from bo1.models.votes import Recommendation
    recommendations = [Recommendation(**r) for r in recommendations_dicts]

    # Format discussion context
    discussion_history = _format_discussion_history(contributions)

    # AI aggregation (not template-based!)
    broker = PromptBroker()
    aggregation, agg_response = await aggregate_recommendations_ai(
        recommendations=recommendations,
        discussion_context=discussion_history,
        broker=broker,
    )

    # Build synthesis report using aggregation
    synthesis_report = _build_synthesis_from_aggregation(
        problem=problem,
        aggregation=aggregation,
        recommendations=recommendations,
    )

    # Add disclaimer
    synthesis_report += "\n\n⚠️ AI-generated for learning purposes only..."

    # Track cost
    # ... existing cost tracking

    return {
        "synthesis": synthesis_report,
        "recommendation_aggregation": aggregation.model_dump(),
        "phase": DeliberationPhase.COMPLETE,
        "metrics": metrics,
    }
```

---

### 6. State Management (bo1/graph/state.py)

**Update DeliberationGraphState**:

```python
class DeliberationGraphState(TypedDict, total=False):
    # ... existing fields
    recommendations: list[dict]  # Changed from 'votes'
    recommendation_aggregation: dict | None  # AI-aggregated result
```

**Update DeliberationState (v1 compatibility)**:

```python
class DeliberationState(BaseModel):
    # ... existing fields
    recommendations: list[Recommendation] = Field(default_factory=list)  # Changed from votes
```

---

### 7. Exports (bo1/export/)

**Update JSON exports**:

```json
{
  "session_id": "...",
  "problem": "...",
  "recommendations": [
    {
      "persona_name": "Maria Santos",
      "recommendation": "60% salary, 40% dividends",
      "reasoning": "...",
      "confidence": 0.85,
      "conditions": [...]
    }
  ],
  "consensus": {
    "recommendation": "Hybrid approach: 60% salary, 40% dividends",
    "confidence_level": "high",
    "critical_conditions": [...],
    "alternative_approaches": [...]
  }
}
```

**Update Markdown reports**:

```markdown
## Expert Recommendations

### Maria Santos (Finance Expert)

**Recommendation**: 60% salary, 40% dividends hybrid
**Confidence**: High (85%)
**Reasoning**: [...]
**Conditions**:

- Review quarterly
- Adjust if company becomes profitable

---

## Consensus Recommendation

**Approach**: Hybrid compensation structure (60% salary, 40% dividends)
**Confidence**: High
**Supported by**: Maria, Aisha, Catherine (75% agreement)

**Critical Conditions**:

- Quarterly review and rebalancing
- Legal compliance verification

**Alternative Approach** (Ahmad):
Pure salary until profitability reached
```

---

## Implementation Plan

### Phase 1: Models & Core Logic (1-2 hours)

- [ ] Update `bo1/models/votes.py`
  - [ ] Rename `Vote` → `Recommendation`
  - [ ] Delete `VoteDecision` enum
  - [ ] Update `Recommendation` fields
  - [ ] Rename `VoteAggregation` → `RecommendationAggregation`
  - [ ] Delete `aggregate_votes()` function
  - [ ] Rename `aggregate_votes_ai()` → `aggregate_recommendations_ai()`

### Phase 2: Prompts & Parsing (1 hour)

- [ ] Update `bo1/prompts/reusable_prompts.py`
  - [ ] Replace voting prompt with recommendation prompt
  - [ ] Update XML structure (`<decision>` → `<recommendation>`)
- [ ] Update `bo1/llm/response_parser.py`
  - [ ] Rename `parse_vote_from_response()` → `parse_recommendation_from_response()`
  - [ ] Remove keyword matching logic
  - [ ] Extract `<recommendation>` tag directly
- [ ] Delete `bo1/utils/vote_parsing.py` entirely (no longer needed)

### Phase 3: Orchestration (1 hour)

- [ ] Update `bo1/orchestration/voting.py`
  - [ ] Rename `collect_votes()` → `collect_recommendations()`
  - [ ] Update function signatures
  - [ ] Update `aggregate_recommendations_ai()` prompt for flexibility

### Phase 4: Graph Integration (1 hour)

- [ ] Update `bo1/graph/nodes.py`
  - [ ] Rename `vote_node()` → `recommendation_node()`
  - [ ] Update `synthesize_node()` to use AI aggregation
  - [ ] Wire `aggregate_recommendations_ai()` into synthesis
- [ ] Update `bo1/graph/state.py`
  - [ ] Rename `votes` → `recommendations` in TypedDict
- [ ] Update `bo1/graph/config.py`
  - [ ] Rename node: `vote` → `recommendation`

### Phase 5: Tests (2 hours)

- [ ] Update test files
  - [ ] Rename `tests/test_vote_*.py` → `tests/test_recommendation_*.py`
  - [ ] Update all Vote references → Recommendation
  - [ ] Add tests for both problem types:
    - [ ] Binary: "Should we invest in X?"
    - [ ] Strategy: "What compensation structure?"
  - [ ] Test AI aggregation with diverse recommendations
- [ ] Delete obsolete tests
  - [ ] Remove tests for `VoteDecision` enum parsing
  - [ ] Remove tests for `aggregate_votes()` mechanical counting

### Phase 6: Exports & UI (1 hour)

- [ ] Update `bo1/export/`
  - [ ] JSON: votes → recommendations
  - [ ] Markdown: Update report templates
- [ ] Update `bo1/interfaces/console.py`
  - [ ] Display recommendations (not votes)
  - [ ] Show consensus recommendation

---

## Testing Strategy

### Unit Tests

```python
# Test recommendation parsing
def test_parse_binary_recommendation():
    content = """
    <recommendation>Approve investment in X</recommendation>
    <reasoning>Strong ROI potential...</reasoning>
    <confidence>high</confidence>
    """
    rec = parse_recommendation_from_response(content, persona)
    assert rec.recommendation == "Approve investment in X"
    assert rec.confidence == 0.85

def test_parse_strategy_recommendation():
    content = """
    <recommendation>60% salary, 40% dividends hybrid</recommendation>
    <reasoning>Balances tax efficiency...</reasoning>
    <confidence>medium</confidence>
    """
    rec = parse_recommendation_from_response(content, persona)
    assert "60%" in rec.recommendation
    assert "hybrid" in rec.recommendation
```

### Integration Tests

```python
# Test full flow with binary problem
async def test_binary_problem_deliberation():
    problem = Problem(description="Should we invest $50K in SEO?")
    # Run deliberation
    # Verify recommendations can be "Yes" or "No, invest in paid ads instead"
    # Verify AI synthesis produces consensus

# Test full flow with strategy problem
async def test_strategy_problem_deliberation():
    problem = Problem(description="What compensation structure for directors?")
    # Run deliberation
    # Verify recommendations are specific strategies
    # Verify AI synthesis handles diverse approaches
```

---

## Migration Checklist

### Breaking Changes (Pre-launch OK)

- [x] `Vote` model → `Recommendation` model
- [x] `VoteDecision` enum deleted
- [x] `votes` field → `recommendations` in state
- [x] Vote parsing logic deleted
- [x] Mechanical `aggregate_votes()` deleted
- [x] Voting prompts completely rewritten
- [x] JSON/Markdown export format changed

### Files to Modify

- [ ] `bo1/models/votes.py` (rename file to `recommendations.py`)
- [ ] `bo1/prompts/reusable_prompts.py`
- [ ] `bo1/llm/response_parser.py`
- [ ] `bo1/orchestration/voting.py` (rename to `recommendations.py`)
- [ ] `bo1/graph/nodes.py`
- [ ] `bo1/graph/state.py`
- [ ] `bo1/graph/config.py`
- [ ] `bo1/interfaces/console.py`
- [ ] `bo1/export/*.py`
- [ ] All test files

### Files to Delete

- [ ] `bo1/utils/vote_parsing.py`
- [ ] `tests/utils/test_vote_parsing.py`

---

## Rollout Strategy

Since we're **pre-launch**, no gradual migration needed:

1. ✅ Create feature branch: `feat/recommendations-model`
2. ✅ Implement all changes in one pass
3. ✅ Update all tests
4. ✅ Test with both problem types
5. ✅ Merge to main (breaking change OK)

---

## Success Criteria

- [ ] Binary problems work: "Should we invest in X?" → experts can say Yes/No/Alternative
- [ ] Strategy problems work: "What should we invest in?" → experts provide specific strategies
- [ ] No more ABSTAIN votes from parser failures
- [ ] AI synthesis produces intelligent consensus from diverse recommendations
- [ ] Exports show recommendations clearly (not "vote: yes")
- [ ] All tests pass with new model

---

## Open Questions

1. **Rename phase enum?** `DeliberationPhase.VOTING` → `DeliberationPhase.RECOMMENDATIONS` (yes)
2. **Keep "voting" terminology in UI?** Switch to "recommendations"
3. **Backward compat for old exports?** (NO - we're pre-launch) NO backwards compat required

---

## Timeline

**Total**: ~8-10 hours of focused work

- **Today**: Create this plan doc (30 min) ✅
- **Session 1**: Phase 1-2 (Models, Prompts, Parsing) - 2-3 hours
- **Session 2**: Phase 3-4 (Orchestration, Graph) - 2 hours
- **Session 3**: Phase 5-6 (Tests, Exports) - 3 hours
- **Final**: Integration test with real problems - 1 hour

---

## Notes

- This is a **clean break** from Vote model, not a hybrid approach
- No backward compatibility needed (pre-launch)
- Simplifies codebase (deletes parsing logic, enum constraints)
- Sets foundation for richer recommendations in future (ranked choice, multi-option, etc.)
