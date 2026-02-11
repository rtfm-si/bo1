"""Shared Tavily web-search client."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import httpx

from bo1.config import get_settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyClient:
    """Thin async wrapper around the Tavily REST API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialise with explicit key or fall back to settings."""
        self._api_key = api_key or get_settings().tavily_api_key

    async def search(
        self,
        query: str,
        *,
        search_depth: str = "basic",
        max_results: int = 5,
        timeout: float = 30.0,
        include_domains: list[str] | None = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        """Execute a Tavily search and return the full response body.

        Returns the raw JSON dict so callers can access both ``results``
        and optional fields like ``answer``.
        """
        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
        }
        if include_domains:
            payload["include_domains"] = include_domains
        if include_answer:
            payload["include_answer"] = True
        if include_raw_content:
            payload["include_raw_content"] = True

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(TAVILY_SEARCH_URL, json=payload)
            response.raise_for_status()
            return response.json()


@lru_cache(maxsize=1)
def get_tavily_client() -> TavilyClient:
    """Return a module-level singleton."""
    return TavilyClient()
