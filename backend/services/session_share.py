"""Session sharing service for generating and managing share tokens.

Provides:
- SessionShareService class for creating, retrieving, and revoking shares
- Token generation and expiry validation
- Background cleanup job for expired shares
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from bo1.utils.logging import get_logger

logger = get_logger(__name__)


class SessionShareService:
    """Manage session sharing via time-limited tokens."""

    TOKEN_LENGTH = 32  # 256-bit entropy
    MAX_TTL_DAYS = 365  # Maximum 1 year

    @staticmethod
    def generate_token() -> str:
        """Generate a random share token.

        Returns:
            URL-safe random token
        """
        return secrets.token_urlsafe(SessionShareService.TOKEN_LENGTH)

    @staticmethod
    def validate_ttl(ttl_days: int) -> int:
        """Validate and normalize TTL in days.

        Args:
            ttl_days: Time-to-live in days

        Returns:
            Validated TTL (capped at MAX_TTL_DAYS)

        Raises:
            ValueError: If TTL is invalid
        """
        if ttl_days <= 0:
            raise ValueError("TTL must be positive")
        if ttl_days > SessionShareService.MAX_TTL_DAYS:
            logger.warning(f"TTL capped to {SessionShareService.MAX_TTL_DAYS} days")
            return SessionShareService.MAX_TTL_DAYS
        return ttl_days

    @staticmethod
    def calculate_expiry(ttl_days: int) -> datetime:
        """Calculate expiry timestamp.

        Args:
            ttl_days: Time-to-live in days

        Returns:
            Expiry datetime in UTC
        """
        return datetime.now(UTC) + timedelta(days=ttl_days)

    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        """Check if share token has expired.

        Args:
            expires_at: Expiry datetime

        Returns:
            True if expired
        """
        return expires_at < datetime.now(UTC)

    @staticmethod
    def format_share_metadata(
        token: str, expires_at: datetime, created_at: datetime
    ) -> dict[str, Any]:
        """Format share metadata for response.

        Args:
            token: Share token
            expires_at: Expiry datetime
            created_at: Creation datetime

        Returns:
            Formatted metadata dict
        """
        return {
            "token": token,
            "expires_at": expires_at.isoformat()
            if isinstance(expires_at, datetime)
            else expires_at,
            "created_at": created_at.isoformat()
            if isinstance(created_at, datetime)
            else created_at,
        }
