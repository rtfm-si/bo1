"""FastAPI router for context management.

Aggregates all context sub-routers into a single router.
Sub-routers are organized by domain:
- core_routes: CRUD, enrichment, refresh, competitor detection, trends refresh
- config_routes: key metrics, working pattern, heatmap depth
- competitors_routes: managed competitors, competitor insights
- goals_routes: goal progress, history, staleness, objectives
- insights_routes: clarification insights, demo questions, enrichment
- metrics_routes: metric suggestions, calculable metrics, calculation
- pending_routes: pending context updates
- research_routes: recent research, embeddings visualization
- trends_routes: trend analysis, insights, summaries, forecasts
"""

from fastapi import APIRouter

from backend.api.context.competitors_routes import router as competitors_router
from backend.api.context.config_routes import router as config_router
from backend.api.context.core_routes import router as core_router
from backend.api.context.goals_routes import router as goals_router
from backend.api.context.insights_routes import router as insights_router
from backend.api.context.metrics_routes import router as metrics_router
from backend.api.context.pending_routes import router as pending_router
from backend.api.context.research_routes import router as research_router
from backend.api.context.trends_routes import router as trends_router

router = APIRouter(tags=["context"])

router.include_router(core_router)
router.include_router(config_router)
router.include_router(competitors_router)
router.include_router(goals_router)
router.include_router(insights_router)
router.include_router(metrics_router)
router.include_router(pending_router)
router.include_router(research_router)
router.include_router(trends_router)

# ---------------------------------------------------------------------------
# Re-exports (tests import from routes.py)
# ---------------------------------------------------------------------------
from backend.api.context.competitors_routes import (  # noqa: E402
    add_managed_competitor as add_managed_competitor,
)
from backend.api.context.insights_routes import (  # noqa: E402
    delete_insight as delete_insight,
    get_insights as get_insights,
)
from backend.api.context.metrics_routes import (  # noqa: E402
    apply_metric_suggestion as apply_metric_suggestion,
    calculate_metric as calculate_metric,
    get_calculable_metrics as get_calculable_metrics,
    get_metric_questions as get_metric_questions,
)
from backend.api.context.models import (  # noqa: E402
    InsightEnrichResponse as InsightEnrichResponse,
)
from backend.api.context.services import (  # noqa: E402
    COMPETITOR_INSIGHT_TIER_LIMITS as COMPETITOR_INSIGHT_TIER_LIMITS,
    GOAL_STALENESS_THRESHOLD_DAYS as GOAL_STALENESS_THRESHOLD_DAYS,
    _get_insight_limit_for_tier as _get_insight_limit_for_tier,
)
from backend.api.context.trends_routes import (  # noqa: E402
    refresh_trend_summary as refresh_trend_summary,
)
