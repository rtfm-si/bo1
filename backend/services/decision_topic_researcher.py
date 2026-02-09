"""Decision topic researcher service.

Discovers high-intent SEO decision topics via Brave + Tavily + Haiku scoring.
Topics map to founder dilemmas that Board of One can help solve.

Cost: ~$0.07 per research run (admin-only, infrequent).
"""

import logging
import os
from typing import Any

import httpx

from bo1.config import get_settings
from bo1.llm.client import ClaudeClient
from bo1.llm.response_parser import extract_json_from_response
from bo1.state.repositories.decision_repository import (
    DECISION_CATEGORIES,
    decision_repository,
)
from bo1.state.repositories.topic_bank_repository import topic_bank_repository

logger = logging.getLogger(__name__)

USE_MOCK = os.getenv("USE_MOCK_TOPIC_RESEARCHER", "").lower() == "true"

POSITIONING_KEYWORDS = [
    "compress management work",
    "management operating system",
    "delay management hires",
    "founder bottleneck",
    "coordination tax",
    "solo founder",
    "expert perspectives",
    "strategic decisions",
]

BRAVE_QUERIES = [
    "solo founder strategic decisions when to hire",
    "startup founder decisions pricing strategy",
    "when should a startup founder raise funding seed round",
    "solo founder pivot or persevere decision framework",
    "startup founder hire first engineer or use contractors",
    "startup pricing decisions freemium vs paid",
    "founder decisions marketing channel strategy",
    "solo founder operations scale decisions",
]

TAVILY_QUERIES = [
    "most common high-stakes startup founder decisions dilemmas",
    "founder decision frameworks strategic choices solo entrepreneur",
]


async def _brave_search(queries: list[str]) -> list[dict[str, Any]]:
    """Run Brave searches and collect raw results."""
    settings = get_settings()
    api_key = settings.brave_api_key

    if not api_key:
        logger.warning("BRAVE_API_KEY not set - skipping Brave search")
        return []

    results = []
    async with httpx.AsyncClient() as client:
        for query in queries:
            try:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": api_key},
                    params={"q": query, "count": 5},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                for r in data.get("web", {}).get("results", []):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "snippet": r.get("description", ""),
                            "url": r.get("url", ""),
                            "source": "brave",
                        }
                    )
            except Exception as e:
                logger.warning(f"Brave search failed for '{query[:50]}': {e}")

    logger.info(f"Brave: collected {len(results)} raw results from {len(queries)} queries")
    return results


async def _tavily_search(queries: list[str]) -> list[dict[str, Any]]:
    """Run Tavily deep searches and collect raw results."""
    settings = get_settings()
    api_key = settings.tavily_api_key

    if not api_key:
        logger.warning("TAVILY_API_KEY not set - skipping Tavily search")
        return []

    results = []
    async with httpx.AsyncClient() as client:
        for query in queries:
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "include_answer": True,
                        "include_raw_content": False,
                        "max_results": 5,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("answer"):
                    results.append(
                        {
                            "title": query,
                            "snippet": data["answer"],
                            "url": "",
                            "source": "tavily",
                        }
                    )

                for r in data.get("results", []):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "snippet": r.get("content", ""),
                            "url": r.get("url", ""),
                            "source": "tavily",
                        }
                    )
            except Exception as e:
                logger.warning(f"Tavily search failed for '{query[:50]}': {e}")

    logger.info(f"Tavily: collected {len(results)} raw results from {len(queries)} queries")
    return results


def _get_mock_topics() -> list[dict[str, Any]]:
    """Return mock topics for dev/testing."""
    return [
        {
            "title": "When to Hire Your First Head of Sales",
            "description": "Solo founders wrestle with whether to keep selling themselves or hire a dedicated sales leader. The timing depends on pipeline size, deal complexity, and founder bandwidth.",
            "category": "hiring",
            "keywords": ["hire head of sales", "startup sales leader", "founder-led sales"],
            "seo_score": 0.85,
            "reasoning": "High search volume for 'when to hire sales leader startup'. Founders actively search this when hitting revenue plateaus.",
            "bo1_alignment": "Bo1's multi-expert deliberation helps founders weigh the cost of a senior hire against the opportunity cost of founder time spent selling. Structured analysis compresses weeks of deliberation into hours.",
            "source": "mock",
        },
        {
            "title": "Should I Raise a Seed Round or Bootstrap Further?",
            "description": "The decision to take outside funding affects control, growth pace, and founder lifestyle. Many founders face this inflection point at $10-50K MRR.",
            "category": "fundraising",
            "keywords": ["raise seed round", "bootstrap vs fundraise", "startup funding decision"],
            "seo_score": 0.82,
            "reasoning": "Evergreen topic with steady search intent. Founders revisit this decision multiple times.",
            "bo1_alignment": "Expert perspectives from finance, strategy, and operations angles help founders see trade-offs they'd miss alone. Delays the need for expensive advisory hires.",
            "source": "mock",
        },
    ]


SCORING_PROMPT = """You are an SEO content strategist for Board of One (Bo1), a tool that helps solo founders make strategic decisions through AI-powered expert deliberation.

Board of One's positioning:
- {positioning_keywords}

## Task
Analyze the search results below and extract {max_topics} high-intent decision topics that solo founders actually search for.

## Requirements for each topic
1. **Title**: Decision-framed ("Should I...", "When to...", "How to decide...")
2. **Description**: 2-3 sentence dilemma summary explaining the tension
3. **Category**: One of: {categories}
4. **Keywords**: 3-5 SEO target phrases founders would search
5. **seo_score**: 0.0-1.0 based on search volume signal + founder relevance
6. **Reasoning**: Why this topic drives high-intent organic traffic
7. **bo1_alignment**: How Board of One's multi-expert deliberation specifically helps (reference: compressing management work, expert perspectives, structured analysis, delaying costly hires)

## Deduplication
Skip topics similar to these existing titles:
{existing_titles}

## Search Results
{search_results}

Return ONLY a JSON object:
{{"topics": [{{
  "title": "...",
  "description": "...",
  "category": "...",
  "keywords": ["..."],
  "seo_score": 0.85,
  "reasoning": "...",
  "bo1_alignment": "..."
}}]}}"""


async def research_decision_topics(max_topics: int = 10) -> list[dict[str, Any]]:
    """Research and score decision topics for the topic bank.

    Args:
        max_topics: Maximum number of topics to return

    Returns:
        List of scored topic dicts, saved to topic bank
    """
    if USE_MOCK:
        topics = _get_mock_topics()[:max_topics]
        created = topic_bank_repository.bulk_create(topics)
        return created

    # 1. Gather existing titles for dedup
    existing_decision_titles = [d["title"] for d in decision_repository.list_decisions(limit=500)]
    existing_bank_titles = topic_bank_repository.get_existing_titles()
    all_existing = existing_decision_titles + existing_bank_titles

    # 2. Run searches in parallel-ish (Brave then Tavily)
    brave_results = await _brave_search(BRAVE_QUERIES)
    tavily_results = await _tavily_search(TAVILY_QUERIES)
    all_results = brave_results + tavily_results

    if not all_results:
        logger.warning("No search results collected - returning empty")
        return []

    # 3. Format for LLM scoring
    search_text = "\n\n".join(
        f"[{r['source']}] {r['title']}\n{r['snippet'][:300]}"
        for r in all_results[:40]  # cap context size
    )

    prompt = SCORING_PROMPT.format(
        positioning_keywords=", ".join(POSITIONING_KEYWORDS),
        max_topics=max_topics,
        categories=", ".join(DECISION_CATEGORIES),
        existing_titles="\n".join(f"- {t}" for t in all_existing) if all_existing else "None",
        search_results=search_text,
    )

    # 4. Call Haiku for scoring
    client = ClaudeClient()
    try:
        response, _usage = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=4096,
            prefill="{",
        )
        data = extract_json_from_response(response)
        raw_topics = data.get("topics", [])
    except Exception as e:
        logger.error(f"LLM scoring failed: {e}")
        return []

    # 5. Validate and normalize
    valid_topics = []
    for t in raw_topics[:max_topics]:
        if not all(
            k in t for k in ("title", "description", "category", "reasoning", "bo1_alignment")
        ):
            continue
        if t["category"] not in DECISION_CATEGORIES:
            t["category"] = "strategy"  # safe fallback
        score = t.get("seo_score", 0.5)
        t["seo_score"] = max(0.0, min(1.0, float(score)))
        t["source"] = "llm-generated"
        t.setdefault("keywords", [])
        valid_topics.append(t)

    if not valid_topics:
        logger.warning("No valid topics after scoring")
        return []

    # 6. Save to bank
    created = topic_bank_repository.bulk_create(valid_topics)
    logger.info(f"Researched and banked {len(created)} decision topics")
    return created
