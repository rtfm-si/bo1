"""Website enrichment service for business context.

Extracts and structures business information from website URLs using:
1. Direct website scraping (meta tags, OG data)
2. Brave Search API for company information
3. Claude Haiku for intelligent extraction and structuring

Usage:
    service = EnrichmentService()
    context = await service.enrich_from_url("https://example.com")
"""

import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from bo1.config import get_settings
from bo1.llm.client import ClaudeClient

logger = logging.getLogger(__name__)


class EnrichedContext(BaseModel):
    """Enriched business context from website analysis."""

    # Company basics
    company_name: str | None = Field(None, description="Company name")
    website: str | None = Field(None, description="Website URL")
    industry: str | None = Field(None, description="Industry vertical")

    # Business model
    business_model: str | None = Field(None, description="Business model type")
    pricing_model: str | None = Field(None, description="Pricing model")
    target_market: str | None = Field(None, description="Target market")

    # Product
    product_description: str | None = Field(None, description="Product/service description")
    product_categories: list[str] | None = Field(None, description="Product categories")
    main_value_proposition: str | None = Field(None, description="Value proposition")

    # Brand
    brand_positioning: str | None = Field(None, description="Brand positioning")
    brand_tone: str | None = Field(None, description="Brand tone/voice")
    brand_maturity: str | None = Field(None, description="Brand maturity level")

    # Tech and SEO
    tech_stack: list[str] | None = Field(None, description="Detected technologies")
    seo_structure: dict[str, Any] | None = Field(None, description="SEO metadata")
    keywords: list[str] | None = Field(None, description="Market keywords")

    # Market intelligence
    detected_competitors: list[str] | None = Field(None, description="Detected competitors")
    ideal_customer_profile: str | None = Field(None, description="ICP description")

    # Metadata
    enrichment_source: str = Field("api", description="Source of enrichment")
    enrichment_date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: str = Field("medium", description="Confidence level: low/medium/high")


class EnrichmentService:
    """Service for enriching business context from website URLs."""

    def __init__(self) -> None:
        """Initialize the enrichment service."""
        self.settings = get_settings()
        self.claude_client = ClaudeClient()
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; BoardOfOne/1.0; +https://boardof.one)"
            },
        )

    async def enrich_from_url(self, url: str) -> EnrichedContext:
        """Enrich business context from a website URL.

        Args:
            url: Website URL to analyze

        Returns:
            EnrichedContext with extracted business information

        Raises:
            ValueError: If URL is invalid
            httpx.HTTPError: If website fetch fails
        """
        # Validate and normalize URL
        url = self._normalize_url(url)
        domain = urlparse(url).netloc

        logger.info(f"Enriching context from URL: {url}")

        # Step 1: Fetch website metadata
        website_data = await self._fetch_website_metadata(url)

        # Step 2: Search for company information (if Brave API key available)
        search_data = await self._search_company_info(domain)

        # Step 3: Use Claude to extract and structure the data
        enriched = await self._extract_with_claude(url, website_data, search_data)

        return enriched

    def _normalize_url(self, url: str) -> str:
        """Normalize URL to ensure it has a scheme."""
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Validate URL structure
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        return url

    async def _fetch_website_metadata(self, url: str) -> dict[str, Any]:
        """Fetch and parse website metadata (meta tags, OG data)."""
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            html = response.text

            # Extract metadata
            metadata: dict[str, Any] = {
                "url": url,
                "title": self._extract_tag(html, "title"),
                "description": self._extract_meta(html, "description"),
                "og_title": self._extract_meta(html, "og:title"),
                "og_description": self._extract_meta(html, "og:description"),
                "og_type": self._extract_meta(html, "og:type"),
                "og_image": self._extract_meta(html, "og:image"),
                "keywords": self._extract_meta(html, "keywords"),
                "author": self._extract_meta(html, "author"),
            }

            # Detect some tech stack indicators
            tech_stack = []
            if "react" in html.lower() or "data-reactroot" in html:
                tech_stack.append("React")
            if "vue" in html.lower() or "data-v-" in html:
                tech_stack.append("Vue.js")
            if "angular" in html.lower():
                tech_stack.append("Angular")
            if "next" in html.lower() or "__NEXT_DATA__" in html:
                tech_stack.append("Next.js")
            if "shopify" in html.lower():
                tech_stack.append("Shopify")
            if "wordpress" in html.lower() or "wp-content" in html:
                tech_stack.append("WordPress")
            if "webflow" in html.lower():
                tech_stack.append("Webflow")

            metadata["detected_tech"] = tech_stack

            # Extract visible text snippet for analysis
            # Remove scripts, styles, and get text
            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            metadata["text_snippet"] = text[:3000]  # First 3000 chars

            return metadata

        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch website {url}: {e}")
            return {"url": url, "error": str(e)}

    def _extract_tag(self, html: str, tag: str) -> str | None:
        """Extract content from a simple tag like <title>."""
        match = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", html, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_meta(self, html: str, name: str) -> str | None:
        """Extract content from a meta tag."""
        # Try both name and property attributes
        patterns = [
            rf'<meta[^>]*name=["\']?{name}["\']?[^>]*content=["\']([^"\']+)["\']',
            rf'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']?{name}["\']?',
            rf'<meta[^>]*property=["\']?{name}["\']?[^>]*content=["\']([^"\']+)["\']',
            rf'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']?{name}["\']?',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    async def _search_company_info(self, domain: str) -> dict[str, Any]:
        """Search for company information using Brave Search API."""
        brave_api_key = self.settings.brave_api_key

        if not brave_api_key:
            logger.info("Brave API key not configured, skipping search enrichment")
            return {}

        try:
            search_url = "https://api.search.brave.com/res/v1/web/search"
            headers = {"X-Subscription-Token": brave_api_key}
            params: dict[str, str | int] = {
                "q": f'"{domain}" company about',
                "count": 5,
            }

            response = await self.http_client.get(search_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Extract relevant info from search results
            results = data.get("web", {}).get("results", [])
            search_info = {
                "results": [
                    {
                        "title": r.get("title"),
                        "description": r.get("description"),
                        "url": r.get("url"),
                    }
                    for r in results[:5]
                ]
            }

            return search_info

        except Exception as e:
            logger.warning(f"Brave search failed for {domain}: {e}")
            return {}

    async def _extract_with_claude(
        self,
        url: str,
        website_data: dict[str, Any],
        search_data: dict[str, Any],
    ) -> EnrichedContext:
        """Use Claude to extract and structure business context."""
        # Build prompt with all available data
        prompt = f"""Analyze this website and extract business context information.

WEBSITE URL: {url}

WEBSITE METADATA:
- Title: {website_data.get("title", "N/A")}
- Description: {website_data.get("description", "N/A")}
- OG Title: {website_data.get("og_title", "N/A")}
- OG Description: {website_data.get("og_description", "N/A")}
- Keywords: {website_data.get("keywords", "N/A")}
- Detected Tech: {", ".join(website_data.get("detected_tech", []))}

WEBSITE TEXT SNIPPET:
{website_data.get("text_snippet", "N/A")[:2000]}

SEARCH RESULTS:
{self._format_search_results(search_data)}

Based on this information, extract and return a JSON object with the following fields:
{{
    "company_name": "extracted company name",
    "industry": "industry vertical (e.g., SaaS, E-commerce, Healthcare)",
    "business_model": "business model type (e.g., B2B SaaS, Marketplace, Agency, D2C)",
    "pricing_model": "pricing model if detected (e.g., Subscription, Freemium, Usage-based)",
    "target_market": "target market description",
    "product_description": "brief product/service description",
    "product_categories": ["category1", "category2"],
    "main_value_proposition": "main value proposition",
    "brand_positioning": "brand positioning statement",
    "brand_tone": "brand tone (e.g., Professional, Friendly, Technical, Casual)",
    "brand_maturity": "brand maturity (startup, emerging, established, mature)",
    "detected_competitors": ["Competitor1", "Competitor2"],
    "ideal_customer_profile": "description of ideal customer",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "confidence": "low/medium/high based on data quality"
}}

IMPORTANT for detected_competitors:
- List 3-5 SPECIFIC competitor company names (e.g., "Notion", "Asana", "Monday.com")
- Do NOT include generic terms like "Top 10 Tools", "Best Software", or "Productivity Apps"
- Only include actual company names you are confident exist
- If unsure about competitors, leave the array empty rather than guessing

Return ONLY valid JSON, no other text."""

        try:
            response, _ = await self.claude_client.call(
                model="haiku",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                prefill="{",
            )

            # Parse JSON response
            import json

            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    logger.error(f"Failed to parse Claude response as JSON: {response[:200]}")
                    data = {}

            # Build EnrichedContext from parsed data
            return EnrichedContext(
                company_name=data.get("company_name"),
                website=url,
                industry=data.get("industry"),
                business_model=data.get("business_model"),
                pricing_model=data.get("pricing_model"),
                target_market=data.get("target_market"),
                product_description=data.get("product_description"),
                product_categories=data.get("product_categories"),
                main_value_proposition=data.get("main_value_proposition"),
                brand_positioning=data.get("brand_positioning"),
                brand_tone=data.get("brand_tone"),
                brand_maturity=data.get("brand_maturity"),
                tech_stack=website_data.get("detected_tech"),
                seo_structure={
                    "title": website_data.get("title"),
                    "description": website_data.get("description"),
                    "og_title": website_data.get("og_title"),
                    "og_description": website_data.get("og_description"),
                    "keywords": website_data.get("keywords"),
                },
                keywords=data.get("keywords"),
                detected_competitors=data.get("detected_competitors"),
                ideal_customer_profile=data.get("ideal_customer_profile"),
                enrichment_source="api",
                confidence=data.get("confidence", "medium"),
            )

        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            # Return basic context from metadata only
            return EnrichedContext(
                company_name=website_data.get("title"),
                website=url,
                industry=None,
                business_model=None,
                pricing_model=None,
                target_market=None,
                product_description=website_data.get("description"),
                product_categories=None,
                main_value_proposition=None,
                brand_positioning=None,
                brand_tone=None,
                brand_maturity=None,
                tech_stack=website_data.get("detected_tech"),
                seo_structure={
                    "title": website_data.get("title"),
                    "description": website_data.get("description"),
                },
                keywords=None,
                detected_competitors=None,
                ideal_customer_profile=None,
                enrichment_source="scrape",
                confidence="low",
            )

    def _format_search_results(self, search_data: dict[str, Any]) -> str:
        """Format search results for the prompt."""
        if not search_data or "results" not in search_data:
            return "No search results available."

        lines = []
        for i, result in enumerate(search_data["results"], 1):
            lines.append(f"{i}. {result.get('title', 'N/A')}")
            lines.append(f"   {result.get('description', 'N/A')}")
        return "\n".join(lines)

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http_client.aclose()


# Convenience function for one-off enrichment
async def enrich_website(url: str) -> EnrichedContext:
    """Convenience function to enrich a single URL.

    Args:
        url: Website URL to analyze

    Returns:
        EnrichedContext with extracted business information
    """
    service = EnrichmentService()
    try:
        return await service.enrich_from_url(url)
    finally:
        await service.close()
