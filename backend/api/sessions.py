"""Session management API endpoints.

Provides:
- POST /api/v1/sessions - Create new deliberation session
- GET /api/v1/sessions - List user's sessions
- GET /api/v1/sessions/{session_id} - Get session details
"""

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.api.dependencies import (
    VerifiedSession,
    get_redis_manager,
    get_session_manager,
    get_session_metadata_cache,
)
from backend.api.metrics import track_api_call
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import SESSION_RATE_LIMIT, limiter, user_rate_limiter
from backend.api.middleware.tier_limits import (
    MeetingLimitResult,
    record_meeting_usage,
    require_meeting_limit,
)
from backend.api.middleware.workspace_auth import require_workspace_access
from backend.api.models import (
    CreateSessionRequest,
    ErrorResponse,
    MessageResponse,
    PhaseCosts,
    ProviderCosts,
    SessionActionsResponse,
    SessionCostBreakdown,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    SubProblemCost,
    TaskStatusUpdate,
    TaskWithStatus,
    TerminationRequest,
    TerminationResponse,
)
from backend.api.utils.auth_helpers import extract_user_id, is_admin
from backend.api.utils.degradation import check_pool_health
from backend.api.utils.errors import handle_api_errors, raise_api_error
from backend.api.utils.honeypot import validate_honeypot_fields
from backend.api.utils.text import truncate_text
from backend.api.utils.validation import validate_session_id
from backend.services.insight_staleness import get_stale_insights
from backend.services.session_export import SessionExporter
from backend.services.session_share import SessionShareService
from bo1.agents.task_extractor import sync_extract_tasks_from_synthesis
from bo1.graph.execution import SessionManager
from bo1.llm.cost_tracker import CostTracker
from bo1.logging.errors import ErrorCode, log_error
from bo1.security import check_for_injection, sanitize_for_prompt
from bo1.security.prompt_validation import PromptInjectionError, validate_problem_statement
from bo1.state.redis_manager import RedisManager
from bo1.state.repositories.dataset_repository import DatasetRepository
from bo1.state.repositories.session_repository import session_repository
from bo1.state.repositories.user_repository import user_repository
from bo1.utils.logging import get_logger

dataset_repository = DatasetRepository()

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post(
    "",
    response_model=SessionResponse,
    status_code=201,
    summary="Create new deliberation session",
    description="Create a new deliberation session with the given problem statement and context.",
    responses={
        201: {"description": "Session created successfully"},
        400: {
            "description": "Invalid request",
            "model": ErrorResponse,
        },
        422: {
            "description": "Validation error (injection pattern detected)",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "xss_rejected": {
                            "summary": "XSS attempt rejected",
                            "value": {"detail": "Problem statement cannot contain script tags"},
                        },
                        "sql_injection_rejected": {
                            "summary": "SQL injection rejected",
                            "value": {"detail": "Problem statement contains invalid SQL patterns"},
                        },
                    }
                }
            },
        },
        429: {
            "description": "Rate limit exceeded",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
        503: {
            "description": "Service unavailable - database pool exhausted",
            "model": ErrorResponse,
        },
    },
)
@limiter.limit(SESSION_RATE_LIMIT)
@handle_api_errors("create session")
async def create_session(
    request: Request,
    session_request: CreateSessionRequest,
    user: dict[str, Any] = Depends(get_current_user),
    tier_usage: MeetingLimitResult = Depends(require_meeting_limit),
    _pool_check: None = Depends(check_pool_health),
) -> SessionResponse:
    """Create a new deliberation session.

    This endpoint creates a new session with a unique identifier and saves
    the initial state to Redis. The session is ready to be started via the
    /start endpoint.

    If tier limit is exceeded but user has promo credits, the session
    will be created using a promo credit (marked with used_promo_credit=True).

    Args:
        request: FastAPI request object for rate limiting
        session_request: Session creation request with problem statement
        user: Authenticated user data
        tier_usage: Meeting limit result with promo credit fallback info

    Returns:
        SessionResponse with session details

    Raises:
        HTTPException: If session creation fails
    """
    with track_api_call("sessions.create", "POST"):
        # Honeypot validation (cheap first-pass bot filter)
        validate_honeypot_fields(session_request, "sessions.create")

        # Create Redis manager
        redis_manager = get_redis_manager()

        if not redis_manager.is_available:
            raise_api_error("redis_unavailable")

        # Extract user ID from authenticated user
        user_id = extract_user_id(user)

        # User-based rate limiting (prevents free tier abuse)
        # This runs AFTER auth, checking per-user limits in Redis
        subscription_tier = user.get("subscription_tier", "free")
        await user_rate_limiter.check_limit(
            user_id=user_id,
            action="session_create",
            limit=5,  # 5 meetings/minute for free tier
            window_seconds=60,
            tier=subscription_tier,
        )

        # Internal budget check (admin-configured cost limits)
        # Blocks session creation if user exceeds hard limit
        try:
            from backend.services import user_cost_tracking as uct

            budget_result = uct.check_budget_status(user_id)
            if budget_result.should_block:
                raise HTTPException(
                    status_code=402,
                    detail="Usage limit reached. Please contact support.",
                )
        except HTTPException:
            raise
        except Exception as e:
            # Don't block on budget check failures - log and continue
            logger.debug("Budget check failed (non-blocking): %s", e)

        # LAYER 1: Pattern-based prompt injection detection (fast, cheap)
        # Checks for obvious injection patterns before expensive LLM call
        # Blocks if PROMPT_INJECTION_BLOCK_SUSPICIOUS=True (default)
        try:
            validate_problem_statement(session_request.problem_statement)
        except PromptInjectionError as e:
            # Return structured 400 error matching LLM-based detection format
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "prompt_injection_detected",
                    "message": str(e),
                    "source": "problem_statement",
                    "detection_layer": "pattern",
                },
            ) from e

        # LAYER 2: LLM-based prompt injection audit (sophisticated, catches subtle attacks)
        # Runs after pattern-based check passes
        await check_for_injection(
            content=session_request.problem_statement,
            source="problem_statement",
            raise_on_unsafe=True,
        )

        # Sanitize problem statement for safe prompt interpolation
        # Escapes XML-like tags to prevent prompt structure manipulation
        sanitized_problem = sanitize_for_prompt(session_request.problem_statement)

        # Validate dataset_id ownership if provided
        validated_dataset_id: str | None = None
        if session_request.dataset_id:
            dataset = dataset_repository.get_by_id(session_request.dataset_id, user_id)
            if not dataset:
                raise HTTPException(
                    status_code=404,
                    detail="Dataset not found or not owned by user",
                )
            validated_dataset_id = session_request.dataset_id

        # Validate workspace_id membership if provided
        validated_workspace_id: str | None = None
        if session_request.workspace_id:
            import uuid as uuid_module

            try:
                ws_uuid = uuid_module.UUID(session_request.workspace_id)
                require_workspace_access(ws_uuid, user_id)
                validated_workspace_id = session_request.workspace_id
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid workspace_id format",
                ) from e

        # Validate context_ids ownership if provided
        validated_context_ids: dict[str, list[str]] | None = None
        if session_request.context_ids:
            validated_context_ids = {"meetings": [], "actions": [], "datasets": []}

            # Validate meeting_ids - must be owned by user
            meeting_ids = session_request.context_ids.get("meetings", [])
            if meeting_ids:
                # Limit to 5 meetings max per plan constraints
                if len(meeting_ids) > 5:
                    raise HTTPException(
                        status_code=400,
                        detail="Maximum 5 past meetings can be attached",
                    )
                for mid in meeting_ids:
                    session = session_repository.get(mid)
                    if not session or session.get("user_id") != user_id:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Meeting {mid} not found or not owned by user",
                        )
                    validated_context_ids["meetings"].append(mid)

            # Validate action_ids - must be owned by user
            action_ids = session_request.context_ids.get("actions", [])
            if action_ids:
                # Limit to 10 actions max per plan constraints
                if len(action_ids) > 10:
                    raise HTTPException(
                        status_code=400,
                        detail="Maximum 10 actions can be attached",
                    )
                from bo1.state.repositories.action_repository import ActionRepository

                action_repo = ActionRepository()
                for aid in action_ids:
                    action = action_repo.get(aid)
                    if not action or action.get("user_id") != user_id:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Action {aid} not found or not owned by user",
                        )
                    validated_context_ids["actions"].append(aid)

            # Validate dataset_ids - must be owned by user
            ds_ids = session_request.context_ids.get("datasets", [])
            if ds_ids:
                # Limit to 3 datasets max per plan constraints
                if len(ds_ids) > 3:
                    raise HTTPException(
                        status_code=400,
                        detail="Maximum 3 datasets can be attached",
                    )
                for did in ds_ids:
                    ds = dataset_repository.get_by_id(did, user_id)
                    if not ds:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Dataset {did} not found or not owned by user",
                        )
                    validated_context_ids["datasets"].append(did)

            # If all lists are empty, set to None
            if not any(validated_context_ids.values()):
                validated_context_ids = None

        # Generate session ID
        session_id = redis_manager.create_session()

        # Fetch user's business context and merge with request context
        # User context provides business background, request context can override/add specifics
        merged_context: dict[str, Any] = {}
        try:
            user_context = user_repository.get_context(user_id)
            if user_context:
                # Include relevant business context fields
                context_fields = [
                    "company_name",
                    "business_model",
                    "target_market",
                    "product_description",
                    "business_stage",
                    "primary_objective",
                    "industry",
                    "competitors",
                    "revenue",
                    "customers",
                    "growth_rate",
                    "website",
                    "pricing_model",
                    "brand_positioning",
                    "ideal_customer_profile",
                    "team_size",
                    "budget_constraints",
                    "time_constraints",
                    "regulatory_constraints",
                ]
                for field in context_fields:
                    if field in user_context and user_context[field]:
                        merged_context[field] = user_context[field]
                logger.debug(
                    f"Injected {len(merged_context)} business context fields for user {user_id}"
                )
        except Exception as e:
            logger.warning(f"Failed to load user context for session creation: {e}")

        # Merge request context (overrides user context if same keys)
        if session_request.problem_context:
            merged_context.update(session_request.problem_context)

        # Create initial metadata
        now = datetime.now(UTC)
        metadata = {
            "status": "created",
            "phase": None,
            "user_id": user_id,  # SECURITY: Track session ownership
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "problem_statement": sanitized_problem,
            "problem_context": merged_context,
            "context_ids": validated_context_ids,  # User-selected context references
        }

        # Save metadata to Redis (for live state and fast lookup)
        if not redis_manager.save_metadata(session_id, metadata):
            raise RuntimeError("Failed to save session metadata")

        # Add session to user's session index for fast lookup
        redis_manager.add_session_to_user_index(user_id, session_id)

        # Save session to PostgreSQL for permanent storage
        # CRITICAL: PostgreSQL is the primary storage - failure should abort the request
        try:
            # Safety net: Ensure user exists in PostgreSQL (FK constraint requires this)
            # Primary sync happens in SuperTokens sign_in_up() override (supertokens_config.py)
            # This is a fallback for edge cases where OAuth sync failed or for direct API calls
            user_email = user.get("email") if user else None
            user_repository.ensure_exists(
                user_id=user_id,
                email=user_email,
                auth_provider="supertokens",  # Unknown at this point, use generic
                subscription_tier=user.get("subscription_tier", "free") if user else "free",
            )

            session_repository.create(
                session_id=session_id,
                user_id=user_id,
                problem_statement=sanitized_problem,
                problem_context=merged_context if merged_context else None,
                status="created",
                dataset_id=validated_dataset_id,
                workspace_id=validated_workspace_id,
                used_promo_credit=tier_usage.uses_promo_credit,
                context_ids=validated_context_ids,
                template_id=session_request.template_id,
            )
            logger.info(
                f"Created session: {session_id} for user: {user_id} (saved to both Redis and PostgreSQL)"
            )

            # Record Prometheus metric
            from backend.api.middleware.metrics import record_session_created

            record_session_created("created")
        except Exception as e:
            # PostgreSQL is primary storage - propagate error to client
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to save session to PostgreSQL: {e}",
                exc_info=True,
                session_id=session_id,
                user_id=user_id,
            )
            # Clean up Redis state since PostgreSQL failed
            try:
                redis_manager.delete_session(session_id)
                redis_manager.remove_session_from_user_index(user_id, session_id)
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up Redis after PostgreSQL failure: {cleanup_error}"
                )
            raise HTTPException(
                status_code=500,
                detail="Failed to create session. Please try again.",
            ) from e

        # Context Auto-Update: Extract business context updates from problem statement
        try:
            from backend.services.context_extractor import (
                ContextUpdateSource,
                extract_context_updates,
                filter_high_confidence_updates,
            )

            updates = await extract_context_updates(
                sanitized_problem, merged_context, ContextUpdateSource.PROBLEM_STATEMENT
            )

            if updates:
                high_conf, low_conf = filter_high_confidence_updates(updates)

                # Load user context for updating
                existing_context = user_repository.get_context(user_id) or {}

                # Auto-apply high confidence updates
                if high_conf:
                    metric_history = existing_context.get("context_metric_history", {})
                    for upd in high_conf:
                        existing_context[upd.field_name] = upd.new_value
                        logger.info(
                            f"Session {session_id}: Auto-applied context from problem: "
                            f"{upd.field_name}={upd.new_value} (conf={upd.confidence:.2f})"
                        )

                        # Track in metric history
                        if upd.field_name not in metric_history:
                            metric_history[upd.field_name] = []
                        metric_history[upd.field_name].insert(
                            0,
                            {
                                "value": upd.new_value,
                                "recorded_at": upd.extracted_at,
                                "source_type": upd.source_type.value,
                                "source_id": session_id,
                            },
                        )
                        metric_history[upd.field_name] = metric_history[upd.field_name][:10]

                    existing_context["context_metric_history"] = metric_history

                # Queue low confidence updates for review
                if low_conf:
                    import uuid

                    pending = existing_context.get("pending_updates", [])
                    for upd in low_conf:
                        if len(pending) >= 5:
                            break
                        pending.append(
                            {
                                "id": str(uuid.uuid4())[:8],
                                "field_name": upd.field_name,
                                "new_value": upd.new_value,
                                "current_value": existing_context.get(upd.field_name),
                                "confidence": upd.confidence,
                                "source_type": upd.source_type.value,
                                "source_text": upd.source_text,
                                "extracted_at": upd.extracted_at,
                                "session_id": session_id,
                            }
                        )
                    existing_context["pending_updates"] = pending

                # Save if any updates were made
                if high_conf or low_conf:
                    user_repository.save_context(user_id, existing_context)
                    logger.info(
                        f"Session {session_id}: Applied {len(high_conf)} auto-updates, "
                        f"queued {min(len(low_conf), 5)} for review"
                    )

        except Exception as e:
            # Non-blocking - don't fail session creation if extraction fails
            logger.debug(f"Context extraction from problem failed (non-blocking): {e}")

        # Check for stale insights (>30 days old)
        stale_insights_list: list[dict[str, Any]] | None = None
        try:
            staleness_result = get_stale_insights(user_id)
            if staleness_result.has_stale_insights:
                stale_insights_list = [
                    {
                        "question": si.question,
                        "days_stale": si.days_stale,
                    }
                    for si in staleness_result.stale_insights[:5]  # Limit to 5
                ]
                logger.info(
                    f"Session {session_id}: {len(staleness_result.stale_insights)} stale insights "
                    f"detected for user {user_id}"
                )
        except Exception as e:
            # Non-blocking - log and continue
            logger.debug(f"Staleness check failed (non-blocking): {e}")

        # Check for stale metrics (volatility-aware)
        stale_metrics_list: list[dict[str, Any]] | None = None
        try:
            from backend.services.insight_staleness import get_stale_metrics_for_session

            # Get action-affected fields from pending updates
            context_data = user_repository.get_context(user_id)
            action_affected_fields: list[str] = []
            if context_data:
                pending = context_data.get("pending_updates", [])
                for p in pending:
                    if p.get("refresh_reason") == "action_affected" and p.get("field_name"):
                        action_affected_fields.append(p["field_name"])

            metrics_result = get_stale_metrics_for_session(
                user_id=user_id,
                action_affected_fields=action_affected_fields if action_affected_fields else None,
            )
            if metrics_result.has_stale_metrics:
                stale_metrics_list = [
                    {
                        "field_name": m.field_name,
                        "current_value": m.current_value,
                        "days_since_update": m.days_since_update,
                        "reason": m.reason.value,
                        "volatility": m.volatility.value,
                    }
                    for m in metrics_result.stale_metrics
                ]
                logger.info(
                    f"Session {session_id}: {len(metrics_result.stale_metrics)} stale metrics "
                    f"detected for user {user_id}"
                )
        except Exception as e:
            # Non-blocking - log and continue
            logger.debug(f"Stale metrics check failed (non-blocking): {e}")

        # Record meeting usage for tier tracking (only if NOT using promo)
        if not tier_usage.uses_promo_credit:
            try:
                record_meeting_usage(user_id)
            except Exception as e:
                # Non-blocking - log and continue
                logger.debug(f"Usage tracking failed (non-blocking): {e}")

        # Return session response
        return SessionResponse(
            id=session_id,
            status="created",
            phase=None,
            created_at=now,
            updated_at=now,
            problem_statement=truncate_text(sanitized_problem),
            cost=None,
            stale_insights=stale_insights_list,
            stale_metrics=stale_metrics_list,
            promo_credits_remaining=(
                tier_usage.promo_credits_remaining if tier_usage.uses_promo_credit else None
            ),
        )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List user's sessions",
    description="List all deliberation sessions for the current user (paginated).",
    responses={
        200: {"description": "Sessions retrieved successfully"},
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def list_sessions(
    user: dict[str, Any] = Depends(get_current_user),
    status: str | None = Query(
        None, description="Filter by status (active, completed, failed, paused)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    workspace_id: str | None = Query(None, description="Filter by workspace UUID"),
) -> SessionListResponse:
    """List user's deliberation sessions.

    Returns a paginated list of sessions with metadata. Full session state
    can be retrieved via the GET /sessions/{session_id} endpoint.

    Args:
        user: Authenticated user data
        status: Optional status filter
        limit: Page size (1-100)
        offset: Page offset
        workspace_id: Optional workspace UUID filter

    Returns:
        SessionListResponse with list of sessions

    Raises:
        HTTPException: If listing fails
    """
    with track_api_call("sessions.list", "GET"):
        try:
            # Extract user ID from authenticated user
            user_id = extract_user_id(user)
            # Security: Only admins can see cost data
            user_is_admin = is_admin(user)

            # Validate workspace access if filtering by workspace
            validated_workspace_id: str | None = None
            if workspace_id:
                import uuid as uuid_module

                try:
                    ws_uuid = uuid_module.UUID(workspace_id)
                    require_workspace_access(ws_uuid, user_id)
                    validated_workspace_id = workspace_id
                except ValueError as e:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid workspace_id format",
                    ) from e

            # PRIMARY SOURCE: Query PostgreSQL for persistent session records
            try:
                pg_sessions = session_repository.list_by_user(
                    user_id=user_id,
                    limit=limit,
                    offset=offset,
                    status_filter=status,
                    workspace_id=validated_workspace_id,
                )
                logger.debug(
                    f"Loaded {len(pg_sessions)} sessions from PostgreSQL for user {user_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to load sessions from PostgreSQL: {e}, falling back to Redis"
                )
                pg_sessions = []

            # If Postgres returned sessions, enrich with Redis live state
            if pg_sessions:
                # Create Redis manager for enrichment
                redis_manager = get_redis_manager()

                sessions: list[SessionResponse] = []
                for pg_session in pg_sessions:
                    session_id = pg_session["id"]

                    # Try to enrich with live metadata from Redis (if available)
                    redis_metadata = None
                    if redis_manager.is_available:
                        redis_metadata = redis_manager.load_metadata(session_id)

                    # Use Redis data if available and more recent, otherwise use Postgres
                    if redis_metadata:
                        # Check if Redis has newer data (e.g., for active sessions)
                        redis_updated = redis_metadata.get("updated_at")
                        pg_updated = (
                            pg_session["updated_at"].isoformat()
                            if pg_session["updated_at"]
                            else None
                        )

                        use_redis = redis_updated and pg_updated and redis_updated > pg_updated
                        status_val = (
                            redis_metadata.get("status") if use_redis else pg_session["status"]
                        )
                        phase_val = (
                            redis_metadata.get("phase") if use_redis else pg_session["phase"]
                        )
                        cost_val = (
                            redis_metadata.get("cost")
                            if use_redis
                            else pg_session.get("total_cost")
                        )
                        last_activity_at = (
                            datetime.fromisoformat(redis_metadata["last_activity_at"])
                            if redis_metadata.get("last_activity_at")
                            else None
                        )
                    else:
                        # Use Postgres data only
                        status_val = pg_session["status"]
                        phase_val = pg_session["phase"]
                        cost_val = pg_session.get("total_cost")
                        last_activity_at = None

                    # Create session response with summary counts
                    # Security: Strip cost data for non-admin users
                    session = SessionResponse(
                        id=session_id,
                        status=status_val,
                        phase=phase_val,
                        created_at=pg_session["created_at"],
                        updated_at=pg_session["updated_at"],
                        last_activity_at=last_activity_at,
                        problem_statement=truncate_text(pg_session["problem_statement"]),
                        cost=cost_val if user_is_admin else None,
                        # Summary counts for dashboard cards
                        expert_count=pg_session.get("expert_count"),
                        contribution_count=pg_session.get("contribution_count"),
                        task_count=pg_session.get("task_count"),
                        focus_area_count=pg_session.get("focus_area_count"),
                    )
                    sessions.append(session)

                # Total is already filtered by status in Postgres query
                # For accurate pagination, we'd need a count query, but this approximation works
                total = len(sessions)

                return SessionListResponse(
                    sessions=sessions,
                    total=total,
                    limit=limit,
                    offset=offset,
                )

            # FALLBACK: If Postgres failed or returned empty, try Redis
            redis_manager = get_redis_manager()

            if not redis_manager.is_available:
                # No data available from either source
                return SessionListResponse(
                    sessions=[],
                    total=0,
                    limit=limit,
                    offset=offset,
                )

            # Get session IDs for this user only (uses Redis SET - O(1) lookup)
            session_ids = redis_manager.list_user_sessions(user_id)

            if not session_ids:
                return SessionListResponse(
                    sessions=[],
                    total=0,
                    limit=limit,
                    offset=offset,
                )

            # Batch load metadata for all user sessions (single Redis pipeline)
            metadata_dict = redis_manager.batch_load_metadata(session_ids)

            # Build session list from metadata
            sessions_fallback: list[SessionResponse] = []
            for session_id, metadata in metadata_dict.items():
                # Skip soft-deleted sessions
                if metadata.get("deleted_at"):
                    continue

                # Apply status filter
                if status and metadata.get("status") != status:
                    continue

                # Parse timestamps
                try:
                    created_at = datetime.fromisoformat(metadata["created_at"])
                    updated_at = datetime.fromisoformat(metadata["updated_at"])
                    last_activity_at = (
                        datetime.fromisoformat(metadata["last_activity_at"])
                        if metadata.get("last_activity_at")
                        else None
                    )
                except (KeyError, ValueError):
                    # Skip sessions with invalid timestamps
                    logger.warning(f"Invalid timestamps for session {session_id}")
                    continue

                # Create session response
                # Security: Strip cost data for non-admin users
                session = SessionResponse(
                    id=session_id,
                    status=metadata.get("status", "unknown"),
                    phase=metadata.get("phase"),
                    created_at=created_at,
                    updated_at=updated_at,
                    last_activity_at=last_activity_at,
                    problem_statement=truncate_text(
                        metadata.get("problem_statement", "Unknown problem")
                    ),
                    cost=metadata.get("cost") if user_is_admin else None,
                )
                sessions_fallback.append(session)

            # Sort by updated_at descending (most recent first)
            sessions_fallback.sort(key=lambda s: s.updated_at, reverse=True)

            # Apply pagination
            total_fallback = len(sessions_fallback)
            paginated_sessions = sessions_fallback[offset : offset + limit]

            logger.info(
                f"Returning {len(paginated_sessions)} sessions from Redis fallback for user {user_id}"
            )

            return SessionListResponse(
                sessions=paginated_sessions,
                total=total_fallback,
                limit=limit,
                offset=offset,
            )

        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to list sessions: {e}",
                user_id=user_id,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list sessions: {str(e)}",
            ) from e


# =============================================================================
# Static Path Endpoints (MUST be before /{session_id} parameterized routes)
# =============================================================================


@router.get(
    "/recent-failures",
    summary="Get recent failed meetings",
    description="Get failed meetings in the last 24 hours for dashboard alert.",
    responses={
        200: {
            "description": "Recent failures retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "count": 1,
                        "failures": [
                            {
                                "session_id": "bo1_abc123",
                                "problem_statement_preview": "How should we approach...",
                                "created_at": "2025-12-16T10:30:00+00:00",
                            }
                        ],
                    }
                }
            },
        },
    },
)
async def get_recent_failures(
    user: dict[str, Any] = Depends(get_current_user),
    hours: int = Query(24, ge=1, le=168, description="Look back window in hours"),
) -> dict[str, Any]:
    """Get recent failed meetings for dashboard alert.

    Returns failed meetings in the specified window (default 24h) so the
    dashboard can show a reassuring alert to the user.

    Args:
        user: Authenticated user data
        hours: Look back window in hours (default 24, max 168/7days)

    Returns:
        Dict with count and list of failures
    """
    with track_api_call("sessions.recent_failures", "GET"):
        user_id = extract_user_id(user)
        failures = session_repository.list_recent_failures(user_id, hours=hours)
        return {
            "count": len(failures),
            "failures": failures,
        }


@router.get(
    "/cap-status",
    summary="Get meeting cap status",
    description="Get current meeting cap status for the authenticated user (beta feature).",
    responses={
        200: {
            "description": "Cap status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "allowed": True,
                        "remaining": 2,
                        "limit": 4,
                        "reset_time": "2025-12-17T12:00:00+00:00",
                        "exceeded": False,
                        "recent_count": 2,
                    }
                }
            },
        },
    },
)
async def get_cap_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get meeting cap status for the current user.

    Returns the current state of the beta meeting cap including:
    - Whether the user can start a new meeting
    - How many meetings remain in the current window
    - When the cap will reset (if exceeded)

    Args:
        user: Authenticated user data

    Returns:
        MeetingCapStatus dict
    """
    from backend.services.meeting_cap import check_meeting_cap

    with track_api_call("sessions.cap_status", "GET"):
        user_id = extract_user_id(user)
        cap_status = check_meeting_cap(user_id)
        return cap_status.to_dict()


@router.post(
    "/acknowledge-failures",
    response_model=MessageResponse,
    summary="Acknowledge failed meetings",
    description="Acknowledge one or more failed meetings, making their actions visible.",
    responses={
        200: {
            "description": "Failures acknowledged successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Acknowledged 2 failed meetings",
                    }
                }
            },
        },
        400: {"description": "No session IDs provided", "model": ErrorResponse},
    },
)
@handle_api_errors("acknowledge failures")
async def acknowledge_failures(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> MessageResponse:
    """Acknowledge failed meetings to make their actions visible.

    When a meeting fails, its actions are hidden by default. Users can
    acknowledge the failure to make actions visible in their action list.

    Args:
        request: Request with session_ids to acknowledge
        user: Authenticated user data

    Returns:
        MessageResponse with count of acknowledged sessions
    """
    with track_api_call("sessions.acknowledge_failures", "POST"):
        user_id = extract_user_id(user)

        # Parse request body
        body = await request.json()
        session_ids = body.get("session_ids", [])

        if not session_ids:
            raise_api_error("invalid_input", "No session IDs provided")

        # Batch acknowledge all failures
        acknowledged_count = session_repository.batch_acknowledge_failures(
            session_ids=session_ids,
            user_id=user_id,
        )

        logger.info(
            f"User {user_id} acknowledged {acknowledged_count} failed meetings: {session_ids}"
        )

        return MessageResponse(
            status="success",
            message=f"Acknowledged {acknowledged_count} failed meeting(s)",
        )


# =============================================================================
# Session Detail Endpoints (parameterized routes)
# =============================================================================


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="Get session details",
    description="Get detailed information about a specific deliberation session.",
    responses={
        200: {"description": "Session details retrieved successfully"},
        404: {
            "description": "Session not found",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_session(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> SessionDetailResponse:
    """Get detailed information about a session.

    Returns full session state including deliberation progress, contributions,
    metrics, and costs.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        SessionDetailResponse with full session details

    Raises:
        HTTPException: If session not found or retrieval fails
    """
    with track_api_call("sessions.get", "GET"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Load full state (if available)
            state = redis_manager.load_state(session_id)

            # Parse timestamps
            try:
                created_at = datetime.fromisoformat(metadata["created_at"])
                updated_at = datetime.fromisoformat(metadata["updated_at"])
            except (KeyError, ValueError) as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid session metadata: {e}",
                ) from e

            # Build problem details
            problem_dict = {
                "statement": metadata.get("problem_statement", ""),
                "context": metadata.get("problem_context", {}),
            }

            # Convert state to dict if it's a DeliberationState
            state_dict: dict[str, Any] | None = None
            if state:
                if isinstance(state, dict):
                    state_dict = state
                else:
                    # Convert DeliberationState to dict
                    state_dict = state.model_dump() if hasattr(state, "model_dump") else None

            # Extract metrics from state if available
            metrics = None
            if state_dict:
                metrics = {
                    "round_number": state_dict.get("round_number", 0),
                    "total_cost": state_dict.get("total_cost", 0.0),
                    "phase_costs": state_dict.get("phase_costs", {}),
                    "contributions_count": len(state_dict.get("contributions", [])),
                }

            # Get reconnect info for admin debugging (optional)
            reconnect_count = None
            try:
                from backend.api.streaming import get_reconnect_info

                reconnect_info = await get_reconnect_info(session_id)
                if reconnect_info:
                    reconnect_count = reconnect_info.get("reconnect_count")
            except Exception as e:
                logger.debug(f"Failed to get reconnect info for {session_id}: {e}")

            return SessionDetailResponse(
                id=session_id,
                status=metadata.get("status", "unknown"),
                phase=metadata.get("phase"),
                created_at=created_at,
                updated_at=updated_at,
                problem=problem_dict,
                state=state_dict,
                metrics=metrics,
                reconnect_count=reconnect_count,
            )

        except HTTPException:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to get session {session_id}: {e}",
                session_id=session_id,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get session: {str(e)}",
            ) from e


@router.delete(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Soft delete a session",
    description="Soft delete a deliberation session. Automatically kills any active executions. Session data is retained but hidden from lists.",
    responses={
        200: {"description": "Session soft deleted successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def delete_session(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> SessionResponse:
    """Soft delete a session.

    This endpoint:
    1. Verifies user owns the session
    2. Kills any active execution
    3. Marks the session as soft deleted with deleted_at timestamp
    4. Updates session status to "deleted"

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance
        session_manager: Session manager instance

    Returns:
        SessionResponse with deleted status

    Raises:
        HTTPException: If session not found or user doesn't own it
    """
    with track_api_call("sessions.delete", "DELETE"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Check if already deleted
            if metadata.get("deleted_at"):
                raise_api_error("gone", f"Session already deleted: {session_id}")

            # Kill any active execution
            if session_id in session_manager.active_executions:
                try:
                    await session_manager.kill_session(session_id, user_id, "User deleted session")
                    logger.info(f"Killed active execution for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to kill active execution: {e}")
                    # Continue with soft delete even if kill fails

            # Update metadata with soft delete
            now = datetime.now(UTC)
            metadata["status"] = "deleted"
            metadata["deleted_at"] = now.isoformat()
            metadata["updated_at"] = now.isoformat()

            # Save updated metadata
            if not redis_manager.save_metadata(session_id, metadata):
                raise HTTPException(
                    status_code=500,
                    detail="Failed to update session metadata",
                )

            # Remove session from user's index for fast listing
            redis_manager.remove_session_from_user_index(user_id, session_id)

            # Also update PostgreSQL status to ensure consistency
            try:
                session_repository.update_status(session_id=session_id, status="deleted")
                # Invalidate cached metadata on status change
                get_session_metadata_cache().invalidate(session_id)
            except Exception as pg_err:
                logger.warning(f"Failed to update PostgreSQL status for {session_id}: {pg_err}")
                # Continue - Redis is the source of truth for active sessions

            # P1-006: Cascade soft delete to actions
            try:
                from bo1.state.repositories.action_repository import ActionRepository

                action_repo = ActionRepository()
                deleted_actions = action_repo.soft_delete_by_session(session_id)
                if deleted_actions > 0:
                    logger.info(
                        f"Cascade soft-deleted {deleted_actions} actions for session {session_id}"
                    )
            except Exception as cascade_err:
                logger.warning(f"Failed to cascade delete actions for {session_id}: {cascade_err}")
                # Continue - session delete should still succeed

            logger.info(f"Soft deleted session: {session_id} for user: {user_id}")

            # Return session response
            return SessionResponse(
                id=session_id,
                status="deleted",
                phase=metadata.get("phase"),
                created_at=datetime.fromisoformat(metadata["created_at"]),
                updated_at=now,
                problem_statement=truncate_text(
                    metadata.get("problem_statement", "Unknown problem")
                ),
                cost=metadata.get("cost"),
            )

        except HTTPException:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to delete session {session_id}: {e}",
                session_id=session_id,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete session: {str(e)}",
            ) from e


@router.post(
    "/{session_id}/terminate",
    response_model=TerminationResponse,
    summary="Terminate session early",
    description="Terminate a session early with optional synthesis. Calculates partial billing.",
    responses={
        200: {"description": "Session terminated successfully"},
        400: {"description": "Invalid termination type or session already terminated"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("terminate session")
async def terminate_session(
    session_id: str,
    termination_request: TerminationRequest,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
    session_manager: SessionManager = Depends(get_session_manager),
) -> TerminationResponse:
    """Terminate a session early with partial billing.

    This endpoint:
    1. Verifies user owns the session
    2. Kills any active execution
    3. Calculates billable portion based on completed sub-problems
    4. Optionally triggers early synthesis (for continue_best_effort)
    5. Updates session status and emits termination events

    Args:
        session_id: Session identifier
        termination_request: Termination request with type and reason
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance
        session_manager: Session manager instance

    Returns:
        TerminationResponse with billing and synthesis info
    """
    with track_api_call("sessions.terminate", "POST"):
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Unpack verified session data
        user_id, metadata = session_data

        # Check if already terminated
        if metadata.get("status") == "terminated":
            raise_api_error("conflict", "Session already terminated")

        # Check if already completed - no need to terminate
        if metadata.get("status") == "completed":
            raise_api_error("conflict", "Session already completed - cannot terminate")

        # Load state to calculate billable portion
        state = redis_manager.load_state(session_id)
        state_dict: dict[str, Any] = {}
        if state:
            if isinstance(state, dict):
                state_dict = state
            else:
                state_dict = state.model_dump() if hasattr(state, "model_dump") else {}

        # Calculate billable portion based on completed sub-problems
        sub_problem_results = state_dict.get("sub_problem_results", [])
        problem = state_dict.get("problem", {})
        total_sub_problems = len(problem.get("sub_problems", [])) if problem else 1

        # Count completed sub-problems (those with synthesis)
        completed_count = len(sub_problem_results)
        billable_portion = completed_count / max(total_sub_problems, 1)

        # For user_cancelled, billable portion is 0 if nothing completed
        if termination_request.termination_type == "user_cancelled" and completed_count == 0:
            billable_portion = 0.0

        # For continue_best_effort, at least bill for what's done
        if termination_request.termination_type == "continue_best_effort":
            billable_portion = max(billable_portion, 0.25)  # Minimum 25% for effort

        # Kill any active execution
        if session_id in session_manager.active_executions:
            try:
                await session_manager.kill_session(
                    session_id,
                    user_id,
                    f"User terminated: {termination_request.termination_type}",
                )
                logger.info(f"Killed active execution for terminated session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to kill active execution during termination: {e}")

        # Update database
        result = session_repository.terminate_session(
            session_id=session_id,
            termination_type=termination_request.termination_type,
            termination_reason=termination_request.reason,
            billable_portion=billable_portion,
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to update session termination status",
            )

        # Update Redis metadata
        now = datetime.now(UTC)
        metadata["status"] = "terminated"
        metadata["terminated_at"] = now.isoformat()
        metadata["termination_type"] = termination_request.termination_type
        metadata["updated_at"] = now.isoformat()
        redis_manager.save_metadata(session_id, metadata)

        # Invalidate cached metadata on status change
        get_session_metadata_cache().invalidate(session_id)

        # Emit SSE termination event
        try:
            from backend.api.event_publisher import publish_event

            await publish_event(
                session_id=session_id,
                event_type="meeting_terminated",
                data={
                    "termination_type": termination_request.termination_type,
                    "reason": termination_request.reason,
                    "billable_portion": billable_portion,
                    "completed_sub_problems": completed_count,
                    "total_sub_problems": total_sub_problems,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to emit termination event: {e}")

        # Record Prometheus metric
        try:
            from backend.api.middleware.metrics import record_session_created

            record_session_created("terminated")
        except Exception as e:
            logger.debug(f"Failed to record termination metric: {e}")

        logger.info(
            f"Terminated session {session_id}: type={termination_request.termination_type}, "
            f"billable_portion={billable_portion:.2f}, completed={completed_count}/{total_sub_problems}"
        )

        # Check if synthesis is available
        synthesis_available = (
            termination_request.termination_type == "continue_best_effort" and completed_count > 0
        )

        return TerminationResponse(
            session_id=session_id,
            status="terminated",
            terminated_at=now,
            termination_type=termination_request.termination_type,
            billable_portion=billable_portion,
            completed_sub_problems=completed_count,
            total_sub_problems=total_sub_problems,
            synthesis_available=synthesis_available,
        )


@router.post(
    "/{session_id}/extract-tasks",
    summary="Extract actionable tasks from synthesis",
    description="Extract discrete, actionable tasks from session synthesis using AI.",
    responses={
        200: {"description": "Tasks extracted successfully"},
        404: {"description": "Session or synthesis not found", "model": ErrorResponse},
        500: {"description": "Task extraction failed", "model": ErrorResponse},
    },
)
async def extract_tasks(
    session_id: str,
    session_data: VerifiedSession,
    redis_manager: RedisManager = Depends(get_redis_manager),
) -> dict[str, Any]:
    """Extract actionable tasks from session synthesis.

    This endpoint:
    1. Retrieves the synthesis from session metadata
    2. Uses Claude to extract discrete, actionable tasks
    3. Returns tasks with priorities, dates, and dependencies

    Args:
        session_id: Session ID
        session_data: Verified session (user_id, metadata) from dependency
        redis_manager: Redis manager instance

    Returns:
        Dict with extracted tasks and metadata

    Raises:
        HTTPException: If synthesis not found or extraction fails
    """
    with track_api_call("sessions.extract_tasks", "POST"):
        try:
            # Validate session ID format
            if not validate_session_id(session_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid session ID format",
                )

            # Unpack verified session data
            user_id, metadata = session_data

            # 1. Check PostgreSQL first for persistent storage (survives Redis expiry)
            try:
                db_tasks = session_repository.get_tasks(session_id)
                if db_tasks:
                    logger.info(f"Returning tasks from PostgreSQL for session {session_id}")
                    return {
                        "tasks": db_tasks["tasks"],
                        "total_tasks": db_tasks["total_tasks"],
                        "extraction_confidence": float(db_tasks["extraction_confidence"]),
                        "synthesis_sections_analyzed": db_tasks["synthesis_sections_analyzed"],
                    }
            except Exception as e:
                logger.warning(
                    f"Failed to load tasks from PostgreSQL: {e}, falling back to extraction"
                )

            # 2. Check Redis cache as fallback (for backwards compatibility)
            cache_key = f"extracted_tasks:{session_id}"
            cached_tasks = redis_manager.redis.get(cache_key)

            if cached_tasks:
                import json

                logger.info(f"Returning cached tasks from Redis for session {session_id}")
                cached_data = json.loads(cached_tasks)

                # Backfill to PostgreSQL if not already there (fixes missing task counts)
                try:
                    session_repository.save_tasks(
                        session_id=session_id,
                        tasks=cached_data.get("tasks", []),
                        total_tasks=cached_data.get("total_tasks", 0),
                        extraction_confidence=cached_data.get("extraction_confidence", 0.0),
                        synthesis_sections_analyzed=cached_data.get(
                            "synthesis_sections_analyzed", []
                        ),
                    )
                    logger.info(f"Backfilled tasks to PostgreSQL for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to backfill tasks to PostgreSQL: {e}")

                return cached_data

            # Extract tasks from ALL synthesis events (sub-problems + meta-synthesis)
            # This ensures tasks are associated with their respective sub-problems
            # Try Redis first (for active sessions), fall back to PostgreSQL (for completed sessions)
            events_key = f"events_history:{session_id}"
            redis_events = redis_manager.redis.lrange(events_key, 0, -1)

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=500,
                    detail="AI service not configured",
                )

            # Collect all synthesis events
            synthesis_events: list[tuple[str, int | None]] = []  # (synthesis, sub_problem_index)

            # Parse events from Redis (JSON strings) or PostgreSQL (dicts)
            if redis_events:
                logger.info(
                    f"Reading {len(redis_events)} events from Redis for session {session_id}"
                )
                for event_json in redis_events:
                    import json

                    event = json.loads(event_json)
                    event_type = event.get("event_type")
                    event_data = event.get("data", {})
                    if event_type == "synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        sub_problem_index = event_data.get("sub_problem_index")
                        if synthesis:
                            synthesis_events.append((synthesis, sub_problem_index))
                    elif event_type == "meta_synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        if synthesis:
                            synthesis_events.append((synthesis, None))
            else:
                # Fall back to PostgreSQL for completed sessions where Redis expired
                logger.info(f"Redis empty, reading events from PostgreSQL for session {session_id}")
                pg_events = session_repository.get_events(session_id)
                for event in pg_events:
                    event_type = event.get("event_type")
                    # PostgreSQL data column has nested structure: {"data": {...payload...}, ...}
                    full_data = event.get("data", {})
                    event_data = full_data.get("data", {}) if isinstance(full_data, dict) else {}
                    if event_type == "synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        sub_problem_index = event_data.get("sub_problem_index")
                        if synthesis:
                            synthesis_events.append((synthesis, sub_problem_index))
                    elif event_type == "meta_synthesis_complete":
                        synthesis = event_data.get("synthesis")
                        if synthesis:
                            synthesis_events.append((synthesis, None))

            if not synthesis_events:
                raise HTTPException(
                    status_code=404,
                    detail="No synthesis found for this session. Run the deliberation to completion first.",
                )

            # Build sub-problem context for cross-sub-problem dependency extraction
            # Filter to get only sub-problem syntheses (not meta-synthesis)
            sub_problem_syntheses = [(s, idx) for s, idx in synthesis_events if idx is not None]
            total_sub_problems = len(sub_problem_syntheses)

            # Build goal map from decomposition_complete event (if available)
            sub_problem_goals: dict[int, str] = {}
            for event_json in redis_events or []:
                try:
                    import json as json_mod

                    event = (
                        json_mod.loads(event_json)
                        if isinstance(event_json, (str, bytes))
                        else event_json
                    )
                    if event.get("event_type") == "decomposition_complete":
                        for idx, sp in enumerate(event.get("data", {}).get("sub_problems", [])):
                            sub_problem_goals[idx] = sp.get("goal", f"Sub-problem {idx + 1}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to parse event JSON: {e}")
                    continue

            # Extract tasks from each synthesis and tag with sub_problem_index
            all_tasks: list[dict[str, Any]] = []
            all_sections_analyzed: list[str] = []
            total_confidence_sum = 0.0
            tasks_by_sp: dict[int | None, int] = {}  # Track task count per sub-problem

            for synthesis, sub_problem_index in synthesis_events:
                logger.info(
                    f"Extracting tasks from synthesis (sub_problem_index={sub_problem_index}) "
                    f"for session {session_id}"
                )

                # Build context for other sub-problems (for cross-sp dependencies)
                other_goals = [
                    f"[sp{idx}] {goal}"
                    for idx, goal in sub_problem_goals.items()
                    if idx != sub_problem_index
                ]

                result = sync_extract_tasks_from_synthesis(
                    synthesis=synthesis,
                    session_id=session_id,
                    anthropic_api_key=api_key,
                    sub_problem_index=sub_problem_index,
                    total_sub_problems=total_sub_problems,
                    other_sub_problem_goals=other_goals,
                )

                # Tag each task with its sub_problem_index
                task_count = 0
                for task in result.tasks:
                    task_dict = task.model_dump() if hasattr(task, "model_dump") else task
                    task_dict["sub_problem_index"] = sub_problem_index
                    all_tasks.append(task_dict)
                    task_count += 1

                # Track task count per sub-problem for validation
                tasks_by_sp[sub_problem_index] = task_count

                all_sections_analyzed.extend(result.synthesis_sections_analyzed)
                total_confidence_sum += result.extraction_confidence

            # ISSUE #2 FIX: Validation that all sub-problems have tasks extracted
            sp_indices_with_tasks = {idx for idx in tasks_by_sp.keys() if idx is not None}
            expected_sp_indices = set(range(total_sub_problems))
            missing_sp_indices = expected_sp_indices - sp_indices_with_tasks

            if missing_sp_indices:
                logger.warning(
                    f"TASK EXTRACTION WARNING: Sub-problems {sorted(missing_sp_indices)} "
                    f"have no tasks extracted for session {session_id}. "
                    f"Tasks by sub-problem: {tasks_by_sp}"
                )

            # Log task distribution for debugging
            logger.info(f"Task distribution by sub-problem for session {session_id}: {tasks_by_sp}")

            # Calculate average confidence across all syntheses
            avg_confidence = (
                total_confidence_sum / len(synthesis_events) if synthesis_events else 0.0
            )

            logger.info(
                f"Extracted {len(all_tasks)} tasks total from {len(synthesis_events)} "
                f"synthesis events for session {session_id} (avg confidence: {avg_confidence:.2f})"
            )

            # Prepare result dictionary
            result_dict = {
                "tasks": all_tasks,
                "total_tasks": len(all_tasks),
                "extraction_confidence": avg_confidence,
                "synthesis_sections_analyzed": list(set(all_sections_analyzed)),
            }

            # 1. Save to PostgreSQL for long-term persistence (PRIMARY storage)
            try:
                session_repository.save_tasks(
                    session_id=session_id,
                    tasks=all_tasks,
                    total_tasks=len(all_tasks),
                    extraction_confidence=avg_confidence,
                    synthesis_sections_analyzed=list(set(all_sections_analyzed)),
                )
                logger.info(f"Saved extracted tasks to PostgreSQL for session {session_id}")
            except Exception as e:
                log_error(
                    logger,
                    ErrorCode.DB_WRITE_ERROR,
                    f"Failed to save tasks to PostgreSQL: {e}",
                    session_id=session_id,
                )

            # 2. Cache in Redis with 24-hour TTL (SECONDARY cache for speed)
            try:
                import json

                redis_manager.redis.setex(cache_key, 86400, json.dumps(result_dict))
                logger.info(f"Cached extracted tasks in Redis for session {session_id} (24h TTL)")
            except Exception as e:
                logger.warning(f"Failed to cache tasks in Redis: {e}")

            # Return task extraction result
            return result_dict

        except HTTPException:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to extract tasks for session {session_id}: {e}",
                session_id=session_id,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Task extraction failed: {str(e)}",
            ) from e


# =============================================================================
# Action/Task Endpoints (Kanban)
# =============================================================================


def _tasks_with_statuses(
    tasks: list[dict[str, Any]], task_statuses: dict[str, str]
) -> list[TaskWithStatus]:
    """Merge tasks with their statuses.

    Args:
        tasks: List of task dictionaries
        task_statuses: Mapping of task_id -> status

    Returns:
        List of TaskWithStatus objects
    """
    result = []
    for task in tasks:
        task_id = task.get("id", "")
        status = task_statuses.get(task_id, "todo")  # Default to "todo"
        result.append(
            TaskWithStatus(
                id=task_id,
                title=task.get("title", ""),
                description=task.get("description", ""),
                what_and_how=task.get("what_and_how", []),
                success_criteria=task.get("success_criteria", []),
                kill_criteria=task.get("kill_criteria", []),
                dependencies=task.get("dependencies", []),
                timeline=task.get("timeline", ""),
                priority=task.get("priority", "medium"),
                category=task.get("category", "implementation"),
                source_section=task.get("source_section"),
                confidence=task.get("confidence", 0.0),
                sub_problem_index=task.get("sub_problem_index"),
                status=status,
            )
        )
    return result


def _count_by_status(tasks: list[TaskWithStatus]) -> dict[str, int]:
    """Count tasks by status.

    Args:
        tasks: List of tasks with statuses

    Returns:
        Dict mapping status -> count
    """
    counts = {"todo": 0, "doing": 0, "done": 0}
    for task in tasks:
        if task.status in counts:
            counts[task.status] += 1
    return counts


@router.get(
    "/{session_id}/actions",
    response_model=SessionActionsResponse,
    summary="Get session actions with statuses",
    description="Get all extracted tasks for a session with their Kanban statuses.",
    responses={
        200: {"description": "Actions retrieved successfully"},
        404: {"description": "Session or tasks not found", "model": ErrorResponse},
    },
)
async def get_session_actions(
    session_id: str,
    session_data: VerifiedSession,
) -> SessionActionsResponse:
    """Get all actions/tasks for a session with their statuses.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        SessionActionsResponse with tasks and status counts
    """
    with track_api_call("sessions.get_actions", "GET"):
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Get tasks from database
        task_record = session_repository.get_tasks(session_id)

        if not task_record:
            raise_api_error(
                "not_found",
                "No tasks found for this session. Extract tasks first using POST /sessions/{id}/extract-tasks",
            )

        # Merge tasks with statuses
        tasks = task_record.get("tasks", [])
        task_statuses = task_record.get("task_statuses", {}) or {}

        tasks_with_status = _tasks_with_statuses(tasks, task_statuses)
        by_status = _count_by_status(tasks_with_status)

        return SessionActionsResponse(
            session_id=session_id,
            tasks=tasks_with_status,
            total_tasks=len(tasks_with_status),
            by_status=by_status,
        )


@router.patch(
    "/{session_id}/actions/{task_id}",
    response_model=MessageResponse,
    summary="Update task status",
    description="Update the Kanban status of a specific task.",
    responses={
        200: {"description": "Status updated successfully"},
        400: {"description": "Invalid status", "model": ErrorResponse},
        404: {"description": "Session or task not found", "model": ErrorResponse},
    },
)
async def update_task_status(
    session_id: str,
    task_id: str,
    status_update: TaskStatusUpdate,
    session_data: VerifiedSession,
) -> MessageResponse:
    """Update the status of a task in a session.

    Args:
        session_id: Session identifier
        task_id: Task identifier (e.g., "task_1")
        status_update: New status
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        MessageResponse with status and message
    """
    with track_api_call("sessions.update_task_status", "PATCH"):
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Validate task_id format (should be "task_N")
        if not task_id or not task_id.startswith("task_"):
            raise_api_error("invalid_input", "Invalid task ID format. Expected 'task_N' format.")

        # Update task status in database
        try:
            success = session_repository.update_task_status(
                session_id=session_id,
                task_id=task_id,
                status=status_update.status,
            )

            if not success:
                raise_api_error(
                    "not_found", f"Session {session_id} not found or no tasks extracted"
                )

            logger.info(
                f"Updated task {task_id} status to {status_update.status} for session {session_id}"
            )

            return MessageResponse(
                status="success",
                message=f"Task {task_id} status updated to {status_update.status}",
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{session_id}/costs",
    response_model=SessionCostBreakdown,
    summary="Get session cost breakdown (admin only)",
    description="Get detailed cost breakdown by sub-problem for a session. Requires admin privileges.",
    responses={
        200: {"description": "Cost breakdown retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get session costs")
async def get_session_costs(
    session_id: str,
    session_data: VerifiedSession,
    current_user: dict = Depends(get_current_user),
) -> SessionCostBreakdown:
    """Get detailed cost breakdown for a session (admin only).

    Returns total costs and per-sub-problem breakdown including:
    - Total cost, tokens, and API calls
    - Cost breakdown by AI provider (Anthropic, Voyage, Brave, Tavily)
    - Cost breakdown by sub-problem with phase attribution

    Security: This endpoint requires admin privileges as cost data is sensitive.

    Args:
        session_id: Session identifier (bo1_xxx format)
        session_data: Verified session (user_id, metadata) from dependency
        current_user: Current authenticated user (for admin check)

    Returns:
        SessionCostBreakdown with total and per-sub-problem costs

    Raises:
        HTTPException 403: If user is not an admin
    """
    # Security: Require admin access to view cost data
    if not is_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view cost breakdown",
        )

    with track_api_call("sessions.get_costs", "GET"):
        # Validate session ID format
        session_id = validate_session_id(session_id)

        # Get total session costs
        total_costs = CostTracker.get_session_costs(session_id)

        # Get per-sub-problem breakdown
        subproblem_costs = CostTracker.get_subproblem_costs(session_id)

        # Convert to response model
        by_sub_problem = [
            SubProblemCost(
                sub_problem_index=sp["sub_problem_index"],
                label=sp["label"],
                total_cost=sp["total_cost"],
                api_calls=sp["api_calls"],
                total_tokens=sp["total_tokens"],
                by_provider=ProviderCosts(**sp["by_provider"]),
                by_phase=PhaseCosts(**sp["by_phase"]),
            )
            for sp in subproblem_costs
        ]

        return SessionCostBreakdown(
            session_id=session_id,
            total_cost=total_costs["total_cost"],
            total_tokens=total_costs["total_tokens"],
            total_api_calls=total_costs["total_calls"],
            by_provider=ProviderCosts(**total_costs["by_provider"]),
            by_sub_problem=by_sub_problem,
        )


# =============================================================================
# Export & Sharing Endpoints
# =============================================================================


@router.get(
    "/{session_id}/export",
    summary="Export session in JSON or Markdown",
    description="Export session data as JSON or Markdown format. Returns file with Content-Disposition header.",
    responses={
        200: {"description": "File exported successfully"},
        400: {"description": "Invalid format", "model": ErrorResponse},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("export session")
async def export_session(
    session_id: str,
    session_data: VerifiedSession,
    format: str = Query("json", pattern="^(json|markdown)$"),
) -> Any:
    """Export session to JSON or Markdown format.

    Args:
        session_id: Session identifier
        format: Export format (json or markdown)
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        File response with appropriate Content-Disposition header

    Raises:
        HTTPException: If session not found or user lacks permission
    """
    with track_api_call("sessions.export", "GET"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Get database session for exporter
            from bo1.state.database import SessionLocal

            db = SessionLocal()
            try:
                exporter = SessionExporter(db)

                if format == "json":
                    export_data = await exporter.export_to_json(session_id, user_id)

                    from fastapi.responses import JSONResponse

                    filename = f"session_{session_id}_{datetime.now(UTC).strftime('%Y%m%d')}.json"
                    return JSONResponse(
                        content=export_data,
                        headers={
                            "Content-Disposition": f"attachment; filename={filename}",
                        },
                    )
                else:  # markdown
                    export_data = await exporter.export_to_markdown(session_id, user_id)

                    from fastapi.responses import PlainTextResponse

                    filename = f"session_{session_id}_{datetime.now(UTC).strftime('%Y%m%d')}.md"
                    return PlainTextResponse(
                        content=export_data,
                        headers={
                            "Content-Disposition": f"attachment; filename={filename}",
                        },
                    )

            finally:
                db.close()

        except ValueError as e:
            # Permission or not found error from SessionExporter
            if "does not own" in str(e):
                raise HTTPException(status_code=403, detail=str(e)) from e
            else:
                raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/{session_id}/share",
    summary="Create a session share link",
    description="Create a time-limited shareable link for this session.",
    responses={
        201: {
            "description": "Share created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "token": "abc123...",
                        "share_url": "https://example.com/share/abc123...",
                        "expires_at": "2025-12-19T00:00:00+00:00",
                    }
                }
            },
        },
        400: {"description": "Invalid TTL", "model": ErrorResponse},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("create share")
async def create_share(
    session_id: str,
    session_data: VerifiedSession,
    ttl_days: int = Query(7, ge=1, le=365),
) -> dict[str, Any]:
    """Create a share link for a session.

    Args:
        session_id: Session identifier
        ttl_days: Time-to-live in days (1-365)
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        Dict with token, share_url, and expires_at

    Raises:
        HTTPException: If validation fails
    """
    with track_api_call("sessions.create_share", "POST"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Validate TTL
            ttl_days = SessionShareService.validate_ttl(ttl_days)

            # Generate token
            token = SessionShareService.generate_token()
            expires_at = SessionShareService.calculate_expiry(ttl_days)

            # Get database session for storage
            from bo1.state.database import SessionLocal

            db = SessionLocal()
            try:
                # Store in PostgreSQL
                session_repository.create_share(
                    session_id=session_id,
                    token=token,
                    expires_at=expires_at,
                )

                logger.info(f"Created share for session {session_id}: {token}")

                # Build share URL
                # In production, this would be the actual domain
                share_url = f"/share/{token}"  # Relative URL; client will build full URL

                return {
                    "token": token,
                    "share_url": share_url,
                    "expires_at": expires_at.isoformat(),
                }

            finally:
                db.close()

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/{session_id}/share",
    summary="List active shares for a session",
    description="List all active share links for this session.",
    responses={
        200: {"description": "Shares retrieved successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("list shares")
async def list_shares(
    session_id: str,
    session_data: VerifiedSession,
) -> dict[str, Any]:
    """List active shares for a session.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        Dict with list of shares

    Raises:
        HTTPException: If session not found or user lacks permission
    """
    with track_api_call("sessions.list_shares", "GET"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Get database session
            from bo1.state.database import SessionLocal

            db = SessionLocal()
            try:
                # Get all shares for this session
                shares = session_repository.list_shares(session_id)

                # Filter out expired shares and format response
                active_shares = []
                for share in shares:
                    expires_at = share.get("expires_at")
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at)

                    is_active = not SessionShareService.is_expired(expires_at)

                    active_shares.append(
                        {
                            "token": share.get("token"),
                            "expires_at": expires_at.isoformat()
                            if isinstance(expires_at, datetime)
                            else expires_at,
                            "created_at": share.get("created_at"),
                            "is_active": is_active,
                        }
                    )

                return {
                    "session_id": session_id,
                    "shares": active_shares,
                    "total": len(active_shares),
                }

            finally:
                db.close()

        except HTTPException:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to list shares for session {session_id}: {e}",
                session_id=session_id,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to list shares",
            ) from e


@router.delete(
    "/{session_id}/share/{token}",
    summary="Revoke a share link",
    description="Revoke/delete a share link. Returns 204 No Content on success.",
    responses={
        204: {"description": "Share revoked successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session or share not found", "model": ErrorResponse},
    },
)
@handle_api_errors("revoke share")
async def revoke_share(
    session_id: str,
    token: str,
    session_data: VerifiedSession,
) -> None:
    """Revoke/delete a share link.

    Args:
        session_id: Session identifier
        token: Share token to revoke
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: If session not found or user lacks permission
    """
    with track_api_call("sessions.revoke_share", "DELETE"):
        try:
            # Validate session ID format
            session_id = validate_session_id(session_id)

            # Unpack verified session data
            user_id, metadata = session_data

            # Get database session
            from bo1.state.database import SessionLocal

            db = SessionLocal()
            try:
                # Revoke the share
                success = session_repository.revoke_share(session_id, token)

                if not success:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Share token not found for session {session_id}",
                    )

                logger.info(f"Revoked share {token} for session {session_id}")

                # Return 204 No Content
                from fastapi.responses import Response

                return Response(status_code=204)

            finally:
                db.close()

        except HTTPException:
            raise
        except Exception as e:
            log_error(
                logger,
                ErrorCode.SERVICE_EXECUTION_ERROR,
                f"Failed to revoke share {token}: {e}",
                session_id=session_id,
                token=token,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to revoke share",
            ) from e


# =========================================================================
# Session-Project Linking
# =========================================================================


@router.get(
    "/{session_id}/projects",
    summary="Get session's linked projects",
    description="Get all projects linked to this session",
    responses={
        200: {"description": "Projects retrieved successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("get session projects")
async def get_session_projects(
    session_id: str,
    session_data: VerifiedSession,
) -> dict[str, Any]:
    """Get all projects linked to a session.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        SessionProjectsResponse with linked projects
    """
    from backend.api.models import SessionProjectsResponse

    with track_api_call("sessions.get_projects", "GET"):
        session_id = validate_session_id(session_id)
        user_id, _ = session_data

        projects = session_repository.get_session_projects(session_id)

        return SessionProjectsResponse(
            session_id=session_id,
            projects=[
                {
                    "project_id": str(p["project_id"]),
                    "name": p["name"],
                    "description": p.get("description"),
                    "status": p["project_status"],
                    "progress_percent": p.get("progress_percent", 0),
                    "relationship": p["relationship"],
                    "linked_at": (p["linked_at"].isoformat() if p.get("linked_at") else None),
                }
                for p in projects
            ],
        )


@router.get(
    "/{session_id}/available-projects",
    summary="Get projects available for linking",
    description="Get projects that can be linked to this session (same workspace)",
    responses={
        200: {"description": "Available projects retrieved successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("get available projects")
async def get_available_projects(
    session_id: str,
    session_data: VerifiedSession,
) -> dict[str, Any]:
    """Get projects available for linking to a session (same workspace).

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        AvailableProjectsResponse with available projects
    """
    from backend.api.models import AvailableProjectsResponse

    with track_api_call("sessions.get_available_projects", "GET"):
        session_id = validate_session_id(session_id)
        user_id, _ = session_data

        projects = session_repository.get_available_projects_for_session(
            session_id=session_id,
            user_id=user_id,
        )

        return AvailableProjectsResponse(
            session_id=session_id,
            projects=[
                {
                    "id": str(p["id"]),
                    "name": p["name"],
                    "description": p.get("description"),
                    "status": p["status"],
                    "progress_percent": p.get("progress_percent", 0),
                    "is_linked": p.get("is_linked", False),
                }
                for p in projects
            ],
        )


@router.post(
    "/{session_id}/projects",
    status_code=201,
    summary="Link projects to session",
    description="Link one or more projects to this session",
    responses={
        201: {"description": "Projects linked successfully"},
        400: {"description": "Workspace mismatch or invalid project", "model": ErrorResponse},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("link projects to session")
async def link_projects_to_session(
    session_id: str,
    request: Request,
    session_data: VerifiedSession,
) -> dict[str, Any]:
    """Link projects to a session.

    Args:
        session_id: Session identifier
        request: Request with project_ids and relationship
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        Dict with session_id and linked project count
    """
    from backend.api.models import SessionProjectLink

    with track_api_call("sessions.link_projects", "POST"):
        session_id = validate_session_id(session_id)
        user_id, _ = session_data

        # Parse request body
        body = await request.json()
        link_request = SessionProjectLink(**body)

        # Validate workspace match
        is_valid, mismatched = session_repository.validate_project_workspace_match(
            session_id=session_id,
            project_ids=link_request.project_ids,
        )
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Projects {mismatched} are in a different workspace than session",
            )

        # Link projects
        try:
            results = session_repository.link_session_to_projects(
                session_id=session_id,
                project_ids=link_request.project_ids,
                relationship=link_request.relationship,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

        return {
            "session_id": session_id,
            "linked_count": len(results),
            "project_ids": link_request.project_ids,
        }


@router.delete(
    "/{session_id}/projects/{project_id}",
    status_code=204,
    summary="Unlink project from session",
    description="Remove a project link from this session",
    responses={
        204: {"description": "Project unlinked successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session or link not found", "model": ErrorResponse},
    },
)
@handle_api_errors("unlink project from session")
async def unlink_project_from_session(
    session_id: str,
    project_id: str,
    session_data: VerifiedSession,
) -> None:
    """Unlink a project from a session.

    Args:
        session_id: Session identifier
        project_id: Project UUID to unlink
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        None (204 No Content)
    """
    from fastapi.responses import Response

    with track_api_call("sessions.unlink_project", "DELETE"):
        session_id = validate_session_id(session_id)
        user_id, _ = session_data

        success = session_repository.unlink_session_from_project(
            session_id=session_id,
            project_id=project_id,
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Project {project_id} not linked to session {session_id}",
            )

        return Response(status_code=204)


# =========================================================================
# Project Suggestions
# =========================================================================


@router.get(
    "/{session_id}/suggest-projects",
    summary="Get project suggestions from meeting",
    description="Analyze meeting and suggest potential projects to create",
    responses={
        200: {"description": "Suggestions retrieved successfully"},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("suggest projects")
async def suggest_projects(
    session_id: str,
    session_data: VerifiedSession,
    min_confidence: float = Query(0.6, ge=0.0, le=1.0, description="Minimum confidence threshold"),
) -> dict[str, Any]:
    """Get project suggestions from a completed meeting.

    Analyzes the meeting's problem statement and resulting actions
    to suggest potential projects that could be created.

    Args:
        session_id: Session identifier
        session_data: Verified session (user_id, metadata) from dependency
        min_confidence: Minimum confidence for suggestions (default 0.6)

    Returns:
        Dict with suggestions list
    """
    from backend.services.project_suggester import suggest_projects_from_session

    with track_api_call("sessions.suggest_projects", "GET"):
        session_id = validate_session_id(session_id)
        user_id, metadata = session_data

        # Check session is completed (suggestions only make sense for finished meetings)
        session = session_repository.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.get("status") not in ("completed", "terminated"):
            raise HTTPException(
                status_code=400,
                detail="Project suggestions are only available for completed meetings",
            )

        suggestions = await suggest_projects_from_session(
            session_id=session_id,
            min_confidence=min_confidence,
        )

        return {
            "session_id": session_id,
            "suggestions": [
                {
                    "name": s.name,
                    "description": s.description,
                    "action_ids": s.action_ids,
                    "confidence": s.confidence,
                    "rationale": s.rationale,
                }
                for s in suggestions
            ],
        }


@router.post(
    "/{session_id}/create-suggested-project",
    status_code=201,
    summary="Create project from suggestion",
    description="Create a project from a suggestion and assign actions",
    responses={
        201: {"description": "Project created successfully"},
        400: {"description": "Invalid suggestion data", "model": ErrorResponse},
        403: {"description": "User does not own this session", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
@handle_api_errors("create suggested project")
async def create_suggested_project(
    session_id: str,
    request: Request,
    session_data: VerifiedSession,
) -> dict[str, Any]:
    """Create a project from a suggestion.

    Args:
        session_id: Session identifier
        request: Request with suggestion data (name, description, action_ids)
        session_data: Verified session (user_id, metadata) from dependency

    Returns:
        Created project data
    """
    from backend.services.project_suggester import (
        ProjectSuggestion,
        create_project_from_suggestion,
    )

    with track_api_call("sessions.create_suggested_project", "POST"):
        session_id = validate_session_id(session_id)
        user_id, _ = session_data

        # Parse request body
        body = await request.json()

        # Get session for workspace_id
        session = session_repository.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        workspace_id = session.get("workspace_id")

        # Create suggestion object
        suggestion = ProjectSuggestion(
            name=body.get("name", "Untitled Project"),
            description=body.get("description", ""),
            action_ids=body.get("action_ids", []),
            confidence=body.get("confidence", 1.0),
            rationale=body.get("rationale", "User-created from suggestion"),
        )

        if not suggestion.name:
            raise HTTPException(status_code=400, detail="Project name is required")

        # Create project
        project = await create_project_from_suggestion(
            session_id=session_id,
            suggestion=suggestion,
            user_id=user_id,
            workspace_id=str(workspace_id) if workspace_id else None,
        )

        return {
            "project": {
                "id": str(project["id"]),
                "name": project["name"],
                "description": project.get("description"),
                "status": project["status"],
                "progress_percent": project.get("progress_percent", 0),
                "total_actions": project.get("total_actions", 0),
            },
            "session_id": session_id,
            "action_count": len(suggestion.action_ids),
        }


# Public share endpoint is in backend/api/share.py
