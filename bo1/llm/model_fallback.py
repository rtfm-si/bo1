"""Within-provider model fallback support.

This module provides fallback model selection when the primary model
is unavailable (e.g., 529 overloaded errors).
"""

import logging

from bo1.config import get_settings

logger = logging.getLogger(__name__)


def get_fallback_model(provider: str, current_model: str) -> str | None:
    """Get the next fallback model for a provider.

    Args:
        provider: The LLM provider ('anthropic' or 'openai')
        current_model: The model that failed

    Returns:
        Next fallback model in chain, or None if exhausted
    """
    settings = get_settings()
    if not settings.llm_model_fallback_enabled:
        return None

    if provider == "anthropic":
        chain = settings.llm_anthropic_fallback_chain
    elif provider == "openai":
        chain = settings.llm_openai_fallback_chain
    else:
        return None

    if not chain:
        return None

    # If current model is in chain, return next; otherwise return first
    try:
        idx = chain.index(current_model)
        # Return next in chain if exists
        if idx + 1 < len(chain):
            return chain[idx + 1]
        return None  # Exhausted
    except ValueError:
        # Current model not in chain - return first fallback
        return chain[0] if chain else None


def is_model_fallback_eligible(status_code: int | None) -> bool:
    """Check if an error status code is eligible for model fallback.

    Only certain errors should trigger model fallback (vs provider fallback):
    - 529: Overloaded (model-specific capacity)
    - 503: Service Unavailable (may be model-specific)

    Args:
        status_code: HTTP status code from the error

    Returns:
        True if model fallback should be attempted
    """
    if status_code is None:
        return False
    return status_code in (529, 503)


def emit_model_fallback_event(
    session_id: str | None,
    provider: str,
    from_model: str,
    to_model: str,
) -> None:
    """Emit SSE event notifying client of model fallback.

    This function safely attempts to publish a model_fallback event
    to the session's SSE stream. If Redis/EventPublisher is unavailable,
    it logs a warning and continues (non-blocking).

    Args:
        session_id: Session identifier (None if not in session context)
        provider: LLM provider name
        from_model: Original model that was overloaded
        to_model: Fallback model being used
    """
    if not session_id:
        return

    try:
        # Import here to avoid circular imports
        from backend.api.dependencies import get_event_publisher

        publisher = get_event_publisher()
        publisher.publish_event(
            session_id=session_id,
            event_type="model_fallback",
            data={
                "provider": provider,
                "from_model": from_model,
                "to_model": to_model,
                "message": "Using backup AI model for faster response",
            },
        )
    except Exception as e:
        # Non-blocking - don't fail the LLM call if event publish fails
        logger.warning(f"Failed to emit model_fallback event: {e}")
