"""SEO Trend Analyzer API endpoints.

Provides:
- POST /api/v1/seo/analyze-trends - Analyze SEO trends for keywords/industry
- GET /api/v1/seo/history - User's past trend analyses
"""

import logging
from datetime import UTC, datetime
from typing import Any  # noqa: F401

from fastapi import APIRouter, Depends, Query, Request
from psycopg2.extras import Json
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import (
    SEO_ANALYZE_RATE_LIMIT,
    SEO_GENERATE_RATE_LIMIT,
    limiter,
)
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import get_user_tier, has_seo_access
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.agents.researcher import ResearcherAgent
from bo1.billing import PlanConfig
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/seo", tags=["seo"])


# =============================================================================
# Models
# =============================================================================


# =============================================================================
# Marketing Asset Models
# =============================================================================


class AssetType(str):
    """Valid asset types for marketing collateral."""

    IMAGE = "image"
    ANIMATION = "animation"
    CONCEPT = "concept"
    TEMPLATE = "template"


class MarketingAsset(BaseModel):
    """A marketing asset in the collateral bank."""

    id: int = Field(..., description="Asset ID")
    filename: str = Field(..., description="Original filename")
    cdn_url: str = Field(..., description="CDN URL for embedding")
    asset_type: str = Field(..., description="Asset type: image, animation, concept, template")
    title: str = Field(..., description="User-friendly title")
    description: str | None = Field(None, description="Optional description")
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    created_at: datetime = Field(..., description="When asset was uploaded")
    updated_at: datetime = Field(..., description="When asset was last updated")


class MarketingAssetCreate(BaseModel):
    """Request to create a marketing asset (metadata only, file uploaded separately)."""

    title: str = Field(..., min_length=1, max_length=255, description="User-friendly title")
    asset_type: str = Field(..., description="Asset type: image, animation, concept, template")
    description: str | None = Field(None, max_length=1000, description="Optional description")
    tags: list[str] = Field(
        default_factory=list, max_length=20, description="Tags for search (max 20)"
    )


class MarketingAssetUpdate(BaseModel):
    """Request to update a marketing asset."""

    title: str | None = Field(None, max_length=255, description="Updated title")
    description: str | None = Field(None, max_length=1000, description="Updated description")
    tags: list[str] | None = Field(None, max_length=20, description="Updated tags")


class MarketingAssetListResponse(BaseModel):
    """Response containing list of marketing assets."""

    assets: list[MarketingAsset] = Field(default_factory=list, description="User's assets")
    total: int = Field(..., description="Total number of assets")
    remaining: int = Field(..., description="Remaining asset slots (-1 for unlimited)")


class AssetSuggestion(BaseModel):
    """A suggested asset for article content."""

    id: int = Field(..., description="Asset ID")
    title: str = Field(..., description="Asset title")
    cdn_url: str = Field(..., description="CDN URL for embedding")
    asset_type: str = Field(..., description="Asset type")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to article keywords")
    matching_tags: list[str] = Field(default_factory=list, description="Tags that matched")


class AssetSuggestionsResponse(BaseModel):
    """Response containing suggested assets for an article."""

    suggestions: list[AssetSuggestion] = Field(default_factory=list, description="Suggested assets")
    article_keywords: list[str] = Field(
        default_factory=list, description="Keywords used for matching"
    )


# =============================================================================
# SEO Trend Models
# =============================================================================


class TrendAnalysisRequest(BaseModel):
    """Request for SEO trend analysis."""

    keywords: list[str] = Field(
        ..., min_length=1, max_length=10, description="Keywords to analyze (1-10)"
    )
    industry: str | None = Field(None, description="Industry context for analysis")


class TrendOpportunity(BaseModel):
    """A trend opportunity identified."""

    topic: str = Field(..., description="Topic name")
    trend_direction: str = Field(..., description="rising, stable, declining")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to keywords")
    description: str = Field(..., description="Brief description")


class TrendThreat(BaseModel):
    """A trend threat identified."""

    topic: str = Field(..., description="Topic name")
    threat_type: str = Field(..., description="competition, saturation, regulation")
    severity: str = Field(..., description="high, medium, low")
    description: str = Field(..., description="Brief description")


class TrendAnalysisResult(BaseModel):
    """Result of SEO trend analysis."""

    executive_summary: str = Field(..., description="Executive summary of trends")
    key_trends: list[str] = Field(default_factory=list, description="Key trend highlights")
    opportunities: list[TrendOpportunity] = Field(
        default_factory=list, description="Identified opportunities"
    )
    threats: list[TrendThreat] = Field(default_factory=list, description="Identified threats")
    keywords_analyzed: list[str] = Field(..., description="Keywords that were analyzed")
    industry: str | None = Field(None, description="Industry context used")
    sources: list[str] = Field(default_factory=list, description="Research sources")


class TrendAnalysisResponse(BaseModel):
    """Response containing trend analysis."""

    id: int = Field(..., description="Analysis ID")
    results: TrendAnalysisResult = Field(..., description="Analysis results")
    created_at: datetime = Field(..., description="When analysis was created")
    remaining_analyses: int = Field(
        ..., description="Remaining analyses this month (-1 for unlimited)"
    )


class HistoryEntry(BaseModel):
    """A historical trend analysis entry."""

    id: int = Field(..., description="Analysis ID")
    keywords: list[str] = Field(..., description="Keywords analyzed")
    industry: str | None = Field(None, description="Industry context")
    executive_summary: str = Field(..., description="Executive summary")
    created_at: datetime = Field(..., description="When analysis was created")


class HistoryResponse(BaseModel):
    """Response containing analysis history."""

    analyses: list[HistoryEntry] = Field(default_factory=list, description="Past analyses")
    total: int = Field(..., description="Total number of analyses")
    remaining_this_month: int = Field(
        ..., description="Remaining analyses this month (-1 for unlimited)"
    )


# =============================================================================
# SEO Topics Models
# =============================================================================


class SeoTopicStatus(str):
    """Valid status values for SEO topics."""

    RESEARCHED = "researched"
    WRITING = "writing"
    PUBLISHED = "published"


# =============================================================================
# Topic Analysis Models
# =============================================================================


class TopicSuggestion(BaseModel):
    """A topic suggestion from user-submitted words analysis."""

    keyword: str = Field(..., description="Primary keyword/topic phrase")
    seo_potential: str = Field(..., description="SEO potential: high, medium, low")
    trend_status: str = Field(..., description="Trend status: rising, stable, declining")
    related_keywords: list[str] = Field(default_factory=list, description="Related keywords")
    description: str = Field(..., description="Brief description of the topic opportunity")
    # Validation fields (populated via web research)
    validation_status: str = Field(
        "unvalidated", description="Validation status: validated, unvalidated"
    )
    competitor_presence: str = Field(
        "unknown", description="Competitor presence: high, medium, low, unknown"
    )
    search_volume_indicator: str = Field(
        "unknown", description="Search volume indicator: high, medium, low, unknown"
    )
    validation_sources: list[str] = Field(
        default_factory=list, description="URLs from web research validation"
    )


class AnalyzeTopicsRequest(BaseModel):
    """Request to analyze user-submitted words for topic suggestions."""

    words: list[str] = Field(
        ..., min_length=1, max_length=10, description="Words/phrases to analyze (1-10)"
    )
    skip_validation: bool = Field(
        False, description="Skip web research validation for faster response"
    )


class AnalyzeTopicsResponse(BaseModel):
    """Response containing topic suggestions."""

    suggestions: list[TopicSuggestion] = Field(
        default_factory=list, description="Topic suggestions"
    )
    analyzed_words: list[str] = Field(..., description="Words that were analyzed")


class SeoTopic(BaseModel):
    """An SEO topic for blog generation."""

    id: int = Field(..., description="Topic ID")
    keyword: str = Field(..., description="Primary keyword/topic")
    status: str = Field(..., description="Status: researched, writing, published")
    source_analysis_id: int | None = Field(None, description="Source trend analysis ID")
    notes: str | None = Field(None, description="User notes")
    created_at: datetime = Field(..., description="When topic was created")
    updated_at: datetime = Field(..., description="When topic was last updated")


class SeoTopicCreate(BaseModel):
    """Request to create an SEO topic."""

    keyword: str = Field(..., min_length=1, max_length=255, description="Primary keyword/topic")
    source_analysis_id: int | None = Field(None, description="Source trend analysis ID")
    notes: str | None = Field(None, max_length=1000, description="User notes")


class SeoTopicUpdate(BaseModel):
    """Request to update an SEO topic."""

    status: str | None = Field(None, description="New status: researched, writing, published")
    notes: str | None = Field(None, max_length=1000, description="Updated notes")


class SeoTopicListResponse(BaseModel):
    """Response containing list of SEO topics."""

    topics: list[SeoTopic] = Field(default_factory=list, description="User's SEO topics")
    total: int = Field(..., description="Total number of topics")


# =============================================================================
# Helpers
# =============================================================================


def _get_monthly_usage(user_id: str) -> int:
    """Get user's SEO analysis usage for current month.

    Args:
        user_id: User ID

    Returns:
        Number of analyses this month
    """
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM seo_trend_analyses
                WHERE user_id = %s
                AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return row["count"] if row else 0


def _save_analysis(
    user_id: str, workspace_id: str | None, keywords: list[str], industry: str | None, results: dict
) -> int:
    """Save analysis to database.

    Args:
        user_id: User ID
        workspace_id: Optional workspace ID
        keywords: Keywords analyzed
        industry: Industry context
        results: Analysis results

    Returns:
        Analysis ID
    """
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO seo_trend_analyses
                (user_id, workspace_id, keywords, industry, results_json)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, workspace_id, keywords, industry, Json(results)),
            )
            row = cursor.fetchone()
            conn.commit()
            return row["id"]


async def _perform_trend_analysis(
    keywords: list[str], industry: str | None, user_tier: str
) -> TrendAnalysisResult:
    """Perform trend analysis using ResearcherAgent.

    Args:
        keywords: Keywords to analyze
        industry: Industry context
        user_tier: User's subscription tier

    Returns:
        TrendAnalysisResult
    """
    # Build research questions for the keywords
    questions = []
    for keyword in keywords:
        questions.append(
            {
                "question": f"What are the current SEO trends for '{keyword}'? Include search volume trends, competition level, and emerging related topics.",
                "priority": "CRITICAL",
                "reason": f"SEO trend analysis for keyword: {keyword}",
            }
        )

    # Add industry-specific question if provided
    if industry:
        questions.append(
            {
                "question": f"What are the top SEO opportunities and threats in the {industry} industry for 2024-2025?",
                "priority": "HIGH",
                "reason": f"Industry context: {industry}",
            }
        )

    # Use ResearcherAgent for deep research
    agent = ResearcherAgent()
    research_results = await agent.research_questions(
        questions,
        category="seo_trends",
        industry=industry,
        research_depth="deep",
        user_tier=user_tier,
    )

    # Parse research results into structured format
    sources = []
    key_trends = []
    opportunities = []
    threats = []

    for result in research_results:
        # Collect sources
        if result.get("sources"):
            sources.extend(result["sources"])

        # Extract summary as a key trend
        if result.get("summary"):
            key_trends.append(result["summary"][:200])

    # Remove duplicates and limit
    sources = list(set(sources))[:10]
    key_trends = key_trends[:5]

    # Generate executive summary from key trends
    executive_summary = (
        f"Analysis of {len(keywords)} keyword(s) "
        + (f"in the {industry} industry " if industry else "")
        + f"identified {len(key_trends)} key trends. "
        + (key_trends[0] if key_trends else "Research in progress.")
    )

    # Create sample opportunities based on research
    if key_trends:
        opportunities.append(
            TrendOpportunity(
                topic=keywords[0],
                trend_direction="rising",
                relevance_score=0.8,
                description=key_trends[0][:150]
                if key_trends
                else "Emerging opportunity identified",
            )
        )

    return TrendAnalysisResult(
        executive_summary=executive_summary,
        key_trends=key_trends,
        opportunities=opportunities,
        threats=threats,
        keywords_analyzed=keywords,
        industry=industry,
        sources=sources,
    )


async def _validate_topic_with_web_research(
    keyword: str,
    industry: str | None,
    competitors: list[str],
    user_tier: str,
) -> dict[str, Any]:
    """Validate a topic suggestion using web research.

    Performs web searches to determine:
    - competitor_presence: How many competitors are actively targeting this keyword
    - search_volume_indicator: Relative search interest based on result count/quality
    - validation_sources: URLs from search results

    Args:
        keyword: Topic keyword to validate
        industry: User's industry for context
        competitors: List of competitor domains to check
        user_tier: User's subscription tier

    Returns:
        Dictionary with:
        - competitor_presence: "high"|"medium"|"low"|"unknown"
        - search_volume_indicator: "high"|"medium"|"low"|"unknown"
        - validation_sources: list[str]
        - validation_status: "validated"|"unvalidated"
    """
    agent = ResearcherAgent()

    # Build search queries
    questions = []

    # Main topic search for search volume estimation
    search_query = f"{keyword}"
    if industry:
        search_query = f"{keyword} {industry}"

    questions.append(
        {
            "question": f"What is the current search interest and content availability for '{search_query}'? How many quality articles and resources exist?",
            "priority": "HIGH",
            "reason": f"SEO validation for topic: {keyword}",
        }
    )

    # Competitor presence check (if we have competitors)
    competitor_mentions = 0
    if competitors:
        # Check top 3 competitors max
        for comp_domain in competitors[:3]:
            questions.append(
                {
                    "question": f"Does {comp_domain} have content about '{keyword}'?",
                    "priority": "MEDIUM",
                    "reason": f"Competitor check: {comp_domain}",
                }
            )

    try:
        results = await agent.research_questions(
            questions,
            category="seo_validation",
            industry=industry,
            research_depth="basic",
            user_tier=user_tier,
        )

        # Parse results
        sources: list[str] = []
        total_source_count = 0

        for result in results:
            if result.get("sources"):
                sources.extend(result["sources"][:3])  # Limit sources per result
                total_source_count += len(result.get("sources", []))

            # Check for competitor mentions in summary
            summary = result.get("summary", "").lower()
            for comp in competitors[:3]:
                if comp.lower() in summary:
                    competitor_mentions += 1

        # Dedupe sources and limit
        sources = list(dict.fromkeys(sources))[:5]

        # Determine search volume indicator based on source count
        if total_source_count >= 5:
            search_volume = "high"
        elif total_source_count >= 2:
            search_volume = "medium"
        elif total_source_count >= 1:
            search_volume = "low"
        else:
            search_volume = "unknown"

        # Determine competitor presence
        if competitors:
            if competitor_mentions >= 2:
                competitor_presence = "high"
            elif competitor_mentions >= 1:
                competitor_presence = "medium"
            else:
                competitor_presence = "low"
        else:
            competitor_presence = "unknown"

        return {
            "validation_status": "validated",
            "competitor_presence": competitor_presence,
            "search_volume_indicator": search_volume,
            "validation_sources": sources,
        }

    except Exception as e:
        logger.warning(f"Topic validation failed for '{keyword}': {e}")
        return {
            "validation_status": "unvalidated",
            "competitor_presence": "unknown",
            "search_volume_indicator": "unknown",
            "validation_sources": [],
        }


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/analyze-trends", response_model=TrendAnalysisResponse, responses={429: RATE_LIMIT_RESPONSE}
)
@handle_api_errors("analyze trends")
@limiter.limit(SEO_ANALYZE_RATE_LIMIT)
async def analyze_trends(
    request: Request,
    body: TrendAnalysisRequest,
    user: dict = Depends(get_current_user),
) -> TrendAnalysisResponse:
    """Analyze SEO trends for given keywords.

    Performs deep research using Brave Search to identify:
    - Current trends and search patterns
    - Opportunities for content creation
    - Competitive threats and market saturation

    Rate limited to 5 requests per minute.
    Tier limits: free=1/month, starter=5/month, pro=unlimited.
    """
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access (tier or promo)
    if not has_seo_access(user_id, tier):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan. Please upgrade to access this feature.",
            status=403,
        )

    # Check monthly limit
    limit = PlanConfig.get_seo_analyses_limit(tier)
    usage = _get_monthly_usage(user_id)

    if not PlanConfig.is_unlimited(limit) and usage >= limit:
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            f"Monthly SEO analysis limit reached ({limit}). Upgrade your plan for more analyses.",
            status=429,
        )

    # Perform analysis
    logger.info(f"Starting SEO trend analysis for user {user_id[:8]}... keywords={body.keywords}")

    results = await _perform_trend_analysis(body.keywords, body.industry, tier)

    # Get workspace ID if in workspace context
    workspace_id = getattr(request.state, "workspace_id", None)

    # Save to database
    analysis_id = _save_analysis(
        user_id=user_id,
        workspace_id=workspace_id,
        keywords=body.keywords,
        industry=body.industry,
        results=results.model_dump(),
    )

    # Calculate remaining
    remaining = -1 if PlanConfig.is_unlimited(limit) else (limit - usage - 1)

    logger.info(f"SEO trend analysis complete for user {user_id[:8]}..., id={analysis_id}")

    return TrendAnalysisResponse(
        id=analysis_id,
        results=results,
        created_at=datetime.now(UTC),
        remaining_analyses=remaining,
    )


@router.get("/history", response_model=HistoryResponse)
@handle_api_errors("get trend history")
async def get_history(
    request: Request,
    limit: int = Query(10, ge=1, le=50, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: dict = Depends(get_current_user),
) -> HistoryResponse:
    """Get user's past SEO trend analyses.

    Returns paginated list of previous analyses with summaries.
    """
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as count FROM seo_trend_analyses WHERE user_id = %s",
                (user_id,),
            )
            total = cursor.fetchone()["count"]

            # Get paginated results
            cursor.execute(
                """
                SELECT id, keywords, industry, results_json, created_at
                FROM seo_trend_analyses
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )

            analyses = []
            for row in cursor.fetchall():
                results_json = row["results_json"] or {}
                analyses.append(
                    HistoryEntry(
                        id=row["id"],
                        keywords=row["keywords"] or [],
                        industry=row["industry"],
                        executive_summary=results_json.get("executive_summary", ""),
                        created_at=row["created_at"],
                    )
                )

    # Calculate remaining this month
    tier_limit = PlanConfig.get_seo_analyses_limit(tier)
    usage = _get_monthly_usage(user_id)
    remaining = -1 if PlanConfig.is_unlimited(tier_limit) else (tier_limit - usage)

    return HistoryResponse(
        analyses=analyses,
        total=total,
        remaining_this_month=remaining,
    )


# =============================================================================
# SEO Topics Endpoints
# =============================================================================


@router.get("/topics", response_model=SeoTopicListResponse)
@handle_api_errors("list topics")
async def list_topics(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Number of topics to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: dict = Depends(get_current_user),
) -> SeoTopicListResponse:
    """List user's SEO topics.

    Returns paginated list of topics with status tracking.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as count FROM seo_topics WHERE user_id = %s",
                (user_id,),
            )
            total = cursor.fetchone()["count"]

            # Get paginated results
            cursor.execute(
                """
                SELECT id, keyword, status, source_analysis_id, notes, created_at, updated_at
                FROM seo_topics
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )

            topics = []
            for row in cursor.fetchall():
                topics.append(
                    SeoTopic(
                        id=row["id"],
                        keyword=row["keyword"],
                        status=row["status"],
                        source_analysis_id=row["source_analysis_id"],
                        notes=row["notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )

    return SeoTopicListResponse(topics=topics, total=total)


@router.post("/topics", response_model=SeoTopic, status_code=201)
@handle_api_errors("create topic")
async def create_topic(
    request: Request,
    body: SeoTopicCreate,
    user: dict = Depends(get_current_user),
) -> SeoTopic:
    """Create a new SEO topic.

    Creates a topic from a keyword, optionally linked to a trend analysis.
    """
    user_id = extract_user_id(user)
    workspace_id = getattr(request.state, "workspace_id", None)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # If source_analysis_id provided, verify it belongs to user
            if body.source_analysis_id:
                cursor.execute(
                    """
                    SELECT id FROM seo_trend_analyses
                    WHERE id = %s AND user_id = %s
                    """,
                    (body.source_analysis_id, user_id),
                )
                if not cursor.fetchone():
                    raise http_error(
                        ErrorCode.API_NOT_FOUND, "Source analysis not found", status=404
                    )

            cursor.execute(
                """
                INSERT INTO seo_topics
                (user_id, workspace_id, keyword, status, source_analysis_id, notes)
                VALUES (%s, %s, %s, 'researched', %s, %s)
                RETURNING id, keyword, status, source_analysis_id, notes, created_at, updated_at
                """,
                (user_id, workspace_id, body.keyword.strip(), body.source_analysis_id, body.notes),
            )
            row = cursor.fetchone()
            conn.commit()

            return SeoTopic(
                id=row["id"],
                keyword=row["keyword"],
                status=row["status"],
                source_analysis_id=row["source_analysis_id"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


class SeoTopicsAutogenerateResponse(BaseModel):
    """Response from autogenerate topics endpoint."""

    topics: list[SeoTopic] = Field(default_factory=list, description="Created topics")
    count: int = Field(0, ge=0, description="Number of topics created")


@router.post(
    "/topics/analyze",
    response_model=AnalyzeTopicsResponse,
    responses={429: RATE_LIMIT_RESPONSE},
)
@handle_api_errors("analyze topics")
@limiter.limit(SEO_ANALYZE_RATE_LIMIT)
async def analyze_topics(
    request: Request,
    body: AnalyzeTopicsRequest,
    user: dict = Depends(get_current_user),
) -> AnalyzeTopicsResponse:
    """Analyze user-submitted words to suggest SEO topic ideas.

    Takes a list of words/phrases and returns intelligent topic suggestions
    with SEO potential scoring, trend status, and related keywords.

    Rate limited to 5 requests per minute.
    """
    import json

    from anthropic import AsyncAnthropic

    from bo1.config import ANTHROPIC_API_KEY, resolve_model_alias

    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access (tier or promo)
    if not has_seo_access(user_id, tier):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan.",
            status=403,
        )

    # Validate input
    words = [w.strip() for w in body.words if w.strip()]
    if not words:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "At least one non-empty word is required",
            status=400,
        )

    # Get user context for personalization
    industry = None
    product_description = None
    competitors: list[str] = []

    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT industry, product_description FROM user_context
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                industry = row.get("industry")
                product_description = row.get("product_description")

            # Fetch competitors for validation (if not skipping)
            if not body.skip_validation:
                cursor.execute(
                    """
                    SELECT website FROM managed_competitors
                    WHERE user_id = %s AND website IS NOT NULL
                    LIMIT 5
                    """,
                    (user_id,),
                )
                competitors = [r["website"] for r in cursor.fetchall() if r.get("website")]

    # Build prompt for LLM
    context_parts = []
    if industry:
        context_parts.append(f"Industry: {industry}")
    if product_description:
        context_parts.append(f"Product/Service: {product_description[:200]}")

    context_str = "\n".join(context_parts) if context_parts else "No business context available."

    prompt = f"""Analyze the following words/phrases and suggest 3-5 SEO topic ideas based on them.

User's words: {", ".join(words)}

Business context:
{context_str}

For each topic suggestion, provide:
1. keyword: The primary keyword/topic phrase (clear, searchable)
2. seo_potential: Rate as "high", "medium", or "low" based on search intent and competition
3. trend_status: Rate as "rising", "stable", or "declining" based on current relevance
4. related_keywords: 2-4 related keywords that could be targeted
5. description: A brief (1-2 sentence) description of the content opportunity

Return your response as valid JSON in this format:
{{
  "suggestions": [
    {{
      "keyword": "example keyword",
      "seo_potential": "high",
      "trend_status": "rising",
      "related_keywords": ["related1", "related2"],
      "description": "Brief description of the opportunity"
    }}
  ]
}}

Focus on actionable, specific topics that would make good blog content. If the user has business context, tailor suggestions to their industry."""

    logger.info(f"Analyzing topics for user {user_id[:8]}... words={words}")

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        model = resolve_model_alias("haiku")

        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        content = response.content[0].text.strip()
        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()

        data = json.loads(content)
        suggestions = []

        for item in data.get("suggestions", [])[:5]:
            suggestions.append(
                TopicSuggestion(
                    keyword=item.get("keyword", "")[:100],
                    seo_potential=item.get("seo_potential", "medium"),
                    trend_status=item.get("trend_status", "stable"),
                    related_keywords=item.get("related_keywords", [])[:5],
                    description=item.get("description", "")[:300],
                )
            )

        logger.info(f"Generated {len(suggestions)} topic suggestions for user {user_id[:8]}...")

        # Validate top 5 suggestions via web research (unless skip_validation)
        if not body.skip_validation and suggestions:
            logger.info(f"Validating {len(suggestions)} suggestions for user {user_id[:8]}...")

            validated_suggestions = []
            for suggestion in suggestions[:5]:
                validation = await _validate_topic_with_web_research(
                    keyword=suggestion.keyword,
                    industry=industry,
                    competitors=competitors,
                    user_tier=tier,
                )
                # Merge validation results
                validated_suggestions.append(
                    TopicSuggestion(
                        keyword=suggestion.keyword,
                        seo_potential=suggestion.seo_potential,
                        trend_status=suggestion.trend_status,
                        related_keywords=suggestion.related_keywords,
                        description=suggestion.description,
                        validation_status=validation["validation_status"],
                        competitor_presence=validation["competitor_presence"],
                        search_volume_indicator=validation["search_volume_indicator"],
                        validation_sources=validation["validation_sources"],
                    )
                )

            suggestions = validated_suggestions
            logger.info(f"Validated {len(suggestions)} suggestions for user {user_id[:8]}...")

        return AnalyzeTopicsResponse(
            suggestions=suggestions,
            analyzed_words=words,
        )

    except json.JSONDecodeError as e:
        log_error(
            logger,
            ErrorCode.LLM_API_ERROR,
            f"Failed to parse topic analysis response for user {user_id[:8]}...",
            error=str(e),
        )
        raise http_error(
            ErrorCode.LLM_API_ERROR,
            "Failed to analyze topics - please try again",
            status=500,
        ) from e
    except Exception as e:
        log_error(
            logger,
            ErrorCode.LLM_API_ERROR,
            f"Topic analysis failed for user {user_id[:8]}...",
            error=str(e),
        )
        raise http_error(
            ErrorCode.LLM_API_ERROR,
            f"Failed to analyze topics: {e}",
            status=500,
        ) from e


@router.post(
    "/topics/autogenerate",
    response_model=SeoTopicsAutogenerateResponse,
    responses={429: RATE_LIMIT_RESPONSE},
)
@handle_api_errors("autogenerate topics")
@limiter.limit(SEO_ANALYZE_RATE_LIMIT)
async def autogenerate_topics(
    request: Request,
    user: dict = Depends(get_current_user),
) -> SeoTopicsAutogenerateResponse:
    """Autogenerate SEO topics using AI-powered discovery.

    Uses user's business context (industry, focus areas) to discover
    relevant topics. Filters out topics that already exist.

    Rate limited to 5 requests per minute.
    """
    from backend.services.topic_discovery import Topic, discover_topics

    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access (tier or promo)
    if not has_seo_access(user_id, tier):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan.",
            status=403,
        )

    # Get user context for discovery
    industry = None
    focus_areas: list[str] = []

    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT industry, focus_areas FROM user_context
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                industry = row.get("industry")
                focus_areas = row.get("focus_areas") or []

            # Get existing topic keywords to avoid duplicates
            cursor.execute(
                "SELECT keyword FROM seo_topics WHERE user_id = %s",
                (user_id,),
            )
            existing_keywords = [r["keyword"].lower() for r in cursor.fetchall()]

    # Discover topics using AI
    logger.info(
        f"Autogenerating topics for user {user_id[:8]}... "
        f"industry={industry}, focus_areas={len(focus_areas)}"
    )

    try:
        discovered: list[Topic] = await discover_topics(
            industry=industry,
            focus_areas=focus_areas,
            existing_topics=existing_keywords,
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.LLM_API_ERROR,
            f"Topic discovery failed for user {user_id[:8]}...",
            error=str(e),
        )
        raise http_error(
            ErrorCode.LLM_API_ERROR,
            f"Failed to generate topics: {e}",
            status=500,
        ) from e

    # Filter out topics that already exist (case-insensitive)
    new_topics = [t for t in discovered if t.title.lower() not in existing_keywords]

    # Get workspace ID if in workspace context
    workspace_id = getattr(request.state, "workspace_id", None)

    # Create topics in database
    created_topics: list[SeoTopic] = []

    with db_session() as conn:
        with conn.cursor() as cursor:
            for topic in new_topics:
                try:
                    cursor.execute(
                        """
                        INSERT INTO seo_topics
                        (user_id, workspace_id, keyword, status, notes)
                        VALUES (%s, %s, %s, 'researched', %s)
                        RETURNING id, keyword, status, source_analysis_id, notes, created_at, updated_at
                        """,
                        (user_id, workspace_id, topic.title, topic.description),
                    )
                    row = cursor.fetchone()
                    created_topics.append(
                        SeoTopic(
                            id=row["id"],
                            keyword=row["keyword"],
                            status=row["status"],
                            source_analysis_id=row["source_analysis_id"],
                            notes=row["notes"],
                            created_at=row["created_at"],
                            updated_at=row["updated_at"],
                        )
                    )
                except Exception as e:
                    # Skip duplicates or other insert errors
                    logger.warning(f"Failed to insert topic '{topic.title}': {e}")
                    continue

            conn.commit()

    logger.info(f"Created {len(created_topics)} autogenerated topics for user {user_id[:8]}...")

    return SeoTopicsAutogenerateResponse(
        topics=created_topics,
        count=len(created_topics),
    )


@router.patch("/topics/{topic_id}", response_model=SeoTopic)
@handle_api_errors("update topic")
async def update_topic(
    request: Request,
    topic_id: int,
    body: SeoTopicUpdate,
    user: dict = Depends(get_current_user),
) -> SeoTopic:
    """Update an SEO topic.

    Updates status and/or notes for a topic.
    """
    user_id = extract_user_id(user)

    # Validate status if provided
    valid_statuses = ["researched", "writing", "published"]
    if body.status and body.status not in valid_statuses:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            status=400,
        )

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Check topic exists and belongs to user
            cursor.execute(
                "SELECT id FROM seo_topics WHERE id = %s AND user_id = %s",
                (topic_id, user_id),
            )
            if not cursor.fetchone():
                raise http_error(ErrorCode.API_NOT_FOUND, "Topic not found", status=404)

            # Build dynamic update query
            updates = ["updated_at = now()"]
            params: list = []

            if body.status:
                updates.append("status = %s")
                params.append(body.status)

            if body.notes is not None:
                updates.append("notes = %s")
                params.append(body.notes)

            # Add WHERE clause params
            params.extend([topic_id, user_id])

            cursor.execute(
                f"""
                UPDATE seo_topics
                SET {", ".join(updates)}
                WHERE id = %s AND user_id = %s
                RETURNING id, keyword, status, source_analysis_id, notes, created_at, updated_at
                """,
                params,
            )
            row = cursor.fetchone()
            conn.commit()

            return SeoTopic(
                id=row["id"],
                keyword=row["keyword"],
                status=row["status"],
                source_analysis_id=row["source_analysis_id"],
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


@router.delete("/topics/{topic_id}", status_code=204, response_model=None)
@handle_api_errors("delete topic")
async def delete_topic(
    request: Request,
    topic_id: int,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete an SEO topic.

    Permanently removes the topic.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM seo_topics WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (topic_id, user_id),
            )
            if not cursor.fetchone():
                raise http_error(ErrorCode.API_NOT_FOUND, "Topic not found", status=404)
            conn.commit()


# =============================================================================
# SEO Blog Article Models
# =============================================================================


class SeoBlogArticle(BaseModel):
    """An SEO blog article."""

    id: int = Field(..., description="Article ID")
    topic_id: int | None = Field(None, description="Source topic ID")
    title: str = Field(..., description="Article title")
    excerpt: str | None = Field(None, description="Article excerpt/meta description")
    content: str = Field(..., description="Article content in Markdown")
    meta_title: str | None = Field(None, description="SEO meta title")
    meta_description: str | None = Field(None, description="SEO meta description")
    status: str = Field(..., description="Status: draft, published")
    created_at: datetime = Field(..., description="When article was created")
    updated_at: datetime = Field(..., description="When article was last updated")


class SeoBlogArticleUpdate(BaseModel):
    """Request to update an article."""

    title: str | None = Field(None, max_length=255, description="Updated title")
    excerpt: str | None = Field(None, max_length=500, description="Updated excerpt")
    content: str | None = Field(None, description="Updated content")
    meta_title: str | None = Field(None, max_length=255, description="Updated meta title")
    meta_description: str | None = Field(
        None, max_length=500, description="Updated meta description"
    )
    status: str | None = Field(None, description="New status: draft, published")


class RegenerateArticleRequest(BaseModel):
    """Request to regenerate an article with changes and/or tone."""

    tone: str | None = Field(
        None,
        description="Desired tone: Professional, Friendly, Technical, Persuasive, Conversational",
    )
    changes: list[str] | None = Field(
        None,
        max_length=3,
        description="List of specific changes to make (max 3)",
    )


class SeoBlogArticleListResponse(BaseModel):
    """Response containing list of articles."""

    articles: list[SeoBlogArticle] = Field(default_factory=list, description="User's articles")
    total: int = Field(..., description="Total number of articles")
    remaining_this_month: int = Field(
        ..., description="Remaining generations this month (-1 for unlimited)"
    )


# =============================================================================
# SEO Article Helpers
# =============================================================================


def _get_monthly_article_usage(user_id: str) -> int:
    """Get user's SEO article generation usage for current month."""
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM seo_blog_articles
                WHERE user_id = %s
                AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return row["count"] if row else 0


# =============================================================================
# SEO Blog Article Endpoints
# =============================================================================


@router.post(
    "/topics/{topic_id}/generate",
    response_model=SeoBlogArticle,
    status_code=201,
    responses={429: RATE_LIMIT_RESPONSE},
)
@handle_api_errors("generate article")
@limiter.limit(SEO_GENERATE_RATE_LIMIT)
async def generate_article(
    request: Request,
    topic_id: int,
    user: dict = Depends(get_current_user),
) -> SeoBlogArticle:
    """Generate a blog article from a topic.

    Uses AI to generate SEO-optimized content based on the topic keyword.
    Stores as draft and updates topic status to 'writing'.

    Rate limited to 2 requests per minute.
    Tier limits: free=1/month, starter=5/month, pro=unlimited.
    """
    from backend.services.content_generator import generate_blog_post

    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access (tier or promo)
    if not has_seo_access(user_id, tier):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan. Please upgrade to access this feature.",
            status=403,
        )

    # Check monthly limit
    monthly_limit = PlanConfig.get_seo_articles_limit(tier)
    usage = _get_monthly_article_usage(user_id)

    if not PlanConfig.is_unlimited(monthly_limit) and usage >= monthly_limit:
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            f"Monthly SEO article limit reached ({monthly_limit}). Upgrade your plan for more generations.",
            status=429,
        )

    # Get topic and verify ownership
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, keyword, status FROM seo_topics
                WHERE id = %s AND user_id = %s
                """,
                (topic_id, user_id),
            )
            topic_row = cursor.fetchone()
            if not topic_row:
                raise http_error(ErrorCode.API_NOT_FOUND, "Topic not found", status=404)

            keyword = topic_row["keyword"]

    # Generate blog content
    logger.info(f"Generating SEO article for user {user_id[:8]}... keyword={keyword}")

    try:
        blog_content = await generate_blog_post(keyword, [keyword])
    except ValueError as e:
        log_error(
            logger,
            ErrorCode.LLM_API_ERROR,
            f"Blog generation failed for topic {topic_id}",
            topic_id=topic_id,
            error=str(e),
        )
        raise http_error(
            ErrorCode.LLM_API_ERROR, f"Article generation failed: {e}", status=500
        ) from e

    # Get workspace ID if in workspace context
    workspace_id = getattr(request.state, "workspace_id", None)

    # Save article and update topic status
    with db_session() as conn:
        with conn.cursor() as cursor:
            # Insert article
            cursor.execute(
                """
                INSERT INTO seo_blog_articles
                (user_id, workspace_id, topic_id, title, excerpt, content, meta_title, meta_description, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'draft')
                RETURNING id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                """,
                (
                    user_id,
                    workspace_id,
                    topic_id,
                    blog_content.title,
                    blog_content.excerpt,
                    blog_content.content,
                    blog_content.meta_title,
                    blog_content.meta_description,
                ),
            )
            article_row = cursor.fetchone()

            # Update topic status to 'writing'
            cursor.execute(
                """
                UPDATE seo_topics SET status = 'writing', updated_at = now()
                WHERE id = %s AND user_id = %s
                """,
                (topic_id, user_id),
            )
            conn.commit()

            logger.info(f"Generated article id={article_row['id']} for topic {topic_id}")

            return SeoBlogArticle(
                id=article_row["id"],
                topic_id=article_row["topic_id"],
                title=article_row["title"],
                excerpt=article_row["excerpt"],
                content=article_row["content"],
                meta_title=article_row["meta_title"],
                meta_description=article_row["meta_description"],
                status=article_row["status"],
                created_at=article_row["created_at"],
                updated_at=article_row["updated_at"],
            )


@router.get("/articles", response_model=SeoBlogArticleListResponse)
@handle_api_errors("list articles")
async def list_articles(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: dict = Depends(get_current_user),
) -> SeoBlogArticleListResponse:
    """List user's SEO blog articles.

    Returns paginated list of generated articles.
    """
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Get total count
            cursor.execute(
                "SELECT COUNT(*) as count FROM seo_blog_articles WHERE user_id = %s",
                (user_id,),
            )
            total = cursor.fetchone()["count"]

            # Get paginated results
            cursor.execute(
                """
                SELECT id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                FROM seo_blog_articles
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )

            articles = []
            for row in cursor.fetchall():
                articles.append(
                    SeoBlogArticle(
                        id=row["id"],
                        topic_id=row["topic_id"],
                        title=row["title"],
                        excerpt=row["excerpt"],
                        content=row["content"],
                        meta_title=row["meta_title"],
                        meta_description=row["meta_description"],
                        status=row["status"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )

    # Calculate remaining this month
    tier_limit = PlanConfig.get_seo_articles_limit(tier)
    usage = _get_monthly_article_usage(user_id)
    remaining = -1 if PlanConfig.is_unlimited(tier_limit) else (tier_limit - usage)

    return SeoBlogArticleListResponse(
        articles=articles,
        total=total,
        remaining_this_month=remaining,
    )


@router.get("/articles/{article_id}", response_model=SeoBlogArticle)
@handle_api_errors("get article")
async def get_article(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> SeoBlogArticle:
    """Get a single article by ID."""
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                FROM seo_blog_articles
                WHERE id = %s AND user_id = %s
                """,
                (article_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            return SeoBlogArticle(
                id=row["id"],
                topic_id=row["topic_id"],
                title=row["title"],
                excerpt=row["excerpt"],
                content=row["content"],
                meta_title=row["meta_title"],
                meta_description=row["meta_description"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


@router.patch("/articles/{article_id}", response_model=SeoBlogArticle)
@handle_api_errors("update article")
async def update_article(
    request: Request,
    article_id: int,
    body: SeoBlogArticleUpdate,
    user: dict = Depends(get_current_user),
) -> SeoBlogArticle:
    """Update an SEO article.

    Can update content, metadata, and status.
    When status changes to 'published', also updates the linked topic status.
    """
    user_id = extract_user_id(user)

    # Validate status if provided
    valid_statuses = ["draft", "published"]
    if body.status and body.status not in valid_statuses:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
            status=400,
        )

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Check article exists and belongs to user
            cursor.execute(
                "SELECT id, topic_id, status FROM seo_blog_articles WHERE id = %s AND user_id = %s",
                (article_id, user_id),
            )
            existing = cursor.fetchone()
            if not existing:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            topic_id = existing["topic_id"]
            old_status = existing["status"]

            # Build dynamic update query
            updates = ["updated_at = now()"]
            params: list = []

            if body.title is not None:
                updates.append("title = %s")
                params.append(body.title)

            if body.excerpt is not None:
                updates.append("excerpt = %s")
                params.append(body.excerpt)

            if body.content is not None:
                updates.append("content = %s")
                params.append(body.content)

            if body.meta_title is not None:
                updates.append("meta_title = %s")
                params.append(body.meta_title)

            if body.meta_description is not None:
                updates.append("meta_description = %s")
                params.append(body.meta_description)

            if body.status is not None:
                updates.append("status = %s")
                params.append(body.status)

            # Add WHERE clause params
            params.extend([article_id, user_id])

            cursor.execute(
                f"""
                UPDATE seo_blog_articles
                SET {", ".join(updates)}
                WHERE id = %s AND user_id = %s
                RETURNING id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                """,
                params,
            )
            row = cursor.fetchone()

            # If status changed to published, update topic status too
            if body.status == "published" and old_status != "published" and topic_id:
                cursor.execute(
                    """
                    UPDATE seo_topics SET status = 'published', updated_at = now()
                    WHERE id = %s AND user_id = %s
                    """,
                    (topic_id, user_id),
                )

            conn.commit()

            return SeoBlogArticle(
                id=row["id"],
                topic_id=row["topic_id"],
                title=row["title"],
                excerpt=row["excerpt"],
                content=row["content"],
                meta_title=row["meta_title"],
                meta_description=row["meta_description"],
                status=row["status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


@router.post(
    "/articles/{article_id}/regenerate",
    response_model=SeoBlogArticle,
    responses={429: RATE_LIMIT_RESPONSE},
)
@handle_api_errors("regenerate article")
@limiter.limit(SEO_GENERATE_RATE_LIMIT)
async def regenerate_article(
    request: Request,
    article_id: int,
    body: RegenerateArticleRequest,
    user: dict = Depends(get_current_user),
) -> SeoBlogArticle:
    """Regenerate an article with specific changes and/or tone.

    Takes the original article and regenerates it with:
    - Up to 3 specific changes requested by the user
    - A different tone of voice (Professional, Friendly, Technical, Persuasive, Conversational)

    Rate limited to 2 requests per minute.
    Uses the same monthly quota as article generation.
    """
    from backend.services.content_generator import BlogContent, regenerate_blog_post

    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access (tier or promo)
    if not has_seo_access(user_id, tier):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan. Please upgrade to access this feature.",
            status=403,
        )

    # Check monthly limit (regeneration counts as generation)
    monthly_limit = PlanConfig.get_seo_articles_limit(tier)
    usage = _get_monthly_article_usage(user_id)

    if not PlanConfig.is_unlimited(monthly_limit) and usage >= monthly_limit:
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            f"Monthly SEO article limit reached ({monthly_limit}). Upgrade your plan for more generations.",
            status=429,
        )

    # Get article and verify ownership
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, topic_id, title, excerpt, content, meta_title, meta_description, status
                FROM seo_blog_articles
                WHERE id = %s AND user_id = %s
                """,
                (article_id, user_id),
            )
            article_row = cursor.fetchone()
            if not article_row:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

    # Create BlogContent from existing article
    original = BlogContent(
        title=article_row["title"],
        excerpt=article_row["excerpt"] or "",
        content=article_row["content"],
        meta_title=article_row["meta_title"] or article_row["title"],
        meta_description=article_row["meta_description"] or article_row["excerpt"] or "",
    )

    # Regenerate the article
    logger.info(
        f"Regenerating article {article_id} for user {user_id[:8]}... "
        f"tone={body.tone}, changes={len(body.changes or [])}"
    )

    try:
        regenerated = await regenerate_blog_post(
            original=original,
            changes=body.changes,
            tone=body.tone,
        )
    except ValueError as e:
        log_error(
            logger,
            ErrorCode.LLM_API_ERROR,
            f"Article regeneration failed for article {article_id}",
            article_id=article_id,
            error=str(e),
        )
        raise http_error(
            ErrorCode.LLM_API_ERROR, f"Article regeneration failed: {e}", status=500
        ) from e

    # Update article in database
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE seo_blog_articles
                SET title = %s, excerpt = %s, content = %s, meta_title = %s, meta_description = %s, updated_at = now()
                WHERE id = %s AND user_id = %s
                RETURNING id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                """,
                (
                    regenerated.title,
                    regenerated.excerpt,
                    regenerated.content,
                    regenerated.meta_title,
                    regenerated.meta_description,
                    article_id,
                    user_id,
                ),
            )
            updated_row = cursor.fetchone()
            conn.commit()

            logger.info(f"Regenerated article id={article_id} for user {user_id[:8]}...")

            return SeoBlogArticle(
                id=updated_row["id"],
                topic_id=updated_row["topic_id"],
                title=updated_row["title"],
                excerpt=updated_row["excerpt"],
                content=updated_row["content"],
                meta_title=updated_row["meta_title"],
                meta_description=updated_row["meta_description"],
                status=updated_row["status"],
                created_at=updated_row["created_at"],
                updated_at=updated_row["updated_at"],
            )


@router.delete("/articles/{article_id}", status_code=204, response_model=None)
@handle_api_errors("delete article")
async def delete_article(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete an SEO article.

    Permanently removes the article. Topic status remains unchanged.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM seo_blog_articles WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (article_id, user_id),
            )
            if not cursor.fetchone():
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)
            conn.commit()


# =============================================================================
# SEO Article Event Models
# =============================================================================


class ArticleEventType(str):
    """Valid event types for article analytics."""

    VIEW = "view"
    CLICK = "click"
    SIGNUP = "signup"


class ArticleEventCreate(BaseModel):
    """Request to record an article event."""

    event_type: str = Field(..., description="Event type: view, click, signup")
    referrer: str | None = Field(None, max_length=1000, description="HTTP referrer")
    utm_source: str | None = Field(None, max_length=255, description="UTM source")
    utm_medium: str | None = Field(None, max_length=255, description="UTM medium")
    utm_campaign: str | None = Field(None, max_length=255, description="UTM campaign")
    session_id: str | None = Field(None, max_length=255, description="Browser session ID")


class ArticleAnalytics(BaseModel):
    """Analytics for a single article."""

    article_id: int = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    views: int = Field(0, ge=0, description="Total views")
    clicks: int = Field(0, ge=0, description="Total clicks")
    signups: int = Field(0, ge=0, description="Total signups")
    ctr: float = Field(0.0, ge=0, le=1, description="Click-through rate (clicks/views)")
    signup_rate: float = Field(0.0, ge=0, le=1, description="Signup rate (signups/views)")


class ArticleAnalyticsListResponse(BaseModel):
    """Response containing analytics for all user's articles."""

    articles: list[ArticleAnalytics] = Field(default_factory=list, description="Article analytics")
    total_views: int = Field(0, ge=0, description="Total views across all articles")
    total_clicks: int = Field(0, ge=0, description="Total clicks across all articles")
    total_signups: int = Field(0, ge=0, description="Total signups across all articles")
    overall_ctr: float = Field(0.0, ge=0, le=1, description="Overall CTR")
    overall_signup_rate: float = Field(0.0, ge=0, le=1, description="Overall signup rate")


# =============================================================================
# SEO Article Event Endpoints
# =============================================================================


# Rate limit for event recording (public endpoint, stricter limit)
SEO_EVENT_RATE_LIMIT = "30/minute"


@router.post(
    "/articles/{article_id}/events",
    status_code=201,
    response_model=None,
    responses={429: RATE_LIMIT_RESPONSE},
)
@handle_api_errors("record article event")
@limiter.limit(SEO_EVENT_RATE_LIMIT)
async def record_article_event(
    request: Request,
    article_id: int,
    body: ArticleEventCreate,
) -> None:
    """Record an analytics event for an article.

    Public endpoint for tracking article views, clicks, and signups.
    Rate limited to 30 requests per minute per IP.

    No authentication required - used by public blog pages.
    """
    # Validate event type
    valid_event_types = ["view", "click", "signup"]
    if body.event_type not in valid_event_types:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}",
            status=400,
        )

    # Get user agent from request
    user_agent = request.headers.get("user-agent", "")[:500]

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Verify article exists (public, so no user_id check)
            cursor.execute(
                "SELECT id FROM seo_blog_articles WHERE id = %s",
                (article_id,),
            )
            if not cursor.fetchone():
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            # Insert event
            cursor.execute(
                """
                INSERT INTO seo_article_events
                (article_id, event_type, referrer, utm_source, utm_medium, utm_campaign, session_id, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    article_id,
                    body.event_type,
                    body.referrer,
                    body.utm_source,
                    body.utm_medium,
                    body.utm_campaign,
                    body.session_id,
                    user_agent,
                ),
            )
            conn.commit()

    logger.debug(f"Recorded {body.event_type} event for article {article_id}")


@router.get("/articles/{article_id}/analytics", response_model=ArticleAnalytics)
@handle_api_errors("get article analytics")
async def get_article_analytics(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> ArticleAnalytics:
    """Get analytics for a single article.

    Returns view/click/signup counts and calculated rates.
    Only accessible by the article owner.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Verify article exists and belongs to user
            cursor.execute(
                """
                SELECT id, title FROM seo_blog_articles
                WHERE id = %s AND user_id = %s
                """,
                (article_id, user_id),
            )
            article = cursor.fetchone()
            if not article:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            # Get event counts
            cursor.execute(
                """
                SELECT
                    event_type,
                    COUNT(*) as count
                FROM seo_article_events
                WHERE article_id = %s
                GROUP BY event_type
                """,
                (article_id,),
            )

            counts = {"view": 0, "click": 0, "signup": 0}
            for row in cursor.fetchall():
                counts[row["event_type"]] = row["count"]

            views = counts["view"]
            clicks = counts["click"]
            signups = counts["signup"]

            # Calculate rates (handle division by zero)
            ctr = clicks / views if views > 0 else 0.0
            signup_rate = signups / views if views > 0 else 0.0

            return ArticleAnalytics(
                article_id=article["id"],
                title=article["title"],
                views=views,
                clicks=clicks,
                signups=signups,
                ctr=round(ctr, 4),
                signup_rate=round(signup_rate, 4),
            )


@router.get("/analytics", response_model=ArticleAnalyticsListResponse)
@handle_api_errors("get aggregated analytics")
async def get_all_analytics(
    request: Request,
    user: dict = Depends(get_current_user),
) -> ArticleAnalyticsListResponse:
    """Get aggregated analytics for all user's articles.

    Returns per-article analytics plus overall totals.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Get all user's articles with their event counts
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.title,
                    COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) as views,
                    COALESCE(SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END), 0) as clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0) as signups
                FROM seo_blog_articles a
                LEFT JOIN seo_article_events e ON e.article_id = a.id
                WHERE a.user_id = %s
                GROUP BY a.id, a.title
                ORDER BY views DESC
                """,
                (user_id,),
            )

            articles = []
            total_views = 0
            total_clicks = 0
            total_signups = 0

            for row in cursor.fetchall():
                views = row["views"]
                clicks = row["clicks"]
                signups = row["signups"]

                total_views += views
                total_clicks += clicks
                total_signups += signups

                ctr = clicks / views if views > 0 else 0.0
                signup_rate = signups / views if views > 0 else 0.0

                articles.append(
                    ArticleAnalytics(
                        article_id=row["id"],
                        title=row["title"],
                        views=views,
                        clicks=clicks,
                        signups=signups,
                        ctr=round(ctr, 4),
                        signup_rate=round(signup_rate, 4),
                    )
                )

            overall_ctr = total_clicks / total_views if total_views > 0 else 0.0
            overall_signup_rate = total_signups / total_views if total_views > 0 else 0.0

            return ArticleAnalyticsListResponse(
                articles=articles,
                total_views=total_views,
                total_clicks=total_clicks,
                total_signups=total_signups,
                overall_ctr=round(overall_ctr, 4),
                overall_signup_rate=round(overall_signup_rate, 4),
            )


# =============================================================================
# Marketing Assets Endpoints
# =============================================================================

SEO_UPLOAD_RATE_LIMIT = "10/minute"


@router.post(
    "/assets", response_model=MarketingAsset, status_code=201, responses={429: RATE_LIMIT_RESPONSE}
)
@handle_api_errors("upload asset")
@limiter.limit(SEO_UPLOAD_RATE_LIMIT)
async def upload_asset(
    request: Request,
    user: dict = Depends(get_current_user),
) -> MarketingAsset:
    """Upload a marketing asset to the collateral bank.

    Accepts multipart form data with file and metadata.
    Validates file type (png, jpg, gif, webp, svg, mp4, webm) and size (max 10MB images, 50MB video).

    Rate limited to 10 uploads per minute.
    Tier limits: free=10 total, starter=50, pro=500, enterprise=unlimited.
    """
    from fastapi import UploadFile

    from backend.services import marketing_assets as asset_service

    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access (tier or promo)
    if not has_seo_access(user_id, tier):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan.",
            status=403,
        )

    # Check storage limit
    limit = PlanConfig.get_marketing_assets_limit(tier)
    current_count = asset_service.get_asset_count(user_id)

    if not PlanConfig.is_unlimited(limit) and current_count >= limit:
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            f"Asset storage limit reached ({limit}). Upgrade your plan for more storage.",
            status=429,
        )

    # Parse multipart form data
    form = await request.form()
    file: UploadFile | None = form.get("file")
    title = form.get("title", "")
    asset_type = form.get("asset_type", "image")
    description = form.get("description")
    tags_str = form.get("tags", "")

    if not file or not hasattr(file, "read"):
        raise http_error(ErrorCode.VALIDATION_ERROR, "File is required", status=400)

    if not title:
        raise http_error(ErrorCode.VALIDATION_ERROR, "Title is required", status=400)

    # Parse tags from comma-separated string
    tags = [t.strip() for t in str(tags_str).split(",") if t.strip()] if tags_str else []

    # Read file content
    file_data = await file.read()
    filename = file.filename or "unnamed"
    mime_type = file.content_type or "application/octet-stream"

    workspace_id = getattr(request.state, "workspace_id", None)

    try:
        record = asset_service.upload_asset(
            user_id=user_id,
            workspace_id=workspace_id,
            filename=filename,
            file_data=file_data,
            mime_type=mime_type,
            title=str(title),
            asset_type=str(asset_type),
            description=str(description) if description else None,
            tags=tags,
        )
    except asset_service.AssetValidationError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from e
    except asset_service.AssetStorageError as e:
        raise http_error(ErrorCode.EXT_SPACES_ERROR, str(e), status=500) from e

    return MarketingAsset(
        id=record.id,
        filename=record.filename,
        cdn_url=record.cdn_url,
        asset_type=record.asset_type,
        title=record.title,
        description=record.description,
        tags=record.tags,
        file_size=record.file_size,
        mime_type=record.mime_type,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/assets", response_model=MarketingAssetListResponse)
@handle_api_errors("list assets")
async def list_assets(
    request: Request,
    asset_type: str | None = Query(None, description="Filter by type"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    search: str | None = Query(None, description="Search in title/description"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user: dict = Depends(get_current_user),
) -> MarketingAssetListResponse:
    """List user's marketing assets with optional filtering.

    Supports filtering by asset type, tags, and text search.
    """
    from backend.services import marketing_assets as asset_service

    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    assets, total = asset_service.list_assets(
        user_id=user_id,
        asset_type=asset_type,
        tags=tag_list,
        search=search,
        limit=limit,
        offset=offset,
    )

    # Calculate remaining
    tier_limit = PlanConfig.get_marketing_assets_limit(tier)
    remaining = -1 if PlanConfig.is_unlimited(tier_limit) else (tier_limit - total)

    return MarketingAssetListResponse(
        assets=[
            MarketingAsset(
                id=a.id,
                filename=a.filename,
                cdn_url=a.cdn_url,
                asset_type=a.asset_type,
                title=a.title,
                description=a.description,
                tags=a.tags,
                file_size=a.file_size,
                mime_type=a.mime_type,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in assets
        ],
        total=total,
        remaining=remaining,
    )


@router.get("/assets/suggest", response_model=AssetSuggestionsResponse)
@handle_api_errors("suggest assets")
async def suggest_assets_for_article(
    request: Request,
    article_id: int = Query(..., description="Article ID to get suggestions for"),
    user: dict = Depends(get_current_user),
) -> AssetSuggestionsResponse:
    """Get suggested assets for an article based on keyword matching.

    Analyzes article title and content to find matching assets from the collateral bank.
    """
    from backend.services import marketing_assets as asset_service

    user_id = extract_user_id(user)

    # Get article to extract keywords
    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.title, a.content, t.keyword
                FROM seo_blog_articles a
                LEFT JOIN seo_topics t ON a.topic_id = t.id
                WHERE a.id = %s AND a.user_id = %s
                """,
                (article_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            title, content, topic_keyword = row

    # Extract keywords from title and topic
    keywords = []
    if topic_keyword:
        keywords.append(topic_keyword)
    if title:
        # Simple keyword extraction from title
        title_words = [w.lower() for w in title.split() if len(w) > 3]
        keywords.extend(title_words[:10])

    if not keywords:
        return AssetSuggestionsResponse(suggestions=[], article_keywords=[])

    # Get suggestions
    suggestions = asset_service.suggest_for_article(user_id, keywords, limit=5)

    return AssetSuggestionsResponse(
        suggestions=[
            AssetSuggestion(
                id=s.asset.id,
                title=s.asset.title,
                cdn_url=s.asset.cdn_url,
                asset_type=s.asset.asset_type,
                relevance_score=s.relevance_score,
                matching_tags=s.matching_tags,
            )
            for s in suggestions
        ],
        article_keywords=keywords,
    )


@router.get("/assets/{asset_id}", response_model=MarketingAsset)
@handle_api_errors("get asset")
async def get_asset(
    request: Request,
    asset_id: int,
    user: dict = Depends(get_current_user),
) -> MarketingAsset:
    """Get a single marketing asset by ID."""
    from backend.services import marketing_assets as asset_service

    user_id = extract_user_id(user)

    record = asset_service.get_asset(user_id, asset_id)
    if not record:
        raise http_error(ErrorCode.API_NOT_FOUND, "Asset not found", status=404)

    return MarketingAsset(
        id=record.id,
        filename=record.filename,
        cdn_url=record.cdn_url,
        asset_type=record.asset_type,
        title=record.title,
        description=record.description,
        tags=record.tags,
        file_size=record.file_size,
        mime_type=record.mime_type,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.patch("/assets/{asset_id}", response_model=MarketingAsset)
@handle_api_errors("update asset")
async def update_asset(
    request: Request,
    asset_id: int,
    body: MarketingAssetUpdate,
    user: dict = Depends(get_current_user),
) -> MarketingAsset:
    """Update marketing asset metadata.

    Can update title, description, and tags.
    """
    from backend.services import marketing_assets as asset_service

    user_id = extract_user_id(user)

    try:
        record = asset_service.update_asset(
            user_id=user_id,
            asset_id=asset_id,
            title=body.title,
            description=body.description,
            tags=body.tags,
        )
    except asset_service.AssetValidationError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), status=400) from e

    if not record:
        raise http_error(ErrorCode.API_NOT_FOUND, "Asset not found", status=404)

    return MarketingAsset(
        id=record.id,
        filename=record.filename,
        cdn_url=record.cdn_url,
        asset_type=record.asset_type,
        title=record.title,
        description=record.description,
        tags=record.tags,
        file_size=record.file_size,
        mime_type=record.mime_type,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.delete("/assets/{asset_id}", status_code=204, response_model=None)
@handle_api_errors("delete asset")
async def delete_asset(
    request: Request,
    asset_id: int,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete a marketing asset.

    Removes the asset from storage and database.
    """
    from backend.services import marketing_assets as asset_service

    user_id = extract_user_id(user)

    deleted = asset_service.delete_asset(user_id, asset_id)
    if not deleted:
        raise http_error(ErrorCode.API_NOT_FOUND, "Asset not found", status=404)
