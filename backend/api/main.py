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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import context, control, health, sessions, streaming


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
    description="Multi-agent deliberation system for strategic decision-making",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
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
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "message": "Board of One API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),  # noqa: S104  # Binding to all interfaces is intentional for dev
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )
