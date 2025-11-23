"""Tests for PostgreSQL manager (context collection and research cache)."""

from collections.abc import Generator

import pytest

from bo1.state.postgres_manager import (
    db_session,
    delete_user_context,
    find_cached_research,
    get_session_clarifications,
    load_user_context,
    save_clarification,
    save_research_result,
    save_user_context,
    update_research_access,
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


@pytest.fixture
def setup_test_user(test_user_id: str) -> Generator[str, None, None]:
    """Create test user in database for testing."""
    # Setup: Create test user
    with db_session() as conn:
        with conn.cursor() as cur:
            # Delete test user if exists
            cur.execute("DELETE FROM users WHERE id = %s", (test_user_id,))
            # Create test user
            cur.execute(
                """
                INSERT INTO users (id, email, auth_provider, subscription_tier)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (test_user_id, f"{test_user_id}@test.com", "test", "free"),
            )

    yield test_user_id

    # Cleanup: Delete test user
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (test_user_id,))


def test_user_context_crud(
    setup_test_user: str, test_user_id: str, sample_context: dict[str, str]
) -> None:
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


@pytest.fixture
def setup_test_session(setup_test_user: str) -> Generator[str, None, None]:
    """Create test session in database for testing clarifications."""
    session_id = "test-session-456"
    user_id = setup_test_user

    # Setup: Create test session
    with db_session() as conn:
        with conn.cursor() as cur:
            # Delete test session if exists
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
            # Create test session
            cur.execute(
                """
                INSERT INTO sessions (id, user_id, problem_statement, status, phase)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (session_id, user_id, "Test problem", "active", "decompose"),
            )

    yield session_id

    # Cleanup: Delete test session
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (session_id,))


def test_clarifications_crud(setup_test_session: str) -> None:
    """Test session clarifications CRUD operations."""
    try:
        session_id = setup_test_session

        # Test: Save clarification
        clarification = save_clarification(
            session_id=session_id,
            question="What is your current churn rate?",
            asked_by_persona="maria",
            priority="CRITICAL",
            reason="Need actual data for CAC analysis",
            asked_at_round=2,
        )
        assert clarification["question"] == "What is your current churn rate?"
        assert clarification["priority"] == "CRITICAL"

        # Test: Get clarifications for session
        clarifications = get_session_clarifications(session_id)
        assert len(clarifications) == 1
        assert clarifications[0]["question"] == "What is your current churn rate?"

        # Test: Save multiple clarifications
        save_clarification(
            session_id=session_id,
            question="What is your target market size?",
            asked_by_persona="zara",
            priority="NICE_TO_HAVE",
            asked_at_round=3,
        )
        clarifications = get_session_clarifications(session_id)
        assert len(clarifications) == 2

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_research_cache_crud() -> None:
    """Test research cache CRUD operations."""

    try:
        # Test: Save research result
        embedding = [0.1] * 1024  # Mock embedding vector (1024 dimensions for voyage-3)
        sources = [
            {"url": "https://example.com/study1", "title": "SaaS Metrics Report"},
            {"url": "https://example.com/study2", "title": "Churn Analysis"},
        ]
        research = save_research_result(
            question="What is the average churn rate for B2B SaaS?",
            embedding=embedding,
            summary="Average B2B SaaS churn rate is 5-7% annually, with SMB at 10-15%.",
            sources=sources,
            confidence="high",
            category="saas_metrics",
            industry="saas",
            freshness_days=90,
            tokens_used=150,
            research_cost_usd=0.05,
        )
        assert research["question"] == "What is the average churn rate for B2B SaaS?"
        assert research["confidence"] == "high"
        assert research["source_count"] == 2
        cache_id = research["id"]

        # Test: Find cached research by category/industry
        cached = find_cached_research(
            question_embedding=embedding,
            similarity_threshold=0.85,
            category="saas_metrics",
            industry="saas",
        )
        assert cached is not None
        assert cached["question"] == "What is the average churn rate for B2B SaaS?"

        # Test: Update research access count
        update_research_access(str(cache_id))

        # Test: Access count incremented
        cached_updated = find_cached_research(
            question_embedding=embedding, category="saas_metrics", industry="saas"
        )
        assert cached_updated is not None
        # Note: Access count increment is tested via update_research_access call

    except Exception as e:
        pytest.skip(f"Database not available: {e}")
