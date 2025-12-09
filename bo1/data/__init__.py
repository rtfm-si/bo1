"""Data module for Board of One.

This module contains static data files used by the application,
including the persona catalog and configuration data.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bo1.models.persona import PersonaProfile

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


@lru_cache(maxsize=256)
def get_persona_by_code(code: str) -> dict[str, Any] | None:
    """Get a single persona by their code.

    Args:
        code: Persona code (e.g., "growth_hacker", "finance_strategist")

    Returns:
        Persona dictionary or None if not found

    Note:
        Uses lru_cache for O(1) repeated lookups during meeting execution.
        First call performs O(n) scan; subsequent calls return cached result.
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
    """Get all active standard personas for expert selection.

    Filters by:
    - is_active=True (persona is enabled)
    - persona_type="standard" (excludes meta, moderator, research personas)

    This ensures only regular experts are available for LLM selection,
    excluding facilitators, moderators, and research personas which have
    special roles in the deliberation process.

    Returns:
        List of active standard persona dictionaries
    """
    personas = load_personas()  # Returns tuple from cache
    return [p for p in personas if p.get("is_active", True) and p.get("persona_type") == "standard"]


@lru_cache(maxsize=256)
def get_persona_profile_by_code(code: str) -> "PersonaProfile | None":
    """Get a PersonaProfile instance by code, with caching.

    This factory caches constructed PersonaProfile objects to avoid repeated
    Pydantic validation during meeting execution when the same persona is
    referenced multiple times (e.g., across rounds).

    Args:
        code: Persona code (e.g., "growth_hacker", "finance_strategist")

    Returns:
        Cached PersonaProfile instance or None if not found

    Note:
        First call constructs and caches the model; subsequent calls return
        the same instance. Safe because PersonaProfile is treated as immutable.
    """
    from bo1.models.persona import PersonaProfile

    persona_dict = get_persona_by_code(code)
    if persona_dict is None:
        return None
    return PersonaProfile.model_validate(persona_dict)
