"""Tests for Bluesky OAuth configuration (AT Protocol)."""

import importlib
import os
from unittest.mock import patch

from backend.api.supertokens_config import get_oauth_providers


class TestBlueskyOAuthProvider:
    """Tests for Bluesky OAuth provider configuration."""

    def test_bluesky_provider_configured_when_credentials_present(self) -> None:
        """Test Bluesky provider is added when credentials are present."""
        env_vars = {
            "BLUESKY_CLIENT_ID": "test-bluesky-client-id",
            "BLUESKY_CLIENT_SECRET": "test-bluesky-client-secret",  # noqa: S105
            "BLUESKY_OAUTH_ENABLED": "true",
            # Disable other providers to isolate Bluesky test
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
            "TWITTER_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Need to reload feature flags to pick up env changes
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Force the module-level variable to True for this test
            with patch("backend.api.supertokens_config.BLUESKY_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should have Bluesky provider
            bluesky_providers = [p for p in providers if p.config.third_party_id == "bluesky"]
            assert len(bluesky_providers) == 1

            bluesky = bluesky_providers[0]
            assert bluesky.config.third_party_id == "bluesky"
            assert len(bluesky.config.clients) == 1
            assert bluesky.config.clients[0].client_id == "test-bluesky-client-id"
            # Check client_secret exists (not the value, to avoid hardcoded secret warning)
            assert bluesky.config.clients[0].client_secret

    def test_bluesky_provider_not_configured_when_disabled(self) -> None:
        """Test Bluesky provider is not added when disabled via feature flag."""
        env_vars = {
            "BLUESKY_CLIENT_ID": "test-bluesky-client-id",
            "BLUESKY_CLIENT_SECRET": "test-bluesky-client-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
            "TWITTER_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.BLUESKY_OAUTH_ENABLED", False):
                providers = get_oauth_providers()

            # Should not have Bluesky provider
            bluesky_providers = [p for p in providers if p.config.third_party_id == "bluesky"]
            assert len(bluesky_providers) == 0

    def test_bluesky_provider_not_configured_when_credentials_missing(self) -> None:
        """Test Bluesky provider is not added when credentials are missing."""
        env_vars = {
            "BLUESKY_CLIENT_ID": "",
            "BLUESKY_CLIENT_SECRET": "",
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
            "TWITTER_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.BLUESKY_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            # Should not have Bluesky provider
            bluesky_providers = [p for p in providers if p.config.third_party_id == "bluesky"]
            assert len(bluesky_providers) == 0

    def test_bluesky_provider_scopes(self) -> None:
        """Test Bluesky provider has correct OAuth scopes."""
        env_vars = {
            "BLUESKY_CLIENT_ID": "test-id",
            "BLUESKY_CLIENT_SECRET": "test-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
            "TWITTER_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.BLUESKY_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            bluesky_providers = [p for p in providers if p.config.third_party_id == "bluesky"]
            assert len(bluesky_providers) == 1

            scopes = bluesky_providers[0].config.clients[0].scope
            # Bluesky uses AT Protocol scopes
            assert "atproto" in scopes
            assert "transition:generic" in scopes

    def test_bluesky_provider_endpoints(self) -> None:
        """Test Bluesky provider has correct AT Protocol endpoints."""
        env_vars = {
            "BLUESKY_CLIENT_ID": "test-id",
            "BLUESKY_CLIENT_SECRET": "test-secret",  # noqa: S105
            "GOOGLE_OAUTH_ENABLED": "false",
            "LINKEDIN_OAUTH_ENABLED": "false",
            "GITHUB_OAUTH_ENABLED": "false",
            "TWITTER_OAUTH_ENABLED": "false",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with patch("backend.api.supertokens_config.BLUESKY_OAUTH_ENABLED", True):
                providers = get_oauth_providers()

            bluesky_providers = [p for p in providers if p.config.third_party_id == "bluesky"]
            assert len(bluesky_providers) == 1

            bluesky = bluesky_providers[0]
            # Check AT Protocol endpoints
            assert bluesky.config.authorization_endpoint == "https://bsky.social/oauth/authorize"
            assert bluesky.config.token_endpoint == "https://bsky.social/oauth/token"  # noqa: S105
            assert (
                bluesky.config.user_info_endpoint
                == "https://bsky.social/xrpc/app.bsky.actor.getProfile"
            )

    def test_bluesky_and_other_providers_can_coexist(self) -> None:
        """Test Bluesky can coexist with other OAuth providers."""
        env_vars = {
            "BLUESKY_CLIENT_ID": "bluesky-id",
            "BLUESKY_CLIENT_SECRET": "bluesky-secret",  # noqa: S105
            "GOOGLE_OAUTH_CLIENT_ID": "google-id",
            "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",  # noqa: S105
            "LINKEDIN_OAUTH_CLIENT_ID": "linkedin-id",
            "LINKEDIN_OAUTH_CLIENT_SECRET": "linkedin-secret",  # noqa: S105
            "GITHUB_OAUTH_CLIENT_ID": "github-id",
            "GITHUB_OAUTH_CLIENT_SECRET": "github-secret",  # noqa: S105
            "TWITTER_OAUTH_CLIENT_ID": "twitter-id",
            "TWITTER_OAUTH_CLIENT_SECRET": "twitter-secret",  # noqa: S105
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with (
                patch("backend.api.supertokens_config.BLUESKY_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GOOGLE_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.LINKEDIN_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.GITHUB_OAUTH_ENABLED", True),
                patch("backend.api.supertokens_config.TWITTER_OAUTH_ENABLED", True),
            ):
                providers = get_oauth_providers()

            provider_ids = [p.config.third_party_id for p in providers]
            assert "bluesky" in provider_ids
            assert "google" in provider_ids
            assert "linkedin" in provider_ids
            assert "github" in provider_ids
            assert "twitter" in provider_ids
            assert len(providers) == 5


class TestBlueskyFeatureFlag:
    """Tests for Bluesky OAuth feature flag."""

    def test_bluesky_oauth_disabled_by_default(self) -> None:
        """Test BLUESKY_OAUTH_ENABLED defaults to False."""
        env_vars = {}  # No env var set

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            # Default should be False (conservative rollout)
            assert ff_module.BLUESKY_OAUTH_ENABLED is False

    def test_bluesky_oauth_can_be_enabled(self) -> None:
        """Test BLUESKY_OAUTH_ENABLED can be set to True."""
        env_vars = {"BLUESKY_OAUTH_ENABLED": "true"}

        with patch.dict(os.environ, env_vars, clear=True):
            import bo1.feature_flags.features as ff_module

            importlib.reload(ff_module)

            assert ff_module.BLUESKY_OAUTH_ENABLED is True
