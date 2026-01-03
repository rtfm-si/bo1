"""SuperTokens configuration for Board of One authentication.

This module initializes SuperTokens with:
- AccountLinking recipe for linking accounts with same email across providers
- EmailVerification recipe (required for AccountLinking)
- ThirdParty recipe for OAuth (Google, LinkedIn, GitHub)
- EmailPassword recipe for email/password authentication
- Session recipe for httpOnly cookie-based session management
- Closed beta whitelist validation
- IP-based lockout after failed auth attempts

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
from supertokens_python.recipe import (
    accountlinking,
    emailpassword,
    emailverification,
    passwordless,
    session,
    thirdparty,
)
from supertokens_python.recipe.accountlinking.types import (
    AccountInfoWithRecipeIdAndUserId,
    ShouldAutomaticallyLink,
    ShouldNotAutomaticallyLink,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    APIInterface as EmailPasswordAPIInterface,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    APIOptions as EmailPasswordAPIOptions,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    RecipeInterface as EmailPasswordRecipeInterface,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    SignInOkResult as EmailPasswordSignInOkResult,
)
from supertokens_python.recipe.emailpassword.interfaces import (
    SignUpOkResult as EmailPasswordSignUpOkResult,
)
from supertokens_python.recipe.emailpassword.types import FormField
from supertokens_python.recipe.passwordless.interfaces import (
    ConsumeCodeOkResult,
)
from supertokens_python.recipe.passwordless.interfaces import (
    RecipeInterface as PasswordlessRecipeInterface,
)
from supertokens_python.recipe.session.interfaces import SessionContainer, SignOutOkayResponse
from supertokens_python.recipe.thirdparty.interfaces import (
    APIInterface,
    APIOptions,
    RecipeInterface,
    SignInUpOkResult,
)
from supertokens_python.recipe.thirdparty.provider import (
    Provider,
    ProviderInput,
    RedirectUriInfo,
    UserFields,
    UserInfoMap,
)
from supertokens_python.recipe.thirdparty.types import RawUserInfoFromProvider
from supertokens_python.types import GeneralErrorResponse
from supertokens_python.types import User as SuperTokensUser

from backend.api.middleware.csrf import (
    clear_csrf_cookie_on_response,
    generate_csrf_token,
    set_csrf_cookie_on_response,
)
from backend.api.utils.db_helpers import execute_query, exists
from backend.api.utils.oauth_errors import sanitize_supertokens_message
from backend.services.auth_lockout import auth_lockout_service
from backend.services.email import send_email, send_email_async
from backend.services.email_templates import render_magic_link_email, render_welcome_email
from bo1.feature_flags import (
    BLUESKY_OAUTH_ENABLED,
    GITHUB_OAUTH_ENABLED,
    GOOGLE_OAUTH_ENABLED,
    LINKEDIN_OAUTH_ENABLED,
    MAGIC_LINK_ENABLED,
    TWITTER_OAUTH_ENABLED,
)
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import user_repository
from bo1.state.repositories.workspace_repository import workspace_repository

logger = logging.getLogger(__name__)


# Password validation constants
MIN_PASSWORD_LENGTH = 12
PASSWORD_REQUIREMENTS_MSG = (
    "Password must be at least 12 characters and contain both letters and numbers"  # noqa: S105
)


async def validate_password_strength(value: str, tenant_id: str) -> str | None:
    """Validate password meets strength requirements.

    Requirements:
    - At least 12 characters
    - Contains at least one letter (a-z or A-Z)
    - Contains at least one digit (0-9)

    Args:
        value: Password to validate
        tenant_id: Tenant ID (unused but required by SuperTokens interface)

    Returns:
        None if valid, error message string if invalid
    """
    if len(value) < MIN_PASSWORD_LENGTH:
        return PASSWORD_REQUIREMENTS_MSG

    has_letter = any(c.isalpha() for c in value)
    has_digit = any(c.isdigit() for c in value)

    if not has_letter or not has_digit:
        return PASSWORD_REQUIREMENTS_MSG

    return None


# Trusted proxy IPs (configure via environment in production)
TRUSTED_PROXIES = [p.strip() for p in os.getenv("TRUSTED_PROXY_IPS", "").split(",") if p.strip()]


def _get_client_ip(request: Any) -> str:
    """Extract client IP from SuperTokens request wrapper.

    Args:
        request: SuperTokens BaseRequest wrapper

    Returns:
        Client IP address, defaulting to 'unknown' if unavailable
    """
    try:
        # SuperTokens wraps the request - try to get underlying request
        # For FastAPI/Starlette, the request object has headers and client

        # Get direct client IP first for proxy validation
        remote_ip = "unknown"
        if hasattr(request, "request") and hasattr(request.request, "client"):
            if request.request.client:
                remote_ip = str(request.request.client.host)

        # Check X-Forwarded-For (for reverse proxy) - only trust from known proxies
        forwarded_for = request.get_header("x-forwarded-for")
        if forwarded_for and (not TRUSTED_PROXIES or remote_ip in TRUSTED_PROXIES):
            return str(forwarded_for.split(",")[0].strip())

        # Check X-Real-IP - only trust from known proxies
        real_ip_header = request.get_header("x-real-ip")
        if real_ip_header and (not TRUSTED_PROXIES or remote_ip in TRUSTED_PROXIES):
            return str(real_ip_header)

        # Return direct client IP if available
        if remote_ip != "unknown":
            return remote_ip

        # Fallback
        return "unknown"
    except Exception as e:
        logger.warning(f"Could not extract client IP: {e}")
        return "unknown"


def _mask_email(email: str) -> str:
    """Mask email for logging (PII redaction).

    Args:
        email: Email address to mask

    Returns:
        Masked email (e.g., 'abc***@domain.com')
    """
    if "@" in email:
        local, domain = email.split("@", 1)
        masked_local = local[:3] + "***" if len(local) > 3 else local[0] + "***"
        return f"{masked_local}@{domain}"
    return email[:3] + "***"


def check_whitelist_db(email: str) -> bool:
    """Check if email is in database whitelist.

    Args:
        email: Email address to check (case-insensitive)

    Returns:
        True if email is whitelisted in database, False otherwise
    """
    try:
        return exists(
            "beta_whitelist",
            where="LOWER(email) = LOWER(%s)",
            params=(email,),
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Error checking database whitelist: {e}",
            email=_mask_email(email),
        )
        return False


def is_whitelisted(email: str) -> bool:
    """Check if email is whitelisted (database-managed).

    Args:
        email: Email address to check (case-insensitive)

    Returns:
        True if email is whitelisted, False otherwise
    """
    email_lower = email.lower()

    # Check database whitelist
    if check_whitelist_db(email):
        logger.info(f"Email {_mask_email(email_lower)} found in database whitelist")
        return True

    return False


def is_user_locked_or_deleted(user_id: str) -> bool:
    """Check if user account is locked or soft deleted.

    Args:
        user_id: User identifier

    Returns:
        True if user is locked or deleted, False otherwise
    """
    try:
        row = execute_query(
            "SELECT is_locked, deleted_at FROM users WHERE id = %s",
            (user_id,),
            fetch="one",
        )
        if row:
            return row["is_locked"] or row["deleted_at"] is not None
        return False  # User not found in DB yet
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Error checking user lock status: {e}",
            user_id=user_id,
        )
        return False  # Fail open - don't block auth on DB errors


def _set_password_upgrade_flag(user_id: str, needs_upgrade: bool) -> None:
    """Set the password upgrade needed flag for a user.

    Args:
        user_id: User identifier
        needs_upgrade: Whether user needs to upgrade their password
    """
    from bo1.state.database import db_session

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET password_upgrade_needed = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (needs_upgrade, user_id),
            )


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
    if GOOGLE_OAUTH_ENABLED:
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
                                scope=[
                                    "openid",
                                    "email",
                                    "profile",
                                    "https://www.googleapis.com/auth/spreadsheets.readonly",
                                ],
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

    # LinkedIn OAuth
    if LINKEDIN_OAUTH_ENABLED:
        linkedin_client_id = os.getenv("LINKEDIN_OAUTH_CLIENT_ID", "")
        linkedin_client_secret = os.getenv("LINKEDIN_OAUTH_CLIENT_SECRET", "")

        if linkedin_client_id and linkedin_client_secret:
            providers.append(
                ProviderInput(
                    config=thirdparty.ProviderConfig(
                        third_party_id="linkedin",
                        clients=[
                            thirdparty.ProviderClientConfig(
                                client_id=linkedin_client_id,
                                client_secret=linkedin_client_secret,
                                scope=[
                                    "openid",
                                    "profile",
                                    "email",
                                ],
                            )
                        ],
                    )
                )
            )
            logger.info("LinkedIn OAuth provider configured")
        else:
            logger.warning(
                "LinkedIn OAuth enabled but credentials missing (LINKEDIN_OAUTH_CLIENT_ID, LINKEDIN_OAUTH_CLIENT_SECRET)"
            )

    # GitHub OAuth
    if GITHUB_OAUTH_ENABLED:
        github_client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
        github_client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")

        if github_client_id and github_client_secret:
            providers.append(
                ProviderInput(
                    config=thirdparty.ProviderConfig(
                        third_party_id="github",
                        clients=[
                            thirdparty.ProviderClientConfig(
                                client_id=github_client_id,
                                client_secret=github_client_secret,
                                scope=[
                                    "read:user",
                                    "user:email",
                                ],
                            )
                        ],
                    )
                )
            )
            logger.info("GitHub OAuth provider configured")
        else:
            logger.warning(
                "GitHub OAuth enabled but credentials missing (GITHUB_OAUTH_CLIENT_ID, GITHUB_OAUTH_CLIENT_SECRET)"
            )

    # Twitter/X OAuth
    if TWITTER_OAUTH_ENABLED:
        twitter_client_id = os.getenv("TWITTER_OAUTH_CLIENT_ID", "")
        twitter_client_secret = os.getenv("TWITTER_OAUTH_CLIENT_SECRET", "")

        if twitter_client_id and twitter_client_secret:
            providers.append(
                ProviderInput(
                    config=thirdparty.ProviderConfig(
                        third_party_id="twitter",
                        clients=[
                            thirdparty.ProviderClientConfig(
                                client_id=twitter_client_id,
                                client_secret=twitter_client_secret,
                                scope=[
                                    "users.read",
                                    "tweet.read",
                                ],
                            )
                        ],
                    )
                )
            )
            logger.info("Twitter/X OAuth provider configured")
        else:
            logger.warning(
                "Twitter OAuth enabled but credentials missing (TWITTER_OAUTH_CLIENT_ID, TWITTER_OAUTH_CLIENT_SECRET)"
            )

    # Bluesky OAuth (AT Protocol)
    if BLUESKY_OAUTH_ENABLED:
        bluesky_client_id = os.getenv("BLUESKY_CLIENT_ID", "")
        bluesky_client_secret = os.getenv("BLUESKY_CLIENT_SECRET", "")

        if bluesky_client_id and bluesky_client_secret:
            # Bluesky uses AT Protocol OAuth 2.0 with PKCE
            # Authorization: https://bsky.social/oauth/authorize
            # Token: https://bsky.social/oauth/token
            # UserInfo: https://bsky.social/xrpc/com.atproto.identity.resolveHandle
            providers.append(
                ProviderInput(
                    config=thirdparty.ProviderConfig(
                        third_party_id="bluesky",
                        clients=[
                            thirdparty.ProviderClientConfig(
                                client_id=bluesky_client_id,
                                client_secret=bluesky_client_secret,
                                scope=[
                                    "atproto",
                                    "transition:generic",
                                ],
                            )
                        ],
                        authorization_endpoint="https://bsky.social/oauth/authorize",
                        token_endpoint="https://bsky.social/oauth/token",  # noqa: S106
                        user_info_endpoint="https://bsky.social/xrpc/app.bsky.actor.getProfile",
                        user_info_map=UserInfoMap(
                            from_user_info_api=UserFields(
                                user_id="did",
                                email="handle",  # Bluesky uses handle, not email
                            )
                        ),
                    )
                )
            )
            logger.info("Bluesky OAuth provider configured (AT Protocol)")
        else:
            logger.warning(
                "Bluesky OAuth enabled but credentials missing (BLUESKY_CLIENT_ID, BLUESKY_CLIENT_SECRET)"
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
                    f"Sign-in attempt rejected: {_mask_email(email.lower())} not whitelisted for closed beta"
                )
                # Log the actual rejection reason for debugging
                logger.warning(
                    f"Whitelist rejection: {_mask_email(email)} not in closed beta whitelist"
                )
                # Raise sanitized message to prevent information disclosure
                raise Exception(sanitize_supertokens_message("whitelist rejection"))

            logger.info(f"Whitelist validation passed for: {_mask_email(email.lower())}")

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
        if not isinstance(result, SignInUpOkResult):
            # SignInUpNotAllowed or LinkingToSessionUserFailedError - return as-is
            return result

        try:
            user_id = result.user.id

            # Log account linking status
            # With AccountLinking, an OAuth sign-in may link to an existing email account
            login_methods = len(result.user.login_methods) if result.user.login_methods else 1
            if login_methods > 1:
                logger.info(
                    f"Account linked: {_mask_email(email)} now has {login_methods} login methods "
                    f"(user_id: {user_id}, added: {third_party_id})"
                )

            user_repository.ensure_exists(
                user_id=user_id,
                email=email,
                auth_provider=third_party_id,  # "google", "linkedin", "github"
                subscription_tier="free",  # Default tier for new users
            )
            logger.info(
                f"User synced to PostgreSQL: {_mask_email(email)} (user_id: {user_id}, provider: {third_party_id})"
            )

            # Save Google OAuth tokens for Sheets API access
            if third_party_id == "google" and oauth_tokens:
                from datetime import UTC, datetime, timedelta

                access_token = oauth_tokens.get("access_token")
                refresh_token = oauth_tokens.get("refresh_token")
                expires_in = oauth_tokens.get("expires_in")  # seconds
                scope = oauth_tokens.get("scope", "")

                # Calculate expiry timestamp
                expires_at = None
                if expires_in:
                    expires_at = (
                        datetime.now(UTC) + timedelta(seconds=int(expires_in))
                    ).isoformat()

                if access_token:
                    user_repository.save_google_tokens(
                        user_id=user_id,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_at=expires_at,
                        scopes=scope,
                    )
                    logger.info(
                        f"Saved Google OAuth tokens for user {user_id} (scopes: {scope[:50]}...)"
                    )

            # Check if user account is locked or deleted
            if is_user_locked_or_deleted(user_id):
                logger.warning(
                    f"Sign-in rejected: user {user_id} ({_mask_email(email)}) is locked or deleted"
                )
                # Raise sanitized message to prevent information disclosure
                raise Exception(sanitize_supertokens_message("account locked"))

            # Send welcome email for new users (fire-and-forget)
            if result.created_new_recipe_user:
                try:
                    # Extract name from provider info if available
                    user_name = None
                    if raw_user_info_from_provider.from_user_info_api:
                        user_name = raw_user_info_from_provider.from_user_info_api.get("name")

                    html, text = render_welcome_email(user_name=user_name, user_id=user_id)
                    send_email_async(
                        to=email,
                        subject="Welcome to Board of One",
                        html=html,
                        text=text,
                    )
                    logger.info(f"Welcome email queued for new user: {_mask_email(email)}")
                except Exception as welcome_err:
                    # Don't block signup on welcome email failure
                    logger.warning(f"Failed to send welcome email: {welcome_err}")

                # Create default personal workspace for new users
                try:
                    workspace_name = "Personal Workspace"
                    workspace = workspace_repository.create_workspace(
                        name=workspace_name,
                        owner_id=user_id,
                    )
                    # Set as user's default workspace
                    user_repository.set_default_workspace(user_id, workspace.id)
                    logger.info(
                        f"Created personal workspace for new user: {_mask_email(email)} "
                        f"(workspace_id: {workspace.id})"
                    )
                except Exception as workspace_err:
                    # Don't block signup on workspace creation failure
                    # User can create workspace manually later
                    logger.warning(f"Failed to create personal workspace: {workspace_err}")
        except Exception as e:
            # Re-raise lock/delete exceptions
            if "locked or deleted" in str(e):
                raise
            # Log but don't block authentication - user will be synced on next API call
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to sync user to PostgreSQL: {e}",
                user_id=user_id,
                email=_mask_email(email),
            )

        logger.info(f"User signed in: {_mask_email(email)} (user_id: {result.user.id})")

        return result

    original_implementation.sign_in_up = sign_in_up  # type: ignore[method-assign]
    return original_implementation


def override_thirdparty_apis(original_implementation: APIInterface) -> APIInterface:
    """Override ThirdParty APIs to add lockout check with request access."""
    original_sign_in_up_post = original_implementation.sign_in_up_post

    async def sign_in_up_post(
        provider: Provider,
        redirect_uri_info: RedirectUriInfo | None,
        oauth_tokens: dict[str, Any] | None,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        tenant_id: str,
        api_options: APIOptions,
        user_context: dict[str, Any],
    ) -> Any:
        """Override sign_in_up_post to check IP lockout before auth."""
        # Extract client IP from request
        client_ip = _get_client_ip(api_options.request)

        # Check if IP is locked out
        lockout_remaining = auth_lockout_service.get_lockout_remaining(client_ip)
        if lockout_remaining and lockout_remaining > 0:
            logger.warning(
                f"Auth attempt blocked: IP {client_ip} locked out for {lockout_remaining}s"
            )
            # Track lockout trigger for security alerting
            auth_lockout_service.record_lockout_triggered(client_ip)
            # Raise sanitized exception to prevent timing information disclosure
            raise Exception(sanitize_supertokens_message("too many attempts"))

        # Store IP in user_context for recording failures in function override
        user_context["client_ip"] = client_ip

        try:
            result = await original_sign_in_up_post(
                provider,
                redirect_uri_info,
                oauth_tokens,
                session,
                should_try_linking_with_session_user,
                tenant_id,
                api_options,
                user_context,
            )

            # On success, optionally clear lockout (comment out if prefer accumulating)
            # auth_lockout_service.clear_attempts(client_ip)

            # Rotate CSRF token on successful sign-in (session fixation mitigation)
            # Generate new token to prevent attackers from planting CSRF token before auth
            if api_options.response:
                cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
                cookie_domain = os.getenv("COOKIE_DOMAIN", None)
                # Don't set domain for localhost (browser won't accept it)
                if cookie_domain == "localhost":
                    cookie_domain = None
                new_csrf_token = generate_csrf_token()
                set_csrf_cookie_on_response(
                    api_options.response,
                    new_csrf_token,
                    secure=cookie_secure,
                    domain=cookie_domain,
                )
                logger.info(f"CSRF token rotated on sign-in for IP {client_ip}")

            return result
        except Exception as e:
            # Record failure for lockout tracking
            error_msg = str(e).lower()
            if "whitelist" in error_msg:
                auth_lockout_service.record_failed_attempt(client_ip, "whitelist_rejection")
            elif "locked or deleted" in error_msg:
                auth_lockout_service.record_failed_attempt(client_ip, "account_locked")
            else:
                # Other auth failures
                auth_lockout_service.record_failed_attempt(client_ip, "auth_error")
            raise

    original_implementation.sign_in_up_post = sign_in_up_post  # type: ignore[method-assign]
    return original_implementation


def override_emailpassword_functions(
    original_implementation: EmailPasswordRecipeInterface,
) -> EmailPasswordRecipeInterface:
    """Override EmailPassword functions for whitelist validation and user sync."""
    original_sign_up = original_implementation.sign_up
    original_sign_in = original_implementation.sign_in

    async def sign_up(
        email: str,
        password: str,
        tenant_id: str,
        session: Any | None,
        should_try_linking_with_session_user: bool | None,
        user_context: dict[str, Any],
    ) -> Any:
        """Override sign_up to add whitelist validation and user sync."""
        # Check closed beta whitelist
        if os.getenv("CLOSED_BETA_MODE", "false").lower() == "true":
            if not is_whitelisted(email):
                logger.warning(
                    f"Email sign-up rejected: {_mask_email(email.lower())} not whitelisted"
                )
                raise Exception(sanitize_supertokens_message("whitelist rejection"))

        result = await original_sign_up(
            email,
            password,
            tenant_id,
            session,
            should_try_linking_with_session_user,
            user_context,
        )

        # Check if sign-up was successful
        if not isinstance(result, EmailPasswordSignUpOkResult):
            return result

        # Sync user to PostgreSQL
        try:
            user_id = result.user.id
            user_repository.ensure_exists(
                user_id=user_id,
                email=email,
                auth_provider="email",
                subscription_tier="free",
            )
            logger.info(
                f"Email user synced to PostgreSQL: {_mask_email(email)} (user_id: {user_id})"
            )

            # Create workspace and send welcome email for new users
            if result.user.login_methods and len(result.user.login_methods) == 1:
                # New user - send welcome email
                try:
                    html, text = render_welcome_email(user_name=None, user_id=user_id)
                    send_email_async(
                        to=email,
                        subject="Welcome to Board of One",
                        html=html,
                        text=text,
                    )
                    logger.info(f"Welcome email queued for new email user: {_mask_email(email)}")
                except Exception as welcome_err:
                    logger.warning(f"Failed to send welcome email: {welcome_err}")

                # Create default workspace
                try:
                    workspace = workspace_repository.create_workspace(
                        name="Personal Workspace",
                        owner_id=user_id,
                    )
                    user_repository.set_default_workspace(user_id, workspace.id)
                    logger.info(
                        f"Created personal workspace for new email user: {_mask_email(email)}"
                    )
                except Exception as workspace_err:
                    logger.warning(f"Failed to create workspace: {workspace_err}")

        except Exception as e:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to sync email user to PostgreSQL: {e}",
                email=_mask_email(email),
            )

        return result

    async def sign_in(
        email: str,
        password: str,
        tenant_id: str,
        session: Any | None,
        should_try_linking_with_session_user: bool | None,
        user_context: dict[str, Any],
    ) -> Any:
        """Override sign_in to check account lock status and password strength."""
        result = await original_sign_in(
            email,
            password,
            tenant_id,
            session,
            should_try_linking_with_session_user,
            user_context,
        )

        # Check if sign-in was successful
        if not isinstance(result, EmailPasswordSignInOkResult):
            return result

        # Check if user is locked or deleted
        user_id = result.user.id
        if is_user_locked_or_deleted(user_id):
            logger.warning(
                f"Email sign-in rejected: user {user_id} ({_mask_email(email)}) is locked/deleted"
            )
            raise Exception(sanitize_supertokens_message("account locked"))

        # Check if existing password meets current strength requirements
        # If not, flag user to prompt for upgrade (non-blocking)
        password_weak = await validate_password_strength(password, tenant_id) is not None
        if password_weak:
            try:
                _set_password_upgrade_flag(user_id, True)
                logger.info(f"Flagged user {user_id} for password upgrade (weak password detected)")
            except Exception as e:
                # Don't block login on flag update failure
                logger.warning(f"Failed to set password upgrade flag: {e}")

        logger.info(f"Email user signed in: {_mask_email(email)} (user_id: {user_id})")
        return result

    original_implementation.sign_up = sign_up  # type: ignore[method-assign]
    original_implementation.sign_in = sign_in  # type: ignore[method-assign]
    return original_implementation


def override_emailpassword_apis(
    original_implementation: EmailPasswordAPIInterface,
) -> EmailPasswordAPIInterface:
    """Override EmailPassword APIs for IP lockout."""
    original_sign_up_post = original_implementation.sign_up_post
    original_sign_in_post = original_implementation.sign_in_post

    async def sign_up_post(
        form_fields: list[FormField],
        tenant_id: str,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        api_options: EmailPasswordAPIOptions,
        user_context: dict[str, Any],
    ) -> Any:
        """Override sign_up_post to check IP lockout."""
        client_ip = _get_client_ip(api_options.request)

        # Check if IP is locked out
        lockout_remaining = auth_lockout_service.get_lockout_remaining(client_ip)
        if lockout_remaining and lockout_remaining > 0:
            logger.warning(f"Email sign-up blocked: IP {client_ip} locked out")
            raise Exception(sanitize_supertokens_message("too many attempts"))

        try:
            result = await original_sign_up_post(
                form_fields,
                tenant_id,
                session,
                should_try_linking_with_session_user,
                api_options,
                user_context,
            )

            # Rotate CSRF token on successful sign-up
            if api_options.response:
                cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
                cookie_domain = os.getenv("COOKIE_DOMAIN", None)
                if cookie_domain == "localhost":
                    cookie_domain = None
                new_csrf_token = generate_csrf_token()
                set_csrf_cookie_on_response(
                    api_options.response,
                    new_csrf_token,
                    secure=cookie_secure,
                    domain=cookie_domain,
                )

            return result
        except Exception as e:
            error_msg = str(e).lower()
            if "whitelist" in error_msg:
                auth_lockout_service.record_failed_attempt(client_ip, "whitelist_rejection")
            else:
                auth_lockout_service.record_failed_attempt(client_ip, "signup_error")
            raise

    async def sign_in_post(
        form_fields: list[FormField],
        tenant_id: str,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        api_options: EmailPasswordAPIOptions,
        user_context: dict[str, Any],
    ) -> Any:
        """Override sign_in_post to check IP lockout."""
        client_ip = _get_client_ip(api_options.request)

        # Check if IP is locked out
        lockout_remaining = auth_lockout_service.get_lockout_remaining(client_ip)
        if lockout_remaining and lockout_remaining > 0:
            logger.warning(f"Email sign-in blocked: IP {client_ip} locked out")
            raise Exception(sanitize_supertokens_message("too many attempts"))

        try:
            result = await original_sign_in_post(
                form_fields,
                tenant_id,
                session,
                should_try_linking_with_session_user,
                api_options,
                user_context,
            )

            # Rotate CSRF token on successful sign-in
            if api_options.response:
                cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
                cookie_domain = os.getenv("COOKIE_DOMAIN", None)
                if cookie_domain == "localhost":
                    cookie_domain = None
                new_csrf_token = generate_csrf_token()
                set_csrf_cookie_on_response(
                    api_options.response,
                    new_csrf_token,
                    secure=cookie_secure,
                    domain=cookie_domain,
                )

            return result
        except Exception as e:
            error_msg = str(e).lower()
            if "locked" in error_msg:
                auth_lockout_service.record_failed_attempt(client_ip, "account_locked")
            else:
                auth_lockout_service.record_failed_attempt(client_ip, "signin_error")
            raise

    original_implementation.sign_up_post = sign_up_post  # type: ignore[method-assign]
    original_implementation.sign_in_post = sign_in_post  # type: ignore[method-assign]
    return original_implementation


def override_passwordless_functions(
    original_implementation: PasswordlessRecipeInterface,
) -> PasswordlessRecipeInterface:
    """Override Passwordless functions for whitelist validation and user sync."""
    original_consume_code = original_implementation.consume_code

    async def consume_code(
        pre_auth_session_id: str,
        user_input_code: str | None,
        device_id: str | None,
        link_code: str | None,
        session: Any | None,
        should_try_linking_with_session_user: bool | None,
        tenant_id: str,
        user_context: dict[str, Any],
    ) -> Any:
        """Override consume_code to sync user to PostgreSQL."""
        result = await original_consume_code(
            pre_auth_session_id,
            user_input_code,
            device_id,
            link_code,
            session,
            should_try_linking_with_session_user,
            tenant_id,
            user_context,
        )

        if not isinstance(result, ConsumeCodeOkResult):
            return result

        user = result.user
        user_id = user.id
        email = None

        # Get email from login methods
        for login_method in user.login_methods:
            if login_method.email:
                email = login_method.email
                break

        if not email:
            logger.warning(f"Passwordless user {user_id} has no email")
            return result

        # Check closed beta whitelist
        if os.getenv("CLOSED_BETA_MODE", "false").lower() == "true":
            if not is_whitelisted(email):
                logger.warning(f"Magic link rejected: {_mask_email(email.lower())} not whitelisted")
                raise Exception(sanitize_supertokens_message("whitelist rejection"))

        # Check if user is locked or deleted
        if is_user_locked_or_deleted(user_id):
            logger.warning(
                f"Magic link rejected: user {user_id} ({_mask_email(email)}) is locked/deleted"
            )
            raise Exception(sanitize_supertokens_message("account locked"))

        # Sync user to PostgreSQL
        try:
            user_repository.ensure_exists(
                user_id=user_id,
                email=email,
                auth_provider="magic_link",
                subscription_tier="free",
            )
            logger.info(
                f"Magic link user synced to PostgreSQL: {_mask_email(email)} (user_id: {user_id})"
            )

            # Track magic link usage for rate limiting
            _update_last_magic_link_at(user_id)

            # Send welcome email for new users
            if result.created_new_recipe_user:
                try:
                    html, text = render_welcome_email(user_name=None, user_id=user_id)
                    send_email_async(
                        to=email,
                        subject="Welcome to Board of One",
                        html=html,
                        text=text,
                    )
                    logger.info(
                        f"Welcome email queued for new magic link user: {_mask_email(email)}"
                    )
                except Exception as welcome_err:
                    logger.warning(f"Failed to send welcome email: {welcome_err}")

                # Create default workspace
                try:
                    workspace = workspace_repository.create_workspace(
                        name="Personal Workspace",
                        owner_id=user_id,
                    )
                    user_repository.set_default_workspace(user_id, workspace.id)
                    logger.info(
                        f"Created personal workspace for new magic link user: {_mask_email(email)}"
                    )
                except Exception as workspace_err:
                    logger.warning(f"Failed to create workspace: {workspace_err}")

        except Exception as e:
            if "locked or deleted" in str(e) or "whitelist" in str(e):
                raise
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to sync magic link user to PostgreSQL: {e}",
                email=_mask_email(email),
            )

        logger.info(f"Magic link user signed in: {_mask_email(email)} (user_id: {user_id})")
        return result

    original_implementation.consume_code = consume_code  # type: ignore[method-assign]
    return original_implementation


def _update_last_magic_link_at(user_id: str) -> None:
    """Update the last_magic_link_at timestamp for rate limiting."""
    from bo1.state.database import db_session

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET last_magic_link_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (user_id,),
                )
    except Exception as e:
        logger.warning(f"Failed to update last_magic_link_at: {e}")


class MagicLinkEmailService(passwordless.EmailDeliveryInterface[passwordless.EmailTemplateVars]):
    """Custom email delivery service for magic link emails."""

    async def send_email(
        self,
        template_vars: passwordless.EmailTemplateVars,
        user_context: dict[str, Any],
    ) -> None:
        """Send magic link email via Resend.

        Args:
            template_vars: Email template variables from SuperTokens
            user_context: Additional context
        """
        email = template_vars.email
        url_with_link_code = template_vars.url_with_link_code
        code_life_time = template_vars.code_life_time

        if not url_with_link_code:
            logger.error("Magic link URL is missing")
            raise ValueError("Magic link URL is required")

        expiry_minutes = code_life_time // 60000  # Convert ms to minutes
        html, text = render_magic_link_email(url_with_link_code, expiry_minutes)

        try:
            send_email(
                to=email,
                subject="Sign in to Board of One",
                html=html,
                text=text,
            )
            logger.info(f"Magic link email sent to {_mask_email(email)}")
        except Exception as e:
            log_error(
                logger,
                ErrorCode.EXTERNAL_API_ERROR,
                f"Failed to send magic link email: {e}",
                email=_mask_email(email),
            )
        raise


def override_session_apis(
    original_implementation: session.interfaces.APIInterface,
) -> session.interfaces.APIInterface:
    """Override Session APIs to clear CSRF token on sign-out."""
    original_signout_post = original_implementation.signout_post

    async def signout_post(
        session_container: SessionContainer,
        api_options: session.interfaces.APIOptions,
        user_context: dict[str, Any],
    ) -> SignOutOkayResponse | GeneralErrorResponse:
        """Override signout_post to clear CSRF token on sign-out."""
        # Call original sign-out first
        result = await original_signout_post(session_container, api_options, user_context)

        # Clear CSRF token cookie after successful sign-out
        if api_options.response:
            cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
            cookie_domain = os.getenv("COOKIE_DOMAIN", None)
            # Don't set domain for localhost (browser won't accept it)
            if cookie_domain == "localhost":
                cookie_domain = None
            clear_csrf_cookie_on_response(
                api_options.response,
                secure=cookie_secure,
                domain=cookie_domain,
            )
            logger.info("CSRF token cleared on sign-out")

        return result

    original_implementation.signout_post = signout_post  # type: ignore[method-assign,assignment]
    return original_implementation


# Trusted OAuth providers that verify email addresses
TRUSTED_OAUTH_PROVIDERS = {"google", "linkedin", "github"}


async def should_do_automatic_account_linking(
    new_account_info: AccountInfoWithRecipeIdAndUserId,
    user: SuperTokensUser | None,
    session_container: SessionContainer | None,
    tenant_id: str,
    user_context: dict[str, Any],
) -> ShouldAutomaticallyLink | ShouldNotAutomaticallyLink:
    """Determine whether to automatically link accounts.

    Links accounts when:
    - Email is present (OAuth providers like Google verify emails)
    - Provider is trusted (Google, LinkedIn, GitHub)

    This allows users who signed up with email/password to later sign in
    with Google using the same email address, and vice versa.

    Note: OAuth providers (Google, LinkedIn, GitHub) verify emails before
    returning them, so we trust emails from thirdparty recipe as verified.
    """
    email = new_account_info.email
    recipe_id = new_account_info.recipe_id

    if email:
        # Log linking attempt
        logger.info(f"Account linking check: email={_mask_email(email)}, recipe={recipe_id}")

        # ThirdParty providers (Google, LinkedIn, GitHub) verify emails
        # We trust the email is verified when coming from OAuth
        if recipe_id == "thirdparty":
            logger.info(f"Auto-linking approved for OAuth email: {_mask_email(email)}")
            # OAuth emails are already verified by the provider
            return ShouldAutomaticallyLink(should_require_verification=False)

        # EmailPassword - require email verification before linking
        if recipe_id == "emailpassword":
            logger.info(f"Auto-linking approved for email/password: {_mask_email(email)}")
            # Require verification for email/password signups
            return ShouldAutomaticallyLink(should_require_verification=True)

        # Passwordless (magic link) - email was verified by clicking link
        if recipe_id == "passwordless":
            logger.info(f"Auto-linking approved for passwordless: {_mask_email(email)}")
            return ShouldAutomaticallyLink(should_require_verification=False)

    # Don't auto-link accounts without email
    logger.info(f"Auto-linking denied: no email present, recipe={recipe_id}")
    return ShouldNotAutomaticallyLink()


def init_supertokens() -> None:
    """Initialize SuperTokens with all recipes and configurations.

    Recipes:
    - AccountLinking: Links accounts with same email across providers
    - EmailVerification: Required for AccountLinking (OPTIONAL mode)
    - ThirdParty: OAuth providers (Google, LinkedIn, GitHub)
    - EmailPassword: Email/password authentication
    - Passwordless: Magic link authentication (if enabled)
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
    env = os.getenv("ENV", "development").lower()

    # Security validation: COOKIE_SECURE must be true in production
    if env == "production" and not cookie_secure:
        logger.critical(
            "SECURITY VIOLATION: COOKIE_SECURE=false in production! "
            "Session cookies will be transmitted over insecure connections. "
            "Set COOKIE_SECURE=true in production environment variables."
        )
        raise RuntimeError(
            "COOKIE_SECURE must be true in production. "
            "Refusing to start with insecure cookie configuration."
        )

    # Log cookie configuration for audit trail
    logger.info(f"Cookie configuration: env={env}, secure={cookie_secure}, domain={cookie_domain}")

    # Build recipe list
    # Note: AccountLinking and EmailVerification must be initialized BEFORE other recipes
    recipe_list = [
        # EmailVerification recipe - required for AccountLinking
        # OAuth providers (Google, LinkedIn, GitHub) already verify emails
        emailverification.init(mode="OPTIONAL"),
        # AccountLinking recipe - enables linking different auth methods to same user
        accountlinking.init(
            should_do_automatic_account_linking=should_do_automatic_account_linking,
        ),
        # ThirdParty recipe for OAuth (Google, LinkedIn, GitHub)
        thirdparty.init(
            sign_in_and_up_feature=thirdparty.SignInAndUpFeature(providers=get_oauth_providers()),
            override=thirdparty.InputOverrideConfig(
                functions=override_thirdparty_functions,
                apis=override_thirdparty_apis,
            ),
        ),
        # EmailPassword recipe for email/password authentication
        emailpassword.init(
            sign_up_feature=emailpassword.InputSignUpFeature(
                form_fields=[
                    emailpassword.InputFormField(id="email"),
                    emailpassword.InputFormField(
                        id="password", validate=validate_password_strength
                    ),
                ]
            ),
            override=emailpassword.InputOverrideConfig(
                functions=override_emailpassword_functions,
                apis=override_emailpassword_apis,
            ),
        ),
    ]

    # Add Passwordless recipe if enabled (magic link auth)
    if MAGIC_LINK_ENABLED:
        # Magic link expiry: 15 minutes (in milliseconds)
        15 * 60 * 1000

        recipe_list.append(
            passwordless.init(
                flow_type="MAGIC_LINK",
                contact_config=passwordless.ContactEmailOnlyConfig(),
                email_delivery=passwordless.EmailDeliveryConfig(
                    service=MagicLinkEmailService(),
                ),
                override=passwordless.InputOverrideConfig(
                    functions=override_passwordless_functions,
                ),
            )
        )
        logger.info("Passwordless (magic link) recipe enabled")

    # Add Session recipe
    recipe_list.append(
        # Session recipe for session management (httpOnly cookies)
        session.init(
            cookie_secure=cookie_secure,  # HTTPS only in production
            cookie_domain=cookie_domain,  # .boardof.one in production
            cookie_same_site="lax",  # CSRF protection
            # Handle cookie domain transitions - if domain was changed,
            # older_cookie_domain clears cookies from previous domain.
            # Set to "" if previous was localhost/unset, or previous domain value.
            # Must keep for 1 year (access token frontend lifetime).
            older_cookie_domain=os.getenv("OLDER_COOKIE_DOMAIN", ""),
            override=session.InputOverrideConfig(
                apis=override_session_apis,
            ),
        ),
    )

    init(
        supertokens_config=get_supertokens_config(),
        app_info=get_app_info(),
        framework="fastapi",
        recipe_list=recipe_list,
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
    app.add_middleware(get_middleware())  # type: ignore[no-untyped-call]
    logger.info("SuperTokens middleware added to FastAPI app")
