"""Tests for SuperTokens configuration security validations."""

import os
from unittest.mock import patch

import pytest


class TestCookieSecureValidation:
    """Tests for COOKIE_SECURE production validation."""

    def test_production_without_cookie_secure_raises(self) -> None:
        """Test that production env without COOKIE_SECURE=true raises RuntimeError."""
        env_vars = {
            "ENV": "production",
            "COOKIE_SECURE": "false",
            "COOKIE_DOMAIN": ".boardof.one",
            "SUPERTOKENS_CONNECTION_URI": "http://localhost:3567",
            "SUPERTOKENS_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Import fresh to trigger validation
            # We need to reload the module to re-run init_supertokens
            from backend.api import supertokens_config

            with pytest.raises(RuntimeError) as exc_info:
                supertokens_config.init_supertokens()

            assert "COOKIE_SECURE must be true in production" in str(exc_info.value)

    def test_production_with_cookie_secure_true_passes(self) -> None:
        """Test that production env with COOKIE_SECURE=true does not raise."""
        env_vars = {
            "ENV": "production",
            "COOKIE_SECURE": "true",
            "COOKIE_DOMAIN": ".boardof.one",
            "SUPERTOKENS_CONNECTION_URI": "http://localhost:3567",
            "SUPERTOKENS_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            from backend.api import supertokens_config

            # Should not raise - but will fail on SuperTokens init since
            # no actual SuperTokens server is running. We just verify
            # the security check passes by catching the subsequent error.
            try:
                supertokens_config.init_supertokens()
            except RuntimeError as e:
                # If we get here with COOKIE_SECURE error, test fails
                if "COOKIE_SECURE" in str(e):
                    pytest.fail(f"Unexpected COOKIE_SECURE error: {e}")
                # Other RuntimeErrors (e.g., SuperTokens connection) are expected
            except Exception:  # noqa: S110
                # Other errors (network, SuperTokens init) are expected in test env
                pass

    def test_development_without_cookie_secure_passes(self) -> None:
        """Test that development env without COOKIE_SECURE=true does not raise."""
        env_vars = {
            "ENV": "development",
            "COOKIE_SECURE": "false",
            "COOKIE_DOMAIN": "localhost",
            "SUPERTOKENS_CONNECTION_URI": "http://localhost:3567",
            "SUPERTOKENS_API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            from backend.api import supertokens_config

            # Should not raise security error - may raise other errors
            try:
                supertokens_config.init_supertokens()
            except RuntimeError as e:
                if "COOKIE_SECURE" in str(e):
                    pytest.fail(f"Unexpected COOKIE_SECURE error in dev: {e}")
            except Exception:  # noqa: S110
                # Other errors (network, SuperTokens init) are expected
                pass

    def test_missing_env_defaults_to_development(self) -> None:
        """Test that missing ENV defaults to development (no security check)."""
        env_vars = {
            "COOKIE_SECURE": "false",
            "COOKIE_DOMAIN": "localhost",
            "SUPERTOKENS_CONNECTION_URI": "http://localhost:3567",
            "SUPERTOKENS_API_KEY": "test-key",
        }

        # Remove ENV if it exists
        with patch.dict(os.environ, env_vars, clear=False):
            if "ENV" in os.environ:
                del os.environ["ENV"]

            from backend.api import supertokens_config

            try:
                supertokens_config.init_supertokens()
            except RuntimeError as e:
                if "COOKIE_SECURE" in str(e):
                    pytest.fail(f"Unexpected COOKIE_SECURE error when ENV missing: {e}")
            except Exception:  # noqa: S110
                pass
