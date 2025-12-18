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

    # SQL INJECTION SAFETY NOTE:
    # CONTEXT_FIELDS is used to build dynamic SQL queries (SELECT field_list, INSERT field_list).
    # This is SAFE because:
    # 1. CONTEXT_FIELDS is a hardcoded class constant (not user input)
    # 2. All values are parameterized with %s placeholders
    # 3. Field names are validated at class load time via _validate_sql_identifiers()
    #
    # DO NOT add user input to CONTEXT_FIELDS - it would create SQL injection vulnerability.

    # List of all context fields for extended business context
    CONTEXT_FIELDS = [
        # Original fields
        "business_model",
        "target_market",
        "product_description",
        "revenue",
        "customers",
        "growth_rate",
        "competitors",
        "website",
        # Extended fields (Tier 3)
        "company_name",
        "business_stage",
        "primary_objective",
        "industry",
        "product_categories",
        "pricing_model",
        "brand_positioning",
        "brand_tone",
        "brand_maturity",
        "tech_stack",
        "seo_structure",
        "detected_competitors",
        "ideal_customer_profile",
        "keywords",
        "target_geography",
        "traffic_range",
        "mau_bucket",
        "revenue_stage",
        "main_value_proposition",
        "team_size",
        "budget_constraints",
        "time_constraints",
        "regulatory_constraints",
        "enrichment_source",
        "enrichment_date",
        "last_refresh_prompt",
        "onboarding_completed",
        "onboarding_completed_at",
        # Goals
        "north_star_goal",
        # Clarification answers from meetings
        "clarifications",
        # Context auto-update tracking
        "context_metric_history",
        "pending_updates",
        # Benchmark value timestamps
        "benchmark_timestamps",
        # Benchmark historical values (max 6 per metric)
        "benchmark_history",
    ]

    @classmethod
    def _validate_sql_identifiers(cls) -> None:
        """Validate that all CONTEXT_FIELDS are safe SQL identifiers.

        This is a defense-in-depth measure to catch any accidentally
        unsafe field names at class load time.

        Raises:
            ValueError: If any field name contains unsafe characters
        """
        import re

        # Safe SQL identifier pattern: lowercase letters, numbers, underscores only
        safe_pattern = re.compile(r"^[a-z][a-z0-9_]*$")

        for field in cls.CONTEXT_FIELDS:
            if not safe_pattern.match(field):
                raise ValueError(
                    f"CONTEXT_FIELDS contains unsafe SQL identifier: '{field}'. "
                    "Field names must start with a letter and contain only "
                    "lowercase letters, numbers, and underscores."
                )

    def get_context(self, user_id: str) -> dict[str, Any] | None:
        """Load user's business context with Redis cache.

        Tries Redis cache first, falls back to PostgreSQL on miss.
        Caches result on miss for subsequent requests.

        Args:
            user_id: User ID (from Supabase auth)

        Returns:
            Dictionary with all context fields or None if not found
        """
        # Try Redis cache first
        try:
            from backend.api.dependencies import get_redis_manager

            redis_manager = get_redis_manager()
            cached = redis_manager.get_cached_context(user_id)

            if cached is not None:
                # Cache hit - emit metric
                try:
                    from backend.api.metrics import prom_metrics

                    prom_metrics.user_context_cache_total.labels(result="hit").inc()
                except ImportError:
                    pass
                return cached

            # Cache miss - emit metric
            try:
                from backend.api.metrics import prom_metrics

                prom_metrics.user_context_cache_total.labels(result="miss").inc()
            except ImportError:
                pass

        except Exception as e:
            # Redis error - fall back to DB (don't fail request)
            logger.warning(f"[CONTEXT_CACHE] Redis error for {user_id}, falling back to DB: {e}")

        # Build SELECT with all fields
        fields = ", ".join(self.CONTEXT_FIELDS + ["created_at", "updated_at"])
        context = self._execute_one(
            f"""
            SELECT {fields}
            FROM user_context
            WHERE user_id = %s
            """,
            (user_id,),
        )

        # Cache result on miss (if we got data)
        if context is not None:
            try:
                from backend.api.dependencies import get_redis_manager

                redis_manager = get_redis_manager()
                redis_manager.cache_context(user_id, context)
            except Exception as e:
                logger.debug(f"[CONTEXT_CACHE] Failed to cache context for {user_id}: {e}")

        return context

    def save_context(self, user_id: str, context: dict[str, Any]) -> dict[str, Any]:
        """Save or update user's business context.

        Invalidates Redis cache after successful DB write.

        Args:
            user_id: User ID (from Supabase auth)
            context: Dictionary with context fields (any subset of CONTEXT_FIELDS)

        Returns:
            Saved context with timestamps
        """
        import json

        # Filter to only valid fields
        valid_fields = [f for f in self.CONTEXT_FIELDS if f in context]

        # Handle empty context - insert/update minimal record with just user_id
        if not valid_fields:
            return_fields = ", ".join(self.CONTEXT_FIELDS + ["created_at", "updated_at"])
            result = self._execute_returning(
                f"""
                INSERT INTO user_context (user_id)
                VALUES (%s)
                ON CONFLICT (user_id) DO UPDATE SET updated_at = NOW()
                RETURNING {return_fields}
                """,
                (user_id,),
            )
            self._invalidate_context_cache(user_id)
            return result

        # Build dynamic INSERT statement
        field_list = ", ".join(valid_fields)
        placeholders = ", ".join(["%s"] * len(valid_fields))
        update_clause = ", ".join([f"{f} = EXCLUDED.{f}" for f in valid_fields])

        # Prepare values, converting lists/dicts to JSON for JSONB columns
        jsonb_fields = {
            "product_categories",
            "tech_stack",
            "seo_structure",
            "detected_competitors",
            "keywords",
            "clarifications",
            "context_metric_history",
            "pending_updates",
            "benchmark_timestamps",
        }

        values = []
        for field in valid_fields:
            value = context.get(field)
            if field in jsonb_fields and value is not None:
                value = json.dumps(value)
            values.append(value)

        # Build return fields
        return_fields = ", ".join(self.CONTEXT_FIELDS + ["created_at", "updated_at"])

        sql = f"""
            INSERT INTO user_context (user_id, {field_list})
            VALUES (%s, {placeholders})
            ON CONFLICT (user_id) DO UPDATE SET
                {update_clause},
                updated_at = NOW()
            RETURNING {return_fields}
        """

        result = self._execute_returning(sql, (user_id, *values))

        # Invalidate cache after successful write
        self._invalidate_context_cache(user_id)

        return result

    def _invalidate_context_cache(self, user_id: str) -> None:
        """Invalidate user context cache in Redis.

        Args:
            user_id: User identifier
        """
        try:
            from backend.api.dependencies import get_redis_manager

            redis_manager = get_redis_manager()
            redis_manager.invalidate_context(user_id)
        except Exception as e:
            # Don't fail save_context if cache invalidation fails
            logger.warning(f"[CONTEXT_CACHE] Failed to invalidate cache for {user_id}: {e}")

    def mark_onboarding_complete(self, user_id: str) -> bool:
        """Mark user's onboarding as complete.

        Args:
            user_id: User ID

        Returns:
            True if updated successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE user_context
                        SET onboarding_completed = true,
                            onboarding_completed_at = NOW(),
                            updated_at = NOW()
                        WHERE user_id = %s
                        """,
                        (user_id,),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to mark onboarding complete: {e}")
            return False

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

    # =========================================================================
    # Google OAuth Tokens
    # =========================================================================

    def save_google_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str | None,
        scopes: str | None,
    ) -> bool:
        """Save Google OAuth tokens for a user (encrypted at rest).

        Args:
            user_id: User identifier
            access_token: Google access token
            refresh_token: Google refresh token (for token refresh)
            expires_at: ISO timestamp when access token expires
            scopes: Comma-separated list of authorized scopes

        Returns:
            True if saved successfully
        """
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        }

        # Encrypt tokens if encryption key is configured
        encrypted_tokens: str
        try:
            from backend.services.encryption import get_encryption_service

            encryption = get_encryption_service()
            encrypted_tokens = encryption.encrypt_json(tokens)
        except Exception as e:
            # If encryption not configured, fall back to plaintext JSON (dev only)
            import json

            logger.warning(f"Encryption not available, storing tokens as plaintext: {e}")
            encrypted_tokens = json.dumps(tokens)

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET google_oauth_tokens = %s,
                            google_oauth_scopes = %s,
                            google_tokens_updated_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (encrypted_tokens, scopes, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to save Google tokens for user {user_id}: {e}")
            return False

    def get_google_tokens(self, user_id: str) -> dict[str, Any] | None:
        """Get Google OAuth tokens for a user (decrypted from storage).

        Args:
            user_id: User identifier

        Returns:
            Dict with access_token, refresh_token, expires_at, scopes or None
        """
        try:
            result = self._execute_one(
                """
                SELECT google_oauth_tokens, google_oauth_scopes, google_tokens_updated_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            if not result:
                return None

            stored_tokens = result.get("google_oauth_tokens")
            if not stored_tokens:
                return None

            # Decrypt tokens - handle both encrypted string and legacy JSON
            tokens: dict[str, Any]
            if isinstance(stored_tokens, str):
                # Try to decrypt (encrypted storage)
                try:
                    from backend.services.encryption import (
                        get_encryption_service,
                        is_encrypted,
                    )

                    if is_encrypted(stored_tokens):
                        encryption = get_encryption_service()
                        tokens = encryption.decrypt_json(stored_tokens)
                    else:
                        # Legacy plaintext JSON string
                        import json

                        tokens = json.loads(stored_tokens)
                except Exception as e:
                    # Decryption failed - token may be corrupted or key changed
                    logger.error(f"Failed to decrypt tokens for user {user_id}: {e}")
                    # Clear corrupted tokens
                    self.clear_google_tokens(user_id)
                    return None
            elif isinstance(stored_tokens, dict):
                # Already a dict (psycopg2 auto-parsed JSONB)
                tokens = stored_tokens
            else:
                logger.error(f"Unexpected token format for user {user_id}: {type(stored_tokens)}")
                return None

            tokens["scopes"] = result.get("google_oauth_scopes")
            tokens["updated_at"] = result.get("google_tokens_updated_at")
            return tokens
        except Exception as e:
            logger.error(f"Failed to get Google tokens for user {user_id}: {e}")
            return None

    def has_google_sheets_connected(self, user_id: str) -> bool:
        """Check if user has Google Sheets connected.

        Args:
            user_id: User identifier

        Returns:
            True if user has valid Google OAuth tokens with sheets scope
        """
        tokens = self.get_google_tokens(user_id)
        if not tokens:
            return False
        scopes = tokens.get("scopes", "")
        return "spreadsheets" in scopes

    def clear_google_tokens(self, user_id: str) -> bool:
        """Clear Google OAuth tokens for a user (disconnect).

        Args:
            user_id: User identifier

        Returns:
            True if cleared successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET google_oauth_tokens = NULL,
                            google_oauth_scopes = NULL,
                            google_tokens_updated_at = NULL,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (user_id,),
                    )
                    return True
        except Exception as e:
            logger.error(f"Failed to clear Google tokens for user {user_id}: {e}")
            return False

    # =========================================================================
    # Google Calendar Tokens (separate from Sheets)
    # =========================================================================

    def save_calendar_tokens(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: str | None,
    ) -> bool:
        """Save Google Calendar OAuth tokens for a user (encrypted at rest).

        Args:
            user_id: User identifier
            access_token: Google access token
            refresh_token: Google refresh token (for token refresh)
            expires_at: ISO timestamp when access token expires

        Returns:
            True if saved successfully
        """
        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        }

        # Encrypt tokens if encryption key is configured
        encrypted_tokens: str
        try:
            from backend.services.encryption import get_encryption_service

            encryption = get_encryption_service()
            encrypted_tokens = encryption.encrypt_json(tokens)
        except Exception as e:
            # If encryption not configured, fall back to plaintext JSON (dev only)
            import json

            logger.warning(f"Encryption not available, storing calendar tokens as plaintext: {e}")
            encrypted_tokens = json.dumps(tokens)

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET google_calendar_tokens = %s,
                            google_calendar_connected_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (encrypted_tokens, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to save Calendar tokens for user {user_id}: {e}")
            return False

    def get_calendar_tokens(self, user_id: str) -> dict[str, Any] | None:
        """Get Google Calendar OAuth tokens for a user (decrypted from storage).

        Args:
            user_id: User identifier

        Returns:
            Dict with access_token, refresh_token, expires_at or None
        """
        try:
            result = self._execute_one(
                """
                SELECT google_calendar_tokens, google_calendar_connected_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            if not result:
                return None

            stored_tokens = result.get("google_calendar_tokens")
            if not stored_tokens:
                return None

            # Decrypt tokens - handle both encrypted string and legacy JSON
            tokens: dict[str, Any]
            if isinstance(stored_tokens, str):
                try:
                    from backend.services.encryption import (
                        get_encryption_service,
                        is_encrypted,
                    )

                    if is_encrypted(stored_tokens):
                        encryption = get_encryption_service()
                        tokens = encryption.decrypt_json(stored_tokens)
                    else:
                        import json

                        tokens = json.loads(stored_tokens)
                except Exception as e:
                    logger.error(f"Failed to decrypt calendar tokens for user {user_id}: {e}")
                    self.clear_calendar_tokens(user_id)
                    return None
            elif isinstance(stored_tokens, dict):
                tokens = stored_tokens
            else:
                logger.error(
                    f"Unexpected calendar token format for user {user_id}: {type(stored_tokens)}"
                )
                return None

            tokens["connected_at"] = result.get("google_calendar_connected_at")
            return tokens
        except Exception as e:
            logger.error(f"Failed to get Calendar tokens for user {user_id}: {e}")
            return None

    def has_calendar_connected(self, user_id: str) -> bool:
        """Check if user has Google Calendar connected.

        Args:
            user_id: User identifier

        Returns:
            True if user has valid Google Calendar tokens
        """
        tokens = self.get_calendar_tokens(user_id)
        return tokens is not None and bool(tokens.get("access_token"))

    def clear_calendar_tokens(self, user_id: str) -> bool:
        """Clear Google Calendar OAuth tokens for a user (disconnect).

        Args:
            user_id: User identifier

        Returns:
            True if cleared successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET google_calendar_tokens = NULL,
                            google_calendar_connected_at = NULL,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (user_id,),
                    )
                    return True
        except Exception as e:
            logger.error(f"Failed to clear Calendar tokens for user {user_id}: {e}")
            return False

    def get_calendar_sync_enabled(self, user_id: str) -> bool:
        """Get user's calendar sync preference.

        Args:
            user_id: User identifier

        Returns:
            True if calendar sync is enabled (default), False if paused
        """
        result = self._execute_one(
            "SELECT calendar_sync_enabled FROM users WHERE id = %s",
            (user_id,),
        )
        if result is None:
            return True  # Default to enabled
        # Handle None value in column (default to True)
        return result.get("calendar_sync_enabled") is not False

    def set_calendar_sync_enabled(self, user_id: str, enabled: bool) -> bool:
        """Set user's calendar sync preference.

        Args:
            user_id: User identifier
            enabled: Whether to enable calendar sync

        Returns:
            True if updated successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET calendar_sync_enabled = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (enabled, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to set calendar sync for user {user_id}: {e}")
            return False

    # =========================================================================
    # Stripe Billing
    # =========================================================================

    def get_stripe_customer_id(self, user_id: str) -> str | None:
        """Get Stripe customer ID for a user.

        Args:
            user_id: User identifier

        Returns:
            Stripe customer ID or None if not set
        """
        result = self._execute_one(
            "SELECT stripe_customer_id FROM users WHERE id = %s",
            (user_id,),
        )
        return result.get("stripe_customer_id") if result else None

    def save_stripe_customer_id(self, user_id: str, customer_id: str) -> bool:
        """Save Stripe customer ID for a user.

        Args:
            user_id: User identifier
            customer_id: Stripe customer ID (cus_...)

        Returns:
            True if saved successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET stripe_customer_id = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (customer_id, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to save Stripe customer ID for user {user_id}: {e}")
            return False

    def save_stripe_subscription(
        self,
        user_id: str,
        subscription_id: str,
        tier: str,
    ) -> bool:
        """Save Stripe subscription and update user tier.

        Args:
            user_id: User identifier
            subscription_id: Stripe subscription ID (sub_...)
            tier: Subscription tier (starter, pro)

        Returns:
            True if saved successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET stripe_subscription_id = %s,
                            subscription_tier = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (subscription_id, tier, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to save subscription for user {user_id}: {e}")
            return False

    def update_subscription_tier(self, user_id: str, tier: str) -> bool:
        """Update user's subscription tier.

        Args:
            user_id: User identifier
            tier: New subscription tier

        Returns:
            True if updated successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET subscription_tier = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (tier, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to update tier for user {user_id}: {e}")
            return False

    def clear_stripe_subscription(self, user_id: str) -> bool:
        """Clear Stripe subscription and downgrade to free tier.

        Args:
            user_id: User identifier

        Returns:
            True if cleared successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET stripe_subscription_id = NULL,
                            subscription_tier = 'free',
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (user_id,),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to clear subscription for user {user_id}: {e}")
            return False

    def get_user_by_stripe_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get user by Stripe customer ID.

        Args:
            customer_id: Stripe customer ID

        Returns:
            User data dict or None if not found
        """
        return self._execute_one(
            """
            SELECT id, email, auth_provider, subscription_tier,
                   stripe_customer_id, stripe_subscription_id,
                   is_admin, created_at, updated_at
            FROM users
            WHERE stripe_customer_id = %s
            """,
            (customer_id,),
        )

    # =========================================================================
    # Default Workspace
    # =========================================================================

    def get_default_workspace(self, user_id: str) -> Any | None:
        """Get user's default workspace ID.

        Args:
            user_id: User identifier

        Returns:
            Default workspace UUID or None if not set
        """
        result = self._execute_one(
            "SELECT default_workspace_id FROM users WHERE id = %s",
            (user_id,),
        )
        return result.get("default_workspace_id") if result else None

    def set_default_workspace(self, user_id: str, workspace_id: Any) -> bool:
        """Set user's default workspace.

        Args:
            user_id: User identifier
            workspace_id: Workspace UUID to set as default

        Returns:
            True if updated successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET default_workspace_id = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (workspace_id, user_id),
                    )
                    return bool(cur.rowcount and cur.rowcount > 0)
        except Exception as e:
            logger.error(f"Failed to set default workspace for user {user_id}: {e}")
            return False

    def clear_default_workspace(self, user_id: str) -> bool:
        """Clear user's default workspace.

        Args:
            user_id: User identifier

        Returns:
            True if cleared successfully
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET default_workspace_id = NULL,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (user_id,),
                    )
                    return True
        except Exception as e:
            logger.error(f"Failed to clear default workspace for user {user_id}: {e}")
            return False

    # =========================================================================
    # Cost Calculator Defaults
    # =========================================================================

    # Default values for cost calculator widget
    DEFAULT_COST_CALCULATOR = {
        "avg_hourly_rate": 75,
        "typical_participants": 5,
        "typical_duration_mins": 60,
        "typical_prep_mins": 30,
    }

    def get_cost_calculator_defaults(self, user_id: str) -> dict[str, Any]:
        """Get user's cost calculator defaults.

        Args:
            user_id: User identifier

        Returns:
            Cost calculator defaults (saved or default values)
        """
        result = self._execute_one(
            "SELECT cost_calculator_defaults FROM users WHERE id = %s",
            (user_id,),
        )
        if result and result.get("cost_calculator_defaults"):
            defaults: dict[str, Any] = result["cost_calculator_defaults"]
            return defaults
        return self.DEFAULT_COST_CALCULATOR.copy()

    def update_cost_calculator_defaults(
        self, user_id: str, defaults: dict[str, Any]
    ) -> dict[str, Any]:
        """Update user's cost calculator defaults.

        Args:
            user_id: User identifier
            defaults: Dictionary with avg_hourly_rate, typical_participants,
                     typical_duration_mins, typical_prep_mins

        Returns:
            Updated defaults
        """
        import json

        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET cost_calculator_defaults = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING cost_calculator_defaults
                        """,
                        (json.dumps(defaults), user_id),
                    )
                    row = cur.fetchone()
                    if row:
                        return row[0] if isinstance(row[0], dict) else json.loads(row[0])
                    return defaults
        except Exception as e:
            logger.error(f"Failed to update cost calculator defaults for user {user_id}: {e}")
            return defaults


# Validate SQL identifiers at module load time (defense-in-depth)
UserRepository._validate_sql_identifiers()

# Singleton instance for convenience
user_repository = UserRepository()
