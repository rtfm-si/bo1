"""Pydantic models and enums for context management.

Contains all data models used by the context API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, RootModel


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

    # Goals
    north_star_goal: str | None = Field(
        None,
        max_length=200,
        description="Primary objective for next 3-6 months (e.g., '10K MRR by Q2')",
        examples=["10K MRR by Q2", "100 paying customers by March"],
    )

    # Onboarding
    onboarding_completed: bool | None = Field(
        None,
        description="Whether user has completed onboarding checklist",
    )

    # Benchmark timestamps - tracks when each metric was last set/updated
    benchmark_timestamps: dict[str, datetime] | None = Field(
        None,
        description="Timestamps for when each benchmark metric was last set",
        examples=[{"revenue": "2025-01-15T12:00:00Z", "customers": "2025-01-10T09:30:00Z"}],
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
        benchmark_timestamps: When each benchmark metric was last set
    """

    exists: bool = Field(..., description="Whether user has saved context")
    context: BusinessContext | None = Field(None, description="Business context data")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    benchmark_timestamps: dict[str, datetime] | None = Field(
        None, description="Timestamps for when each benchmark metric was last set"
    )

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


class StaleFieldSummary(BaseModel):
    """Summary of a stale field for refresh banner."""

    field_name: str = Field(..., description="Context field name (e.g., 'revenue')")
    display_name: str = Field(..., description="Human-readable display name")
    volatility: str = Field(..., description="Volatility level: volatile, moderate, stable")
    days_since_update: int = Field(..., description="Days since last update")
    action_affected: bool = Field(False, description="Whether related to recent action")


class RefreshCheckResponse(BaseModel):
    """Response for refresh check endpoint."""

    needs_refresh: bool = Field(..., description="Whether context needs refreshing")
    last_updated: datetime | None = Field(None, description="When context was last updated")
    days_since_update: int | None = Field(None, description="Days since last update")
    stale_metrics: list[StaleFieldSummary] = Field(
        default_factory=list, description="Stale fields with volatility info"
    )
    highest_urgency: str | None = Field(
        None, description="Highest urgency level: action_affected, volatile, moderate, stable"
    )


class DismissRefreshRequest(BaseModel):
    """Request to dismiss refresh prompt with volatility context."""

    volatility: str = Field(
        default="moderate",
        description="Volatility level to set dismiss expiry: volatile=7d, moderate=30d, stable=90d",
    )


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


# =============================================================================
# Phase 4: Insights Models (Clarifications from Meetings)
# =============================================================================


class InsightCategory(str, Enum):
    """Business insight categories."""

    REVENUE = "revenue"
    GROWTH = "growth"
    CUSTOMERS = "customers"
    TEAM = "team"
    PRODUCT = "product"
    OPERATIONS = "operations"
    MARKET = "market"
    COMPETITION = "competition"
    FUNDING = "funding"
    COSTS = "costs"
    UNCATEGORIZED = "uncategorized"


class InsightMetricResponse(BaseModel):
    """Extracted metric from insight."""

    value: float | None = Field(None, description="Numeric value (e.g., 25000)")
    unit: str | None = Field(None, description="Unit: USD, %, count, etc.")
    metric_type: str | None = Field(None, description="Type: MRR, ARR, churn, headcount, etc.")
    period: str | None = Field(None, description="Period: monthly, yearly, quarterly, etc.")
    raw_text: str | None = Field(None, description="Original metric text")


class ClarificationInsight(BaseModel):
    """A clarification answer from a meeting.

    Captures user responses to clarifying questions asked during meetings.
    These insights are accumulated over time and help improve future meetings.
    """

    question: str = Field(..., description="The clarifying question that was asked")
    answer: str = Field(..., description="User's answer to the question")
    answered_at: datetime | None = Field(None, description="When the answer was provided")
    session_id: str | None = Field(None, description="Meeting ID where this was answered")
    # Structured fields (populated by Haiku parsing)
    category: InsightCategory | None = Field(None, description="Business category")
    metric: InsightMetricResponse | None = Field(None, description="Extracted metric data")
    confidence_score: float | None = Field(None, ge=0.0, le=1.0, description="Parse confidence")
    summary: str | None = Field(None, description="Brief one-line summary")
    key_entities: list[str] | None = Field(None, description="Mentioned entities")
    parsed_at: datetime | None = Field(None, description="When parsing occurred")


class UpdateInsightRequest(BaseModel):
    """Request to update a clarification insight.

    Allows users to edit their answer to a clarifying question and optionally
    add a note explaining the update.
    """

    value: str = Field(..., description="Updated answer to the clarifying question")
    note: str | None = Field(None, description="Optional note about why the answer was updated")


class InsightsResponse(BaseModel):
    """Response containing user's accumulated insights from meetings.

    Insights are derived from:
    - Clarification questions answered during meetings
    - Future: Key decisions, preferences learned over time
    """

    clarifications: list[ClarificationInsight] = Field(
        default_factory=list, description="Clarification Q&A from meetings"
    )
    total_count: int = Field(0, description="Total number of insights")


# =============================================================================
# Phase 6: Context Auto-Update Models
# =============================================================================


class ContextUpdateSource(str, Enum):
    """Source of context update."""

    CLARIFICATION = "clarification"
    PROBLEM_STATEMENT = "problem_statement"
    ACTION = "action"


class ContextUpdateSuggestion(BaseModel):
    """A pending context update suggestion requiring user approval.

    Created when confidence < 80%. User can approve or dismiss.
    """

    id: str = Field(..., description="Unique identifier for this suggestion")
    field_name: str = Field(..., description="Context field to update")
    new_value: str | float | int | list[str] = Field(..., description="Proposed new value")
    current_value: str | float | int | list[str] | None = Field(
        None, description="Current field value"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence (0-1)")
    source_type: ContextUpdateSource = Field(..., description="Where update was detected")
    source_text: str = Field(..., description="Original text containing the update")
    extracted_at: datetime = Field(..., description="When this was extracted")
    session_id: str | None = Field(None, description="Related session ID if from meeting")


class PendingUpdatesResponse(BaseModel):
    """Response for pending context update suggestions."""

    suggestions: list[ContextUpdateSuggestion] = Field(
        default_factory=list, description="Pending update suggestions"
    )
    count: int = Field(0, description="Number of pending suggestions")


class ApproveUpdateRequest(BaseModel):
    """Request to approve a pending update suggestion."""

    pass  # No body needed, ID is in URL path


class ApproveUpdateResponse(BaseModel):
    """Response after approving a pending update."""

    success: bool = Field(..., description="Whether update was applied")
    field_name: str = Field(..., description="Field that was updated")
    new_value: Any = Field(..., description="Value that was applied")


class MetricHistoryEntry(BaseModel):
    """A single historical value for a metric."""

    value: str | float | int = Field(..., description="The value at this point in time")
    recorded_at: datetime = Field(..., description="When this value was recorded")
    source_type: ContextUpdateSource = Field(..., description="Source of this value")
    source_id: str | None = Field(None, description="Session or action ID if applicable")


class MetricHistory(BaseModel):
    """Historical values for a context metric."""

    field_name: str = Field(..., description="Context field name")
    history: list[MetricHistoryEntry] = Field(
        default_factory=list, description="Historical values (newest first)"
    )


class TrendDirection(str, Enum):
    """Direction of metric trend."""

    IMPROVING = "improving"
    WORSENING = "worsening"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class MetricTrend(BaseModel):
    """Trend information for a context metric."""

    field_name: str = Field(..., description="Context field name")
    direction: TrendDirection = Field(..., description="Trend direction")
    current_value: str | float | int | None = Field(None, description="Current value")
    previous_value: str | float | int | None = Field(
        None, description="Previous value for comparison"
    )
    change_percent: float | None = Field(None, description="Percentage change if calculable")
    period_description: str | None = Field(
        None, description="Human description like 'since last month'"
    )


class ContextWithTrends(BaseModel):
    """Business context with trend indicators for metrics."""

    context: BusinessContext = Field(..., description="Current business context")
    trends: list[MetricTrend] = Field(
        default_factory=list, description="Trends for metrics with history"
    )
    updated_at: datetime | None = Field(None, description="Last context update")


# =============================================================================
# Clarification Storage Validation Models
# =============================================================================


ClarificationSource = Literal["meeting", "manual", "migration"]


class ClarificationStorageEntry(BaseModel):
    """Validated structure for a single clarification entry stored in JSONB.

    This model ensures consistent structure for clarification data before
    persisting to the database. Handles both new entries and legacy formats.
    """

    answer: str = Field(..., min_length=1, description="User's answer (required)")
    answered_at: datetime | None = Field(None, description="When answer was provided")
    session_id: str | None = Field(None, description="Meeting session ID if applicable")
    source: ClarificationSource = Field(default="meeting", description="Source of clarification")
    # Structured parsing fields (populated by Haiku)
    category: InsightCategory | None = Field(None, description="Business category")
    metric: InsightMetricResponse | None = Field(None, description="Extracted metric")
    confidence_score: Annotated[float | None, Field(ge=0.0, le=1.0)] = Field(
        None, description="Parse confidence 0-1"
    )
    summary: str | None = Field(None, description="Brief one-line summary")
    key_entities: list[str] | None = Field(None, description="Mentioned entities")
    parsed_at: datetime | None = Field(None, description="When parsing occurred")
    # Update tracking
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    update_note: str | None = Field(None, description="Note for manual updates")


class ClarificationsStorage(RootModel[dict[str, ClarificationStorageEntry]]):
    """Validated storage model for the entire clarifications JSONB field.

    Maps question text (str) to ClarificationStorageEntry.
    Use model_validate() to validate raw dicts from DB before processing.
    """

    pass


# =============================================================================
# Stale Metrics Detection Models
# =============================================================================


class VolatilityLevel(str, Enum):
    """Metric volatility classification for refresh scheduling."""

    STABLE = "stable"
    MODERATE = "moderate"
    VOLATILE = "volatile"


class StalenessReason(str, Enum):
    """Reason why a metric is considered stale."""

    AGE = "age"
    ACTION_AFFECTED = "action_affected"
    VOLATILITY = "volatility"


class StaleMetricResponse(BaseModel):
    """A stale business context metric requiring user refresh."""

    field_name: str = Field(..., description="Context field name (e.g., 'revenue')")
    current_value: str | float | int | None = Field(None, description="Current stored value")
    updated_at: datetime | None = Field(None, description="When the metric was last updated")
    days_since_update: int = Field(..., description="Days since last update")
    reason: StalenessReason = Field(..., description="Why this metric is stale")
    volatility: VolatilityLevel = Field(..., description="Volatility classification")
    threshold_days: int = Field(..., description="Staleness threshold for this metric")
    action_id: str | None = Field(None, description="Related action ID if action-affected")


class StaleMetricsResponse(BaseModel):
    """Response for stale metrics check endpoint."""

    has_stale_metrics: bool = Field(..., description="Whether any metrics are stale")
    stale_metrics: list[StaleMetricResponse] = Field(
        default_factory=list, description="List of stale metrics (max 3)"
    )
    total_metrics_checked: int = Field(..., description="Total number of metrics checked")
