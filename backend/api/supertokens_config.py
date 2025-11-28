"""SuperTokens configuration for Board of One authentication.

This module initializes SuperTokens with:
- ThirdParty recipe for OAuth (Google, LinkedIn, GitHub)
- Session recipe for httpOnly cookie-based session management
- Closed beta whitelist validation

Architecture: BFF (Backend-for-Frontend) pattern
- Tokens never reach frontend (exchanged server-side)
- Sessions stored as httpOnly cookies (XSS-proof)
- Automatic token refresh and CSRF protection
"""

import logging
import os
from typing import Any

from fastapi import FastAPI
from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe import session, thirdparty
from supertokens_python.recipe.thirdparty.interfaces import RecipeInterface
from supertokens_python.recipe.thirdparty.provider import ProviderInput
from supertokens_python.recipe.thirdparty.types import RawUserInfoFromProvider

from bo1.state.postgres_manager import db_session, ensure_user_exists

logger = logging.getLogger(__name__)


def check_whitelist_db(email: str) -> bool:
    """Check if email is in database whitelist.

    Args:
        email: Email address to check (case-insensitive)

    Returns:
        True if email is whitelisted in database, False otherwise
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM beta_whitelist WHERE LOWER(email) = LOWER(%s)",
                    (email,),
                )
                return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking database whitelist: {e}")
        return False


def is_whitelisted(email: str) -> bool:
    """Check if email is whitelisted (env var or database).

    Checks environment variable first for backwards compatibility,
    then falls back to database check.

    Args:
        email: Email address to check (case-insensitive)

    Returns:
        True if email is whitelisted, False otherwise
    """
    email_lower = email.lower()

    # Check env var first (backwards compat)
    env_whitelist = os.getenv("BETA_WHITELIST", "").split(",")
    env_whitelist = [e.strip().lower() for e in env_whitelist if e.strip()]
    if email_lower in env_whitelist:
        logger.info(f"Email {email_lower} found in env var whitelist")
        return True

    # Then check database
    if check_whitelist_db(email):
        logger.info(f"Email {email_lower} found in database whitelist")
        return True

    return False


def get_app_info() -> InputAppInfo:
    """Get SuperTokens app configuration from environment."""
    return InputAppInfo(
        app_name=os.getenv("SUPERTOKENS_APP_NAME", "Board of One"),
        api_domain=os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000"),
        website_domain=os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:5173"),
        api_base_path="/api/auth",  # All auth endpoints under /api/auth
        website_base_path="/auth",  # Frontend auth pages under /auth
    )


def get_supertokens_config() -> SupertokensConfig:
    """Get SuperTokens Core connection configuration."""
    return SupertokensConfig(
        connection_uri=os.getenv("SUPERTOKENS_CONNECTION_URI", "http://supertokens:3567"),
        api_key=os.getenv("SUPERTOKENS_API_KEY", "dev_api_key_change_in_production"),
    )


def get_oauth_providers() -> list[ProviderInput]:
    """Get configured OAuth providers (Google, LinkedIn, GitHub)."""
    providers = []

    # Google OAuth
    if os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() == "true":
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")

        if client_id and client_secret:
            providers.append(
                ProviderInput(
                    config=thirdparty.ProviderConfig(
                        third_party_id="google",
                        clients=[
                            thirdparty.ProviderClientConfig(
                                client_id=client_id,
                                client_secret=client_secret,
                                scope=["openid", "email", "profile"],
                            )
                        ],
                    )
                )
            )
            logger.info("Google OAuth provider configured")
        else:
            logger.warning(
                "Google OAuth enabled but credentials missing (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET)"
            )

    return providers


def override_thirdparty_functions(
    original_implementation: RecipeInterface,
) -> RecipeInterface:
    """Override ThirdParty functions to add custom logic (whitelist validation)."""
    original_sign_in_up = original_implementation.sign_in_up

    async def sign_in_up(
        third_party_id: str,
        third_party_user_id: str,
        email: str,
        is_verified: bool,
        oauth_tokens: dict[str, Any],
        raw_user_info_from_provider: RawUserInfoFromProvider,
        session: Any | None,
        should_try_linking_with_session_user: bool | None,
        tenant_id: str,
        user_context: dict[str, Any],
    ) -> Any:  # Return type matches SuperTokens RecipeInterface
        """Override sign in/up to add closed beta whitelist validation."""
        # Check if closed beta mode is enabled
        if os.getenv("CLOSED_BETA_MODE", "false").lower() == "true":
            # Validate against whitelist (env var + database)
            if not is_whitelisted(email):
                # Reject user - not on whitelist
                logger.warning(
                    f"Sign-in attempt rejected: {email.lower()} not whitelisted for closed beta"
                )
                raise Exception(
                    f"Email {email} is not whitelisted for closed beta access. "
                    f"Please contact support to request access."
                )

            logger.info(f"Whitelist validation passed for: {email.lower()}")

        # Call original sign_in_up
        result = await original_sign_in_up(
            third_party_id,
            third_party_user_id,
            email,
            is_verified,
            oauth_tokens,
            raw_user_info_from_provider,
            session,
            should_try_linking_with_session_user,
            tenant_id,
            user_context,
        )

        # Sync user to PostgreSQL on authentication (not on first session creation)
        # This ensures the user exists in the DB immediately after OAuth success
        # PostgreSQL is the source of truth for persistent data; Redis is for transient state
        try:
            user_id = result.user.id
            ensure_user_exists(
                user_id=user_id,
                email=email,
                auth_provider=third_party_id,  # "google", "linkedin", "github"
                subscription_tier="free",  # Default tier for new users
            )
            logger.info(
                f"User synced to PostgreSQL: {email} (user_id: {user_id}, provider: {third_party_id})"
            )
        except Exception as e:
            # Log but don't block authentication - user will be synced on next API call
            logger.error(f"Failed to sync user to PostgreSQL: {e}")

        logger.info(f"User signed in: {email} (user_id: {result.user.id})")

        return result

    original_implementation.sign_in_up = sign_in_up
    return original_implementation


def init_supertokens() -> None:
    """Initialize SuperTokens with all recipes and configurations.

    Recipes:
    - ThirdParty: OAuth providers (Google, LinkedIn, GitHub)
    - Session: httpOnly cookie-based session management

    Security:
    - Tokens never reach frontend (server-side exchange)
    - httpOnly cookies (JavaScript cannot access, XSS-proof)
    - Automatic token refresh
    - CSRF protection (cookie_same_site="lax")
    - Closed beta whitelist validation
    """
    cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    cookie_domain = os.getenv("COOKIE_DOMAIN", "localhost")

    init(
        supertokens_config=get_supertokens_config(),
        app_info=get_app_info(),
        framework="fastapi",
        recipe_list=[
            # ThirdParty recipe for OAuth (Google, LinkedIn, GitHub)
            thirdparty.init(
                sign_in_and_up_feature=thirdparty.SignInAndUpFeature(
                    providers=get_oauth_providers()
                ),
                override=thirdparty.InputOverrideConfig(functions=override_thirdparty_functions),
            ),
            # Session recipe for session management (httpOnly cookies)
            session.init(
                cookie_secure=cookie_secure,  # HTTPS only in production
                cookie_domain=cookie_domain,  # .boardof.one in production
                cookie_same_site="lax",  # CSRF protection
            ),
        ],
        mode="asgi",  # FastAPI uses ASGI
    )

    logger.info(
        f"SuperTokens initialized (cookie_secure={cookie_secure}, cookie_domain={cookie_domain})"
    )


def add_supertokens_middleware(app: FastAPI) -> None:
    """Add SuperTokens middleware to FastAPI app.

    This middleware:
    - Handles SuperTokens API routes (/api/auth/*)
    - Manages session cookies
    - Provides session verification for protected routes

    IMPORTANT: Add this BEFORE CORS middleware to ensure SuperTokens
    headers (rid, fdi-version, anti-csrf) are properly handled.
    """
    app.add_middleware(get_middleware())
    logger.info("SuperTokens middleware added to FastAPI app")
