"""Admin SEO content analytics endpoints.

Provides global SEO content performance metrics for the admin dashboard:
- Total views, clicks, signups across all articles
- Top-performing articles by views and conversion rate
- CTR and signup rate trends
"""

import logging

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seo", tags=["admin-seo"])


# =============================================================================
# Response Models
# =============================================================================


class TopArticle(BaseModel):
    """Top-performing article info."""

    article_id: int = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    user_email: str | None = Field(None, description="Author email")
    views: int = Field(0, description="Total views")
    clicks: int = Field(0, description="Total clicks")
    signups: int = Field(0, description="Total signups")
    ctr: float = Field(0.0, description="Click-through rate")
    signup_rate: float = Field(0.0, description="Signup conversion rate")


class SeoAnalyticsSummary(BaseModel):
    """Global SEO analytics summary."""

    total_articles: int = Field(0, description="Total articles across all users")
    total_views: int = Field(0, description="Total article views")
    total_clicks: int = Field(0, description="Total clicks")
    total_signups: int = Field(0, description="Total signups")
    overall_ctr: float = Field(0.0, description="Overall click-through rate")
    overall_signup_rate: float = Field(0.0, description="Overall signup conversion rate")
    views_today: int = Field(0, description="Views in last 24 hours")
    views_this_week: int = Field(0, description="Views in last 7 days")
    views_this_month: int = Field(0, description="Views in last 30 days")


class AdminSeoAnalyticsResponse(BaseModel):
    """Full admin SEO analytics response."""

    summary: SeoAnalyticsSummary = Field(..., description="Overall summary stats")
    top_by_views: list[TopArticle] = Field(
        default_factory=list, description="Top articles by view count"
    )
    top_by_conversion: list[TopArticle] = Field(
        default_factory=list, description="Top articles by signup conversion rate"
    )


class BlogPostPerformance(BaseModel):
    """Blog post with CTR and cost metrics."""

    id: str = Field(..., description="Post UUID")
    title: str = Field(..., description="Post title")
    slug: str = Field(..., description="URL slug")
    view_count: int = Field(0, description="Total views")
    click_through_count: int = Field(0, description="Total CTA clicks")
    ctr_percent: float = Field(0.0, description="Click-through rate percentage")
    generation_cost: float = Field(0.0, description="LLM generation cost in GBP")
    cost_per_view: float = Field(0.0, description="Cost per view in GBP")
    cost_per_click: float = Field(0.0, description="Cost per click in GBP")
    published_at: str | None = Field(None, description="Publication date")
    last_viewed_at: str | None = Field(None, description="Last view timestamp")


class BlogPerformanceResponse(BaseModel):
    """Blog post performance analytics response."""

    posts: list[BlogPostPerformance] = Field(
        default_factory=list, description="Blog posts with performance metrics"
    )
    total_views: int = Field(0, description="Total views across all posts")
    total_clicks: int = Field(0, description="Total clicks across all posts")
    total_cost: float = Field(0.0, description="Total generation cost in GBP")
    overall_ctr: float = Field(0.0, description="Overall CTR percentage")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/analytics", response_model=AdminSeoAnalyticsResponse)
@handle_api_errors("get admin seo analytics")
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_admin_seo_analytics(
    request: Request,
    top_limit: int = Query(10, ge=1, le=50, description="Number of top articles to return"),
    _admin: dict = Depends(require_admin_any),
) -> AdminSeoAnalyticsResponse:
    """Get global SEO content performance analytics.

    Returns:
    - Overall summary: total views, clicks, signups, CTR, signup rate
    - Time-based metrics: views today, this week, this month
    - Top articles by views
    - Top articles by signup conversion rate (min 10 views)
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get overall summary
            cur.execute("""
                SELECT
                    COUNT(DISTINCT a.id) as total_articles,
                    COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) as total_views,
                    COALESCE(SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END), 0) as total_clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0) as total_signups
                FROM seo_blog_articles a
                LEFT JOIN seo_article_events e ON e.article_id = a.id
            """)
            summary_row = cur.fetchone()

            total_articles = summary_row["total_articles"] or 0
            total_views = summary_row["total_views"] or 0
            total_clicks = summary_row["total_clicks"] or 0
            total_signups = summary_row["total_signups"] or 0

            overall_ctr = total_clicks / total_views if total_views > 0 else 0.0
            overall_signup_rate = total_signups / total_views if total_views > 0 else 0.0

            # Get time-based view counts
            cur.execute("""
                SELECT
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 ELSE 0 END), 0) as today,
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END), 0) as this_week,
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 ELSE 0 END), 0) as this_month
                FROM seo_article_events
                WHERE event_type = 'view'
            """)
            time_row = cur.fetchone()

            views_today = time_row["today"] or 0
            views_this_week = time_row["this_week"] or 0
            views_this_month = time_row["this_month"] or 0

            # Get top articles by views
            cur.execute(
                """
                SELECT
                    a.id,
                    a.title,
                    u.email,
                    COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) as views,
                    COALESCE(SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END), 0) as clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0) as signups
                FROM seo_blog_articles a
                LEFT JOIN seo_article_events e ON e.article_id = a.id
                LEFT JOIN users u ON u.id = a.user_id
                GROUP BY a.id, a.title, u.email
                ORDER BY views DESC
                LIMIT %s
            """,
                (top_limit,),
            )

            top_by_views = []
            for row in cur.fetchall():
                views = row["views"]
                clicks = row["clicks"]
                signups = row["signups"]
                ctr = clicks / views if views > 0 else 0.0
                signup_rate = signups / views if views > 0 else 0.0

                top_by_views.append(
                    TopArticle(
                        article_id=row["id"],
                        title=row["title"],
                        user_email=row["email"],
                        views=views,
                        clicks=clicks,
                        signups=signups,
                        ctr=round(ctr, 4),
                        signup_rate=round(signup_rate, 4),
                    )
                )

            # Get top articles by conversion rate (min 10 views for statistical significance)
            cur.execute(
                """
                SELECT
                    a.id,
                    a.title,
                    u.email,
                    COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) as views,
                    COALESCE(SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END), 0) as clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0) as signups
                FROM seo_blog_articles a
                LEFT JOIN seo_article_events e ON e.article_id = a.id
                LEFT JOIN users u ON u.id = a.user_id
                GROUP BY a.id, a.title, u.email
                HAVING COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) >= 10
                ORDER BY (
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0)::float /
                    NULLIF(COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0), 0)
                ) DESC NULLS LAST
                LIMIT %s
            """,
                (top_limit,),
            )

            top_by_conversion = []
            for row in cur.fetchall():
                views = row["views"]
                clicks = row["clicks"]
                signups = row["signups"]
                ctr = clicks / views if views > 0 else 0.0
                signup_rate = signups / views if views > 0 else 0.0

                top_by_conversion.append(
                    TopArticle(
                        article_id=row["id"],
                        title=row["title"],
                        user_email=row["email"],
                        views=views,
                        clicks=clicks,
                        signups=signups,
                        ctr=round(ctr, 4),
                        signup_rate=round(signup_rate, 4),
                    )
                )

            return AdminSeoAnalyticsResponse(
                summary=SeoAnalyticsSummary(
                    total_articles=total_articles,
                    total_views=total_views,
                    total_clicks=total_clicks,
                    total_signups=total_signups,
                    overall_ctr=round(overall_ctr, 4),
                    overall_signup_rate=round(overall_signup_rate, 4),
                    views_today=views_today,
                    views_this_week=views_this_week,
                    views_this_month=views_this_month,
                ),
                top_by_views=top_by_views,
                top_by_conversion=top_by_conversion,
            )


@router.get("/performance", response_model=BlogPerformanceResponse)
@handle_api_errors("get blog post performance")
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_blog_performance(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Max posts to return"),
    sort_by: str = Query("views", description="Sort by: views, ctr, cost_per_click, roi"),
    _admin: dict = Depends(require_admin_any),
) -> BlogPerformanceResponse:
    """Get blog post performance metrics with generation costs.

    Returns published blog posts with:
    - View and click counts
    - CTR percentage
    - Generation cost (from api_costs with cost_category='internal_seo')
    - Cost per view and cost per click (ROI metrics)

    Sorted by the specified metric (default: views descending).
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Determine sort column
            sort_map = {
                "views": "bp.view_count DESC",
                "ctr": "ctr_percent DESC",
                "cost_per_click": "cost_per_click ASC NULLS LAST",
                "roi": "cost_per_click ASC NULLS LAST",  # Lower cost per click = better ROI
            }
            sort_clause = sort_map.get(sort_by, "bp.view_count DESC")

            # Get posts with CTR metrics and generation costs
            cur.execute(
                f"""
                SELECT
                    bp.id::text,
                    bp.title,
                    bp.slug,
                    bp.view_count,
                    bp.click_through_count,
                    bp.published_at,
                    bp.last_viewed_at,
                    CASE WHEN bp.view_count > 0
                         THEN ROUND(bp.click_through_count::numeric / bp.view_count * 100, 2)
                         ELSE 0
                    END as ctr_percent,
                    COALESCE(costs.total_cost, 0) as generation_cost,
                    CASE WHEN bp.view_count > 0
                         THEN ROUND(COALESCE(costs.total_cost, 0) / bp.view_count, 4)
                         ELSE NULL
                    END as cost_per_view,
                    CASE WHEN bp.click_through_count > 0
                         THEN ROUND(COALESCE(costs.total_cost, 0) / bp.click_through_count, 4)
                         ELSE NULL
                    END as cost_per_click
                FROM blog_posts bp
                LEFT JOIN (
                    SELECT
                        metadata->>'blog_slug' as slug,
                        SUM(cost_usd * 0.79) as total_cost  -- Convert to GBP
                    FROM api_costs
                    WHERE cost_category = 'internal_seo'
                      AND metadata->>'blog_slug' IS NOT NULL
                    GROUP BY metadata->>'blog_slug'
                ) costs ON costs.slug = bp.slug
                WHERE bp.status = 'published'
                ORDER BY {sort_clause}
                LIMIT %s
                """,
                (limit,),
            )

            posts = []
            total_views = 0
            total_clicks = 0
            total_cost = 0.0

            for row in cur.fetchall():
                total_views += row["view_count"]
                total_clicks += row["click_through_count"]
                total_cost += float(row["generation_cost"])

                posts.append(
                    BlogPostPerformance(
                        id=row["id"],
                        title=row["title"],
                        slug=row["slug"],
                        view_count=row["view_count"],
                        click_through_count=row["click_through_count"],
                        ctr_percent=float(row["ctr_percent"]),
                        generation_cost=round(float(row["generation_cost"]), 4),
                        cost_per_view=float(row["cost_per_view"]) if row["cost_per_view"] else 0.0,
                        cost_per_click=float(row["cost_per_click"])
                        if row["cost_per_click"]
                        else 0.0,
                        published_at=row["published_at"].isoformat()
                        if row["published_at"]
                        else None,
                        last_viewed_at=row["last_viewed_at"].isoformat()
                        if row["last_viewed_at"]
                        else None,
                    )
                )

            overall_ctr = round(total_clicks / total_views * 100, 2) if total_views > 0 else 0.0

            return BlogPerformanceResponse(
                posts=posts,
                total_views=total_views,
                total_clicks=total_clicks,
                total_cost=round(total_cost, 2),
                overall_ctr=overall_ctr,
            )
