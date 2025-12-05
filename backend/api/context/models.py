"""Pydantic models and enums for context management.

Contains all data models used by the context API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


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


class RefreshCheckResponse(BaseModel):
    """Response for refresh check endpoint."""

    needs_refresh: bool = Field(..., description="Whether context needs refreshing")
    last_updated: datetime | None = Field(None, description="When context was last updated")
    days_since_update: int | None = Field(None, description="Days since last update")


# =============================================================================
# Phase 3: Strategic Context Models
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
