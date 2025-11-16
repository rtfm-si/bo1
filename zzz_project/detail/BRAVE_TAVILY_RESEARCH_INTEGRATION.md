# Brave Search API + Tavily Integration Plan

**Status**: Planning Phase
**Timeline**: 3-5 days
**Dependencies**: ResearcherAgent (stub), Research Cache (planned Week 6)

---

## Executive Summary

**Objective**: Replace placeholder research implementation with a two-tier search strategy:
- **Brave Search API** as the default "cheap web+news layer" for general queries
- **Tavily Advanced Search** for specialized deep research (competitor analysis, market landscape, regulation/policy)

**Cost Optimization**:
- Current placeholder: No actual research
- Brave-only approach: ~$0.005-0.009 per query
- Smart routing (70% Brave, 30% Tavily): ~$0.0065 per query average
- **90% cost reduction when combined with semantic cache** (after 1-3 months)

**Benefits**:
1. **Cost Efficiency**: Brave is 40-50% cheaper than Tavily basic for general queries
2. **Quality Depth**: Tavily advanced provides LLM-optimized deep research when needed
3. **Intelligent Routing**: Automatic selection based on query categorization
4. **Flexibility**: Fallback strategies if one provider fails or hits rate limits

---

## API Comparison

### Brave Search API

| Feature | Details |
|---------|---------|
| **Pricing** | Free: 2,000 queries/month<br>Base AI: $5/1,000 queries ($0.005/query)<br>Pro AI: $9/1,000 queries ($0.009/query) |
| **Rate Limits** | Free: 1 query/sec<br>Base: 20 queries/sec<br>Pro: 50 queries/sec |
| **Capabilities** | Web search, images, videos, news<br>30+ billion page index<br>Daily updates (100M+ pages)<br>Independent indexing (not repackaged) |
| **Best For** | General web search, news, quick facts, industry benchmarks |
| **Response Format** | Up to 5 snippets per result, structured data, schema-enriched |
| **Latency** | Faster than SerpAPI/Serper (per Brave claims) |

### Tavily API

| Feature | Details |
|---------|---------|
| **Pricing** | Free: 1,000 credits/month<br>Project: $30/4,000 credits ($0.0075/basic, $0.015/advanced)<br>Add-on: $100/8,000 credits (one-time, no expiration) |
| **Rate Limits** | Varies by plan (documented in API dashboard) |
| **Capabilities** | Basic search: Generic snippets (1 credit)<br>Advanced search: Deep research, semantic understanding, LLM-optimized chunks (2 credits)<br>Relevance scoring<br>Multiple chunks per source (configurable) |
| **Best For** | In-depth competitor analysis, market research, regulatory analysis, multi-step queries |
| **Response Format** | Relevance-scored results, contextually-aligned content chunks, high-quality source filtering |
| **Special Features** | Semantic search + keyword filtering<br>LLM consumption optimization<br>Chunks per source (advanced only, default 3) |

### Cost Comparison (per 1,000 queries)

| Scenario | Brave Base | Tavily Basic | Tavily Advanced |
|----------|------------|--------------|-----------------|
| **1,000 general queries** | $5.00 | $7.50 | $15.00 |
| **1,000 deep research queries** | $5.00 | $7.50 | $15.00 |
| **Smart routing (700 Brave + 300 Tavily Advanced)** | - | - | **$8.00** |
| **With 90% cache hit rate** | $0.50 | $0.75 | **$0.80** |

**Winner**: Smart routing + cache = **90% cost savings** after 3 months

---

## Architecture Design

### Multi-Provider Search System

```
ResearcherAgent.research_questions()
    ↓
┌──────────────────────────────────────────────────┐
│ 1. Categorize Query                             │
│    - Analyze question text                      │
│    - Classify: general | competitor_analysis |  │
│      market_landscape | regulation              │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│ 2. Check Semantic Cache (existing feature)      │
│    - Generate embedding (OpenAI ada-002)        │
│    - Search for similarity > 0.85               │
│    - If HIT → return cached result              │
│    - If MISS → continue to provider selection   │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│ 3. Select Search Provider (NEW)                 │
│    IF category in [competitor_analysis,         │
│                     market_landscape,            │
│                     regulation]:                 │
│        → TavilySearchProvider (advanced)        │
│    ELSE:                                         │
│        → BraveSearchProvider (web)              │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│ 4. Execute Search (NEW)                         │
│    - provider.search(query, max_results=5)      │
│    - Extract snippets/content                   │
│    - Calculate cost                             │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│ 5. Summarize Results (Haiku 4.5)                │
│    - Combine snippets from all sources          │
│    - Generate 200-300 token summary             │
│    - Include source citations                   │
│    - Assess confidence (high/medium/low)        │
└──────────────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────────────┐
│ 6. Save to Cache (existing feature)             │
│    - Store question + embedding + summary       │
│    - Include provider metadata                  │
│    - Track costs (search + summarization)       │
└──────────────────────────────────────────────────┘
```

### Query Categorization Logic

**Context-Aware Research Request Model**

Research requests are generated during:
1. **Problem decomposition** - Decomposer identifies external information gaps
2. **Expert deliberation** - Facilitator/experts request clarification data
3. **User explicit requests** - User specifies research type in problem statement

Each request includes:
- `question`: The research question
- `category`: User-specified or AI-inferred category
- `priority`: CRITICAL | IMPORTANT | NICE_TO_HAVE
- `confidence_in_value_add`: 0.0-1.0 (predicted impact on decision quality)
- `estimated_decision_impact`: LOW | MEDIUM | HIGH
- `requester`: "decomposer" | "facilitator" | "expert:{code}" | "user"
- `context`: Business domain, problem type, stakeholder info

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class ResearchCategory(str, Enum):
    """Research categories mapped to provider + search depth."""
    # Tavily advanced (2 credits, deep research)
    COMPETITOR_ANALYSIS = "competitor_analysis"
    MARKET_LANDSCAPE = "market_landscape"
    REGULATION = "regulation"

    # Brave web search (cheaper, faster)
    BENCHMARKS = "benchmarks"  # Industry metrics, SaaS benchmarks
    NEWS = "news"  # Recent news, press releases
    GENERAL = "general"  # Facts, definitions, quick lookups

    # User-specified (explicit categorization)
    USER_SPECIFIED = "user_specified"


class ResearchPriority(str, Enum):
    """Priority levels for research requests."""
    CRITICAL = "critical"  # Blocks decision, must research
    IMPORTANT = "important"  # Valuable but not blocking
    NICE_TO_HAVE = "nice_to_have"  # Optional, low impact


@dataclass
class ResearchRequest:
    """Structured research request from decomposer/facilitator/experts."""

    question: str
    category: ResearchCategory
    priority: ResearchPriority
    confidence_in_value_add: float  # 0.0-1.0
    estimated_decision_impact: Literal["LOW", "MEDIUM", "HIGH"]
    requester: str  # "decomposer", "facilitator", "expert:FINTECH_CFO", "user"
    context: dict[str, str]  # Business domain, problem type, etc.

    # Demand tracking
    requested_at: str  # ISO timestamp
    fulfilled: bool = False
    cache_hit: bool = False

    def __post_init__(self):
        """Validate request fields."""
        if not 0.0 <= self.confidence_in_value_add <= 1.0:
            raise ValueError("confidence_in_value_add must be 0.0-1.0")


class ResearchThresholdConfig:
    """Configurable thresholds for research execution."""

    # Minimum confidence to actually execute research
    MIN_CONFIDENCE_TO_EXECUTE = 0.40

    # Minimum confidence to cache request for proactive scraping
    MIN_CONFIDENCE_TO_TRACK = 0.25

    # Priority overrides (always execute if CRITICAL, even low confidence)
    ALWAYS_EXECUTE_PRIORITIES = {ResearchPriority.CRITICAL}

    # Cost gates (max spend per category)
    MAX_COST_PER_SESSION_BRAVE = 0.10  # $0.10 max Brave calls per session
    MAX_COST_PER_SESSION_TAVILY = 0.30  # $0.30 max Tavily calls per session


def categorize_research_request(request: ResearchRequest) -> tuple[str, str]:
    """Select provider and search depth based on category and priority.

    Args:
        request: Structured research request

    Returns:
        Tuple of (provider_name, search_depth)

    Provider selection logic:
        - USER_SPECIFIED category with explicit provider → use as specified
        - COMPETITOR_ANALYSIS, MARKET_LANDSCAPE, REGULATION → Tavily advanced
        - BENCHMARKS, NEWS, GENERAL → Brave web search
        - CRITICAL priority + HIGH impact → Upgrade to Tavily even if normally Brave

    Examples:
        >>> req = ResearchRequest(
        ...     question="Who are our main competitors?",
        ...     category=ResearchCategory.COMPETITOR_ANALYSIS,
        ...     priority=ResearchPriority.CRITICAL,
        ...     confidence_in_value_add=0.85,
        ...     estimated_decision_impact="HIGH",
        ...     requester="decomposer",
        ...     context={"business_model": "B2B SaaS"},
        ... )
        >>> categorize_research_request(req)
        ('tavily', 'advanced')

        >>> req = ResearchRequest(
        ...     question="Average SaaS churn rate?",
        ...     category=ResearchCategory.BENCHMARKS,
        ...     priority=ResearchPriority.IMPORTANT,
        ...     confidence_in_value_add=0.60,
        ...     estimated_decision_impact="MEDIUM",
        ...     requester="expert:FINTECH_CFO",
        ...     context={"industry": "SaaS"},
        ... )
        >>> categorize_research_request(req)
        ('brave', 'web')
    """
    # User specified provider (explicit in problem statement)
    if request.category == ResearchCategory.USER_SPECIFIED:
        provider_hint = request.context.get("provider", "tavily")
        if provider_hint == "tavily":
            return ("tavily", "advanced")
        return ("brave", "web")

    # Deep research categories → Tavily advanced
    if request.category in {
        ResearchCategory.COMPETITOR_ANALYSIS,
        ResearchCategory.MARKET_LANDSCAPE,
        ResearchCategory.REGULATION,
    }:
        return ("tavily", "advanced")

    # Quick lookups → Brave
    if request.category in {
        ResearchCategory.BENCHMARKS,
        ResearchCategory.NEWS,
        ResearchCategory.GENERAL,
    }:
        # Upgrade to Tavily if critical AND high impact
        if (
            request.priority == ResearchPriority.CRITICAL
            and request.estimated_decision_impact == "HIGH"
            and request.confidence_in_value_add >= 0.75
        ):
            logger.info(
                f"⬆️ Upgrading {request.category} to Tavily advanced "
                f"(CRITICAL priority, HIGH impact, {request.confidence_in_value_add:.2f} confidence)"
            )
            return ("tavily", "advanced")

        return ("brave", "web")

    # Default fallback
    return ("brave", "web")


def should_execute_research(
    request: ResearchRequest,
    session_costs: dict[str, float],
) -> tuple[bool, str]:
    """Decide if research should be executed based on thresholds and budget.

    Args:
        request: Research request
        session_costs: Current session costs by provider
            e.g., {"brave": 0.05, "tavily": 0.12}

    Returns:
        Tuple of (should_execute: bool, reason: str)

    Decision logic:
        1. CRITICAL priority → always execute (unless cost cap hit)
        2. confidence_in_value_add >= 0.40 → execute
        3. confidence_in_value_add >= 0.25 → track demand but don't execute
        4. confidence_in_value_add < 0.25 → skip and don't track

    Examples:
        >>> req = ResearchRequest(
        ...     category=ResearchCategory.BENCHMARKS,
        ...     priority=ResearchPriority.IMPORTANT,
        ...     confidence_in_value_add=0.65,
        ...     ...
        ... )
        >>> should_execute_research(req, {"brave": 0.03})
        (True, "Confidence 0.65 exceeds threshold 0.40")

        >>> req = ResearchRequest(
        ...     priority=ResearchPriority.NICE_TO_HAVE,
        ...     confidence_in_value_add=0.30,
        ...     ...
        ... )
        >>> should_execute_research(req, {"brave": 0.02})
        (False, "Confidence 0.30 below execution threshold 0.40 (tracked for proactive scraping)")
    """
    config = ResearchThresholdConfig()
    provider, depth = categorize_research_request(request)

    # Check cost gates
    cost_key = "tavily" if provider == "tavily" else "brave"
    current_cost = session_costs.get(cost_key, 0.0)
    max_cost = (
        config.MAX_COST_PER_SESSION_TAVILY
        if provider == "tavily"
        else config.MAX_COST_PER_SESSION_BRAVE
    )

    if current_cost >= max_cost:
        return (
            False,
            f"Session cost cap reached: ${current_cost:.2f} >= ${max_cost:.2f} for {provider}"
        )

    # CRITICAL priority always executes (unless cost cap)
    if request.priority in config.ALWAYS_EXECUTE_PRIORITIES:
        return (True, f"CRITICAL priority (impact: {request.estimated_decision_impact})")

    # Confidence-based execution
    if request.confidence_in_value_add >= config.MIN_CONFIDENCE_TO_EXECUTE:
        return (
            True,
            f"Confidence {request.confidence_in_value_add:.2f} exceeds threshold {config.MIN_CONFIDENCE_TO_EXECUTE}"
        )

    # Track but don't execute (for proactive scraping)
    if request.confidence_in_value_add >= config.MIN_CONFIDENCE_TO_TRACK:
        return (
            False,
            f"Confidence {request.confidence_in_value_add:.2f} below execution threshold "
            f"{config.MIN_CONFIDENCE_TO_EXECUTE} (tracked for proactive scraping)"
        )

    # Skip entirely
    return (
        False,
        f"Confidence {request.confidence_in_value_add:.2f} too low to track "
        f"(threshold: {config.MIN_CONFIDENCE_TO_TRACK})"
    )
```

### Search Provider Interface

```python
# bo1/llm/search_providers.py

from abc import ABC, abstractmethod
from typing import Any
from enum import Enum

class ResearchCategory(str, Enum):
    """Categories for research query routing."""
    GENERAL = "general"
    COMPETITOR_ANALYSIS = "competitor_analysis"
    MARKET_LANDSCAPE = "market_landscape"
    REGULATION = "regulation"


class SearchResult:
    """Standardized search result format across providers."""

    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        relevance_score: float | None = None,
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.relevance_score = relevance_score


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Execute search query and return standardized results.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects

        Raises:
            SearchProviderError: If search fails
        """
        pass

    @abstractmethod
    def calculate_cost(self, num_queries: int) -> float:
        """Calculate cost for given number of queries.

        Args:
            num_queries: Number of search queries

        Returns:
            Total cost in USD
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging/analytics."""
        pass
```

---

## Research Demand Tracking System

**Purpose**: Track research requests that don't meet execution thresholds to identify opportunities for proactive data scraping.

### Database Schema

```sql
-- Research demand tracking table
CREATE TABLE research_demand (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Request metadata
    question TEXT NOT NULL,
    question_embedding vector(1536),  -- For clustering similar requests
    category TEXT,  -- Research category
    priority TEXT,  -- CRITICAL, IMPORTANT, NICE_TO_HAVE

    -- Decision metrics
    confidence_in_value_add DECIMAL(3, 2),  -- 0.00-1.00
    estimated_decision_impact TEXT,  -- LOW, MEDIUM, HIGH
    requester TEXT,  -- "decomposer", "facilitator", "expert:CODE", "user"

    -- Context
    business_context JSONB,  -- Business domain, industry, etc.
    problem_context TEXT,  -- Original problem statement

    -- Tracking
    requested_at TIMESTAMP DEFAULT NOW(),
    fulfilled BOOLEAN DEFAULT FALSE,
    fulfilled_at TIMESTAMP,
    execution_decision TEXT,  -- Reason for execute/skip decision

    -- Demand aggregation
    request_count INT DEFAULT 1,  -- How many times this question (or similar) requested
    last_requested_at TIMESTAMP DEFAULT NOW(),

    -- Session tracking
    session_id TEXT,
    user_id UUID  -- Future: link to user accounts
);

-- Indexes
CREATE INDEX idx_research_demand_embedding ON research_demand
    USING ivfflat (question_embedding vector_cosine_ops);
CREATE INDEX idx_research_demand_category ON research_demand(category);
CREATE INDEX idx_research_demand_fulfilled ON research_demand(fulfilled);
CREATE INDEX idx_research_demand_request_count ON research_demand(request_count DESC);
CREATE INDEX idx_research_demand_confidence ON research_demand(confidence_in_value_add DESC);

-- Materialized view: High-demand research topics (update daily)
CREATE MATERIALIZED VIEW research_demand_hotspots AS
SELECT
    category,
    question,
    COUNT(*) as total_requests,
    AVG(confidence_in_value_add) as avg_confidence,
    MAX(last_requested_at) as most_recent_request,
    COUNT(*) FILTER (WHERE fulfilled = FALSE) as unfulfilled_count,
    -- Extract common business contexts
    jsonb_agg(DISTINCT business_context->'business_model') as business_models,
    jsonb_agg(DISTINCT business_context->'industry') as industries
FROM research_demand
WHERE requested_at >= NOW() - INTERVAL '30 days'
GROUP BY category, question
HAVING COUNT(*) >= 3  -- At least 3 requests
ORDER BY total_requests DESC, avg_confidence DESC;

CREATE INDEX idx_demand_hotspots_requests ON research_demand_hotspots(total_requests DESC);
```

### Demand Tracking Flow

```
Research Request Generated
    ↓
Check Execution Thresholds
    ↓
┌─────────────────────────────────────────────────────┐
│ Should Execute? (confidence, priority, budget)      │
└─────────────────────────────────────────────────────┘
    ↓                                    ↓
  YES (execute)                        NO (skip)
    ↓                                    ↓
┌─────────────────────┐          ┌──────────────────────┐
│ 1. Check Cache      │          │ Should Track?        │
│ 2. Execute Search   │          │ (confidence >= 0.25) │
│ 3. Save to Cache    │          └──────────────────────┘
│ 4. Mark fulfilled   │                ↓                ↓
└─────────────────────┘              YES              NO
                                      ↓                ↓
                              ┌──────────────┐   [Skip entirely]
                              │ Save to      │
                              │ research_    │
                              │ demand       │
                              │ (unfulfilled)│
                              └──────────────┘
                                      ↓
                              ┌──────────────────────────┐
                              │ Clustering & Analysis    │
                              │ - Similar questions?     │
                              │ - High aggregate demand? │
                              │ - Proactive scraping?    │
                              └──────────────────────────┘
```

### Proactive Scraping Strategy

**Trigger Conditions** (check daily via cron job):

1. **High Repeat Demand**
   - Same question requested 3+ times in 30 days
   - Average confidence >= 0.50
   - Currently unfulfilled

2. **Clustered Similar Requests**
   - 5+ similar questions (embedding similarity > 0.85)
   - Aggregate confidence >= 0.60
   - Same category + industry

3. **Cross-User Patterns**
   - Question requested by 2+ different users
   - Similar business contexts (e.g., all B2B SaaS)
   - Average confidence >= 0.55

**Proactive Scraping Action**:
```python
async def run_proactive_scraping_job():
    """Daily job to pre-research high-demand topics."""

    # 1. Find high-demand unfulfilled requests
    hotspots = await db.fetch("""
        SELECT * FROM research_demand_hotspots
        WHERE unfulfilled_count >= 3
          AND avg_confidence >= 0.50
        ORDER BY total_requests DESC, avg_confidence DESC
        LIMIT 20
    """)

    for hotspot in hotspots:
        # 2. Execute research
        request = ResearchRequest(
            question=hotspot["question"],
            category=hotspot["category"],
            priority=ResearchPriority.IMPORTANT,
            confidence_in_value_add=hotspot["avg_confidence"],
            estimated_decision_impact="MEDIUM",
            requester="proactive_scraper",
            context={},
        )

        result = await researcher.research_question(request)

        # 3. Save to cache (will be available for future requests)
        # 4. Mark demand entries as fulfilled
        await db.execute("""
            UPDATE research_demand
            SET fulfilled = TRUE, fulfilled_at = NOW()
            WHERE question = $1 AND fulfilled = FALSE
        """, hotspot["question"])

        logger.info(
            f"✓ Proactively scraped: {hotspot['question'][:60]}... "
            f"(demand: {hotspot['total_requests']} requests)"
        )
```

### Demand Analytics Dashboard (Admin)

**Key Metrics**:

1. **Execution Rate**
   - % of research requests executed vs skipped
   - Breakdown by category, priority, confidence range

2. **Cost Avoidance**
   - Requests skipped due to low confidence
   - Estimated cost savings

3. **Demand Hotspots**
   - Most requested unfulfilled questions
   - Category distribution
   - Industry clustering

4. **Proactive Scraping ROI**
   - Cache hit rate on proactively scraped data
   - Cost of proactive scraping vs on-demand cost savings

**Example Queries**:

```sql
-- Execution rate by confidence range
SELECT
    CASE
        WHEN confidence_in_value_add >= 0.75 THEN '0.75-1.00 (high)'
        WHEN confidence_in_value_add >= 0.50 THEN '0.50-0.74 (medium)'
        WHEN confidence_in_value_add >= 0.25 THEN '0.25-0.49 (low)'
        ELSE '<0.25 (very low)'
    END as confidence_range,
    COUNT(*) as total_requests,
    COUNT(*) FILTER (WHERE fulfilled = TRUE) as executed,
    COUNT(*) FILTER (WHERE fulfilled = FALSE) as skipped,
    ROUND(100.0 * COUNT(*) FILTER (WHERE fulfilled = TRUE) / COUNT(*), 2) as execution_rate_pct
FROM research_demand
WHERE requested_at >= NOW() - INTERVAL '30 days'
GROUP BY confidence_range
ORDER BY MIN(confidence_in_value_add) DESC;

-- Top 20 unfulfilled research questions (proactive scraping candidates)
SELECT
    question,
    category,
    COUNT(*) as request_count,
    AVG(confidence_in_value_add) as avg_confidence,
    MAX(last_requested_at) as most_recent,
    jsonb_agg(DISTINCT business_context->'business_model') as common_business_models
FROM research_demand
WHERE fulfilled = FALSE
  AND requested_at >= NOW() - INTERVAL '30 days'
  AND confidence_in_value_add >= 0.25
GROUP BY question, category
HAVING COUNT(*) >= 3
ORDER BY COUNT(*) DESC, AVG(confidence_in_value_add) DESC
LIMIT 20;

-- Cost avoidance from skipped low-confidence requests
SELECT
    category,
    COUNT(*) as skipped_requests,
    -- Estimate cost saved (avg $0.07 per research call)
    ROUND(COUNT(*) * 0.07, 2) as estimated_cost_saved_usd
FROM research_demand
WHERE fulfilled = FALSE
  AND confidence_in_value_add < 0.40
  AND requested_at >= NOW() - INTERVAL '30 days'
GROUP BY category
ORDER BY COUNT(*) DESC;
```

---

## Implementation Plan

### Phase 1: Configuration & Setup (Day 1)

**Tasks**:

1. **Add API Keys to Environment**
   ```bash
   # .env.example additions
   BRAVE_API_KEY=your_brave_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here

   # Optional: Provider selection override (for testing)
   RESEARCH_PROVIDER_OVERRIDE=brave  # or 'tavily' or 'auto' (default)
   ```

2. **Update Settings Class**
   ```python
   # bo1/config.py

   class Settings(BaseSettings):
       # ... existing fields ...

       # Research API Keys (Week 6)
       brave_api_key: str | None = Field(
           default=None,
           description="Brave Search API key for web research"
       )
       tavily_api_key: str | None = Field(
           default=None,
           description="Tavily API key for deep research"
       )

       # Research Provider Configuration
       research_provider_override: str = Field(
           default="auto",
           description="Override provider selection: auto | brave | tavily"
       )
   ```

3. **Install Python SDKs**
   ```bash
   uv add httpx  # For Brave API (REST)
   uv add tavily-python  # Official Tavily SDK
   ```

**Success Criteria**:
- [ ] Environment variables added to `.env.example`
- [ ] Settings class updated with new fields
- [ ] Python dependencies installed
- [ ] Configuration validated in tests

---

### Phase 2: Search Provider Implementation (Days 2-3)

**Tasks**:

1. **Create Abstract Interface**

   File: `bo1/llm/search_providers.py` (shown above)

   - [ ] Define `ResearchCategory` enum
   - [ ] Define `SearchResult` dataclass
   - [ ] Define `SearchProvider` abstract base class
   - [ ] Add `SearchProviderError` exception class

2. **Implement BraveSearchProvider**

   File: `bo1/llm/search_providers.py`

   ```python
   import httpx
   from bo1.config import get_settings

   class BraveSearchProvider(SearchProvider):
       """Brave Search API provider for general web + news research."""

       BASE_URL = "https://api.search.brave.com/res/v1/web/search"

       def __init__(self):
           settings = get_settings()
           self.api_key = settings.brave_api_key
           if not self.api_key:
               raise SearchProviderError("BRAVE_API_KEY not configured")

           self.client = httpx.AsyncClient(
               headers={"X-Subscription-Token": self.api_key}
           )

       async def search(
           self,
           query: str,
           max_results: int = 5,
       ) -> list[SearchResult]:
           """Execute Brave web search."""
           params = {
               "q": query,
               "count": max_results,
               "text_decorations": False,
               "search_lang": "en",
           }

           try:
               response = await self.client.get(self.BASE_URL, params=params)
               response.raise_for_status()
               data = response.json()

               results = []
               for item in data.get("web", {}).get("results", [])[:max_results]:
                   results.append(SearchResult(
                       title=item.get("title", ""),
                       url=item.get("url", ""),
                       snippet=item.get("description", ""),
                       relevance_score=None,  # Brave doesn't provide scores
                   ))

               return results

           except httpx.HTTPError as e:
               raise SearchProviderError(f"Brave search failed: {e}")

       def calculate_cost(self, num_queries: int) -> float:
           """Brave Base AI: $5 per 1,000 queries."""
           return (num_queries / 1000) * 5.00

       @property
       def name(self) -> str:
           return "brave"
   ```

3. **Implement TavilySearchProvider**

   File: `bo1/llm/search_providers.py`

   ```python
   from tavily import TavilyClient

   class TavilySearchProvider(SearchProvider):
       """Tavily API provider for deep research (competitor, market, regulation)."""

       def __init__(self, search_depth: str = "advanced"):
           settings = get_settings()
           self.api_key = settings.tavily_api_key
           if not self.api_key:
               raise SearchProviderError("TAVILY_API_KEY not configured")

           self.client = TavilyClient(api_key=self.api_key)
           self.search_depth = search_depth  # "basic" or "advanced"

       async def search(
           self,
           query: str,
           max_results: int = 5,
       ) -> list[SearchResult]:
           """Execute Tavily advanced search."""
           try:
               # Tavily SDK is synchronous, so run in executor
               import asyncio
               loop = asyncio.get_event_loop()

               response = await loop.run_in_executor(
                   None,
                   lambda: self.client.search(
                       query=query,
                       search_depth=self.search_depth,
                       max_results=max_results,
                   )
               )

               results = []
               for item in response.get("results", []):
                   results.append(SearchResult(
                       title=item.get("title", ""),
                       url=item.get("url", ""),
                       snippet=item.get("content", ""),
                       relevance_score=item.get("score"),  # Tavily provides scores
                   ))

               return results

           except Exception as e:
               raise SearchProviderError(f"Tavily search failed: {e}")

       def calculate_cost(self, num_queries: int) -> float:
           """Tavily Project plan: $30 / 4,000 credits.
           Advanced search = 2 credits per query.
           """
           if self.search_depth == "advanced":
               credits_per_query = 2
           else:
               credits_per_query = 1

           cost_per_credit = 30.00 / 4000  # $0.0075 per credit
           return num_queries * credits_per_query * cost_per_credit

       @property
       def name(self) -> str:
           return f"tavily_{self.search_depth}"
   ```

4. **Create Provider Factory**

   ```python
   def get_search_provider(category: ResearchCategory) -> SearchProvider:
       """Get appropriate search provider for research category.

       Args:
           category: Research category

       Returns:
           SearchProvider instance
       """
       settings = get_settings()

       # Allow override for testing
       if settings.research_provider_override == "brave":
           return BraveSearchProvider()
       elif settings.research_provider_override == "tavily":
           return TavilySearchProvider(search_depth="advanced")

       # Auto-routing logic
       if category in [
           ResearchCategory.COMPETITOR_ANALYSIS,
           ResearchCategory.MARKET_LANDSCAPE,
           ResearchCategory.REGULATION,
       ]:
           return TavilySearchProvider(search_depth="advanced")

       # Default: Brave for general queries
       return BraveSearchProvider()
   ```

**Success Criteria**:
- [ ] `SearchProvider` abstract class defined
- [ ] `BraveSearchProvider` implemented and tested
- [ ] `TavilySearchProvider` implemented and tested
- [ ] Provider factory function created
- [ ] Unit tests passing (mocked API responses)

---

### Phase 3: ResearcherAgent Integration (Day 3)

**Tasks**:

1. **Update ResearcherAgent to Use Providers**

   File: `bo1/agents/researcher.py`

   ```python
   from bo1.llm.search_providers import (
       categorize_research_query,
       get_search_provider,
       SearchProviderError,
   )
   from bo1.llm.client import call_llm
   from bo1.config import get_model_for_role

   class ResearcherAgent:
       """Agent for researching external information gaps with multi-provider support."""

       async def _perform_web_research(
           self,
           question: str,
           category: str | None = None,
       ) -> dict[str, Any]:
           """Perform actual web research using Brave or Tavily.

           Args:
               question: Research question
               category: Optional category override

           Returns:
               Research result with summary, sources, confidence, cost
           """
           # 1. Categorize query (unless category provided)
           if category:
               research_category = ResearchCategory(category)
           else:
               research_category = categorize_research_query(question)

           logger.info(
               f"Research query categorized as: {research_category.value} | "
               f"Question: {question[:60]}..."
           )

           # 2. Get appropriate search provider
           try:
               provider = get_search_provider(research_category)
               logger.info(f"Using provider: {provider.name}")
           except SearchProviderError as e:
               logger.error(f"Provider initialization failed: {e}")
               return {
                   "summary": f"[Research unavailable: {e}]",
                   "sources": [],
                   "confidence": "low",
                   "tokens_used": 0,
                   "cost": 0.0,
                   "provider": "none",
               }

           # 3. Execute search
           try:
               search_results = await provider.search(
                   query=question,
                   max_results=5,
               )

               if not search_results:
                   logger.warning(f"No results found for: {question}")
                   return {
                       "summary": "[No relevant sources found]",
                       "sources": [],
                       "confidence": "low",
                       "tokens_used": 0,
                       "cost": provider.calculate_cost(1),
                       "provider": provider.name,
                   }

           except SearchProviderError as e:
               logger.error(f"Search failed: {e}")
               return {
                   "summary": f"[Search error: {e}]",
                   "sources": [],
                   "confidence": "low",
                   "tokens_used": 0,
                   "cost": 0.0,
                   "provider": provider.name,
               }

           # 4. Summarize results using Haiku 4.5
           sources_text = self._format_search_results(search_results)

           summary_prompt = f"""Summarize the following search results to answer the question.

Question: {question}

Search Results:
{sources_text}

Provide a concise 200-300 token summary that directly answers the question.
Include key facts, data points, and insights. Cite sources by number [1], [2], etc."""

           model = get_model_for_role("researcher")  # Haiku 4.5
           response = await call_llm(
               model=model,
               messages=[{"role": "user", "content": summary_prompt}],
               max_tokens=400,
           )

           summary = response["content"]
           tokens_used = response["usage"]["input_tokens"] + response["usage"]["output_tokens"]

           # Calculate total cost (search + summarization)
           search_cost = provider.calculate_cost(1)
           llm_cost = response["cost"]
           total_cost = search_cost + llm_cost

           # Assess confidence based on number of quality sources
           confidence = self._assess_confidence(search_results)

           logger.info(
               f"✓ Research complete | Provider: {provider.name} | "
               f"Sources: {len(search_results)} | Cost: ${total_cost:.4f}"
           )

           return {
               "summary": summary,
               "sources": [
                   {"url": r.url, "title": r.title, "snippet": r.snippet}
                   for r in search_results
               ],
               "confidence": confidence,
               "tokens_used": tokens_used,
               "cost": total_cost,
               "provider": provider.name,
           }

       def _format_search_results(self, results: list[SearchResult]) -> str:
           """Format search results for LLM summarization."""
           lines = []
           for i, result in enumerate(results, 1):
               lines.append(f"[{i}] {result.title}")
               lines.append(f"    URL: {result.url}")
               lines.append(f"    {result.snippet}")
               if result.relevance_score:
                   lines.append(f"    Relevance: {result.relevance_score:.2f}")
               lines.append("")
           return "\n".join(lines)

       def _assess_confidence(self, results: list[SearchResult]) -> str:
           """Assess confidence based on result quality."""
           if not results:
               return "low"

           # High confidence if we have 4+ sources
           if len(results) >= 4:
               return "high"
           # Medium if we have 2-3 sources
           elif len(results) >= 2:
               return "medium"
           # Low if only 1 source
           else:
               return "low"
   ```

2. **Update Cache to Store Provider Metadata**

   File: `bo1/state/postgres_manager.py` (update schema)

   ```sql
   -- Add provider column to research_cache table
   ALTER TABLE research_cache
   ADD COLUMN provider TEXT;  -- 'brave', 'tavily_basic', 'tavily_advanced'

   -- Index for analytics
   CREATE INDEX idx_research_cache_provider ON research_cache(provider);
   ```

**Success Criteria**:
- [ ] `ResearcherAgent._perform_web_research()` fully implemented
- [ ] Provider selection logic integrated
- [ ] Summarization working with Haiku 4.5
- [ ] Cost tracking includes both search + LLM costs
- [ ] Provider metadata stored in cache
- [ ] Integration tests passing

---

### Phase 4: Testing (Day 4)

**Tasks**:

1. **Unit Tests for Search Providers**

   File: `tests/llm/test_search_providers.py`

   ```python
   import pytest
   from unittest.mock import AsyncMock, patch
   from bo1.llm.search_providers import (
       BraveSearchProvider,
       TavilySearchProvider,
       categorize_research_query,
       ResearchCategory,
   )


   @pytest.mark.unit
   def test_categorize_competitor_analysis():
       """Competitor keywords trigger COMPETITOR_ANALYSIS category."""
       questions = [
           "Who are our main competitors in the B2B SaaS space?",
           "How does our pricing compare to alternatives?",
           "What is Salesforce's market share vs HubSpot?",
       ]

       for question in questions:
           assert categorize_research_query(question) == ResearchCategory.COMPETITOR_ANALYSIS


   @pytest.mark.unit
   def test_categorize_market_landscape():
       """Market keywords trigger MARKET_LANDSCAPE category."""
       questions = [
           "What is the market size for project management software?",
           "Industry trends in AI-powered SaaS tools?",
           "Market opportunity for B2B marketplace platforms?",
       ]

       for question in questions:
           assert categorize_research_query(question) == ResearchCategory.MARKET_LANDSCAPE


   @pytest.mark.unit
   def test_categorize_regulation():
       """Regulation keywords trigger REGULATION category."""
       questions = [
           "What are GDPR requirements for user data storage?",
           "HIPAA compliance checklist for healthcare SaaS?",
           "UK tax regulations for limited companies?",
       ]

       for question in questions:
           assert categorize_research_query(question) == ResearchCategory.REGULATION


   @pytest.mark.unit
   def test_categorize_general():
       """Non-specialized queries default to GENERAL."""
       questions = [
           "What is average churn rate for B2B SaaS?",
           "How much should I spend on customer acquisition?",
           "Best practices for SaaS pricing tiers?",
       ]

       for question in questions:
           assert categorize_research_query(question) == ResearchCategory.GENERAL


   @pytest.mark.unit
   @pytest.mark.asyncio
   async def test_brave_search_success():
       """Brave search returns formatted results."""
       provider = BraveSearchProvider()

       # Mock HTTP response
       mock_response = {
           "web": {
               "results": [
                   {
                       "title": "SaaS Churn Benchmarks 2025",
                       "url": "https://example.com/churn",
                       "description": "Average B2B SaaS churn rate is 5-7% annually.",
                   }
               ]
           }
       }

       with patch.object(provider.client, "get") as mock_get:
           mock_get.return_value = AsyncMock(
               json=lambda: mock_response,
               raise_for_status=lambda: None,
           )

           results = await provider.search("average SaaS churn rate")

           assert len(results) == 1
           assert results[0].title == "SaaS Churn Benchmarks 2025"
           assert results[0].url == "https://example.com/churn"
           assert "5-7%" in results[0].snippet


   @pytest.mark.unit
   def test_brave_cost_calculation():
       """Brave cost calculation is correct."""
       provider = BraveSearchProvider()

       assert provider.calculate_cost(1) == 0.005  # $5 / 1000
       assert provider.calculate_cost(1000) == 5.00
       assert provider.calculate_cost(100) == 0.50


   @pytest.mark.unit
   def test_tavily_cost_calculation():
       """Tavily cost calculation varies by search depth."""
       basic_provider = TavilySearchProvider(search_depth="basic")
       advanced_provider = TavilySearchProvider(search_depth="advanced")

       # Basic: 1 credit per query, $0.0075 per credit
       assert basic_provider.calculate_cost(1) == 0.0075
       assert basic_provider.calculate_cost(100) == 0.75

       # Advanced: 2 credits per query
       assert advanced_provider.calculate_cost(1) == 0.015
       assert advanced_provider.calculate_cost(100) == 1.50
   ```

2. **Integration Tests for ResearcherAgent**

   File: `tests/agents/test_researcher_integration.py`

   ```python
   @pytest.mark.integration
   @pytest.mark.requires_llm
   @pytest.mark.asyncio
   async def test_research_with_brave_provider():
       """General query uses Brave provider."""
       agent = ResearcherAgent()

       result = await agent._perform_web_research(
           question="What is average B2B SaaS churn rate?",
       )

       assert result["provider"] == "brave"
       assert "churn" in result["summary"].lower()
       assert len(result["sources"]) > 0
       assert result["cost"] > 0


   @pytest.mark.integration
   @pytest.mark.requires_llm
   @pytest.mark.asyncio
   async def test_research_with_tavily_provider():
       """Competitor analysis uses Tavily advanced."""
       agent = ResearcherAgent()

       result = await agent._perform_web_research(
           question="Who are HubSpot's main competitors in the CRM space?",
       )

       assert result["provider"] == "tavily_advanced"
       assert "competitor" in result["summary"].lower() or "salesforce" in result["summary"].lower()
       assert len(result["sources"]) > 0
       assert result["cost"] > 0
   ```

**Success Criteria**:
- [ ] All unit tests passing (categorization, provider methods, cost calculation)
- [ ] Integration tests passing (real API calls, optional via `@pytest.mark.requires_llm`)
- [ ] Cost tracking validated
- [ ] Provider selection logic validated

---

### Phase 5: Documentation & Deployment (Day 5)

**Tasks**:

1. **Update CLAUDE.md**

   Add section:
   ```markdown
   ### Research Providers (Week 6)

   Board of One uses a two-tier research strategy:

   - **Brave Search API**: Default for general web + news queries (~$0.005/query)
   - **Tavily Advanced Search**: Deep research for competitor analysis, market landscape, regulation (~$0.015/query)

   **Query Categorization**: Automatic routing based on keywords
   **Cost Optimization**: 90% reduction when combined with semantic cache (after 3 months)

   **Configuration**:
   ```bash
   # .env
   BRAVE_API_KEY=your_brave_api_key
   TAVILY_API_KEY=your_tavily_api_key
   RESEARCH_PROVIDER_OVERRIDE=auto  # or 'brave', 'tavily'
   ```
   ```

2. **Update .env.example**

   Add API keys and configuration examples

3. **Create Migration Guide**

   File: `zzz_project/detail/RESEARCH_PROVIDER_MIGRATION.md`

   Document:
   - Why we chose Brave + Tavily
   - Cost analysis
   - Categorization logic
   - Fallback strategies
   - Testing recommendations

4. **Add to Roadmap**

   Update `MVP_IMPLEMENTATION_ROADMAP.md` to mark research implementation complete

**Success Criteria**:
- [ ] CLAUDE.md updated
- [ ] .env.example updated
- [ ] Migration guide written
- [ ] Roadmap updated
- [ ] All documentation reviewed

---

## Cost Analysis

### Scenario 1: 100 Deliberations/Month (Current Usage)

**Assumptions**:
- Average 3 external research questions per deliberation
- Total queries: 300/month
- Distribution: 70% general (Brave), 30% specialized (Tavily advanced)

**Without Cache**:
- Brave queries: 210 × $0.005 = **$1.05**
- Tavily queries: 90 × $0.015 = **$1.35**
- Summarization (Haiku): 300 × $0.05 = **$15.00**
- **Total: $17.40/month**

**With Cache (70% hit rate after 1 month)**:
- Cache hits: 210 × $0.0001 (embedding) = **$0.02**
- Brave queries: 63 × $0.005 = **$0.32**
- Tavily queries: 27 × $0.015 = **$0.41**
- Summarization: 90 × $0.05 = **$4.50**
- **Total: $5.25/month (70% savings)**

**With Cache (90% hit rate after 3 months)**:
- Cache hits: 270 × $0.0001 = **$0.03**
- Brave queries: 21 × $0.005 = **$0.11**
- Tavily queries: 9 × $0.015 = **$0.14**
- Summarization: 30 × $0.05 = **$1.50**
- **Total: $1.78/month (90% savings)**

### Scenario 2: 1,000 Deliberations/Month (Growth)

**Without Cache**: $174.00/month
**With 70% Cache**: $52.50/month
**With 90% Cache**: $17.80/month

**ROI**: Cache pays for itself immediately (embedding costs negligible vs search savings)

---

## Fallback Strategies

### Provider Failure Handling

```python
async def _perform_web_research_with_fallback(
    self,
    question: str,
    category: str | None = None,
) -> dict[str, Any]:
    """Research with automatic fallback to alternative provider."""

    # Try primary provider
    try:
        return await self._perform_web_research(question, category)

    except SearchProviderError as e:
        logger.warning(f"Primary provider failed: {e}. Trying fallback...")

        # Fallback logic
        settings = get_settings()

        # If Tavily failed, try Brave
        if "tavily" in str(e).lower() and settings.brave_api_key:
            logger.info("Falling back to Brave Search")
            provider = BraveSearchProvider()
            # ... execute search ...

        # If Brave failed, try Tavily basic
        elif "brave" in str(e).lower() and settings.tavily_api_key:
            logger.info("Falling back to Tavily Basic Search")
            provider = TavilySearchProvider(search_depth="basic")
            # ... execute search ...

        # Both failed
        else:
            logger.error("All providers failed")
            return {
                "summary": "[Research temporarily unavailable]",
                "sources": [],
                "confidence": "low",
                "cost": 0.0,
            }
```

### Rate Limit Handling

- Brave free tier: 1 query/sec → Implement exponential backoff
- Tavily: Rate limits vary by plan → Check response headers, queue requests if needed
- Cache first strategy: Always check cache before hitting API (reduces rate limit issues)

---

## Success Metrics

- [ ] **Provider Selection**: 70% Brave, 30% Tavily (validates categorization logic)
- [ ] **Cost Per Query**: Average $0.0065 (Brave + Tavily mix)
- [ ] **Cache Hit Rate**: 70% after 1 month, 90% after 3 months
- [ ] **Research Quality**: 80%+ "high" or "medium" confidence results
- [ ] **Latency**: <5 seconds per query (search + summarization)
- [ ] **Error Rate**: <5% (fallback strategies working)

---

## Future Enhancements (Post-MVP)

### Tier 1: Optimization & UX (Weeks 15-20)

1. **Dynamic Provider Selection**: Use LLM to categorize query intent (more nuanced than current logic)
2. **Provider Performance Tracking**: A/B test providers, track quality metrics, auto-optimize
3. **Hybrid Search**: Combine Brave + Tavily results for critical queries
4. **Streaming Results**: Return search results immediately, summarize in background
5. **Custom Search Filters**: Industry-specific filters (e.g., "SaaS only", "US market only")
6. **Multi-Language Support**: Detect language, route to appropriate provider/region

### Tier 2: Academic Research Integration - CORE API (Post-MVP, Premium/Add-on)

**Purpose**: Add evidence-based research from academic papers for high-stakes decisions.

#### CORE API Overview

| Feature | Details |
|---------|---------|
| **Content** | 431M+ research papers, 46M+ full texts |
| **Coverage** | 14K+ data providers, 150+ countries |
| **Pricing** | **FREE** (basic tier with rate limits) |
| **Rate Limits** | Free: 5 single requests per 10 seconds OR 1 batch request per 10 seconds |
| **VIP Rates** | Custom quotes for higher usage (contact CORE) |
| **Best For** | Evidence-based decisions requiring peer-reviewed research, academic validation |

#### When to Use CORE vs. Brave/Tavily

| Provider | Use Case | Example Query | Cost |
|----------|----------|---------------|------|
| **Brave** | General facts, news, industry benchmarks | "Average SaaS churn rate 2025" | $0.005 |
| **Tavily** | Deep market research, competitor analysis | "HubSpot vs Salesforce market positioning" | $0.015 |
| **CORE** | Academic evidence, peer-reviewed studies | "Research on SaaS pricing psychology" | **FREE** |

**CORE is ideal for**:
- Healthcare/medical decisions (peer-reviewed clinical studies)
- Scientific/technical validation (research papers on AI, ML, engineering)
- Economic/business strategy (academic studies on pricing, growth, retention)
- Policy/regulation (research on GDPR impact, compliance effectiveness)

#### ResearchCategory Extension

```python
class ResearchCategory(str, Enum):
    # Existing categories
    COMPETITOR_ANALYSIS = "competitor_analysis"  # Tavily
    MARKET_LANDSCAPE = "market_landscape"        # Tavily
    REGULATION = "regulation"                    # Tavily
    BENCHMARKS = "benchmarks"                    # Brave
    NEWS = "news"                                # Brave
    GENERAL = "general"                          # Brave

    # New academic categories (CORE API)
    ACADEMIC_RESEARCH = "academic_research"      # CORE
    SCIENTIFIC_VALIDATION = "scientific_validation"  # CORE
    PEER_REVIEWED_EVIDENCE = "peer_reviewed_evidence"  # CORE
```

#### CORE Search Provider Implementation

```python
# bo1/llm/search_providers.py

import httpx
from typing import Any

class CORESearchProvider(SearchProvider):
    """CORE API provider for academic research papers and peer-reviewed evidence.

    Free tier: 5 requests per 10 seconds.
    VIP tier: Custom rate limits (enterprise only).
    """

    BASE_URL = "https://api.core.ac.uk/v3"

    def __init__(self, api_key: str | None = None):
        """Initialize CORE provider.

        Args:
            api_key: CORE API key (optional for free tier, required for VIP rates)
        """
        self.api_key = api_key  # Free tier doesn't require API key
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {}
        )

    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Execute CORE academic search.

        Returns peer-reviewed papers with abstracts, DOIs, and citations.
        """
        params = {
            "q": query,
            "limit": max_results,
            "scroll": False,  # Don't paginate for initial results
        }

        try:
            # CORE API v3 search endpoint
            response = await self.client.get(
                f"{self.BASE_URL}/search/works",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", [])[:max_results]:
                # Extract paper metadata
                title = item.get("title", "Untitled")
                abstract = item.get("abstract", "")
                doi = item.get("doi")
                year = item.get("yearPublished")
                authors = item.get("authors", [])
                citations_count = item.get("citationCount", 0)

                # Construct URL (prefer DOI, fallback to CORE URL)
                url = f"https://doi.org/{doi}" if doi else item.get("downloadUrl", "")

                # Format snippet: abstract + metadata
                snippet = f"{abstract[:300]}... | Year: {year} | Citations: {citations_count} | Authors: {', '.join([a.get('name', '') for a in authors[:3]])}"

                # Use citation count as relevance score (higher citations = higher relevance)
                relevance_score = min(citations_count / 100, 1.0)  # Normalize to 0-1

                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    relevance_score=relevance_score,
                ))

            return results

        except httpx.HTTPError as e:
            raise SearchProviderError(f"CORE search failed: {e}")

    def calculate_cost(self, num_queries: int) -> float:
        """CORE API is free (basic tier)."""
        return 0.0  # Free!

    @property
    def name(self) -> str:
        return "core_academic"
```

#### Smart Routing with CORE

```python
def categorize_research_request(request: ResearchRequest) -> tuple[str, str]:
    """Select provider including CORE for academic research.

    New routing rules:
        - ACADEMIC_RESEARCH, SCIENTIFIC_VALIDATION, PEER_REVIEWED_EVIDENCE → CORE
        - User tier "premium" or "enterprise" → Enable CORE access
        - Free tier users → Skip CORE (or offer upsell prompt)
    """
    # Check if user has access to CORE (premium/enterprise tier)
    user_tier = request.context.get("user_tier", "free")

    # Academic research categories → CORE (if user has access)
    if request.category in {
        ResearchCategory.ACADEMIC_RESEARCH,
        ResearchCategory.SCIENTIFIC_VALIDATION,
        ResearchCategory.PEER_REVIEWED_EVIDENCE,
    }:
        if user_tier in {"premium", "enterprise", "addon_academic"}:
            return ("core", "academic")
        else:
            logger.info(
                f"🔒 CORE research requested but user tier '{user_tier}' lacks access. "
                f"Consider upselling to Premium tier."
            )
            # Fallback to Tavily for free users
            return ("tavily", "advanced")

    # Existing routing logic (Brave/Tavily)
    if request.category in {
        ResearchCategory.COMPETITOR_ANALYSIS,
        ResearchCategory.MARKET_LANDSCAPE,
        ResearchCategory.REGULATION,
    }:
        return ("tavily", "advanced")

    return ("brave", "web")
```

#### Use Cases & Examples

**Healthcare/Medical Decisions**
```python
request = ResearchRequest(
    question="What does peer-reviewed research say about the effectiveness of remote patient monitoring?",
    category=ResearchCategory.PEER_REVIEWED_EVIDENCE,
    priority=ResearchPriority.CRITICAL,
    confidence_in_value_add=0.90,
    estimated_decision_impact="HIGH",
    requester="expert:HEALTHCARE_DIRECTOR",
    context={"user_tier": "premium", "industry": "healthcare"}
)

# Result: CORE returns 5 peer-reviewed papers with citations, abstracts, DOIs
# Summary: "Meta-analysis of 12 studies shows 30% reduction in hospital readmissions..."
```

**Scientific/Technical Validation**
```python
request = ResearchRequest(
    question="Academic research on AI hallucination reduction techniques in LLMs",
    category=ResearchCategory.SCIENTIFIC_VALIDATION,
    priority=ResearchPriority.IMPORTANT,
    confidence_in_value_add=0.75,
    estimated_decision_impact="HIGH",
    requester="decomposer",
    context={"user_tier": "enterprise", "industry": "ai_ml"}
)

# Result: CORE returns recent papers on RLHF, RAG, prompt engineering
# Summary: "Top 3 techniques: Retrieval-augmented generation (35% reduction), constitutional AI..."
```

**Economic/Business Strategy**
```python
request = ResearchRequest(
    question="Research on optimal SaaS pricing tier structure for SMB markets",
    category=ResearchCategory.ACADEMIC_RESEARCH,
    priority=ResearchPriority.IMPORTANT,
    confidence_in_value_add=0.70,
    estimated_decision_impact="MEDIUM",
    requester="expert:PRICING_STRATEGIST",
    context={"user_tier": "addon_academic", "business_model": "B2B SaaS"}
)

# Result: CORE returns academic studies on pricing psychology, willingness-to-pay
# Summary: "Studies show 3-tier structure optimizes conversion (42% vs 2-tier or 4-tier)..."
```

#### Pricing & Monetization Strategy

**Free Tier**
- Brave + Tavily only
- No CORE access
- Upsell prompt: "Upgrade to Premium for peer-reviewed academic research"

**Premium Tier ($29/month)**
- Brave + Tavily + **CORE (5 requests/10 sec)**
- Academic research for business decisions
- Healthcare/medical validation
- Scientific/technical evidence

**Enterprise Tier ($99/month)**
- Brave + Tavily + **CORE VIP rates** (custom rate limits)
- Unlimited academic research
- Direct CORE technical support
- Batch processing for large research projects

**Add-on: Academic Research ($15/month)**
- CORE access only (for free tier users)
- Great for consultants, researchers, healthcare professionals
- 5 requests/10 sec rate limit

#### Rate Limit Handling

```python
class CORESearchProvider(SearchProvider):
    """CORE API with rate limiting (5 requests per 10 seconds)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(max_requests=5, window_seconds=10)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search with rate limiting."""
        # Wait if rate limit exceeded
        await self.rate_limiter.acquire()

        # Execute search (implementation above)
        ...
```

#### Success Metrics

- [ ] **Adoption Rate**: 20%+ of premium users use CORE at least once/month
- [ ] **User Retention**: Premium users with CORE access have 15% higher retention vs non-CORE
- [ ] **Decision Quality**: Recommendations backed by CORE research rated 25% higher quality (user surveys)
- [ ] **Upsell Conversion**: 10%+ of free users upgrade after seeing CORE upsell prompt

#### Implementation Timeline

**Phase 1** (Week 21, 3 days):
- [ ] Add CORE API integration to `search_providers.py`
- [ ] Implement rate limiting (5 req/10 sec)
- [ ] Add `ACADEMIC_RESEARCH` categories to `ResearchCategory` enum
- [ ] Update routing logic for premium/enterprise tiers

**Phase 2** (Week 22, 2 days):
- [ ] Add `user_tier` to `ResearchRequest` context
- [ ] Implement upsell prompts for free tier users
- [ ] Create admin dashboard for CORE usage tracking

**Phase 3** (Week 23, 2 days):
- [ ] Integration testing with real CORE API
- [ ] Cost analysis (free tier, VIP tier quote)
- [ ] Documentation and user onboarding

**Total**: 7 days (post-MVP, optional premium feature)

---

---

## Dependencies

- **httpx**: HTTP client for Brave API
- **tavily-python**: Official Tavily SDK
- **OpenAI API**: Embeddings for cache (already integrated)
- **Haiku 4.5**: Summarization (already configured in MODEL_BY_ROLE)
- **PostgreSQL + pgvector**: Research cache (already set up)

---

## Timeline Summary

| Day | Phase | Hours | Deliverables |
|-----|-------|-------|--------------|
| 1 | Configuration & Setup | 4h | Config, environment, SDKs installed |
| 2 | Provider Implementation | 6h | BraveSearchProvider, TavilySearchProvider |
| 3 | ResearcherAgent Integration | 6h | Full integration, cache updates |
| 4 | Testing | 6h | Unit + integration tests, validation |
| 5 | Documentation | 4h | Docs, migration guide, roadmap update |
| **Total** | | **26h** | **Production-ready multi-provider research** |

---

**End of Plan**
