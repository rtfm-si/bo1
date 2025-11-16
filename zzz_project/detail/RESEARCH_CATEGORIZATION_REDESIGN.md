# Research Categorization System - Redesign Summary

**Status**: Design Complete
**Replaces**: Keyword-based categorization (brittle, context-unaware)
**New Approach**: Context-aware, data-driven, threshold-based execution

---

## Problems with Keyword Matching Approach

1. **Brittle**: Relies on exact keyword presence, misses semantic variations
2. **Context-Unaware**: Ignores who requested it, why, and the business context
3. **No Priority Handling**: Treats all requests equally (no CRITICAL vs NICE_TO_HAVE)
4. **No Cost Control**: No mechanism to limit research spend per session
5. **No Demand Tracking**: Missed opportunities for proactive data gathering

---

## New Design Principles

### 1. Explicit Research Request Structure

Research is **requested explicitly** during:
- **Problem decomposition**: Decomposer identifies external information gaps
- **Expert deliberation**: Facilitator/experts request clarification data
- **User specification**: User explicitly states "research competitor landscape"

Each request is structured with:

```python
@dataclass
class ResearchRequest:
    question: str                           # The research question
    category: ResearchCategory             # COMPETITOR_ANALYSIS, BENCHMARKS, etc.
    priority: ResearchPriority             # CRITICAL, IMPORTANT, NICE_TO_HAVE
    confidence_in_value_add: float         # 0.0-1.0 (predicted impact)
    estimated_decision_impact: str         # LOW, MEDIUM, HIGH
    requester: str                         # "decomposer", "expert:FINTECH_CFO"
    context: dict[str, str]                # Business domain, industry, etc.
```

**Key Insight**: Research isn't keyword-triggered, it's **intentionally requested** with metadata about value/priority/context.

---

### 2. Threshold-Based Execution

Not all research requests are executed. Decision based on:

| Threshold | Action | Rationale |
|-----------|--------|-----------|
| **confidence >= 0.40** | ✅ Execute research | High enough value-add to justify cost |
| **0.25 <= confidence < 0.40** | 📊 Track demand, don't execute | Capture for proactive scraping |
| **confidence < 0.25** | ⏭️ Skip entirely | Too low value to even track |
| **CRITICAL priority** | ✅ Always execute | Blocks decision, must research |

**Cost Gates** (per session):
- Brave: $0.10 max per session
- Tavily: $0.30 max per session

---

### 3. Smart Provider Selection

```python
def categorize_research_request(request: ResearchRequest) -> tuple[str, str]:
    """Select provider and depth based on category + priority + impact."""

    # Deep research categories → Tavily advanced
    if request.category in {COMPETITOR_ANALYSIS, MARKET_LANDSCAPE, REGULATION}:
        return ("tavily", "advanced")

    # Quick lookups → Brave
    if request.category in {BENCHMARKS, NEWS, GENERAL}:
        # Upgrade to Tavily if CRITICAL + HIGH impact + high confidence
        if (request.priority == CRITICAL and
            request.estimated_decision_impact == "HIGH" and
            request.confidence_in_value_add >= 0.75):
            return ("tavily", "advanced")  # Upgrade!

        return ("brave", "web")
```

**Dynamic Upgrading**: Even "benchmark" queries can be upgraded to Tavily if they're critical and high-impact.

---

### 4. Demand Tracking for Proactive Scraping

**Problem**: Some valuable questions don't meet execution thresholds (0.30 confidence).
**Solution**: Track them anyway for **proactive scraping**.

#### Database: `research_demand` table

```sql
CREATE TABLE research_demand (
    id UUID PRIMARY KEY,
    question TEXT NOT NULL,
    question_embedding vector(1536),  -- Cluster similar requests
    category TEXT,
    priority TEXT,
    confidence_in_value_add DECIMAL(3, 2),
    estimated_decision_impact TEXT,
    requester TEXT,
    business_context JSONB,
    requested_at TIMESTAMP,
    fulfilled BOOLEAN DEFAULT FALSE,
    request_count INT DEFAULT 1  -- Aggregate similar requests
);
```

#### Proactive Scraping Triggers (daily cron job)

1. **High Repeat Demand**
   Same question requested **3+ times** in 30 days, avg confidence >= 0.50

2. **Clustered Similar Requests**
   **5+ similar questions** (embedding similarity > 0.85), same category/industry

3. **Cross-User Patterns**
   Question requested by **2+ users** with similar business contexts

**Action**: Pre-research the question, save to cache → future requests are instant (cache hit).

---

## Example Scenarios

### Scenario 1: Critical Competitor Analysis

```python
request = ResearchRequest(
    question="Who are Slack's main competitors in team communication?",
    category=ResearchCategory.COMPETITOR_ANALYSIS,
    priority=ResearchPriority.CRITICAL,
    confidence_in_value_add=0.85,
    estimated_decision_impact="HIGH",
    requester="decomposer",
    context={"business_model": "B2B SaaS", "industry": "team_communication"}
)

# Decision
should_execute_research(request) → (True, "CRITICAL priority (impact: HIGH)")
categorize_research_request(request) → ("tavily", "advanced")

# Cost: $0.015 (Tavily advanced) + $0.05 (summarization) = $0.065
# Saved to cache, fulfilled = True
```

---

### Scenario 2: Important Benchmark (Execute)

```python
request = ResearchRequest(
    question="Average churn rate for B2B SaaS companies?",
    category=ResearchCategory.BENCHMARKS,
    priority=ResearchPriority.IMPORTANT,
    confidence_in_value_add=0.65,
    estimated_decision_impact="MEDIUM",
    requester="expert:FINTECH_CFO",
    context={"industry": "SaaS"}
)

# Decision
should_execute_research(request) → (True, "Confidence 0.65 exceeds threshold 0.40")
categorize_research_request(request) → ("brave", "web")

# Cost: $0.005 (Brave) + $0.05 (summarization) = $0.055
# Saved to cache, fulfilled = True
```

---

### Scenario 3: Low Confidence (Track, Don't Execute)

```python
request = ResearchRequest(
    question="What's the average marketing budget for SaaS startups?",
    category=ResearchCategory.BENCHMARKS,
    priority=ResearchPriority.NICE_TO_HAVE,
    confidence_in_value_add=0.35,  # Below execution threshold
    estimated_decision_impact="LOW",
    requester="expert:MARKETING_VP",
    context={"industry": "SaaS"}
)

# Decision
should_execute_research(request) → (False, "Confidence 0.35 below threshold 0.40 (tracked for proactive scraping)")

# Action: Save to research_demand table (fulfilled = False)
# If 3+ similar requests appear in 30 days → proactive scraping job executes it
# Cost: $0 (not executed immediately)
```

---

### Scenario 4: Critical Benchmark (Upgraded to Tavily)

```python
request = ResearchRequest(
    question="What are industry-standard SaaS security compliance requirements?",
    category=ResearchCategory.BENCHMARKS,  # Normally Brave
    priority=ResearchPriority.CRITICAL,
    confidence_in_value_add=0.80,
    estimated_decision_impact="HIGH",
    requester="decomposer",
    context={"industry": "SaaS", "compliance_focus": True}
)

# Decision
should_execute_research(request) → (True, "CRITICAL priority (impact: HIGH)")
categorize_research_request(request) → ("tavily", "advanced")  # UPGRADED!

# Reasoning: CRITICAL + HIGH impact + 0.80 confidence → Upgrade to deep research
# Cost: $0.015 (Tavily advanced) + $0.05 (summarization) = $0.065
```

---

## Demand Tracking Analytics

### Key Metrics

**1. Execution Rate by Confidence**

| Confidence Range | Total Requests | Executed | Skipped | Execution Rate |
|-----------------|----------------|----------|---------|----------------|
| 0.75-1.00 (high) | 120 | 118 | 2 | 98% |
| 0.50-0.74 (medium) | 85 | 72 | 13 | 85% |
| 0.25-0.49 (low) | 43 | 0 | 43 | 0% (tracked) |
| <0.25 (very low) | 12 | 0 | 12 | 0% (not tracked) |

**2. Cost Avoidance**

- Skipped requests (confidence < 0.40): 55 requests
- Estimated cost saved: 55 × $0.07 = **$3.85/month**

**3. Proactive Scraping Candidates**

| Question | Category | Requests | Avg Confidence | Action |
|----------|----------|----------|----------------|--------|
| "Average SaaS churn rate?" | BENCHMARKS | 7 | 0.58 | ✅ Scrape |
| "Market size for project mgmt software?" | MARKET_LANDSCAPE | 5 | 0.62 | ✅ Scrape |
| "GDPR compliance checklist?" | REGULATION | 4 | 0.55 | ✅ Scrape |

**Proactive Scraping ROI**:
- Pre-research cost: 3 questions × $0.07 = $0.21
- Future cache hits: 16 requests × $0.07 = $1.12 saved
- **ROI: 533% (5.3x return)**

---

## Benefits vs. Keyword Matching

| Feature | Keyword Matching | New Design |
|---------|------------------|------------|
| **Context Awareness** | ❌ None | ✅ Business context, requester, priority |
| **Cost Control** | ❌ None | ✅ Per-session caps, confidence thresholds |
| **Priority Handling** | ❌ All equal | ✅ CRITICAL always executes |
| **Demand Tracking** | ❌ None | ✅ Tracks unfulfilled requests |
| **Proactive Scraping** | ❌ None | ✅ Pre-research high-demand topics |
| **Smart Upgrades** | ❌ Fixed routing | ✅ Dynamic (CRITICAL + HIGH → Tavily) |
| **Analytics** | ❌ None | ✅ Execution rates, cost avoidance, ROI |

---

## Implementation Impact

### Phase 1 (Immediate)
- Replace keyword matching with `ResearchRequest` dataclass
- Implement `should_execute_research()` threshold logic
- Add `research_demand` table to PostgreSQL

### Phase 2 (Week 2)
- Integrate with decomposer (generate `ResearchRequest` objects)
- Integrate with facilitator/experts (request research mid-deliberation)
- Track unfulfilled requests to database

### Phase 3 (Week 3)
- Build proactive scraping cron job
- Create demand analytics dashboard
- Monitor ROI and tune thresholds

---

## Tunable Parameters

All thresholds are configurable:

```python
class ResearchThresholdConfig:
    MIN_CONFIDENCE_TO_EXECUTE = 0.40   # Tune based on budget
    MIN_CONFIDENCE_TO_TRACK = 0.25     # Lower = more tracking
    MAX_COST_PER_SESSION_BRAVE = 0.10  # Cost gates
    MAX_COST_PER_SESSION_TAVILY = 0.30
```

**Tuning Strategy**:
- **Tight budget**: Raise `MIN_CONFIDENCE_TO_EXECUTE` to 0.50
- **Aggressive scraping**: Lower `MIN_CONFIDENCE_TO_TRACK` to 0.20
- **High-value users**: Raise cost caps to $0.50 (Tavily)

---

## Success Metrics

- [ ] **Execution Rate**: 80%+ of requests with confidence >= 0.40 executed
- [ ] **Cost Avoidance**: 20%+ of requests skipped due to low confidence
- [ ] **Proactive Scraping ROI**: 3x+ return (cache hits vs scraping cost)
- [ ] **Demand Hotspots**: 10+ high-demand topics identified per month
- [ ] **Cache Hit Rate**: 70%+ after 1 month (including proactive scraping)

---

**End of Summary**

See full implementation plan in: `BRAVE_TAVILY_RESEARCH_INTEGRATION.md`
