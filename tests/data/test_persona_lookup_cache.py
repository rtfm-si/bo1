"""Tests for persona lookup caching in bo1/data/__init__.py.

Tests cover:
- get_persona_by_code() lru_cache behavior
- get_persona_profile_by_code() cached factory
- Cache reuse verification
"""

import pytest

from bo1.data import get_persona_by_code, get_persona_profile_by_code
from bo1.models.persona import PersonaProfile


@pytest.mark.unit
def test_get_persona_by_code_is_cached():
    """Test that get_persona_by_code() uses lru_cache for O(1) repeated lookups."""
    # Clear any existing cache
    get_persona_by_code.cache_clear()

    # First call - should populate cache
    result1 = get_persona_by_code("growth_hacker")
    assert result1 is not None
    assert result1["code"] == "growth_hacker"

    # Check cache info
    cache_info = get_persona_by_code.cache_info()
    assert cache_info.misses >= 1

    # Second call - should hit cache
    result2 = get_persona_by_code("growth_hacker")
    assert result2 is not None

    # Verify cache hit occurred
    cache_info_after = get_persona_by_code.cache_info()
    assert cache_info_after.hits >= 1


@pytest.mark.unit
def test_get_persona_by_code_not_found():
    """Test that get_persona_by_code() returns None for unknown codes."""
    result = get_persona_by_code("nonexistent_persona_xyz")
    assert result is None


@pytest.mark.unit
def test_get_persona_profile_by_code_returns_model():
    """Test that get_persona_profile_by_code() returns a PersonaProfile instance."""
    # Clear cache for clean test
    get_persona_profile_by_code.cache_clear()

    result = get_persona_profile_by_code("growth_hacker")
    assert result is not None
    assert isinstance(result, PersonaProfile)
    assert result.code == "growth_hacker"


@pytest.mark.unit
def test_get_persona_profile_by_code_not_found():
    """Test that get_persona_profile_by_code() returns None for unknown codes."""
    result = get_persona_profile_by_code("nonexistent_persona_xyz")
    assert result is None


@pytest.mark.unit
def test_persona_profile_cache_reuses_instance():
    """Test that get_persona_profile_by_code() returns the same cached instance."""
    # Clear cache for clean test
    get_persona_profile_by_code.cache_clear()

    # First call
    profile1 = get_persona_profile_by_code("growth_hacker")
    assert profile1 is not None

    # Second call - should return same instance (not a new object)
    profile2 = get_persona_profile_by_code("growth_hacker")
    assert profile2 is not None

    # Verify same object (identity check)
    assert profile1 is profile2

    # Verify cache stats
    cache_info = get_persona_profile_by_code.cache_info()
    assert cache_info.hits >= 1


@pytest.mark.unit
def test_persona_profile_cache_different_codes():
    """Test that different persona codes get different cached instances."""
    get_persona_profile_by_code.cache_clear()

    profile1 = get_persona_profile_by_code("growth_hacker")
    profile2 = get_persona_profile_by_code("finance_strategist")

    assert profile1 is not None
    assert profile2 is not None
    assert profile1 is not profile2
    assert profile1.code == "growth_hacker"
    assert profile2.code == "finance_strategist"
