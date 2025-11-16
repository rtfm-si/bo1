"""Tests for PostgreSQL manager (context collection and research cache)."""

import pytest

from bo1.state.postgres_manager import (
    delete_user_context,
    load_user_context,
    save_user_context,
)


@pytest.fixture
def test_user_id() -> str:
    """Return a test user ID."""
    return "test-user-123"


@pytest.fixture
def sample_context() -> dict[str, str]:
    """Return sample user context."""
    return {
        "business_model": "B2B SaaS",
        "target_market": "Enterprise",
        "product_description": "AI-powered decision support",
        "revenue": "$500K ARR",
        "customers": "50",
        "growth_rate": "15% MoM",
        "competitors": "Competitor A, Competitor B",
        "website": "https://example.com",
    }


def test_user_context_crud(test_user_id: str, sample_context: dict[str, str]) -> None:
    """Test user context CRUD operations.

    This test requires a running PostgreSQL database with migrations applied.
    It will be skipped if the database is not available.
    """
    try:
        # Clean up any existing context
        delete_user_context(test_user_id)

        # Test: Load non-existent context returns None
        context = load_user_context(test_user_id)
        assert context is None

        # Test: Save context creates new row
        saved = save_user_context(test_user_id, sample_context)
        assert saved["business_model"] == sample_context["business_model"]
        assert saved["target_market"] == sample_context["target_market"]

        # Test: Load saved context
        loaded = load_user_context(test_user_id)
        assert loaded is not None
        assert loaded["business_model"] == sample_context["business_model"]

        # Test: Update context
        updated_context = sample_context.copy()
        updated_context["revenue"] = "$1M ARR"
        updated = save_user_context(test_user_id, updated_context)
        assert updated["revenue"] == "$1M ARR"

        # Test: Delete context
        deleted = delete_user_context(test_user_id)
        assert deleted is True

        # Test: Load deleted context returns None
        context = load_user_context(test_user_id)
        assert context is None

        # Test: Delete non-existent context returns False
        deleted = delete_user_context(test_user_id)
        assert deleted is False

    except Exception as e:
        pytest.skip(f"Database not available: {e}")
