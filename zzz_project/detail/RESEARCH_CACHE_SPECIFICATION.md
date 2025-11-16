# External Research Cache with Embeddings - Specification

**Status**: Planned for Week 6 (Day 37-38)
**Dependencies**: Context Collection Feature, pgvector extension

---

## Executive Summary

**Problem**: External research gaps (industry benchmarks, competitor data, market trends) are expensive to research via web search APIs + LLM summarization (~$0.05-0.10 per question).

**Solution**: Cache research results with embeddings for semantic similarity matching. When a similar question is asked, return cached results instead of re-researching.

**Impact**:
- **Cost Reduction**: 70-90% fewer web searches (most questions are variations of common themes)
- **Speed**: Cached results return in ~50ms vs 5-10 seconds for fresh research
- **Quality**: Aggregated knowledge over time (multiple sources → better answers)

---

## Research Cache Architecture

### Database Schema

```sql
-- Research cache table (persistent, shared across all users)
CREATE TABLE research_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Question & Answer
    question TEXT NOT NULL,
    question_embedding vector(1024),  -- Voyage AI voyage-3 embeddings
    answer_summary TEXT NOT NULL,
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),

    -- Sources
    sources JSONB,  -- [{"url": "...", "title": "...", "snippet": "..."}]
    source_count INT,

    -- Metadata
    category TEXT,  -- 'pricing', 'churn', 'saas_metrics', 'competitor_analysis', etc.
    industry TEXT,  -- 'saas', 'e-commerce', 'marketplace', etc.
    research_date TIMESTAMP DEFAULT NOW(),

    -- Cache management
    access_count INT DEFAULT 1,
    last_accessed_at TIMESTAMP DEFAULT NOW(),
    freshness_days INT DEFAULT 90,  -- How long before re-research

    -- Search optimization
    tokens_used INT,
    research_cost_usd DECIMAL(10, 6),

    -- Full-text search
    question_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', question)) STORED
);

-- Indexes
CREATE INDEX idx_research_cache_embedding ON research_cache
    USING ivfflat (question_embedding vector_cosine_ops);
CREATE INDEX idx_research_cache_category ON research_cache(category);
CREATE INDEX idx_research_cache_industry ON research_cache(industry);
CREATE INDEX idx_research_cache_freshness ON research_cache(research_date);
CREATE INDEX idx_research_cache_tsv ON research_cache USING GIN(question_tsv);

-- Composite index for category + industry filtering
CREATE INDEX idx_research_cache_cat_ind ON research_cache(category, industry);

-- Trigger to update last_accessed_at
CREATE OR REPLACE FUNCTION update_research_cache_access()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed_at = NOW();
    NEW.access_count = OLD.access_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_research_cache_access
    BEFORE UPDATE ON research_cache
    FOR EACH ROW
    WHEN (NEW.question = OLD.question)
    EXECUTE FUNCTION update_research_cache_access();
```

### Research Result Aggregation

When multiple cached results are found, aggregate for higher confidence:

```sql
-- Research result aggregation (combines similar cached results)
CREATE TABLE research_aggregations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Aggregation metadata
    question_cluster TEXT,  -- Representative question for this cluster
    cluster_embedding vector(1024),  -- Voyage AI voyage-3 embeddings

    -- Aggregated results
    combined_summary TEXT,  -- Synthesized from multiple sources
    source_cache_ids UUID[],  -- Links to research_cache entries
    total_sources INT,

    -- Quality metrics
    confidence TEXT,
    agreement_score DECIMAL(3, 2),  -- 0.0-1.0, how much sources agree

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Research Caching Flow

### 1. Query with Cache Check

```
User Question: "What is the average churn rate for B2B SaaS?"
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. Generate Embedding (question)                           │
│    - Voyage AI voyage-3: ~$0.00006 per 1K tokens           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Semantic Similarity Search (pgvector)                   │
│    - Find cached questions with cosine similarity > 0.85   │
│    - Filter by category, industry (if specified)           │
│    - Check freshness (research_date within freshness_days) │
└─────────────────────────────────────────────────────────────┘
                          ↓
                   ┌──────┴──────┐
                   │             │
              CACHE HIT      CACHE MISS
                   │             │
                   ↓             ↓
┌──────────────────────────┐  ┌──────────────────────────┐
│ 3a. Return Cached Result │  │ 3b. Perform Research     │
│  - Update access_count   │  │  - Web search (Brave)    │
│  - Update last_accessed  │  │  - Extract content       │
│  - Cost: ~$0.00006       │  │  - Summarize (Haiku)     │
│  - Time: ~50ms           │  │  - Cache result          │
│                          │  │  - Cost: ~$0.05-0.10     │
│                          │  │  - Time: ~5-10 seconds   │
└──────────────────────────┘  └──────────────────────────┘
```

### 2. Semantic Similarity Matching

**Example Variations** (all would match same cached result):
- "What is the average churn rate for B2B SaaS?" (original)
- "Average monthly churn for SaaS companies?" (90% similar)
- "How much customer churn do B2B software companies experience?" (88% similar)
- "Typical SaaS churn rate benchmarks?" (92% similar)

**Similarity Threshold**: 0.85 (configurable)
- 0.85-1.0: Cache hit (return cached result)
- 0.70-0.84: Similar but not identical (optional: aggregate multiple results)
- <0.70: Cache miss (perform new research)

**Prioritization Order** (when multiple matches found):
1. **Similarity** (highest first) - Most relevant match
2. **Recency** (newest first) - More recent data preferred
3. **Popularity** (most accessed first) - Community-validated quality

### 3. Freshness Management

Research becomes stale over time. Freshness policy:

| Category | Freshness Period | Rationale |
|----------|-----------------|-----------|
| `saas_metrics` | 90 days | Industry benchmarks change quarterly |
| `pricing` | 180 days | Pricing strategies evolve slowly |
| `competitor_analysis` | 30 days | Competitive landscape changes fast |
| `market_trends` | 60 days | Trends evolve monthly |
| `regulations` | 365 days | Regulations change annually |

**Stale Handling**:
- If cached result is stale → trigger background re-research
- Return stale result immediately (don't block user)
- Next user gets fresh result

---

## Implementation

### ResearcherAgent Cache Integration

```python
# bo1/agents/researcher.py

import asyncio
from typing import Any
import numpy as np
from bo1.state.postgres_manager import (
    find_cached_research,
    save_research_result,
    update_research_access,
)
from bo1.llm.embeddings import generate_embedding

class ResearcherAgent:
    """Agent for researching external information gaps with caching."""

    async def research_questions(
        self,
        questions: list[dict[str, Any]],
        category: str | None = None,
        industry: str | None = None,
    ) -> list[dict[str, Any]]:
        """Research external questions with semantic cache.

        Args:
            questions: List of external gaps from identify_information_gaps()
                Format: [{"question": "...", "priority": "...", "reason": "..."}]
            category: Optional category filter ('pricing', 'churn', etc.)
            industry: Optional industry filter ('saas', 'e-commerce', etc.)

        Returns:
            List of research results with cache metadata:
            [
                {
                    "question": "...",
                    "summary": "...",
                    "sources": [...],
                    "confidence": "high|medium|low",
                    "cached": True|False,
                    "cache_age_days": 15 (if cached),
                }
            ]
        """
        results = []

        for question_data in questions:
            question = question_data.get("question", "")

            # 1. Generate embedding for semantic search
            embedding = await generate_embedding(question)

            # 2. Check cache with similarity threshold
            cached_result = await find_cached_research(
                question_embedding=embedding,
                similarity_threshold=0.85,
                category=category,
                industry=industry,
                max_age_days=self._get_freshness_days(category),
            )

            if cached_result:
                # CACHE HIT
                await update_research_access(cached_result["id"])

                results.append({
                    "question": question,
                    "summary": cached_result["answer_summary"],
                    "sources": cached_result["sources"],
                    "confidence": cached_result["confidence"],
                    "cached": True,
                    "cache_age_days": cached_result["age_days"],
                })

                logger.info(
                    f"✓ Cache hit for '{question[:50]}...' "
                    f"(similarity: {cached_result['similarity']:.2f}, "
                    f"age: {cached_result['age_days']} days)"
                )

            else:
                # CACHE MISS - perform research
                research_result = await self._perform_web_research(question)

                # Save to cache
                await save_research_result(
                    question=question,
                    question_embedding=embedding,
                    answer_summary=research_result["summary"],
                    sources=research_result["sources"],
                    confidence=research_result["confidence"],
                    category=category,
                    industry=industry,
                    tokens_used=research_result["tokens_used"],
                    research_cost_usd=research_result["cost"],
                )

                results.append({
                    "question": question,
                    "summary": research_result["summary"],
                    "sources": research_result["sources"],
                    "confidence": research_result["confidence"],
                    "cached": False,
                })

                logger.info(
                    f"✓ Researched '{question[:50]}...' "
                    f"(cost: ${research_result['cost']:.4f}, "
                    f"sources: {len(research_result['sources'])})"
                )

        return results

    def _get_freshness_days(self, category: str | None) -> int:
        """Get freshness period for category."""
        freshness_map = {
            "saas_metrics": 90,
            "pricing": 180,
            "competitor_analysis": 30,
            "market_trends": 60,
            "regulations": 365,
        }
        return freshness_map.get(category, 90)  # Default: 90 days

    async def _perform_web_research(self, question: str) -> dict[str, Any]:
        """Perform actual web research (Brave Search + summarization).

        Week 4+ implementation - currently a stub.
        """
        # Placeholder - will integrate Brave Search API + Haiku summarization
        return {
            "summary": "[Research pending - Week 4 implementation]",
            "sources": [],
            "confidence": "stub",
            "tokens_used": 0,
            "cost": 0.0,
        }
```

### PostgreSQL Functions

```python
# bo1/state/postgres_manager.py

import asyncpg
from typing import Any

async def find_cached_research(
    question_embedding: list[float],
    similarity_threshold: float = 0.85,
    category: str | None = None,
    industry: str | None = None,
    max_age_days: int = 90,
) -> dict[str, Any] | None:
    """Find cached research result by semantic similarity.

    Args:
        question_embedding: Embedding vector for the question
        similarity_threshold: Minimum cosine similarity (0.0-1.0)
        category: Optional category filter
        industry: Optional industry filter
        max_age_days: Maximum age of cached result in days

    Returns:
        Cached result with similarity score and age, or None if no match
    """
    query = """
        SELECT
            id,
            question,
            answer_summary,
            confidence,
            sources,
            1 - (question_embedding <=> $1::vector) AS similarity,
            EXTRACT(DAY FROM NOW() - research_date) AS age_days,
            access_count,
            research_date
        FROM research_cache
        WHERE
            (1 - (question_embedding <=> $1::vector)) >= $2
            AND ($3::TEXT IS NULL OR category = $3)
            AND ($4::TEXT IS NULL OR industry = $4)
            AND research_date >= NOW() - INTERVAL '1 day' * $5
        ORDER BY similarity DESC, research_date DESC, access_count DESC
        LIMIT 1
    """

    conn = await get_db_connection()

    row = await conn.fetchrow(
        query,
        question_embedding,
        similarity_threshold,
        category,
        industry,
        max_age_days,
    )

    if not row:
        return None

    return {
        "id": row["id"],
        "question": row["question"],
        "answer_summary": row["answer_summary"],
        "confidence": row["confidence"],
        "sources": row["sources"],
        "similarity": row["similarity"],
        "age_days": int(row["age_days"]),
        "access_count": row["access_count"],
    }


async def save_research_result(
    question: str,
    question_embedding: list[float],
    answer_summary: str,
    sources: list[dict[str, str]],
    confidence: str,
    category: str | None = None,
    industry: str | None = None,
    tokens_used: int = 0,
    research_cost_usd: float = 0.0,
) -> str:
    """Save research result to cache.

    Args:
        question: The research question
        question_embedding: Embedding vector for semantic search
        answer_summary: Summarized answer (200-300 tokens)
        sources: List of source URLs with metadata
        confidence: 'high', 'medium', or 'low'
        category: Research category
        industry: Industry context
        tokens_used: Total tokens for research + summarization
        research_cost_usd: Total cost in USD

    Returns:
        Cache entry ID (UUID)
    """
    query = """
        INSERT INTO research_cache (
            question,
            question_embedding,
            answer_summary,
            confidence,
            sources,
            source_count,
            category,
            industry,
            tokens_used,
            research_cost_usd
        )
        VALUES ($1, $2::vector, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
    """

    conn = await get_db_connection()

    result = await conn.fetchval(
        query,
        question,
        question_embedding,
        answer_summary,
        confidence,
        json.dumps(sources),
        len(sources),
        category,
        industry,
        tokens_used,
        research_cost_usd,
    )

    return str(result)


async def update_research_access(cache_id: str) -> None:
    """Update access count and last_accessed_at for cached result.

    This is handled by database trigger, but we call it explicitly
    for clarity.
    """
    query = """
        UPDATE research_cache
        SET
            access_count = access_count + 1,
            last_accessed_at = NOW()
        WHERE id = $1
    """

    conn = await get_db_connection()
    await conn.execute(query, cache_id)
```

### Embedding Generation

```python
# bo1/llm/embeddings.py

import os
import voyageai

async def generate_embedding(
    text: str,
    model: str = "voyage-3",
    input_type: str | None = None,
) -> list[float]:
    """Generate embedding vector for semantic similarity.

    Args:
        text: Text to embed (question, typically)
        model: Voyage AI embedding model (voyage-3 = 1024 dimensions)
        input_type: Optional - 'query' or 'document' for optimized retrieval

    Returns:
        List of floats (embedding vector)

    Cost:
        voyage-3: ~$0.00006 per 1K tokens (10x cheaper than OpenAI ada-002)
    """
    api_key = os.getenv("VOYAGEAI_API_KEY")
    client = voyageai.Client(api_key=api_key)

    result = client.embed(
        texts=[text.strip()],
        model=model,
        input_type=input_type,
    )

    return result.embeddings[0]
```

---

## Cache Analytics Dashboard (Admin)

Track cache performance metrics:

```sql
-- Cache hit rate (last 30 days)
SELECT
    DATE(created_at) AS date,
    COUNT(*) FILTER (WHERE cached = TRUE) AS cache_hits,
    COUNT(*) FILTER (WHERE cached = FALSE) AS cache_misses,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE cached = TRUE) / COUNT(*),
        2
    ) AS hit_rate_percent
FROM research_logs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Most frequently accessed cached results
SELECT
    question,
    access_count,
    EXTRACT(DAY FROM NOW() - research_date) AS age_days,
    confidence,
    category,
    industry
FROM research_cache
ORDER BY access_count DESC
LIMIT 20;

-- Cost savings from cache
SELECT
    SUM(research_cost_usd) FILTER (WHERE cached = FALSE) AS total_research_cost,
    COUNT(*) FILTER (WHERE cached = TRUE) AS cache_hits,
    AVG(research_cost_usd) FILTER (WHERE cached = FALSE) AS avg_research_cost,
    COUNT(*) FILTER (WHERE cached = TRUE) * AVG(research_cost_usd) FILTER (WHERE cached = FALSE) AS estimated_savings
FROM research_logs
WHERE created_at >= NOW() - INTERVAL '30 days';
```

---

## Cache Maintenance

### Background Jobs

1. **Stale Result Refresh** (daily cron)
   - Find results with `research_date` older than `freshness_days`
   - Re-research top 10 most accessed stale results
   - Update cache entries

2. **Low-Usage Pruning** (weekly cron)
   - Delete results with `access_count = 1` and `age_days > 180`
   - Rationale: If only used once in 6 months, unlikely to be used again

3. **Embedding Index Optimization** (monthly)
   - Rebuild ivfflat index for optimal performance
   - `REINDEX INDEX idx_research_cache_embedding;`

---

## Testing Strategy

### Unit Tests

```python
# tests/agents/test_researcher_cache.py

async def test_research_cache_hit():
    """Identical question returns cached result."""
    # Pre-populate cache
    await save_research_result(
        question="What is average SaaS churn rate?",
        embedding=test_embedding,
        answer_summary="Average SaaS churn: 5-7% annually",
        sources=[...],
        confidence="high",
    )

    # Research same question
    agent = ResearcherAgent()
    results = await agent.research_questions([
        {"question": "What is average SaaS churn rate?", "priority": "CRITICAL"}
    ])

    assert results[0]["cached"] is True
    assert results[0]["summary"] == "Average SaaS churn: 5-7% annually"


async def test_research_cache_prioritizes_recent():
    """When multiple matches exist, most recent is returned."""
    # Pre-populate cache with two similar results
    old_embedding = generate_test_embedding("What is average SaaS churn?")
    await save_research_result(
        question="What is average SaaS churn rate?",
        embedding=old_embedding,
        answer_summary="Average SaaS churn: 5-7% annually (2024 data)",
        sources=[...],
        confidence="high",
        research_date=datetime.now() - timedelta(days=80),  # 80 days old
    )

    new_embedding = generate_test_embedding("What is typical SaaS churn?")
    await save_research_result(
        question="What is typical SaaS churn rate?",
        embedding=new_embedding,
        answer_summary="Average SaaS churn: 4-6% annually (2025 data)",
        sources=[...],
        confidence="high",
        research_date=datetime.now() - timedelta(days=10),  # 10 days old
    )

    # Both have similar embeddings (>0.85 similarity to query)
    # Should return the more recent one
    agent = ResearcherAgent()
    results = await agent.research_questions([
        {"question": "Average churn for SaaS companies?", "priority": "CRITICAL"}
    ])

    assert results[0]["cached"] is True
    assert "2025 data" in results[0]["summary"]  # More recent result
    assert results[0]["cache_age_days"] < 20


async def test_research_semantic_similarity():
    """Similar question matches cached result (>0.85 similarity)."""
    # Pre-populate cache
    await save_research_result(
        question="What is average SaaS churn rate?",
        embedding=test_embedding,
        answer_summary="Average SaaS churn: 5-7% annually",
        sources=[...],
        confidence="high",
    )

    # Research semantically similar question
    agent = ResearcherAgent()
    results = await agent.research_questions([
        {"question": "Typical churn for B2B SaaS companies?", "priority": "CRITICAL"}
    ])

    assert results[0]["cached"] is True  # Should match cached result


async def test_research_cache_miss():
    """Dissimilar question triggers new research."""
    agent = ResearcherAgent()
    results = await agent.research_questions([
        {"question": "What is the capital of France?", "priority": "CRITICAL"}
    ])

    assert results[0]["cached"] is False  # No similar cached result


async def test_research_freshness_filter():
    """Stale cached result not returned."""
    # Pre-populate cache with 100-day-old result
    await save_research_result(
        question="What is average SaaS churn rate?",
        embedding=test_embedding,
        answer_summary="Average SaaS churn: 5-7% annually",
        sources=[...],
        confidence="high",
        research_date=datetime.now() - timedelta(days=100),  # Stale
    )

    # Research with 90-day freshness requirement
    agent = ResearcherAgent()
    results = await agent.research_questions(
        [{"question": "What is average SaaS churn rate?", "priority": "CRITICAL"}],
        category="saas_metrics",  # 90-day freshness
    )

    assert results[0]["cached"] is False  # Stale result ignored
```

### Integration Tests

```python
# tests/integration/test_research_cache_integration.py

async def test_full_research_flow_with_cache():
    """Full deliberation with cached external research."""
    # 1. First deliberation - research happens
    session_1 = await create_deliberation_session(
        problem="Should I invest $100K in SEO or paid ads?",
        category="saas",
    )

    # Gap: "Average CAC for B2B SaaS via SEO vs paid ads"
    # External research performed, result cached

    # 2. Second deliberation - cache hit
    session_2 = await create_deliberation_session(
        problem="Should I focus on SEO or Google Ads for customer acquisition?",
        category="saas",
    )

    # Same gap identified, cache returns result
    # Verify cost reduction

    assert session_2.research_cost < session_1.research_cost
    assert session_2.research_time < session_1.research_time
```

---

## API Endpoints (Admin)

```python
# backend/api/admin.py

@router.get("/api/admin/research-cache/stats")
async def get_research_cache_stats():
    """Get cache performance metrics."""
    return {
        "total_cached_results": await count_cached_results(),
        "cache_hit_rate_30d": await calculate_hit_rate(days=30),
        "cost_savings_30d": await calculate_cost_savings(days=30),
        "top_cached_questions": await get_top_cached_questions(limit=20),
    }

@router.delete("/api/admin/research-cache/{cache_id}")
async def delete_cached_result(cache_id: str):
    """Delete specific cached result (admin only)."""
    await delete_research_cache_entry(cache_id)
    return {"status": "deleted"}

@router.post("/api/admin/research-cache/refresh-stale")
async def refresh_stale_cache():
    """Trigger background re-research of stale results."""
    task_id = await queue_stale_refresh_job()
    return {"status": "queued", "task_id": task_id}
```

---

## Cost Analysis

### Without Cache

- **100 deliberations/month**
- **Average 3 external gaps per deliberation**
- **Total research queries**: 300/month
- **Cost per query**: ~$0.07 (web search $0.02 + summarization $0.05)
- **Total monthly cost**: $21.00

### With Cache (70% hit rate after 1 month)

- **100 deliberations/month**
- **300 research queries**
- **Cache hits**: 210 (70%)
- **Cache misses**: 90 (30%)
- **Cache hit cost**: 210 × $0.00006 = $0.01 (Voyage AI embeddings only)
- **Cache miss cost**: 90 × $0.07 = $6.30
- **Total monthly cost**: $6.31
- **Savings**: $14.69/month (70% reduction)

### With Cache (90% hit rate after 3 months)

- **Cache hits**: 270 (90%)
- **Cache misses**: 30 (10%)
- **Cache hit cost**: 270 × $0.00006 = $0.02 (Voyage AI embeddings)
- **Cache miss cost**: 30 × $0.07 = $2.10
- **Total monthly cost**: $2.12
- **Savings**: $18.88/month (90% reduction)

---

## Roadmap Updates

### Day 36 (Database Schema)

Add to existing tasks:

- [ ] Create `research_cache` table migration
- [ ] Install pgvector extension (if not already installed)
- [ ] Create ivfflat index on `question_embedding`
- [ ] Create `research_aggregations` table (optional, future enhancement)
- [ ] Add cache analytics views

### Day 37 (Research Integration)

- [ ] Implement `generate_embedding()` in `bo1/llm/embeddings.py`
- [ ] Implement `find_cached_research()` in `bo1/state/postgres_manager.py`
- [ ] Implement `save_research_result()` in `bo1/state/postgres_manager.py`
- [ ] Update `ResearcherAgent.research_questions()` to use cache
- [ ] Add cache metadata to research results (cached, age_days, similarity)
- [ ] Write unit tests for cache hit/miss/freshness

### Day 38 (Admin Endpoints)

- [ ] Add `GET /api/admin/research-cache/stats` - Cache analytics
- [ ] Add `DELETE /api/admin/research-cache/{id}` - Delete cached result
- [ ] Add `POST /api/admin/research-cache/refresh-stale` - Refresh stale cache

---

## Success Metrics

- [ ] Cache hit rate >70% after 1 month of usage
- [ ] Cache hit rate >90% after 3 months of usage
- [ ] Research cost reduced by 70-90%
- [ ] Average research time <100ms (vs 5-10 seconds without cache)
- [ ] Embedding generation <50ms per question
- [ ] Semantic similarity matching <30ms per query

---

## Recency Benefits

### Why Prioritize Recent Data?

1. **Accuracy**: Industry benchmarks change over time
   - Example: SaaS churn was 7% in 2023, but 5% in 2025 (improved retention)

2. **Relevance**: Market conditions evolve
   - Example: CAC via paid ads doubled after iOS 14 privacy changes

3. **Trend Awareness**: Recent data reflects current reality
   - Example: Remote work adoption changed hiring benchmarks

### Recency vs Popularity Trade-off

**Prioritization Order**: `similarity DESC, research_date DESC, access_count DESC`

| Scenario | Result 1 | Result 2 | Selected | Reason |
|----------|----------|----------|----------|---------|
| Same similarity (0.92) | 15 days old, 5 accesses | 80 days old, 100 accesses | Result 1 | Recency > Popularity |
| Different similarity | 0.95 similarity, 80 days | 0.88 similarity, 10 days | Result 1 | Similarity > Recency |
| Same similarity + date | 0.92, 15 days, 10 access | 0.92, 15 days, 100 access | Result 2 | Popularity tie-breaker |

**Design Principle**: Relevance (similarity) > Freshness (recency) > Validation (popularity)

---

## Future Enhancements (Post-MVP)

1. **Multi-Result Aggregation**: Combine multiple similar cached results for higher confidence
2. **Active Learning**: Track which cached results were helpful, improve similarity thresholds
3. **Category Auto-Classification**: ML model to auto-assign category/industry from question text
4. **Cross-User Sharing**: Anonymized cache shared across all users (privacy-preserving)
5. **Proactive Cache Warming**: Pre-research common questions before users ask
6. **Trend Analysis**: Compare cached results over time to detect trends
   - Example: "How has SaaS churn changed from 2023 to 2025?"
   - Query multiple cached results across date ranges
7. **Confidence Decay**: Reduce confidence score as results age
   - Example: 90-day-old result → confidence: "medium" (was "high")

---

**End of Specification**
