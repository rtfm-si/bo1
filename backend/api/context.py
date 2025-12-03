"""Context management API endpoints.

Provides:
- GET /api/v1/context - Get user's saved business context
- PUT /api/v1/context - Update user's business context
- DELETE /api/v1/context - Delete user's saved context
- GET /api/v1/context/refresh-check - Check if refresh prompt needed
- POST /api/v1/context/dismiss-refresh - Dismiss refresh prompt
"""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from bo1.config import get_settings
from bo1.services.enrichment import EnrichmentService
from bo1.state.database import db_session
from bo1.state.postgres_manager import (
    delete_user_context,
    load_user_context,
    save_user_context,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])

# Context refresh interval (3 months)
CONTEXT_REFRESH_DAYS = 90


class BusinessStage(str, Enum):
    """Business development stage."""

    IDEA = "idea"
    EARLY = "early"
    GROWING = "growing"
    SCALING = "scaling"


class PrimaryObjective(str, Enum):
    """Primary business objective."""

    ACQUIRE_CUSTOMERS = "acquire_customers"
    IMPROVE_RETENTION = "improve_retention"
    RAISE_CAPITAL = "raise_capital"
    LAUNCH_PRODUCT = "launch_product"
    REDUCE_COSTS = "reduce_costs"


class EnrichmentSource(str, Enum):
    """Source of business context enrichment."""

    MANUAL = "manual"
    API = "api"
    SCRAPE = "scrape"


class BusinessContext(BaseModel):
    """Business context data model.

    Contains both basic fields (original) and extended fields (new).
    """

    # =========================================================================
    # Original fields (backward compatible)
    # =========================================================================
    business_model: str | None = Field(
        None,
        description="Business model (e.g., B2B SaaS, marketplace)",
        examples=["B2B SaaS"],
    )
    target_market: str | None = Field(
        None,
        description="Target market description",
        examples=["Small businesses in North America"],
    )
    product_description: str | None = Field(
        None,
        description="Product/service description",
        examples=["AI-powered project management tool"],
    )
    revenue: str | None = Field(
        None,
        description="Monthly/annual revenue",
        examples=["$50,000 MRR"],
    )
    customers: str | None = Field(
        None,
        description="Number of active customers",
        examples=["150"],
    )
    growth_rate: str | None = Field(
        None,
        description="Growth rate percentage",
        examples=["15% MoM"],
    )
    competitors: str | None = Field(
        None,
        description="List of competitors (comma-separated or JSON)",
        examples=["Asana, Monday.com, Jira"],
    )
    website: str | None = Field(
        None,
        description="Website URL",
        examples=["https://example.com"],
    )

    # =========================================================================
    # New extended fields (Tier 3)
    # =========================================================================
    company_name: str | None = Field(
        None,
        description="Company name",
        examples=["Acme Inc"],
    )
    business_stage: BusinessStage | None = Field(
        None,
        description="Business development stage",
    )
    primary_objective: PrimaryObjective | None = Field(
        None,
        description="Primary business objective",
    )
    industry: str | None = Field(
        None,
        description="Industry vertical",
        examples=["Software", "Healthcare", "Finance"],
    )
    product_categories: list[str] | None = Field(
        None,
        description="Product/service categories",
        examples=[["Project Management", "Collaboration"]],
    )
    pricing_model: str | None = Field(
        None,
        description="Pricing model",
        examples=["Subscription", "Freemium", "Usage-based"],
    )
    brand_positioning: str | None = Field(
        None,
        description="Brand positioning statement",
    )
    brand_tone: str | None = Field(
        None,
        description="Brand tone/voice",
        examples=["Professional", "Friendly", "Technical"],
    )
    brand_maturity: str | None = Field(
        None,
        description="Brand maturity level",
        examples=["startup", "emerging", "established", "mature"],
    )
    tech_stack: list[str] | None = Field(
        None,
        description="Technology stack",
        examples=[["React", "Node.js", "PostgreSQL"]],
    )
    seo_structure: dict[str, Any] | None = Field(
        None,
        description="SEO metadata from website",
    )
    detected_competitors: list[str] | None = Field(
        None,
        description="Auto-detected competitors",
    )
    ideal_customer_profile: str | None = Field(
        None,
        description="Ideal customer profile description",
    )
    keywords: list[str] | None = Field(
        None,
        description="Market category keywords",
    )
    target_geography: str | None = Field(
        None,
        description="Target geography",
        examples=["North America", "Global", "Europe"],
    )
    traffic_range: str | None = Field(
        None,
        description="Website traffic range",
        examples=["<1k", "1k-10k", "10k-100k", "100k+"],
    )
    mau_bucket: str | None = Field(
        None,
        description="Monthly active users bucket",
    )
    revenue_stage: str | None = Field(
        None,
        description="Revenue stage",
        examples=["pre-revenue", "early", "growth", "mature"],
    )
    main_value_proposition: str | None = Field(
        None,
        description="Main value proposition",
    )
    team_size: str | None = Field(
        None,
        description="Team size",
        examples=["solo", "small (2-5)", "medium (6-20)", "large (20+)"],
    )
    budget_constraints: str | None = Field(
        None,
        description="Budget constraints",
    )
    time_constraints: str | None = Field(
        None,
        description="Time constraints",
    )
    regulatory_constraints: str | None = Field(
        None,
        description="Regulatory constraints",
    )

    # Enrichment metadata
    enrichment_source: EnrichmentSource | None = Field(
        None,
        description="Source of enrichment data",
    )
    enrichment_date: datetime | None = Field(
        None,
        description="When enrichment was performed",
    )


class EnrichmentRequest(BaseModel):
    """Request to enrich context from website."""

    website_url: str = Field(
        ...,
        description="Website URL to analyze",
        examples=["https://example.com"],
    )


class EnrichmentResponse(BaseModel):
    """Response from website enrichment."""

    success: bool = Field(..., description="Whether enrichment succeeded")
    context: BusinessContext | None = Field(None, description="Enriched context")
    enrichment_source: str | None = Field(None, description="Source of enrichment")
    confidence: str | None = Field(None, description="Confidence level")
    error: str | None = Field(None, description="Error message if failed")


class ContextResponse(BaseModel):
    """Response model for context retrieval.

    Attributes:
        exists: Whether user has saved context
        context: Business context data (if exists)
        updated_at: Last update timestamp (if exists)
    """

    exists: bool = Field(..., description="Whether user has saved context")
    context: BusinessContext | None = Field(None, description="Business context data")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "exists": True,
                    "context": {
                        "business_model": "B2B SaaS",
                        "target_market": "Small businesses in North America",
                        "product_description": "AI-powered project management tool",
                        "revenue": 50000.0,
                        "customers": 150,
                        "growth_rate": 15.5,
                        "competitors": ["Asana", "Monday.com", "Jira"],
                        "website": "https://example.com",
                    },
                    "updated_at": "2025-01-15T12:00:00",
                },
                {
                    "exists": False,
                    "context": None,
                    "updated_at": None,
                },
            ]
        }
    }


class ClarificationRequest(BaseModel):
    """Request model for clarification answer.

    Attributes:
        answer: User's answer to the clarification question
    """

    answer: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Answer to clarification question",
    )


@router.get(
    "/v1/context",
    response_model=ContextResponse,
    summary="Get user's saved business context",
    description="""
    Retrieve the authenticated user's saved business context.

    Business context is persistent across sessions and helps the AI personas
    provide more relevant recommendations. Context includes:
    - Business model and target market
    - Product/service description
    - Revenue and growth metrics
    - Competitor information

    **Use Cases:**
    - Check if user has saved context before starting deliberation
    - Display saved context in user profile
    - Pre-fill forms with existing context
    """,
    responses={
        200: {
            "description": "Context retrieved successfully (exists=true if saved, false if not)",
            "content": {
                "application/json": {
                    "examples": {
                        "with_context": {
                            "summary": "User has saved context",
                            "value": {
                                "exists": True,
                                "context": {
                                    "business_model": "B2B SaaS",
                                    "target_market": "Small businesses in North America",
                                    "product_description": "AI-powered project management tool",
                                    "revenue": 50000.0,
                                    "customers": 150,
                                    "growth_rate": 15.5,
                                    "competitors": ["Asana", "Monday.com", "Jira"],
                                    "website": "https://example.com",
                                },
                                "updated_at": "2025-01-15T12:00:00",
                            },
                        },
                        "no_context": {
                            "summary": "User has no saved context",
                            "value": {
                                "exists": False,
                                "context": None,
                                "updated_at": None,
                            },
                        },
                    }
                }
            },
        },
        500: {"description": "Database error"},
    },
)
async def get_context(user: dict[str, Any] = Depends(get_current_user)) -> ContextResponse:
    """Get user's saved business context.

    Args:
        user: Authenticated user data

    Returns:
        ContextResponse with context data if exists

    Raises:
        HTTPException: If database error occurs
    """
    try:
        user_id = extract_user_id(user)

        # Load context from database
        context_data = load_user_context(user_id)

        if not context_data:
            return ContextResponse(exists=False, context=None, updated_at=None)

        # Parse into BusinessContext - include all extended fields
        context = BusinessContext(
            # Original fields
            business_model=context_data.get("business_model"),
            target_market=context_data.get("target_market"),
            product_description=context_data.get("product_description"),
            revenue=context_data.get("revenue"),
            customers=context_data.get("customers"),
            growth_rate=context_data.get("growth_rate"),
            competitors=context_data.get("competitors"),
            website=context_data.get("website"),
            # Extended fields (Tier 3)
            company_name=context_data.get("company_name"),
            business_stage=context_data.get("business_stage"),
            primary_objective=context_data.get("primary_objective"),
            industry=context_data.get("industry"),
            product_categories=context_data.get("product_categories"),
            pricing_model=context_data.get("pricing_model"),
            brand_positioning=context_data.get("brand_positioning"),
            brand_tone=context_data.get("brand_tone"),
            brand_maturity=context_data.get("brand_maturity"),
            tech_stack=context_data.get("tech_stack"),
            seo_structure=context_data.get("seo_structure"),
            detected_competitors=context_data.get("detected_competitors"),
            ideal_customer_profile=context_data.get("ideal_customer_profile"),
            keywords=context_data.get("keywords"),
            target_geography=context_data.get("target_geography"),
            traffic_range=context_data.get("traffic_range"),
            mau_bucket=context_data.get("mau_bucket"),
            revenue_stage=context_data.get("revenue_stage"),
            main_value_proposition=context_data.get("main_value_proposition"),
            team_size=context_data.get("team_size"),
            budget_constraints=context_data.get("budget_constraints"),
            time_constraints=context_data.get("time_constraints"),
            regulatory_constraints=context_data.get("regulatory_constraints"),
            enrichment_source=context_data.get("enrichment_source"),
            enrichment_date=context_data.get("enrichment_date"),
        )

        return ContextResponse(
            exists=True,
            context=context,
            updated_at=context_data.get("updated_at"),
        )

    except Exception as e:
        logger.error(f"Failed to get context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get context: {str(e)}",
        ) from e


@router.put(
    "/v1/context",
    response_model=dict[str, str],
    summary="Update user's business context",
    description="""
    Create or update the authenticated user's business context.

    Business context is saved to PostgreSQL and persists across sessions.
    This context is used during deliberations to provide more relevant
    recommendations from AI personas.

    **Use Cases:**
    - Save business context during onboarding
    - Update context when business metrics change
    - Pre-populate context for faster deliberation setup

    **Note:** All fields are optional. Only provided fields will be saved.
    """,
    responses={
        200: {
            "description": "Context updated successfully",
            "content": {"application/json": {"example": {"status": "updated"}}},
        },
        500: {"description": "Database error"},
    },
)
async def update_context(
    context: BusinessContext, user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, str]:
    """Update user's business context.

    Args:
        context: Business context to save
        user: Authenticated user data

    Returns:
        Status message

    Raises:
        HTTPException: If database error occurs
    """
    try:
        user_id = extract_user_id(user)

        # Convert to dict for save function - include all fields
        context_dict = {
            # Original fields
            "business_model": context.business_model,
            "target_market": context.target_market,
            "product_description": context.product_description,
            "revenue": context.revenue,
            "customers": context.customers,
            "growth_rate": context.growth_rate,
            "competitors": context.competitors,
            "website": context.website,
            # Extended fields (Tier 3)
            "company_name": context.company_name,
            "business_stage": context.business_stage.value if context.business_stage else None,
            "primary_objective": context.primary_objective.value
            if context.primary_objective
            else None,
            "industry": context.industry,
            "product_categories": context.product_categories,
            "pricing_model": context.pricing_model,
            "brand_positioning": context.brand_positioning,
            "brand_tone": context.brand_tone,
            "brand_maturity": context.brand_maturity,
            "tech_stack": context.tech_stack,
            "seo_structure": context.seo_structure,
            "detected_competitors": context.detected_competitors,
            "ideal_customer_profile": context.ideal_customer_profile,
            "keywords": context.keywords,
            "target_geography": context.target_geography,
            "traffic_range": context.traffic_range,
            "mau_bucket": context.mau_bucket,
            "revenue_stage": context.revenue_stage,
            "main_value_proposition": context.main_value_proposition,
            "team_size": context.team_size,
            "budget_constraints": context.budget_constraints,
            "time_constraints": context.time_constraints,
            "regulatory_constraints": context.regulatory_constraints,
            "enrichment_source": context.enrichment_source.value
            if context.enrichment_source
            else None,
            "enrichment_date": context.enrichment_date,
        }

        # Save to database
        save_user_context(user_id, context_dict)

        logger.info(f"Updated context for user {user_id}")

        return {"status": "updated"}

    except Exception as e:
        logger.error(f"Failed to update context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update context: {str(e)}",
        ) from e


@router.delete(
    "/v1/context",
    response_model=dict[str, str],
    status_code=200,
    summary="Delete user's saved context",
    description="""
    Delete the authenticated user's saved business context.

    This permanently removes all saved business context from the database.
    Future deliberations will not have access to this context unless
    it is re-entered.

    **Use Cases:**
    - User wants to start fresh
    - User wants to remove outdated business information
    - Privacy: Remove all stored business data

    **Warning:** This action cannot be undone.
    """,
    responses={
        200: {
            "description": "Context deleted successfully",
            "content": {"application/json": {"example": {"status": "deleted"}}},
        },
        404: {"description": "No context found to delete"},
        500: {"description": "Database error"},
    },
)
async def delete_context(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    """Delete user's saved business context.

    Args:
        user: Authenticated user data

    Returns:
        Status message

    Raises:
        HTTPException: If database error occurs
    """
    try:
        user_id = extract_user_id(user)

        # Delete from database
        deleted = delete_user_context(user_id)

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="No context found to delete",
            )

        logger.info(f"Deleted context for user {user_id}")

        return {"status": "deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete context: {str(e)}",
        ) from e


# Clarify endpoint moved to control.py (Day 39)


@router.post(
    "/v1/context/enrich",
    response_model=EnrichmentResponse,
    summary="Enrich context from website",
    description="""
    Analyze a website URL and extract business context information.

    Uses:
    - Website metadata (title, description, OG tags)
    - Brave Search API for company information
    - Claude AI for intelligent extraction

    **Auto-save**: The enriched data is automatically merged with existing
    context and saved. Empty fields are not overwritten.
    """,
    responses={
        200: {
            "description": "Enrichment completed (check success field)",
        },
        422: {"description": "Invalid URL format"},
        500: {"description": "Enrichment service error"},
    },
)
async def enrich_context(
    request: EnrichmentRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> EnrichmentResponse:
    """Enrich business context from website URL and auto-save."""
    try:
        user_id = extract_user_id(user)
        logger.info(f"Enriching context from {request.website_url} for user {user_id}")

        # Run enrichment
        service = EnrichmentService()
        try:
            enriched = await service.enrich_from_url(request.website_url)
        finally:
            await service.close()

        # Convert to BusinessContext
        context = BusinessContext(
            company_name=enriched.company_name,
            website=enriched.website,
            industry=enriched.industry,
            business_model=enriched.business_model,
            pricing_model=enriched.pricing_model,
            target_market=enriched.target_market,
            product_description=enriched.product_description,
            product_categories=enriched.product_categories,
            main_value_proposition=enriched.main_value_proposition,
            brand_positioning=enriched.brand_positioning,
            brand_tone=enriched.brand_tone,
            brand_maturity=enriched.brand_maturity,
            tech_stack=enriched.tech_stack,
            seo_structure=enriched.seo_structure,
            keywords=enriched.keywords,
            detected_competitors=enriched.detected_competitors,
            ideal_customer_profile=enriched.ideal_customer_profile,
            enrichment_source=EnrichmentSource(enriched.enrichment_source),
            enrichment_date=enriched.enrichment_date,
        )

        # Auto-save: Merge enriched data with existing context (preserve user values)
        existing_context = load_user_context(user_id) or {}
        enriched_dict = {
            "company_name": enriched.company_name,
            "website": enriched.website,
            "industry": enriched.industry,
            "business_model": enriched.business_model,
            "pricing_model": enriched.pricing_model,
            "target_market": enriched.target_market,
            "product_description": enriched.product_description,
            "product_categories": enriched.product_categories,
            "main_value_proposition": enriched.main_value_proposition,
            "brand_positioning": enriched.brand_positioning,
            "brand_tone": enriched.brand_tone,
            "brand_maturity": enriched.brand_maturity,
            "tech_stack": enriched.tech_stack,
            "seo_structure": enriched.seo_structure,
            "keywords": enriched.keywords,
            "detected_competitors": enriched.detected_competitors,
            "ideal_customer_profile": enriched.ideal_customer_profile,
            "enrichment_source": enriched.enrichment_source,
            "enrichment_date": enriched.enrichment_date.isoformat()
            if enriched.enrichment_date
            else None,
        }

        # Only update fields that don't already have user values (preserve user input)
        merged_context = existing_context.copy()
        for key, value in enriched_dict.items():
            if value is not None and not existing_context.get(key):
                merged_context[key] = value

        # Save merged context
        save_user_context(user_id, merged_context)
        logger.info(f"Auto-saved enriched context for user {user_id}")

        return EnrichmentResponse(
            success=True,
            context=context,
            enrichment_source=enriched.enrichment_source,
            confidence=enriched.confidence,
        )

    except ValueError as e:
        logger.warning(f"Invalid URL: {e}")
        return EnrichmentResponse(
            success=False,
            error=f"Invalid URL: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        return EnrichmentResponse(
            success=False,
            error=f"Enrichment failed: {str(e)}",
        )


class RefreshCheckResponse(BaseModel):
    """Response for refresh check endpoint."""

    needs_refresh: bool = Field(..., description="Whether context needs refreshing")
    last_updated: datetime | None = Field(None, description="When context was last updated")
    days_since_update: int | None = Field(None, description="Days since last update")


@router.get(
    "/v1/context/refresh-check",
    response_model=RefreshCheckResponse,
    summary="Check if context refresh needed",
    description=f"""
    Check if the user's business context needs refreshing.

    Returns true if:
    - No context exists
    - Context hasn't been updated in {CONTEXT_REFRESH_DAYS} days
    - Last refresh prompt was dismissed more than {CONTEXT_REFRESH_DAYS} days ago

    Use this to show "Are these details still correct?" prompts.
    """,
)
async def check_refresh_needed(
    user: dict[str, Any] = Depends(get_current_user),
) -> RefreshCheckResponse:
    """Check if context refresh is needed."""
    try:
        user_id = extract_user_id(user)

        # Get context with extended fields
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT updated_at, last_refresh_prompt, onboarding_completed
                    FROM user_context
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

        if not row:
            return RefreshCheckResponse(
                needs_refresh=True,
                last_updated=None,
                days_since_update=None,
            )

        updated_at = row.get("updated_at")
        last_refresh_prompt = row.get("last_refresh_prompt")
        onboarding_completed = row.get("onboarding_completed", False)

        # If onboarding not completed, don't show refresh prompts
        if not onboarding_completed:
            return RefreshCheckResponse(
                needs_refresh=False,
                last_updated=updated_at,
                days_since_update=None,
            )

        # Calculate days since update
        now = datetime.now(UTC)
        days_since_update = (now - updated_at).days if updated_at else None

        # Check if refresh needed
        needs_refresh = False
        if days_since_update is not None and days_since_update >= CONTEXT_REFRESH_DAYS:
            # Check if we already prompted recently
            if last_refresh_prompt:
                days_since_prompt = (now - last_refresh_prompt).days
                needs_refresh = days_since_prompt >= CONTEXT_REFRESH_DAYS
            else:
                needs_refresh = True

        return RefreshCheckResponse(
            needs_refresh=needs_refresh,
            last_updated=updated_at,
            days_since_update=days_since_update,
        )

    except Exception as e:
        logger.error(f"Failed to check refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check refresh: {str(e)}",
        ) from e


@router.post(
    "/v1/context/dismiss-refresh",
    response_model=dict[str, str],
    summary="Dismiss refresh prompt",
    description="""
    Dismiss the "Are these details still correct?" refresh prompt.

    This updates the last_refresh_prompt timestamp so the user won't see
    the prompt again for another refresh interval.
    """,
)
async def dismiss_refresh_prompt(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Dismiss the refresh prompt."""
    try:
        user_id = extract_user_id(user)

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_context
                    SET last_refresh_prompt = NOW(), updated_at = updated_at
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="No context found")

        return {"status": "dismissed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to dismiss refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to dismiss refresh: {str(e)}",
        ) from e


# =============================================================================
# Phase 3: Strategic Context Endpoints
# =============================================================================


class CompetitorDetectRequest(BaseModel):
    """Request to detect competitors."""

    industry: str | None = Field(None, description="Industry to search in")
    product_description: str | None = Field(None, description="Product description")


class DetectedCompetitor(BaseModel):
    """A detected competitor."""

    name: str = Field(..., description="Competitor name")
    url: str | None = Field(None, description="Competitor website")
    description: str | None = Field(None, description="Brief description")


class CompetitorDetectResponse(BaseModel):
    """Response from competitor detection."""

    success: bool = Field(..., description="Whether detection succeeded")
    competitors: list[DetectedCompetitor] = Field(
        default_factory=list, description="Detected competitors"
    )
    error: str | None = Field(None, description="Error message if failed")


class MarketTrend(BaseModel):
    """A market trend."""

    trend: str = Field(..., description="Trend description")
    source: str | None = Field(None, description="Source name")
    source_url: str | None = Field(None, description="Source URL")


class TrendsRefreshRequest(BaseModel):
    """Request to refresh market trends."""

    industry: str | None = Field(None, description="Industry to search trends for")


class TrendsRefreshResponse(BaseModel):
    """Response from trends refresh."""

    success: bool = Field(..., description="Whether refresh succeeded")
    trends: list[MarketTrend] = Field(default_factory=list, description="Market trends")
    error: str | None = Field(None, description="Error message if failed")


@router.post(
    "/v1/context/competitors/detect",
    response_model=CompetitorDetectResponse,
    summary="Auto-detect competitors",
    description="""
    Automatically detect competitors using Tavily Search API.

    First checks if competitors were already detected during website enrichment.
    If not, uses Tavily to search G2, Capterra, and other review sites for
    high-quality competitor information.

    **Auto-save**: Detected competitors are automatically saved to Competitor Watch
    (up to the user's tier limit). Existing competitors are not duplicated.

    Returns a list of detected competitors with names, URLs, and descriptions.
    """,
)
async def detect_competitors(
    request: CompetitorDetectRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> CompetitorDetectResponse:
    """Detect competitors using Tavily Search API and auto-save to Competitor Watch."""
    import httpx

    try:
        user_id = extract_user_id(user)
        logger.info(f"Detecting competitors for user {user_id}")

        # Load user context
        context_data = load_user_context(user_id)

        # First, check if we already have enriched competitors
        if context_data:
            enriched_competitors = context_data.get("detected_competitors", [])
            if enriched_competitors and len(enriched_competitors) > 0:
                logger.info(f"Using {len(enriched_competitors)} pre-enriched competitors")
                detected = [
                    DetectedCompetitor(name=name, url=None, description=None)
                    for name in enriched_competitors[:10]
                ]
                # Auto-save pre-enriched competitors
                await _auto_save_competitors(user_id, detected)
                return CompetitorDetectResponse(
                    success=True,
                    competitors=detected,
                )

        # Get context for search
        company_name = context_data.get("company_name") if context_data else None
        industry = request.industry if request else None
        product_description = request.product_description if request else None

        if context_data:
            industry = industry or context_data.get("industry")
            product_description = product_description or context_data.get("product_description")

        if not company_name and not industry and not product_description:
            return CompetitorDetectResponse(
                success=False,
                competitors=[],
                error="Please complete the Overview tab first (company name, industry, or product description required).",
            )

        settings = get_settings()
        if not settings.tavily_api_key:
            return CompetitorDetectResponse(
                success=False,
                competitors=[],
                error="Tavily Search API not configured. Please try again later.",
            )

        # Build targeted search query for competitor discovery
        # Focus on review sites that list actual companies
        if company_name:
            search_query = f'"{company_name}" competitors alternatives'
        elif industry and product_description:
            search_query = f"best {industry} software companies {product_description[:50]}"
        else:
            search_query = f"top {industry or product_description[:80]} companies competitors"

        logger.info(f"Tavily competitor search: {search_query}")

        # Use Tavily Search API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": search_query,
                    "search_depth": "advanced",  # Better quality
                    "include_domains": [
                        "g2.com",
                        "capterra.com",
                        "trustradius.com",
                        "getapp.com",
                        "softwareadvice.com",
                        "alternativeto.net",
                    ],
                    "max_results": 10,
                },
            )
            response.raise_for_status()
            data = response.json()

        # Extract company names from results
        results = data.get("results", [])
        competitors = []
        seen_names = set()

        for result in results:
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("content", "")

            # Extract company name from title
            # G2/Capterra titles often like "Company Name Reviews 2025" or "Company Name vs Competitor"
            name = title.split(" Reviews")[0].split(" vs ")[0].split(" -")[0].split(" |")[0].strip()

            # Skip if it's our own company, generic terms, or duplicates
            if not name or len(name) < 2 or len(name) > 50:
                continue
            if company_name and name.lower() == company_name.lower():
                continue
            if name.lower() in seen_names:
                continue
            if any(
                skip in name.lower()
                for skip in [
                    "best",
                    "top",
                    "review",
                    "compare",
                    "alternative",
                    "software",
                    "2024",
                    "2025",
                    "guide",
                    "list",
                ]
            ):
                continue

            seen_names.add(name.lower())
            competitors.append(
                DetectedCompetitor(
                    name=name,
                    url=url,
                    description=content[:200] if content else None,
                )
            )

        if not competitors:
            return CompetitorDetectResponse(
                success=False,
                competitors=[],
                error="No competitors found. Try adding more context about your company or industry.",
            )

        # Auto-save detected competitors to Competitor Watch
        await _auto_save_competitors(user_id, competitors[:8])

        return CompetitorDetectResponse(
            success=True,
            competitors=competitors[:8],  # Return top 8 quality results
        )

    except httpx.HTTPError as e:
        logger.error(f"Tavily API error: {e}")
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error="Search service temporarily unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Competitor detection failed: {e}")
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error=f"Detection failed: {str(e)}",
        )


async def _auto_save_competitors(user_id: str, competitors: list[DetectedCompetitor]) -> None:
    """Auto-save detected competitors to competitor_profiles table.

    Respects tier limits and doesn't duplicate existing competitors.
    """
    if not competitors:
        return

    try:
        # Get user tier and limits
        tier_limits = {
            "free": {"max_competitors": 3, "data_depth": "basic"},
            "starter": {"max_competitors": 5, "data_depth": "standard"},
            "pro": {"max_competitors": 8, "data_depth": "deep"},
        }

        with db_session() as conn:
            with conn.cursor() as cur:
                # Get user's tier
                cur.execute(
                    "SELECT subscription_tier FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                tier = row["subscription_tier"] if row else "free"
                tier_config = tier_limits.get(tier, tier_limits["free"])

                # Get current competitor count and names
                cur.execute(
                    "SELECT name FROM competitor_profiles WHERE user_id = %s",
                    (user_id,),
                )
                existing = {row["name"].lower() for row in cur.fetchall()}
                current_count = len(existing)

                # Calculate how many we can add
                available_slots = tier_config["max_competitors"] - current_count
                if available_slots <= 0:
                    logger.info(
                        f"User {user_id} at competitor limit ({current_count}/{tier_config['max_competitors']})"
                    )
                    return

                # Add new competitors (up to available slots)
                added = 0
                for comp in competitors:
                    if added >= available_slots:
                        break
                    if comp.name.lower() in existing:
                        continue

                    cur.execute(
                        """
                        INSERT INTO competitor_profiles (user_id, name, website, tagline, data_depth)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (
                            user_id,
                            comp.name,
                            comp.url,
                            comp.description,
                            tier_config["data_depth"],
                        ),
                    )
                    if cur.rowcount > 0:
                        added += 1
                        existing.add(comp.name.lower())

                logger.info(f"Auto-saved {added} competitors for user {user_id}")

    except Exception as e:
        # Don't fail the main request if auto-save fails
        logger.error(f"Failed to auto-save competitors: {e}")


@router.post(
    "/v1/context/trends/refresh",
    response_model=TrendsRefreshResponse,
    summary="Refresh market trends",
    description="""
    Fetch current market trends for the user's industry using Brave Search API.

    Uses the industry from saved context or the request to search for
    recent trends and news.

    Returns a list of trends with sources.
    """,
)
async def refresh_trends(
    request: TrendsRefreshRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> TrendsRefreshResponse:
    """Refresh market trends using Brave Search."""
    try:
        user_id = extract_user_id(user)
        logger.info(f"Refreshing trends for user {user_id}")

        # Get industry from request or saved context
        industry = request.industry if request else None

        if not industry:
            context_data = load_user_context(user_id)
            if context_data:
                industry = context_data.get("industry")

        if not industry:
            return TrendsRefreshResponse(
                success=False,
                trends=[],
                error="No industry available. Please set your industry first.",
            )

        # Search for trends using Brave API
        import httpx

        settings = get_settings()
        if not settings.brave_api_key:
            return TrendsRefreshResponse(
                success=False,
                trends=[],
                error="Brave Search API not configured. Please try again later.",
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": settings.brave_api_key},
                params={
                    "q": f"{industry} industry trends 2025 insights market analysis",
                    "count": 10,
                    "freshness": "pw",  # Past week
                },
            )
            response.raise_for_status()
            data = response.json()

        # Extract trends from search results
        results = data.get("web", {}).get("results", [])
        trends = []

        for result in results[:5]:
            title = result.get("title", "")
            url = result.get("url", "")
            description = result.get("description", "")

            # Create trend from result
            if title and description:
                trends.append(
                    MarketTrend(
                        trend=f"{title}: {description[:150]}...",
                        source=result.get("profile", {}).get("name", "Web"),
                        source_url=url,
                    )
                )

        return TrendsRefreshResponse(
            success=True,
            trends=trends,
        )

    except Exception as e:
        logger.error(f"Trends refresh failed: {e}")
        return TrendsRefreshResponse(
            success=False,
            trends=[],
            error=f"Refresh failed: {str(e)}",
        )
