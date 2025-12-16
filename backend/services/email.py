"""Email service using Resend for transactional emails.

Provides:
- Async email sending with retries
- Structured logging for sent/failed emails
- Unsubscribe token generation/validation
"""

import hashlib
import hmac
import logging
import time
from typing import Any

import resend

from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0


class EmailError(Exception):
    """Raised when email sending fails after retries."""

    pass


def _get_resend_client() -> bool:
    """Initialize Resend client with API key.

    Returns:
        True if client initialized successfully, False otherwise.
    """
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, emails will not be sent")
        return False
    # Log key prefix for debugging (first 8 chars only, safe to log)
    key_prefix = settings.resend_api_key[:8] if len(settings.resend_api_key) >= 8 else "***"
    logger.debug(f"Resend API key configured: {key_prefix}...")
    resend.api_key = settings.resend_api_key
    return True


def send_email(
    to: str | list[str],
    subject: str,
    html: str,
    text: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
    tags: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    """Send an email via Resend with retry logic.

    Args:
        to: Recipient email(s)
        subject: Email subject
        html: HTML email body
        text: Plain text email body (optional, auto-generated if not provided)
        from_address: Sender address (defaults to config EMAIL_FROM_ADDRESS)
        reply_to: Reply-to address (optional)
        tags: Resend tags for tracking (optional)

    Returns:
        Resend API response dict on success, None on failure

    Raises:
        EmailError: If email fails after all retries
    """
    if not _get_resend_client():
        logger.info(f"Email not sent (no API key): to={to}, subject={subject}")
        return None

    settings = get_settings()

    # Build sender address
    if not from_address:
        from_name = getattr(settings, "email_from_name", "Board of One")
        from_addr = getattr(settings, "email_from_address", "noreply@boardof.one")
        from_address = f"{from_name} <{from_addr}>"

    # Ensure 'to' is a list
    recipients = [to] if isinstance(to, str) else to

    # Build email params
    params: dict[str, Any] = {
        "from": from_address,
        "to": recipients,
        "subject": subject,
        "html": html,
    }

    if text:
        params["text"] = text
    if reply_to:
        params["reply_to"] = reply_to
    if tags:
        params["tags"] = tags

    # Send with retries
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = resend.Emails.send(params)
            logger.info(
                f"Email sent: to={recipients}, subject={subject}, "
                f"id={response.get('id', 'unknown')}"
            )
            return response
        except Exception as e:
            last_error = e
            logger.warning(
                f"Email send attempt {attempt}/{MAX_RETRIES} failed: {e}",
                extra={
                    "to": recipients,
                    "subject": subject,
                    "error_type": type(e).__name__,
                    "error_detail": str(e),
                },
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)  # Exponential backoff

    # All retries exhausted
    logger.error(
        f"Email send failed after {MAX_RETRIES} attempts: to={recipients}, "
        f"subject={subject}, error={last_error}"
    )
    raise EmailError(f"Failed to send email after {MAX_RETRIES} attempts: {last_error}")


def send_email_async(
    to: str | list[str],
    subject: str,
    html: str,
    text: str | None = None,
    from_address: str | None = None,
) -> None:
    """Fire-and-forget email sending (logs errors but doesn't raise).

    Use this for non-critical emails like welcome messages where delivery
    failure shouldn't block the main flow.

    Args:
        to: Recipient email(s)
        subject: Email subject
        html: HTML email body
        text: Plain text email body (optional)
        from_address: Sender address (optional)
    """
    try:
        send_email(to=to, subject=subject, html=html, text=text, from_address=from_address)
    except EmailError as e:
        logger.error(f"Async email failed (non-blocking): {e}")


# =============================================================================
# Unsubscribe Token Management
# =============================================================================


def _get_unsubscribe_secret() -> bytes:
    """Get secret key for unsubscribe token signing."""
    settings = get_settings()
    # Use Resend API key as secret (or a dedicated secret if configured)
    secret = settings.resend_api_key or "default-dev-secret"
    return secret.encode("utf-8")


def generate_unsubscribe_token(user_id: str, email_type: str = "all") -> str:
    """Generate a signed unsubscribe token.

    Args:
        user_id: User identifier
        email_type: Type of emails to unsubscribe from ('all', 'reminders', 'digest')

    Returns:
        Signed token string (hex-encoded)
    """
    payload = f"{user_id}:{email_type}"
    signature = hmac.new(
        _get_unsubscribe_secret(),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def validate_unsubscribe_token(token: str) -> tuple[str, str] | None:
    """Validate an unsubscribe token and extract user_id and email_type.

    Args:
        token: Token string from unsubscribe link

    Returns:
        Tuple of (user_id, email_type) if valid, None if invalid
    """
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None

        payload, signature = parts
        expected_signature = hmac.new(
            _get_unsubscribe_secret(),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None

        user_parts = payload.split(":", 1)
        if len(user_parts) != 2:
            return None

        return user_parts[0], user_parts[1]
    except Exception:
        return None


def get_unsubscribe_url(user_id: str, email_type: str = "all") -> str:
    """Generate full unsubscribe URL for email footer.

    Args:
        user_id: User identifier
        email_type: Type of emails to unsubscribe from

    Returns:
        Full unsubscribe URL
    """
    settings = get_settings()
    api_domain = settings.supertokens_api_domain
    token = generate_unsubscribe_token(user_id, email_type)
    return f"{api_domain}/api/v1/email/unsubscribe?token={token}"
