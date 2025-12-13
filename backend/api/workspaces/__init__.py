"""Workspaces API module."""


def __getattr__(name: str) -> object:
    """Lazy import to avoid circular imports."""
    if name == "router":
        from backend.api.workspaces.routes import router

        return router
    if name == "invitations_user_router":
        from backend.api.workspaces.invitations import user_router

        return user_router
    if name == "billing_router":
        from backend.api.workspaces.billing import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["router", "invitations_user_router", "billing_router"]
