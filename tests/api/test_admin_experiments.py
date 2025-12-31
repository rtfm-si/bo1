"""Admin experiments API integration tests.

Tests the experiment management API endpoints with mocked database connections.
"""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.admin.experiments import router
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import limiter as global_limiter
from backend.services.experiments import Experiment, Variant


def mock_admin_override():
    """Override admin auth to always succeed."""
    return "test-admin-user-id"


@pytest.fixture
def app():
    """Create test app with experiments routes and mocked auth."""
    # Disable global rate limiter for tests (to avoid Redis connection)
    original_enabled = global_limiter.enabled
    global_limiter.enabled = False

    app = FastAPI()

    # Set up rate limiter with memory storage for tests
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    app.state.limiter = limiter

    # Mock admin auth
    app.dependency_overrides[require_admin_any] = mock_admin_override

    # Include the experiments router
    app.include_router(router, prefix="/api/admin")

    yield app

    # Restore original limiter state
    global_limiter.enabled = original_enabled


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


def make_experiment(
    exp_id=None,
    name="test_experiment",
    status="draft",
    start_date=None,
    end_date=None,
):
    """Helper to create an Experiment instance."""
    now = datetime.now(UTC)
    return Experiment(
        id=exp_id or uuid4(),
        name=name,
        description="Test experiment",
        status=status,
        variants=[Variant("control", 50), Variant("treatment", 50)],
        metrics=["conversion_rate"],
        start_date=start_date,
        end_date=end_date,
        created_at=now,
        updated_at=now,
    )


class TestListExperiments:
    """Tests for GET /experiments."""

    @patch("backend.api.admin.experiments.exp_service.list_experiments")
    def test_list_all(self, mock_list, client):
        """Should list all experiments."""
        exp1 = make_experiment(name="exp1")
        exp2 = make_experiment(name="exp2", status="running")
        mock_list.return_value = [exp1, exp2]

        response = client.get("/api/admin/experiments")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["experiments"]) == 2
        assert data["experiments"][0]["name"] == "exp1"

    @patch("backend.api.admin.experiments.exp_service.list_experiments")
    def test_filter_by_status(self, mock_list, client):
        """Should filter by status."""
        exp = make_experiment(status="running")
        mock_list.return_value = [exp]

        response = client.get("/api/admin/experiments?status=running")

        assert response.status_code == 200
        mock_list.assert_called_once_with(status="running")


class TestCreateExperiment:
    """Tests for POST /experiments."""

    @patch("backend.api.admin.experiments.exp_service.create_experiment")
    def test_create_with_defaults(self, mock_create, client):
        """Should create experiment with defaults."""
        exp = make_experiment()
        mock_create.return_value = exp

        response = client.post(
            "/api/admin/experiments",
            json={"name": "new_experiment"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_experiment"
        assert data["status"] == "draft"

    @patch("backend.api.admin.experiments.exp_service.create_experiment")
    def test_create_with_custom_variants(self, mock_create, client):
        """Should create with custom variants."""
        exp = make_experiment()
        mock_create.return_value = exp

        response = client.post(
            "/api/admin/experiments",
            json={
                "name": "custom_exp",
                "variants": [
                    {"name": "a", "weight": 33},
                    {"name": "b", "weight": 33},
                    {"name": "c", "weight": 34},
                ],
            },
        )

        assert response.status_code == 200

    @patch("backend.api.admin.experiments.exp_service.create_experiment")
    def test_create_invalid_weights(self, mock_create, client):
        """Should return 400 for invalid weights."""
        mock_create.side_effect = ValueError("weights must sum to 100")

        response = client.post(
            "/api/admin/experiments",
            json={
                "name": "bad_exp",
                "variants": [{"name": "a", "weight": 30}, {"name": "b", "weight": 30}],
            },
        )

        assert response.status_code == 400
        assert "weights must sum to 100" in response.json()["detail"]


class TestGetExperiment:
    """Tests for GET /experiments/{id}."""

    @patch("backend.api.admin.experiments.exp_service.get_experiment")
    def test_get_found(self, mock_get, client):
        """Should return experiment when found."""
        exp_id = uuid4()
        exp = make_experiment(exp_id=exp_id)
        mock_get.return_value = exp

        response = client.get(f"/api/admin/experiments/{exp_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(exp_id)

    @patch("backend.api.admin.experiments.exp_service.get_experiment")
    def test_get_not_found(self, mock_get, client):
        """Should return 404 when not found."""
        mock_get.return_value = None

        response = client.get(f"/api/admin/experiments/{uuid4()}")

        assert response.status_code == 404


class TestUpdateExperiment:
    """Tests for PATCH /experiments/{id}."""

    @patch("backend.api.admin.experiments.exp_service.update_experiment")
    def test_update_description(self, mock_update, client):
        """Should update experiment description."""
        exp_id = uuid4()
        exp = make_experiment(exp_id=exp_id)
        mock_update.return_value = exp

        response = client.patch(
            f"/api/admin/experiments/{exp_id}",
            json={"description": "Updated description"},
        )

        assert response.status_code == 200

    @patch("backend.api.admin.experiments.exp_service.update_experiment")
    def test_update_not_draft(self, mock_update, client):
        """Should return 400 when updating non-draft experiment."""
        mock_update.side_effect = ValueError("Cannot update experiment in 'running' status")

        response = client.patch(
            f"/api/admin/experiments/{uuid4()}",
            json={"description": "Updated"},
        )

        assert response.status_code == 400
        assert "running" in response.json()["detail"]


class TestDeleteExperiment:
    """Tests for DELETE /experiments/{id}."""

    @patch("backend.api.admin.experiments.exp_service.delete_experiment")
    def test_delete_success(self, mock_delete, client):
        """Should delete draft experiment."""
        exp_id = uuid4()
        mock_delete.return_value = True

        response = client.delete(f"/api/admin/experiments/{exp_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @patch("backend.api.admin.experiments.exp_service.delete_experiment")
    def test_delete_not_found(self, mock_delete, client):
        """Should return 404 when not found."""
        mock_delete.return_value = False

        response = client.delete(f"/api/admin/experiments/{uuid4()}")

        assert response.status_code == 404

    @patch("backend.api.admin.experiments.exp_service.delete_experiment")
    def test_delete_not_draft(self, mock_delete, client):
        """Should return 400 when deleting non-draft."""
        mock_delete.side_effect = ValueError("Cannot delete experiment in 'running' status")

        response = client.delete(f"/api/admin/experiments/{uuid4()}")

        assert response.status_code == 400


class TestStartExperiment:
    """Tests for POST /experiments/{id}/start."""

    @patch("backend.api.admin.experiments.exp_service.start_experiment")
    def test_start_success(self, mock_start, client):
        """Should start experiment."""
        exp_id = uuid4()
        exp = make_experiment(exp_id=exp_id, status="running", start_date=datetime.now(UTC))
        mock_start.return_value = exp

        response = client.post(f"/api/admin/experiments/{exp_id}/start")

        assert response.status_code == 200
        assert response.json()["status"] == "running"

    @patch("backend.api.admin.experiments.exp_service.start_experiment")
    def test_start_invalid_transition(self, mock_start, client):
        """Should return 400 for invalid transition."""
        mock_start.side_effect = ValueError("Cannot transition from 'concluded' to 'running'")

        response = client.post(f"/api/admin/experiments/{uuid4()}/start")

        assert response.status_code == 400


class TestPauseExperiment:
    """Tests for POST /experiments/{id}/pause."""

    @patch("backend.api.admin.experiments.exp_service.pause_experiment")
    def test_pause_success(self, mock_pause, client):
        """Should pause experiment."""
        exp_id = uuid4()
        exp = make_experiment(exp_id=exp_id, status="paused")
        mock_pause.return_value = exp

        response = client.post(f"/api/admin/experiments/{exp_id}/pause")

        assert response.status_code == 200
        assert response.json()["status"] == "paused"


class TestConcludeExperiment:
    """Tests for POST /experiments/{id}/conclude."""

    @patch("backend.api.admin.experiments.exp_service.conclude_experiment")
    def test_conclude_success(self, mock_conclude, client):
        """Should conclude experiment."""
        exp_id = uuid4()
        now = datetime.now(UTC)
        exp = make_experiment(exp_id=exp_id, status="concluded", start_date=now, end_date=now)
        mock_conclude.return_value = exp

        response = client.post(f"/api/admin/experiments/{exp_id}/conclude")

        assert response.status_code == 200
        assert response.json()["status"] == "concluded"
        assert response.json()["end_date"] is not None


class TestGetUserVariant:
    """Tests for GET /experiments/{name}/variant/{user_id}."""

    @patch("backend.api.admin.experiments.exp_service.get_user_variant")
    def test_get_variant_running(self, mock_get, client):
        """Should return variant for running experiment."""
        mock_get.return_value = "treatment"

        response = client.get("/api/admin/experiments/my_exp/variant/user123")

        assert response.status_code == 200
        data = response.json()
        assert data["experiment_name"] == "my_exp"
        assert data["user_id"] == "user123"
        assert data["variant"] == "treatment"

    @patch("backend.api.admin.experiments.exp_service.get_user_variant")
    def test_get_variant_not_running(self, mock_get, client):
        """Should return null variant when not running."""
        mock_get.return_value = None

        response = client.get("/api/admin/experiments/draft_exp/variant/user123")

        assert response.status_code == 200
        assert response.json()["variant"] is None
