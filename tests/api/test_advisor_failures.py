"""Tests for mentor failure patterns API endpoint."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.advisor import router
from backend.api.middleware.auth import get_current_user
from backend.services.action_failure_detector import (
    FailurePattern,
    FailurePatternSummary,
)


def mock_user_override():
    """Override auth to return test user."""
    return {"user_id": "test-user-123", "email": "test@example.com"}


@pytest.fixture
def test_app():
    """Create test app with mentor router and auth override."""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = mock_user_override
    # Router already has /v1/advisor prefix
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


class TestFailurePatternsAuthRequired:
    """Tests for authentication on failure patterns endpoint."""

    def test_failure_patterns_requires_auth(self, unauthenticated_client):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/advisor/failure-patterns")
        assert response.status_code == 401


class TestFailurePatternsResponseStructure:
    """Tests for response structure validation."""

    def test_returns_expected_fields(self, client):
        """Response includes all expected fields."""
        mock_summary = FailurePatternSummary(
            patterns=[
                FailurePattern(
                    action_id="action-1",
                    title="Build auth system",
                    project_id="proj-1",
                    project_name="Core",
                    status="cancelled",
                    priority="high",
                    failure_reason="Scope too large",
                    failure_category="scope_creep",
                    failed_at="2025-12-10T10:00:00+00:00",
                    tags=["backend"],
                ),
                FailurePattern(
                    action_id="action-2",
                    title="Deploy to prod",
                    project_id=None,
                    project_name=None,
                    status="blocked",
                    priority="critical",
                    failure_reason="Pipeline broken",
                    failure_category="blocker",
                    failed_at="2025-12-12T10:00:00+00:00",
                    tags=[],
                ),
                FailurePattern(
                    action_id="action-3",
                    title="Write docs",
                    project_id="proj-1",
                    project_name="Core",
                    status="cancelled",
                    priority="medium",
                    failure_reason="Deprioritized",
                    failure_category="unknown",
                    failed_at="2025-12-14T10:00:00+00:00",
                    tags=["docs"],
                ),
            ],
            failure_rate=0.4,
            total_actions=10,
            failed_actions=4,
            period_days=30,
            by_project={"Core": 3, "No Project": 1},
            by_category={"scope_creep": 2, "blocker": 1, "unknown": 1},
        )

        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            response = client.get("/api/v1/advisor/failure-patterns")

            assert response.status_code == 200
            data = response.json()

            # Check top-level fields
            assert "patterns" in data
            assert "failure_rate" in data
            assert "total_actions" in data
            assert "failed_actions" in data
            assert "period_days" in data
            assert "by_project" in data
            assert "by_category" in data
            assert "analysis_timestamp" in data

            # Check values
            assert data["failure_rate"] == 0.4
            assert data["total_actions"] == 10
            assert data["failed_actions"] == 4
            assert data["period_days"] == 30

    def test_pattern_fields(self, client):
        """Pattern objects include correct fields."""
        mock_summary = FailurePatternSummary(
            patterns=[
                FailurePattern(
                    action_id="action-xyz",
                    title="Test Action",
                    project_id="proj-abc",
                    project_name="Test Project",
                    status="cancelled",
                    priority="high",
                    failure_reason="Cancelled by user",
                    failure_category="scope_creep",
                    failed_at="2025-12-15T10:00:00+00:00",
                    tags=["test", "important"],
                ),
            ]
            * 3,  # Need at least 3 to pass min_failures
            failure_rate=0.5,
            total_actions=6,
            failed_actions=3,
            period_days=30,
            by_project={"Test Project": 3},
            by_category={"scope_creep": 3},
        )

        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            response = client.get("/api/v1/advisor/failure-patterns")

            assert response.status_code == 200
            data = response.json()
            pattern = data["patterns"][0]

            assert pattern["action_id"] == "action-xyz"
            assert pattern["title"] == "Test Action"
            assert pattern["project_id"] == "proj-abc"
            assert pattern["project_name"] == "Test Project"
            assert pattern["status"] == "cancelled"
            assert pattern["priority"] == "high"
            assert pattern["failure_reason"] == "Cancelled by user"
            assert pattern["failure_category"] == "scope_creep"
            assert pattern["failed_at"] == "2025-12-15T10:00:00+00:00"
            assert pattern["tags"] == ["test", "important"]


class TestMinFailuresFiltering:
    """Tests for min_failures parameter."""

    def test_filters_when_below_min_failures(self, client):
        """Returns empty patterns when below min_failures threshold."""
        mock_summary = FailurePatternSummary(
            patterns=[
                FailurePattern(
                    action_id="action-1",
                    title="Only one failure",
                    project_id=None,
                    project_name=None,
                    status="cancelled",
                    priority="medium",
                    failure_reason="Test",
                    failure_category="unknown",
                    failed_at="2025-12-15T10:00:00+00:00",
                    tags=[],
                ),
            ],
            failure_rate=0.1,
            total_actions=10,
            failed_actions=1,
            period_days=30,
            by_project={"No Project": 1},
            by_category={"unknown": 1},
        )

        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            # Default min_failures is 3
            response = client.get("/api/v1/advisor/failure-patterns")

            assert response.status_code == 200
            data = response.json()
            # Patterns should be empty because we have < 3 failures
            assert data["patterns"] == []
            # But stats should still be returned
            assert data["failure_rate"] == 0.1
            assert data["failed_actions"] == 1

    def test_min_failures_param(self, client):
        """Custom min_failures parameter is respected."""
        mock_summary = FailurePatternSummary(
            patterns=[
                FailurePattern(
                    action_id=f"action-{i}",
                    title=f"Failure {i}",
                    project_id=None,
                    project_name=None,
                    status="cancelled",
                    priority="medium",
                    failure_reason="Test",
                    failure_category="unknown",
                    failed_at="2025-12-15T10:00:00+00:00",
                    tags=[],
                )
                for i in range(5)
            ],
            failure_rate=0.5,
            total_actions=10,
            failed_actions=5,
            period_days=30,
            by_project={},
            by_category={},
        )

        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            # Set min_failures to 10, should return empty
            response = client.get("/api/v1/advisor/failure-patterns?min_failures=10")

            assert response.status_code == 200
            data = response.json()
            assert data["patterns"] == []

            # Set min_failures to 1, should return all
            response = client.get("/api/v1/advisor/failure-patterns?min_failures=1")
            data = response.json()
            assert len(data["patterns"]) == 5


class TestDaysParamValidation:
    """Tests for days parameter validation."""

    def test_days_default(self, client):
        """Default days is 30."""
        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_summary = FailurePatternSummary(
                patterns=[],
                failure_rate=0.0,
                total_actions=0,
                failed_actions=0,
                period_days=30,
                by_project={},
                by_category={},
            )
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            response = client.get("/api/v1/advisor/failure-patterns")

            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 30

    def test_days_range_min(self, client):
        """Days parameter minimum is 7."""
        response = client.get("/api/v1/advisor/failure-patterns?days=1")
        # FastAPI validates query params
        assert response.status_code == 422

    def test_days_range_max(self, client):
        """Days parameter maximum is 90."""
        response = client.get("/api/v1/advisor/failure-patterns?days=100")
        assert response.status_code == 422

    def test_days_valid_values(self, client):
        """Valid days values work correctly."""
        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            for days in [7, 30, 90]:
                mock_summary = FailurePatternSummary(
                    patterns=[],
                    failure_rate=0.0,
                    total_actions=0,
                    failed_actions=0,
                    period_days=days,
                    by_project={},
                    by_category={},
                )
                mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

                response = client.get(f"/api/v1/advisor/failure-patterns?days={days}")
                assert response.status_code == 200


class TestEmptyPatterns:
    """Tests for empty/no-failure cases."""

    def test_no_actions(self, client):
        """User with no actions returns empty patterns."""
        mock_summary = FailurePatternSummary(
            patterns=[],
            failure_rate=0.0,
            total_actions=0,
            failed_actions=0,
            period_days=30,
            by_project={},
            by_category={},
        )

        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            response = client.get("/api/v1/advisor/failure-patterns")

            assert response.status_code == 200
            data = response.json()
            assert data["patterns"] == []
            assert data["failure_rate"] == 0.0
            assert data["total_actions"] == 0
            assert data["failed_actions"] == 0
            assert data["by_project"] == {}
            assert data["by_category"] == {}

    def test_all_completed(self, client):
        """User with all completed actions returns 0% failure rate."""
        mock_summary = FailurePatternSummary(
            patterns=[],
            failure_rate=0.0,
            total_actions=20,
            failed_actions=0,
            period_days=30,
            by_project={},
            by_category={},
        )

        with patch(
            "backend.services.action_failure_detector.get_action_failure_detector"
        ) as mock_detector:
            mock_detector.return_value.detect_failure_patterns.return_value = mock_summary

            response = client.get("/api/v1/advisor/failure-patterns")

            assert response.status_code == 200
            data = response.json()
            assert data["failure_rate"] == 0.0
            assert data["total_actions"] == 20
            assert data["failed_actions"] == 0
