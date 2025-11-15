"""
Tests for configuration management.
"""

from pathlib import Path

import pytest

from bo1.config import Settings


@pytest.mark.unit
def test_settings_can_be_created() -> None:
    """Test that Settings can be created with required API keys."""
    settings = Settings(
        anthropic_api_key="test_key",
        voyage_api_key="test_key",
    )
    assert settings.anthropic_api_key == "test_key"
    assert settings.voyage_api_key == "test_key"


@pytest.mark.unit
def test_settings_defaults() -> None:
    """Test default values are set correctly."""
    settings = Settings(
        anthropic_api_key="test_key",
        voyage_api_key="test_key",
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
    )

    assert settings.redis_host == "localhost"
    assert settings.redis_port == 6379
    assert settings.redis_db == 0
    # log_level can be INFO or DEBUG depending on environment (docker-compose.yml sets DEBUG)
    assert settings.log_level in ["INFO", "DEBUG"]
    assert settings.max_cost_per_session == 1.00
    assert settings.ab_testing_enabled is True


@pytest.mark.unit
def test_personas_path_exists(personas_path: Path) -> None:
    """Test that personas.json file exists."""
    assert personas_path.exists()
    assert personas_path.name == "personas.json"
