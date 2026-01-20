"""Auth provider repository for account linking.

Handles:
- Linking multiple auth methods to a primary user
- Email verification token management
- Primary user lookup by email

Security model:
- OAuth providers (google, linkedin, github) = trusted email verification
- Email/Password = MUST verify email before access
- Passwordless (magic link) = clicking link = email verified
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Email verification token expiry (24 hours)
VERIFICATION_TOKEN_EXPIRY_HOURS = 24

# Trusted OAuth providers that verify email addresses
TRUSTED_OAUTH_PROVIDERS = {"google", "linkedin", "github", "twitter", "bluesky"}


class AuthProviderRepository(BaseRepository):
    """Repository for auth provider linking and email verification."""

    # =========================================================================
    # Primary User Lookup
    # =========================================================================

    def get_primary_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Find existing primary user by email (case-insensitive).

        Args:
            email: Email address to search

        Returns:
            Dict with primary_user_id, provider, email_verified, or None if not found
        """
        return self._execute_one(
            """
            SELECT primary_user_id, provider, email_verified, linked_at
            FROM user_auth_providers
            WHERE LOWER(email) = LOWER(%s)
            ORDER BY linked_at ASC
            LIMIT 1
            """,
            (email,),
        )

    def get_provider_by_st_user_id(self, st_user_id: str) -> dict[str, Any] | None:
        """Lookup provider record by SuperTokens user ID.

        Args:
            st_user_id: SuperTokens user ID

        Returns:
            Provider record dict or None if not found
        """
        return self._execute_one(
            """
            SELECT id, primary_user_id, supertokens_user_id, provider,
                   email, email_verified, linked_at, last_used_at, created_at
            FROM user_auth_providers
            WHERE supertokens_user_id = %s
            """,
            (st_user_id,),
        )

    def get_providers_for_user(self, primary_user_id: str) -> list[dict[str, Any]]:
        """Get all linked auth providers for a primary user.

        Args:
            primary_user_id: Primary user ID

        Returns:
            List of provider records
        """
        return self._execute_query(
            """
            SELECT id, supertokens_user_id, provider, email,
                   email_verified, linked_at, last_used_at
            FROM user_auth_providers
            WHERE primary_user_id = %s
            ORDER BY linked_at ASC
            """,
            (primary_user_id,),
            user_id=primary_user_id,
        )

    # =========================================================================
    # Provider Record Management
    # =========================================================================

    def create_provider_record(
        self,
        primary_user_id: str,
        supertokens_user_id: str,
        provider: str,
        email: str,
        email_verified: bool = False,
    ) -> dict[str, Any]:
        """Create a new auth provider record.

        Args:
            primary_user_id: The canonical user ID for this account
            supertokens_user_id: SuperTokens recipe user ID
            provider: Auth provider name (google, linkedin, github, email, passwordless)
            email: Email address used with this provider
            email_verified: Whether email is verified (True for OAuth, depends for others)

        Returns:
            Created provider record
        """
        return self._execute_returning(
            """
            INSERT INTO user_auth_providers
                (primary_user_id, supertokens_user_id, provider, email, email_verified)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (supertokens_user_id) DO UPDATE SET
                last_used_at = NOW()
            RETURNING id, primary_user_id, supertokens_user_id, provider,
                      email, email_verified, linked_at, last_used_at, created_at
            """,
            (primary_user_id, supertokens_user_id, provider, email, email_verified),
        )

    def link_provider_to_user(
        self,
        primary_user_id: str,
        supertokens_user_id: str,
        provider: str,
        email: str,
        email_verified: bool = False,
    ) -> dict[str, Any]:
        """Link an auth provider to an existing primary user.

        This is called when a user signs up with a different auth method
        but same email as an existing account.

        Args:
            primary_user_id: Existing primary user ID to link to
            supertokens_user_id: New SuperTokens recipe user ID
            provider: Auth provider name
            email: Email address
            email_verified: Whether email is verified

        Returns:
            Created provider record
        """
        logger.info(
            f"Linking {provider} provider to existing user {primary_user_id[:8]}... "
            f"(st_user_id: {supertokens_user_id[:8]}..., verified: {email_verified})"
        )
        return self.create_provider_record(
            primary_user_id=primary_user_id,
            supertokens_user_id=supertokens_user_id,
            provider=provider,
            email=email,
            email_verified=email_verified,
        )

    def update_last_used(self, supertokens_user_id: str) -> bool:
        """Update last_used_at timestamp for a provider.

        Args:
            supertokens_user_id: SuperTokens user ID

        Returns:
            True if updated
        """
        count = self._execute_count(
            """
            UPDATE user_auth_providers
            SET last_used_at = NOW()
            WHERE supertokens_user_id = %s
            """,
            (supertokens_user_id,),
        )
        return count > 0

    # =========================================================================
    # Email Verification
    # =========================================================================

    def mark_email_verified(self, supertokens_user_id: str) -> bool:
        """Mark a provider's email as verified.

        Also updates the primary user's email_verified_at if not already set.

        Args:
            supertokens_user_id: SuperTokens user ID

        Returns:
            True if updated
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Update provider record
                cur.execute(
                    """
                    UPDATE user_auth_providers
                    SET email_verified = true
                    WHERE supertokens_user_id = %s
                    RETURNING primary_user_id
                    """,
                    (supertokens_user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return False

                primary_user_id = row["primary_user_id"]

                # Also update user's email_verified_at if not set
                cur.execute(
                    """
                    UPDATE users
                    SET email_verified_at = NOW(), updated_at = NOW()
                    WHERE id = %s AND email_verified_at IS NULL
                    """,
                    (primary_user_id,),
                )

                logger.info(f"Marked email verified for ST user {supertokens_user_id[:8]}...")
                return True

    def get_unverified_by_email(self, email: str) -> dict[str, Any] | None:
        """Get unverified provider record by email.

        Args:
            email: Email address

        Returns:
            Provider record or None
        """
        return self._execute_one(
            """
            SELECT id, primary_user_id, supertokens_user_id, provider, email
            FROM user_auth_providers
            WHERE LOWER(email) = LOWER(%s)
              AND email_verified = false
              AND provider = 'email'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (email,),
        )

    # =========================================================================
    # Verification Token Management
    # =========================================================================

    def create_verification_token(self, supertokens_user_id: str, email: str) -> str:
        """Create a new email verification token.

        Args:
            supertokens_user_id: SuperTokens user ID
            email: Email address to verify

        Returns:
            Verification token (64-char secure random string)
        """
        token = secrets.token_urlsafe(48)  # 64 chars
        expires_at = datetime.now(UTC) + timedelta(hours=VERIFICATION_TOKEN_EXPIRY_HOURS)

        with db_session() as conn:
            with conn.cursor() as cur:
                # Invalidate any existing tokens for this user/email
                cur.execute(
                    """
                    UPDATE email_verifications
                    SET verified_at = NOW()
                    WHERE supertokens_user_id = %s
                      AND verified_at IS NULL
                    """,
                    (supertokens_user_id,),
                )

                # Create new token
                cur.execute(
                    """
                    INSERT INTO email_verifications
                        (supertokens_user_id, email, token, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (supertokens_user_id, email, token, expires_at),
                )

        logger.info(f"Created verification token for {email[:3]}***")
        return token

    def get_verification_by_token(self, token: str) -> dict[str, Any] | None:
        """Get verification record by token.

        Args:
            token: Verification token

        Returns:
            Verification record or None
        """
        return self._execute_one(
            """
            SELECT id, supertokens_user_id, email, token,
                   expires_at, verified_at, created_at
            FROM email_verifications
            WHERE token = %s
            """,
            (token,),
        )

    def mark_token_verified(self, token: str) -> bool:
        """Mark a verification token as used.

        Args:
            token: Verification token

        Returns:
            True if marked as verified
        """
        count = self._execute_count(
            """
            UPDATE email_verifications
            SET verified_at = NOW()
            WHERE token = %s AND verified_at IS NULL
            """,
            (token,),
        )
        return count > 0

    def check_recent_verification_sent(self, email: str, seconds: int = 60) -> bool:
        """Check if a verification email was sent recently (rate limiting).

        Args:
            email: Email address
            seconds: Cooldown period in seconds

        Returns:
            True if a token was created within the cooldown period
        """
        row = self._execute_one(
            """
            SELECT id FROM email_verifications
            WHERE LOWER(email) = LOWER(%s)
              AND created_at > NOW() - INTERVAL '%s seconds'
            LIMIT 1
            """,
            (email, seconds),
        )
        return row is not None

    def cleanup_expired_tokens(self) -> int:
        """Delete expired verification tokens.

        Returns:
            Number of tokens deleted
        """
        return self._execute_count(
            """
            DELETE FROM email_verifications
            WHERE expires_at < NOW()
              AND verified_at IS NULL
            """,
        )


# Singleton instance
auth_provider_repository = AuthProviderRepository()
