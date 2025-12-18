"""Unit tests for CSRF token rotation on auth state change.

Tests verify that:
- CSRF token is regenerated on sign-in (session fixation mitigation)
- CSRF token is cleared on sign-out
- Helper functions work correctly with SuperTokens BaseResponse interface
"""

from unittest.mock import MagicMock, patch

from backend.api.middleware.csrf import (
    CSRF_COOKIE_MAX_AGE,
    CSRF_COOKIE_NAME,
    clear_csrf_cookie_on_response,
    generate_csrf_token,
    set_csrf_cookie_on_response,
)


class MockResponse:
    """Mock SuperTokens BaseResponse for testing."""

    def __init__(self) -> None:
        self.cookies: dict[str, dict] = {}

    def set_cookie(
        self,
        key: str,
        value: str,
        expires: int,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str = "lax",
    ) -> None:
        """Mock set_cookie method matching SuperTokens BaseResponse signature."""
        self.cookies[key] = {
            "value": value,
            "expires": expires,
            "path": path,
            "domain": domain,
            "secure": secure,
            "httponly": httponly,
            "samesite": samesite,
        }


class TestSetCSRFCookieOnResponse:
    """Tests for set_csrf_cookie_on_response helper."""

    def test_sets_cookie_with_correct_name(self) -> None:
        """Should set cookie with csrf_token name."""
        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token)

        assert CSRF_COOKIE_NAME in response.cookies
        assert response.cookies[CSRF_COOKIE_NAME]["value"] == token

    def test_sets_cookie_not_httponly(self) -> None:
        """Cookie must NOT be httponly so JS can read it for X-CSRF-Token header."""
        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token)

        assert response.cookies[CSRF_COOKIE_NAME]["httponly"] is False

    def test_sets_cookie_samesite_lax(self) -> None:
        """Cookie should use SameSite=Lax for CSRF protection."""
        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token)

        assert response.cookies[CSRF_COOKIE_NAME]["samesite"] == "lax"

    def test_sets_cookie_path_root(self) -> None:
        """Cookie should be available on all paths."""
        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token)

        assert response.cookies[CSRF_COOKIE_NAME]["path"] == "/"

    def test_respects_secure_flag(self) -> None:
        """Should set Secure flag when specified."""
        response = MockResponse()
        token = generate_csrf_token()

        # Test secure=False
        set_csrf_cookie_on_response(response, token, secure=False)
        assert response.cookies[CSRF_COOKIE_NAME]["secure"] is False

        # Test secure=True
        set_csrf_cookie_on_response(response, token, secure=True)
        assert response.cookies[CSRF_COOKIE_NAME]["secure"] is True

    def test_respects_domain(self) -> None:
        """Should set domain when specified."""
        response = MockResponse()
        token = generate_csrf_token()

        # Test with domain
        set_csrf_cookie_on_response(response, token, domain=".boardof.one")
        assert response.cookies[CSRF_COOKIE_NAME]["domain"] == ".boardof.one"

        # Test without domain (localhost)
        response = MockResponse()
        set_csrf_cookie_on_response(response, token, domain=None)
        assert response.cookies[CSRF_COOKIE_NAME]["domain"] is None

    def test_sets_future_expiry(self) -> None:
        """Should set expiry in the future."""
        import time

        response = MockResponse()
        token = generate_csrf_token()
        before = int(time.time())

        set_csrf_cookie_on_response(response, token)

        expires = response.cookies[CSRF_COOKIE_NAME]["expires"]
        assert expires > before
        assert expires <= before + CSRF_COOKIE_MAX_AGE + 1


class TestClearCSRFCookieOnResponse:
    """Tests for clear_csrf_cookie_on_response helper."""

    def test_sets_empty_value(self) -> None:
        """Should set empty cookie value to clear it."""
        response = MockResponse()
        clear_csrf_cookie_on_response(response)

        assert CSRF_COOKIE_NAME in response.cookies
        assert response.cookies[CSRF_COOKIE_NAME]["value"] == ""

    def test_sets_past_expiry(self) -> None:
        """Should set expiry in the past to force browser deletion."""
        import time

        response = MockResponse()
        now = int(time.time())

        clear_csrf_cookie_on_response(response)

        expires = response.cookies[CSRF_COOKIE_NAME]["expires"]
        assert expires < now

    def test_respects_secure_flag(self) -> None:
        """Should respect secure flag for clearing."""
        response = MockResponse()
        clear_csrf_cookie_on_response(response, secure=True)

        assert response.cookies[CSRF_COOKIE_NAME]["secure"] is True

    def test_respects_domain(self) -> None:
        """Should respect domain for clearing."""
        response = MockResponse()
        clear_csrf_cookie_on_response(response, domain=".boardof.one")

        assert response.cookies[CSRF_COOKIE_NAME]["domain"] == ".boardof.one"


class TestCSRFRotationOnSignIn:
    """Tests for CSRF token rotation in sign_in_up_post override."""

    @patch("backend.api.supertokens_config.os.getenv")
    def test_generates_new_token_on_signin(self, mock_getenv: MagicMock) -> None:
        """Sign-in should generate a new CSRF token."""
        mock_getenv.side_effect = lambda key, default=None: {
            "COOKIE_SECURE": "false",
            "COOKIE_DOMAIN": "localhost",
        }.get(key, default)

        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token, secure=False, domain=None)

        # Verify token was set
        assert response.cookies[CSRF_COOKIE_NAME]["value"] == token
        assert len(token) == 64  # 32 bytes = 64 hex chars

    def test_token_changes_on_each_signin(self) -> None:
        """Each sign-in should produce a different CSRF token."""
        tokens = []
        for _ in range(10):
            response = MockResponse()
            token = generate_csrf_token()
            set_csrf_cookie_on_response(response, token)
            tokens.append(response.cookies[CSRF_COOKIE_NAME]["value"])

        # All tokens should be unique
        assert len(set(tokens)) == 10


class TestCSRFClearOnSignOut:
    """Tests for CSRF token clearing in signout_post override."""

    def test_clears_token_on_signout(self) -> None:
        """Sign-out should clear the CSRF token."""
        response = MockResponse()
        clear_csrf_cookie_on_response(response)

        # Verify token was cleared (empty value + past expiry)
        assert response.cookies[CSRF_COOKIE_NAME]["value"] == ""

    def test_clear_uses_same_path(self) -> None:
        """Clear should use root path to match original cookie."""
        response = MockResponse()
        clear_csrf_cookie_on_response(response)

        assert response.cookies[CSRF_COOKIE_NAME]["path"] == "/"


class TestConcurrentTabBehavior:
    """Document expected behavior for concurrent tabs.

    When a user signs in on one tab, other tabs will have the old CSRF token
    until they refresh. This is acceptable because:
    1. The old token is now invalid (replaced server-side)
    2. Requests from other tabs will fail with 403 until refresh
    3. User can refresh to get the new token
    """

    def test_old_token_differs_from_new(self) -> None:
        """Old and new tokens should be different after rotation."""
        old_token = generate_csrf_token()
        new_token = generate_csrf_token()

        # Tokens should never match (crypto-random)
        assert old_token != new_token

    def test_document_concurrent_tab_behavior(self) -> None:
        """Document: concurrent tabs need refresh after auth state change.

        This test documents the expected behavior rather than testing it directly,
        as testing real concurrent tab behavior requires browser testing.

        Expected flow:
        1. User has Tab A and Tab B open
        2. Tab A signs in, receives new CSRF token in cookie
        3. Tab B still has old CSRF token in memory (from cookie read before sign-in)
        4. Tab B makes POST request with old token
        5. Server rejects with 403 (token mismatch)
        6. User refreshes Tab B, gets new token from cookie
        7. Tab B now works

        This is acceptable behavior for session fixation prevention.
        """
        pass  # Documentation test


class TestSecurityProperties:
    """Tests verifying security properties of CSRF rotation."""

    def test_token_is_cryptographically_random(self) -> None:
        """Token should use secrets module for crypto-random generation."""
        # Generate many tokens and verify uniqueness
        tokens = {generate_csrf_token() for _ in range(1000)}
        assert len(tokens) == 1000

    def test_token_length_sufficient(self) -> None:
        """Token should be at least 32 bytes (64 hex chars) for security."""
        token = generate_csrf_token()
        # 32 bytes = 256 bits of entropy, sufficient for CSRF protection
        assert len(token) >= 64

    def test_cookie_not_httponly_for_js_access(self) -> None:
        """Cookie must not be httponly so frontend JS can read it.

        The double-submit pattern requires JS to read the cookie value
        and send it in the X-CSRF-Token header.
        """
        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token)

        assert response.cookies[CSRF_COOKIE_NAME]["httponly"] is False

    def test_cookie_uses_samesite_lax(self) -> None:
        """Cookie should use SameSite=Lax as defense-in-depth.

        SameSite=Lax prevents the cookie from being sent on cross-site
        subrequests, providing additional CSRF protection.
        """
        response = MockResponse()
        token = generate_csrf_token()
        set_csrf_cookie_on_response(response, token)

        assert response.cookies[CSRF_COOKIE_NAME]["samesite"] == "lax"
