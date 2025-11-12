"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_llm: mark test as requiring LLM API keys (deselect with '-m \"not requires_llm\"')",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test",
    )


@pytest.fixture
def personas_path() -> Path:
    """Get path to personas.json file."""
    bo1_dir = Path(__file__).parent.parent / "bo1"
    return bo1_dir / "data" / "personas.json"
