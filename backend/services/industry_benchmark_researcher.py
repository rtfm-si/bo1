"""Industry benchmark researcher service.

When no peer benchmark data exists for an industry, this service provides
research-based benchmarks via web search (Brave + Tavily) and LLM extraction.

Features:
- Global cache per-industry (shared across all users)
- Dual search: Brave (broad) + Tavily (deep reports)
- LLM extraction with Claude Haiku for structured metrics
- Embedding similarity for fallback to similar industries
- Admin metrics tracking for query effectiveness
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx
from anthropic import AsyncAnthropic

from bo1.config import get_settings, resolve_model_alias
from bo1.llm.circuit_breaker import get_service_circuit_breaker
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.embeddings import generate_embedding
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Cache TTL in days
CACHE_TTL_DAYS = 30

# Minimum confidence to cache results
MIN_CONFIDENCE_TO_CACHE = 0.3

# Similarity threshold for finding similar industries
SIMILAR_INDUSTRY_THRESHOLD = 0.75


@dataclass
class BenchmarkMetric:
    """A single benchmark metric extracted from research."""

    metric: str
    display_name: str
    p25: float | None = None
    p50: float | None = None  # Median - most commonly available
    p75: float | None = None
    source_url: str | None = None
    confidence: float = 0.5  # 0-1 confidence score


@dataclass
class IndustryBenchmarkResult:
    """Result of industry benchmark research."""

    industry: str
    metrics: list[BenchmarkMetric] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.5
    generated_at: datetime | None = None
    source_type: Literal["cache", "research", "similar_industry"] = "research"
    similar_industry: str | None = None  # If source is similar_industry


class IndustryBenchmarkResearcher:
    """Generate industry benchmarks via web research when peer data unavailable."""

    def __init__(self) -> None:
        """Initialize the researcher."""
        self.settings = get_settings()

    async def get_or_research_benchmarks(
        self,
        industry: str,
        force_refresh: bool = False,
    ) -> IndustryBenchmarkResult | None:
        """Get cached benchmarks or research new ones.

        Args:
            industry: Industry name to research
            force_refresh: Force refresh even if cache exists

        Returns:
            IndustryBenchmarkResult or None if research failed
        """
        industry_normalized = industry.lower().strip()

        # Step 1: Check cache
        if not force_refresh:
            cached = self._get_cached_benchmarks(industry_normalized)
            if cached:
                logger.info(f"Cache hit for industry benchmarks: {industry}")
                return cached

        # Step 2: Research via dual search
        logger.info(f"Researching industry benchmarks: {industry}")
        search_results = await self._search_industry_benchmarks(industry)

        if not search_results:
            logger.warning(f"No search results for industry: {industry}")
            return None

        # Step 3: Extract structured metrics with LLM
        metrics = await self._extract_benchmark_metrics(industry, search_results)

        if not metrics:
            logger.warning(f"Failed to extract metrics for industry: {industry}")
            return None

        # Step 4: Calculate confidence and cache
        confidence = self._calculate_confidence(metrics, search_results)
        sources = [r["url"] for r in search_results if r.get("url")]

        result = IndustryBenchmarkResult(
            industry=industry,
            metrics=metrics,
            sources=sources,
            confidence=confidence,
            generated_at=datetime.now(UTC),
            source_type="research",
        )

        # Cache if confidence is sufficient
        if confidence >= MIN_CONFIDENCE_TO_CACHE:
            self._cache_benchmarks(industry, industry_normalized, result)

        return result

    async def find_similar_industry(
        self,
        industry: str,
        threshold: float = SIMILAR_INDUSTRY_THRESHOLD,
    ) -> IndustryBenchmarkResult | None:
        """Find cached benchmarks for a similar industry via embedding similarity.

        Args:
            industry: Industry name to find match for
            threshold: Minimum similarity threshold (0-1)

        Returns:
            IndustryBenchmarkResult from similar industry, or None
        """
        try:
            # Generate embedding for the target industry
            embedding = generate_embedding(industry, input_type="query")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for industry '{industry}': {e}")
            return None

        with db_session() as conn:
            with conn.cursor() as cur:
                # Find most similar cached industry using cosine similarity
                # Note: Using ARRAY comparison since we store as ARRAY(Float)
                cur.execute(
                    """
                    SELECT
                        id, industry, benchmarks, sources, confidence, generated_at,
                        1 - (
                            (SELECT SUM(a * b) FROM UNNEST(industry_embedding, %s::float[]) AS t(a, b))
                            / (
                                SQRT((SELECT SUM(a * a) FROM UNNEST(industry_embedding) AS t(a)))
                                * SQRT((SELECT SUM(b * b) FROM UNNEST(%s::float[]) AS t(b)))
                            )
                        ) AS distance
                    FROM industry_benchmark_cache
                    WHERE industry_embedding IS NOT NULL
                    AND expires_at > NOW()
                    ORDER BY distance ASC
                    LIMIT 1
                    """,
                    (embedding, embedding),
                )
                result = cur.fetchone()

                if not result:
                    return None

                # Check similarity (1 - distance = similarity)
                similarity = 1 - result["distance"] if result["distance"] else 0
                if similarity < threshold:
                    logger.info(
                        f"Best match for '{industry}' is '{result['industry']}' "
                        f"with similarity {similarity:.3f} (below threshold {threshold})"
                    )
                    return None

                logger.info(
                    f"Found similar industry for '{industry}': "
                    f"'{result['industry']}' (similarity: {similarity:.3f})"
                )

                # Parse cached benchmarks
                benchmarks_data = result["benchmarks"] or []
                metrics = [
                    BenchmarkMetric(
                        metric=b.get("metric", ""),
                        display_name=b.get("display_name", ""),
                        p25=b.get("p25"),
                        p50=b.get("p50"),
                        p75=b.get("p75"),
                        source_url=b.get("source_url"),
                        confidence=b.get("confidence", 0.5),
                    )
                    for b in benchmarks_data
                ]

                return IndustryBenchmarkResult(
                    industry=industry,
                    metrics=metrics,
                    sources=result["sources"] or [],
                    confidence=result["confidence"] or 0.5,
                    generated_at=result["generated_at"],
                    source_type="similar_industry",
                    similar_industry=result["industry"],
                )

    def _get_cached_benchmarks(self, industry_normalized: str) -> IndustryBenchmarkResult | None:
        """Get cached benchmarks for an industry."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT industry, benchmarks, sources, confidence, generated_at
                    FROM industry_benchmark_cache
                    WHERE industry_normalized = %s
                    AND expires_at > NOW()
                    """,
                    (industry_normalized,),
                )
                result = cur.fetchone()

                if not result:
                    return None

                # Parse benchmarks from JSONB
                benchmarks_data = result["benchmarks"] or []
                metrics = [
                    BenchmarkMetric(
                        metric=b.get("metric", ""),
                        display_name=b.get("display_name", ""),
                        p25=b.get("p25"),
                        p50=b.get("p50"),
                        p75=b.get("p75"),
                        source_url=b.get("source_url"),
                        confidence=b.get("confidence", 0.5),
                    )
                    for b in benchmarks_data
                ]

                return IndustryBenchmarkResult(
                    industry=result["industry"],
                    metrics=metrics,
                    sources=result["sources"] or [],
                    confidence=result["confidence"] or 0.5,
                    generated_at=result["generated_at"],
                    source_type="cache",
                )

    def _cache_benchmarks(
        self,
        industry: str,
        industry_normalized: str,
        result: IndustryBenchmarkResult,
    ) -> None:
        """Cache benchmark results globally."""
        try:
            # Generate embedding for similarity matching
            embedding = generate_embedding(industry, input_type="document")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for caching: {e}")
            embedding = None

        # Convert metrics to JSONB format
        benchmarks_json = [
            {
                "metric": m.metric,
                "display_name": m.display_name,
                "p25": m.p25,
                "p50": m.p50,
                "p75": m.p75,
                "source_url": m.source_url,
                "confidence": m.confidence,
            }
            for m in result.metrics
        ]

        expires_at = datetime.now(UTC) + timedelta(days=CACHE_TTL_DAYS)

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO industry_benchmark_cache (
                        industry, industry_normalized, industry_embedding,
                        benchmarks, sources, confidence, metrics_count, expires_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (industry_normalized)
                    DO UPDATE SET
                        industry = EXCLUDED.industry,
                        industry_embedding = EXCLUDED.industry_embedding,
                        benchmarks = EXCLUDED.benchmarks,
                        sources = EXCLUDED.sources,
                        confidence = EXCLUDED.confidence,
                        metrics_count = EXCLUDED.metrics_count,
                        generated_at = NOW(),
                        expires_at = EXCLUDED.expires_at
                    """,
                    (
                        industry,
                        industry_normalized,
                        embedding,
                        benchmarks_json,
                        result.sources,
                        result.confidence,
                        len(result.metrics),
                        expires_at,
                    ),
                )
                conn.commit()
                logger.info(f"Cached {len(result.metrics)} metrics for industry: {industry}")

    async def _search_industry_benchmarks(self, industry: str) -> list[dict[str, Any]]:
        """Perform dual search using Brave and Tavily.

        Returns combined, deduplicated search results.
        """
        # Generate search queries
        queries = [
            f"{industry} benchmarks 2025 statistics metrics",
            f"{industry} industry KPIs averages report",
            f"{industry} benchmark report statistics averages",
        ]

        # Run all searches in parallel (2 Brave + 1 Tavily)
        search_tasks = [
            self._brave_search(queries[0], industry),
            self._brave_search(queries[1], industry),
            self._tavily_search(queries[2], industry),
        ]
        all_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Flatten and deduplicate results
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for batch in all_results:
            if isinstance(batch, Exception):
                logger.warning(f"Search batch failed: {batch}")
                continue
            for r in batch:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(r)

        return results

    async def _brave_search(self, query: str, industry: str) -> list[dict[str, Any]]:
        """Search using Brave Search API."""
        api_key = self.settings.brave_api_key
        if not api_key:
            logger.warning("BRAVE_API_KEY not set")
            return []

        breaker = get_service_circuit_breaker("brave")
        if breaker.state.value == "open":
            logger.warning("Brave circuit breaker is OPEN")
            return []

        try:
            with CostTracker.track_call(
                provider="brave",
                operation_type="web_search",
                prompt_type="industry_benchmark_research",
                metadata={"query": query[:100], "industry": industry},
            ):
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        headers={"X-Subscription-Token": api_key},
                        params={"q": query, "count": 5},
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    breaker._record_success_sync()

            # Track research metric
            self._track_research_metric(
                industry=industry,
                query_pattern=query,
                search_provider="brave",
                success=True,
            )

            return [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "snippet": r["description"],
                    "provider": "brave",
                }
                for r in data.get("web", {}).get("results", [])
            ]

        except Exception as e:
            logger.error(f"Brave search error: {e}")
            self._track_research_metric(
                industry=industry,
                query_pattern=query,
                search_provider="brave",
                success=False,
                error_message=str(e),
            )
            return []

    async def _tavily_search(self, query: str, industry: str) -> list[dict[str, Any]]:
        """Search using Tavily AI API."""
        api_key = self.settings.tavily_api_key
        if not api_key:
            logger.warning("TAVILY_API_KEY not set")
            return []

        breaker = get_service_circuit_breaker("tavily")
        if breaker.state.value == "open":
            logger.warning("Tavily circuit breaker is OPEN")
            return []

        try:
            with CostTracker.track_call(
                provider="tavily",
                operation_type="advanced_search",
                prompt_type="industry_benchmark_research",
                metadata={"query": query[:100], "industry": industry},
            ):
                async with httpx.AsyncClient() as client:
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
                    breaker._record_success_sync()

            # Track research metric
            self._track_research_metric(
                industry=industry,
                query_pattern=query,
                search_provider="tavily",
                success=True,
            )

            results = []
            for r in data.get("results", []):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", ""),
                        "provider": "tavily",
                    }
                )

            # Include the AI answer if available
            if data.get("answer"):
                results.insert(
                    0,
                    {
                        "title": "Tavily AI Summary",
                        "url": "",
                        "snippet": data["answer"],
                        "provider": "tavily_answer",
                    },
                )

            return results

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            self._track_research_metric(
                industry=industry,
                query_pattern=query,
                search_provider="tavily",
                success=False,
                error_message=str(e),
            )
            return []

    async def _extract_benchmark_metrics(
        self,
        industry: str,
        search_results: list[dict[str, Any]],
    ) -> list[BenchmarkMetric]:
        """Extract structured benchmark metrics using Claude Haiku."""
        if not search_results:
            return []

        # Format search results for extraction
        context = "\n\n".join(
            [
                f"**{sanitize_user_input(r['title'], context='search_result_raw')}**\n"
                f"{sanitize_user_input(r['snippet'], context='search_result_raw')}\n"
                f"Source: {r['url']}"
                for r in search_results
            ]
        )

        prompt = f"""You are a business analyst extracting industry benchmark data.

Industry: {industry}

From the search results below, extract structured benchmark metrics. Focus on:
- Revenue metrics (ARR, MRR, revenue per employee, revenue growth)
- Customer metrics (churn rate, NPS, retention rate, LTV:CAC ratio)
- Operational metrics (team size, efficiency ratios)
- Industry-specific KPIs

For each metric found, provide:
- metric: snake_case identifier (e.g., "customer_churn_rate")
- display_name: Human-readable name (e.g., "Customer Churn Rate")
- p25: 25th percentile value (if available)
- p50: Median/average value (required - this is the most important)
- p75: 75th percentile value (if available)
- source_url: URL where this data was found
- confidence: Your confidence in this data (0.0-1.0)

Search Results:
{context}

Respond with a JSON array of metrics. Only include metrics where you found actual numeric data.
If a metric is expressed as a percentage (e.g., "5% churn"), store as decimal (0.05).
If no reliable metrics found, return an empty array.

Example response format:
[
  {{"metric": "customer_churn_rate", "display_name": "Customer Churn Rate", "p25": 0.03, "p50": 0.05, "p75": 0.08, "source_url": "https://...", "confidence": 0.8}},
  {{"metric": "nps_score", "display_name": "Net Promoter Score", "p50": 32, "confidence": 0.7}}
]"""

        try:
            model_name = resolve_model_alias("haiku")
            anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="extraction",
                model_name=model_name,
                prompt_type="benchmark_extraction",
                metadata={"industry": industry},
            ) as cost_record:
                message = await anthropic_client.messages.create(
                    model=model_name,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )

                cost_record.input_tokens = message.usage.input_tokens
                cost_record.output_tokens = message.usage.output_tokens

            # Parse response
            response_text = message.content[0].text if message.content else ""

            # Extract JSON from response
            import json
            import re

            # Find JSON array in response
            json_match = re.search(r"\[[\s\S]*\]", response_text)
            if not json_match:
                logger.warning(f"No JSON found in extraction response for {industry}")
                return []

            metrics_data = json.loads(json_match.group())

            metrics = [
                BenchmarkMetric(
                    metric=m.get("metric", ""),
                    display_name=m.get("display_name", ""),
                    p25=m.get("p25"),
                    p50=m.get("p50"),
                    p75=m.get("p75"),
                    source_url=m.get("source_url"),
                    confidence=m.get("confidence", 0.5),
                )
                for m in metrics_data
                if m.get("metric") and m.get("p50") is not None
            ]

            # Track extraction success
            for m in metrics:
                if m.source_url:
                    self._track_research_metric(
                        industry=industry,
                        query_pattern="extraction",
                        search_provider="anthropic",
                        source_url=m.source_url,
                        metrics_extracted=1,
                        confidence_avg=m.confidence,
                        success=True,
                    )

            logger.info(f"Extracted {len(metrics)} metrics for industry: {industry}")
            return metrics

        except Exception as e:
            logger.error(f"Metric extraction failed for {industry}: {e}")
            return []

    def _calculate_confidence(
        self,
        metrics: list[BenchmarkMetric],
        search_results: list[dict[str, Any]],
    ) -> float:
        """Calculate overall confidence score for the benchmark result."""
        if not metrics:
            return 0.0

        # Factors:
        # 1. Average metric confidence
        # 2. Number of metrics found
        # 3. Number of sources

        avg_metric_confidence = sum(m.confidence for m in metrics) / len(metrics)
        metric_count_factor = min(len(metrics) / 5.0, 1.0)  # Max at 5 metrics
        source_factor = min(len(search_results) / 5.0, 1.0)  # Max at 5 sources

        # Weighted average
        confidence = avg_metric_confidence * 0.5 + metric_count_factor * 0.3 + source_factor * 0.2

        return round(confidence, 2)

    def _track_research_metric(
        self,
        industry: str,
        query_pattern: str,
        search_provider: str,
        source_url: str | None = None,
        metrics_extracted: int = 0,
        confidence_avg: float | None = None,
        success: bool = True,
        error_message: str | None = None,
        cost_usd: float | None = None,
    ) -> None:
        """Track research metrics for admin analytics."""
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO industry_benchmark_research_metrics (
                            industry, query_pattern, search_provider, source_url,
                            metrics_extracted, confidence_avg, success, error_message, cost_usd
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            industry,
                            query_pattern[:500],
                            search_provider,
                            source_url,
                            metrics_extracted,
                            confidence_avg,
                            success,
                            error_message,
                            cost_usd,
                        ),
                    )
                    conn.commit()
        except Exception as e:
            logger.warning(f"Failed to track research metric: {e}")
