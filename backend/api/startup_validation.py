"""Startup validation for local development authentication.

Validates auth configuration and logs warnings for common issues:
- Missing SuperTokens env vars
- Missing OAuth credentials
- SuperTokens Core reachability
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def validate_auth_config() -> list[str]:
    """Validate authentication configuration at startup.

    Returns:
        List of warning messages (empty if all checks pass)
    """
    warnings: list[str] = []

    # Check if auth is enabled
    if os.getenv("ENABLE_SUPERTOKENS_AUTH", "true").lower() != "true":
        warnings.append("SuperTokens auth disabled (ENABLE_SUPERTOKENS_AUTH=false)")
        return warnings

    # Check SuperTokens Core connection
    supertokens_uri = os.getenv("SUPERTOKENS_CONNECTION_URI", "http://supertokens:3567")
    supertokens_reachable = _check_supertokens_core(supertokens_uri)
    if not supertokens_reachable:
        warnings.append(
            f"SuperTokens Core not reachable at {supertokens_uri}. "
            "Ensure container is running: docker-compose ps supertokens"
        )

    # Check SuperTokens API key
    if not os.getenv("SUPERTOKENS_API_KEY"):
        warnings.append("SUPERTOKENS_API_KEY not set. Generate with: openssl rand -hex 32")

    # Check OAuth provider credentials
    oauth_warnings = _check_oauth_providers()
    warnings.extend(oauth_warnings)

    # Log OAuth provider status
    _log_oauth_status()

    return warnings


def _check_supertokens_core(uri: str) -> bool:
    """Check if SuperTokens Core is reachable.

    Args:
        uri: SuperTokens Core connection URI

    Returns:
        True if reachable, False otherwise
    """
    try:
        response = httpx.get(f"{uri}/hello", timeout=5.0)
        if response.status_code == 200:
            logger.info(f"SuperTokens Core reachable at {uri}")
            return True
        logger.warning(f"SuperTokens Core returned status {response.status_code}")
        return False
    except httpx.RequestError as e:
        logger.warning(f"SuperTokens Core connection failed: {e}")
        return False


def _check_oauth_providers() -> list[str]:
    """Check OAuth provider credentials.

    Returns:
        List of warning messages for missing credentials
    """
    warnings: list[str] = []

    # Google OAuth
    if os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() == "true":
        if not os.getenv("GOOGLE_OAUTH_CLIENT_ID"):
            warnings.append(
                "Google OAuth enabled but GOOGLE_OAUTH_CLIENT_ID not set. "
                "See: https://console.cloud.google.com/apis/credentials"
            )
        if not os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"):
            warnings.append("Google OAuth enabled but GOOGLE_OAUTH_CLIENT_SECRET not set")

    # LinkedIn OAuth
    if os.getenv("LINKEDIN_OAUTH_ENABLED", "false").lower() == "true":
        if not os.getenv("LINKEDIN_OAUTH_CLIENT_ID"):
            warnings.append("LinkedIn OAuth enabled but LINKEDIN_OAUTH_CLIENT_ID not set")
        if not os.getenv("LINKEDIN_OAUTH_CLIENT_SECRET"):
            warnings.append("LinkedIn OAuth enabled but LINKEDIN_OAUTH_CLIENT_SECRET not set")

    # GitHub OAuth
    if os.getenv("GITHUB_OAUTH_ENABLED", "false").lower() == "true":
        if not os.getenv("GITHUB_OAUTH_CLIENT_ID"):
            warnings.append("GitHub OAuth enabled but GITHUB_OAUTH_CLIENT_ID not set")
        if not os.getenv("GITHUB_OAUTH_CLIENT_SECRET"):
            warnings.append("GitHub OAuth enabled but GITHUB_OAUTH_CLIENT_SECRET not set")

    return warnings


def _log_oauth_status() -> None:
    """Log OAuth provider registration status."""
    providers_enabled: list[str] = []

    if os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() == "true":
        if os.getenv("GOOGLE_OAUTH_CLIENT_ID") and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"):
            providers_enabled.append("Google")

    if os.getenv("LINKEDIN_OAUTH_ENABLED", "false").lower() == "true":
        if os.getenv("LINKEDIN_OAUTH_CLIENT_ID") and os.getenv("LINKEDIN_OAUTH_CLIENT_SECRET"):
            providers_enabled.append("LinkedIn")

    if os.getenv("GITHUB_OAUTH_ENABLED", "false").lower() == "true":
        if os.getenv("GITHUB_OAUTH_CLIENT_ID") and os.getenv("GITHUB_OAUTH_CLIENT_SECRET"):
            providers_enabled.append("GitHub")

    if providers_enabled:
        logger.info(f"OAuth providers registered: {', '.join(providers_enabled)}")
    else:
        logger.warning("No OAuth providers configured. Login will not work.")


def validate_oauth_callback_urls() -> list[str]:
    """Validate OAuth callback URL configuration.

    Checks that callback URLs are correctly configured for each enabled provider.
    Logs expected callback URLs for provider dashboard configuration.

    Returns:
        List of warning messages (empty if all checks pass)
    """
    warnings: list[str] = []

    api_domain = os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000")

    # Map of provider to (enabled_env_var, default_enabled)
    providers = {
        "google": ("GOOGLE_OAUTH_ENABLED", "true"),
        "linkedin": ("LINKEDIN_OAUTH_ENABLED", "false"),
        "github": ("GITHUB_OAUTH_ENABLED", "false"),
        "twitter": ("TWITTER_OAUTH_ENABLED", "false"),
        "bluesky": ("BLUESKY_OAUTH_ENABLED", "false"),
    }

    enabled_providers: list[str] = []

    for provider, (env_var, default) in providers.items():
        if os.getenv(env_var, default).lower() == "true":
            enabled_providers.append(provider)

    if enabled_providers:
        callback_urls = [
            f"{api_domain}/api/auth/callback/{provider}" for provider in enabled_providers
        ]
        logger.info(f"OAuth callback URLs configured: {', '.join(callback_urls)}")

        # Log reminder about production vs local callback URLs
        if "localhost" in api_domain:
            logger.info(
                "Local development: Ensure OAuth provider dashboards have callback URL "
                f"set to {api_domain}/api/auth/callback/<provider>"
            )
        else:
            logger.info(
                f"Production: Ensure OAuth provider dashboards have callback URL "
                f"set to {api_domain}/api/auth/callback/<provider>"
            )

    return warnings


def get_oauth_callback_url(provider: str) -> str:
    """Get the expected OAuth callback URL for a provider.

    Args:
        provider: OAuth provider ID (google, linkedin, github, twitter, bluesky)

    Returns:
        Expected callback URL for the provider
    """
    api_domain = os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000")
    return f"{api_domain}/api/auth/callback/{provider}"


def validate_spaces_config() -> list[str]:
    """Validate DO Spaces configuration at startup.

    Returns:
        List of warning messages (empty if all checks pass)
    """
    warnings: list[str] = []

    do_spaces_key = os.getenv("DO_SPACES_KEY", "")
    do_spaces_secret = os.getenv("DO_SPACES_SECRET", "")
    do_spaces_bucket = os.getenv("DO_SPACES_BUCKET", "")

    if not do_spaces_key:
        warnings.append(
            "DO_SPACES_KEY not set. File uploads will fail. "
            "See: https://docs.digitalocean.com/products/spaces/"
        )
    if not do_spaces_secret:
        warnings.append("DO_SPACES_SECRET not set. File uploads will fail.")
    if not do_spaces_bucket:
        warnings.append("DO_SPACES_BUCKET not set. File uploads will fail.")

    # Log status
    if do_spaces_key and do_spaces_secret and do_spaces_bucket:
        logger.info(f"DO Spaces configured: bucket={do_spaces_bucket}")
    else:
        logger.warning("DO Spaces credentials incomplete - file uploads disabled")

    return warnings


def get_auth_diagnostic_info() -> dict[str, Any]:
    """Get diagnostic information for auth-check command.

    Returns:
        Dict with auth configuration status
    """
    supertokens_uri = os.getenv("SUPERTOKENS_CONNECTION_URI", "http://supertokens:3567")
    api_domain = os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000")

    return {
        "supertokens": {
            "connection_uri": supertokens_uri,
            "reachable": _check_supertokens_core(supertokens_uri),
            "api_key_set": bool(os.getenv("SUPERTOKENS_API_KEY")),
            "api_domain": api_domain,
            "website_domain": os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:5173"),
        },
        "cookies": {
            "secure": os.getenv("COOKIE_SECURE", "false").lower() == "true",
            "domain": os.getenv("COOKIE_DOMAIN", "localhost"),
        },
        "oauth_providers": {
            "google": {
                "enabled": os.getenv("GOOGLE_OAUTH_ENABLED", "true").lower() == "true",
                "client_id_set": bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID")),
                "client_secret_set": bool(os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")),
                "callback_url": f"{api_domain}/api/auth/callback/google",
            },
            "linkedin": {
                "enabled": os.getenv("LINKEDIN_OAUTH_ENABLED", "false").lower() == "true",
                "client_id_set": bool(os.getenv("LINKEDIN_OAUTH_CLIENT_ID")),
                "client_secret_set": bool(os.getenv("LINKEDIN_OAUTH_CLIENT_SECRET")),
                "callback_url": f"{api_domain}/api/auth/callback/linkedin",
            },
            "github": {
                "enabled": os.getenv("GITHUB_OAUTH_ENABLED", "false").lower() == "true",
                "client_id_set": bool(os.getenv("GITHUB_OAUTH_CLIENT_ID")),
                "client_secret_set": bool(os.getenv("GITHUB_OAUTH_CLIENT_SECRET")),
                "callback_url": f"{api_domain}/api/auth/callback/github",
            },
        },
        "closed_beta_mode": os.getenv("CLOSED_BETA_MODE", "false").lower() == "true",
        "debug": os.getenv("DEBUG", "false").lower() == "true",
    }
