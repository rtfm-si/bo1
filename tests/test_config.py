"""
Tests for configuration management.
"""

from pathlib import Path

import pytest

from bo1.config import Settings


@pytest.mark.unit
def test_settings_has_required_fields():
    """Test that Settings requires necessary API keys."""
    from pydantic import ValidationError

    # This will raise ValidationError if required fields are missing
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # Don't load from .env file


@pytest.mark.unit
def test_settings_defaults():
    """Test default values are set correctly."""
    settings = Settings(
        anthropic_api_key="test_key",
        voyage_api_key="test_key"
    )

    assert settings.redis_host == "localhost"
    assert settings.redis_port == 6379
    assert settings.redis_db == 0
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.max_cost_per_session == 1.00
    assert settings.ab_testing_enabled is True


@pytest.mark.unit
def test_personas_path_exists(personas_path: Path):
    """Test that personas.json file exists."""
    assert personas_path.exists()
    assert personas_path.name == "personas.json"
