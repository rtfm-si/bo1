"""Persona domain models for Board of One.

Defines persona profiles and their attributes.
"""

import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonaType(str, Enum):
    """Type of persona."""

    STANDARD = "standard"
    MODERATOR = "moderator"
    FACILITATOR = "facilitator"
    RESEARCH = "research"
    META = "meta"


class ResponseStyle(str, Enum):
    """Communication style of the persona."""

    TECHNICAL = "technical"
    ANALYTICAL = "analytical"
    NARRATIVE = "narrative"
    SOCRATIC = "socratic"


class PersonaCategory(str, Enum):
    """Domain category for the persona."""

    MARKETING = "marketing"
    FINANCE = "finance"
    LEGAL = "legal"
    PRODUCT = "product"
    TECH = "tech"
    OPS = "ops"
    LEADERSHIP = "leadership"
    DATA = "data"
    SALES = "sales"
    STRATEGY = "strategy"
    CUSTOMER = "customer"
    INNOVATION = "innovation"
    WELLNESS = "wellness"
    ETHICS = "ethics"
    COMMUNITY = "community"
    META = "meta"
    MASKED = "masked"


class PersonaTraits(BaseModel):
    """Personality traits that influence persona behavior."""

    creative: float = Field(..., ge=0.0, le=1.0, description="Creativity level (0-1)")
    analytical: float = Field(..., ge=0.0, le=1.0, description="Analytical thinking level (0-1)")
    optimistic: float = Field(..., ge=0.0, le=1.0, description="Optimism level (0-1)")
    risk_averse: float = Field(..., ge=0.0, le=1.0, description="Risk aversion level (0-1)")
    detail_oriented: float = Field(
        ..., ge=0.0, le=1.0, description="Detail orientation level (0-1)"
    )


class PersonaProfile(BaseModel):
    """Complete profile for an expert persona."""

    id: str = Field(..., description="Unique identifier (UUID)")
    code: str = Field(..., description="Unique code for this persona (e.g., 'growth_hacker')")
    name: str = Field(..., description="Full name of the persona")
    archetype: str = Field(..., description="Role archetype (e.g., 'Growth Hacker')")
    category: PersonaCategory = Field(..., description="Domain category")
    description: str = Field(..., description="Description of persona's expertise and value")
    emoji: str = Field(..., description="Emoji representation")
    color_hex: str = Field(..., description="Color hex code for UI display")
    traits: dict[str, float] | PersonaTraits = Field(
        ..., description="Personality traits (can be dict or PersonaTraits object)"
    )
    default_weight: float = Field(
        ..., ge=0.0, le=2.0, description="Default voting weight (0-2, typically 0.8-1.2)"
    )
    temperature: float = Field(..., ge=0.0, le=2.0, description="LLM temperature for this persona")
    system_prompt: str = Field(
        ...,
        description="Bespoke system prompt defining persona's identity and role (XML format)",
    )
    response_style: ResponseStyle = Field(..., description="Communication style")
    is_active: bool = Field(default=True, description="Whether this persona is available for use")
    persona_type: PersonaType = Field(default=PersonaType.STANDARD, description="Type of persona")
    is_visible: bool = Field(default=True, description="Whether this persona is visible in UI")
    display_name: str = Field(..., description="Short display name (e.g., 'Zara')")
    domain_expertise: list[str] | str = Field(
        ..., description="Areas of domain expertise (can be list or postgres array string)"
    )

    @property
    def domain(self) -> str:
        """Primary domain from archetype or category."""
        return self.archetype

    @field_validator("traits", mode="before")
    @classmethod
    def parse_traits(cls, v: Any) -> dict[str, float] | PersonaTraits:
        """Parse traits from JSON string or dict."""
        if isinstance(v, str):
            # Parse JSON string to dict
            parsed: dict[str, float] = json.loads(v)
            return parsed
        result: dict[str, float] | PersonaTraits = v
        return result

    @field_validator("domain_expertise", mode="before")
    @classmethod
    def parse_domain_expertise(cls, v: Any) -> list[str] | str:
        """Parse domain expertise from PostgreSQL array format if needed."""
        if isinstance(v, str) and v.startswith("{"):
            # PostgreSQL array format: {technical,strategic}
            parsed_list: list[str] = [e.strip() for e in v.strip("{}").split(",")]
            return parsed_list
        result: list[str] | str = v
        return result

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "9e9979e7-4a97-441c-b5ef-59c93326a2aa",
                    "code": "growth_hacker",
                    "name": "Zara Morales",
                    "archetype": "Growth Hacker",
                    "category": "marketing",
                    "description": "Growth experimentation expert focusing on user acquisition",
                    "emoji": "📈",
                    "color_hex": "#EF4444",
                    "traits": {
                        "creative": 0.9,
                        "analytical": 0.7,
                        "optimistic": 0.8,
                        "risk_averse": 0.2,
                        "detail_oriented": 0.4,
                    },
                    "default_weight": 0.9,
                    "temperature": 0.85,
                    "system_prompt": "<system_role>You are Zara Morales...</system_role>",
                    "response_style": "technical",
                    "is_active": True,
                    "persona_type": "standard",
                    "is_visible": True,
                    "display_name": "Zara",
                    "domain_expertise": ["technical", "strategic"],
                }
            ]
        }
    )

    def get_traits(self) -> PersonaTraits:
        """Get traits as PersonaTraits object.

        Returns:
            PersonaTraits object (converts from dict if necessary)
        """
        if isinstance(self.traits, PersonaTraits):
            return self.traits
        # Convert dict to PersonaTraits
        return PersonaTraits(**self.traits)

    def get_expertise_list(self) -> list[str]:
        """Get domain expertise as a list.

        Returns:
            List of expertise areas
        """
        if isinstance(self.domain_expertise, list):
            return self.domain_expertise
        # Parse PostgreSQL array format: {technical,strategic} -> ["technical", "strategic"]
        expertise_str = self.domain_expertise.strip("{}")
        return [e.strip() for e in expertise_str.split(",") if e.strip()]
