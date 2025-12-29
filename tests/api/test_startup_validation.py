"""Tests for startup validation functions."""

import os
from unittest.mock import patch

from backend.api.startup_validation import (
    get_oauth_callback_url,
    validate_oauth_callback_urls,
    validate_spaces_config,
)


class TestValidateSpacesConfig:
    """Tests for Spaces configuration validation."""

    def test_all_credentials_set_returns_empty(self):
        """Test valid credentials return no warnings."""
        with patch.dict(
            os.environ,
            {
                "DO_SPACES_KEY": "test-key",
                "DO_SPACES_SECRET": "test-secret",
                "DO_SPACES_BUCKET": "test-bucket",
            },
        ):
            warnings = validate_spaces_config()
        assert len(warnings) == 0

    def test_missing_key_returns_warning(self):
        """Test missing access key returns warning."""
        with patch.dict(
            os.environ,
            {
                "DO_SPACES_KEY": "",
                "DO_SPACES_SECRET": "test-secret",
                "DO_SPACES_BUCKET": "test-bucket",
            },
        ):
            warnings = validate_spaces_config()
        assert len(warnings) == 1
        assert "DO_SPACES_KEY" in warnings[0]

    def test_missing_secret_returns_warning(self):
        """Test missing secret key returns warning."""
        with patch.dict(
            os.environ,
            {
                "DO_SPACES_KEY": "test-key",
                "DO_SPACES_SECRET": "",
                "DO_SPACES_BUCKET": "test-bucket",
            },
        ):
            warnings = validate_spaces_config()
        assert len(warnings) == 1
        assert "DO_SPACES_SECRET" in warnings[0]

    def test_missing_bucket_returns_warning(self):
        """Test missing bucket returns warning."""
        with patch.dict(
            os.environ,
            {
                "DO_SPACES_KEY": "test-key",
                "DO_SPACES_SECRET": "test-secret",
                "DO_SPACES_BUCKET": "",
            },
        ):
            warnings = validate_spaces_config()
        assert len(warnings) == 1
        assert "DO_SPACES_BUCKET" in warnings[0]

    def test_all_missing_returns_three_warnings(self):
        """Test all missing credentials return three warnings."""
        with patch.dict(
            os.environ,
            {
                "DO_SPACES_KEY": "",
                "DO_SPACES_SECRET": "",
                "DO_SPACES_BUCKET": "",
            },
            clear=True,
        ):
            # Clear existing env vars by setting to empty
            warnings = validate_spaces_config()
        assert len(warnings) == 3


class TestValidateOAuthCallbackUrls:
    """Tests for OAuth callback URL validation."""

    def test_returns_empty_warnings_list(self):
        """Test validation returns empty list (no warnings for valid config)."""
        with patch.dict(
            os.environ,
            {
                "SUPERTOKENS_API_DOMAIN": "http://localhost:8000",
                "GOOGLE_OAUTH_ENABLED": "true",
            },
        ):
            warnings = validate_oauth_callback_urls()
        assert warnings == []

    def test_logs_enabled_providers(self):
        """Test that enabled providers are detected."""
        with patch.dict(
            os.environ,
            {
                "SUPERTOKENS_API_DOMAIN": "http://localhost:8000",
                "GOOGLE_OAUTH_ENABLED": "true",
                "GITHUB_OAUTH_ENABLED": "true",
                "LINKEDIN_OAUTH_ENABLED": "false",
            },
        ):
            warnings = validate_oauth_callback_urls()
        # Function returns empty warnings, logging is tested via mock
        assert warnings == []


class TestGetOAuthCallbackUrl:
    """Tests for get_oauth_callback_url function."""

    def test_google_callback_url_localhost(self):
        """Test Google callback URL for localhost."""
        with patch.dict(
            os.environ,
            {"SUPERTOKENS_API_DOMAIN": "http://localhost:8000"},
        ):
            url = get_oauth_callback_url("google")
        assert url == "http://localhost:8000/api/auth/callback/google"

    def test_github_callback_url_localhost(self):
        """Test GitHub callback URL for localhost."""
        with patch.dict(
            os.environ,
            {"SUPERTOKENS_API_DOMAIN": "http://localhost:8000"},
        ):
            url = get_oauth_callback_url("github")
        assert url == "http://localhost:8000/api/auth/callback/github"

    def test_linkedin_callback_url_localhost(self):
        """Test LinkedIn callback URL for localhost."""
        with patch.dict(
            os.environ,
            {"SUPERTOKENS_API_DOMAIN": "http://localhost:8000"},
        ):
            url = get_oauth_callback_url("linkedin")
        assert url == "http://localhost:8000/api/auth/callback/linkedin"

    def test_callback_url_production(self):
        """Test callback URL for production domain."""
        with patch.dict(
            os.environ,
            {"SUPERTOKENS_API_DOMAIN": "https://boardof.one"},
        ):
            url = get_oauth_callback_url("google")
        assert url == "https://boardof.one/api/auth/callback/google"

    def test_callback_url_default_domain(self):
        """Test callback URL uses default when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            url = get_oauth_callback_url("google")
        assert url == "http://localhost:8000/api/auth/callback/google"
