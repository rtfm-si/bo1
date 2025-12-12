"""Tests for LinkedIn OAuth configuration."""

import importlib
import os
from unittest.mock import patch

from backend.api.supertokens_config import get_oauth_providers


class TestLinkedInOAuthProvider:
    """Tests for LinkedIn OAuth provider configuration."""

    def test_linkedin_provider_configured_when_credentials_present(self) -> None:
        """Test LinkedIn provider is added when credentials are present."""
        env_vars = {
            "LINKEDIN_OAUTH_CLIENT_ID": "test-linkedin-client-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "test-linkedin-client-secret",  # noqa: S105
            "LINKEDIN_OAUTH_ENABLED": "true",
            # Disable Google to isolate LinkedIn test
            "GOOGLE_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Need to reload feature flags to pick up env changes
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Force the module-level variable to True for this test
            with patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should have LinkedIn provider
            linkedin_providers = [p for p in providers if p.config.third_party_id == "linkedin"]
            assert len(linkedin_providers) == 1

            linkedin = linkedin_providers[0]
            assert linkedin.config.third_party_id == "linkedin"
            assert len(linkedin.config.clients) == 1
            assert linkedin.config.clients[0].client_id == "test-linkedin-client-id"
            # Check client_secret exists (not the value, to avoid hardcoded secret warning)
            assert linkedin.config.clients[0].client_secret

    def test_linkedin_provider_not_configured_when_disabled(self) -> None:
        """Test LinkedIn provider is not added when disabled via feature flag."""
        env_vars = {
            "LINKEDIN_OAUTH_CLIENT_ID": "test-linkedin-client-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "test-linkedin-client-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", False):
                providers = get_oauth_providers()

            # Should not have LinkedIn provider
            linkedin_providers = [p for p in providers if p.config.third_party_id == "linkedin"]
            assert len(linkedin_providers) == 0

    def test_linkedin_provider_not_configured_when_credentials_missing(self) -> None:
        """Test LinkedIn provider is not added when credentials are missing."""
        env_vars = {
            "LINKEDIN_OAUTH_CLIENT_ID": "",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "",
            "GOOGLE_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should not have LinkedIn provider
            linkedin_providers = [p for p in providers if p.config.third_party_id == "linkedin"]
            assert len(linkedin_providers) == 0

    def test_linkedin_provider_scopes(self) -> None:
        """Test LinkedIn provider has correct OAuth scopes."""
        env_vars = {
            "LINKEDIN_OAUTH_CLIENT_ID": "test-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "test-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            linkedin_providers = [p for p in providers if p.config.third_party_id == "linkedin"]
            assert len(linkedin_providers) == 1

            scopes = linkedin_providers[0].config.clients[0].scope
            # LinkedIn uses OpenID Connect scopes
            assert "openid" in scopes
            assert "profile" in scopes
            assert "email" in scopes

    def test_linkedin_and_google_can_coexist(self) -> None:
        """Test both LinkedIn and Google providers can be configured together."""
        env_vars = {
            "LINKEDIN_OAUTH_CLIENT_ID": "linkedin-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "linkedin-secret",  # noqa: S105
            "GOOGLE_OAUTH_CLIENT_ID": "google-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GOOGLE_OAUTH_ENABLED", True),
            ):
                providers = get_oauth_providers()

            provider_ids = [p.config.third_party_id for p in providers]
            assert "linkedin" in provider_ids
            assert "google" in provider_ids


class TestLinkedInFeatureFlag:
    """Tests for LinkedIn OAuth feature flag."""

    def test_linkedin_oauth_enabled_default(self) -> None:
        """Test LINKEDIN_OAUTH_ENABLED defaults to True."""
        env_vars = {}  # No env var set

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Default should be True
            assert ff_module.LINKEDIN_OAUTH_ENABLED is True

    def test_linkedin_oauth_can_be_disabled(self) -> None:
        """Test LINKEDIN_OAUTH_ENABLED can be set to False."""
        env_vars = {"LINKEDIN_OAUTH_ENABLED": "false"}

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            assert ff_module.LINKEDIN_OAUTH_ENABLED is False
