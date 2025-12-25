"""Utility modules for Board of One API."""

from backend.api.utils.errors import ErrorDetailDict, http_error
from backend.api.utils.pagination import make_page_pagination_fields, make_pagination_fields
from backend.api.utils.validation import (
    validate_cache_id,
    validate_session_id,
    validate_user_id,
)


def __getattr__(name: str) -> object:
    """Lazy load RATE_LIMIT_RESPONSE to avoid circular import with models.py."""
    if name == "RATE_LIMIT_RESPONSE":
        from backend.api.utils.responses import RATE_LIMIT_RESPONSE

        return RATE_LIMIT_RESPONSE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ErrorDetailDict",
    "RATE_LIMIT_RESPONSE",
    "http_error",
    "make_page_pagination_fields",
    "make_pagination_fields",
    "validate_cache_id",
    "validate_session_id",
    "validate_user_id",
]
