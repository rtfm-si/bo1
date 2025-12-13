"""Tests for Twitter/X OAuth configuration."""

import importlib
import os
from unittest.mock import patch

from backend.api.supertokens_config import get_oauth_providers


class TestTwitterOAuthProvider:
    """Tests for Twitter/X OAuth provider configuration."""

    def test_twitter_provider_configured_when_credentials_present(self) -> None:
        """Test Twitter provider is added when credentials are present."""
        env_vars = {
            "TWITTER_OAUTH_CLIENT_ID": "test-twitter-client-id",
            "TWITTER_OAUTH_CLIENT_SECRET": "test-twitter-client-secret",  # noqa: S105
            "TWITTER_OAUTH_ENABLED": "true",
            # Disable other providers to isolate Twitter test
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Need to reload feature flags to pick up env changes
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Force the module-level variable to True for this test
            with patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should have Twitter provider
            twitter_providers = [p for p in providers if p.config.third_party_id == "twitter"]
            assert len(twitter_providers) == 1

            twitter = twitter_providers[0]
            assert twitter.config.third_party_id == "twitter"
            assert len(twitter.config.clients) == 1
            assert twitter.config.clients[0].client_id == "test-twitter-client-id"
            # Check client_secret exists (not the value, to avoid hardcoded secret warning)
            assert twitter.config.clients[0].client_secret

    def test_twitter_provider_not_configured_when_disabled(self) -> None:
        """Test Twitter provider is not added when disabled via feature flag."""
        env_vars = {
            "TWITTER_OAUTH_CLIENT_ID": "test-twitter-client-id",
            "TWITTER_OAUTH_CLIENT_SECRET": "test-twitter-client-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", False):
                providers = get_oauth_providers()

            # Should not have Twitter provider
            twitter_providers = [p for p in providers if p.config.third_party_id == "twitter"]
            assert len(twitter_providers) == 0

    def test_twitter_provider_not_configured_when_credentials_missing(self) -> None:
        """Test Twitter provider is not added when credentials are missing."""
        env_vars = {
            "TWITTER_OAUTH_CLIENT_ID": "",
            "TWITTER_OAUTH_CLIENT_SECRET": "",
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should not have Twitter provider
            twitter_providers = [p for p in providers if p.config.third_party_id == "twitter"]
            assert len(twitter_providers) == 0

    def test_twitter_provider_scopes(self) -> None:
        """Test Twitter provider has correct OAuth scopes."""
        env_vars = {
            "TWITTER_OAUTH_CLIENT_ID": "test-id",
            "TWITTER_OAUTH_CLIENT_SECRET": "test-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            twitter_providers = [p for p in providers if p.config.third_party_id == "twitter"]
            assert len(twitter_providers) == 1

            scopes = twitter_providers[0].config.clients[0].scope
            # Twitter uses users.read and tweet.read scopes
            assert "users.read" in scopes
            assert "tweet.read" in scopes

    def test_twitter_and_google_can_coexist(self) -> None:
        """Test both Twitter and Google providers can be configured together."""
        env_vars = {
            "TWITTER_OAUTH_CLIENT_ID": "twitter-id",
            "TWITTER_OAUTH_CLIENT_SECRET": "twitter-secret",  # noqa: S105
            "GOOGLE_OAUTH_CLIENT_ID": "google-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",  # noqa: S105
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GOOGLE_OAUTH_ENABLED", True),
            ):
                providers = get_oauth_providers()

            provider_ids = [p.config.third_party_id for p in providers]
            assert "twitter" in provider_ids
            assert "google" in provider_ids

    def test_all_four_providers_can_coexist(self) -> None:
        """Test Twitter, GitHub, LinkedIn, and Google providers can all be configured together."""
        env_vars = {
            "TWITTER_OAUTH_CLIENT_ID": "twitter-id",
            "TWITTER_OAUTH_CLIENT_SECRET": "twitter-secret",  # noqa: S105
            "GITHUB_OAUTH_CLIENT_ID": "github-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "github-secret",  # noqa: S105
            "LINKEDIN_OAUTH_CLIENT_ID": "linkedin-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "linkedin-secret",  # noqa: S105
            "GOOGLE_OAUTH_CLIENT_ID": "google-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GOOGLE_OAUTH_ENABLED", True),
            ):
                providers = get_oauth_providers()

            provider_ids = [p.config.third_party_id for p in providers]
            assert "twitter" in provider_ids
            assert "github" in provider_ids
            assert "linkedin" in provider_ids
            assert "google" in provider_ids
            assert len(providers) == 4


class TestTwitterFeatureFlag:
    """Tests for Twitter OAuth feature flag."""

    def test_twitter_oauth_disabled_by_default(self) -> None:
        """Test TWITTER_OAUTH_ENABLED defaults to False."""
        env_vars = {}  # No env var set

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Default should be False (unlike other providers)
            assert ff_module.TWITTER_OAUTH_ENABLED is False

    def test_twitter_oauth_can_be_enabled(self) -> None:
        """Test TWITTER_OAUTH_ENABLED can be set to True."""
        env_vars = {"TWITTER_OAUTH_ENABLED": "true"}

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            assert ff_module.TWITTER_OAUTH_ENABLED is True
