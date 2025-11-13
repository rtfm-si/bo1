"""Data module for Board of One.

This module contains static data files used by the application,
including the persona catalog and configuration data.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directory containing data files
DATA_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_personas() -> tuple[dict[str, Any], ...]:
    """Load the persona catalog from personas.json.

    Returns:
        Tuple of persona dictionaries (cached for performance)

    Note:
        Uses lru_cache to avoid reloading the catalog on every call.
        Returns tuple (immutable) for caching to work correctly.
    """
    personas_path = DATA_DIR / "personas.json"
    logger.debug(f"Loading personas from {personas_path}")
    with open(personas_path, encoding="utf-8") as f:
        personas_list: list[dict[str, Any]] = json.load(f)
        logger.info(f"Loaded {len(personas_list)} personas from catalog")
        # Return as tuple for immutability and caching
        return tuple(personas_list)


def get_persona_by_code(code: str) -> dict[str, Any] | None:
    """Get a single persona by their code.

    Args:
        code: Persona code (e.g., "growth_hacker", "finance_strategist")

    Returns:
        Persona dictionary or None if not found
    """
    personas = load_personas()
    persona = next((p for p in personas if p["code"] == code), None)
    if persona:
        logger.debug(f"Found persona: {persona['name']} ({code})")
    else:
        logger.warning(f"Persona not found: {code}")
    return persona


def get_personas_by_category(category: str) -> list[dict[str, Any]]:
    """Get all personas in a specific category.

    Args:
        category: Category name (e.g., "marketing", "finance", "technology")

    Returns:
        List of persona dictionaries in that category
    """
    personas = load_personas()  # Returns tuple from cache
    return [p for p in personas if p.get("category") == category]


def get_active_personas() -> list[dict[str, Any]]:
    """Get all active personas (where is_active=True).

    Returns:
        List of active persona dictionaries
    """
    personas = load_personas()  # Returns tuple from cache
    return [p for p in personas if p.get("is_active", True)]
