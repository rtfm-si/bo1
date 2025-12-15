"""Tests for mentor improvement plan API endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.mentor import router
from backend.api.middleware.auth import get_current_user
from backend.services.improvement_plan_generator import ImprovementPlan, Suggestion


def mock_user_override():
    """Override auth to return test user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def test_app():
    """Create test app with mentor router and auth override."""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = mock_user_override
    # Router already has /v1/mentor prefix
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(test_app):
    """Create test client with auth bypass."""
    return TestClient(test_app)


@pytest.fixture
def unauthenticated_client():
    """Create test client without auth bypass (for auth tests)."""
    from backend.api.main import app

    return TestClient(app)


@pytest.fixture
def mock_plan():
    """Create a mock improvement plan."""
    return ImprovementPlan(
        suggestions=[
            Suggestion(
                category="execution",
                title="Break down large tasks",
                description="Your action failure rate suggests tasks may be too large. Try breaking them into smaller pieces.",
                action_steps=[
                    "Review task size before starting",
                    "Split tasks over 4 hours into subtasks",
                    "Set daily progress milestones",
                ],
                priority="high",
            ),
            Suggestion(
                category="planning",
                title="Improve estimation accuracy",
                description="Several tasks were cancelled due to scope creep. Consider adding buffer time.",
                action_steps=[
                    "Add 20% buffer to initial estimates",
                    "Review estimates after each sprint",
                ],
                priority="medium",
            ),
        ],
        generated_at="2025-12-15T10:00:00+00:00",
        inputs_summary={
            "days_analyzed": 30,
            "topics_detected": 2,
            "failure_rate": 0.35,
            "total_actions": 20,
            "failed_actions": 7,
        },
        confidence=0.65,
    )


class TestImprovementPlanEndpoint:
    """Tests for GET /api/v1/mentor/improvement-plan."""

    def test_improvement_plan_endpoint_auth(self, unauthenticated_client):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/mentor/improvement-plan")
        assert response.status_code == 401

    def test_improvement_plan_returns_suggestions(self, client, mock_plan):
        """Returns improvement plan with suggestions."""
        with patch(
            "backend.services.improvement_plan_generator.get_improvement_plan_generator"
        ) as mock_gen:
            mock_generator = MagicMock()
            mock_generator.generate_plan = AsyncMock(return_value=mock_plan)
            mock_gen.return_value = mock_generator

            response = client.get("/api/v1/mentor/improvement-plan")

            assert response.status_code == 200
            data = response.json()

            assert len(data["suggestions"]) == 2
            assert data["suggestions"][0]["category"] == "execution"
            assert data["suggestions"][0]["title"] == "Break down large tasks"
            assert len(data["suggestions"][0]["action_steps"]) == 3
            assert data["suggestions"][0]["priority"] == "high"

    def test_improvement_plan_includes_metadata(self, client, mock_plan):
        """Response includes metadata fields."""
        with patch(
            "backend.services.improvement_plan_generator.get_improvement_plan_generator"
        ) as mock_gen:
            mock_generator = MagicMock()
            mock_generator.generate_plan = AsyncMock(return_value=mock_plan)
            mock_gen.return_value = mock_generator

            response = client.get("/api/v1/mentor/improvement-plan")

            data = response.json()
            assert "generated_at" in data
            assert "inputs_summary" in data
            assert "confidence" in data
            assert data["confidence"] == 0.65

    def test_improvement_plan_inputs_summary(self, client, mock_plan):
        """Response includes inputs summary."""
        with patch(
            "backend.services.improvement_plan_generator.get_improvement_plan_generator"
        ) as mock_gen:
            mock_generator = MagicMock()
            mock_generator.generate_plan = AsyncMock(return_value=mock_plan)
            mock_gen.return_value = mock_generator

            response = client.get("/api/v1/mentor/improvement-plan")

            data = response.json()
            summary = data["inputs_summary"]
            assert summary["days_analyzed"] == 30
            assert summary["topics_detected"] == 2
            assert summary["failure_rate"] == 0.35

    def test_improvement_plan_days_param(self, client, mock_plan):
        """Days parameter is passed to generator."""
        with patch(
            "backend.services.improvement_plan_generator.get_improvement_plan_generator"
        ) as mock_gen:
            mock_generator = MagicMock()
            mock_generator.generate_plan = AsyncMock(return_value=mock_plan)
            mock_gen.return_value = mock_generator

            response = client.get("/api/v1/mentor/improvement-plan?days=60")

            assert response.status_code == 200
            mock_generator.generate_plan.assert_called_once_with(
                user_id="test-user-123",
                days=60,
                force_refresh=False,
            )

    def test_improvement_plan_force_refresh_param(self, client, mock_plan):
        """Force refresh parameter is passed to generator."""
        with patch(
            "backend.services.improvement_plan_generator.get_improvement_plan_generator"
        ) as mock_gen:
            mock_generator = MagicMock()
            mock_generator.generate_plan = AsyncMock(return_value=mock_plan)
            mock_gen.return_value = mock_generator

            response = client.get("/api/v1/mentor/improvement-plan?force_refresh=true")

            assert response.status_code == 200
            mock_generator.generate_plan.assert_called_once_with(
                user_id="test-user-123",
                days=30,
                force_refresh=True,
            )

    def test_improvement_plan_days_validation_min(self, client):
        """Days parameter must be >= 7."""
        response = client.get("/api/v1/mentor/improvement-plan?days=3")
        assert response.status_code == 422

    def test_improvement_plan_days_validation_max(self, client):
        """Days parameter must be <= 90."""
        response = client.get("/api/v1/mentor/improvement-plan?days=100")
        assert response.status_code == 422


class TestImprovementPlanOnTrack:
    """Tests for 'on track' scenario."""

    def test_returns_on_track_when_no_patterns(self, client):
        """Returns on track message when no patterns detected."""
        on_track_plan = ImprovementPlan(
            suggestions=[
                Suggestion(
                    category="status",
                    title="You're on track!",
                    description="No significant patterns detected.",
                    action_steps=["Continue current practices"],
                    priority="low",
                )
            ],
            generated_at="2025-12-15T10:00:00+00:00",
            inputs_summary={"days_analyzed": 30, "topics_detected": 0},
            confidence=0.0,
        )

        with patch(
            "backend.services.improvement_plan_generator.get_improvement_plan_generator"
        ) as mock_gen:
            mock_generator = MagicMock()
            mock_generator.generate_plan = AsyncMock(return_value=on_track_plan)
            mock_gen.return_value = mock_generator

            response = client.get("/api/v1/mentor/improvement-plan")

            data = response.json()
            assert len(data["suggestions"]) == 1
            assert data["suggestions"][0]["category"] == "status"
            assert "on track" in data["suggestions"][0]["title"].lower()
            assert data["confidence"] == 0.0
