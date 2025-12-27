"""SEO Trend Analyzer API endpoints.

Provides:
- POST /api/v1/seo/analyze-trends - Analyze SEO trends for keywords/industry
- GET /api/v1/seo/history - User's past trend analyses
"""

import logging
from datetime import UTC, datetime
from typing import Any  # noqa: F401

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import (
    SEO_ANALYZE_RATE_LIMIT,
    SEO_GENERATE_RATE_LIMIT,
    limiter,
)
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.db_helpers import get_user_tier
from backend.api.utils.errors import handle_api_errors
from bo1.agents.researcher import ResearcherAgent
from bo1.billing import PlanConfig
from bo1.logging.errors import ErrorCode  # noqa: F401
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/seo", tags=["seo"])


# =============================================================================
# Models
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
    from sqlalchemy import text

    with db_session() as session:
        result = session.execute(
            text("""
                SELECT COUNT(*) FROM seo_trend_analyses
                WHERE user_id = :user_id
                AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
            """),
            {"user_id": user_id},
        )
        row = result.fetchone()
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
    from sqlalchemy import text

    with db_session() as session:
        result = session.execute(
            text("""
                INSERT INTO seo_trend_analyses
                (user_id, workspace_id, keywords, industry, results_json)
                VALUES (:user_id, :workspace_id, :keywords, :industry, :results_json)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "keywords": keywords,
                "industry": industry,
                "results_json": results,
            },
        )
        row = result.fetchone()
        session.commit()
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


@router.post("/analyze-trends", response_model=TrendAnalysisResponse)
@handle_api_errors
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
    tier = await get_user_tier(user_id)

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
        raise HTTPException(
            status_code=403,
            detail="SEO tools are not available on your plan. Please upgrade to access this feature.",
        )

    # Check monthly limit
    limit = PlanConfig.get_seo_analyses_limit(tier)
    usage = _get_monthly_usage(user_id)

    if not PlanConfig.is_unlimited(limit) and usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly SEO analysis limit reached ({limit}). Upgrade your plan for more analyses.",
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
@handle_api_errors
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
    tier = await get_user_tier(user_id)

    from sqlalchemy import text

    with db_session() as session:
        # Get total count
        count_result = session.execute(
            text("SELECT COUNT(*) FROM seo_trend_analyses WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        total = count_result.fetchone()[0]

        # Get paginated results
        result = session.execute(
            text("""
                SELECT id, keywords, industry, results_json, created_at
                FROM seo_trend_analyses
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": user_id, "limit": limit, "offset": offset},
        )

        analyses = []
        for row in result.fetchall():
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
@handle_api_errors
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

    from sqlalchemy import text

    with db_session() as session:
        # Get total count
        count_result = session.execute(
            text("SELECT COUNT(*) FROM seo_topics WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        total = count_result.fetchone()[0]

        # Get paginated results
        result = session.execute(
            text("""
                SELECT id, keyword, status, source_analysis_id, notes, created_at, updated_at
                FROM seo_topics
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": user_id, "limit": limit, "offset": offset},
        )

        topics = []
        for row in result.fetchall():
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
@handle_api_errors
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

    from sqlalchemy import text

    with db_session() as session:
        # If source_analysis_id provided, verify it belongs to user
        if body.source_analysis_id:
            verify_result = session.execute(
                text("""
                    SELECT id FROM seo_trend_analyses
                    WHERE id = :id AND user_id = :user_id
                """),
                {"id": body.source_analysis_id, "user_id": user_id},
            )
            if not verify_result.fetchone():
                raise HTTPException(status_code=404, detail="Source analysis not found")

        result = session.execute(
            text("""
                INSERT INTO seo_topics
                (user_id, workspace_id, keyword, status, source_analysis_id, notes)
                VALUES (:user_id, :workspace_id, :keyword, 'researched', :source_analysis_id, :notes)
                RETURNING id, keyword, status, source_analysis_id, notes, created_at, updated_at
            """),
            {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "keyword": body.keyword.strip(),
                "source_analysis_id": body.source_analysis_id,
                "notes": body.notes,
            },
        )
        row = result.fetchone()
        session.commit()

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
@handle_api_errors
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
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    from sqlalchemy import text

    with db_session() as session:
        # Check topic exists and belongs to user
        check_result = session.execute(
            text("""
                SELECT id FROM seo_topics WHERE id = :id AND user_id = :user_id
            """),
            {"id": topic_id, "user_id": user_id},
        )
        if not check_result.fetchone():
            raise HTTPException(status_code=404, detail="Topic not found")

        # Build dynamic update query
        updates = ["updated_at = now()"]
        params: dict = {"id": topic_id, "user_id": user_id}

        if body.status:
            updates.append("status = :status")
            params["status"] = body.status

        if body.notes is not None:
            updates.append("notes = :notes")
            params["notes"] = body.notes

        result = session.execute(
            text(f"""
                UPDATE seo_topics
                SET {", ".join(updates)}
                WHERE id = :id AND user_id = :user_id
                RETURNING id, keyword, status, source_analysis_id, notes, created_at, updated_at
            """),
            params,
        )
        row = result.fetchone()
        session.commit()

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
@handle_api_errors
async def delete_topic(
    request: Request,
    topic_id: int,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete an SEO topic.

    Permanently removes the topic.
    """
    user_id = extract_user_id(user)

    from sqlalchemy import text

    with db_session() as session:
        result = session.execute(
            text("""
                DELETE FROM seo_topics WHERE id = :id AND user_id = :user_id
                RETURNING id
            """),
            {"id": topic_id, "user_id": user_id},
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Topic not found")
        session.commit()


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
    from sqlalchemy import text

    with db_session() as session:
        result = session.execute(
            text("""
                SELECT COUNT(*) FROM seo_blog_articles
                WHERE user_id = :user_id
                AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)
            """),
            {"user_id": user_id},
        )
        row = result.fetchone()
        return row[0] if row else 0


# =============================================================================
# SEO Blog Article Endpoints
# =============================================================================


@router.post("/topics/{topic_id}/generate", response_model=SeoBlogArticle, status_code=201)
@handle_api_errors
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
    from sqlalchemy import text

    from backend.services.content_generator import generate_blog_post

    user_id = extract_user_id(user)
    tier = await get_user_tier(user_id)

    # Check feature access
    if not PlanConfig.is_feature_enabled(tier, "seo_tools"):
        raise HTTPException(
            status_code=403,
            detail="SEO tools are not available on your plan. Please upgrade to access this feature.",
        )

    # Check monthly limit
    limit = PlanConfig.get_seo_articles_limit(tier)
    usage = _get_monthly_article_usage(user_id)

    if not PlanConfig.is_unlimited(limit) and usage >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly SEO article limit reached ({limit}). Upgrade your plan for more generations.",
        )

    # Get topic and verify ownership
    with db_session() as session:
        topic_result = session.execute(
            text("""
                SELECT id, keyword, status FROM seo_topics
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": topic_id, "user_id": user_id},
        )
        topic_row = topic_result.fetchone()
        if not topic_row:
            raise HTTPException(status_code=404, detail="Topic not found")

        keyword = topic_row[1]

    # Generate blog content
    logger.info(f"Generating SEO article for user {user_id[:8]}... keyword={keyword}")

    try:
        blog_content = await generate_blog_post(keyword, [keyword])
    except ValueError as e:
        logger.error(f"Blog generation failed for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Article generation failed: {e}") from e

    # Get workspace ID if in workspace context
    workspace_id = getattr(request.state, "workspace_id", None)

    # Save article and update topic status
    with db_session() as session:
        # Insert article
        article_result = session.execute(
            text("""
                INSERT INTO seo_blog_articles
                (user_id, workspace_id, topic_id, title, excerpt, content, meta_title, meta_description, status)
                VALUES (:user_id, :workspace_id, :topic_id, :title, :excerpt, :content, :meta_title, :meta_description, 'draft')
                RETURNING id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
            """),
            {
                "user_id": user_id,
                "workspace_id": workspace_id,
                "topic_id": topic_id,
                "title": blog_content.title,
                "excerpt": blog_content.excerpt,
                "content": blog_content.content,
                "meta_title": blog_content.meta_title,
                "meta_description": blog_content.meta_description,
            },
        )
        article_row = article_result.fetchone()

        # Update topic status to 'writing'
        session.execute(
            text("""
                UPDATE seo_topics SET status = 'writing', updated_at = now()
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": topic_id, "user_id": user_id},
        )
        session.commit()

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
@handle_api_errors
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
    tier = await get_user_tier(user_id)

    from sqlalchemy import text

    with db_session() as session:
        # Get total count
        count_result = session.execute(
            text("SELECT COUNT(*) FROM seo_blog_articles WHERE user_id = :user_id"),
            {"user_id": user_id},
        )
        total = count_result.fetchone()[0]

        # Get paginated results
        result = session.execute(
            text("""
                SELECT id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                FROM seo_blog_articles
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": user_id, "limit": limit, "offset": offset},
        )

        articles = []
        for row in result.fetchall():
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
@handle_api_errors
async def get_article(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> SeoBlogArticle:
    """Get a single article by ID."""
    user_id = extract_user_id(user)

    from sqlalchemy import text

    with db_session() as session:
        result = session.execute(
            text("""
                SELECT id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
                FROM seo_blog_articles
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": article_id, "user_id": user_id},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")

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
@handle_api_errors
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
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    from sqlalchemy import text

    with db_session() as session:
        # Check article exists and belongs to user
        check_result = session.execute(
            text("""
                SELECT id, topic_id, status FROM seo_blog_articles WHERE id = :id AND user_id = :user_id
            """),
            {"id": article_id, "user_id": user_id},
        )
        existing = check_result.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Article not found")

        topic_id = existing[1]
        old_status = existing[2]

        # Build dynamic update query
        updates = ["updated_at = now()"]
        params: dict = {"id": article_id, "user_id": user_id}

        if body.title is not None:
            updates.append("title = :title")
            params["title"] = body.title

        if body.excerpt is not None:
            updates.append("excerpt = :excerpt")
            params["excerpt"] = body.excerpt

        if body.content is not None:
            updates.append("content = :content")
            params["content"] = body.content

        if body.meta_title is not None:
            updates.append("meta_title = :meta_title")
            params["meta_title"] = body.meta_title

        if body.meta_description is not None:
            updates.append("meta_description = :meta_description")
            params["meta_description"] = body.meta_description

        if body.status is not None:
            updates.append("status = :status")
            params["status"] = body.status

        result = session.execute(
            text(f"""
                UPDATE seo_blog_articles
                SET {", ".join(updates)}
                WHERE id = :id AND user_id = :user_id
                RETURNING id, topic_id, title, excerpt, content, meta_title, meta_description, status, created_at, updated_at
            """),
            params,
        )
        row = result.fetchone()

        # If status changed to published, update topic status too
        if body.status == "published" and old_status != "published" and topic_id:
            session.execute(
                text("""
                    UPDATE seo_topics SET status = 'published', updated_at = now()
                    WHERE id = :id AND user_id = :user_id
                """),
                {"id": topic_id, "user_id": user_id},
            )

        session.commit()

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
@handle_api_errors
async def delete_article(
    request: Request,
    article_id: int,
    user: dict = Depends(get_current_user),
) -> None:
    """Delete an SEO article.

    Permanently removes the article. Topic status remains unchanged.
    """
    user_id = extract_user_id(user)

    from sqlalchemy import text

    with db_session() as session:
        result = session.execute(
            text("""
                DELETE FROM seo_blog_articles WHERE id = :id AND user_id = :user_id
                RETURNING id
            """),
            {"id": article_id, "user_id": user_id},
        )
        if not result.fetchone():
            raise HTTPException(status_code=404, detail="Article not found")
        session.commit()


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


@router.post("/articles/{article_id}/events", status_code=201, response_model=None)
@handle_api_errors
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
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_event_types)}",
        )

    from sqlalchemy import text

    # Get user agent from request
    user_agent = request.headers.get("user-agent", "")[:500]

    with db_session() as session:
        # Verify article exists (public, so no user_id check)
        article_check = session.execute(
            text("SELECT id FROM seo_blog_articles WHERE id = :id"),
            {"id": article_id},
        )
        if not article_check.fetchone():
            raise HTTPException(status_code=404, detail="Article not found")

        # Insert event
        session.execute(
            text("""
                INSERT INTO seo_article_events
                (article_id, event_type, referrer, utm_source, utm_medium, utm_campaign, session_id, user_agent)
                VALUES (:article_id, :event_type, :referrer, :utm_source, :utm_medium, :utm_campaign, :session_id, :user_agent)
            """),
            {
                "article_id": article_id,
                "event_type": body.event_type,
                "referrer": body.referrer,
                "utm_source": body.utm_source,
                "utm_medium": body.utm_medium,
                "utm_campaign": body.utm_campaign,
                "session_id": body.session_id,
                "user_agent": user_agent,
            },
        )
        session.commit()

    logger.debug(f"Recorded {body.event_type} event for article {article_id}")


@router.get("/articles/{article_id}/analytics", response_model=ArticleAnalytics)
@handle_api_errors
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

    from sqlalchemy import text

    with db_session() as session:
        # Verify article exists and belongs to user
        article_result = session.execute(
            text("""
                SELECT id, title FROM seo_blog_articles
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": article_id, "user_id": user_id},
        )
        article = article_result.fetchone()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Get event counts
        analytics_result = session.execute(
            text("""
                SELECT
                    event_type,
                    COUNT(*) as count
                FROM seo_article_events
                WHERE article_id = :article_id
                GROUP BY event_type
            """),
            {"article_id": article_id},
        )

        counts = {"view": 0, "click": 0, "signup": 0}
        for row in analytics_result.fetchall():
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
@handle_api_errors
async def get_all_analytics(
    request: Request,
    user: dict = Depends(get_current_user),
) -> ArticleAnalyticsListResponse:
    """Get aggregated analytics for all user's articles.

    Returns per-article analytics plus overall totals.
    """
    user_id = extract_user_id(user)

    from sqlalchemy import text

    with db_session() as session:
        # Get all user's articles with their event counts
        result = session.execute(
            text("""
                SELECT
                    a.id,
                    a.title,
                    COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) as views,
                    COALESCE(SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END), 0) as clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0) as signups
                FROM seo_blog_articles a
                LEFT JOIN seo_article_events e ON e.article_id = a.id
                WHERE a.user_id = :user_id
                GROUP BY a.id, a.title
                ORDER BY views DESC
            """),
            {"user_id": user_id},
        )

        articles = []
        total_views = 0
        total_clicks = 0
        total_signups = 0

        for row in result.fetchall():
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
