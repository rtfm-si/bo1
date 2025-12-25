"""Trend analyzer prompts for generating market trend insights.

Provides prompt templates for analyzing market trend URLs and generating
structured insights with key takeaways, relevance, and recommended actions.
"""

# System prompt for trend analysis
TREND_SYSTEM_PROMPT = """You are a market intelligence analyst helping business leaders extract actionable insights from market trends and industry news.

Given a trend URL with its content and user's business context, generate a structured analysis.

Your analysis should include:
1. Key takeaway - The single most important insight from this trend
2. Relevance to user's business - Why this matters for their specific situation
3. Recommended actions - 2-3 concrete steps they could take
4. Timeframe - When this trend is most relevant (immediate/short-term/long-term)

IMPORTANT RULES:
- Focus on ACTIONABLE insights, not just summaries
- Be specific to the user's industry and business context
- If content is paywalled or inaccessible, say so clearly
- Keep language concise and business-focused
- Prioritize strategic implications over tactical details
- Limit recommended actions to 2-3 high-impact items

Output JSON object:
{
  "title": "Trend title or headline",
  "key_takeaway": "The single most important insight",
  "relevance": "Why this matters for the user's specific business",
  "actions": ["Action 1", "Action 2", "Action 3"],
  "timeframe": "immediate|short_term|long_term",
  "confidence": "high|medium|low"
}

No markdown, no explanation - just the JSON object."""

# User prompt template
TREND_USER_TEMPLATE = """Analyze this market trend for actionable insights:

URL: {url}

Content excerpt:
{content}

User's business context:
- Industry: {industry}
- Product: {product_description}
- Business model: {business_model}
- Target market: {target_market}

Generate an actionable insight analysis JSON for this trend."""

# Template for when content is limited
LIMITED_CONTENT_TEMPLATE = """Analyze this market trend with limited available content:

URL: {url}
Title: {title}

Note: Full content not accessible. Generate insight based on title and URL only.
Set confidence to "low" and note in relevance that full analysis requires content access.

User's industry: {industry}

Generate a partial insight analysis JSON for this trend."""


def build_trend_prompt(
    url: str,
    content: str | None = None,
    title: str | None = None,
    industry: str | None = None,
    product_description: str | None = None,
    business_model: str | None = None,
    target_market: str | None = None,
) -> str:
    """Build the user prompt for trend analysis.

    Args:
        url: URL of the trend article
        content: Extracted text content from the URL
        title: Page title if available
        industry: User's industry for context
        product_description: User's product description
        business_model: User's business model
        target_market: User's target market

    Returns:
        Formatted user prompt string
    """
    # Use limited template if no content available
    if not content or len(content.strip()) < 100:
        return LIMITED_CONTENT_TEMPLATE.format(
            url=url,
            title=title or "Unknown",
            industry=industry or "Not specified",
        )

    # Truncate content to ~10KB to fit context window
    truncated_content = content[:10000]
    if len(content) > 10000:
        truncated_content += "\n\n[Content truncated...]"

    return TREND_USER_TEMPLATE.format(
        url=url,
        content=truncated_content,
        industry=industry or "Not specified",
        product_description=product_description or "Not specified",
        business_model=business_model or "Not specified",
        target_market=target_market or "Not specified",
    )
