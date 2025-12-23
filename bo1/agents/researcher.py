"""Research agent for external information gathering with semantic caching.

Integrates:
- Semantic cache with Voyage AI embeddings (voyage-3, 1024 dimensions)
- PostgreSQL pgvector for similarity search
- Freshness-based cache invalidation
- Cost tracking (cache hit ~$0.00006 vs cache miss ~$0.05-0.10)
- Brave Search API (default: cheap web+news layer)
- Tavily AI (premium: deep competitor/market/regulatory research)
- Request consolidation (P2-RESEARCH-3): Batch similar queries
- Rate limiting (P2-RESEARCH-4): Token bucket for API calls
- Metrics tracking (P2-RESEARCH-5): Success rate by depth/keywords

Research Strategy:
- Default: Brave Search ($5/1000 queries = $0.005/query) + Haiku summarization
- Premium: Tavily ($1/1000 = $0.001/query) for in-depth analysis requiring context
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Literal

import httpx
from anthropic import AsyncAnthropic

from bo1.agents.research_consolidation import (
    consolidate_research_requests,
    merge_batch_questions,
    split_batch_results,
)
from bo1.agents.research_metrics import ResearchMetric, track_research_metric
from bo1.agents.research_rate_limiter import get_rate_limiter
from bo1.config import get_settings
from bo1.constants import SimilarityCacheThresholds
from bo1.llm.circuit_breaker import (
    get_service_circuit_breaker,
)
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.embeddings import generate_embedding
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.state.repositories import cache_repository

logger = logging.getLogger(__name__)


class ResearcherAgent:
    """Agent for researching external information gaps with semantic caching.

    Features:
    - Semantic similarity matching (cosine similarity >0.85)
    - Category-based freshness policies (saas_metrics: 90 days, pricing: 180 days, etc.)
    - Cost tracking (embedding + search/summarization)
    - Source citations

    Production Integration:
    - Used in bo1/graph/nodes.py:research_node() for external research during deliberation
    - Invoked via facilitator decision when additional context is needed
    - Supports both Brave Search (basic) and Tavily AI (deep analysis)

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
        research_depth: Literal["basic", "deep"] = "basic",
        enable_consolidation: bool = True,
    ) -> list[dict[str, Any]]:
        """Research external questions with semantic cache.

        Args:
            questions: List of external gaps from identify_information_gaps()
                Format: [{"question": "...", "priority": "...", "reason": "..."}]
            category: Optional category filter (e.g., 'saas_metrics', 'pricing')
            industry: Optional industry filter (e.g., 'saas', 'ecommerce')
            research_depth: Depth of research - "basic" for quick facts, "deep" for comprehensive analysis
            enable_consolidation: Enable request consolidation (P2-RESEARCH-3)

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

        # P2-RESEARCH-3: Consolidate similar requests
        if enable_consolidation and len(questions) > 1:
            batches = consolidate_research_requests(
                questions, similarity_threshold=SimilarityCacheThresholds.CONSOLIDATION
            )
        else:
            # No consolidation - each question is its own batch
            batches = [[q] for q in questions]

        total_cost = 0.0

        # Process batches SEQUENTIALLY to respect rate limits
        # (Brave free tier: 1 req/sec - parallel requests cause 429 errors)
        batch_results = []
        for batch in batches:
            result_items, cost = await self._process_batch_with_retry(
                batch, category, industry, research_depth
            )
            batch_results.append((result_items, cost))

        # Aggregate results
        results = []
        for batch_items, cost in batch_results:
            results.extend(batch_items)
            total_cost += cost

        logger.info(f"Research complete - Total cost: ${total_cost:.4f}")
        return results

    async def _process_batch_with_retry(
        self,
        batch: list[dict[str, Any]],
        category: str | None,
        industry: str | None,
        research_depth: Literal["basic", "deep"],
        max_retries: int = 3,
    ) -> tuple[list[dict[str, Any]], float]:
        """Process a batch with exponential backoff on rate limit errors.

        Args:
            batch: List of question dicts to process
            category: Category filter
            industry: Industry filter
            research_depth: Research depth
            max_retries: Maximum retry attempts for rate limit errors

        Returns:
            Tuple of (result_items, total_cost)
        """
        if len(batch) > 1:
            merged_question = merge_batch_questions(batch)
            logger.info(
                f"Processing consolidated batch: {len(batch)} questions → '{merged_question[:50]}...'"
            )
            question_data = batch[0].copy()
            question_data["question"] = merged_question
        else:
            question_data = batch[0]

        for attempt in range(max_retries):
            try:
                result = await self._research_single_question(
                    question_data, category, industry, research_depth
                )

                # Check if result indicates rate limit failure
                if "429" in result.get("summary", "") or "Rate limit" in result.get("summary", ""):
                    if attempt < max_retries - 1:
                        wait_time = self._calculate_backoff(attempt)
                        logger.warning(
                            f"Rate limited (detected in result), waiting {wait_time:.1f}s before retry"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Rate limit persists after {max_retries} attempts")

                # Split back if batch was consolidated
                if len(batch) > 1:
                    return split_batch_results(result, batch), result.get("cost", 0.0)
                return [result], result.get("cost", 0.0)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"Rate limited (HTTP 429), waiting {wait_time:.1f}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Re-raise non-429 errors or final 429
                    raise

        # After all retries exhausted, return failure result
        failure_result = {
            "question": question_data.get("question", ""),
            "summary": "[Rate limit exceeded after retries - please try again later]",
            "sources": [],
            "confidence": "low",
            "cached": False,
            "cost": 0.0,
            "rate_limited": True,
        }
        if len(batch) > 1:
            return split_batch_results(failure_result, batch), 0.0
        return [failure_result], 0.0

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff wait time.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Wait time in seconds (1s, 2s, 4s, ... capped at 30s)
        """
        return float(min(2**attempt, 30))

    async def _research_single_question(
        self,
        question_data: dict[str, Any],
        category: str | None,
        industry: str | None,
        research_depth: Literal["basic", "deep"],
    ) -> dict[str, Any]:
        """Research a single question (internal method).

        This method handles the actual research logic, separated out to support
        both individual and batched requests.

        Args:
            question_data: Single question dict
            category: Category filter
            industry: Industry filter
            research_depth: Research depth

        Returns:
            Research result dict
        """
        start_time = time.time()
        question = question_data.get("question", "")

        # Determine keywords for metrics tracking (P2-RESEARCH-5)
        deep_keywords = ["competitor", "market", "landscape", "regulation", "policy", "analysis"]
        keywords_matched = [kw for kw in deep_keywords if kw in question.lower()]

        # Get cost context for attribution
        ctx = get_cost_context()

        # Step 1: Generate embedding for semantic search (~$0.00006)
        # Note: embedding cost is already tracked by generate_embedding()
        try:
            embedding = generate_embedding(question, input_type="query")
            embedding_cost = 0.00006  # Voyage AI voyage-3 cost estimate (for local tracking)
        except Exception as e:
            logger.warning(f"Failed to generate embedding for '{question[:50]}...': {e}")
            # Fall back to placeholder
            return {
                "question": question,
                "summary": "[Embedding generation failed - cache unavailable]",
                "sources": [],
                "confidence": "low",
                "cached": False,
                "cost": 0.0,
            }

        # Step 2: Check cache with similarity threshold
        freshness_days = self._get_freshness_days(category)
        try:
            cached_result = cache_repository.find_by_embedding(
                question_embedding=embedding,
                similarity_threshold=SimilarityCacheThresholds.RESEARCH_CACHE,
                category=category,
                industry=industry,
                max_age_days=freshness_days,
            )
        except Exception as e:
            logger.warning(f"Cache lookup failed for '{question[:50]}...': {e}")
            cached_result = None

        if cached_result:
            # CACHE HIT - Track semantic cache savings
            try:
                cache_repository.update_access(str(cached_result["id"]))
            except Exception as e:
                logger.warning(f"Failed to update access count: {e}")

            # Calculate age
            research_date = cached_result.get("research_date")
            if research_date and isinstance(research_date, datetime):
                # Handle timezone-aware datetimes from PostgreSQL
                now = datetime.now(research_date.tzinfo) if research_date.tzinfo else datetime.now()
                age_days = (now - research_date).days
            else:
                age_days = 0

            response_time_ms = (time.time() - start_time) * 1000

            # Calculate what it would have cost without semantic cache
            # Estimate: Brave search ($0.003) + Haiku summarization (~$0.02) + embedding ($0.00006)
            estimated_cost_without_cache = 0.003 + 0.02 + embedding_cost

            # Track semantic cache hit using Voyage provider (since we used embedding for lookup)
            # This is essentially a "free" research result - only embedding cost
            from bo1.llm.cost_tracker import CostRecord

            cache_hit_record = CostRecord(
                provider="voyage",  # Use voyage since we used embeddings for lookup
                model_name="voyage-3",
                operation_type="semantic_cache_hit",
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name=ctx.get("node_name", "research_node"),
                phase=ctx.get("phase"),
                input_tokens=len(question.split()),  # Approximate embedding tokens
                total_cost=embedding_cost,  # Only embedding cost
                optimization_type="semantic_cache",
                cost_without_optimization=estimated_cost_without_cache,
                latency_ms=int(response_time_ms),
                status="success",
                metadata={
                    "query": question[:100],
                    "cache_age_days": age_days,
                    "similarity_threshold": SimilarityCacheThresholds.RESEARCH_CACHE,
                    "confidence": cached_result.get("confidence", "medium"),
                    "cache_hit": True,
                },
            )
            CostTracker.log_cost(cache_hit_record)

            # Track metrics (P2-RESEARCH-5)
            metric = ResearchMetric(
                query=question,
                research_depth=research_depth,
                keywords_matched=keywords_matched,
                success=True,  # Cache hit = success
                cached=True,
                sources_count=cached_result.get("source_count", 0),
                confidence=cached_result.get("confidence", "medium"),
                cost_usd=embedding_cost,
                response_time_ms=response_time_ms,
            )
            track_research_metric(metric)

            logger.info(
                f"✓ Cache hit for '{question[:50]}...' "
                f"(age: {age_days} days, cost: ${embedding_cost:.6f}, "
                f"saved: ${estimated_cost_without_cache - embedding_cost:.4f})"
            )

            return {
                "question": question,
                "summary": cached_result.get("answer_summary", ""),
                "sources": cached_result.get("sources", []),
                "confidence": cached_result.get("confidence", "medium"),
                "cached": True,
                "cache_age_days": age_days,
                "cost": embedding_cost,  # Only embedding cost for cache hit
            }

        else:
            # CACHE MISS - Perform research (Brave or Tavily based on depth)
            research_result = await self._perform_web_research(question, research_depth)

            # Only cache successful results with meaningful data
            # Don't cache rate-limited, errored, or empty results
            is_rate_limited = "429" in research_result.get(
                "summary", ""
            ) or "[Search API error" in research_result.get("summary", "")
            has_sources = len(research_result.get("sources", [])) > 0
            has_good_confidence = research_result.get("confidence") in ("high", "medium")

            if has_sources and has_good_confidence and not is_rate_limited:
                try:
                    cache_repository.save(
                        question=question,
                        embedding=embedding,
                        summary=research_result["summary"],
                        sources=research_result.get("sources"),
                        confidence=research_result["confidence"],
                        category=category,
                        industry=industry,
                        tokens_used=research_result.get("tokens_used", 0),
                        research_cost_usd=research_result["cost"],
                    )
                    logger.info(f"Saved research result to cache for '{question[:50]}...'")
                except Exception as e:
                    logger.warning(f"Failed to save research result to cache: {e}")
            else:
                logger.info(
                    f"Skipping cache for '{question[:50]}...' "
                    f"(sources={has_sources}, confidence={research_result.get('confidence')}, rate_limited={is_rate_limited})"
                )

            total_research_cost = embedding_cost + research_result["cost"]
            response_time_ms = (time.time() - start_time) * 1000

            # Determine success based on confidence and sources
            success = (
                research_result["confidence"] in ("high", "medium")
                and len(research_result.get("sources", [])) > 0
            )

            # Track metrics (P2-RESEARCH-5)
            metric = ResearchMetric(
                query=question,
                research_depth=research_depth,
                keywords_matched=keywords_matched,
                success=success,
                cached=False,
                sources_count=len(research_result.get("sources", [])),
                confidence=research_result["confidence"],
                cost_usd=total_research_cost,
                response_time_ms=response_time_ms,
            )
            track_research_metric(metric)

            logger.info(
                f"✓ Researched '{question[:50]}...' "
                f"(cost: ${total_research_cost:.4f}, sources: {len(research_result.get('sources', []))})"
            )

            return {
                "question": question,
                "summary": research_result["summary"],
                "sources": research_result.get("sources", []),
                "confidence": research_result["confidence"],
                "cached": False,
                "cost": total_research_cost,
            }

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

    async def _perform_web_research(
        self, question: str, research_depth: Literal["basic", "deep"] = "basic"
    ) -> dict[str, Any]:
        """Perform web research using Brave Search (default) or Tavily (premium).

        Research Strategy:
        - basic: Brave Search + Haiku summarization (~$0.025 per query)
          Use for: quick facts, statistics, general info
        - deep: Tavily AI (combined search + analysis) (~$0.001 per query, but richer)
          Use for: competitor analysis, market landscape, regulatory research

        Args:
            question: Research question
            research_depth: "basic" (Brave) or "deep" (Tavily)

        Returns:
            Dictionary with summary, sources, confidence, tokens_used, cost

        Examples:
            >>> agent = ResearcherAgent()
            >>> result = await agent._perform_web_research("What is average SaaS churn?")
            >>> result = await agent._perform_web_research(
            ...     "Analyze competitor pricing strategies", research_depth="deep"
            ... )
        """
        if research_depth == "deep":
            return await self._tavily_search(question)
        else:
            return await self._brave_search_and_summarize(question)

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

    async def _brave_search_and_summarize(self, question: str) -> dict[str, Any]:
        """Perform web search using Brave Search API + Haiku summarization.

        Cost: ~$0.025 per query ($0.005 search + $0.02 Haiku)

        Args:
            question: Research question

        Returns:
            Dictionary with summary, sources, confidence, tokens_used, cost
        """
        settings = get_settings()
        brave_api_key = settings.brave_api_key

        if not brave_api_key:
            logger.warning("BRAVE_API_KEY not set - research unavailable")
            return {
                "summary": "[Brave Search API key not configured]",
                "sources": [],
                "confidence": "low",
                "tokens_used": 0,
                "cost": 0.0,
            }

        # Check circuit breaker before making API call
        breaker = get_service_circuit_breaker("brave")
        if breaker.state.value == "open":
            logger.warning("Brave circuit breaker is OPEN - fast-failing search request")
            return {
                "summary": "[Brave Search unavailable - service circuit breaker open]",
                "sources": [],
                "confidence": "low",
                "tokens_used": 0,
                "cost": 0.0,
                "circuit_breaker_open": True,
            }

        # P2-RESEARCH-4: Apply rate limiting
        limiter = get_rate_limiter("brave_free")  # TODO: Detect API tier from settings
        wait_time = await limiter.acquire()
        if wait_time > 0:
            logger.info(f"Rate limited: waited {wait_time:.2f}s for Brave API")

        # Get cost context for attribution
        ctx = get_cost_context()

        try:
            # Step 1: Brave Search - Track cost
            with CostTracker.track_call(
                provider="brave",
                operation_type="web_search",
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name=ctx.get("node_name", "research_node"),
                phase=ctx.get("phase"),
                prompt_type="search",
                metadata={"query": question[:100]},
            ) as search_cost_record:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": brave_api_key},
                        params={"q": question, "count": 5},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    results_data = response.json()
                    # Record success for circuit breaker
                    breaker._record_success_sync()
                # Cost is calculated automatically by CostTracker

            search_results = [
                {
                    "title": result["title"],
                    "url": result["url"],
                    "snippet": result["description"],
                }
                for result in results_data.get("web", {}).get("results", [])
            ]

            if not search_results:
                logger.warning(f"No search results for: {question[:50]}...")
                return {
                    "summary": "[No search results found]",
                    "sources": [],
                    "confidence": "low",
                    "tokens_used": 0,
                    "cost": search_cost_record.total_cost,
                }

            # Step 2: Summarize with Haiku - Track cost
            # Sanitize raw search snippets before LLM summarization (P0 security)
            context = "\n\n".join(
                [
                    f"**{sanitize_user_input(r['title'], context='search_result_raw')}**\n"
                    f"{sanitize_user_input(r['snippet'], context='search_result_raw')}\n"
                    f"Source: {r['url']}"
                    for r in search_results
                ]
            )

            prompt = f"""You are a research assistant. Summarize the following search results to answer the question.

Question: {question}

Search Results:
{context}

Provide a concise 200-300 word summary with key facts and statistics. Be direct and factual. If the results don't contain sufficient information, state what's known and what's missing."""

            from bo1.config import resolve_model_alias

            model_name = resolve_model_alias("haiku")
            anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="summarization",
                model_name=model_name,
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name=ctx.get("node_name", "research_node"),
                phase=ctx.get("phase"),
                prompt_type="research_summary",
                metadata={"query": question[:100], "search_provider": "brave"},
            ) as llm_cost_record:
                message = await anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Record token usage
                llm_cost_record.input_tokens = message.usage.input_tokens
                llm_cost_record.output_tokens = message.usage.output_tokens
                llm_cost_record.cache_creation_tokens = getattr(
                    message.usage, "cache_creation_input_tokens", 0
                )
                llm_cost_record.cache_read_tokens = getattr(
                    message.usage, "cache_read_input_tokens", 0
                )
                # Cost is calculated automatically by CostTracker

            # Extract text from first content block (guaranteed to be TextBlock for text responses)
            first_block = message.content[0]
            raw_summary = first_block.text if hasattr(first_block, "text") else str(first_block)
            # Sanitize LLM output before re-injection into prompts (P0 security)
            summary = sanitize_user_input(raw_summary, context="search_result_summarized")
            tokens_used = message.usage.input_tokens + message.usage.output_tokens

            total_cost = search_cost_record.total_cost + llm_cost_record.total_cost

            logger.info(
                f"[BRAVE] Researched '{question[:50]}...' - "
                f"{len(search_results)} results, {tokens_used} tokens, ${total_cost:.4f}"
            )

            return {
                "summary": summary,
                "sources": [
                    f"{sanitize_user_input(r['title'], context='search_result_raw')} - {r['url']}"
                    for r in search_results
                ],
                "confidence": "high" if len(search_results) >= 3 else "medium",
                "tokens_used": tokens_used,
                "cost": total_cost,
            }

        except httpx.HTTPStatusError as e:
            # Record failure for circuit breaker (server errors and rate limits)
            if e.response.status_code >= 500 or e.response.status_code == 429:
                breaker._record_failure_sync(e)
            logger.error(f"Brave Search API error: {e.response.status_code} - {e.response.text}")
            return {
                "summary": f"[Search API error: {e.response.status_code}]",
                "sources": [],
                "confidence": "low",
                "tokens_used": 0,
                "cost": 0.0,
            }
        except Exception as e:
            # Record failure for circuit breaker (connection errors, timeouts)
            breaker._record_failure_sync(e)
            logger.error(f"Research failed: {e}")
            return {
                "summary": f"[Research error: {str(e)[:100]}]",
                "sources": [],
                "confidence": "low",
                "tokens_used": 0,
                "cost": 0.0,
            }

    async def _tavily_search(self, question: str) -> dict[str, Any]:
        """Perform deep research using Tavily AI (premium option).

        Tavily provides AI-powered search with built-in summarization and context.
        Use for: competitor analysis, market landscape, regulatory research.

        Cost: ~$0.002 per query for advanced search

        Args:
            question: Research question requiring deep analysis

        Returns:
            Dictionary with summary, sources, confidence, tokens_used, cost
        """
        settings = get_settings()
        tavily_api_key = settings.tavily_api_key

        if not tavily_api_key:
            logger.warning("TAVILY_API_KEY not set - falling back to Brave")
            return await self._brave_search_and_summarize(question)

        # Check circuit breaker before making API call
        breaker = get_service_circuit_breaker("tavily")
        if breaker.state.value == "open":
            logger.warning("Tavily circuit breaker is OPEN - falling back to Brave")
            return await self._brave_search_and_summarize(question)

        # P2-RESEARCH-4: Apply rate limiting
        limiter = get_rate_limiter("tavily_free")  # TODO: Detect API tier from settings
        wait_time = await limiter.acquire()
        if wait_time > 0:
            logger.info(f"Rate limited: waited {wait_time:.2f}s for Tavily API")

        # Get cost context for attribution
        ctx = get_cost_context()

        try:
            # Track Tavily API call cost
            with (
                CostTracker.track_call(
                    provider="tavily",
                    operation_type="advanced_search",  # Using advanced depth
                    session_id=ctx.get("session_id"),
                    user_id=ctx.get("user_id"),
                    node_name=ctx.get("node_name", "research_node"),
                    phase=ctx.get("phase"),
                    prompt_type="search",
                    metadata={"query": question[:100], "depth": "advanced"},
                ) as cost_record
            ):
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": tavily_api_key,
                            "query": question,
                            "search_depth": "advanced",  # Premium deep search
                            "include_answer": True,  # Get AI-generated answer
                            "include_raw_content": False,  # Don't need full HTML
                            "max_results": 5,
                        },
                        timeout=15.0,  # Longer timeout for deep search
                    )
                    response.raise_for_status()
                    data = response.json()
                    # Record success for circuit breaker
                    breaker._record_success_sync()
                # Cost is calculated automatically by CostTracker

            raw_summary = data.get("answer", "[No answer provided]")
            # Sanitize Tavily AI-generated answer before re-injection (P0 security)
            summary = sanitize_user_input(raw_summary, context="search_result_summarized")
            results = data.get("results", [])

            # Sanitize source titles from external content
            sources = [
                f"{sanitize_user_input(r.get('title', 'Untitled'), context='search_result_raw')} - {r.get('url', '')}"
                for r in results
            ]

            tokens_used = len(summary.split())  # Approximate

            logger.info(
                f"[TAVILY] Deep research '{question[:50]}...' - "
                f"{len(results)} sources, ${cost_record.total_cost:.4f}"
            )

            return {
                "summary": summary,
                "sources": sources,
                "confidence": "high" if len(results) >= 3 else "medium",
                "tokens_used": tokens_used,
                "cost": cost_record.total_cost,
            }

        except httpx.HTTPStatusError as e:
            # Record failure for circuit breaker (server errors and rate limits)
            if e.response.status_code >= 500 or e.response.status_code == 429:
                breaker._record_failure_sync(e)
            logger.error(f"Tavily API error: {e.response.status_code} - {e.response.text}")
            logger.info("Falling back to Brave Search")
            return await self._brave_search_and_summarize(question)
        except Exception as e:
            # Record failure for circuit breaker (connection errors, timeouts)
            breaker._record_failure_sync(e)
            logger.error(f"Tavily research failed: {e}, falling back to Brave")
            return await self._brave_search_and_summarize(question)
