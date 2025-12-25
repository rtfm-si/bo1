# Research Provider Audit Report

**Date**: 2025-12-25
**Auditor**: Claude Code
**Status**: ✅ PASS - All call sites compliant

---

## Summary

Audited all web research call sites to verify that external web search uses Brave/Tavily APIs instead of Anthropic/OpenAI's built-in web search capabilities.

**Finding**: All research call sites are **compliant**. Anthropic/OpenAI are used exclusively for LLM inference, not web research.

---

## Call Sites Audited

### 1. `backend/services/competitor_analyzer.py`
- **Provider**: Tavily API (`api.tavily.com/search`)
- **Usage**: Competitor information lookup
- **Compliance**: ✅ PASS
- **Notes**: Uses `search_depth: "basic"`, 5 max results

### 2. `backend/services/trend_analyzer.py`
- **Provider**: Direct HTTP fetch (httpx)
- **Usage**: Fetches URL content for trend analysis
- **Compliance**: ✅ PASS (N/A - no API search, direct fetch)
- **Notes**: Claude Haiku used for summarization only, not search

### 3. `bo1/agents/researcher.py`
- **Provider**: Brave Search API (default) or Tavily (premium)
- **Usage**: External research during deliberation
- **Compliance**: ✅ PASS
- **Strategy**:
  - `basic` depth → Brave Search + Haiku summarization (~$0.025/query)
  - `deep` depth → Tavily advanced search (~$0.002/query)

### 4. `bo1/services/enrichment.py`
- **Provider**: Brave Search API
- **Usage**: Company information enrichment from website URLs
- **Compliance**: ✅ PASS
- **Notes**: Claude Haiku used for data extraction/structuring only

### 5. `bo1/graph/nodes/research.py`
- **Provider**: Delegates to `ResearcherAgent` (Brave/Tavily)
- **Compliance**: ✅ PASS
- **Notes**: Entry point for deliberation research

### 6. `bo1/llm/broker.py`
- **Provider**: Anthropic/OpenAI
- **Usage**: LLM inference (completion) only
- **Compliance**: ✅ PASS
- **Notes**: No web search tool usage; only text completion

---

## Provider Summary

| Provider | Role | Call Sites |
|----------|------|------------|
| **Brave Search** | Web search (default) | researcher.py, enrichment.py |
| **Tavily** | Web search (premium/deep) | researcher.py, competitor_analyzer.py |
| **Anthropic** | LLM inference only | broker.py (via ClaudeClient) |
| **OpenAI** | LLM inference fallback | broker.py (via OpenAIClient) |

---

## Cost Tracking

Research costs are tracked separately from LLM costs:

- Brave Search: `provider="brave"`, `operation_type="web_search"`
- Tavily: `provider="tavily"`, `operation_type="advanced_search"`
- LLM summarization: `provider="anthropic"`, `operation_type="summarization"`

All research call sites use `CostTracker.track_call()` with appropriate provider tags.

---

## Recommendations

1. **No action required** - All call sites are compliant
2. **Future consideration**: Track Brave/Tavily costs in admin dashboard ([RESEARCH][P2] task)
3. **Future consideration**: Tier research providers (Brave=starter, Tavily=pro) - ([RESEARCH][P2] task)

---

## Non-Compliant Findings

None found.
