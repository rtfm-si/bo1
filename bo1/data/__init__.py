"""Data module for Board of One.

This module contains static data files used by the application,
including the persona catalog and configuration data.
"""

import json
from pathlib import Path
from typing import Any

# Directory containing data files
DATA_DIR = Path(__file__).parent


def load_personas() -> list[dict[str, Any]]:
    """Load the persona catalog from personas.json.

    Returns:
        List of persona dictionaries with all persona attributes
    """
    personas_path = DATA_DIR / "personas.json"
    with open(personas_path, encoding="utf-8") as f:
        result: list[dict[str, Any]] = json.load(f)
        return result


def get_persona_by_code(code: str) -> dict[str, Any] | None:
    """Get a single persona by their code.

    Args:
        code: Persona code (e.g., "growth_hacker", "finance_strategist")

    Returns:
        Persona dictionary or None if not found
    """
    personas = load_personas()
    return next((p for p in personas if p["code"] == code), None)


def get_personas_by_category(category: str) -> list[dict[str, Any]]:
    """Get all personas in a specific category.

    Args:
        category: Category name (e.g., "marketing", "finance", "technology")

    Returns:
        List of persona dictionaries in that category
    """
    personas = load_personas()
    return [p for p in personas if p.get("category") == category]


def get_active_personas() -> list[dict[str, Any]]:
    """Get all active personas (where is_active=True).

    Returns:
        List of active persona dictionaries
    """
    personas = load_personas()
    return [p for p in personas if p.get("is_active", True)]
