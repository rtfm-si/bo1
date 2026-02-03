"""Sentry SDK integration for error tracking.

Disabled by default - enable via SENTRY_DSN environment variable.
When enabled, captures unhandled exceptions and optionally performance traces.

Environment variables:
    SENTRY_DSN: Sentry project DSN (required to enable)
    SENTRY_ENVIRONMENT: Environment tag (default: development)
    SENTRY_TRACES_SAMPLE_RATE: Performance sampling rate 0.0-1.0 (default: 0.1)

Example:
    SENTRY_DSN=https://xxx@sentry.io/xxx
    SENTRY_ENVIRONMENT=production
    SENTRY_TRACES_SAMPLE_RATE=0.1
"""

import logging
import os

logger = logging.getLogger(__name__)

# Module-level state
_sentry_initialized = False


def is_sentry_enabled() -> bool:
    """Check if Sentry SDK is initialized.

    Returns:
        True if Sentry was successfully initialized, False otherwise
    """
    return _sentry_initialized


def init_sentry() -> bool:
    """Initialize Sentry SDK if DSN is configured.

    Reads configuration from environment variables or Settings.
    Does nothing if SENTRY_DSN is not set.

    Returns:
        True if Sentry was successfully initialized, False otherwise
    """
    global _sentry_initialized

    if _sentry_initialized:
        logger.debug("Sentry already initialized, skipping")
        return True

    # Get DSN from env or settings
    dsn = os.getenv("SENTRY_DSN", "")
    if not dsn:
        # Try to get from settings (lazy import to avoid circular deps)
        try:
            from bo1.config import get_settings

            settings = get_settings()
            dsn = settings.sentry_dsn
        except Exception:
            logger.debug("Could not load settings for Sentry DSN")

    if not dsn:
        logger.debug("Sentry disabled (no SENTRY_DSN configured)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        # Get configuration
        environment = os.getenv("SENTRY_ENVIRONMENT", "")
        traces_sample_rate_str = os.getenv("SENTRY_TRACES_SAMPLE_RATE", "")

        # Fall back to settings if env vars not set
        try:
            from bo1.config import get_settings

            settings = get_settings()
            if not environment:
                environment = settings.sentry_environment
            if not traces_sample_rate_str:
                traces_sample_rate = settings.sentry_traces_sample_rate
            else:
                traces_sample_rate = float(traces_sample_rate_str)
        except Exception:
            environment = environment or "development"
            traces_sample_rate = float(traces_sample_rate_str) if traces_sample_rate_str else 0.1

        # Get release version
        release = _get_release_version()

        # Check if OTEL tracing is enabled - disable Sentry tracing to avoid duplication
        otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() in ("true", "1", "yes")
        if otel_enabled:
            # Disable Sentry performance tracing when OTEL is active
            traces_sample_rate = 0.0
            logger.info("Sentry performance tracing disabled (OTEL_ENABLED=true)")

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
            ],
            # Default PII scrubbing is enabled
            send_default_pii=False,
        )

        _sentry_initialized = True
        logger.info(
            f"Sentry initialized: env={environment}, release={release}, "
            f"traces_sample_rate={traces_sample_rate}"
        )
        return True

    except ImportError as e:
        logger.warning(f"Sentry SDK not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def _get_release_version() -> str:
    """Get release version for Sentry.

    Tries in order:
    1. SENTRY_RELEASE env var
    2. bo1 package version
    3. Git SHA (if available)
    4. "unknown"
    """
    # Check env var first
    release = os.getenv("SENTRY_RELEASE", "")
    if release:
        return release

    # Try package version
    try:
        from importlib.metadata import version

        return f"bo1@{version('bo1')}"
    except Exception:
        logger.debug("Could not get package version for release")

    # Try git SHA
    try:
        import shutil
        import subprocess

        git_path = shutil.which("git")
        if git_path:
            result = subprocess.run(  # noqa: S603 - git_path is from shutil.which
                [git_path, "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return f"bo1@{result.stdout.strip()}"
    except Exception:
        logger.debug("Could not get git SHA for release")

    return "bo1@unknown"
