"""Admin API module - combines all domain-specific admin routers.

This module provides a unified router for all admin endpoints, organized by domain:
- Users: User management and statistics
- Sessions: Active session monitoring and control
- Research Cache: Cache statistics and maintenance
- Beta Whitelist: Beta access control
- Waitlist: Waitlist management and approvals
- Metrics: System metrics and monitoring

Rate Limiting:
    Admin endpoints use higher rate limits (300/minute) to support dashboard
    page loads that fire multiple API requests in parallel. This is safe because
    admin endpoints require API key authentication.

Usage:
    from backend.api import admin
    app.include_router(admin.router, prefix="/api", tags=["admin"])
"""

from fastapi import APIRouter

from backend.api.admin import (
    alerts,
    beta_whitelist,
    billing,
    blog,
    cost_analytics,
    costs,
    dashboard,
    decisions,
    drilldown,
    email,
    email_stats,
    embeddings,
    experiments,
    extended_kpis,
    feature_flags,
    feedback,
    impersonation,
    metrics,
    observability,
    ops,
    partitions,
    promotions,
    queries,
    research_cache,
    runtime_config,
    seo_analytics,
    session_control,
    templates,
    terms,
    user_metrics,
    users,
    waitlist,
)

# Create the main admin router with /admin prefix
router = APIRouter(prefix="/admin", tags=["admin"])

# Include all domain-specific sub-routers
router.include_router(users.router)
router.include_router(session_control.router)
router.include_router(research_cache.router)
router.include_router(beta_whitelist.router)
router.include_router(waitlist.router)
router.include_router(metrics.router)
router.include_router(user_metrics.router)
router.include_router(cost_analytics.router)
router.include_router(feature_flags.router)
router.include_router(alerts.router)
router.include_router(observability.router)
router.include_router(impersonation.router)
router.include_router(promotions.router)
router.include_router(feedback.router)
router.include_router(ops.router)
router.include_router(blog.router)
router.include_router(decisions.router)
router.include_router(partitions.router)
router.include_router(embeddings.router)
router.include_router(extended_kpis.router)
router.include_router(costs.router)
router.include_router(email_stats.router)
router.include_router(drilldown.router)
router.include_router(runtime_config.router)
router.include_router(email.router)
router.include_router(queries.router)
router.include_router(templates.router)
router.include_router(dashboard.router)
router.include_router(terms.router)
router.include_router(seo_analytics.router)
router.include_router(experiments.router)
router.include_router(billing.router)

# Re-export models for backward compatibility
from backend.api.admin.models import (  # noqa: E402, F401
    ActiveSessionInfo,
    ActiveSessionsResponse,
    AddWhitelistRequest,
    AdminStatsResponse,
    AlertHistoryItem,
    AlertHistoryResponse,
    AlertSettingsResponse,
    ApproveWaitlistResponse,
    BetaWhitelistEntry,
    BetaWhitelistResponse,
    FullSessionResponse,
    KillAllResponse,
    ResearchCacheStats,
    StaleEntriesResponse,
    UpdateUserRequest,
    UserInfo,
    UserListResponse,
    WaitlistEntry,
    WaitlistResponse,
)

__all__ = [
    "router",
    # Models
    "UserInfo",
    "UserListResponse",
    "UpdateUserRequest",
    "AdminStatsResponse",
    "ActiveSessionInfo",
    "ActiveSessionsResponse",
    "FullSessionResponse",
    "KillAllResponse",
    "ResearchCacheStats",
    "StaleEntriesResponse",
    "BetaWhitelistEntry",
    "BetaWhitelistResponse",
    "AddWhitelistRequest",
    "WaitlistEntry",
    "WaitlistResponse",
    "ApproveWaitlistResponse",
    "AlertHistoryItem",
    "AlertHistoryResponse",
    "AlertSettingsResponse",
]
