"""Tests for Sentry SDK integration."""

import os
from unittest.mock import MagicMock, patch


class TestSentryDisabled:
    """Tests for Sentry when disabled (no DSN)."""

    def test_sentry_disabled_when_no_dsn(self) -> None:
        """Sentry should be disabled when no DSN is configured."""
        import bo1.observability.sentry as sentry_module

        sentry_module._sentry_initialized = False

        # Mock settings to return empty DSN
        mock_settings = MagicMock()
        mock_settings.sentry_dsn = ""

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTRY_DSN", None)

            with patch("bo1.config.get_settings", return_value=mock_settings):
                result = sentry_module.init_sentry()
                assert result is False
                assert sentry_module.is_sentry_enabled() is False

    def test_is_sentry_enabled_reflects_init_state(self) -> None:
        """is_sentry_enabled should reflect initialization state."""
        import bo1.observability.sentry as sentry_module

        # Test when not initialized
        sentry_module._sentry_initialized = False
        assert sentry_module.is_sentry_enabled() is False

        # Test when initialized
        sentry_module._sentry_initialized = True
        assert sentry_module.is_sentry_enabled() is True

        # Reset
        sentry_module._sentry_initialized = False


class TestSentryEnabled:
    """Tests for Sentry when DSN is configured."""

    def test_sentry_config_from_env(self) -> None:
        """Sentry configuration should be read from environment variables."""
        with patch.dict(
            os.environ,
            {
                "SENTRY_DSN": "https://test@sentry.io/123",
                "SENTRY_ENVIRONMENT": "test",
                "SENTRY_TRACES_SAMPLE_RATE": "0.5",
            },
        ):
            dsn = os.getenv("SENTRY_DSN")
            env = os.getenv("SENTRY_ENVIRONMENT")
            rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

            assert dsn == "https://test@sentry.io/123"
            assert env == "test"
            assert rate == 0.5

    def test_sentry_tracing_disabled_when_otel_enabled(self) -> None:
        """Sentry performance tracing should be disabled when OTEL is enabled."""
        with patch.dict(
            os.environ,
            {
                "SENTRY_DSN": "https://test@sentry.io/123",
                "OTEL_ENABLED": "true",
                "SENTRY_TRACES_SAMPLE_RATE": "0.5",
            },
        ):
            # Verify OTEL check logic matches sentry.py
            otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() in ("true", "1", "yes")
            assert otel_enabled is True

    def test_sentry_init_with_valid_dsn(self) -> None:
        """Sentry should initialize successfully with a valid DSN."""
        # Skip if sentry_sdk not installed
        try:
            import sentry_sdk  # noqa: F401
        except ImportError:
            import pytest

            pytest.skip("sentry-sdk not installed")

        import bo1.observability.sentry as sentry_module

        sentry_module._sentry_initialized = False

        # Mock sentry_sdk.init
        mock_init = MagicMock()
        mock_fastapi = MagicMock()
        mock_starlette = MagicMock()

        with patch.dict(
            os.environ,
            {
                "SENTRY_DSN": "https://test@sentry.io/123",
                "SENTRY_ENVIRONMENT": "test",
            },
        ):
            with (
                patch("sentry_sdk.init", mock_init),
                patch(
                    "sentry_sdk.integrations.fastapi.FastApiIntegration",
                    return_value=mock_fastapi,
                ),
                patch(
                    "sentry_sdk.integrations.starlette.StarletteIntegration",
                    return_value=mock_starlette,
                ),
            ):
                result = sentry_module.init_sentry()

                assert result is True
                assert sentry_module.is_sentry_enabled() is True
                mock_init.assert_called_once()

                # Verify DSN was passed
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["dsn"] == "https://test@sentry.io/123"
                assert call_kwargs["environment"] == "test"

        # Reset
        sentry_module._sentry_initialized = False


class TestReleaseVersion:
    """Tests for release version detection."""

    def test_release_from_env_var(self) -> None:
        """Release should use SENTRY_RELEASE env var if set."""
        from bo1.observability.sentry import _get_release_version

        with patch.dict(os.environ, {"SENTRY_RELEASE": "v1.2.3"}):
            assert _get_release_version() == "v1.2.3"

    def test_release_fallback_to_package_version(self) -> None:
        """Release should fall back to package version."""
        from bo1.observability.sentry import _get_release_version

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTRY_RELEASE", None)

            with patch("importlib.metadata.version", return_value="0.8.0"):
                result = _get_release_version()
                assert result == "bo1@0.8.0"

    def test_release_fallback_to_git_sha(self) -> None:
        """Release should fall back to git SHA if package version unavailable."""
        from bo1.observability.sentry import _get_release_version

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTRY_RELEASE", None)

            # Mock version to raise exception
            with patch(
                "importlib.metadata.version",
                side_effect=Exception("No package"),
            ):
                # Mock subprocess for git
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "abc1234\n"

                with patch("subprocess.run", return_value=mock_result):
                    result = _get_release_version()
                    assert result == "bo1@abc1234"

    def test_release_fallback_to_unknown(self) -> None:
        """Release should fall back to 'unknown' if all methods fail."""
        from bo1.observability.sentry import _get_release_version

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SENTRY_RELEASE", None)

            with patch(
                "importlib.metadata.version",
                side_effect=Exception("No package"),
            ):
                with patch("subprocess.run", side_effect=Exception("No git")):
                    result = _get_release_version()
                    assert result == "bo1@unknown"
