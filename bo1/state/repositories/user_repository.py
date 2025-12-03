"""User repository for user and context operations.

Handles:
- User CRUD operations
- Business context management
- Admin detection and email sync
"""

import logging
from typing import Any

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """Repository for user data and business context."""

    # =========================================================================
    # User CRUD
    # =========================================================================

    def ensure_exists(
        self,
        user_id: str,
        email: str | None = None,
        auth_provider: str = "supertokens",
        subscription_tier: str = "free",
    ) -> bool:
        """Ensure a user exists in the PostgreSQL users table.

        Creates the user if they don't exist, or updates their info if they do.
        This is critical for FK constraints - sessions require a valid user_id.

        When updating existing users:
        - Real emails (not @placeholder.local) always replace placeholder emails
        - auth_provider is updated when a real email is provided (OAuth sync)
        - Placeholder emails never overwrite real emails
        - Admin status is auto-set if email is in ADMIN_EMAILS config

        Args:
            user_id: User identifier (from SuperTokens or auth provider)
            email: User email (optional, may not be available from all providers)
            auth_provider: Authentication provider (default: supertokens)
            subscription_tier: Subscription tier (default: free)

        Returns:
            True if user exists or was created successfully
        """
        from bo1.config import get_settings

        settings = get_settings()

        # Determine if this is a real email or placeholder
        is_real_email = email is not None and not email.endswith("@placeholder.local")
        final_email = email or f"{user_id}@placeholder.local"

        # Check if email should be auto-admin
        is_admin = is_real_email and final_email.lower() in settings.admin_email_set

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    if is_real_email:
                        # Real email from OAuth - always update email and auth_provider
                        cur.execute(
                            """
                            INSERT INTO users (id, email, auth_provider, subscription_tier, is_admin)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE
                            SET email = EXCLUDED.email,
                                auth_provider = EXCLUDED.auth_provider,
                                is_admin = CASE
                                    WHEN EXCLUDED.is_admin = true THEN true
                                    ELSE users.is_admin
                                END,
                                updated_at = NOW()
                            """,
                            (user_id, final_email, auth_provider, subscription_tier, is_admin),
                        )
                        if is_admin:
                            logger.info(f"User {user_id} ({final_email}) auto-set as admin")
                        else:
                            logger.info(f"User {user_id} synced with real email ({auth_provider})")
                    else:
                        # Placeholder email - only insert, don't overwrite real data
                        cur.execute(
                            """
                            INSERT INTO users (id, email, auth_provider, subscription_tier)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                            """,
                            (user_id, final_email, auth_provider, subscription_tier),
                        )
                    return True
        except Exception as e:
            logger.error(f"Failed to ensure user exists: {e}")
            return False

    def get(self, user_id: str) -> dict[str, Any] | None:
        """Get user data from PostgreSQL.

        Args:
            user_id: User identifier (from SuperTokens)

        Returns:
            User data dict or None if not found
        """
        try:
            return self._execute_one(
                """
                SELECT id, email, auth_provider, subscription_tier,
                       is_admin, gdpr_consent_at, created_at, updated_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None

    # =========================================================================
    # User Context
    # =========================================================================

    def get_context(self, user_id: str) -> dict[str, Any] | None:
        """Load user's business context from database.

        Args:
            user_id: User ID (from Supabase auth)

        Returns:
            Dictionary with context fields or None if not found
        """
        return self._execute_one(
            """
            SELECT business_model, target_market, product_description,
                   revenue, customers, growth_rate, competitors, website,
                   created_at, updated_at
            FROM user_context
            WHERE user_id = %s
            """,
            (user_id,),
        )

    def save_context(self, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        """Save or update user's business context.

        Args:
            user_id: User ID (from Supabase auth)
            context: Dictionary with context fields

        Returns:
            Saved context with timestamps
        """
        return self._execute_returning(
            """
            INSERT INTO user_context (
                user_id, business_model, target_market, product_description,
                revenue, customers, growth_rate, competitors, website
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                business_model = EXCLUDED.business_model,
                target_market = EXCLUDED.target_market,
                product_description = EXCLUDED.product_description,
                revenue = EXCLUDED.revenue,
                customers = EXCLUDED.customers,
                growth_rate = EXCLUDED.growth_rate,
                competitors = EXCLUDED.competitors,
                website = EXCLUDED.website,
                updated_at = NOW()
            RETURNING business_model, target_market, product_description,
                      revenue, customers, growth_rate, competitors, website,
                      created_at, updated_at
            """,
            (
                user_id,
                context.get("business_model"),
                context.get("target_market"),
                context.get("product_description"),
                context.get("revenue"),
                context.get("customers"),
                context.get("growth_rate"),
                context.get("competitors"),
                context.get("website"),
            ),
        )

    def delete_context(self, user_id: str) -> bool:
        """Delete user's business context.

        Args:
            user_id: User ID (from Supabase auth)

        Returns:
            True if context was deleted, False if not found
        """
        deleted = self._execute_count(
            "DELETE FROM user_context WHERE user_id = %s",
            (user_id,),
        )
        return deleted > 0


# Singleton instance for convenience
user_repository = UserRepository()
