"""FastAPI router for pending context update endpoints.

Provides:
- GET /api/v1/context/pending-updates - List pending suggestions
- POST /api/v1/context/pending-updates/{id}/approve - Approve a suggestion
- DELETE /api/v1/context/pending-updates/{id} - Dismiss a suggestion
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends

from backend.api.context.models import (
    ApproveUpdateResponse,
    ContextUpdateSource,
    ContextUpdateSuggestion,
    PendingUpdatesResponse,
)
from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from backend.api.utils.responses import (
    ERROR_403_RESPONSE,
    ERROR_404_RESPONSE,
)
from bo1.logging import ErrorCode
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["context"])


@router.get(
    "/v1/context/pending-updates",
    response_model=PendingUpdatesResponse,
    summary="List pending context update suggestions",
    description="""
    Get pending context update suggestions that require user approval.

    These are updates extracted with < 80% confidence from:
    - Clarification answers during meetings
    - Problem statements when creating meetings
    - Action completion/cancellation notes

    **Use Cases:**
    - Display "Suggested Updates" section in Settings > Context
    - Allow users to review and approve/dismiss detected changes
    """,
    responses={403: ERROR_403_RESPONSE},
)
@handle_api_errors("get pending updates")
async def get_pending_updates(
    user: dict[str, Any] = Depends(get_current_user),
) -> PendingUpdatesResponse:
    """Get pending context update suggestions."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        return PendingUpdatesResponse(suggestions=[], count=0)

    pending = context_data.get("pending_updates", [])
    suggestions = []

    for item in pending:
        try:
            suggestions.append(
                ContextUpdateSuggestion(
                    id=item.get("id", ""),
                    field_name=item.get("field_name", ""),
                    new_value=item.get("new_value", ""),
                    current_value=item.get("current_value"),
                    confidence=item.get("confidence", 0.5),
                    source_type=ContextUpdateSource(item.get("source_type", "clarification")),
                    source_text=item.get("source_text", ""),
                    extracted_at=datetime.fromisoformat(
                        item.get("extracted_at", "2025-01-01T00:00:00")
                    ),
                    session_id=item.get("session_id"),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to parse pending update: {e}")
            continue

    return PendingUpdatesResponse(suggestions=suggestions, count=len(suggestions))


@router.post(
    "/v1/context/pending-updates/{suggestion_id}/approve",
    response_model=ApproveUpdateResponse,
    summary="Approve a pending context update",
    description="""
    Apply a pending context update suggestion.

    This will:
    1. Update the specified context field with the suggested value
    2. Record the change in metric history for trend tracking
    3. Remove the suggestion from pending updates
    """,
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("approve pending update")
async def approve_pending_update(
    suggestion_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> ApproveUpdateResponse:
    """Approve and apply a pending context update."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    pending = context_data.get("pending_updates", [])

    # Find the suggestion
    suggestion = None
    suggestion_idx = None
    for idx, item in enumerate(pending):
        if item.get("id") == suggestion_id:
            suggestion = item
            suggestion_idx = idx
            break

    if suggestion is None:
        raise http_error(ErrorCode.API_NOT_FOUND, "Pending update not found", status=404)

    # Apply the update
    field_name = suggestion.get("field_name", "")
    new_value = suggestion.get("new_value", "")

    context_data[field_name] = new_value

    # Track in metric history
    metric_history = context_data.get("context_metric_history", {})
    if field_name not in metric_history:
        metric_history[field_name] = []
    metric_history[field_name].insert(
        0,
        {
            "value": new_value,
            "recorded_at": datetime.now(UTC).isoformat(),
            "source_type": suggestion.get("source_type", "clarification"),
            "source_id": suggestion.get("session_id"),
        },
    )
    metric_history[field_name] = metric_history[field_name][:10]
    context_data["context_metric_history"] = metric_history

    # Remove from pending
    pending.pop(suggestion_idx)
    context_data["pending_updates"] = pending

    # Save
    user_repository.save_context(user_id, context_data)
    logger.info(f"User {user_id} approved pending update: {field_name}={new_value}")

    return ApproveUpdateResponse(
        success=True,
        field_name=field_name,
        new_value=new_value,
    )


@router.delete(
    "/v1/context/pending-updates/{suggestion_id}",
    response_model=dict[str, str],
    summary="Dismiss a pending context update",
    description="""
    Dismiss a pending context update suggestion without applying it.

    The suggestion is removed from the pending list and will not be shown again.
    """,
    responses={403: ERROR_403_RESPONSE, 404: ERROR_404_RESPONSE},
)
@handle_api_errors("dismiss pending update")
async def dismiss_pending_update(
    suggestion_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    """Dismiss a pending context update without applying it."""
    user_id = extract_user_id(user)

    context_data = user_repository.get_context(user_id)
    if not context_data:
        raise http_error(ErrorCode.API_NOT_FOUND, "No context found", status=404)

    pending = context_data.get("pending_updates", [])

    # Find and remove the suggestion
    new_pending = [item for item in pending if item.get("id") != suggestion_id]

    if len(new_pending) == len(pending):
        raise http_error(ErrorCode.API_NOT_FOUND, "Pending update not found", status=404)

    context_data["pending_updates"] = new_pending
    user_repository.save_context(user_id, context_data)
    logger.info(f"User {user_id} dismissed pending update: {suggestion_id}")

    return {"status": "dismissed"}
