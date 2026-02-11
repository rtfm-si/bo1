"""Shared Google OAuth2 token refresh helper."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105


def refresh_google_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any] | None:
    """POST to the Google token endpoint.

    Returns the parsed JSON body (``access_token``, ``expires_in``, …)
    on success, or ``None`` on failure.
    """
    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(f"Google token refresh failed: {response.text}")
            return None

        return response.json()
    except requests.RequestException as e:
        logger.error(f"Google token refresh request failed: {e}")
        return None
