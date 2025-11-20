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
from supertokens_python.recipe.thirdparty.provider import ProviderInput
from supertokens_python.recipe.thirdparty.types import RawUserInfoFromProvider

logger = logging.getLogger(__name__)


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

    # LinkedIn OAuth (future implementation)
    # if os.getenv("LINKEDIN_OAUTH_ENABLED", "false").lower() == "true":
    #     providers.append(...)

    # GitHub OAuth (future implementation)
    # if os.getenv("GITHUB_OAUTH_ENABLED", "false").lower() == "true":
    #     providers.append(...)

    return providers


async def override_thirdparty_functions(
    original_implementation: thirdparty.RecipeInterface,
) -> thirdparty.RecipeInterface:
    """Override ThirdParty functions to add custom logic (whitelist validation)."""
    original_sign_in_up = original_implementation.sign_in_up

    async def sign_in_up(
        third_party_id: str,
        third_party_user_id: str,
        email: str,
        oauth_tokens: dict[str, Any],
        raw_user_info_from_provider: RawUserInfoFromProvider,
        session: Any | None,
        tenant_id: str,
        user_context: dict[str, Any],
    ):
        """Override sign in/up to add closed beta whitelist validation."""
        # Check if closed beta mode is enabled
        if os.getenv("CLOSED_BETA_MODE", "false").lower() == "true":
            whitelist = os.getenv("BETA_WHITELIST", "").split(",")
            whitelist = [email_str.strip().lower() for email_str in whitelist if email_str.strip()]

            # Validate against whitelist
            user_email_lower = email.lower()
            if user_email_lower not in whitelist:
                # Reject user - not on whitelist
                logger.warning(
                    f"Sign-in attempt rejected: {user_email_lower} not whitelisted for closed beta"
                )
                raise Exception(
                    f"Email {email} is not whitelisted for closed beta access. "
                    f"Please contact support to request access."
                )

            logger.info(f"Whitelist validation passed for: {user_email_lower}")

        # Call original sign_in_up
        result = await original_sign_in_up(
            third_party_id,
            third_party_user_id,
            email,
            oauth_tokens,
            raw_user_info_from_provider,
            session,
            tenant_id,
            user_context,
        )

        logger.info(
            f"User signed in: {email} (user_id: {result.user.user_id}, is_new: {result.recipe_user_id})"
        )

        return result

    original_implementation.sign_in_up = sign_in_up
    return original_implementation


def init_supertokens():
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


def add_supertokens_middleware(app: FastAPI):
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
