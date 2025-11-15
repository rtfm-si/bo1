"""Configuration management for Board of One.

Loads settings from environment variables and .env file.
"""

import logging
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

__all__ = [
    "Settings",
    "get_settings",
    "MODEL_ALIASES",
    "MODEL_BY_ROLE",
    "MODEL_PRICING",
    "resolve_model_alias",
    "get_model_for_role",
    "calculate_cost",
]


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
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # PostgreSQL Configuration (v2+, Week 3.5)
    database_url: str = Field(
        default="postgresql://bo1:bo1_dev_password@localhost:5432/boardofone",
        description="PostgreSQL connection URL",
    )

    # Development Settings
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    verbose_libs: bool = Field(
        default=False, description="Show debug logs from third-party libraries"
    )

    # Cost Limits
    max_cost_per_session: float = Field(default=1.00, description="Maximum cost per session in USD")

    # A/B Testing
    ab_testing_enabled: bool = Field(default=True, description="Enable A/B testing")

    # AI Model Override (for testing to avoid expensive model costs)
    ai_override: bool = Field(
        default=False,
        description="Override ALL AI model calls with a cheaper model (for testing)",
    )
    ai_override_model: str = Field(
        default="claude-3-5-haiku-latest",
        description="Model to use when AI_OVERRIDE is True (alias or full ID)",
    )

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


# =============================================================================
# Model Aliases (Simple names that won't change when versions update)
# =============================================================================
# When Haiku 5 or Sonnet 5 are released, just update these mappings.
# All code uses the simple aliases, so no changes needed elsewhere.

MODEL_ALIASES = {
    "sonnet": "claude-sonnet-4-5-20250929",  # Current: Sonnet 4.5 (Sep 2025)
    "haiku": "claude-haiku-4-5-20251001",  # Current: Haiku 4.5 (Oct 2025)
    "opus": "claude-opus-4-1-20250805",  # Current: Opus 4.1 (Aug 2025) - not used in v1
    # Testing aliases (3.5 models - faster and cheaper for testing)
    "claude-3-5-haiku-latest": "claude-3-5-haiku-20241022",  # 3.5 Haiku for testing
}

# =============================================================================
# Model Assignment by Role (Day 19-20 optimization)
# =============================================================================
# Research shows Sonnet + caching is cheaper than Haiku for personas!
# Use simple aliases so code doesn't need updates when models change.

MODEL_BY_ROLE = {
    "persona": "sonnet",  # Needs reasoning, benefits from caching
    "facilitator": "sonnet",  # Complex orchestration decisions
    "summarizer": "haiku",  # Simple compression task
    "decomposer": "sonnet",  # Complex problem analysis
    "selector": "sonnet",  # Complex persona matching analysis
    "moderator": "haiku",  # Simple interventions
    "researcher": "haiku",  # Future feature - simple web searches
}

# =============================================================================
# Model Pricing (per 1M tokens, current as of 2025)
# =============================================================================
# Source: https://docs.claude.com/en/docs/about-claude/models/overview
# Caching: https://claude.com/pricing
#
# NOTE: When updating to new model versions, update MODEL_ALIASES above,
# then add pricing for the new model ID here.

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
    "claude-opus-4-1-20250805": {
        "input": 15.00,  # $15 per 1M input tokens
        "output": 75.00,  # $75 per 1M output tokens
        "cache_creation": 18.75,  # $18.75 per 1M cache write
        "cache_read": 1.50,  # $1.50 per 1M cache read
        "context_window": 200_000,  # 200K tokens
        "max_output": 32_000,  # 32K tokens
    },
    # Claude 3.5 models (for testing - faster and cheaper than 4.5)
    "claude-3-5-haiku-20241022": {
        "input": 0.80,  # $0.80 per 1M input tokens
        "output": 4.00,  # $4.00 per 1M output tokens
        "cache_creation": 1.00,  # $1.00 per 1M cache write
        "cache_read": 0.08,  # $0.08 per 1M cache read
        "context_window": 200_000,  # 200K tokens
        "max_output": 8_000,  # 8K tokens
    },
}


def get_settings() -> Settings:
    """Get settings instance (lazy loaded)."""
    return Settings()  # type: ignore[call-arg]


def resolve_model_alias(model_name: str) -> str:
    """Resolve a model alias to its full model ID.

    If AI_OVERRIDE is enabled, ALL models are overridden with AI_OVERRIDE_MODEL.
    This is useful for testing to avoid expensive model costs.

    Args:
        model_name: Model name (alias like 'sonnet' or full ID)

    Returns:
        Full model ID (or override model if AI_OVERRIDE is True)

    Examples:
        >>> resolve_model_alias("sonnet")
        "claude-sonnet-4-5-20250929"
        >>> resolve_model_alias("claude-sonnet-4-5-20250929")
        "claude-sonnet-4-5-20250929"

        >>> # With AI_OVERRIDE=True and AI_OVERRIDE_MODEL="haiku"
        >>> resolve_model_alias("sonnet")
        "claude-haiku-4-5-20251001"
    """
    # Check for AI override (for testing)
    settings = get_settings()
    if settings.ai_override:
        override_model = settings.ai_override_model
        logger.info(
            f"🔄 AI_OVERRIDE enabled: {model_name} → {override_model} "
            "(using cheaper model for testing)"
        )
        # Resolve the override model (in case it's also an alias)
        if override_model in MODEL_ALIASES:
            return MODEL_ALIASES[override_model]
        return override_model

    # Normal resolution: If it's an alias, resolve it
    if model_name in MODEL_ALIASES:
        return MODEL_ALIASES[model_name]
    # Otherwise, assume it's already a full model ID
    return model_name


def get_model_for_role(role: str) -> str:
    """Get the full model ID for a given role.

    Args:
        role: Role name (e.g., 'PERSONA', 'FACILITATOR')

    Returns:
        Full model ID string (resolved from alias)

    Raises:
        ValueError: If role is not recognized

    Examples:
        >>> get_model_for_role("PERSONA")
        "claude-sonnet-4-5-20250929"
    """
    # Normalize role to lowercase for case-insensitive lookup
    role_lower = role.lower()
    if role_lower not in MODEL_BY_ROLE:
        raise ValueError(f"Unknown role: {role}. Valid roles: {list(MODEL_BY_ROLE.keys())}")

    model_alias = MODEL_BY_ROLE[role_lower]
    return resolve_model_alias(model_alias)


def calculate_cost(
    model_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float:
    """Calculate cost for an LLM call.

    Args:
        model_id: Model identifier (alias like 'sonnet' or full ID)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Number of cache creation tokens
        cache_read_tokens: Number of cache read tokens

    Returns:
        Total cost in USD

    Raises:
        ValueError: If model is not recognized

    Examples:
        >>> calculate_cost("sonnet", input_tokens=1000, output_tokens=200)
        0.006
    """
    # Resolve alias to full model ID
    full_model_id = resolve_model_alias(model_id)

    if full_model_id not in MODEL_PRICING:
        raise ValueError(
            f"Unknown model: {model_id} (resolved to: {full_model_id}). "
            f"Available models: {list(MODEL_PRICING.keys())}"
        )

    pricing = MODEL_PRICING[full_model_id]

    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
        + (cache_creation_tokens / 1_000_000) * pricing["cache_creation"]
        + (cache_read_tokens / 1_000_000) * pricing["cache_read"]
    )

    return cost
