# Embeddings & Web Research UX Opportunities

_Research completed: 2026-01-11_

## Current State Audit

### Embedding Infrastructure (MATURE)

| Component | Status | Location |
|-----------|--------|----------|
| Voyage AI client | Production | `bo1/llm/embeddings.py` |
| Batch embeddings | Production | `generate_embeddings_batch()` |
| Cosine similarity | Production | `cosine_similarity()`, `find_most_similar()` |
| pgvector storage | Production | `research_cache` table, 1024-dim vectors |
| Circuit breaker | Production | Voyage-specific breaker with retry |
| Cost tracking | Production | Per-call attribution to sessions/users |
| Semantic dedup | Production | `bo1/graph/quality/semantic_dedup.py` |
| Topic detection | Production | `backend/services/topic_detector.py` |
| Admin visualization | Production | `/admin/embeddings` - 2D projection, clustering |

### Web Research Infrastructure (MATURE)

| Provider | Use Case | Cost |
|----------|----------|------|
| Brave Search | Default web research | $0.005/query |
| Tavily AI | Deep competitor/market analysis | $0.001/query |

Current usage:
- **ResearcherAgent**: External research during deliberations (semantic cache hit ~$0.00006)
- **EnrichmentService**: Website enrichment from URLs
- **TrendSummaryGenerator**: Market intelligence from news
- **IndustryBenchmarkResearcher**: Competitor/benchmark data

---

## Prioritized UX Opportunities

### 1. Advisor Conversation Memory (HIGH VALUE)

**What**: Semantic search over past advisor conversations to find similar questions/answers.

**User value**: HIGH
- Users often ask similar questions months apart
- "What did I discuss about pricing?" currently requires manual scrolling
- TopicDetector already clusters similar questions - expose this in UI

**Implementation complexity**: SIMPLE
- TopicDetector exists (`backend/services/topic_detector.py`)
- Embeddings already cached for messages
- Add "Find similar conversations" to MentorChat
- Show related past advice when typing new question

**Dependencies**: None (infrastructure exists)

**Recommended first feature**: Add autocomplete/suggestions showing similar past Q&A when user starts typing in advisor chat.

---

### 2. Dataset Similarity Discovery (HIGH VALUE)

**What**: Find similar datasets or analyses based on semantic similarity of column names, data patterns, and insight content.

**User value**: HIGH
- Users upload similar datasets over time
- "Have I analyzed data like this before?" requires manual memory
- Cross-pollinate insights between similar datasets

**Implementation complexity**: MODERATE
- Need to embed dataset metadata (column names, sample values, generated insights)
- Store in new vector table or extend existing
- Add "Similar Datasets" panel to dataset detail page

**Dependencies**:
- New migration for dataset embeddings
- Embed on upload (async job)

---

### 3. SEO Topic Research Enhancement (MEDIUM VALUE)

**What**: Use web research to validate topic suggestions and enrich with real competitor content.

**User value**: MEDIUM
- Current topic suggestions are LLM-generated
- Web research can validate search volume, competition
- Find real competitor articles for each topic

**Implementation complexity**: MODERATE
- Brave Search for "best [topic] articles 2025"
- Extract top competitor URLs and meta descriptions
- Show "Competitors covering this topic" in topic suggestions

**Dependencies**:
- BRAVE_API_KEY (already configured)
- Rate limit consideration (batch topics)

---

### 4. Context Insight Enrichment (MEDIUM VALUE)

**What**: Auto-enrich user-submitted context insights with web-sourced supporting data.

**User value**: MEDIUM
- User adds "Our CAC is $50" - system finds industry benchmarks
- Contextualizes insights with market data
- Already partially done in benchmark alignment

**Implementation complexity**: SIMPLE
- Extend existing `IndustryBenchmarkResearcher`
- Trigger enrichment when insight is saved
- Show "Market context" tooltip on insight cards

**Dependencies**:
- API key limits (already managed)

---

### 5. Competitor Intelligence Web Research (MEDIUM VALUE)

**What**: Automatic web research when user adds competitors, finding recent news, funding, product launches.

**User value**: MEDIUM-HIGH
- CompetitorManager already has "Enrich" button
- Currently uses Brave Search for basic info
- Could add deeper intelligence: news, LinkedIn, Crunchbase data

**Implementation complexity**: MODERATE
- Extend `EnrichmentService.enrich_from_url()`
- Add Tavily deep search for competitor analysis
- Cache results in `competitor_profiles`

**Dependencies**:
- TAVILY_API_KEY (already configured)
- Consider cost per competitor ($0.001-0.005)

---

## Complexity/Value Matrix

```
                    HIGH VALUE
                        |
    [1. Advisor Memory] | [2. Dataset Similarity]
         SIMPLE         |      MODERATE
                        |
    --------------------|--------------------
                        |
    [4. Insight Enrich] | [3. SEO Research]
         SIMPLE         | [5. Competitor Intel]
                        |      MODERATE
                        |
                    LOW VALUE
```

---

## Recommended First Implementation

**Advisor Conversation Search** (Opportunity #1)

Rationale:
1. Infrastructure already exists (TopicDetector, embeddings cached)
2. High user impact - solves "what did I ask before?" problem
3. Simple implementation - UI addition only
4. Zero new API costs (embeddings already generated)

### Implementation Sketch

1. Add search input to MentorChat header
2. On keystroke (debounced), call `TopicDetector.find_similar_questions()`
3. Show dropdown with matching past conversations
4. Click to load conversation context or insert as reference

```typescript
// New API endpoint
GET /api/v1/advisor/search?q=pricing strategy
// Returns: { matches: [{ conversation_id, preview, similarity }] }
```

---

## Existing Code to Leverage

| Feature | Existing Code | Notes |
|---------|---------------|-------|
| Message embeddings | `TopicDetector._get_cached_embedding()` | 7-day cache |
| Similarity search | `cache_repository.find_similar()` | pgvector HNSW |
| Batch embedding | `generate_embeddings_batch()` | Efficient batching |
| Web research | `ResearcherAgent.research_questions()` | Semantic cache |
| Trend summaries | `TrendSummaryGenerator` | Brave + Haiku |
| Competitor enrichment | `EnrichmentService` | URL analysis |

---

## Not Recommended (Low ROI)

- **Full-text search replacement**: Current UX doesn't require it; semantic search better
- **Real-time web widgets**: High cost, low differentiation from existing trend panels
- **Chat with documents**: Out of scope for Bo1's advisor focus

---

## Next Steps

To convert these into actionable tasks:

1. **Phase 1** (Advisor Search): Add conversation search UI using existing TopicDetector
2. **Phase 2** (Dataset Similarity): Embed dataset metadata, add similarity panel
3. **Phase 3** (SEO Enrichment): Web-validate topics with competitor analysis
