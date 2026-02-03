"""Dataset objective analysis models for Board of One.

Pydantic models for the Data Analysis Reimagination feature, supporting
objective-aligned analysis results, relevance assessment, data stories,
and insights.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from bo1.models.util import (
    FromDbRowMixin,
    coerce_enum,
    normalize_uuid,
    normalize_uuid_required,
)

# --- Enums ---


class AnalysisMode(str, Enum):
    """Analysis mode for dataset analysis."""

    OBJECTIVE_FOCUSED = "objective_focused"
    OPEN_EXPLORATION = "open_exploration"


class RelevanceLevel(str, Enum):
    """Relevance level for objective matching."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ConfidenceLevel(str, Enum):
    """Confidence level for insights."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ChartType(str, Enum):
    """Chart type for visualizations."""

    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    PIE = "pie"


class DataPriority(str, Enum):
    """Priority level for valuable data additions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# --- Relevance Assessment Models ---


class ObjectiveMatch(BaseModel):
    """Match assessment between dataset and a specific objective."""

    objective_id: str | None = Field(None, description="Objective UUID if linked")
    objective_name: str = Field(..., description="Name of the objective")
    relevance: RelevanceLevel = Field(..., description="Relevance level")
    explanation: str = Field(..., description="Why the data helps or doesn't help")
    answerable_questions: list[str] = Field(
        default_factory=list, description="Questions the data CAN answer"
    )
    unanswerable_questions: list[str] = Field(
        default_factory=list, description="Questions the data CANNOT answer"
    )

    model_config = ConfigDict(from_attributes=True)


class MissingData(BaseModel):
    """Data that would strengthen the analysis if available."""

    data_needed: str = Field(..., description="What data is missing")
    why_valuable: str = Field(..., description="How it would help the analysis")
    objectives_unlocked: list[str] = Field(
        default_factory=list, description="Which objectives this would serve"
    )

    model_config = ConfigDict(from_attributes=True)


class RelevanceAssessment(BaseModel):
    """Full relevance assessment for a dataset against user objectives."""

    relevance_score: int = Field(..., ge=0, le=100, description="Overall relevance score 0-100")
    assessment_summary: str = Field(..., description="2-3 sentence summary of dataset fit")
    objective_matches: list[ObjectiveMatch] = Field(
        default_factory=list, description="Per-objective relevance assessment"
    )
    missing_data: list[MissingData] = Field(
        default_factory=list, description="Data that would strengthen analysis"
    )
    recommended_focus: str = Field(..., description="Where to focus the analysis given limitations")

    model_config = ConfigDict(from_attributes=True)


# --- Insight Models ---


class InsightVisualization(BaseModel):
    """Visualization configuration for an insight."""

    type: ChartType = Field(..., description="Chart type")
    x_axis: str | None = Field(None, description="X-axis column")
    y_axis: str | None = Field(None, description="Y-axis column")
    group_by: str | None = Field(None, description="Grouping column")
    title: str = Field(..., description="Chart title")
    figure_json: dict[str, Any] | None = Field(None, description="Plotly figure spec for rendering")

    model_config = ConfigDict(from_attributes=True)


class BenchmarkComparison(BaseModel):
    """Comparison of a metric to industry benchmark."""

    metric_name: str = Field(..., description="Name of the metric being compared")
    your_value: float = Field(..., description="Your actual value")
    industry_median: float | None = Field(None, description="Industry median value")
    industry_top_quartile: float | None = Field(None, description="Top quartile value")
    performance: str = Field(
        ..., description="Performance level: top_performer, above_average, average, below_average"
    )
    gap_to_median: float | None = Field(None, description="Gap from your value to median")
    gap_to_top: float | None = Field(None, description="Gap from your value to top quartile")
    unit: str = Field(default="", description="Unit of measurement")

    model_config = ConfigDict(from_attributes=True)


class ImpactModel(BaseModel):
    """Modeled impact of a proposed change."""

    scenario: str = Field(..., description="Description of the improvement scenario")
    monthly_impact: float = Field(..., description="Monthly revenue/savings impact")
    annual_impact: float = Field(..., description="Annual revenue/savings impact")
    narrative: str = Field(..., description="Human-readable impact description")
    assumptions: list[str] = Field(default_factory=list, description="Assumptions made in model")

    model_config = ConfigDict(from_attributes=True)


class Insight(BaseModel):
    """Single insight generated from analysis."""

    id: str = Field(..., description="Unique insight identifier")
    objective_id: str | None = Field(None, description="Linked objective UUID")
    objective_name: str | None = Field(None, description="Linked objective name")
    headline: str = Field(..., max_length=100, description="Key finding in 10 words max")
    narrative: str = Field(..., description="2-4 sentences explaining the insight")
    supporting_data: dict[str, Any] = Field(
        default_factory=dict, description="Key metrics and comparisons"
    )
    visualization: InsightVisualization | None = Field(
        None, description="Recommended chart configuration"
    )
    recommendation: str = Field(..., description="Specific action to take")
    follow_up_questions: list[str] = Field(default_factory=list, description="What to explore next")
    confidence: ConfidenceLevel = Field(..., description="Confidence level")
    benchmark_comparison: BenchmarkComparison | None = Field(
        None, description="Industry benchmark comparison"
    )
    impact_model: ImpactModel | None = Field(None, description="Modeled impact of improvement")
    industry_context: str | None = Field(None, description="Additional industry context")

    model_config = ConfigDict(from_attributes=True)


# --- Data Story Models ---


class ObjectiveSection(BaseModel):
    """Section of data story focused on a specific objective."""

    objective_id: str | None = Field(None, description="Objective UUID if linked")
    objective_name: str = Field(..., description="Name of the objective")
    summary: str = Field(..., description="2-3 sentences synthesizing insights")
    insight_ids: list[str] = Field(default_factory=list, description="Linked insight IDs")
    key_metric: str = Field(..., description="The most important number")
    recommended_action: str = Field(..., description="What to do")

    model_config = ConfigDict(from_attributes=True)


class UnexpectedFinding(BaseModel):
    """Something interesting not directly related to objectives."""

    headline: str = Field(..., description="What was found")
    narrative: str = Field(..., description="Why it might matter")
    should_investigate: bool = Field(..., description="Whether to explore further")

    model_config = ConfigDict(from_attributes=True)


class DataStory(BaseModel):
    """AI-generated narrative from analysis results."""

    opening_hook: str = Field(
        ..., description="1 sentence capturing attention, references North Star"
    )
    objective_sections: list[ObjectiveSection] = Field(
        default_factory=list, description="Insights grouped by objective"
    )
    data_quality_summary: str = Field(..., description="Honest assessment of data limitations")
    unexpected_finding: UnexpectedFinding | None = Field(
        None, description="Something interesting not in objectives"
    )
    next_steps: list[str] = Field(default_factory=list, description="Prioritized actions to take")
    suggested_questions: list[str] = Field(
        default_factory=list, description="Questions derived from objectives + data"
    )

    model_config = ConfigDict(from_attributes=True)


# --- Data Requirements Models (for "What Data Do I Need?" feature) ---


class EssentialData(BaseModel):
    """Data required for meaningful analysis of an objective."""

    name: str = Field(..., description="Data type name")
    description: str = Field(..., description="What this data represents")
    example_columns: list[str] = Field(default_factory=list, description="Example column names")
    why_essential: str = Field(..., description="Why analysis fails without this")
    questions_answered: list[str] = Field(
        default_factory=list, description="What questions this enables"
    )

    model_config = ConfigDict(from_attributes=True)


class ValuableAddition(BaseModel):
    """Data that would strengthen but isn't required for analysis."""

    name: str = Field(..., description="Data type name")
    description: str = Field(..., description="What this data represents")
    insight_unlocked: str = Field(..., description="What additional insight this provides")
    priority: DataPriority = Field(..., description="How valuable this addition is")

    model_config = ConfigDict(from_attributes=True)


class DataSource(BaseModel):
    """Suggested source for obtaining data."""

    source_type: str = Field(..., description="CRM, Analytics, Billing, etc.")
    example_tools: list[str] = Field(
        default_factory=list, description="Tool names like Salesforce, Stripe"
    )
    typical_export_name: str = Field(..., description="Common export/report name")
    columns_typically_included: list[str] = Field(
        default_factory=list, description="Columns usually in this export"
    )

    model_config = ConfigDict(from_attributes=True)


class DataRequirements(BaseModel):
    """Full data requirements guide for analyzing an objective."""

    objective_summary: str = Field(
        ..., description="1 sentence restating what we're trying to analyze"
    )
    essential_data: list[EssentialData] = Field(
        default_factory=list, description="Data required for analysis"
    )
    valuable_additions: list[ValuableAddition] = Field(
        default_factory=list, description="Data that would strengthen analysis"
    )
    data_sources: list[DataSource] = Field(
        default_factory=list, description="Where to find the data"
    )
    analysis_preview: str = Field(..., description="2-3 sentences describing possible insights")

    model_config = ConfigDict(from_attributes=True)


# --- Main Analysis Model ---


class DatasetObjectiveAnalysis(BaseModel):
    """Full objective-aligned analysis result for a dataset.

    Stores the complete analysis including relevance assessment,
    data story, and insights linked to user objectives.
    """

    id: str = Field(..., description="Analysis UUID")
    dataset_id: str = Field(..., description="Dataset UUID")
    user_id: str = Field(..., description="User UUID")
    analysis_mode: AnalysisMode = Field(..., description="Analysis mode used")
    relevance_score: int | None = Field(None, ge=0, le=100, description="Overall relevance")
    relevance_assessment: RelevanceAssessment | None = Field(
        None, description="Full relevance assessment"
    )
    data_story: DataStory | None = Field(None, description="Generated data narrative")
    insights: list[Insight] = Field(default_factory=list, description="Generated insights")
    context_snapshot: dict[str, Any] | None = Field(
        None, description="Business context at analysis time"
    )
    selected_objective_id: str | None = Field(
        None, description="Pre-selected objective from 'What Data Do I Need?' flow"
    )
    created_at: datetime = Field(..., description="Analysis creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "dataset_id": "456e7890-e89b-12d3-a456-426614174001",
                    "user_id": "789a0123-e89b-12d3-a456-426614174002",
                    "analysis_mode": "objective_focused",
                    "relevance_score": 85,
                }
            ]
        },
    )

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "DatasetObjectiveAnalysis":
        """Create DatasetObjectiveAnalysis from database row dict.

        Args:
            row: Dict from psycopg2 cursor with analysis columns

        Returns:
            DatasetObjectiveAnalysis instance with validated data
        """
        # Parse JSONB fields
        relevance_assessment = None
        if row.get("relevance_assessment"):
            relevance_assessment = RelevanceAssessment.model_validate(row["relevance_assessment"])

        data_story = None
        if row.get("data_story"):
            data_story = DataStory.model_validate(row["data_story"])

        insights = []
        if row.get("insights"):
            insights = [Insight.model_validate(i) for i in row["insights"]]

        return cls(
            id=normalize_uuid_required(row["id"]),
            dataset_id=normalize_uuid_required(row["dataset_id"]),
            user_id=normalize_uuid_required(row["user_id"]),
            analysis_mode=coerce_enum(row["analysis_mode"], AnalysisMode),
            relevance_score=row.get("relevance_score"),
            relevance_assessment=relevance_assessment,
            data_story=data_story,
            insights=insights,
            context_snapshot=row.get("context_snapshot"),
            selected_objective_id=normalize_uuid(row.get("selected_objective_id")),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class InsightObjectiveLink(FromDbRowMixin):
    """Link between an insight and an objective for tracking."""

    id: str = Field(..., description="Link UUID")
    insight_id: str = Field(..., description="Insight ID from insights JSONB")
    analysis_id: str = Field(..., description="Parent analysis UUID")
    objective_id: str | None = Field(None, description="Linked objective UUID")
    objective_name: str | None = Field(None, description="Objective name")
    relevance_score: int | None = Field(None, description="Relevance to objective")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)
