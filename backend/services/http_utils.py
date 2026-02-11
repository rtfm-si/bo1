"""HTTP session factory with retry logic."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_STATUS_FORCELIST = [500, 502, 503, 504]


def create_resilient_session(
    status_forcelist: list[int] | None = None,
    total_retries: int = 3,
    backoff_factor: float = 0.5,
) -> requests.Session:
    """Create a requests.Session with automatic retry on transient errors."""
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist or DEFAULT_STATUS_FORCELIST,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session
