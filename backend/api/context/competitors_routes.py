"""FastAPI router for competitor-related context endpoints.

Extracted from routes.py. Provides:
- POST /v1/context/competitors/{name}/insights - Generate competitor insight
- GET /v1/context/competitors/insights - List cached insights
- DELETE /v1/context/competitors/{name}/insights - Delete cached insight
- GET /v1/context/managed-competitors - List managed competitors
- POST /v1/context/managed-competitors - Add managed competitor
- PATCH /v1/context/managed-competitors/{name} - Update managed competitor
- DELETE /v1/context/managed-competitors/{name} - Remove managed competitor
- POST /v1/context/managed-competitors/{name}/enrich - Enrich single competitor
- POST /v1/context/managed-competitors/enrich-all - Enrich all competitors
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request

from backend.api.context.models import (
    CompetitorInsightResponse,
    CompetitorInsightsListResponse,
    DetectedCompetitor,
    ManagedCompetitor,
    ManagedCompetitorBulkEnrichResponse,
    ManagedCompetitorCreate,
    ManagedCompetitorEnrichResponse,
    ManagedCompetitorListResponse,
    ManagedCompetitorResponse,
    ManagedCompetitorUpdate,
    RelevanceFlags,
)
from backend.api.context.services import (
    COMPETITOR_INSIGHT_TIER_LIMITS as COMPETITOR_INSIGHT_TIER_LIMITS,
)
from backend.api.context.services import (
    _get_insight_limit_for_tier,
)
from backend.api.context.skeptic import evaluate_competitor_relevance
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTEXT_RATE_LIMIT, limiter
from backend.api.utils import RATE_LIMIT_RESPONSE
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_400_RESPONSE,
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
    ERROR_409_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.logging.errors import log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


# =============================================================================
# Competitor Insights Endpoints (AI-generated analysis cards)
# =============================================================================


@router.post(
    "/v1/context/competitors/{name}/insights",
    response_model=CompetitorInsightResponse,
    summary="Generate insight for a competitor",
    description="""
    Generate an AI-powered insight card for a specific competitor.

    Uses Haiku for fast, cost-effective analysis (~$0.003/request).
    Includes web search for fresh company data when available.

    **Rate Limit:** 3 requests per minute per user (LLM cost control).

    **Caching:** Results are cached in user context. Subsequent calls
    for the same competitor return cached data unless forced refresh.
    """,
    responses={
        200: {"description": "Insight generated or retrieved from cache"},
        400: ERROR_400_RESPONSE,
        403: ERROR_403_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
    },
)
@handle_api_errors("generate competitor insight")
async def generate_competitor_insight(
    name: str,
    refresh: bool = False,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorInsightResponse:
    """Generate AI-powered insight for a competitor."""
    from backend.services.competitor_analyzer import get_competitor_analyzer

    user_id = extract_user_id(user)

    # Sanitize competitor name
    name = name.strip()[:100]
    if not name:
        raise http_error(ErrorCode.API_BAD_REQUEST, "Competitor name required", status=400)

    # Load user context
    context_data = user_repository.get_context(user_id) or {}

    # Check cache first (unless refresh requested)
    cached_insights = context_data.get("competitor_insights", {})
    if name in cached_insights and not refresh:
        insight_data = cached_insights[name]
        from backend.api.context.models import CompetitorInsight

        return CompetitorInsightResponse(
            success=True,
            insight=CompetitorInsight(**insight_data),
            generation_status="cached",
        )

    # Generate new insight
    analyzer = get_competitor_analyzer()
    result = await analyzer.generate_insight(
        competitor_name=name,
        industry=context_data.get("industry"),
        product_description=context_data.get("product_description"),
        value_proposition=context_data.get("main_value_proposition"),
    )

    if result.status == "error":
        return CompetitorInsightResponse(
            success=False,
            insight=None,
            error=result.error,
            generation_status="error",
        )

    # Cache the result
    insight_dict = result.to_dict()
    cached_insights[name] = insight_dict
    context_data["competitor_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Generated competitor insight for {name} (user={user_id})")

    from backend.api.context.models import CompetitorInsight

    return CompetitorInsightResponse(
        success=True,
        insight=CompetitorInsight(**insight_dict),
        generation_status=result.status,
    )


@router.get(
    "/v1/context/competitors/insights",
    response_model=CompetitorInsightsListResponse,
    summary="List cached competitor insights",
    description="""
    Retrieve all cached competitor insights for the user.

    **Tier Gating:**
    - Free: 1 visible insight
    - Starter: 3 visible insights
    - Pro: Unlimited insights

    Returns `visible_count` and `total_count` to show users what they're missing.
    Includes `upgrade_prompt` when tier limit is reached.
    """,
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("list competitor insights")
async def list_competitor_insights(
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorInsightsListResponse:
    """List all cached competitor insights with tier gating."""
    from backend.api.context.models import CompetitorInsight

    user_id = extract_user_id(user)
    tier = user.get("subscription_tier", "free")

    # Load cached insights
    context_data = user_repository.get_context(user_id)
    if not context_data:
        return CompetitorInsightsListResponse(
            success=True,
            insights=[],
            visible_count=0,
            total_count=0,
            tier=tier,
        )

    cached_insights = context_data.get("competitor_insights", {})
    total_count = len(cached_insights)

    # Apply tier limit
    limit = _get_insight_limit_for_tier(tier)
    visible_count = min(total_count, limit)

    # Convert to list and apply limit
    insights = []
    for i, (name, data) in enumerate(cached_insights.items()):
        if i >= limit:
            break
        try:
            insights.append(CompetitorInsight(**data))
        except Exception as e:
            logger.warning(f"Failed to parse cached insight for {name}: {e}")
            continue

    # Build upgrade prompt if limit reached
    upgrade_prompt = None
    if total_count > visible_count:
        hidden_count = total_count - visible_count
        upgrade_prompt = (
            f"Upgrade to see {hidden_count} more competitor insight"
            f"{'s' if hidden_count > 1 else ''}."
        )

    return CompetitorInsightsListResponse(
        success=True,
        insights=insights,
        visible_count=visible_count,
        total_count=total_count,
        tier=tier,
        upgrade_prompt=upgrade_prompt,
    )


@router.delete(
    "/v1/context/competitors/{name}/insights",
    response_model=dict[str, str],
    summary="Delete cached competitor insight",
    description="""
    Remove a cached competitor insight.

    This frees up a slot for users on limited tiers.
    The insight can be regenerated by calling the POST endpoint.
    """,
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("delete competitor insight")
async def delete_competitor_insight(
    name: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Delete a cached competitor insight."""
    user_id = extract_user_id(user)

    # Load context
    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    cached_insights = context_data.get("competitor_insights", {})
    if name not in cached_insights:
        raise http_error(ErrorCode.API_NOT_FOUND, "Insight not found", status=404)

    # Remove insight
    del cached_insights[name]
    context_data["competitor_insights"] = cached_insights
    user_repository.save_context(user_id, context_data)

    logger.info(f"Deleted competitor insight for {name} (user={user_id})")

    return {"status": "deleted"}


# =============================================================================
# Managed Competitors Endpoints (User-submitted competitor list)
# =============================================================================


@router.get(
    "/v1/context/managed-competitors",
    response_model=ManagedCompetitorListResponse,
    summary="List user's managed competitors",
    description="""
    Retrieve the user's manually managed competitor list.

    These are competitors the user has explicitly added, distinct from:
    - Auto-detected competitors (from enrichment)
    - Competitor insights (AI-generated analysis cards)

    Returns competitors sorted by added_at (newest first).
    """,
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("list managed competitors")
async def list_managed_competitors(
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorListResponse:
    """List user's managed competitors."""
    import time

    user_id = extract_user_id(user)

    start_time = time.monotonic()
    logger.debug(f"[MANAGED_COMPETITORS] Fetching for user {user_id[:8]}...")
    competitors_data = user_repository.get_managed_competitors(user_id)
    elapsed_ms = (time.monotonic() - start_time) * 1000
    logger.debug(
        f"[MANAGED_COMPETITORS] Fetched {len(competitors_data)} competitors in {elapsed_ms:.1f}ms"
    )

    # Convert to models and sort by added_at (newest first)
    competitors = []
    for c in competitors_data:
        try:
            added_at = c.get("added_at")
            if isinstance(added_at, str):
                added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))
            # Parse relevance_flags if present
            flags_data = c.get("relevance_flags")
            relevance_flags = None
            if flags_data and isinstance(flags_data, dict):
                relevance_flags = RelevanceFlags(**flags_data)
            competitors.append(
                ManagedCompetitor(
                    name=c.get("name", ""),
                    url=c.get("url"),
                    notes=c.get("notes"),
                    added_at=added_at or datetime.now(UTC),
                    relevance_score=c.get("relevance_score"),
                    relevance_flags=relevance_flags,
                    relevance_warning=c.get("relevance_warning"),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse managed competitor: {e}")
            continue

    # Sort by added_at (newest first)
    competitors.sort(key=lambda c: c.added_at, reverse=True)

    return ManagedCompetitorListResponse(
        success=True,
        competitors=competitors,
        count=len(competitors),
    )


@router.post(
    "/v1/context/managed-competitors",
    response_model=ManagedCompetitorResponse,
    summary="Add a managed competitor",
    description="""
    Add a new competitor to the user's managed list.

    Performs case-insensitive deduplication - if a competitor with
    the same name (ignoring case) already exists, returns error.

    **Use Cases:**
    - User manually adds known competitor
    - Capture competitor from external source
    """,
    responses={
        200: {"description": "Competitor added successfully"},
        403: ERROR_403_RESPONSE,
        409: ERROR_409_RESPONSE,
    },
)
@handle_api_errors("add managed competitor")
async def add_managed_competitor(
    request: ManagedCompetitorCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorResponse:
    """Add a new managed competitor."""
    user_id = extract_user_id(user)

    result = user_repository.add_managed_competitor(
        user_id=user_id,
        name=request.name,
        url=request.url,
        notes=request.notes,
    )

    if result is None:
        raise http_error(
            ErrorCode.API_CONFLICT,
            f"Competitor '{request.name}' already exists",
            status=409,
        )

    # Convert added_at to datetime
    added_at = result.get("added_at")
    if isinstance(added_at, str):
        added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

    # Run skeptic check to warn about low-relevance competitors
    relevance_warning = None
    relevance_score = None
    try:
        context_data = user_repository.get_context(user_id)
        if context_data:
            competitor = DetectedCompetitor(
                name=request.name,
                url=request.url,
                description=request.notes,
            )
            evaluated = await evaluate_competitor_relevance(competitor, context_data)
            relevance_score = evaluated.relevance_score
            relevance_warning = evaluated.relevance_warning
    except Exception as e:
        logger.warning(f"Skeptic check failed for manual competitor: {e}")

    return ManagedCompetitorResponse(
        success=True,
        competitor=ManagedCompetitor(
            name=result.get("name", ""),
            url=result.get("url"),
            notes=result.get("notes"),
            added_at=added_at or datetime.now(UTC),
        ),
        relevance_warning=relevance_warning,
        relevance_score=relevance_score,
    )


@router.patch(
    "/v1/context/managed-competitors/{name}",
    response_model=ManagedCompetitorResponse,
    summary="Update a managed competitor",
    description="""
    Update the URL and/or notes for a managed competitor.

    Competitor is matched by name (case-insensitive).
    Only provided fields are updated - omitted fields remain unchanged.
    """,
    responses={
        200: {"description": "Competitor updated successfully"},
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@handle_api_errors("update managed competitor")
async def update_managed_competitor(
    name: str,
    request: ManagedCompetitorUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorResponse:
    """Update a managed competitor's url and/or notes."""
    user_id = extract_user_id(user)

    result = user_repository.update_managed_competitor(
        user_id=user_id,
        name=name,
        url=request.url,
        notes=request.notes,
    )

    if result is None:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            f"Competitor '{name}' not found",
            status=404,
        )

    # Convert added_at to datetime
    added_at = result.get("added_at")
    if isinstance(added_at, str):
        added_at = datetime.fromisoformat(added_at.replace("Z", "+00:00"))

    return ManagedCompetitorResponse(
        success=True,
        competitor=ManagedCompetitor(
            name=result.get("name", ""),
            url=result.get("url"),
            notes=result.get("notes"),
            added_at=added_at or datetime.now(UTC),
        ),
    )


@router.delete(
    "/v1/context/managed-competitors/{name}",
    response_model=dict[str, str],
    summary="Remove a managed competitor",
    description="""
    Remove a competitor from the user's managed list.

    Competitor is matched by name (case-insensitive).
    This does not delete any associated competitor insights.
    """,
    responses={
        200: {"description": "Competitor removed successfully"},
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
    },
)
@handle_api_errors("remove managed competitor")
async def remove_managed_competitor(
    name: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Remove a managed competitor."""
    user_id = extract_user_id(user)

    success = user_repository.remove_managed_competitor(user_id, name)

    if not success:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            f"Competitor '{name}' not found",
            status=404,
        )

    return {"status": "deleted"}


# =============================================================================
# Phase 8.5: Managed Competitor Enrichment
# =============================================================================


@router.post(
    "/v1/context/managed-competitors/{name}/enrich",
    response_model=ManagedCompetitorEnrichResponse,
    summary="Enrich a managed competitor with Tavily data",
    description="""
    Enrich a single managed competitor with data from Tavily Search API.

    Retrieves:
    - Company tagline and description
    - Funding information (deep tier)
    - Employee count (deep tier)
    - Recent news (deep tier)

    Rate limited to prevent API abuse.
    """,
    responses={
        200: {"description": "Enrichment completed"},
        403: ERROR_403_RESPONSE,
        404: ERROR_404_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit(CONTEXT_RATE_LIMIT)
@handle_api_errors("enrich managed competitor")
async def enrich_managed_competitor(
    request: Request,
    name: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorEnrichResponse:
    """Enrich a single managed competitor with Tavily data."""
    import asyncio
    import time

    import httpx
    from psycopg2 import DatabaseError, OperationalError

    from backend.api.competitors import enrich_competitor_with_tavily
    from backend.api.utils.db_helpers import get_user_tier

    user_id = extract_user_id(user)

    # Get tier config for data depth
    tier = get_user_tier(user_id)
    tier_config = {"free": "basic", "starter": "standard", "pro": "deep"}
    data_depth = tier_config.get(tier, "basic")

    # Find competitor in user's managed list
    competitors = user_repository.get_managed_competitors(user_id)
    name_lower = name.lower().strip()
    target_competitor = None
    target_index = -1

    for i, c in enumerate(competitors):
        if c.get("name", "").lower().strip() == name_lower:
            target_competitor = c
            target_index = i
            break

    if target_competitor is None:
        raise http_error(
            ErrorCode.API_NOT_FOUND,
            f"Competitor '{name}' not found",
            status=404,
        )

    try:
        # Enrich with Tavily
        start_time = time.monotonic()
        enriched = await enrich_competitor_with_tavily(
            target_competitor["name"],
            target_competitor.get("url"),
            data_depth,
        )
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(f"Tavily enrichment took {elapsed_ms:.0f}ms for {target_competitor['name']}")

        # Detect changes
        changes = []
        for key, value in enriched.items():
            if value and target_competitor.get(key) != value:
                changes.append(key)

        # Update competitor record with enriched data
        target_competitor.update(
            {
                "tagline": enriched.get("tagline") or target_competitor.get("tagline"),
                "product_description": enriched.get("product_description")
                or target_competitor.get("product_description"),
                "funding_info": enriched.get("funding_info")
                or target_competitor.get("funding_info"),
                "employee_count": enriched.get("employee_count")
                or target_competitor.get("employee_count"),
                "recent_news": enriched.get("recent_news") or target_competitor.get("recent_news"),
                "last_enriched_at": datetime.now(UTC).isoformat(),
                "changes_detected": changes if changes else None,
            }
        )

        # Save updated competitors list
        competitors[target_index] = target_competitor
        context = user_repository.get_context(user_id) or {}
        context["managed_competitors"] = competitors
        user_repository.save_context(user_id, context)

        # Build response
        return ManagedCompetitorEnrichResponse(
            success=True,
            competitor=ManagedCompetitor(
                name=target_competitor["name"],
                url=target_competitor.get("url"),
                notes=target_competitor.get("notes"),
                added_at=datetime.fromisoformat(target_competitor["added_at"]),
                relevance_score=target_competitor.get("relevance_score"),
                relevance_flags=target_competitor.get("relevance_flags"),
                relevance_warning=target_competitor.get("relevance_warning"),
                tagline=target_competitor.get("tagline"),
                product_description=target_competitor.get("product_description"),
                funding_info=target_competitor.get("funding_info"),
                employee_count=target_competitor.get("employee_count"),
                tech_stack=target_competitor.get("tech_stack"),
                recent_news=target_competitor.get("recent_news"),
                last_enriched_at=datetime.fromisoformat(target_competitor["last_enriched_at"])
                if target_competitor.get("last_enriched_at")
                else None,
                changes_detected=target_competitor.get("changes_detected"),
            ),
            changes=changes if changes else None,
        )

    except httpx.HTTPError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"HTTP error during enrichment: {e}",
            competitor_name=target_competitor["name"],
        )
        return ManagedCompetitorEnrichResponse(
            success=False,
            error=f"Failed to connect to enrichment service: {e}",
        )
    except (DatabaseError, OperationalError) as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Database error during enrichment: {e}",
            competitor_name=target_competitor["name"],
        )
        return ManagedCompetitorEnrichResponse(
            success=False,
            error="Database error during enrichment",
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Unexpected error during enrichment: {e}",
            exc_info=True,
            competitor_name=target_competitor["name"],
        )
        return ManagedCompetitorEnrichResponse(
            success=False,
            error=str(e),
        )


@router.post(
    "/v1/context/managed-competitors/enrich-all",
    response_model=ManagedCompetitorBulkEnrichResponse,
    summary="Enrich all managed competitors (monthly refresh)",
    description="""
    Enrich all managed competitors with data from Tavily Search API.

    This is an expensive operation - use sparingly (monthly refresh recommended).
    Competitors are enriched sequentially with a small delay between requests.
    """,
    responses={
        200: {"description": "Bulk enrichment completed"},
        403: ERROR_403_RESPONSE,
        429: RATE_LIMIT_RESPONSE,
    },
)
@limiter.limit("1/minute")
@handle_api_errors("enrich all managed competitors")
async def enrich_all_managed_competitors(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> ManagedCompetitorBulkEnrichResponse:
    """Enrich all managed competitors with Tavily data."""
    import asyncio

    import httpx
    from psycopg2 import DatabaseError, OperationalError

    from backend.api.competitors import enrich_competitor_with_tavily
    from backend.api.utils.db_helpers import get_user_tier

    user_id = extract_user_id(user)

    # Get tier config
    tier = get_user_tier(user_id)
    tier_config = {"free": "basic", "starter": "standard", "pro": "deep"}
    data_depth = tier_config.get(tier, "basic")

    competitors = user_repository.get_managed_competitors(user_id)
    if not competitors:
        return ManagedCompetitorBulkEnrichResponse(
            success=True,
            enriched_count=0,
            competitors=[],
        )

    enriched_competitors = []
    errors = []

    for i, comp in enumerate(competitors):
        try:
            # Small delay between requests to avoid rate limiting
            if i > 0:
                await asyncio.sleep(0.5)

            enriched = await enrich_competitor_with_tavily(
                comp["name"],
                comp.get("url"),
                data_depth,
            )

            # Update competitor with enriched data
            comp.update(
                {
                    "tagline": enriched.get("tagline") or comp.get("tagline"),
                    "product_description": enriched.get("product_description")
                    or comp.get("product_description"),
                    "funding_info": enriched.get("funding_info") or comp.get("funding_info"),
                    "employee_count": enriched.get("employee_count") or comp.get("employee_count"),
                    "recent_news": enriched.get("recent_news") or comp.get("recent_news"),
                    "last_enriched_at": datetime.now(UTC).isoformat(),
                }
            )

            enriched_competitors.append(
                ManagedCompetitor(
                    name=comp["name"],
                    url=comp.get("url"),
                    notes=comp.get("notes"),
                    added_at=datetime.fromisoformat(comp["added_at"]),
                    relevance_score=comp.get("relevance_score"),
                    relevance_flags=comp.get("relevance_flags"),
                    relevance_warning=comp.get("relevance_warning"),
                    tagline=comp.get("tagline"),
                    product_description=comp.get("product_description"),
                    funding_info=comp.get("funding_info"),
                    employee_count=comp.get("employee_count"),
                    tech_stack=comp.get("tech_stack"),
                    recent_news=comp.get("recent_news"),
                    last_enriched_at=datetime.fromisoformat(comp["last_enriched_at"])
                    if comp.get("last_enriched_at")
                    else None,
                    changes_detected=comp.get("changes_detected"),
                )
            )

        except httpx.HTTPError as e:
            errors.append(f"{comp['name']}: HTTP error - {e}")
            enriched_competitors.append(
                ManagedCompetitor(
                    name=comp["name"],
                    url=comp.get("url"),
                    notes=comp.get("notes"),
                    added_at=datetime.fromisoformat(comp["added_at"]),
                )
            )
        except (DatabaseError, OperationalError):
            errors.append(f"{comp['name']}: Database error")
            enriched_competitors.append(
                ManagedCompetitor(
                    name=comp["name"],
                    url=comp.get("url"),
                    notes=comp.get("notes"),
                    added_at=datetime.fromisoformat(comp["added_at"]),
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Unexpected error enriching {comp['name']}: {e}",
                exc_info=True,
                competitor_name=comp["name"],
            )
            errors.append(f"{comp['name']}: {str(e)}")
            enriched_competitors.append(
                ManagedCompetitor(
                    name=comp["name"],
                    url=comp.get("url"),
                    notes=comp.get("notes"),
                    added_at=datetime.fromisoformat(comp["added_at"]),
                )
            )

    # Save updated competitors list
    context = user_repository.get_context(user_id) or {}
    context["managed_competitors"] = competitors
    user_repository.save_context(user_id, context)

    return ManagedCompetitorBulkEnrichResponse(
        success=len(errors) == 0,
        enriched_count=len(competitors) - len(errors),
        competitors=enriched_competitors,
        errors=errors if errors else None,
    )
