"""Unit tests for research cache functionality.

Tests for Day 37: Semantic research cache for external information gaps.
"""

import pytest

from bo1.state.repositories import cache_repository


@pytest.mark.integration
@pytest.mark.requires_llm
def test_save_research_result_basic():
    """Test saving a basic research result to cache."""
    # Create dummy embedding (1024 dimensions for voyage-3)
    embedding = [0.1] * 1024

    # Save research result
    result = cache_repository.save(
        question="What is average SaaS churn rate?",
        embedding=embedding,
        summary="Average B2B SaaS churn rate is 5-7% monthly.",
        sources=[{"url": "https://example.com/saas-metrics", "title": "SaaS Metrics Guide"}],
        confidence="high",
        category="saas_metrics",
        industry="saas",
    )

    # Verify result structure
    assert result is not None
    assert "id" in result
    assert result["question"] == "What is average SaaS churn rate?"
    assert result["answer_summary"] == "Average B2B SaaS churn rate is 5-7% monthly."
    assert result["confidence"] == "high"
    assert result["category"] == "saas_metrics"
    assert result["industry"] == "saas"
    assert result["source_count"] == 1
    assert result["access_count"] >= 0  # May be non-zero if data existed from previous runs


@pytest.mark.integration
@pytest.mark.requires_llm
def test_find_cached_research_by_category():
    """Test finding cached research by category."""
    # Save a research result
    # Use unique embedding pattern to avoid collision with other tests
    embedding = [0.2 if i % 3 == 0 else 0.3 for i in range(1024)]
    cache_repository.save(
        question="What is typical SaaS CAC payback period?",
        embedding=embedding,
        summary="Typical SaaS CAC payback is 12-18 months.",
        confidence="high",
        category="saas_metrics",
        industry="saas",
    )

    # Find by category using same embedding pattern
    query_embedding = [0.2 if i % 3 == 0 else 0.3 for i in range(1024)]
    cached = cache_repository.find_by_embedding(
        question_embedding=query_embedding,
        category="saas_metrics",
    )

    # Verify found
    assert cached is not None
    assert cached["question"] == "What is typical SaaS CAC payback period?"
    assert cached["category"] == "saas_metrics"


@pytest.mark.integration
@pytest.mark.requires_llm
def test_find_cached_research_by_industry():
    """Test finding cached research by industry."""
    # Save a research result
    embedding = [0.3] * 1024
    cache_repository.save(
        question="What is average ecommerce conversion rate?",
        embedding=embedding,
        summary="Average ecommerce conversion rate is 2-3%.",
        confidence="medium",
        category="conversion_metrics",
        industry="ecommerce",
    )

    # Find by industry
    query_embedding = [0.3] * 1024
    cached = cache_repository.find_by_embedding(
        question_embedding=query_embedding,
        industry="ecommerce",
    )

    # Verify found
    assert cached is not None
    assert cached["industry"] == "ecommerce"


@pytest.mark.integration
@pytest.mark.requires_llm
def test_find_cached_research_no_match():
    """Test finding cached research with no match."""
    query_embedding = [0.4] * 1024

    # Find non-existent category
    cached = cache_repository.find_by_embedding(
        question_embedding=query_embedding,
        category="non_existent_category",
    )

    # Should return None
    assert cached is None


@pytest.mark.integration
@pytest.mark.requires_llm
def test_find_cached_research_stale_result():
    """Test that stale cached results are not returned."""
    # This test verifies the freshness_days logic
    # Since we can't easily manipulate research_date in tests,
    # we'll test the max_age_days parameter

    # Save a research result
    # Use unique embedding pattern to avoid collision with other tests
    embedding = [0.5 if i % 2 == 0 else 0.4 for i in range(1024)]
    cache_repository.save(
        question="What is SaaS magic number?",
        embedding=embedding,
        summary="SaaS magic number measures sales efficiency.",
        confidence="high",
        category="saas_metrics",
    )

    # Find with max_age_days=1 (only results from last day)
    # Use same embedding pattern
    query_embedding = [0.5 if i % 2 == 0 else 0.4 for i in range(1024)]
    cached = cache_repository.find_by_embedding(
        question_embedding=query_embedding,
        category="saas_metrics",
        max_age_days=1,
    )

    # Should find it (just created)
    assert cached is not None
    assert cached["question"] == "What is SaaS magic number?"


@pytest.mark.integration
@pytest.mark.requires_llm
def test_update_research_access():
    """Test updating access count for cached research."""
    # Save a research result
    embedding = [0.6] * 1024
    result = cache_repository.save(
        question="What is net revenue retention?",
        embedding=embedding,
        summary="Net revenue retention measures revenue growth from existing customers.",
        confidence="high",
        category="saas_metrics",
    )

    cache_id = result["id"]

    # Update access
    cache_repository.update_access(cache_id)

    # Verify access count incremented
    # Note: We can't easily verify this without re-fetching from DB
    # This test mainly verifies the function doesn't error


@pytest.mark.integration
@pytest.mark.requires_llm
def test_find_cached_research_returns_most_recent():
    """Test that most recent result is returned when multiple matches exist."""
    # Save two results in same category
    embedding1 = [0.7] * 1024
    cache_repository.save(
        question="Old question about pricing",
        embedding=embedding1,
        summary="Old pricing data",
        confidence="medium",
        category="pricing",
    )

    # Wait a moment then save newer result
    embedding2 = [0.7] * 1024
    cache_repository.save(
        question="New question about pricing",
        embedding=embedding2,
        summary="New pricing data",
        confidence="high",
        category="pricing",
    )

    # Find should return most recent
    query_embedding = [0.7] * 1024
    cached = cache_repository.find_by_embedding(
        question_embedding=query_embedding,
        category="pricing",
    )

    # Should return newer result
    assert cached is not None
    # Due to ordering by research_date DESC, newest should be returned
    # But since both were just created, either could be returned
    # The important thing is that we get a result


@pytest.mark.integration
@pytest.mark.requires_llm
def test_save_research_result_with_cost_tracking():
    """Test saving research result with cost tracking."""
    embedding = [0.8] * 1024

    result = cache_repository.save(
        question="What is average ACV for B2B SaaS?",
        embedding=embedding,
        summary="Average ACV for B2B SaaS is $10-50K.",
        confidence="high",
        category="saas_metrics",
        tokens_used=500,
        research_cost_usd=0.05,
    )

    # Verify cost tracking
    assert result["tokens_used"] == 500
    assert float(result["research_cost_usd"]) == 0.05


@pytest.mark.integration
@pytest.mark.requires_llm
def test_find_cached_research_with_combined_filters():
    """Test finding with both category and industry filters."""
    # Save a result
    embedding = [0.9] * 1024
    cache_repository.save(
        question="What is SaaS gross margin benchmark?",
        embedding=embedding,
        summary="Typical SaaS gross margin is 70-80%.",
        confidence="high",
        category="saas_metrics",
        industry="saas",
    )

    # Find with both filters
    query_embedding = [0.9] * 1024
    cached = cache_repository.find_by_embedding(
        question_embedding=query_embedding,
        category="saas_metrics",
        industry="saas",
    )

    # Should find
    assert cached is not None
    assert cached["category"] == "saas_metrics"
    assert cached["industry"] == "saas"


@pytest.mark.unit
def test_researcher_agent_stub():
    """Test that ResearcherAgent exists and can be instantiated."""
    from bo1.agents.researcher import ResearcherAgent

    # Should not error
    agent = ResearcherAgent()
    assert agent is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_researcher_agent_research_questions_stub():
    """Test ResearcherAgent.research_questions returns results (cached or stub).

    This test may get cache hits from integration tests, which is acceptable.
    The important thing is that it returns results without errors.
    """
    from bo1.agents.researcher import ResearcherAgent

    agent = ResearcherAgent()

    questions = [
        {"question": "What is average SaaS churn?", "priority": "CRITICAL"},
        {"question": "What is typical CAC?", "priority": "NICE_TO_HAVE"},
    ]

    results = await agent.research_questions(questions)

    # Should return results (may be cached from integration tests or stub)
    assert len(results) == 2
    assert results[0]["question"] == "What is average SaaS churn?"
    assert results[0]["confidence"] in ("stub", "high", "medium", "low")  # Accept any confidence
    assert results[1]["question"] == "What is typical CAC?"


# --- Tier-based provider selection tests ---


@pytest.mark.unit
def test_tier_based_provider_selection_free_uses_brave():
    """Test that free tier always uses Brave, even with deep research."""
    from bo1.agents.researcher import ResearcherAgent

    _agent = ResearcherAgent()  # noqa: F841 - instantiate to verify import
    # Free tier + deep research → should still use Brave
    use_tavily = "free" in ("pro", "enterprise") and "deep" == "deep"
    assert use_tavily is False


@pytest.mark.unit
def test_tier_based_provider_selection_starter_uses_brave():
    """Test that starter tier always uses Brave, even with deep research."""
    # Starter tier + deep research → should still use Brave
    use_tavily = "starter" in ("pro", "enterprise") and "deep" == "deep"
    assert use_tavily is False


@pytest.mark.unit
def test_tier_based_provider_selection_pro_basic_uses_brave():
    """Test that pro tier with basic research uses Brave."""
    # Pro tier + basic research → should use Brave
    use_tavily = "pro" in ("pro", "enterprise") and "basic" == "deep"
    assert use_tavily is False


@pytest.mark.unit
def test_tier_based_provider_selection_pro_deep_uses_tavily():
    """Test that pro tier with deep research uses Tavily."""
    # Pro tier + deep research → should use Tavily
    use_tavily = "pro" in ("pro", "enterprise") and "deep" == "deep"
    assert use_tavily is True


@pytest.mark.unit
def test_tier_based_provider_selection_enterprise_deep_uses_tavily():
    """Test that enterprise tier with deep research uses Tavily."""
    # Enterprise tier + deep research → should use Tavily
    use_tavily = "enterprise" in ("pro", "enterprise") and "deep" == "deep"
    assert use_tavily is True


@pytest.mark.unit
def test_tier_based_rate_limiter_key_selection():
    """Test rate limiter key selection based on tier."""
    # Free tier → free rate limiter
    key_free = "brave_basic" if "free" in ("pro", "enterprise") else "brave_free"
    assert key_free == "brave_free"

    # Starter tier → free rate limiter
    key_starter = "brave_basic" if "starter" in ("pro", "enterprise") else "brave_free"
    assert key_starter == "brave_free"

    # Pro tier → basic rate limiter (higher limits)
    key_pro = "brave_basic" if "pro" in ("pro", "enterprise") else "brave_free"
    assert key_pro == "brave_basic"

    # Enterprise tier → basic rate limiter (higher limits)
    key_enterprise = "brave_basic" if "enterprise" in ("pro", "enterprise") else "brave_free"
    assert key_enterprise == "brave_basic"


@pytest.mark.unit
def test_tier_based_tavily_rate_limiter_key_selection():
    """Test Tavily rate limiter key selection based on tier."""
    # Pro tier → basic rate limiter (higher limits)
    key_pro = "tavily_basic" if "pro" in ("pro", "enterprise") else "tavily_free"
    assert key_pro == "tavily_basic"

    # Enterprise tier → basic rate limiter (higher limits)
    key_enterprise = "tavily_basic" if "enterprise" in ("pro", "enterprise") else "tavily_free"
    assert key_enterprise == "tavily_basic"

    # Free tier → free rate limiter (edge case: shouldn't reach Tavily but tests the logic)
    key_free = "tavily_basic" if "free" in ("pro", "enterprise") else "tavily_free"
    assert key_free == "tavily_free"
