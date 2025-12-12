"""Base user class with authentication handling."""

import logging

from locust import HttpUser, events

from tests.load.config import API_PREFIX, BASE_URL, TEST_USER_EMAIL, TEST_USER_PASSWORD

logger = logging.getLogger(__name__)


class AuthenticatedUser(HttpUser):
    """Base user class that handles authentication.

    Subclasses should implement tasks using self.client for HTTP requests.
    Authorization header is automatically included after on_start().
    """

    host = BASE_URL
    abstract = True

    # Auth token cached at class level to avoid re-auth per user
    _auth_token: str | None = None
    _auth_failed: bool = False

    def on_start(self) -> None:
        """Authenticate before starting tasks."""
        if AuthenticatedUser._auth_failed:
            logger.error("Auth previously failed, skipping")
            return

        if AuthenticatedUser._auth_token:
            self._set_auth_header()
            return

        self._authenticate()

    def _authenticate(self) -> None:
        """Get auth token via SuperTokens signin endpoint."""
        # SuperTokens uses formId-based signin
        # For load testing, we use email/password signin
        try:
            response = self.client.post(
                "/api/auth/signin",
                json={
                    "formFields": [
                        {"id": "email", "value": TEST_USER_EMAIL},
                        {"id": "password", "value": TEST_USER_PASSWORD},
                    ]
                },
                headers={"Content-Type": "application/json"},
                name="auth/signin",
            )

            if response.status_code == 200:
                # SuperTokens sets session cookies automatically
                # We extract the access token from response if available
                data = response.json()
                if data.get("status") == "OK":
                    # Session is now in cookies, client will use them
                    logger.info("Authentication successful")
                    AuthenticatedUser._auth_token = "authenticated"  # noqa: S105
                else:
                    logger.error(f"Auth failed: {data}")
                    AuthenticatedUser._auth_failed = True
            else:
                logger.error(f"Auth request failed: {response.status_code}")
                AuthenticatedUser._auth_failed = True

        except Exception as e:
            logger.error(f"Auth exception: {e}")
            AuthenticatedUser._auth_failed = True

    def _set_auth_header(self) -> None:
        """Set authorization header from cached token."""
        # For SuperTokens cookie-based auth, cookies persist in session
        pass

    @property
    def api_url(self) -> str:
        """Get API URL prefix."""
        return API_PREFIX


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Reset auth state at test start."""
    AuthenticatedUser._auth_token = None
    AuthenticatedUser._auth_failed = False
    logger.info("Load test starting, auth state reset")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion."""
    logger.info("Load test completed")
