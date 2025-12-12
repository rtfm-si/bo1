"""Tests for GitHub OAuth configuration."""

import importlib
import os
from unittest.mock import patch

from backend.api.supertokens_config import get_oauth_providers


class TestGitHubOAuthProvider:
    """Tests for GitHub OAuth provider configuration."""

    def test_github_provider_configured_when_credentials_present(self) -> None:
        """Test GitHub provider is added when credentials are present."""
        env_vars = {
            "GITHUB_OAUTH_CLIENT_ID": "test-github-client-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "test-github-client-secret",  # noqa: S105
            "GITHUB_OAUTH_ENABLED": "true",
            # Disable Google and LinkedIn to isolate GitHub test
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Need to reload feature flags to pick up env changes
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Force the module-level variable to True for this test
            with patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should have GitHub provider
            github_providers = [p for p in providers if p.config.third_party_id == "github"]
            assert len(github_providers) == 1

            github = github_providers[0]
            assert github.config.third_party_id == "github"
            assert len(github.config.clients) == 1
            assert github.config.clients[0].client_id == "test-github-client-id"
            # Check client_secret exists (not the value, to avoid hardcoded secret warning)
            assert github.config.clients[0].client_secret

    def test_github_provider_not_configured_when_disabled(self) -> None:
        """Test GitHub provider is not added when disabled via feature flag."""
        env_vars = {
            "GITHUB_OAUTH_CLIENT_ID": "test-github-client-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "test-github-client-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", False):
                providers = get_oauth_providers()

            # Should not have GitHub provider
            github_providers = [p for p in providers if p.config.third_party_id == "github"]
            assert len(github_providers) == 0

    def test_github_provider_not_configured_when_credentials_missing(self) -> None:
        """Test GitHub provider is not added when credentials are missing."""
        env_vars = {
            "GITHUB_OAUTH_CLIENT_ID": "",
            "GITHUB_OAUTH_CLIENT_SECRET": "",
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should not have GitHub provider
            github_providers = [p for p in providers if p.config.third_party_id == "github"]
            assert len(github_providers) == 0

    def test_github_provider_scopes(self) -> None:
        """Test GitHub provider has correct OAuth scopes."""
        env_vars = {
            "GITHUB_OAUTH_CLIENT_ID": "test-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "test-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            github_providers = [p for p in providers if p.config.third_party_id == "github"]
            assert len(github_providers) == 1

            scopes = github_providers[0].config.clients[0].scope
            # GitHub uses read:user and user:email scopes
            assert "read:user" in scopes
            assert "user:email" in scopes

    def test_github_and_google_can_coexist(self) -> None:
        """Test both GitHub and Google providers can be configured together."""
        env_vars = {
            "GITHUB_OAUTH_CLIENT_ID": "github-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "github-secret",  # noqa: S105
            "GOOGLE_OAUTH_CLIENT_ID": "google-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",  # noqa: S105
            "LINKEDIN_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GOOGLE_OAUTH_ENABLED", True),
            ):
                providers = get_oauth_providers()

            provider_ids = [p.config.third_party_id for p in providers]
            assert "github" in provider_ids
            assert "google" in provider_ids

    def test_all_three_providers_can_coexist(self) -> None:
        """Test GitHub, LinkedIn, and Google providers can all be configured together."""
        env_vars = {
            "GITHUB_OAUTH_CLIENT_ID": "github-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "github-secret",  # noqa: S105
            "LINKEDIN_OAUTH_CLIENT_ID": "linkedin-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "linkedin-secret",  # noqa: S105
            "GOOGLE_OAUTH_CLIENT_ID": "google-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GOOGLE_OAUTH_ENABLED", True),
            ):
                providers = get_oauth_providers()

            provider_ids = [p.config.third_party_id for p in providers]
            assert "github" in provider_ids
            assert "linkedin" in provider_ids
            assert "google" in provider_ids
            assert len(providers) == 3


class TestGitHubFeatureFlag:
    """Tests for GitHub OAuth feature flag."""

    def test_github_oauth_enabled_default(self) -> None:
        """Test GITHUB_OAUTH_ENABLED defaults to True."""
        env_vars = {}  # No env var set

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Default should be True
            assert ff_module.GITHUB_OAUTH_ENABLED is True

    def test_github_oauth_can_be_disabled(self) -> None:
        """Test GITHUB_OAUTH_ENABLED can be set to False."""
        env_vars = {"GITHUB_OAUTH_ENABLED": "false"}

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            assert ff_module.GITHUB_OAUTH_ENABLED is False
