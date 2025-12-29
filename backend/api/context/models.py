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
        max_length=500,
        description="Business model (e.g., B2B SaaS, marketplace)",
        examples=["B2B SaaS"],
    )
    target_market: str | None = Field(
        None,
        max_length=1000,
        description="Target market description",
        examples=["Small businesses in North America"],
    )
    product_description: str | None = Field(
        None,
        max_length=2000,
        description="Product/service description",
        examples=["AI-powered project management tool"],
    )
    revenue: str | None = Field(
        None,
        max_length=200,
        description="Monthly/annual revenue",
        examples=["$50,000 MRR"],
    )
    customers: str | None = Field(
        None,
        max_length=200,
        description="Number of active customers",
        examples=["150"],
    )
    growth_rate: str | None = Field(
        None,
        max_length=200,
        description="Growth rate percentage",
        examples=["15% MoM"],
    )
    competitors: str | None = Field(
        None,
        max_length=2000,
        description="List of competitors (comma-separated or JSON)",
        examples=["Asana, Monday.com, Jira"],
    )
    website: str | None = Field(
        None,
        max_length=500,
        description="Website URL",
        examples=["https://example.com"],
    )

    # =========================================================================
    # New extended fields (Tier 3)
    # =========================================================================
    company_name: str | None = Field(
        None,
        max_length=200,
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
        max_length=200,
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
        max_length=200,
        description="Pricing model",
        examples=["Subscription", "Freemium", "Usage-based"],
    )
    brand_positioning: str | None = Field(
        None,
        max_length=1000,
        description="Brand positioning statement",
    )
    brand_tone: str | None = Field(
        None,
        max_length=200,
        description="Brand tone/voice",
        examples=["Professional", "Friendly", "Technical"],
    )
    brand_maturity: str | None = Field(
        None,
        max_length=100,
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
        max_length=2000,
        description="Ideal customer profile description",
    )
    keywords: list[str] | None = Field(
        None,
        description="Market category keywords",
    )
    target_geography: str | None = Field(
        None,
        max_length=500,
        description="Target geography",
        examples=["North America", "Global", "Europe"],
    )
    traffic_range: str | None = Field(
        None,
        max_length=50,
        description="Website traffic range",
        examples=["<1k", "1k-10k", "10k-100k", "100k+"],
    )
    mau_bucket: str | None = Field(
        None,
        max_length=50,
        description="Monthly active users bucket",
    )
    revenue_stage: str | None = Field(
        None,
        max_length=50,
        description="Revenue stage",
        examples=["pre-revenue", "early", "growth", "mature"],
    )
    main_value_proposition: str | None = Field(
        None,
        max_length=1000,
        description="Main value proposition",
    )
    team_size: str | None = Field(
        None,
        max_length=100,
        description="Team size",
        examples=["solo", "small (2-5)", "medium (6-20)", "large (20+)"],
    )
    budget_constraints: str | None = Field(
        None,
        max_length=500,
        description="Budget constraints",
    )
    time_constraints: str | None = Field(
        None,
        max_length=500,
        description="Time constraints",
    )
    regulatory_constraints: str | None = Field(
        None,
        max_length=1000,
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
    strategic_objectives: list[str] | None = Field(
        None,
        max_length=5,
        description="Supporting strategic objectives (up to 5) to complement the north star goal",
        examples=[["Increase conversion rate", "Reduce churn", "Expand to EU market"]],
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
        needs_competitor_refresh: Whether auto-detect should run for competitors
        competitor_count: Current number of managed competitors
    """

    exists: bool = Field(..., description="Whether user has saved context")
    context: BusinessContext | None = Field(None, description="Business context data")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    benchmark_timestamps: dict[str, datetime] | None = Field(
        None, description="Timestamps for when each benchmark metric was last set"
    )
    needs_competitor_refresh: bool = Field(
        False, description="Whether auto-detect should run for competitors"
    )
    competitor_count: int = Field(0, description="Current number of managed competitors")

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


class RelevanceFlags(BaseModel):
    """Relevance check flags for a detected competitor."""

    similar_product: bool = Field(False, description="Solves the same core problem")
    same_icp: bool = Field(False, description="Targets similar customer profile")
    same_market: bool = Field(False, description="Same geographic/market segment")


class DetectedCompetitor(BaseModel):
    """A detected competitor."""

    name: str = Field(..., description="Competitor name")
    url: str | None = Field(None, description="Competitor website")
    description: str | None = Field(None, description="Brief description")
    # Relevance scoring (populated by skeptic check)
    relevance_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score: 1.0=3 checks, 0.66=2, 0.33=1, 0.0=0",
    )
    relevance_flags: RelevanceFlags | None = Field(
        None,
        description="Individual relevance check results",
    )
    relevance_warning: str | None = Field(
        None,
        max_length=200,
        description="Warning message if <2 checks pass",
    )


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


# =============================================================================
# Competitor Insight Models
# =============================================================================


class CompetitorInsight(BaseModel):
    """Structured AI-generated insight about a competitor.

    Contains comprehensive analysis of competitor including:
    - Company identification and positioning
    - Size and revenue estimates
    - Strengths, weaknesses, and market gaps
    """

    name: str = Field(..., description="Competitor company name")
    tagline: str | None = Field(None, max_length=200, description="Company tagline/slogan")
    size_estimate: str | None = Field(
        None,
        max_length=100,
        description="Estimated company size (e.g., '50-200 employees')",
    )
    revenue_estimate: str | None = Field(
        None,
        max_length=100,
        description="Estimated revenue range (e.g., '$5M-20M ARR')",
    )
    strengths: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Key strengths (up to 5)",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Key weaknesses (up to 5)",
    )
    market_gaps: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Market gaps/opportunities (up to 5)",
    )
    last_updated: datetime | None = Field(None, description="When insight was last generated")


class CompetitorInsightRequest(BaseModel):
    """Request to generate insight for a single competitor."""

    competitor_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of competitor to analyze",
    )


class CompetitorInsightResponse(BaseModel):
    """Response from generating a single competitor insight."""

    success: bool = Field(..., description="Whether generation succeeded")
    insight: CompetitorInsight | None = Field(None, description="Generated insight")
    error: str | None = Field(None, description="Error message if failed")
    generation_status: str | None = Field(
        None,
        description="Status: 'complete', 'cached', 'limited_data'",
    )


class CompetitorInsightsListResponse(BaseModel):
    """Response containing list of competitor insights with tier gating.

    Tier limits:
    - Free: 1 visible insight
    - Starter: 3 visible insights
    - Pro: Unlimited insights
    """

    success: bool = Field(..., description="Whether retrieval succeeded")
    insights: list[CompetitorInsight] = Field(
        default_factory=list,
        description="List of competitor insights (tier-gated)",
    )
    visible_count: int = Field(0, description="Number of visible insights for tier")
    total_count: int = Field(0, description="Total number of cached insights")
    tier: str | None = Field(None, description="User's current tier")
    upgrade_prompt: str | None = Field(
        None,
        description="Upgrade prompt if limit reached",
    )
    error: str | None = Field(None, description="Error message if failed")


class GoalProgressResponse(BaseModel):
    """Response for goal progress tracking.

    Returns action completion stats for the last 30 days,
    useful for showing progress toward goals on the dashboard.
    """

    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of actions completed in period",
    )
    trend: Literal["up", "down", "stable"] = Field(
        ...,
        description="Trend compared to previous period",
    )
    completed_count: int = Field(0, description="Actions completed in period")
    total_count: int = Field(0, description="Total active actions in period")


# =============================================================================
# Trend Insight Models
# =============================================================================


class TrendInsight(BaseModel):
    """Structured AI-generated insight from a market trend URL.

    Contains actionable analysis of market trends including:
    - Key takeaway from the trend
    - Relevance to user's business
    - Recommended actions
    - Timeframe classification
    """

    url: str = Field(..., description="Original URL of the trend article")
    title: str | None = Field(None, max_length=200, description="Article title")
    key_takeaway: str | None = Field(
        None,
        max_length=500,
        description="The single most important insight from this trend",
    )
    relevance: str | None = Field(
        None,
        max_length=500,
        description="Why this trend matters for the user's business",
    )
    actions: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Recommended actions (2-3 items)",
    )
    timeframe: Literal["immediate", "short_term", "long_term"] | None = Field(
        None,
        description="When this trend is most relevant",
    )
    confidence: Literal["high", "medium", "low"] | None = Field(
        None,
        description="Confidence level of the analysis",
    )
    analyzed_at: datetime | None = Field(None, description="When insight was generated")


class TrendInsightRequest(BaseModel):
    """Request to analyze a single trend URL."""

    url: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="URL of the trend article to analyze",
    )


class TrendInsightResponse(BaseModel):
    """Response from analyzing a single trend URL."""

    success: bool = Field(..., description="Whether analysis succeeded")
    insight: TrendInsight | None = Field(None, description="Generated insight")
    error: str | None = Field(None, description="Error message if failed")
    analysis_status: str | None = Field(
        None,
        description="Status: 'complete', 'cached', 'limited_data', 'error'",
    )


class TrendInsightsListResponse(BaseModel):
    """Response containing list of trend insights.

    Rate limited to 3/min per user due to web fetching costs.
    """

    success: bool = Field(..., description="Whether retrieval succeeded")
    insights: list[TrendInsight] = Field(
        default_factory=list,
        description="List of trend insights",
    )
    count: int = Field(0, description="Number of cached insights")
    error: str | None = Field(None, description="Error message if failed")


# =============================================================================
# Managed Competitor Models (User-submitted competitors)
# =============================================================================


class ManagedCompetitor(BaseModel):
    """A user-managed competitor entry.

    Stores competitor name, optional URL and notes, and when it was added.
    Distinct from CompetitorInsight which is AI-generated analysis.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Competitor company name",
    )
    url: str | None = Field(
        None,
        max_length=500,
        description="Competitor website URL",
    )
    notes: str | None = Field(
        None,
        max_length=1000,
        description="User notes about the competitor",
    )
    added_at: datetime = Field(..., description="When competitor was added")


class ManagedCompetitorCreate(BaseModel):
    """Request to add a new managed competitor."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Competitor company name",
    )
    url: str | None = Field(
        None,
        max_length=500,
        description="Competitor website URL",
    )
    notes: str | None = Field(
        None,
        max_length=1000,
        description="User notes about the competitor",
    )


class ManagedCompetitorUpdate(BaseModel):
    """Request to update a managed competitor."""

    url: str | None = Field(
        None,
        max_length=500,
        description="Updated competitor website URL",
    )
    notes: str | None = Field(
        None,
        max_length=1000,
        description="Updated user notes",
    )


class ManagedCompetitorResponse(BaseModel):
    """Response for single managed competitor operations."""

    success: bool = Field(..., description="Whether operation succeeded")
    competitor: ManagedCompetitor | None = Field(None, description="Competitor data")
    error: str | None = Field(None, description="Error message if failed")
    relevance_warning: str | None = Field(
        None,
        max_length=200,
        description="Warning if competitor has low relevance (<2 checks pass)",
    )
    relevance_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score (0.0-1.0) if skeptic check ran",
    )


class ManagedCompetitorListResponse(BaseModel):
    """Response for listing managed competitors."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    competitors: list[ManagedCompetitor] = Field(
        default_factory=list,
        description="List of user-managed competitors",
    )
    count: int = Field(0, description="Number of competitors")
    error: str | None = Field(None, description="Error message if failed")


# =============================================================================
# Trend Summary Models (AI-generated industry summaries)
# =============================================================================


class TrendSummary(BaseModel):
    """AI-generated market trend summary for user's industry.

    Generated from Brave Search + Claude Haiku analysis.
    Refreshes every 7 days or when industry changes.
    Cost: ~$0.005/generation.
    """

    summary: str = Field(
        ...,
        max_length=1000,
        description="Executive summary of current market trends",
    )
    key_trends: list[str] = Field(
        default_factory=list,
        description="Top 3-5 key market trends",
    )
    opportunities: list[str] = Field(
        default_factory=list,
        description="2-4 identified opportunities",
    )
    threats: list[str] = Field(
        default_factory=list,
        description="2-4 identified threats/challenges",
    )
    generated_at: datetime = Field(..., description="When summary was generated")
    industry: str = Field(..., description="Industry the summary is for")
    timeframe: str = Field(
        default="3m",
        description="Forecast timeframe: 3m, 12m, or 24m",
    )
    available_timeframes: list[str] = Field(
        default_factory=lambda: ["3m"],
        description="Timeframes available to user's tier",
    )


class TrendSummaryResponse(BaseModel):
    """Response for trend summary endpoint."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    summary: TrendSummary | None = Field(None, description="Trend summary data")
    stale: bool = Field(False, description="Whether summary needs refresh (>7 days)")
    needs_industry: bool = Field(
        False,
        description="True if user has no industry set",
    )
    error: str | None = Field(None, description="Error message if failed")
    can_refresh_now: bool = Field(
        True,
        description="Whether refresh is allowed (free tier: only if >28 days old)",
    )
    refresh_blocked_reason: str | None = Field(
        None,
        description="Reason refresh is blocked (e.g., 'Refresh available in X days')",
    )


class TrendSummaryRefreshResponse(BaseModel):
    """Response from refreshing trend summary."""

    success: bool = Field(..., description="Whether refresh succeeded")
    summary: TrendSummary | None = Field(None, description="New trend summary")
    error: str | None = Field(None, description="Error message if failed")
    rate_limited: bool = Field(
        False,
        description="True if rate limit exceeded (1/hour)",
    )


class TrendForecastResponse(BaseModel):
    """Response for trend forecast endpoint with tier-gating."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    summary: TrendSummary | None = Field(None, description="Forecast data")
    timeframe: str = Field(default="3m", description="Requested timeframe")
    available_timeframes: list[str] = Field(
        default_factory=lambda: ["3m"],
        description="Timeframes available to user's tier",
    )
    stale: bool = Field(False, description="Whether forecast needs refresh (>7 days)")
    needs_industry: bool = Field(False, description="True if user has no industry set")
    upgrade_prompt: str | None = Field(
        None,
        description="Shown when user requests locked timeframe",
    )
    error: str | None = Field(None, description="Error message if failed")


class TrendForecastRefreshRequest(BaseModel):
    """Request to refresh a specific forecast timeframe."""

    timeframe: str = Field(
        default="3m",
        description="Timeframe to refresh: 3m, 12m, or 24m",
    )


# =============================================================================
# Goal History Models (North Star Goal Tracking)
# =============================================================================


class GoalHistoryEntry(BaseModel):
    """A single goal change in history."""

    goal_text: str = Field(..., description="The goal text")
    changed_at: datetime = Field(..., description="When this goal was set")
    previous_goal: str | None = Field(None, description="Previous goal before this change")


class GoalHistoryResponse(BaseModel):
    """Response for goal history endpoint."""

    entries: list[GoalHistoryEntry] = Field(
        default_factory=list,
        description="Goal history entries, newest first",
    )
    count: int = Field(0, description="Number of entries returned")


class GoalStalenessResponse(BaseModel):
    """Response for goal staleness check."""

    days_since_change: int | None = Field(
        None,
        description="Days since last goal change, or None if no history",
    )
    should_prompt: bool = Field(
        False,
        description="Whether to show 'Review your goal?' prompt (>30 days)",
    )
    last_goal: str | None = Field(None, description="Current/last goal text")


# =============================================================================
# Action Metric Trigger Models (28-day delayed staleness)
# =============================================================================


class ActionMetricTrigger(BaseModel):
    """Trigger for delayed metric staleness after action completion.

    When an action completes that targets a metric (e.g., "reduce churn"),
    we store a trigger that fires 28 days later to prompt metric refresh.
    """

    action_id: str = Field(..., description="ID of the completed action")
    action_title: str = Field(..., description="Title of the action for display")
    metric_field: str = Field(..., description="Context field to refresh (e.g., 'churn')")
    completed_at: datetime = Field(..., description="When the action was completed")
    trigger_at: datetime = Field(..., description="When to trigger staleness (completed_at + 28d)")


class ActionMetricTriggersResponse(BaseModel):
    """Response for listing action metric triggers."""

    triggers: list[ActionMetricTrigger] = Field(
        default_factory=list,
        description="Active triggers pending for metric refresh",
    )
    count: int = Field(0, description="Number of active triggers")


# =============================================================================
# Strategic Objective Progress Models
# =============================================================================


class ObjectiveProgress(BaseModel):
    """Progress data for a single strategic objective.

    Stores current and target values as flexible strings to support
    various formats (e.g., "$5K", "50%", "100 customers").
    """

    current: str = Field(
        ...,
        max_length=50,
        description="Current value (e.g., '$5K', '50%', '100')",
    )
    target: str = Field(
        ...,
        max_length=50,
        description="Target value (e.g., '$10K', '80%', '500')",
    )
    unit: str | None = Field(
        None,
        max_length=20,
        description="Optional unit label (e.g., 'MRR', '%', 'customers')",
    )
    updated_at: datetime = Field(..., description="When progress was last updated")


class ObjectiveProgressUpdate(BaseModel):
    """Request to update progress for a strategic objective."""

    current: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Current value",
    )
    target: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Target value",
    )
    unit: str | None = Field(
        None,
        max_length=20,
        description="Optional unit label",
    )


class ObjectiveProgressResponse(BaseModel):
    """Response for a single objective's progress."""

    objective_index: int = Field(..., description="Index of the objective (0-4)")
    objective_text: str = Field(..., description="Text of the objective")
    progress: ObjectiveProgress | None = Field(None, description="Progress data (null if not set)")


class ObjectiveProgressListResponse(BaseModel):
    """Response for listing all objective progress."""

    objectives: list[ObjectiveProgressResponse] = Field(
        default_factory=list, description="Progress for each objective"
    )
    count: int = Field(0, description="Number of objectives with progress set")


# =============================================================================
# Key Metrics Models (Metrics You Need to Know)
# =============================================================================


class MetricImportance(str, Enum):
    """Importance classification for key metrics."""

    NOW = "now"  # Focus on this metric immediately
    LATER = "later"  # Track for future focus
    MONITOR = "monitor"  # Keep an eye on, low priority


class MetricSourceCategory(str, Enum):
    """Source category for key metrics."""

    USER = "user"  # User's own metrics (revenue, customers, etc.)
    COMPETITOR = "competitor"  # Competitor comparison metrics
    INDUSTRY = "industry"  # Industry benchmark metrics


class KeyMetricConfig(BaseModel):
    """Configuration for a single key metric in user's dashboard.

    Stores user's prioritization and categorization of metrics they want to track.
    """

    metric_key: str = Field(
        ...,
        max_length=50,
        description="Metric identifier (e.g., 'revenue', 'customers', 'churn')",
    )
    importance: MetricImportance = Field(
        default=MetricImportance.MONITOR,
        description="Priority level: now, later, or monitor",
    )
    category: MetricSourceCategory = Field(
        default=MetricSourceCategory.USER,
        description="Source category: user, competitor, or industry",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Display order within importance bucket",
    )
    notes: str | None = Field(
        None,
        max_length=500,
        description="Optional user notes about this metric",
    )


class MetricTrendIndicator(str, Enum):
    """Direction of metric trend (pendulum indicator)."""

    UP = "up"  # Improving
    DOWN = "down"  # Declining
    STABLE = "stable"  # No significant change
    UNKNOWN = "unknown"  # Insufficient data


class KeyMetricDisplay(BaseModel):
    """Display model for a single key metric with current value and trends.

    Used to render metric cards in the UI.
    """

    metric_key: str = Field(..., description="Metric identifier")
    name: str = Field(..., max_length=100, description="Display name")
    value: str | float | int | None = Field(None, description="Current value")
    unit: str | None = Field(None, max_length=20, description="Unit (%, $, count)")
    trend: MetricTrendIndicator = Field(
        default=MetricTrendIndicator.UNKNOWN,
        description="Trend direction (pendulum)",
    )
    trend_change: str | None = Field(
        None,
        max_length=50,
        description="Human-readable change (e.g., '+15% MoM')",
    )
    importance: MetricImportance = Field(..., description="User's priority level")
    category: MetricSourceCategory = Field(..., description="Source category")
    benchmark_value: str | float | int | None = Field(
        None, description="Industry benchmark for comparison"
    )
    percentile: int | None = Field(
        None,
        ge=0,
        le=100,
        description="User's percentile vs industry (0-100)",
    )
    notes: str | None = Field(None, description="User notes")
    last_updated: datetime | None = Field(None, description="When value was last updated")


class KeyMetricConfigUpdate(BaseModel):
    """Request to update key metrics configuration."""

    metrics: list[KeyMetricConfig] = Field(
        ...,
        max_length=20,
        description="Updated list of key metric configurations",
    )


class KeyMetricsResponse(BaseModel):
    """Response containing user's key metrics with current values and trends."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    metrics: list[KeyMetricDisplay] = Field(
        default_factory=list,
        description="Key metrics with values and trends, sorted by importance",
    )
    now_count: int = Field(0, description="Number of 'now' priority metrics")
    later_count: int = Field(0, description="Number of 'later' priority metrics")
    monitor_count: int = Field(0, description="Number of 'monitor' priority metrics")
    error: str | None = Field(None, description="Error message if failed")


class KeyMetricSuggestion(BaseModel):
    """AI-suggested key metric with reasoning."""

    metric_key: str = Field(..., description="Suggested metric identifier")
    name: str = Field(..., description="Display name")
    importance: MetricImportance = Field(..., description="Suggested priority")
    category: MetricSourceCategory = Field(..., description="Source category")
    reasoning: str = Field(..., max_length=300, description="Why this metric matters")


class KeyMetricsSuggestResponse(BaseModel):
    """Response from AI metric suggestion."""

    success: bool = Field(..., description="Whether suggestion succeeded")
    suggestions: list[KeyMetricSuggestion] = Field(
        default_factory=list,
        description="Suggested metrics based on context (5-7 items)",
    )
    error: str | None = Field(None, description="Error message if failed")


# =============================================================================
# Working Pattern Models (Activity Heatmap)
# =============================================================================


class WorkingPattern(BaseModel):
    """User's regular working pattern for activity visualization.

    Stores which days of the week the user typically works.
    Non-working days are greyed out in ActivityHeatmap.
    """

    working_days: list[int] = Field(
        default=[1, 2, 3, 4, 5],
        description="Working days as ISO weekday numbers (1=Mon, 7=Sun). Default: Mon-Fri",
    )

    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        """Validate and normalize working days."""
        if not v:
            return [1, 2, 3, 4, 5]  # Default to Mon-Fri
        # Filter to valid days (1-7) and deduplicate
        valid_days = sorted({d for d in v if 1 <= d <= 7})
        if not valid_days:
            return [1, 2, 3, 4, 5]  # Default if all invalid
        return valid_days

    def model_post_init(self, __context: Any) -> None:
        """Normalize working days after initialization."""
        self.working_days = self.validate_days(self.working_days)


class WorkingPatternResponse(BaseModel):
    """Response for working pattern endpoint."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    pattern: WorkingPattern = Field(
        default_factory=WorkingPattern,
        description="User's working pattern (defaults to Mon-Fri)",
    )
    error: str | None = Field(None, description="Error message if failed")


class WorkingPatternUpdate(BaseModel):
    """Request to update working pattern."""

    working_days: list[int] = Field(
        ...,
        min_length=1,
        max_length=7,
        description="Working days as ISO weekday numbers (1=Mon, 7=Sun). At least one day required.",
    )


# =============================================================================
# Heatmap History Depth Models
# =============================================================================


class HeatmapHistoryDepth(BaseModel):
    """User's preferred activity heatmap history depth.

    Controls how many months of history are shown in the ActivityHeatmap.
    """

    history_months: Literal[1, 3, 6] = Field(
        default=3,
        description="History depth in months: 1, 3, or 6. Default: 3",
    )


class HeatmapHistoryDepthResponse(BaseModel):
    """Response for heatmap history depth endpoint."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    depth: HeatmapHistoryDepth = Field(
        default_factory=HeatmapHistoryDepth,
        description="User's heatmap history depth preference (defaults to 3 months)",
    )
    error: str | None = Field(None, description="Error message if failed")


class HeatmapHistoryDepthUpdate(BaseModel):
    """Request to update heatmap history depth."""

    history_months: Literal[1, 3, 6] = Field(
        ...,
        description="History depth in months: 1, 3, or 6",
    )


# =============================================================================
# Research Embeddings Visualization Models
# =============================================================================


class ResearchPoint(BaseModel):
    """A single point in the research embeddings visualization."""

    x: float = Field(..., description="X coordinate (PCA reduced)")
    y: float = Field(..., description="Y coordinate (PCA reduced)")
    preview: str = Field(..., max_length=150, description="First ~100 chars of question")
    category: str | None = Field(None, description="Research category (e.g., 'saas_metrics')")
    created_at: str = Field(..., description="ISO datetime when research was created")


class ResearchCategory(BaseModel):
    """Category summary for legend display."""

    name: str = Field(..., description="Category name")
    count: int = Field(..., ge=0, description="Number of research items in category")


class ResearchEmbeddingsResponse(BaseModel):
    """Response containing user's research embeddings for visualization."""

    success: bool = Field(..., description="Whether retrieval succeeded")
    points: list[ResearchPoint] = Field(
        default_factory=list,
        description="2D coordinates with metadata for scatter plot",
    )
    categories: list[ResearchCategory] = Field(
        default_factory=list,
        description="Category counts for legend",
    )
    total_count: int = Field(0, description="Total research items (may exceed points if > limit)")
    error: str | None = Field(None, description="Error message if failed")
