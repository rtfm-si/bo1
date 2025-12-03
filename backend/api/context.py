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

        # Parse into BusinessContext
        context = BusinessContext(
            business_model=context_data.get("business_model"),
            target_market=context_data.get("target_market"),
            product_description=context_data.get("product_description"),
            revenue=context_data.get("revenue"),
            customers=context_data.get("customers"),
            growth_rate=context_data.get("growth_rate"),
            competitors=context_data.get("competitors"),
            website=context_data.get("website"),
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

        # Convert to dict for save function
        context_dict = {
            "business_model": context.business_model,
            "target_market": context.target_market,
            "product_description": context.product_description,
            "revenue": context.revenue,
            "customers": context.customers,
            "growth_rate": context.growth_rate,
            "competitors": context.competitors,
            "website": context.website,
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

    The enriched data can then be saved using PUT /v1/context.
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
    """Enrich business context from website URL."""
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
