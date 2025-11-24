"""Tests for persona selection caching with semantic similarity.

Tests cover:
- Cache hit/miss logic
- Cosine similarity calculation
- Semantic matching of similar problems
- Cache statistics tracking
- TTL expiration
- Error handling
"""

import pytest

from bo1.agents.persona_cache import PersonaSelectionCache
from bo1.llm.embeddings import cosine_similarity
from bo1.models.persona import PersonaProfile
from bo1.models.problem import SubProblem


def test_cosine_similarity_identical():
    """Test cosine similarity with identical vectors."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]

    similarity = cosine_similarity(vec1, vec2)

    assert similarity == pytest.approx(1.0, abs=0.001)


def test_cosine_similarity_orthogonal():
    """Test cosine similarity with orthogonal vectors."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]

    similarity = cosine_similarity(vec1, vec2)

    assert similarity == pytest.approx(0.0, abs=0.001)


def test_cosine_similarity_opposite():
    """Test cosine similarity with opposite vectors."""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [-1.0, 0.0, 0.0]

    similarity = cosine_similarity(vec1, vec2)

    assert similarity == pytest.approx(-1.0, abs=0.001)


def test_cosine_similarity_similar():
    """Test cosine similarity with similar vectors."""
    vec1 = [0.8, 0.6, 0.0]
    vec2 = [0.9, 0.5, 0.0]

    similarity = cosine_similarity(vec1, vec2)

    # Should be high but not 1.0
    assert 0.9 < similarity < 1.0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_persona_cache_miss_no_entries(redis_manager):
    """Test cache returns None when no entries exist."""
    cache = PersonaSelectionCache(redis_manager)

    # Clear any existing cache entries
    keys = redis_manager.redis.keys("personas:cache:*")
    if keys:
        redis_manager.redis.delete(*keys)

    problem = SubProblem(
        id="sp_001",
        goal="Should we expand to European markets?",
        context="SaaS company with $1M ARR",
        complexity_score=6,
    )

    cached = await cache.get_cached_personas(problem)

    assert cached is None
    assert cache._misses == 1
    assert cache.hit_rate == 0.0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_persona_cache_hit_similar_problem(redis_manager):
    """Test cache returns personas for similar problem."""
    cache = PersonaSelectionCache(redis_manager)

    # Clear any existing cache entries
    keys = redis_manager.redis.keys("personas:cache:*")
    if keys:
        redis_manager.redis.delete(*keys)

    # Original problem
    problem1 = SubProblem(
        id="sp_001",
        goal="Should we expand to European markets?",
        context="SaaS company",
        complexity_score=6,
    )

    personas = [
        PersonaProfile(
            code="finance_strategist",
            name="Maria Santos",
            role="CFO & Financial Strategist",
            description="Strategic financial analysis",
            expertise_areas=["finance"],
            category="finance",
            system_prompt="Test prompt",
        ),
        PersonaProfile(
            code="growth_hacker",
            name="Zara Morales",
            role="Growth Hacker",
            description="Growth strategy",
            expertise_areas=["growth"],
            category="marketing",
            system_prompt="Test prompt",
        ),
    ]

    # Cache first problem's selection
    await cache.cache_persona_selection(problem1, personas)

    # Similar problem (high similarity expected)
    problem2 = SubProblem(
        id="sp_002",
        goal="Should we launch in Europe?",
        context="SaaS business",
        complexity_score=6,
    )

    # Should hit cache due to semantic similarity
    cached = await cache.get_cached_personas(problem2)

    assert cached is not None
    assert len(cached) == 2
    assert cached[0].code == "finance_strategist"
    assert cached[1].code == "growth_hacker"
    assert cache._hits == 1
    assert cache.hit_rate > 0.0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_persona_cache_miss_different_problem(redis_manager):
    """Test cache returns None for very different problem."""
    cache = PersonaSelectionCache(redis_manager)

    # Clear any existing cache entries
    keys = redis_manager.redis.keys("personas:cache:*")
    if keys:
        redis_manager.redis.delete(*keys)

    # Original problem
    problem1 = SubProblem(
        id="sp_001",
        goal="Should we expand to Europe?",
        context="SaaS company",
        complexity_score=6,
    )

    personas = [
        PersonaProfile(
            code="finance_strategist",
            name="Maria Santos",
            role="CFO",
            description="Finance",
            expertise_areas=["finance"],
            category="finance",
            system_prompt="Test",
        )
    ]

    await cache.cache_persona_selection(problem1, personas)

    # Very different problem (low similarity expected)
    problem2 = SubProblem(
        id="sp_002",
        goal="What tech stack for mobile app?",
        context="App development",
        complexity_score=4,
    )

    # Should miss cache due to low similarity
    cached = await cache.get_cached_personas(problem2)

    assert cached is None
    assert cache._misses > 0


@pytest.mark.asyncio
async def test_persona_cache_disabled(redis_manager, monkeypatch):
    """Test cache returns None when disabled."""
    # Mock settings to disable cache
    from unittest.mock import Mock

    mock_cache_config = Mock()
    mock_cache_config.persona_cache_enabled = False
    mock_cache_config.persona_cache_ttl_seconds = 604800  # 7 days
    mock_cache_config.persona_cache_similarity_threshold = 0.90

    mock_settings = Mock()
    mock_settings.cache = mock_cache_config

    monkeypatch.setattr("bo1.agents.persona_cache.get_settings", lambda: mock_settings)

    cache = PersonaSelectionCache(redis_manager)

    problem = SubProblem(
        id="sp_001",
        goal="Test problem",
        context="Test context",
        complexity_score=5,
    )

    cached = await cache.get_cached_personas(problem)

    assert cached is None
    assert cache.enabled is False


def test_persona_cache_get_stats(redis_manager):
    """Test cache statistics calculation."""
    cache = PersonaSelectionCache(redis_manager)

    # Simulate hits and misses
    cache._hits = 7
    cache._misses = 3

    stats = cache.get_stats()

    assert stats["hits"] == 7
    assert stats["misses"] == 3
    assert stats["hit_rate"] == pytest.approx(0.7)
    assert stats["similarity_threshold"] == 0.90
    assert stats["ttl_days"] == 7
    assert isinstance(stats["enabled"], bool)  # May be True or False depending on settings


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_persona_cache_multiple_entries(redis_manager):
    """Test cache searches across multiple entries for best match."""
    cache = PersonaSelectionCache(redis_manager)

    # Clear cache
    keys = redis_manager.redis.keys("personas:cache:*")
    if keys:
        redis_manager.redis.delete(*keys)

    # Cache multiple different problems
    problem1 = SubProblem(
        id="sp_001",
        goal="Should we raise prices by 20%?",
        context="SaaS pricing",
        complexity_score=5,
    )

    problem2 = SubProblem(
        id="sp_002",
        goal="Should we hire a VP of Sales?",
        context="Sales team expansion",
        complexity_score=6,
    )

    personas_pricing = [
        PersonaProfile(
            code="finance_strategist",
            name="Maria",
            role="CFO",
            description="Finance",
            expertise_areas=["finance"],
            category="finance",
            system_prompt="Test",
        )
    ]

    personas_hiring = [
        PersonaProfile(
            code="operations_leader",
            name="Ops Lead",
            role="COO",
            description="Operations",
            expertise_areas=["operations"],
            category="operations",
            system_prompt="Test",
        )
    ]

    await cache.cache_persona_selection(problem1, personas_pricing)
    await cache.cache_persona_selection(problem2, personas_hiring)

    # Query similar to problem1 (pricing)
    query = SubProblem(
        id="sp_003",
        goal="Should we increase our pricing?",
        context="Pricing strategy",
        complexity_score=5,
    )

    cached = await cache.get_cached_personas(query)

    # Should match pricing problem, not hiring
    assert cached is not None
    assert cached[0].code == "finance_strategist"


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_persona_cache_error_handling(redis_manager, monkeypatch):
    """Test cache handles errors gracefully."""
    cache = PersonaSelectionCache(redis_manager)

    # Mock generate_embedding to raise error
    async def mock_generate_embedding(*args, **kwargs):
        raise Exception("Embedding API error")

    monkeypatch.setattr("bo1.agents.persona_cache.generate_embedding", mock_generate_embedding)

    problem = SubProblem(
        id="sp_001",
        goal="Test problem",
        context="Test",
        complexity_score=5,
    )

    # Should return None and not crash
    cached = await cache.get_cached_personas(problem)

    assert cached is None
    assert cache._misses == 1  # Counted as miss
