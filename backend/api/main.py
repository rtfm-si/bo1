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
from bo1.logging.errors import ErrorCode, log_error  # noqa: E402

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
    blog,
    business_metrics,
    client_errors,
    client_metrics,
    competitors,
    context,
    control,
    csp_reports,
    datasets,
    e2e_auth,
    email,
    feedback,
    health,
    industry_insights,
    mentor,
    onboarding,
    page_analytics,
    peer_benchmarks,
    projects,
    ratings,
    research_sharing,
    seo,
    sessions,
    share,
    status,
    streaming,
    tags,
    templates,
    terms,
    user,
    waitlist,
    workspaces,
)
from backend.api.integrations import calendar_router  # noqa: E402
from backend.api.middleware.admin import require_admin_any  # noqa: E402
from backend.api.middleware.api_version import API_VERSION, ApiVersionMiddleware  # noqa: E402
from backend.api.middleware.audit_logging import AuditLoggingMiddleware  # noqa: E402
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

    # Validate local dev auth configuration
    op_start = time.perf_counter()
    from backend.api.startup_validation import validate_auth_config

    auth_warnings = validate_auth_config()
    if auth_warnings:
        for warning in auth_warnings:
            print(f"⚠️  {warning}")
    else:
        print("✓ Auth configuration validated")
    _track_startup_time("auth_config_validation", op_start)

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

    # Start LLM health probe (background provider probing)
    op_start = time.perf_counter()
    from backend.api.llm_health_probe import get_llm_health_probe

    try:
        llm_probe = get_llm_health_probe()
        await llm_probe.start()
        app.state.llm_health_probe = llm_probe
        print("✓ LLM health probe started")
    except Exception as e:
        print(f"⚠️  Failed to start LLM health probe: {e}")
    _track_startup_time("llm_health_probe", op_start)

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
                    log_error(
                        _shutdown_logger,
                        ErrorCode.SERVICE_EXECUTION_ERROR,
                        f"Session share cleanup failed: {e}",
                        exc_info=True,
                    )
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

    # Stop LLM health probe
    try:
        if hasattr(app.state, "llm_health_probe"):
            await app.state.llm_health_probe.stop()
            print("✓ LLM health probe stopped")
    except Exception as e:
        print(f"⚠️  Failed to stop LLM health probe: {e}")

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

    This API uses cookie-based session authentication via SuperTokens.

    - **User Endpoints**: Require valid `sAccessToken` session cookie
    - **Admin Endpoints**: Require session cookie with admin privileges (is_admin=true)

    Authentication flow:
    1. User authenticates via OAuth (Google, LinkedIn, etc.) at `/auth/*` endpoints
    2. SuperTokens sets httpOnly `sAccessToken` cookie on successful auth
    3. All subsequent requests include cookie automatically
    4. Session is validated on each request

    ## Rate Limits

    - Global: 500 requests/minute per IP
    - Control endpoints: 30 requests/minute per user
    - SSE: 5 concurrent connections per user

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
app.include_router(ratings.router, prefix="/api", tags=["ratings"])
app.include_router(ratings.admin_router, prefix="/api", tags=["admin"])
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
app.include_router(blog.router, prefix="/api", tags=["blog"])
app.include_router(seo.router, prefix="/api", tags=["seo"])
app.include_router(peer_benchmarks.router, prefix="/api", tags=["peer-benchmarks"])
app.include_router(research_sharing.router, prefix="/api", tags=["research-sharing"])
app.include_router(templates.router, prefix="/api", tags=["templates"])
app.include_router(terms.terms_router, prefix="/api", tags=["terms"])
app.include_router(terms.user_terms_router, prefix="/api", tags=["user"])
app.include_router(e2e_auth.router, prefix="/api", tags=["e2e"])

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


def _log_api_error_to_audit(
    request: Request,
    status_code: int,
    error_message: str,
    user_id: str | None = None,
) -> None:
    """Log API error to audit_log for ops tracking.

    Non-blocking - failures are logged but don't affect request.
    Only logs errors (4xx/5xx) to avoid noise.
    """
    import json
    import logging

    from slowapi.util import get_remote_address

    from backend.api.utils.db_helpers import execute_query

    # Only log errors worth tracking
    if status_code < 400:
        return

    # Skip logging rate limits for non-interesting endpoints
    if status_code == 429 and "/health" in request.url.path:
        return

    try:
        ip = get_remote_address(request)
        details = {
            "status_code": status_code,
            "endpoint": request.url.path,
            "method": request.method,
            "error": error_message[:500] if error_message else "",
        }

        execute_query(
            """
            INSERT INTO audit_log (user_id, action, resource_type, resource_id, details, ip_address)
            VALUES (%s, 'api_error', 'api', %s, %s, %s)
            """,
            (user_id, request.url.path, json.dumps(details), ip),
            fetch="none",
        )
    except Exception as e:
        logging.getLogger(__name__).debug(f"Failed to log API error to audit: {e}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors.

    SECURITY: Sanitizes error messages in production to prevent information leakage.
    Development mode returns full error details for debugging.

    Special handling:
    - SuperTokens connection errors on auth paths return 503 (graceful degradation)

    Args:
        request: FastAPI request object
        exc: Exception that was raised

    Returns:
        JSON error response (sanitized in production)
    """
    import logging

    from backend.api.middleware.metrics import record_api_endpoint_error
    from backend.api.middleware.supertokens_error import handle_supertokens_error

    logger = logging.getLogger(__name__)

    # Check if this is a SuperTokens connection error on an auth path
    # Returns 503 for graceful degradation when SuperTokens Core is unavailable
    supertokens_response = handle_supertokens_error(request, exc)
    if supertokens_response is not None:
        record_api_endpoint_error(request.url.path, 503)
        return supertokens_response

    # Get settings to check debug mode
    from bo1.config import get_settings

    settings = get_settings()

    # Log full error server-side for all environments
    log_error(
        logger,
        ErrorCode.SERVICE_EXECUTION_ERROR,
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        exc_info=True,
        request_path=request.url.path,
        request_method=request.method,
    )

    # Record error metric
    record_api_endpoint_error(request.url.path, 500)

    # Log to audit for ops tracking
    _log_api_error_to_audit(request, 500, str(exc))

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
    Calculates Retry-After from the rate limit window when available.
    """
    from backend.api.middleware.metrics import record_api_endpoint_error

    # Record error metric
    record_api_endpoint_error(request.url.path, 429)

    # Log to audit for ops tracking (rate limits are important to track)
    _log_api_error_to_audit(request, 429, "Rate limit exceeded")

    # Try to extract retry time from slowapi exception
    # Format: "N per M second/minute/hour" - extract window in seconds
    retry_after = 60  # default fallback
    try:
        if hasattr(exc, "detail") and exc.detail:
            detail_str = str(exc.detail)
            # Parse rate limit format: "5 per 1 minute" -> extract window
            if "per" in detail_str.lower():
                parts = detail_str.lower().split("per")
                if len(parts) == 2:
                    time_part = parts[1].strip()
                    if "second" in time_part:
                        retry_after = int(time_part.split()[0])
                    elif "minute" in time_part:
                        retry_after = int(time_part.split()[0]) * 60
                    elif "hour" in time_part:
                        retry_after = int(time_part.split()[0]) * 3600
    except (ValueError, IndexError, AttributeError):
        pass  # Use default 60 seconds

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "error_code": "rate_limited",
            "retry_after": retry_after,  # Also include in body for client convenience
        },
        headers={"Retry-After": str(retry_after)},
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
    from backend.api.middleware.metrics import record_api_endpoint_error

    # Record error metric for 4xx and 5xx responses
    if exc.status_code >= 400:
        record_api_endpoint_error(request.url.path, exc.status_code)

    # Log to audit for ops tracking (only 401s and 5xx to reduce noise)
    if exc.status_code == 401 or exc.status_code >= 500:
        error_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        _log_api_error_to_audit(request, exc.status_code, error_msg)

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
async def admin_info(user: dict[str, Any] = Depends(require_admin_any)) -> dict[str, Any]:
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
async def api_docs(user: dict[str, Any] = Depends(require_admin_any)) -> HTMLResponse:
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
async def api_redoc(user: dict[str, Any] = Depends(require_admin_any)) -> HTMLResponse:
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


def custom_openapi() -> dict[str, Any]:
    """Generate custom OpenAPI schema with security schemes.

    Adds sessionAuth (cookie-based) and adminAuth security schemes to the
    OpenAPI specification. This documents the SuperTokens session cookie
    authentication used by the API.

    Returns:
        OpenAPI schema dict with security schemes
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # Add security schemes to components
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "sessionAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "sAccessToken",
            "description": (
                "SuperTokens session cookie. Set automatically after OAuth login. "
                "Contains encrypted session token validated on each request."
            ),
        },
        "csrfToken": {
            "type": "apiKey",
            "in": "header",
            "name": "X-CSRF-Token",
            "description": (
                "CSRF protection token. Must match the value in the csrf_token cookie. "
                "Required for all mutating requests (POST, PUT, DELETE, PATCH)."
            ),
        },
    }

    # Add global security requirement (most endpoints require auth)
    openapi_schema["security"] = [{"sessionAuth": [], "csrfToken": []}]

    # Add version metadata
    openapi_schema["info"]["x-api-version"] = API_VERSION

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Override FastAPI's default openapi() method
app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/api/v1/openapi.json", include_in_schema=False)
async def api_openapi(user: dict[str, Any] = Depends(require_admin_any)) -> dict[str, Any]:
    """Admin-only OpenAPI specification with version metadata.

    Args:
        user: Admin user data

    Returns:
        OpenAPI JSON spec with version info
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
