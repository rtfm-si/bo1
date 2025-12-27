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
    from sqlalchemy import text

    with db_session() as session:
        # Get overall summary
        summary_result = session.execute(
            text("""
                SELECT
                    COUNT(DISTINCT a.id) as total_articles,
                    COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) as total_views,
                    COALESCE(SUM(CASE WHEN e.event_type = 'click' THEN 1 ELSE 0 END), 0) as total_clicks,
                    COALESCE(SUM(CASE WHEN e.event_type = 'signup' THEN 1 ELSE 0 END), 0) as total_signups
                FROM seo_blog_articles a
                LEFT JOIN seo_article_events e ON e.article_id = a.id
            """)
        )
        summary_row = summary_result.fetchone()

        total_articles = summary_row[0] or 0
        total_views = summary_row[1] or 0
        total_clicks = summary_row[2] or 0
        total_signups = summary_row[3] or 0

        overall_ctr = total_clicks / total_views if total_views > 0 else 0.0
        overall_signup_rate = total_signups / total_views if total_views > 0 else 0.0

        # Get time-based view counts
        time_result = session.execute(
            text("""
                SELECT
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 ELSE 0 END), 0) as today,
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 ELSE 0 END), 0) as this_week,
                    COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 ELSE 0 END), 0) as this_month
                FROM seo_article_events
                WHERE event_type = 'view'
            """)
        )
        time_row = time_result.fetchone()

        views_today = time_row[0] or 0
        views_this_week = time_row[1] or 0
        views_this_month = time_row[2] or 0

        # Get top articles by views
        top_views_result = session.execute(
            text("""
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
                LIMIT :limit
            """),
            {"limit": top_limit},
        )

        top_by_views = []
        for row in top_views_result.fetchall():
            views = row[3]
            clicks = row[4]
            signups = row[5]
            ctr = clicks / views if views > 0 else 0.0
            signup_rate = signups / views if views > 0 else 0.0

            top_by_views.append(
                TopArticle(
                    article_id=row[0],
                    title=row[1],
                    user_email=row[2],
                    views=views,
                    clicks=clicks,
                    signups=signups,
                    ctr=round(ctr, 4),
                    signup_rate=round(signup_rate, 4),
                )
            )

        # Get top articles by conversion rate (min 10 views for statistical significance)
        top_conversion_result = session.execute(
            text("""
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
                LIMIT :limit
            """),
            {"limit": top_limit},
        )

        top_by_conversion = []
        for row in top_conversion_result.fetchall():
            views = row[3]
            clicks = row[4]
            signups = row[5]
            ctr = clicks / views if views > 0 else 0.0
            signup_rate = signups / views if views > 0 else 0.0

            top_by_conversion.append(
                TopArticle(
                    article_id=row[0],
                    title=row[1],
                    user_email=row[2],
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
