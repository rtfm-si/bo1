"""
Pytest configuration and shared fixtures.
"""

from pathlib import Path

import pytest


@pytest.fixture
def personas_path() -> Path:
    """Path to personas.json file."""
    return Path(__file__).parent.parent / "zzz_important" / "personas.json"


@pytest.fixture
def sample_problem() -> str:
    """Sample problem for testing."""
    return (
        "I'm a solopreneur building a SaaS product. "
        "Should I focus on acquiring more customers or improving the product?"
    )
