"""Tests for context management API endpoints."""

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.api.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

# Mock user for all tests
MOCK_USER = {
    "user_id": "test_user_1",
    "email": "test@example.com",
    "role": "authenticated",
    "subscription_tier": "free",
    "is_admin": False,
}


async def override_get_current_user():
    """Override auth dependency to return test user."""
    return MOCK_USER


@pytest.fixture
def mock_user_repository():
    """Mock user_repository for isolated testing."""
    mock_repo = MagicMock()
    # In-memory storage for test isolation
    storage: dict[str, Any] = {}

    def get_context(user_id: str) -> dict | None:
        return storage.get(user_id)

    def save_context(user_id: str, context: dict) -> None:
        storage[user_id] = context

    def delete_context(user_id: str) -> bool:
        if user_id in storage:
            del storage[user_id]
            return True
        return False

    mock_repo.get_context = MagicMock(side_effect=get_context)
    mock_repo.save_context = MagicMock(side_effect=save_context)
    mock_repo.delete_context = MagicMock(side_effect=delete_context)

    # Override auth dependency and mock repository
    app.dependency_overrides[get_current_user] = override_get_current_user
    with patch("backend.api.context.routes.user_repository", mock_repo):
        yield mock_repo
    # Clean up
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def client(mock_user_repository) -> TestClient:
    """Create test client with mocked dependencies."""
    return TestClient(app)


def test_get_context_not_exists(client: TestClient, mock_user_repository) -> None:
    """Test getting context when none exists."""
    response = client.get("/api/v1/context")

    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is False
    assert data["context"] is None
    assert data["updated_at"] is None


def test_update_and_get_context(client: TestClient, mock_user_repository) -> None:
    """Test updating and retrieving context."""
    # Update context
    update_response = client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
            "target_market": "Small businesses",
            "product_description": "AI-powered analytics",
            "revenue": "$50,000 MRR",
            "customers": "150",
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
    assert data["context"]["revenue"] == "$50,000 MRR"


def test_update_context_multiple_times(client: TestClient, mock_user_repository) -> None:
    """Test updating context multiple times (upsert)."""
    # First update
    client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
            "revenue": "$50,000 MRR",
        },
    )

    # Second update (should upsert)
    update_response = client.put(
        "/api/v1/context",
        json={
            "business_model": "B2C Marketplace",
            "revenue": "$75,000 MRR",
            "customers": "200",
        },
    )
    assert update_response.status_code == 200

    # Verify latest values
    get_response = client.get("/api/v1/context")
    data = get_response.json()

    assert data["context"]["business_model"] == "B2C Marketplace"
    assert data["context"]["revenue"] == "$75,000 MRR"
    assert data["context"]["customers"] == "200"


def test_delete_context(client: TestClient, mock_user_repository) -> None:
    """Test deleting context."""
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


def test_delete_context_not_exists(client: TestClient, mock_user_repository) -> None:
    """Test deleting context when none exists."""
    delete_response = client.delete("/api/v1/context")

    assert delete_response.status_code == 404
    assert "no context found" in delete_response.json()["detail"].lower()


def test_update_context_with_all_fields(client: TestClient, mock_user_repository) -> None:
    """Test updating context with all optional fields."""
    update_response = client.put(
        "/api/v1/context",
        json={
            "business_model": "B2B SaaS",
            "target_market": "Enterprise",
            "product_description": "AI analytics platform",
            "revenue": "$100,000 MRR",
            "customers": "500",
            "growth_rate": "25% MoM",
            "competitors": "Competitor A, Competitor B",
            "website": "https://example.com",
        },
    )
    assert update_response.status_code == 200

    # Verify all fields saved
    get_response = client.get("/api/v1/context")
    data = get_response.json()

    assert data["context"]["growth_rate"] == "25% MoM"
    assert data["context"]["competitors"] == "Competitor A, Competitor B"
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
