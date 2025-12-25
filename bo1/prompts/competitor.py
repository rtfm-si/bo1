"""Competitor analyzer prompts for generating competitor insights.

Provides prompt templates for analyzing competitors and generating
structured insight cards with strengths, weaknesses, and market gaps.
"""

from typing import Any

# System prompt for competitor analysis
COMPETITOR_SYSTEM_PROMPT = """You are a competitive intelligence analyst helping to understand competitor companies.
Given a competitor name and user context, generate a structured competitive analysis.

Your analysis should include:
1. Company identification (tagline, size estimate)
2. Revenue estimation based on public signals
3. Key strengths (what they do well)
4. Key weaknesses (where they fall short)
5. Market gaps (opportunities for the user)

IMPORTANT RULES:
- Base analysis on REAL data from web search results when available
- Be specific and actionable, not generic
- If information is limited, say "Limited public data" rather than hallucinating
- Focus on B2B/SaaS context if user is in that space
- Limit each list to 3-5 items, prioritized by importance
- Keep estimates conservative with ranges (e.g., "$5M-20M ARR" not "$15M ARR")

Output JSON object:
{
  "name": "Company Name",
  "tagline": "Their positioning statement or null if unknown",
  "size_estimate": "Employee range or null",
  "revenue_estimate": "ARR/revenue range or null",
  "strengths": ["Strength 1", "Strength 2", ...],
  "weaknesses": ["Weakness 1", "Weakness 2", ...],
  "market_gaps": ["Gap/opportunity 1", "Gap/opportunity 2", ...]
}

No markdown, no explanation - just the JSON object."""

# User prompt template
COMPETITOR_USER_TEMPLATE = """Analyze this competitor:
- Competitor: {competitor_name}

User context for comparison:
- Industry: {industry}
- Product: {product_description}
- Value proposition: {value_proposition}

{search_context}

Generate a competitive analysis JSON for this competitor."""

# Template for when no search results are available
LIMITED_DATA_TEMPLATE = """Analyze this competitor with limited available data:
- Competitor: {competitor_name}
- Industry: {industry}

Note: No web search results available. Base analysis on general knowledge.
If you don't have reliable information, use null values and mark data as limited.

Generate a competitive analysis JSON for this competitor."""


def build_competitor_prompt(
    competitor_name: str,
    industry: str | None = None,
    product_description: str | None = None,
    value_proposition: str | None = None,
    search_results: list[dict[str, Any]] | None = None,
) -> str:
    """Build the user prompt for competitor analysis.

    Args:
        competitor_name: Name of competitor to analyze
        industry: User's industry for context
        product_description: User's product description
        value_proposition: User's main value proposition
        search_results: Optional web search results for the competitor

    Returns:
        Formatted user prompt string
    """
    # Build search context if available
    search_context = ""
    if search_results:
        context_parts = []
        for i, result in enumerate(search_results[:5], 1):
            title = result.get("title", "")
            content = result.get("content", result.get("snippet", ""))[:300]
            url = result.get("url", "")
            context_parts.append(f"{i}. {title}\n   URL: {url}\n   {content}")
        search_context = "Web search results:\n" + "\n\n".join(context_parts)
    else:
        search_context = (
            "Note: No web search results available. Base analysis on general knowledge."
        )

    # Use limited data template if no context
    if not industry and not product_description:
        return LIMITED_DATA_TEMPLATE.format(
            competitor_name=competitor_name,
            industry=industry or "Unknown",
        )

    return COMPETITOR_USER_TEMPLATE.format(
        competitor_name=competitor_name,
        industry=industry or "Not specified",
        product_description=product_description or "Not specified",
        value_proposition=value_proposition or "Not specified",
        search_context=search_context,
    )
