"""Admin API module - combines all domain-specific admin routers.

This module provides a unified router for all admin endpoints, organized by domain:
- Users: User management and statistics
- Sessions: Active session monitoring and control
- Research Cache: Cache statistics and maintenance
- Beta Whitelist: Beta access control
- Waitlist: Waitlist management and approvals
- Metrics: System metrics and monitoring

Usage:
    from backend.api import admin
    app.include_router(admin.router, prefix="/api", tags=["admin"])
"""

from fastapi import APIRouter

from backend.api.admin import (
    beta_whitelist,
    metrics,
    research_cache,
    sessions,
    users,
    waitlist,
)

# Create the main admin router with /admin prefix
router = APIRouter(prefix="/admin", tags=["admin"])

# Include all domain-specific sub-routers
router.include_router(users.router)
router.include_router(sessions.router)
router.include_router(research_cache.router)
router.include_router(beta_whitelist.router)
router.include_router(waitlist.router)
router.include_router(metrics.router)

# Re-export models for backward compatibility
from backend.api.admin.models import (  # noqa: E402, F401
    ActiveSessionInfo,
    ActiveSessionsResponse,
    AddWhitelistRequest,
    AdminStatsResponse,
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
]
