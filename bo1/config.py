"""Configuration management for Board of One.

Loads settings from environment variables and .env file.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

__all__ = [
    "Settings",
    "get_settings",
    "reset_settings",
    "CacheConfig",
    "MODEL_ALIASES",
    "MODEL_BY_ROLE",
    "ANTHROPIC_PRICING",
    "VOYAGE_PRICING",
    "BRAVE_PRICING",
    "TAVILY_PRICING",
    "MODEL_PRICING",
    "resolve_model_alias",
    "get_model_for_role",
    "calculate_cost",
    "get_service_pricing",
]


@dataclass
class CacheConfig:
    """Configuration for all cache implementations.

    Centralizes cache settings to eliminate hardcoded values and provide
    single source of truth for cache behavior across LLM, persona, and research caches.

    Attributes:
        llm_cache_enabled: Enable/disable LLM response caching
        llm_cache_ttl_seconds: Time-to-live for LLM cache entries (default: 24 hours)
        persona_cache_enabled: Enable/disable persona selection caching
        persona_cache_similarity_threshold: Cosine similarity threshold for persona cache hits
        persona_cache_ttl_seconds: Time-to-live for persona cache entries (default: 7 days)
        research_cache_similarity_threshold: Cosine similarity threshold for research cache hits
        research_cache_freshness_map: Category-specific freshness policies (days)
        research_cache_default_freshness_days: Default freshness for uncategorized research
    """

    # LLM Response Cache
    llm_cache_enabled: bool = True
    llm_cache_ttl_seconds: int = 24 * 60 * 60  # 24 hours

    # Persona Selection Cache
    persona_cache_enabled: bool = True
    persona_cache_similarity_threshold: float = 0.90  # Higher threshold for accuracy
    persona_cache_ttl_seconds: int = 7 * 24 * 60 * 60  # 7 days

    # Research Cache
    research_cache_similarity_threshold: float = 0.85  # Lower threshold for flexibility
    research_cache_freshness_map: dict[str, int] = field(
        default_factory=lambda: {
            "saas_metrics": 90,  # SaaS metrics updated quarterly
            "pricing": 180,  # Pricing data stable for 6 months
            "competitor_analysis": 30,  # Competitive landscape changes monthly
            "market_trends": 60,  # Market trends updated bimonthly
            "regulations": 365,  # Regulations change annually
        }
    )
    research_cache_default_freshness_days: int = 90  # Default 90-day freshness


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from .env (for v2 API settings)
    )

    # LLM API Keys (optional to allow tests without real keys)
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude")
    voyage_api_key: str = Field(default="", description="Voyage AI API key for embeddings")

    # Research API Keys (for external research features)
    tavily_api_key: str = Field(default="", description="Tavily API key for web search")
    brave_api_key: str = Field(default="", description="Brave Search API key")

    # Email Configuration (Resend)
    resend_api_key: str = Field(default="", description="Resend API key for transactional emails")

    # ntfy Push Notifications
    ntfy_server: str = Field(default="https://ntfy.boardof.one", description="ntfy server URL")
    ntfy_topic_waitlist: str = Field(
        default="", description="ntfy topic for waitlist signup notifications"
    )
    ntfy_topic_meeting: str = Field(
        default="", description="ntfy topic for meeting start notifications"
    )
    ntfy_topic_reports: str = Field(
        default="", description="ntfy topic for daily/weekly database reports"
    )
    ntfy_topic_alerts: str = Field(
        default="", description="ntfy topic for critical database alerts (high priority)"
    )

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str = Field(default="", description="Redis password (if required)")
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

    # Admin Emails (auto-set is_admin=true on login/signup)
    admin_emails: str = Field(
        default="si@boardof.one",
        description="Comma-separated list of emails that should be auto-set as admin on login/signup",
    )

    @property
    def admin_email_set(self) -> set[str]:
        """Parse admin emails into a set of lowercase emails."""
        if self.admin_emails:
            return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}
        return set()

    # Beta Whitelist (Closed Beta Access Control)
    # DEPRECATED: Use database-managed whitelist instead (see backend/api/admin.py)
    # This environment variable approach will be removed in v2.0
    closed_beta_mode: bool = Field(
        default=False,
        description="Enable closed beta mode - only whitelisted emails can authenticate",
    )
    beta_whitelist: str = Field(
        default="",
        description="DEPRECATED: Use database-managed whitelist instead. "
        "Comma-separated list of whitelisted emails for closed beta (e.g., 'alice@example.com,bob@company.com')",
    )

    @property
    def beta_whitelist_emails(self) -> set[str]:
        """Parse beta whitelist into a set of lowercase emails.

        DEPRECATED: This property is deprecated in favor of database-managed whitelist.
        Will be removed in v2.0. Use admin API endpoints to manage whitelist instead.
        """
        if self.beta_whitelist:
            logger.warning(
                "DEPRECATION WARNING: BETA_WHITELIST environment variable is deprecated. "
                "Please migrate to database-managed whitelist using admin API endpoints. "
                "This will be removed in v2.0."
            )

        if not self.beta_whitelist:
            return set()
        return {email.strip().lower() for email in self.beta_whitelist.split(",") if email.strip()}

    # Feature Flags (Sprint Optimizations - Week 1)
    # LLM Response Caching
    enable_llm_response_cache: bool = Field(
        default=False,
        description="Enable LLM response caching with Redis backend (60-80% cost reduction)",
    )
    llm_response_cache_ttl_seconds: int = Field(
        default=86400,  # 24 hours
        description="TTL for cached LLM responses in seconds",
    )

    # Persona Selection Caching
    enable_persona_selection_cache: bool = Field(
        default=False,
        description="Enable semantic persona selection caching (40-60% hit rate, $200-400/month savings)",
    )

    # Context Collection
    enable_context_collection: bool = Field(
        default=True,
        description="Enable business context collection and information gap analysis (improves recommendations by 40%)",
    )

    # SSE Streaming Mode
    enable_sse_streaming: bool = Field(
        default=False,
        description="Enable real-time SSE streaming via LangGraph astream_events (vs polling). See STREAMING_IMPLEMENTATION_PLAN.md",
    )

    # Cache Configuration (Centralized)
    @property
    def cache(self) -> CacheConfig:
        """Get centralized cache configuration.

        This property provides a single source of truth for all cache settings,
        overriding individual cache configuration from environment variables where applicable.

        Returns:
            CacheConfig instance with all cache settings

        Examples:
            >>> settings = get_settings()
            >>> settings.cache.llm_cache_ttl_seconds
            86400
            >>> settings.cache.persona_cache_similarity_threshold
            0.90
        """
        # Create cache config, using env var overrides where available
        return CacheConfig(
            llm_cache_enabled=self.enable_llm_response_cache,
            llm_cache_ttl_seconds=self.llm_response_cache_ttl_seconds,
            persona_cache_enabled=self.enable_persona_selection_cache,
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
    # Primary aliases - use these throughout the codebase
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

# =============================================================================
# AI SERVICE PRICING - Anthropic Models (per 1M tokens)
# Last updated: 2025-11-28
# Source: https://docs.claude.com/en/docs/about-claude/models/overview
# =============================================================================

ANTHROPIC_PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,  # $3 per 1M input tokens
        "output": 15.00,  # $15 per 1M output tokens
        "cache_write": 3.75,  # $3.75 per 1M cache write (25% of input)
        "cache_read": 0.30,  # $0.30 per 1M cache read (90% cheaper)
    },
    "claude-haiku-4-5-20251001": {
        "input": 1.00,  # $1 per 1M input tokens
        "output": 5.00,  # $5 per 1M output tokens
        "cache_write": 1.25,  # $1.25 per 1M cache write (25% of input)
        "cache_read": 0.10,  # $0.10 per 1M cache read (90% cheaper)
    },
    "claude-opus-4-20250514": {
        "input": 15.00,  # $15 per 1M input tokens
        "output": 75.00,  # $75 per 1M output tokens
        "cache_write": 18.75,  # $18.75 per 1M cache write (25% of input)
        "cache_read": 1.50,  # $1.50 per 1M cache read (90% cheaper)
    },
    # Claude 3.5 models (for testing - faster and cheaper than 4.5)
    "claude-3-5-haiku-20241022": {
        "input": 0.80,  # $0.80 per 1M input tokens
        "output": 4.00,  # $4.00 per 1M output tokens
        "cache_write": 1.00,  # $1.00 per 1M cache write (25% of input)
        "cache_read": 0.08,  # $0.08 per 1M cache read (90% cheaper)
    },
}

# =============================================================================
# AI SERVICE PRICING - Voyage AI Embeddings (per 1M tokens)
# Last updated: 2025-11-28
# Source: https://www.voyageai.com/pricing
# =============================================================================

VOYAGE_PRICING = {
    "voyage-3": {"embedding": 0.06},  # $0.06 per 1M tokens
    "voyage-3-lite": {"embedding": 0.02},  # $0.02 per 1M tokens (cheapest)
    "voyage-3-large": {"embedding": 0.18},  # $0.18 per 1M tokens (most capable)
}

# =============================================================================
# AI SERVICE PRICING - Web Search APIs
# Last updated: 2025-11-28
# =============================================================================

BRAVE_PRICING = {
    "web_search": 0.003,  # $0.003 per query
    "ai_search": 0.005,  # $0.005 per query
}

TAVILY_PRICING = {
    "basic_search": 0.001,  # $0.001 per query
    "advanced_search": 0.002,  # $0.002 per query
}

# =============================================================================
# MODEL PRICING - Backward compatibility (maps to ANTHROPIC_PRICING with metadata)
# =============================================================================
# Used by calculate_cost() and existing code. Includes context_window and max_output
# for reference. New code should use ANTHROPIC_PRICING and get_service_pricing().

MODEL_PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,
        "output": 15.00,
        "cache_creation": 3.75,
        "cache_read": 0.30,
        "context_window": 200_000,
        "max_output": 64_000,
    },
    "claude-haiku-4-5-20251001": {
        "input": 1.00,
        "output": 5.00,
        "cache_creation": 1.25,
        "cache_read": 0.10,
        "context_window": 200_000,
        "max_output": 64_000,
    },
    "claude-opus-4-1-20250805": {
        "input": 15.00,
        "output": 75.00,
        "cache_creation": 18.75,
        "cache_read": 1.50,
        "context_window": 200_000,
        "max_output": 32_000,
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.80,
        "output": 4.00,
        "cache_creation": 1.00,
        "cache_read": 0.08,
        "context_window": 200_000,
        "max_output": 8_000,
    },
}


# Global singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get settings instance (singleton, lazy loaded)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (for testing only).

    This allows tests to reload settings with different environment variables
    or to ensure a clean state between tests.
    """
    global _settings
    _settings = None


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
        logger.debug(
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


def get_service_pricing(provider: str, model: str | None = None, operation: str = "") -> float:
    """Get price per unit for any AI service.

    Supports pricing lookup across all AI services: Anthropic, Voyage, Brave, Tavily.

    Args:
        provider: Service provider ('anthropic', 'voyage', 'brave', 'tavily')
        model: Model identifier (e.g., 'claude-sonnet-4-5-20250929', 'voyage-3')
               Required for 'anthropic' and 'voyage', optional for others
        operation: Operation type ('input', 'output', 'cache_write', 'cache_read', 'embedding', etc.)

    Returns:
        Price per unit (usually per 1M tokens or per query) in USD

    Raises:
        ValueError: If provider/model/operation combination is not recognized

    Examples:
        >>> get_service_pricing("anthropic", "claude-haiku-4-5-20251001", "input")
        1.00
        >>> get_service_pricing("voyage", "voyage-3-lite", "embedding")
        0.02
        >>> get_service_pricing("brave", operation="web_search")
        0.003
        >>> get_service_pricing("tavily", operation="advanced_search")
        0.002
    """
    provider_lower = provider.lower()

    if provider_lower == "anthropic":
        if not model:
            raise ValueError("'model' is required for anthropic provider")
        # Resolve alias to full model ID
        full_model_id = resolve_model_alias(model)
        if full_model_id not in ANTHROPIC_PRICING:
            raise ValueError(
                f"Unknown Anthropic model: {model} (resolved to: {full_model_id}). "
                f"Available models: {list(ANTHROPIC_PRICING.keys())}"
            )
        if operation not in ANTHROPIC_PRICING[full_model_id]:
            raise ValueError(
                f"Unknown operation '{operation}' for model {full_model_id}. "
                f"Available operations: {list(ANTHROPIC_PRICING[full_model_id].keys())}"
            )
        return ANTHROPIC_PRICING[full_model_id][operation]

    elif provider_lower == "voyage":
        if not model:
            raise ValueError("'model' is required for voyage provider")
        if model not in VOYAGE_PRICING:
            raise ValueError(
                f"Unknown Voyage model: {model}. Available models: {list(VOYAGE_PRICING.keys())}"
            )
        if operation not in VOYAGE_PRICING[model]:
            raise ValueError(
                f"Unknown operation '{operation}' for model {model}. "
                f"Available operations: {list(VOYAGE_PRICING[model].keys())}"
            )
        return VOYAGE_PRICING[model][operation]

    elif provider_lower == "brave":
        if operation not in BRAVE_PRICING:
            raise ValueError(
                f"Unknown Brave operation: {operation}. "
                f"Available operations: {list(BRAVE_PRICING.keys())}"
            )
        return BRAVE_PRICING[operation]

    elif provider_lower == "tavily":
        if operation not in TAVILY_PRICING:
            raise ValueError(
                f"Unknown Tavily operation: {operation}. "
                f"Available operations: {list(TAVILY_PRICING.keys())}"
            )
        return TAVILY_PRICING[operation]

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available providers: ['anthropic', 'voyage', 'brave', 'tavily']"
        )
