"""Context variables for async request tracing.

Provides request_id propagation through async execution without explicit parameter passing.
"""

import contextvars

# Context variable for request/correlation ID
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def set_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    """Set the current request ID in async context."""
    return request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Get the current request ID from async context."""
    return request_id_var.get()


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    """Reset request ID to previous value using token from set_request_id()."""
    request_id_var.reset(token)
