"""Research agent for external information gathering with semantic caching.

Integrates:
- Semantic cache with Voyage AI embeddings (voyage-3, 1024 dimensions)
- PostgreSQL pgvector for similarity search
- Freshness-based cache invalidation
- Cost tracking (cache hit ~$0.00006 vs cache miss ~$0.05-0.10)

Web search integration (Brave Search API / Tavily) will be implemented in Week 4 (Day 27).
"""

import logging
from datetime import datetime
from typing import Any

from bo1.config import get_settings
from bo1.llm.embeddings import generate_embedding
from bo1.state.postgres_manager import (
    find_cached_research,
    save_research_result,
    update_research_access,
)

logger = logging.getLogger(__name__)


class ResearcherAgent:
    """Agent for researching external information gaps with semantic caching.

    Features:
    - Semantic similarity matching (cosine similarity >0.85)
    - Category-based freshness policies (saas_metrics: 90 days, pricing: 180 days, etc.)
    - Cost tracking (embedding + search/summarization)
    - Source citations

    Examples:
        >>> agent = ResearcherAgent()
        >>> result = await agent.research_questions([
        ...     {"question": "What is average B2B SaaS churn rate?", "priority": "CRITICAL"}
        ... ], category="saas_metrics", industry="saas")
        >>> print(result[0]["summary"])  # Cached or fresh research
    """

    def __init__(self) -> None:
        """Initialize the researcher agent."""
        logger.info("ResearcherAgent initialized with semantic cache support")

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
            category: Optional category filter (e.g., 'saas_metrics', 'pricing')
            industry: Optional industry filter (e.g., 'saas', 'ecommerce')

        Returns:
            List of research results with cache metadata:
            [
                {
                    "question": "...",
                    "summary": "...",  # 200-300 token summary
                    "sources": [...],  # Citations
                    "confidence": "high|medium|low",
                    "cached": True|False,
                    "cache_age_days": 15 (if cached),
                    "cost": 0.00006 (if cached) or 0.05-0.10 (if not)
                }
            ]

        Examples:
            >>> agent = ResearcherAgent()
            >>> questions = [
            ...     {"question": "What is average SaaS churn?", "priority": "CRITICAL"}
            ... ]
            >>> results = await agent.research_questions(
            ...     questions, category="saas_metrics", industry="saas"
            ... )
        """
        if not questions:
            logger.info("No external questions to research")
            return []

        results = []
        total_cost = 0.0

        for question_data in questions:
            question = question_data.get("question", "")

            # Step 1: Generate embedding for semantic search (~$0.00006)
            try:
                embedding = generate_embedding(question, input_type="query")
                embedding_cost = 0.00006  # Voyage AI voyage-3 cost estimate
                total_cost += embedding_cost
            except Exception as e:
                logger.warning(f"Failed to generate embedding for '{question[:50]}...': {e}")
                # Fall back to placeholder
                results.append(
                    {
                        "question": question,
                        "summary": "[Embedding generation failed - cache unavailable]",
                        "sources": [],
                        "confidence": "low",
                        "cached": False,
                        "cost": 0.0,
                    }
                )
                continue

            # Step 2: Check cache with similarity threshold
            freshness_days = self._get_freshness_days(category)
            try:
                cached_result = find_cached_research(
                    question_embedding=embedding,
                    similarity_threshold=0.85,
                    category=category,
                    industry=industry,
                    max_age_days=freshness_days,
                )
            except Exception as e:
                logger.warning(f"Cache lookup failed for '{question[:50]}...': {e}")
                cached_result = None

            if cached_result:
                # CACHE HIT - Return cached result
                try:
                    update_research_access(str(cached_result["id"]))
                except Exception as e:
                    logger.warning(f"Failed to update access count: {e}")

                # Calculate age
                research_date = cached_result.get("research_date")
                if research_date and isinstance(research_date, datetime):
                    # Handle timezone-aware datetimes from PostgreSQL
                    now = (
                        datetime.now(research_date.tzinfo)
                        if research_date.tzinfo
                        else datetime.now()
                    )
                    age_days = (now - research_date).days
                else:
                    age_days = 0

                results.append(
                    {
                        "question": question,
                        "summary": cached_result.get("answer_summary", ""),
                        "sources": cached_result.get("sources", []),
                        "confidence": cached_result.get("confidence", "medium"),
                        "cached": True,
                        "cache_age_days": age_days,
                        "cost": embedding_cost,  # Only embedding cost for cache hit
                    }
                )

                logger.info(
                    f"✓ Cache hit for '{question[:50]}...' "
                    f"(age: {age_days} days, cost: ${embedding_cost:.6f})"
                )

            else:
                # CACHE MISS - Perform research (stub for now)
                research_result = await self._perform_web_research(question)

                # Save to cache
                try:
                    save_research_result(
                        question=question,
                        embedding=embedding,
                        summary=research_result["summary"],
                        sources=research_result.get("sources"),
                        confidence=research_result["confidence"],
                        category=category,
                        industry=industry,
                        freshness_days=freshness_days,
                        tokens_used=research_result.get("tokens_used", 0),
                        research_cost_usd=research_result["cost"],
                    )
                    logger.info(f"Saved research result to cache for '{question[:50]}...'")
                except Exception as e:
                    logger.warning(f"Failed to save research result to cache: {e}")

                total_research_cost = embedding_cost + research_result["cost"]
                total_cost += research_result["cost"]

                results.append(
                    {
                        "question": question,
                        "summary": research_result["summary"],
                        "sources": research_result.get("sources", []),
                        "confidence": research_result["confidence"],
                        "cached": False,
                        "cost": total_research_cost,
                    }
                )

                logger.info(
                    f"✓ Researched '{question[:50]}...' "
                    f"(cost: ${total_research_cost:.4f}, sources: {len(research_result.get('sources', []))})"
                )

        logger.info(f"Research complete - Total cost: ${total_cost:.4f}")
        return results

    def _get_freshness_days(self, category: str | None) -> int:
        """Get freshness period for category.

        Uses centralized configuration from CacheConfig to determine
        category-specific freshness policies.

        Args:
            category: Research category (e.g., 'saas_metrics', 'pricing')

        Returns:
            Number of days before cache result is considered stale
        """
        settings = get_settings()
        cache_config = settings.cache

        if not category:
            return cache_config.research_cache_default_freshness_days

        return cache_config.research_cache_freshness_map.get(
            category, cache_config.research_cache_default_freshness_days
        )

    async def _perform_web_research(self, question: str) -> dict[str, Any]:
        """Perform actual web research (Brave Search + summarization).

        **STUB**: Week 4+ implementation - currently returns placeholder.

        Future implementation:
        1. Search web using Brave Search API / Tavily
        2. Extract relevant information from top results
        3. Summarize findings using Haiku (200-300 tokens)
        4. Include source citations
        5. Track costs (search API + LLM summarization)

        Args:
            question: Research question

        Returns:
            Dictionary with summary, sources, confidence, tokens_used, cost
        """
        # Placeholder - will integrate Brave Search API + Haiku summarization
        logger.info(f"[STUB] Would perform web research for: {question[:50]}...")
        return {
            "summary": "[Research pending - Week 4 implementation]",
            "sources": [],
            "confidence": "stub",
            "tokens_used": 0,
            "cost": 0.0,
        }

    def format_research_context(self, research_results: list[dict[str, Any]]) -> str:
        """Format research results for inclusion in deliberation prompts.

        Args:
            research_results: List of research results from research_questions()

        Returns:
            Formatted string for prompt inclusion

        Examples:
            >>> agent = ResearcherAgent()
            >>> results = [{"question": "...", "summary": "...", "sources": [...]}]
            >>> formatted = agent.format_research_context(results)
        """
        if not research_results:
            return ""

        lines = ["<external_research>"]

        for result in research_results:
            question = result.get("question", "")
            summary = result.get("summary", "")
            sources = result.get("sources", [])
            confidence = result.get("confidence", "unknown")

            lines.append("  <research_item>")
            lines.append(f"    <question>{question}</question>")
            lines.append(f'    <findings confidence="{confidence}">')
            lines.append(f"      {summary}")
            lines.append("    </findings>")

            if sources:
                lines.append("    <sources>")
                for source in sources:
                    lines.append(f"      <source>{source}</source>")
                lines.append("    </sources>")

            lines.append("  </research_item>")

        lines.append("</external_research>")

        return "\n".join(lines)
