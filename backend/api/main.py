"""FastAPI application for Board of One web API.

Provides HTTP endpoints for:
- Health checks (database, Redis, Anthropic API)
- Deliberation execution with SSE streaming
- User context management
- Session management
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse

from backend.api import admin, context, control, health, sessions, streaming
from backend.api.middleware.auth import require_admin


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    print("Starting Board of One API...")
    yield
    # Shutdown
    print("Shutting down Board of One API...")


# Create FastAPI application
app = FastAPI(
    title="Board of One API",
    description="""
    **Board of One** is a multi-agent deliberation system that uses AI personas
    to provide strategic decision-making insights through structured debate and synthesis.

    ## Features

    - **Multi-Agent Deliberation**: 3-5 expert personas debate your problem
    - **Structured Synthesis**: AI-powered consensus building
    - **Real-time Streaming**: Server-Sent Events (SSE) for live updates
    - **Context Management**: Business context and clarification support
    - **Session Control**: Pause, resume, and kill deliberations
    - **Admin Monitoring**: Track and manage all active sessions

    ## Authentication

    - **User Endpoints**: Currently use hardcoded user ID (test_user_1) for MVP
    - **Admin Endpoints**: Require X-Admin-Key header with valid admin API key

    ## Rate Limits

    - No rate limits enforced in v1.0 (MVP)
    - Will be added in v2.0 with Stripe integration

    ## Support

    - Documentation: [GitHub](https://github.com/anthropics/board-of-one)
    - Issues: [GitHub Issues](https://github.com/anthropics/board-of-one/issues)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable public docs (admin-only via custom endpoint)
    redoc_url=None,  # Disable public redoc
    openapi_url=None,  # Disable public OpenAPI spec
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check endpoints for monitoring system status",
        },
        {
            "name": "sessions",
            "description": "Session management (create, list, get details)",
        },
        {
            "name": "streaming",
            "description": "Real-time deliberation streaming via Server-Sent Events (SSE)",
        },
        {
            "name": "context",
            "description": "User context management (business info, clarifications)",
        },
        {
            "name": "deliberation-control",
            "description": "Deliberation control (start, pause, resume, kill, clarify)",
        },
        {
            "name": "admin",
            "description": "Admin endpoints (requires X-Admin-Key header)",
        },
    ],
)

# Configure CORS
# Parse CORS origins from environment variable
# Format: Comma-separated list (e.g., "http://localhost:3000,http://localhost:5173")
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
CORS_ORIGINS = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(streaming.router, prefix="/api", tags=["streaming"])
app.include_router(context.router, prefix="/api", tags=["context"])
app.include_router(control.router, prefix="/api", tags=["deliberation-control"])
app.include_router(admin.router, prefix="/api", tags=["admin"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSON error response
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "type": type(exc).__name__,
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Public landing page.

    Returns:
        Welcome message for visitors
    """
    return {
        "service": "Board of One",
        "description": "AI-powered strategic decision-making through multi-agent deliberation",
        "status": "Private Beta",
        "message": "This is a private API service. Access requires authentication.",
        "contact": "For access, visit boardof.one",
    }


@app.get("/admin/info")
async def admin_info(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Admin-only API information endpoint.

    Args:
        user: Admin user data

    Returns:
        Detailed API information for admins
    """
    return {
        "message": "Board of One API - Admin Panel",
        "version": "1.0.0",
        "admin_user": user.get("email"),
        "admin_id": user.get("user_id"),
        "documentation": {
            "swagger": "/admin/docs",
            "redoc": "/admin/redoc",
            "openapi_spec": "/admin/openapi.json",
        },
        "services": {
            "api": "Running",
            "authentication": "Supabase JWT",
            "mode": "Closed Beta",
        },
    }


@app.get("/admin/docs", response_class=HTMLResponse, include_in_schema=False)
async def admin_docs(user: dict[str, Any] = Depends(require_admin)) -> HTMLResponse:
    """Admin-only Swagger UI documentation.

    Args:
        user: Admin user data

    Returns:
        Swagger UI HTML
    """
    return get_swagger_ui_html(
        openapi_url="/admin/openapi.json",
        title=f"{app.title} - Admin Documentation",
        swagger_favicon_url="/favicon.ico",
    )


@app.get("/admin/redoc", response_class=HTMLResponse, include_in_schema=False)
async def admin_redoc(user: dict[str, Any] = Depends(require_admin)) -> HTMLResponse:
    """Admin-only ReDoc documentation.

    Args:
        user: Admin user data

    Returns:
        ReDoc HTML
    """
    return get_redoc_html(
        openapi_url="/admin/openapi.json",
        title=f"{app.title} - Admin Documentation",
        redoc_favicon_url="/favicon.ico",
    )


@app.get("/admin/openapi.json", include_in_schema=False)
async def admin_openapi(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Admin-only OpenAPI specification.

    Args:
        user: Admin user data

    Returns:
        OpenAPI JSON spec
    """
    return app.openapi()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),  # noqa: S104  # Binding to all interfaces is intentional for dev
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )
