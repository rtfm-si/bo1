# Plan: Competitor Intelligence - Deeper Web Research

## Summary

- Enhance competitor enrichment with deeper web research (news, funding, product updates)
- Extend Tavily integration to include Crunchbase, LinkedIn, TechCrunch, industry blogs
- Add intelligence categories: recent news, funding rounds, product launches, key hires
- Display enriched data in CompetitorManager with collapsible intelligence panels

## Implementation Steps

1. **Create `CompetitorIntelligenceService`** (`backend/services/competitor_intelligence.py`)
   - `gather_competitor_intel(name: str, website: str | None, depth: str) -> CompetitorIntel`
   - Multi-query Tavily search:
     - `"{name}" funding OR raised OR series` (Crunchbase, TechCrunch)
     - `"{name}" product launch OR release OR update` (press, blogs)
     - `"{name}" news 2025 OR 2026` (recent coverage)
   - Parse results with LLM (Haiku) into structured intelligence categories
   - Return: `funding_rounds`, `product_updates`, `recent_news`, `key_signals`

2. **Extend `ManagedCompetitor` model** (`backend/api/context/models.py`)
   - Add fields: `product_updates: list[dict] | None`, `key_signals: list[str] | None`
   - Add `intel_gathered_at: datetime | None` timestamp for freshness
   - `product_updates`: list of `{title, date, description, source_url}`
   - `key_signals`: list of notable signals (e.g., "Raised Series B", "Launched AI feature")

3. **Update `enrich_competitor_with_tavily()`** (`backend/api/competitors.py`)
   - For `deep` tier: call `CompetitorIntelligenceService.gather_competitor_intel()`
   - Merge intel results into existing enrichment flow
   - Update DB columns: `product_updates`, `key_signals`, `intel_gathered_at`

4. **Add migration for new columns** (`migrations/versions/zzz_competitor_intel.py`)
   - Add `product_updates JSONB`, `key_signals JSONB`, `intel_gathered_at TIMESTAMPTZ`
   - Add index on `intel_gathered_at` for freshness queries

5. **Frontend: Extend CompetitorManager UI** (`frontend/src/lib/components/context/CompetitorManager.svelte`)
   - Add TypeScript types for new intel fields
   - Display intelligence panel when expanded:
     - Recent news cards with date, headline, source link
     - Funding info with badge (if available)
     - Product updates as timeline
     - Key signals as chips/badges
   - Add "Gather Intel" button (separate from basic Enrich) for pro tier

6. **Add tests** (`tests/services/test_competitor_intelligence.py`)
   - Unit tests for `CompetitorIntelligenceService`
   - Mock Tavily responses, test LLM parsing
   - Integration test for enrichment flow with intel

## Tests

- Unit tests:
  - `CompetitorIntelligenceService.gather_competitor_intel()` with mock Tavily
  - LLM parsing of search results into structured intel
  - Handling missing/empty results gracefully
- Integration tests:
  - Full enrichment flow with deep tier calling intel service
  - Intel fields persisted to DB and returned in GET
  - Frontend displays intel correctly (Playwright optional)
- Manual validation:
  - Test with real competitor (e.g., "Notion") to verify quality

## Dependencies & Risks

- Dependencies:
  - Tavily API key (already configured, $0.001/query)
  - Haiku for parsing (~$0.002/call)
  - Pro tier gate for deep intel (already exists)
- Risks:
  - API cost: ~$0.01 per competitor deep refresh (3 queries + parsing)
  - Rate limiting: Tavily has limits; add backoff
  - Stale intel: Add 30-day freshness indicator, "Refresh Intel" button
