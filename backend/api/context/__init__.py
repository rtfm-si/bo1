"""Context management API module.

Provides endpoints for managing user business context including:
- CRUD operations for business context
- Website enrichment
- Competitor detection
- Market trends

This module is split into:
- models.py: Pydantic models and enums
- services.py: Business logic helpers
- competitors.py: Competitor detection logic
- routes.py: FastAPI router and endpoints

For backward compatibility, the router is re-exported here.
"""

from backend.api.context.models import (
    BusinessContext,
    BusinessStage,
    ClarificationRequest,
    CompetitorDetectRequest,
    CompetitorDetectResponse,
    ContextResponse,
    DetectedCompetitor,
    EnrichmentRequest,
    EnrichmentResponse,
    EnrichmentSource,
    MarketTrend,
    PrimaryObjective,
    RefreshCheckResponse,
    TrendsRefreshRequest,
    TrendsRefreshResponse,
)
from backend.api.context.routes import router

__all__ = [
    # Router
    "router",
    # Enums
    "BusinessStage",
    "PrimaryObjective",
    "EnrichmentSource",
    # Models
    "BusinessContext",
    "EnrichmentRequest",
    "EnrichmentResponse",
    "ContextResponse",
    "ClarificationRequest",
    "RefreshCheckResponse",
    "CompetitorDetectRequest",
    "DetectedCompetitor",
    "CompetitorDetectResponse",
    "MarketTrend",
    "TrendsRefreshRequest",
    "TrendsRefreshResponse",
]
