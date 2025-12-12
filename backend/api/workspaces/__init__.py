"""Workspaces API module."""


def __getattr__(name: str) -> object:
    """Lazy import to avoid circular imports."""
    if name == "router":
        from backend.api.workspaces.routes import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router"]
