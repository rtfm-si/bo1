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
        return Path(__file__).parent.parent / "zzz_important" / "personas.json"

    @property
    def exports_path(self) -> Path:
        """Path to exports directory."""
        path = Path(__file__).parent.parent / "exports"
        path.mkdir(exist_ok=True)
        return path


def get_settings() -> Settings:
    """Get settings instance (lazy loaded)."""
    return Settings()  # type: ignore[call-arg]
