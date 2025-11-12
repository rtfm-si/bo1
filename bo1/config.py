"""Configuration management for Board of One.

Loads settings from environment variables and .env file.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM API Keys
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    voyage_api_key: str = Field(..., description="Voyage AI API key for embeddings")

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")

    # Development Settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # Cost Limits
    max_cost_per_session: float = Field(
        default=1.00, description="Maximum cost per session in USD"
    )

    # A/B Testing
    ab_testing_enabled: bool = Field(default=True, description="Enable A/B testing")

    # Paths
    @property
    def personas_path(self) -> Path:
        """Path to personas.json file."""
        return Path(__file__).parent / "data" / "personas.json"

    @property
    def exports_path(self) -> Path:
        """Path to exports directory."""
        path = Path(__file__).parent.parent / "exports"
        path.mkdir(exist_ok=True)
        return path


# Model configurations (Day 19-20 optimization)
# Research shows Sonnet + caching is cheaper than Haiku for personas
MODEL_BY_ROLE = {
    "PERSONA": "claude-sonnet-4-5-20250929",  # Sonnet 4.5 with caching
    "FACILITATOR": "claude-sonnet-4-5-20250929",  # Needs reasoning
    "SUMMARIZER": "claude-haiku-4-5-20251001",  # Haiku 4.5 for simple compression
    "DECOMPOSER": "claude-sonnet-4-5-20250929",  # Complex analysis
    "MODERATOR": "claude-haiku-4-5-20251001",  # Simple interventions
    "RESEARCHER": "claude-haiku-4-5-20251001",  # Future feature
}

# Model pricing (per 1M tokens, current as of 2025)
# Source: https://docs.claude.com/en/docs/about-claude/models/overview
# Caching: https://claude.com/pricing
MODEL_PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,  # $3 per 1M input tokens
        "output": 15.00,  # $15 per 1M output tokens
        "cache_creation": 3.75,  # $3.75 per 1M cache write (≤200K prompts)
        "cache_read": 0.30,  # $0.30 per 1M cache read (90% cheaper!)
        "context_window": 200_000,  # 200K tokens
        "max_output": 64_000,  # 64K tokens
    },
    "claude-haiku-4-5-20251001": {
        "input": 1.00,  # $1 per 1M input tokens
        "output": 5.00,  # $5 per 1M output tokens
        "cache_creation": 1.25,  # $1.25 per 1M cache write
        "cache_read": 0.10,  # $0.10 per 1M cache read
        "context_window": 200_000,  # 200K tokens
        "max_output": 64_000,  # 64K tokens
    },
    # Model aliases (for convenience)
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5": "claude-haiku-4-5-20251001",
}


def get_settings() -> Settings:
    """Get settings instance (lazy loaded)."""
    return Settings()  # type: ignore[call-arg]


def get_model_for_role(role: str) -> str:
    """Get the model ID for a given role.

    Args:
        role: Role name (e.g., 'PERSONA', 'FACILITATOR')

    Returns:
        Model ID string

    Raises:
        ValueError: If role is not recognized
    """
    if role not in MODEL_BY_ROLE:
        raise ValueError(f"Unknown role: {role}. Valid roles: {list(MODEL_BY_ROLE.keys())}")
    return MODEL_BY_ROLE[role]


def calculate_cost(
    model_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Calculate cost for an LLM call.

    Args:
        model_id: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Number of cache creation tokens
        cache_read_tokens: Number of cache read tokens

    Returns:
        Total cost in USD
    """
    if model_id not in MODEL_PRICING:
        raise ValueError(f"Unknown model: {model_id}")

    pricing = MODEL_PRICING[model_id]

    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
        + (cache_creation_tokens / 1_000_000) * pricing["cache_creation"]
        + (cache_read_tokens / 1_000_000) * pricing["cache_read"]
    )

    return cost
