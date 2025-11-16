"""Tests for context management API endpoints."""

import logging

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from bo1.state.postgres_manager import delete_user_context

logger = logging.getLogger(__name__)


@pytest.fixture
def client() -> TestClient:
    """Create test client.

    Returns:
        FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
def db_cleanup() -> None:
    """Clean up test data from database.

    Yields:
        None
    """
    yield

    # Cleanup after test
    try:
        delete_user_context("test_user_1")
    except Exception as e:
        # Ignore cleanup errors (user may not exist)
        logger.debug(f"Cleanup failed (expected if user doesn't exist): {e}")


@pytest.mark.skip(reason="Requires user in database - will be enabled with auth in Week 7")
def test_get_context_not_exists(client: TestClient, db_cleanup: None) -> None:
    """Test getting context when none exists.

    Args:
        client: FastAPI test client
        db_cleanup: Database cleanup fixture
    """
    response = client.get("/api/v1/context")

    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is False
    assert data["context"] is None
    assert data["updated_at"] is None


@pytest.mark.skip(reason="Requires user in database - will be enabled with auth in Week 7")
def test_update_and_get_context(client: TestClient, db_cleanup: None) -> None:
    """Test updating and retrieving context.

    Args:
        client: FastAPI test client
        db_cleanup: Database cleanup fixture
    """
    # Update context
    update_response = client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
            "target_market": "Small businesses",
            "product_description": "AI-powered analytics",
            "revenue": 50000.0,
            "customers": 150,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "updated"

    # Get context
    get_response = client.get("/api/v1/context")
    assert get_response.status_code == 200
    data = get_response.json()

    assert data["exists"] is True
    assert data["context"]["business_model"] == "B2B SaaS"
    assert data["context"]["target_market"] == "Small businesses"
    assert data["context"]["revenue"] == 50000.0


@pytest.mark.skip(reason="Requires user in database - will be enabled with auth in Week 7")
def test_update_context_multiple_times(client: TestClient, db_cleanup: None) -> None:
    """Test updating context multiple times (upsert).

    Args:
        client: FastAPI test client
        db_cleanup: Database cleanup fixture
    """
    # First update
    client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
            "revenue": 50000.0,
        },
    )

    # Second update (should upsert)
    update_response = client.put(
        "/api/v1/context",
        json={
            "business_model": "B2C Marketplace",
            "revenue": 75000.0,
            "customers": 200,
        },
    )
    assert update_response.status_code == 200

    # Verify latest values
    get_response = client.get("/api/v1/context")
    data = get_response.json()

    assert data["context"]["business_model"] == "B2C Marketplace"
    assert data["context"]["revenue"] == 75000.0
    assert data["context"]["customers"] == 200


@pytest.mark.skip(reason="Requires user in database - will be enabled with auth in Week 7")
def test_delete_context(client: TestClient, db_cleanup: None) -> None:
    """Test deleting context.

    Args:
        client: FastAPI test client
        db_cleanup: Database cleanup fixture
    """
    # Create context first
    client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
        },
    )

    # Delete context
    delete_response = client.delete("/api/v1/context")
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    # Verify deleted
    get_response = client.get("/api/v1/context")
    data = get_response.json()
    assert data["exists"] is False


@pytest.mark.skip(reason="Requires user in database - will be enabled with auth in Week 7")
def test_delete_context_not_exists(client: TestClient, db_cleanup: None) -> None:
    """Test deleting context when none exists.

    Args:
        client: FastAPI test client
        db_cleanup: Database cleanup fixture
    """
    delete_response = client.delete("/api/v1/context")

    assert delete_response.status_code == 404
    assert "not found" in delete_response.json()["detail"].lower()


@pytest.mark.skip(reason="Requires user in database - will be enabled with auth in Week 7")
def test_update_context_with_all_fields(client: TestClient, db_cleanup: None) -> None:
    """Test updating context with all optional fields.

    Args:
        client: FastAPI test client
        db_cleanup: Database cleanup fixture
    """
    update_response = client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
            "target_market": "Enterprise",
            "product_description": "AI analytics platform",
            "revenue": 100000.0,
            "customers": 500,
            "growth_rate": 25.5,
            "competitors": ["Competitor A", "Competitor B"],
            "website": "https://example.com",
        },
    )
    assert update_response.status_code == 200

    # Verify all fields saved
    get_response = client.get("/api/v1/context")
    data = get_response.json()

    assert data["context"]["growth_rate"] == 25.5
    assert data["context"]["competitors"] == ["Competitor A", "Competitor B"]
    assert data["context"]["website"] == "https://example.com"


def test_clarification_endpoint_moved_to_control() -> None:
    """Test that clarification endpoint was moved to control.py.

    Note: This test was replaced - the clarification endpoint moved
    to /api/v1/sessions/{id}/clarify in control.py (Day 39).
    Full tests are in test_control_api.py.
    """
    # This test is kept as a placeholder to document the migration
    # See test_control_api.py::test_submit_clarification_* for actual tests
    assert True  # Placeholder - endpoint moved to control.py
