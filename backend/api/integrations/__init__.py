"""Integration API endpoints."""

from backend.api.integrations.calendar import router as calendar_router
from backend.api.integrations.search_console import router as search_console_router

__all__ = ["calendar_router", "search_console_router"]
