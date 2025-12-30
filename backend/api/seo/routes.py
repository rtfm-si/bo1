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
from backend.api.utils.db_helpers import get_user_tier
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
                SELECT COUNT(*) FROM seo_trend_analyses
                WHERE user_id = %s
                AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else 0


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
            return row[0]


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

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
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
                "SELECT COUNT(*) FROM seo_trend_analyses WHERE user_id = %s",
                (user_id,),
            )
            total = cursor.fetchone()[0]

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
                results_json = row[3] or {}
                analyses.append(
                    HistoryEntry(
                        id=row[0],
                        keywords=row[1] or [],
                        industry=row[2],
                        executive_summary=results_json.get("executive_summary", ""),
                        created_at=row[4],
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
                "SELECT COUNT(*) FROM seo_topics WHERE user_id = %s",
                (user_id,),
            )
            total = cursor.fetchone()[0]

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
                        id=row[0],
                        keyword=row[1],
                        status=row[2],
                        source_analysis_id=row[3],
                        notes=row[4],
                        created_at=row[5],
                        updated_at=row[6],
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
                id=row[0],
                keyword=row[1],
                status=row[2],
                source_analysis_id=row[3],
                notes=row[4],
                created_at=row[5],
                updated_at=row[6],
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
                id=row[0],
                keyword=row[1],
                status=row[2],
                source_analysis_id=row[3],
                notes=row[4],
                created_at=row[5],
                updated_at=row[6],
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
                SELECT COUNT(*) FROM seo_blog_articles
                WHERE user_id = %s
                AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else 0


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

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
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

            keyword = topic_row[1]

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

            logger.info(f"Generated article id={article_row[0]} for topic {topic_id}")

            return SeoBlogArticle(
                id=article_row[0],
                topic_id=article_row[1],
                title=article_row[2],
                excerpt=article_row[3],
                content=article_row[4],
                meta_title=article_row[5],
                meta_description=article_row[6],
                status=article_row[7],
                created_at=article_row[8],
                updated_at=article_row[9],
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
                "SELECT COUNT(*) FROM seo_blog_articles WHERE user_id = %s",
                (user_id,),
            )
            total = cursor.fetchone()[0]

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
                        id=row[0],
                        topic_id=row[1],
                        title=row[2],
                        excerpt=row[3],
                        content=row[4],
                        meta_title=row[5],
                        meta_description=row[6],
                        status=row[7],
                        created_at=row[8],
                        updated_at=row[9],
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
                id=row[0],
                topic_id=row[1],
                title=row[2],
                excerpt=row[3],
                content=row[4],
                meta_title=row[5],
                meta_description=row[6],
                status=row[7],
                created_at=row[8],
                updated_at=row[9],
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

            topic_id = existing[1]
            old_status = existing[2]

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
                id=row[0],
                topic_id=row[1],
                title=row[2],
                excerpt=row[3],
                content=row[4],
                meta_title=row[5],
                meta_description=row[6],
                status=row[7],
                created_at=row[8],
                updated_at=row[9],
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


# =============================================================================
# SEO Autopilot Models
# =============================================================================


class SEOAutopilotConfig(BaseModel):
    """Configuration for SEO autopilot content scheduling.

    Stores user preferences for automated topic discovery and article generation.
    """

    enabled: bool = Field(default=False, description="Whether autopilot is enabled")
    frequency_per_week: int = Field(
        default=1,
        ge=1,
        le=7,
        description="Number of articles to generate per week (1-7)",
    )
    auto_publish: bool = Field(
        default=False,
        description="Automatically publish generated articles (vs review queue)",
    )
    require_approval: bool = Field(
        default=True,
        description="Require manual approval before publishing (default: True for new users)",
    )
    target_keywords: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Keywords to focus on for topic discovery",
    )
    purchase_intent_only: bool = Field(
        default=True,
        description="Only target high-intent keywords (transactional, comparison, etc.)",
    )


class SEOAutopilotConfigResponse(BaseModel):
    """Response for autopilot config retrieval."""

    config: SEOAutopilotConfig = Field(..., description="Current autopilot configuration")
    next_run: datetime | None = Field(None, description="Next scheduled autopilot run")
    articles_this_week: int = Field(0, ge=0, description="Articles generated this week")
    articles_pending_review: int = Field(0, ge=0, description="Articles awaiting approval")


class ArticleStatus(str):
    """Valid status values for SEO blog articles including autopilot statuses."""

    DRAFT = "draft"
    PUBLISHED = "published"
    PENDING_REVIEW = "pending_review"  # Awaiting approval (autopilot-generated)
    REJECTED = "rejected"  # User rejected the article


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
                counts[row[0]] = row[1]

            views = counts["view"]
            clicks = counts["click"]
            signups = counts["signup"]

            # Calculate rates (handle division by zero)
            ctr = clicks / views if views > 0 else 0.0
            signup_rate = signups / views if views > 0 else 0.0

            return ArticleAnalytics(
                article_id=article[0],
                title=article[1],
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
                views = row[2]
                clicks = row[3]
                signups = row[4]

                total_views += views
                total_clicks += clicks
                total_signups += signups

                ctr = clicks / views if views > 0 else 0.0
                signup_rate = signups / views if views > 0 else 0.0

                articles.append(
                    ArticleAnalytics(
                        article_id=row[0],
                        title=row[1],
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
# SEO Autopilot Endpoints
# =============================================================================


def _get_autopilot_stats(user_id: str) -> tuple[int, int]:
    """Get autopilot stats: articles generated this week and pending review count.

    Args:
        user_id: User ID

    Returns:
        Tuple of (articles_this_week, articles_pending_review)
    """
    with db_session() as conn:
        with conn.cursor() as cursor:
            # Articles generated this week (by autopilot - status pending_review or via autopilot source)
            cursor.execute(
                """
                SELECT COUNT(*) FROM seo_blog_articles
                WHERE user_id = %s
                AND created_at >= date_trunc('week', CURRENT_TIMESTAMP)
                """,
                (user_id,),
            )
            articles_this_week = cursor.fetchone()[0] or 0

            # Articles pending review
            cursor.execute(
                """
                SELECT COUNT(*) FROM seo_blog_articles
                WHERE user_id = %s
                AND status = 'pending_review'
                """,
                (user_id,),
            )
            articles_pending = cursor.fetchone()[0] or 0

            return articles_this_week, articles_pending


@router.get("/autopilot/config", response_model=SEOAutopilotConfigResponse)
@handle_api_errors("get autopilot config")
async def get_autopilot_config(
    request: Request,
    user: dict = Depends(get_current_user),
) -> SEOAutopilotConfigResponse:
    """Get current SEO autopilot configuration.

    Returns autopilot settings and status (next run, articles this week, pending).
    """
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan. Please upgrade.",
            status=403,
        )

    with db_session() as cursor:
        cursor.execute(
            """
            SELECT seo_autopilot_config FROM user_context
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()

    # Parse config or return defaults
    if row and row[0]:
        config = SEOAutopilotConfig(**row[0])
    else:
        config = SEOAutopilotConfig()

    # Get stats
    articles_this_week, articles_pending = _get_autopilot_stats(user_id)

    # Calculate next run (if enabled, next Monday at 9am UTC)
    next_run = None
    if config.enabled:
        from datetime import timedelta

        now = datetime.now(UTC)
        # Next Monday
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_monday = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=days_until_monday
        )
        next_run = next_monday

    return SEOAutopilotConfigResponse(
        config=config,
        next_run=next_run,
        articles_this_week=articles_this_week,
        articles_pending_review=articles_pending,
    )


@router.put("/autopilot/config", response_model=SEOAutopilotConfigResponse)
@handle_api_errors("update autopilot config")
async def update_autopilot_config(
    request: Request,
    body: SEOAutopilotConfig,
    user: dict = Depends(get_current_user),
) -> SEOAutopilotConfigResponse:
    """Update SEO autopilot configuration.

    Configure automated topic discovery and article generation settings.
    """
    user_id = extract_user_id(user)
    tier = get_user_tier(user_id)

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "SEO tools are not available on your plan. Please upgrade.",
            status=403,
        )

    # Check tier limits - autopilot is only available if user has article quota
    autopilot_limit = PlanConfig.get_seo_articles_limit(tier)
    if not PlanConfig.is_unlimited(autopilot_limit) and autopilot_limit <= 0:
        raise http_error(
            ErrorCode.API_FORBIDDEN,
            "Autopilot requires SEO article generation quota. Upgrade your plan.",
            status=403,
        )

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Check if user_context exists
            cursor.execute(
                "SELECT 1 FROM user_context WHERE user_id = %s",
                (user_id,),
            )
            exists = cursor.fetchone()

            if exists:
                cursor.execute(
                    """
                    UPDATE user_context
                    SET seo_autopilot_config = %s, updated_at = now()
                    WHERE user_id = %s
                    """,
                    (Json(body.model_dump()), user_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_context (user_id, seo_autopilot_config)
                    VALUES (%s, %s)
                    """,
                    (user_id, Json(body.model_dump())),
                )
            conn.commit()

    logger.info(f"Updated autopilot config for user {user_id[:8]}...: enabled={body.enabled}")

    # Get stats
    articles_this_week, articles_pending = _get_autopilot_stats(user_id)

    # Calculate next run
    next_run = None
    if body.enabled:
        from datetime import timedelta

        now = datetime.now(UTC)
        days_until_monday = (7 - now.weekday()) % 7 or 7
        next_monday = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=days_until_monday
        )
        next_run = next_monday

    return SEOAutopilotConfigResponse(
        config=body,
        next_run=next_run,
        articles_this_week=articles_this_week,
        articles_pending_review=articles_pending,
    )


# =============================================================================
# Pending Articles Queue Endpoints
# =============================================================================


class PendingArticle(BaseModel):
    """An article pending review from autopilot."""

    id: int = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    excerpt: str | None = Field(None, description="Article excerpt")
    keyword: str | None = Field(None, description="Source keyword/topic")
    created_at: datetime = Field(..., description="When article was generated")


class PendingArticlesResponse(BaseModel):
    """Response containing articles pending review."""

    articles: list[PendingArticle] = Field(
        default_factory=list, description="Articles pending review"
    )
    count: int = Field(0, ge=0, description="Number of pending articles")


@router.get("/autopilot/pending", response_model=PendingArticlesResponse)
@handle_api_errors("get pending articles")
async def get_pending_articles(
    request: Request,
    user: dict = Depends(get_current_user),
) -> PendingArticlesResponse:
    """Get articles pending review from autopilot.

    Returns all articles with status 'pending_review'.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.id, a.title, a.excerpt, t.keyword, a.created_at
                FROM seo_blog_articles a
                LEFT JOIN seo_topics t ON a.topic_id = t.id
                WHERE a.user_id = %s AND a.status = 'pending_review'
                ORDER BY a.created_at DESC
                """,
                (user_id,),
            )

            articles = []
            for row in cursor.fetchall():
                articles.append(
                    PendingArticle(
                        id=row[0],
                        title=row[1],
                        excerpt=row[2],
                        keyword=row[3],
                        created_at=row[4],
                    )
                )

    return PendingArticlesResponse(articles=articles, count=len(articles))


@router.post("/autopilot/articles/{article_id}/approve", response_model=SeoBlogArticle)
@handle_api_errors("approve article")
async def approve_article(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> SeoBlogArticle:
    """Approve a pending article for publishing.

    Changes status from 'pending_review' to 'published'.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Check article exists and is pending
            cursor.execute(
                """
                SELECT id, status, topic_id FROM seo_blog_articles
                WHERE id = %s AND user_id = %s
                """,
                (article_id, user_id),
            )
            row = cursor.fetchone()

            if not row:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            if row[1] != "pending_review":
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    f"Article is not pending review (status: {row[1]})",
                    status=400,
                )

            topic_id = row[2]

            # Update to published
            cursor.execute(
                """
                UPDATE seo_blog_articles
                SET status = 'published', updated_at = now()
                WHERE id = %s AND user_id = %s
                RETURNING id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                """,
                (article_id, user_id),
            )
            article_row = cursor.fetchone()

            # Update topic status if linked
            if topic_id:
                cursor.execute(
                    """
                    UPDATE seo_topics SET status = 'published', updated_at = now()
                    WHERE id = %s AND user_id = %s
                    """,
                    (topic_id, user_id),
                )

            conn.commit()

            logger.info(f"Approved article {article_id} for user {user_id[:8]}...")

            return SeoBlogArticle(
                id=article_row[0],
                topic_id=article_row[1],
                title=article_row[2],
                excerpt=article_row[3],
                content=article_row[4],
                meta_title=article_row[5],
                meta_description=article_row[6],
                status=article_row[7],
                created_at=article_row[8],
                updated_at=article_row[9],
            )


@router.post("/autopilot/articles/{article_id}/reject", status_code=204, response_model=None)
@handle_api_errors("reject article")
async def reject_article(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> None:
    """Reject a pending article.

    Changes status from 'pending_review' to 'rejected'.
    """
    user_id = extract_user_id(user)

    with db_session() as conn:
        with conn.cursor() as cursor:
            # Check article exists and is pending
            cursor.execute(
                """
                SELECT id, status FROM seo_blog_articles
                WHERE id = %s AND user_id = %s
                """,
                (article_id, user_id),
            )
            row = cursor.fetchone()

            if not row:
                raise http_error(ErrorCode.API_NOT_FOUND, "Article not found", status=404)

            if row[1] != "pending_review":
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    f"Article is not pending review (status: {row[1]})",
                    status=400,
                )

            # Update to rejected
            cursor.execute(
                """
                UPDATE seo_blog_articles
                SET status = 'rejected', updated_at = now()
                WHERE id = %s AND user_id = %s
                """,
                (article_id, user_id),
            )
            conn.commit()

    logger.info(f"Rejected article {article_id} for user {user_id[:8]}...")


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

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
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
