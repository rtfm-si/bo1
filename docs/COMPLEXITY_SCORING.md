# Complexity Scoring and Adaptive Deliberation Parameters

## Overview

The Board of One system now features **adaptive deliberation parameters** based on problem complexity. Instead of using fixed 6-round limits for all problems, the system automatically adjusts:

- **Round limits**: 3-6 rounds (simple to complex)
- **Expert count**: 3-5 experts per round (focused to diverse)

This enables:
- **30-50% time savings** on simple problems (3 rounds vs 6)
- **Full deliberation** for complex strategic decisions (6 rounds, 5 experts)
- **Better resource allocation** (cost, time, expert attention)

## Architecture

### Flow

```
Problem → Decompose → Assess Complexity → Set Adaptive Parameters → Deliberate
```

1. **Decompose** (`decompose_node`): Break problem into sub-problems
2. **Assess Complexity** (`ComplexityAssessor`): Evaluate 5 dimensions
3. **Set Parameters**: Store in `metrics.recommended_rounds`, `metrics.recommended_experts`
4. **Apply**: Graph uses adaptive parameters for `max_rounds` and expert selection

### Complexity Dimensions (0.0-1.0)

The system evaluates problems across 5 dimensions:

1. **Scope Breadth** (25% weight): How many domains? (technical, business, legal, etc.)
2. **Dependencies** (25% weight): How interconnected are factors?
3. **Ambiguity** (20% weight): How clear are requirements?
4. **Stakeholders** (15% weight): How many parties affected?
5. **Novelty** (15% weight): How novel/unprecedented?

**Overall Complexity** = weighted average of 5 dimensions

### Adaptive Parameters

#### Round Limits (3-6)

| Complexity | Rounds | Use Case |
|-----------|--------|----------|
| 0.0-0.3 | 3 | Simple technical choices, binary decisions |
| 0.3-0.5 | 4 | Moderate business decisions, familiar problems |
| 0.5-0.7 | 5 | Complex problems spanning multiple domains |
| 0.7-1.0 | 6 | Strategic pivots, unprecedented situations |

#### Expert Count (3-5 per round)

| Complexity | Experts | Strategy |
|-----------|---------|----------|
| 0.0-0.3 | 3 | Focused panel, quick consensus |
| 0.3-0.7 | 4 | Balanced perspectives |
| 0.7-1.0 | 5 | Diverse viewpoints, thorough exploration |

**Phase Adjustments**:
- **Exploration** (rounds 1-2): Use full expert count
- **Challenge** (rounds 3-4): Use expert count - 1 (min 2)
- **Convergence** (rounds 5+): Use expert count - 1 (min 2)

## Code Integration

### ComplexityAssessor Agent

```python
from bo1.agents.complexity_assessor import ComplexityAssessor

assessor = ComplexityAssessor()
response = await assessor.assess_complexity(
    problem_description="Should I pivot from B2B to B2C?",
    context="18 months in, $500K ARR, team of 5",
    sub_problems=[
        {"id": "sp_001", "goal": "Market analysis"},
        {"id": "sp_002", "goal": "Product changes"}
    ]
)

# Response contains JSON:
{
    "scope_breadth": 0.9,
    "dependencies": 0.8,
    "ambiguity": 0.8,
    "stakeholders": 0.7,
    "novelty": 0.7,
    "overall_complexity": 0.80,
    "recommended_rounds": 6,
    "recommended_experts": 5,
    "reasoning": "Highly complex strategic pivot..."
}
```

### DeliberationMetrics

```python
from bo1.models.state import DeliberationMetrics

metrics = DeliberationMetrics()

# After complexity assessment:
metrics.complexity_score = 0.80
metrics.scope_breadth = 0.9
metrics.dependencies = 0.8
metrics.ambiguity = 0.8
metrics.stakeholders_complexity = 0.7
metrics.novelty = 0.7
metrics.recommended_rounds = 6
metrics.recommended_experts = 5
metrics.complexity_reasoning = "Highly complex strategic pivot..."
```

### decompose_node

The `decompose_node` automatically:
1. Decomposes problem into sub-problems
2. Assesses complexity using `ComplexityAssessor`
3. Updates `metrics` with complexity scores
4. Sets `state["max_rounds"]` to `metrics.recommended_rounds`

```python
# In decompose_node (bo1/graph/nodes.py):
assessor = ComplexityAssessor()
complexity_response = await assessor.assess_complexity(
    problem_description=problem.description,
    context=problem.context,
    sub_problems=[...]
)

# Parse and validate
complexity_assessment = validate_complexity_assessment(
    extract_json_with_fallback(complexity_response.content, ...)
)

# Update metrics
metrics.complexity_score = complexity_assessment["overall_complexity"]
metrics.recommended_rounds = complexity_assessment["recommended_rounds"]
metrics.recommended_experts = complexity_assessment["recommended_experts"]

# Apply to state
return {
    ...
    "max_rounds": metrics.recommended_rounds,  # Adaptive!
    "metrics": metrics,
}
```

### _select_experts_for_round

Expert selection now uses adaptive counts:

```python
# In _select_experts_for_round (bo1/graph/nodes.py):
metrics = state.get("metrics")
recommended_experts = 4  # Default fallback
if metrics and metrics.recommended_experts:
    recommended_experts = metrics.recommended_experts

if phase == "exploration":
    target_count = min(recommended_experts, len(personas))
elif phase == "challenge":
    target_count = min(max(2, recommended_experts - 1), len(personas))
elif phase == "convergence":
    target_count = min(max(2, recommended_experts - 1), len(personas))
```

## Examples

### Example 1: Simple Technical Decision

**Problem**: "Should I use PostgreSQL or MySQL for my database?"

**Complexity Assessment**:
```json
{
    "scope_breadth": 0.1,       // Single domain (database)
    "dependencies": 0.2,        // Mostly independent factors
    "ambiguity": 0.2,           // Clear trade-offs
    "stakeholders": 0.1,        // Solo developer
    "novelty": 0.2,             // Established patterns
    "overall_complexity": 0.16,
    "recommended_rounds": 3,    // Quick resolution
    "recommended_experts": 3    // Focused panel
}
```

**Deliberation**:
- 3 rounds (vs 6 default) = **50% time savings**
- 3 experts per round
- Total: ~9 contributions (vs 18-30 default)
- Time: ~2 minutes (vs ~5 minutes default)

### Example 2: Moderate Business Decision

**Problem**: "Should I invest $50K in SEO or paid ads?"

**Complexity Assessment**:
```json
{
    "scope_breadth": 0.4,       // Marketing + finance + operations
    "dependencies": 0.5,        // Interconnected factors
    "ambiguity": 0.5,           // Some unknowns about ROI
    "stakeholders": 0.3,        // Small team, limited customers
    "novelty": 0.3,             // Familiar problem
    "overall_complexity": 0.41,
    "recommended_rounds": 4,    // Standard debate
    "recommended_experts": 4    // Balanced panel
}
```

**Deliberation**:
- 4 rounds (vs 6 default) = **33% time savings**
- 4 experts per round
- Total: ~16 contributions (vs 18-30 default)
- Time: ~3.5 minutes (vs ~5 minutes default)

### Example 3: Complex Strategic Decision

**Problem**: "Should I pivot from B2B to B2C?"

**Complexity Assessment**:
```json
{
    "scope_breadth": 0.9,       // Market + product + finance + org + legal
    "dependencies": 0.8,        // Tightly coupled decisions
    "ambiguity": 0.8,           // High uncertainty
    "stakeholders": 0.7,        // Many parties (investors, team, customers)
    "novelty": 0.7,             // Novel for this context
    "overall_complexity": 0.80,
    "recommended_rounds": 6,    // Full deliberation
    "recommended_experts": 5    // Diverse perspectives
}
```

**Deliberation**:
- 6 rounds (full deliberation)
- 5 experts per round
- Total: ~30 contributions (maximum thoroughness)
- Time: ~5-6 minutes (full depth)

## Validation & Fallbacks

The system includes robust validation:

### Complexity Score Validation

```python
from bo1.agents.complexity_assessor import validate_complexity_assessment

# Clamps scores to valid ranges
assessment = validate_complexity_assessment({
    "overall_complexity": 1.5,  # → 1.0 (clamped)
    "scope_breadth": -0.1,      # → 0.0 (clamped)
    "recommended_rounds": 10,   # → 6 (clamped)
    "recommended_experts": 1,   # → 3 (clamped to min)
})
```

### Fallback Defaults

If complexity assessment fails:
```python
# In decompose_node:
def create_complexity_fallback():
    return {
        "scope_breadth": 0.4,
        "dependencies": 0.4,
        "ambiguity": 0.4,
        "stakeholders": 0.3,
        "novelty": 0.3,
        "overall_complexity": 0.38,
        "recommended_rounds": 4,     # Moderate defaults
        "recommended_experts": 4,
        "reasoning": "Complexity assessment failed, using moderate defaults",
    }
```

### Metrics Defaults

If metrics not available during expert selection:
```python
# In _select_experts_for_round:
recommended_experts = 4  # Safe default
if metrics and metrics.recommended_experts:
    recommended_experts = metrics.recommended_experts
```

## Testing

Comprehensive test coverage in `tests/test_complexity_assessment.py`:

```bash
pytest tests/test_complexity_assessment.py -v
```

Tests cover:
- Adaptive round calculation (3-6)
- Adaptive expert calculation (3-5)
- Complexity validation and clamping
- Real-world examples
- Metrics model integration

## Cost & Performance Impact

### Simple Problems (complexity < 0.3)

- **Before**: 6 rounds × 4 experts = 24 contributions
- **After**: 3 rounds × 3 experts = 9 contributions
- **Savings**: 62% fewer contributions, ~60% time savings
- **Cost**: ~$0.03 vs ~$0.10 (70% savings)

### Moderate Problems (complexity 0.3-0.5)

- **Before**: 6 rounds × 4 experts = 24 contributions
- **After**: 4 rounds × 4 experts = 16 contributions
- **Savings**: 33% fewer contributions, ~33% time savings
- **Cost**: ~$0.07 vs ~$0.10 (30% savings)

### Complex Problems (complexity > 0.7)

- **Before**: 6 rounds × 4 experts = 24 contributions
- **After**: 6 rounds × 5 experts = 30 contributions
- **Change**: 25% more contributions (better quality)
- **Cost**: ~$0.12 vs ~$0.10 (20% increase for higher quality)

### Complexity Assessment Cost

- Model: Haiku (cheap, fast)
- Cost: ~$0.001 per assessment
- Time: ~500ms
- Negligible overhead compared to deliberation savings

## Future Enhancements

Potential improvements:

1. **Model Selection**: Use Haiku for simple problems, Sonnet for complex
2. **Dynamic Phase Tuning**: Adjust phase transitions based on complexity
3. **Historical Learning**: Learn from past complexity assessments
4. **User Feedback**: Allow users to adjust complexity if assessment seems off
5. **Sub-problem Complexity**: Individual complexity scores per sub-problem

## Files Modified

- `bo1/prompts/complexity_prompts.py` - Complexity assessment prompts
- `bo1/agents/complexity_assessor.py` - ComplexityAssessor agent
- `bo1/models/state.py` - Added complexity fields to DeliberationMetrics
- `bo1/graph/nodes.py` - Integrated complexity scoring into decompose_node and _select_experts_for_round
- `tests/test_complexity_assessment.py` - Comprehensive test coverage

## References

- **Complexity Scoring Rubric**: See `bo1/prompts/complexity_prompts.py`
- **Adaptive Functions**: `bo1/agents/complexity_assessor.py::get_adaptive_max_rounds()`, `get_adaptive_num_experts()`
- **Loop Prevention**: `bo1/graph/safety/loop_prevention.py::get_adaptive_max_rounds()` (legacy, replaced)
