"""Tests for SuperTokens Account Linking configuration."""

import pytest
from supertokens_python.recipe.accountlinking.types import (
    ShouldAutomaticallyLink,
    ShouldNotAutomaticallyLink,
)

from backend.api.supertokens_config import (
    TRUSTED_OAUTH_PROVIDERS,
    should_do_automatic_account_linking,
)


class MockAccountInfo:
    """Mock account info for testing.

    Matches the structure of AccountInfoWithRecipeIdAndUserId.
    """

    def __init__(self, recipe_id: str, email: str | None = None):
        self.recipe_id = recipe_id
        self.email = email
        self.phone_number = None
        self.third_party = None
        self.recipe_user_id = None


class TestAccountLinkingPolicy:
    """Tests for the should_do_automatic_account_linking callback."""

    @pytest.mark.asyncio
    async def test_google_oauth_email_links(self) -> None:
        """Test that Google OAuth emails are auto-linked."""
        account_info = MockAccountInfo(
            recipe_id="thirdparty",
            email="user@example.com",
        )

        result = await should_do_automatic_account_linking(
            new_account_info=account_info,  # type: ignore
            user=None,
            session_container=None,
            tenant_id="public",
            user_context={},
        )

        assert isinstance(result, ShouldAutomaticallyLink)
        # OAuth emails are already verified by provider
        assert result.should_require_verification is False

    @pytest.mark.asyncio
    async def test_linkedin_oauth_email_links(self) -> None:
        """Test that LinkedIn OAuth emails are auto-linked."""
        account_info = MockAccountInfo(
            recipe_id="thirdparty",
            email="user@company.com",
        )

        result = await should_do_automatic_account_linking(
            new_account_info=account_info,  # type: ignore
            user=None,
            session_container=None,
            tenant_id="public",
            user_context={},
        )

        assert isinstance(result, ShouldAutomaticallyLink)

    @pytest.mark.asyncio
    async def test_emailpassword_links_with_verification(self) -> None:
        """Test that email/password accounts link with verification required."""
        account_info = MockAccountInfo(
            recipe_id="emailpassword",
            email="user@example.com",
        )

        result = await should_do_automatic_account_linking(
            new_account_info=account_info,  # type: ignore
            user=None,
            session_container=None,
            tenant_id="public",
            user_context={},
        )

        assert isinstance(result, ShouldAutomaticallyLink)
        # Email password requires verification before linking for security
        assert result.should_require_verification is True

    @pytest.mark.asyncio
    async def test_passwordless_links(self) -> None:
        """Test that passwordless (magic link) accounts are auto-linked."""
        account_info = MockAccountInfo(
            recipe_id="passwordless",
            email="user@example.com",
        )

        result = await should_do_automatic_account_linking(
            new_account_info=account_info,  # type: ignore
            user=None,
            session_container=None,
            tenant_id="public",
            user_context={},
        )

        assert isinstance(result, ShouldAutomaticallyLink)
        # Passwordless emails are verified by clicking the link
        assert result.should_require_verification is False

    @pytest.mark.asyncio
    async def test_no_email_does_not_link(self) -> None:
        """Test that accounts without email are not auto-linked."""
        account_info = MockAccountInfo(
            recipe_id="thirdparty",
            email=None,
        )

        result = await should_do_automatic_account_linking(
            new_account_info=account_info,  # type: ignore
            user=None,
            session_container=None,
            tenant_id="public",
            user_context={},
        )

        assert isinstance(result, ShouldNotAutomaticallyLink)

    @pytest.mark.asyncio
    async def test_unknown_recipe_does_not_link(self) -> None:
        """Test that unknown recipe types don't auto-link."""
        account_info = MockAccountInfo(
            recipe_id="unknown_recipe",
            email="user@example.com",
        )

        result = await should_do_automatic_account_linking(
            new_account_info=account_info,  # type: ignore
            user=None,
            session_container=None,
            tenant_id="public",
            user_context={},
        )

        assert isinstance(result, ShouldNotAutomaticallyLink)


class TestTrustedProviders:
    """Tests for trusted OAuth provider configuration."""

    def test_google_is_trusted(self) -> None:
        """Test that Google is in the trusted providers list."""
        assert "google" in TRUSTED_OAUTH_PROVIDERS

    def test_linkedin_is_trusted(self) -> None:
        """Test that LinkedIn is in the trusted providers list."""
        assert "linkedin" in TRUSTED_OAUTH_PROVIDERS

    def test_github_is_trusted(self) -> None:
        """Test that GitHub is in the trusted providers list."""
        assert "github" in TRUSTED_OAUTH_PROVIDERS

    def test_untrusted_provider_not_in_list(self) -> None:
        """Test that random providers are not trusted."""
        assert "random_provider" not in TRUSTED_OAUTH_PROVIDERS
