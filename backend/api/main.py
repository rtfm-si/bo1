"""FastAPI application for Board of One web API.

Provides HTTP endpoints for:
- Health checks (database, Redis, Anthropic API)
- Deliberation execution with SSE streaming
- User context management
- Session management

Features:
- Graceful shutdown with in-flight request draining
- SIGTERM/SIGINT signal handling
- Health probes for k8s (liveness: /health, readiness: /ready)
"""

import time as _time_module

_module_load_start = _time_module.perf_counter()

import asyncio  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402

# Configure logging early, before other imports that may log
from backend.api.logging_config import configure_logging  # noqa: E402
from bo1.config import get_settings as _get_settings_early  # noqa: E402

_early_settings = _get_settings_early()
configure_logging(
    log_level=_early_settings.log_level,
    log_format=_early_settings.log_format,
    verbose_libs=_early_settings.verbose_libs,
)
import signal  # noqa: E402
import time  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from typing import Any  # noqa: E402

from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.middleware.gzip import GZipMiddleware  # noqa: E402
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html  # noqa: E402
from fastapi.responses import HTMLResponse, JSONResponse  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from backend.api import (  # noqa: E402
    actions,
    admin,
    analysis,
    auth,
    billing,
    business_metrics,
    client_errors,
    client_metrics,
    competitors,
    context,
    control,
    csp_reports,
    datasets,
    email,
    feedback,
    health,
    industry_insights,
    mentor,
    onboarding,
    page_analytics,
    projects,
    sessions,
    share,
    status,
    streaming,
    tags,
    user,
    waitlist,
    workspaces,
)
from backend.api.integrations import calendar_router  # noqa: E402
from backend.api.middleware.api_version import API_VERSION, ApiVersionMiddleware  # noqa: E402
from backend.api.middleware.audit_logging import AuditLoggingMiddleware  # noqa: E402
from backend.api.middleware.auth import require_admin  # noqa: E402
from backend.api.middleware.correlation_id import CorrelationIdMiddleware  # noqa: E402
from backend.api.middleware.csrf import CSRFMiddleware  # noqa: E402
from backend.api.middleware.degraded_mode import DegradedModeMiddleware  # noqa: E402
from backend.api.middleware.metrics import create_instrumentator  # noqa: E402
from backend.api.middleware.metrics_auth import MetricsAuthMiddleware  # noqa: E402
from backend.api.middleware.rate_limit import GlobalRateLimitMiddleware, limiter  # noqa: E402
from backend.api.middleware.security_headers import add_security_headers_middleware  # noqa: E402
from backend.api.supertokens_config import (  # noqa: E402
    add_supertokens_middleware,
    init_supertokens,
)
from bo1.config import get_settings  # noqa: E402

# Track import time
_import_time = (time.perf_counter() - _module_load_start) * 1000
print(f"⏱️  Module imports: {_import_time:.1f}ms")

# Graceful shutdown state
_shutdown_event: asyncio.Event | None = None
_in_flight_requests = 0
_shutdown_logger = logging.getLogger(__name__)

# Graceful shutdown timeout (seconds)
SHUTDOWN_TIMEOUT = 30

# Startup timing tracker
_startup_times: dict[str, float] = {}
_startup_start: float = 0.0


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def is_shutting_down() -> bool:
    """Check if the application is shutting down."""
    return _shutdown_event is not None and _shutdown_event.is_set()


def _handle_shutdown_signal(signum: int, frame: Any) -> None:
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    _shutdown_logger.info(f"Received {sig_name}, initiating graceful shutdown...")
    shutdown_event = get_shutdown_event()
    shutdown_event.set()


def _track_startup_time(operation: str, start: float) -> None:
    """Track and log startup operation timing."""
    elapsed = (time.perf_counter() - start) * 1000  # ms
    _startup_times[operation] = elapsed
    _shutdown_logger.info(f"⏱️  {operation}: {elapsed:.1f}ms")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup and shutdown events with graceful shutdown support.
    """
    global _startup_start
    _startup_start = time.perf_counter()

    # Startup
    print("Starting Board of One API...")

    # Initialize shutdown event
    op_start = time.perf_counter()
    get_shutdown_event()
    _track_startup_time("shutdown_event_init", op_start)

    # Register signal handlers for graceful shutdown
    op_start = time.perf_counter()
    try:
        signal.signal(signal.SIGTERM, _handle_shutdown_signal)
        signal.signal(signal.SIGINT, _handle_shutdown_signal)
        print("✓ Signal handlers registered for graceful shutdown")
    except (ValueError, OSError) as e:
        print(f"⚠️  Could not register signal handlers: {e}")
    _track_startup_time("signal_handlers", op_start)

    # SECURITY: Validate authentication is enabled in production
    op_start = time.perf_counter()
    from backend.api.middleware.auth import require_production_auth

    try:
        require_production_auth()
        print("✓ Production authentication check passed")
    except RuntimeError as e:
        print(f"✗ SECURITY ERROR: {e}")
        raise
    _track_startup_time("auth_validation", op_start)

    # Start persistence retry worker
    op_start = time.perf_counter()
    from backend.api.persistence_worker import start_persistence_worker

    try:
        await start_persistence_worker()
        print("✓ Persistence retry worker started")
    except Exception as e:
        print(f"⚠️  Failed to start persistence worker: {e}")
    _track_startup_time("persistence_worker", op_start)

    # Start batch event persistence task
    op_start = time.perf_counter()
    from backend.api.event_publisher import start_batch_flush_task

    start_batch_flush_task()
    print("✓ Batch event persistence task started")
    _track_startup_time("batch_flush_task", op_start)

    # Start session share cleanup job (daily)
    op_start = time.perf_counter()
    from backend.jobs.session_share_cleanup import cleanup_expired_shares

    try:
        loop = asyncio.get_event_loop()

        async def run_cleanup() -> None:
            """Run cleanup task periodically (daily)."""
            while not is_shutting_down():
                try:
                    result = cleanup_expired_shares()
                    _shutdown_logger.info(f"Session share cleanup: {result}")
                except Exception as e:
                    _shutdown_logger.error(f"Session share cleanup failed: {e}")
                try:
                    await asyncio.wait_for(
                        asyncio.shield(get_shutdown_event().wait()),
                        timeout=86400,  # 24 hours
                    )
                except TimeoutError:
                    pass
                except Exception as e:
                    _shutdown_logger.debug(f"Cleanup wait interrupted: {e}")

        _ = loop.create_task(run_cleanup())
        print("✓ Session share cleanup job started")
    except Exception as e:
        _shutdown_logger.warning(f"Failed to start cleanup job: {e}")
    _track_startup_time("cleanup_job", op_start)

    # Log total startup time
    total_startup = (time.perf_counter() - _startup_start) * 1000
    _startup_times["total_lifespan"] = total_startup
    total_startup_time = _startup_times.get("module_init_total", 0) + total_startup
    print(
        f"🚀 API startup complete in {total_startup_time:.1f}ms (module={_startup_times.get('module_init_total', 0):.0f}ms + lifespan={total_startup:.0f}ms)"
    )
    print(
        f"   Breakdown: {', '.join(f'{k}={v:.0f}ms' for k, v in _startup_times.items() if k not in ('total_lifespan', 'module_init_total'))}"
    )

    # Record to Prometheus
    from backend.api.metrics import prom_metrics

    prom_metrics.record_startup_time("lifespan", total_startup)
    prom_metrics.record_startup_time("total", total_startup_time)

    yield

    # Shutdown
    print("Shutting down Board of One API...")

    # Signal shutdown to health checks
    shutdown_event = get_shutdown_event()
    shutdown_event.set()
    print("✓ Shutdown event signaled (health checks now return 503)")

    # Wait for in-flight requests with timeout
    global _in_flight_requests
    if _in_flight_requests > 0:
        print(
            f"⏳ Waiting for {_in_flight_requests} in-flight requests (max {SHUTDOWN_TIMEOUT}s)..."
        )
        start_time = asyncio.get_event_loop().time()
        while _in_flight_requests > 0:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= SHUTDOWN_TIMEOUT:
                print(
                    f"⚠️  Shutdown timeout reached with {_in_flight_requests} requests still in-flight"
                )
                break
            await asyncio.sleep(0.1)
        else:
            print("✓ All in-flight requests completed")

    # Stop batch event persistence task and flush remaining events
    from backend.api.event_publisher import _flush_batch, stop_batch_flush_task

    try:
        stop_batch_flush_task()
        await _flush_batch()  # Final flush on shutdown
        print("✓ Batch event persistence task stopped")
    except Exception as e:
        print(f"⚠️  Failed to stop batch persistence: {e}")

    # Stop persistence retry worker
    from backend.api.persistence_worker import stop_persistence_worker

    try:
        await stop_persistence_worker()
        print("✓ Persistence retry worker stopped")
    except Exception as e:
        print(f"⚠️  Failed to stop persistence worker: {e}")

    # Close database connection pool
    try:
        from bo1.state.database import close_pool

        close_pool()
        print("✓ Database connection pool closed")
    except Exception as e:
        print(f"⚠️  Failed to close database pool: {e}")


# Create FastAPI application
app = FastAPI(
    title="Board of One API",
    description="""
    **Board of One** is a multi-agent deliberation system that uses AI personas
    to provide strategic decision-making insights through structured debate and synthesis.

    ## Features

    - **Multi-Agent Deliberation**: 3-5 expert personas debate your decision
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
            "name": "authentication",
            "description": "OAuth authentication (Google OAuth for closed beta)",
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
        {
            "name": "waitlist",
            "description": "Waitlist management for closed beta access",
        },
        {
            "name": "onboarding",
            "description": "User onboarding and driver.js tour tracking",
        },
    ],
)

# Initialize SuperTokens (MUST be before CORS middleware and routes)
_module_init_start = time.perf_counter()
init_supertokens()
add_supertokens_middleware(app)
_startup_times["supertokens_init"] = (time.perf_counter() - _module_init_start) * 1000
print(f"⏱️  SuperTokens init: {_startup_times['supertokens_init']:.1f}ms")

# Add SlowAPI state to app (required for rate limiting)
app.state.limiter = limiter

# Track middleware setup time
_middleware_start = time.perf_counter()

# Configure CORS with explicit allow lists (SECURITY: No wildcards in production)
# Use centralized settings for CORS origins
settings_for_cors = get_settings()
CORS_ORIGINS = settings_for_cors.cors_origins_list

# SECURITY: Validate no wildcards in production
if not settings_for_cors.debug:
    if "*" in settings_for_cors.cors_origins:
        raise RuntimeError(
            "SECURITY: Wildcard CORS origins not allowed in production. "
            "Set specific origins in CORS_ORIGINS environment variable."
        )

# Explicit allowed methods (no wildcards)
ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
# Explicit allowed headers (common auth headers + SuperTokens headers)
ALLOWED_HEADERS = [
    "Authorization",
    "Content-Type",
    "Accept",
    "X-Admin-Key",
    "X-Request-ID",
    "X-CSRF-Token",  # CSRF protection header
    "Origin",
    "Referer",
    # SuperTokens headers
    "rid",  # Recipe ID
    "fdi-version",  # Frontend driver interface version
    "anti-csrf",  # CSRF token
    "st-auth-mode",  # SuperTokens auth mode
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=["front-token"],  # SuperTokens uses front-token header for JWT payload
)

# Add GZip compression middleware for responses (applies to responses >= 1KB)
# Reduces bandwidth usage by ~60-80% for JSON/text responses
# IMPORTANT: Add AFTER CORS middleware (middleware is executed in reverse order)
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,  # Only compress responses >= 1KB (avoid overhead for tiny responses)
)

# Add metrics auth middleware (protects /metrics if METRICS_AUTH_TOKEN is set)
# IMPORTANT: Add AFTER GZip (middleware executes in reverse order)
# This runs early to protect /metrics before rate limiting
app.add_middleware(MetricsAuthMiddleware)

# Add global IP-based rate limiting middleware
# IMPORTANT: Add AFTER MetricsAuth (middleware executes in reverse order)
# This provides flood protection before any auth or endpoint-specific limits
# Ordering: CORS > GZip > MetricsAuth > GlobalRateLimit > SecurityHeaders > ... > EndpointRateLimit
app.add_middleware(GlobalRateLimitMiddleware)

# Add security headers middleware (X-Frame-Options, CSP, HSTS, etc.)
# IMPORTANT: Add AFTER GZip (middleware executes in reverse order)
# This ensures security headers are added to all responses including compressed ones
add_security_headers_middleware(app)

# Add correlation ID middleware for request tracing
# Generates/extracts X-Request-ID header and stores in request.state
app.add_middleware(CorrelationIdMiddleware)

# Add API version header to all responses
app.add_middleware(ApiVersionMiddleware)

# Add degraded mode middleware (returns 503 for LLM operations when providers unavailable)
# IMPORTANT: Add AFTER ApiVersionMiddleware (executes before it in request flow)
app.add_middleware(DegradedModeMiddleware)

# Add audit logging middleware for request tracking
# IMPORTANT: Add AFTER DegradedModeMiddleware (needs auth state from downstream)
# Logs all API requests to database for security/compliance auditing
app.add_middleware(AuditLoggingMiddleware)

# Add CSRF protection middleware (double-submit cookie pattern)
# IMPORTANT: Add AFTER AuditLoggingMiddleware (middleware executes in reverse order)
# Validates X-CSRF-Token header matches csrf_token cookie for mutating requests
app.add_middleware(CSRFMiddleware)

# Add impersonation middleware (admin "view as user" feature)
# IMPORTANT: Add AFTER CSRFMiddleware (middleware executes in reverse order)
# Checks for active impersonation session and swaps user context
from backend.api.middleware.impersonation import ImpersonationMiddleware  # noqa: E402

app.add_middleware(ImpersonationMiddleware)

_startup_times["middleware_setup"] = (time.perf_counter() - _middleware_start) * 1000
print(f"⏱️  Middleware setup: {_startup_times['middleware_setup']:.1f}ms")


# In-flight request tracking middleware
@app.middleware("http")
async def track_in_flight_requests(request: Request, call_next: Any) -> Any:
    """Track in-flight requests for graceful shutdown."""
    global _in_flight_requests

    # Skip tracking for health endpoints (they should always respond quickly)
    if request.url.path in ("/api/health", "/api/ready"):
        return await call_next(request)

    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1


# Include routers
# IMPORTANT: Register streaming router BEFORE sessions router to avoid
# /{session_id} catch-all matching /{session_id}/stream
_routers_start = time.perf_counter()
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(
    auth.router, prefix="/api/v1/auth", tags=["authentication"]
)  # Custom auth endpoints (e.g., /me, /google/sheets/*)
app.include_router(streaming.router, prefix="/api", tags=["streaming"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(share.router, prefix="/api", tags=["share"])
app.include_router(actions.router, prefix="/api", tags=["actions"])
app.include_router(tags.router, prefix="/api", tags=["tags"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(context.router, prefix="/api", tags=["context"])
app.include_router(datasets.router, prefix="/api", tags=["datasets"])
app.include_router(mentor.router, prefix="/api", tags=["mentor"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(business_metrics.router, prefix="/api", tags=["business-metrics"])
app.include_router(billing.router, prefix="/api", tags=["billing"])
app.include_router(industry_insights.router, prefix="/api", tags=["industry-insights"])
app.include_router(competitors.router, prefix="/api", tags=["competitors"])
app.include_router(onboarding.router, prefix="/api", tags=["onboarding"])
app.include_router(control.router, prefix="/api", tags=["deliberation-control"])
app.include_router(waitlist.router, prefix="/api", tags=["waitlist"])
app.include_router(client_errors.router, prefix="/api", tags=["client-errors"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(email.router, prefix="/api", tags=["email"])
app.include_router(feedback.router, prefix="/api", tags=["feedback"])
app.include_router(user.router, prefix="/api", tags=["user"])
app.include_router(status.router, prefix="/api", tags=["status"])
app.include_router(workspaces.router, prefix="/api", tags=["workspaces"])
app.include_router(workspaces.invitations_user_router, prefix="/api", tags=["invitations"])
app.include_router(workspaces.billing_router, prefix="/api", tags=["workspace-billing"])
app.include_router(csp_reports.router, tags=["security"])
app.include_router(client_metrics.router, tags=["metrics"])
app.include_router(calendar_router, prefix="/api", tags=["integrations"])
app.include_router(page_analytics.router, prefix="/api", tags=["analytics"])
app.include_router(page_analytics.admin_router, prefix="/api", tags=["admin"])

_startup_times["router_registration"] = (time.perf_counter() - _routers_start) * 1000
print(f"⏱️  Router registration: {_startup_times['router_registration']:.1f}ms")

# Initialize Prometheus metrics instrumentation
# Exposes /metrics endpoint for Prometheus scraping
# SECURITY: /metrics is not rate limited but should be internal-only (via network rules)
# Uses custom instrumentator with path normalization and business metrics
_prom_start = time.perf_counter()
create_instrumentator().instrument(app).expose(app, include_in_schema=False)
_startup_times["prometheus_init"] = (time.perf_counter() - _prom_start) * 1000
print(f"⏱️  Prometheus init: {_startup_times['prometheus_init']:.1f}ms")

# Log total module-level init time
_module_init_total = (time.perf_counter() - _module_load_start) * 1000
_startup_times["module_init_total"] = _module_init_total
print(f"🔧 Module init complete in {_module_init_total:.1f}ms (before lifespan)")

# Record module init time to Prometheus
from backend.api.metrics import prom_metrics as _prom_metrics  # noqa: E402

_prom_metrics.record_startup_time("module_init", _module_init_total)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    SECURITY: Sanitizes error messages in production to prevent information leakage.
    Development mode returns full error details for debugging.

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSON error response (sanitized in production)
    """
    import logging

    logger = logging.getLogger(__name__)

    # Get settings to check debug mode
    from bo1.config import get_settings

    settings = get_settings()

    # Log full error server-side for all environments
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={
            "request_path": request.url.path,
            "request_method": request.method,
        },
    )

    if settings.debug:
        # Development: Return full error details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__,
                "debug_mode": True,
            },
        )
    else:
        # Production: Return sanitized generic error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later. "
                "If this issue persists, contact support.",
                "type": "InternalError",
            },
        )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded exceptions from SlowAPI.

    Returns 429 Too Many Requests with Retry-After header.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "error_code": "rate_limited",
        },
        headers={"Retry-After": "60"},  # Suggest retry after 60 seconds
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException with consistent JSON shape.

    Ensures all HTTP errors have both 'detail' and 'error_code' fields.
    If error_code is not provided, defaults to 'unknown_error'.

    Args:
        request: FastAPI request object
        exc: HTTPException that was raised

    Returns:
        JSON error response with consistent shape
    """
    # Check if detail is already structured (dict with error_code)
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers=exc.headers,
        )

    # If detail is a dict without error_code (e.g., health check responses),
    # add error_code to the dict
    if isinstance(exc.detail, dict):
        content = exc.detail.copy()
        content["error_code"] = "unknown_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers,
        )

    # If detail is a string, wrap it in structured format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": "unknown_error",
        },
        headers=exc.headers,
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


@app.get("/api/version", tags=["health"])
async def api_version() -> dict[str, str]:
    """Get API version information.

    Returns version metadata for client compatibility checks.
    This endpoint is version-agnostic (not under /v1/).
    """
    return {
        "api_version": API_VERSION,
        "app_version": app.version,
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
        "version": app.version,
        "api_version": API_VERSION,
        "admin_user": user.get("email"),
        "admin_id": user.get("user_id"),
        "documentation": {
            "swagger": "/api/v1/docs",
            "redoc": "/api/v1/redoc",
            "openapi_spec": "/api/v1/openapi.json",
        },
        "services": {
            "api": "Running",
            "authentication": "Supabase JWT",
            "mode": "Closed Beta",
        },
    }


@app.get("/api/v1/docs", response_class=HTMLResponse, include_in_schema=False)
async def api_docs(user: dict[str, Any] = Depends(require_admin)) -> HTMLResponse:
    """Admin-only Swagger UI documentation.

    Args:
        user: Admin user data

    Returns:
        Swagger UI HTML
    """
    return get_swagger_ui_html(
        openapi_url="/api/v1/openapi.json",
        title=f"{app.title} - API Documentation (v{API_VERSION})",
        swagger_favicon_url="/favicon.ico",
    )


@app.get("/api/v1/redoc", response_class=HTMLResponse, include_in_schema=False)
async def api_redoc(user: dict[str, Any] = Depends(require_admin)) -> HTMLResponse:
    """Admin-only ReDoc documentation.

    Args:
        user: Admin user data

    Returns:
        ReDoc HTML
    """
    return get_redoc_html(
        openapi_url="/api/v1/openapi.json",
        title=f"{app.title} - API Documentation (v{API_VERSION})",
        redoc_favicon_url="/favicon.ico",
    )


@app.get("/api/v1/openapi.json", include_in_schema=False)
async def api_openapi(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Admin-only OpenAPI specification with version metadata.

    Args:
        user: Admin user data

    Returns:
        OpenAPI JSON spec with version info
    """
    spec = app.openapi()
    # Ensure version info is in spec
    if "info" in spec:
        spec["info"]["version"] = app.version
        spec["info"]["x-api-version"] = API_VERSION
    return spec


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),  # noqa: S104  # Binding to all interfaces is intentional for dev
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "true").lower() == "true",
    )
