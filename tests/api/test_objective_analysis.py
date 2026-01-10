"""Tests for objective analysis API endpoints.

Tests for:
- GET /api/v1/objectives/data-requirements - returns objectives list
- GET /api/v1/objectives/{index}/data-requirements - returns requirements for specific objective
- POST /api/v1/datasets/{id}/analyze - triggers analysis
- GET /api/v1/datasets/{id}/objective-analysis - returns analysis results
- POST /api/v1/datasets/{id}/fix - applies data cleaning
"""

import uuid
from datetime import UTC, datetime

from backend.api.routes.dataset_objective_analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    ObjectiveAnalysisResponse,
)
from backend.api.routes.objective_data_requirements import (
    AllObjectivesRequirementsResponse,
    ObjectiveDataRequirementsResponse,
)


class TestAllObjectivesDataRequirements:
    """Tests for GET /api/v1/objectives/data-requirements."""

    def test_response_model_has_required_fields(self):
        """Test AllObjectivesRequirementsResponse has required fields."""
        response = AllObjectivesRequirementsResponse(
            objectives=[],
            count=0,
            north_star_goal=None,
        )
        assert response.objectives == []
        assert response.count == 0
        assert response.north_star_goal is None

    def test_response_with_objectives(self):
        """Test response with multiple objectives."""
        from backend.api.routes.objective_data_requirements import (
            ObjectiveRequirementsSummary,
        )

        response = AllObjectivesRequirementsResponse(
            objectives=[
                ObjectiveRequirementsSummary(
                    index=0,
                    name="Increase customer retention by 20%",
                    requirements_summary="Customer activity data, subscription history",
                    essential_data_count=4,
                ),
                ObjectiveRequirementsSummary(
                    index=1,
                    name="Grow MRR to $100K",
                    requirements_summary="Transaction data with amounts and dates",
                    essential_data_count=3,
                ),
            ],
            count=2,
            north_star_goal="Build a sustainable SaaS business",
        )
        assert len(response.objectives) == 2
        assert response.count == 2
        assert response.north_star_goal == "Build a sustainable SaaS business"
        assert response.objectives[0].index == 0
        assert response.objectives[1].essential_data_count == 3


class TestObjectiveDataRequirements:
    """Tests for GET /api/v1/objectives/{index}/data-requirements."""

    def test_response_model_has_required_fields(self):
        """Test ObjectiveDataRequirementsResponse has required fields."""
        from backend.api.routes.objective_data_requirements import ObjectiveSummary
        from bo1.models.dataset_objective_analysis import DataRequirements

        response = ObjectiveDataRequirementsResponse(
            objective=ObjectiveSummary(
                index=0,
                name="Reduce customer churn",
                has_progress=True,
                current_value="5%",
                target_value="3%",
            ),
            requirements=DataRequirements(
                objective_summary="Analyze customer behavior to reduce churn",
                essential_data=[],
                valuable_additions=[],
                data_sources=[],
                analysis_preview="Expected insights from this analysis",
            ),
            generated_at=datetime.now(UTC),
            model_used="claude-3-5-sonnet-20241022",
        )
        assert response.objective.index == 0
        assert response.objective.name == "Reduce customer churn"
        assert response.objective.has_progress is True
        assert response.model_used == "claude-3-5-sonnet-20241022"

    def test_objective_without_progress(self):
        """Test response for objective without progress tracking."""
        from backend.api.routes.objective_data_requirements import ObjectiveSummary
        from bo1.models.dataset_objective_analysis import DataRequirements

        response = ObjectiveDataRequirementsResponse(
            objective=ObjectiveSummary(
                index=1,
                name="Launch new product line",
                has_progress=False,
                current_value=None,
                target_value=None,
            ),
            requirements=DataRequirements(
                objective_summary="Plan new product launch",
                essential_data=[],
                valuable_additions=[],
                data_sources=[],
                analysis_preview="Expected insights",
            ),
            generated_at=datetime.now(UTC),
            model_used="claude-3-5-sonnet-20241022",
        )
        assert response.objective.has_progress is False
        assert response.objective.current_value is None
        assert response.objective.target_value is None


class TestAnalyzeDataset:
    """Tests for POST /api/v1/datasets/{id}/analyze."""

    def test_analyze_request_defaults(self):
        """Test AnalyzeRequest has sensible defaults."""
        request = AnalyzeRequest()
        assert request.include_context is True
        assert request.objective_id is None
        assert request.force_mode is None

    def test_analyze_request_with_objective(self):
        """Test AnalyzeRequest with objective selection."""
        request = AnalyzeRequest(
            include_context=True,
            objective_id="0",
            force_mode="objective_focused",
        )
        assert request.objective_id == "0"
        assert request.force_mode == "objective_focused"

    def test_analyze_response_structure(self):
        """Test AnalyzeResponse has required fields."""
        response = AnalyzeResponse(
            analysis_id=str(uuid.uuid4()),
            analysis_mode="objective_focused",
            relevance_score=75,
            status="completed",
        )
        assert response.status == "completed"
        assert response.analysis_mode == "objective_focused"
        assert response.relevance_score == 75

    def test_analyze_response_open_exploration(self):
        """Test AnalyzeResponse for open exploration mode."""
        response = AnalyzeResponse(
            analysis_id=str(uuid.uuid4()),
            analysis_mode="open_exploration",
            relevance_score=None,
            status="completed",
        )
        assert response.analysis_mode == "open_exploration"
        assert response.relevance_score is None


class TestGetObjectiveAnalysis:
    """Tests for GET /api/v1/datasets/{id}/objective-analysis."""

    def test_response_model_structure(self):
        """Test ObjectiveAnalysisResponse has required fields."""

        response = ObjectiveAnalysisResponse(
            id=str(uuid.uuid4()),
            dataset_id=str(uuid.uuid4()),
            analysis_mode="objective_focused",
            relevance_score=80,
            relevance_assessment=None,
            data_story=None,
            insights=[],
            created_at=datetime.now(UTC),
        )
        assert response.analysis_mode == "objective_focused"
        assert response.relevance_score == 80
        assert len(response.insights) == 0

    def test_response_with_insights(self):
        """Test response with actual insights."""
        from bo1.models.dataset_objective_analysis import Insight

        insight = Insight(
            id="insight-1",
            headline="Revenue growth accelerating",
            narrative="Your MRR has grown 15% month-over-month",
            confidence="high",
            objective_name="Grow MRR",
            recommendation="Consider expanding sales team",
            follow_up_questions=["What drives the growth?"],
        )
        response = ObjectiveAnalysisResponse(
            id=str(uuid.uuid4()),
            dataset_id=str(uuid.uuid4()),
            analysis_mode="objective_focused",
            relevance_score=85,
            relevance_assessment=None,
            data_story=None,
            insights=[insight],
            created_at=datetime.now(UTC),
        )
        assert len(response.insights) == 1
        assert response.insights[0].headline == "Revenue growth accelerating"
        assert response.insights[0].confidence == "high"


class TestQuickRequirementsSummary:
    """Tests for the quick requirements summary helper."""

    def test_churn_objective_summary(self):
        """Test summary generation for churn-related objective."""
        from backend.api.routes.objective_data_requirements import (
            _generate_quick_requirements_summary,
        )

        summary = _generate_quick_requirements_summary("Reduce customer churn by 20%")
        assert "Customer" in summary or "customer" in summary

    def test_revenue_objective_summary(self):
        """Test summary generation for revenue objective."""
        from backend.api.routes.objective_data_requirements import (
            _generate_quick_requirements_summary,
        )

        summary = _generate_quick_requirements_summary("Increase MRR to $100K")
        assert "Transaction" in summary or "transaction" in summary

    def test_generic_objective_summary(self):
        """Test summary for generic objective."""
        from backend.api.routes.objective_data_requirements import (
            _generate_quick_requirements_summary,
        )

        summary = _generate_quick_requirements_summary("Improve team happiness")
        assert "metrics" in summary.lower()


class TestEstimateEssentialDataCount:
    """Tests for essential data count estimation."""

    def test_churn_objective_count(self):
        """Test data count for churn objective."""
        from backend.api.routes.objective_data_requirements import (
            _estimate_essential_data_count,
        )

        count = _estimate_essential_data_count("Reduce customer churn")
        assert count == 4

    def test_revenue_objective_count(self):
        """Test data count for revenue objective."""
        from backend.api.routes.objective_data_requirements import (
            _estimate_essential_data_count,
        )

        count = _estimate_essential_data_count("Grow sales by 50%")
        assert count == 3

    def test_generic_objective_count(self):
        """Test default data count."""
        from backend.api.routes.objective_data_requirements import (
            _estimate_essential_data_count,
        )

        count = _estimate_essential_data_count("Some generic goal")
        assert count == 3  # Default minimum


class TestAnalysisMode:
    """Tests for analysis mode determination."""

    def test_objective_focused_mode(self):
        """Test objective_focused mode is valid."""
        from bo1.models.dataset_objective_analysis import AnalysisMode

        mode = AnalysisMode.OBJECTIVE_FOCUSED
        assert mode.value == "objective_focused"

    def test_open_exploration_mode(self):
        """Test open_exploration mode is valid."""
        from bo1.models.dataset_objective_analysis import AnalysisMode

        mode = AnalysisMode.OPEN_EXPLORATION
        assert mode.value == "open_exploration"


class TestDataRequirementsModel:
    """Tests for DataRequirements model validation."""

    def test_empty_requirements(self):
        """Test empty requirements model."""
        from bo1.models.dataset_objective_analysis import DataRequirements

        req = DataRequirements(
            objective_summary="Test objective",
            essential_data=[],
            valuable_additions=[],
            data_sources=[],
            analysis_preview="Preview text",
        )
        assert req.objective_summary == "Test objective"
        assert len(req.essential_data) == 0

    def test_full_requirements(self):
        """Test requirements with all fields populated."""
        from bo1.models.dataset_objective_analysis import (
            DataPriority,
            DataRequirements,
            DataSource,
            EssentialData,
            ValuableAddition,
        )

        req = DataRequirements(
            objective_summary="Analyze customer retention",
            essential_data=[
                EssentialData(
                    name="Customer activity data",
                    description="Login and usage patterns",
                    example_columns=["user_id", "last_login", "session_count"],
                    why_essential="Required to identify at-risk customers",
                    questions_answered=["Who is likely to churn?"],
                )
            ],
            valuable_additions=[
                ValuableAddition(
                    name="Support tickets",
                    description="Customer support interactions",
                    insight_unlocked="Correlation between support issues and churn",
                    priority=DataPriority.HIGH,
                )
            ],
            data_sources=[
                DataSource(
                    source_type="CRM",
                    example_tools=["Salesforce", "HubSpot"],
                    typical_export_name="customer_export.csv",
                    columns_typically_included=["customer_id", "status", "created_at"],
                )
            ],
            analysis_preview="You'll be able to identify at-risk customers",
        )
        assert len(req.essential_data) == 1
        assert len(req.valuable_additions) == 1
        assert req.valuable_additions[0].priority == DataPriority.HIGH
        assert len(req.data_sources) == 1
