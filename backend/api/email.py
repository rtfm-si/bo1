"""Email service and API endpoints using Resend for transactional emails.

Handles:
- Waitlist approval notifications
- Welcome emails for beta users
- Email preference management
- Unsubscribe handling
"""

import json
import logging

import resend
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

from backend.api.middleware.rate_limit import AUTH_RATE_LIMIT, limiter
from backend.api.utils.errors import handle_api_errors
from backend.services.email import validate_unsubscribe_token
from bo1.config import get_settings
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Brand colors from logo.svg
BRAND_COLOR = "#00C3D0"  # Primary teal
BRAND_COLOR_DARK = "#03767E"  # Darker teal for gradients


def _get_resend_client() -> bool:
    """Initialize Resend with API key.

    Returns:
        True if API key is configured, False otherwise
    """
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured - emails will not be sent")
        return False
    resend.api_key = settings.resend_api_key
    return True


def _get_beta_welcome_html(email: str) -> str:
    """Generate branded HTML email for beta welcome.

    Args:
        email: Recipient email address

    Returns:
        HTML string for the email body
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Board of One Beta</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse;">
                    <!-- Header with Logo -->
                    <tr>
                        <td align="center" style="padding: 0 0 32px 0;">
                            <div style="width: 80px; height: 80px; background: linear-gradient(180deg, {BRAND_COLOR} 0%, {BRAND_COLOR_DARK} 100%); border-radius: 16px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                                <span style="color: white; font-size: 32px; font-weight: bold;">B1</span>
                            </div>
                        </td>
                    </tr>

                    <!-- Main Card -->
                    <tr>
                        <td style="background-color: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                            <!-- Accent Bar -->
                            <div style="height: 4px; background: linear-gradient(90deg, {BRAND_COLOR} 0%, {BRAND_COLOR_DARK} 100%); border-radius: 16px 16px 0 0;"></div>

                            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 40px 40px 32px 40px;">
                                        <h1 style="margin: 0 0 24px 0; font-size: 28px; font-weight: 600; color: #1a1a1a; line-height: 1.3;">
                                            You're in! Welcome to Board of One
                                        </h1>

                                        <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #4a4a4a;">
                                            Great news - your request for beta access has been approved!
                                        </p>

                                        <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #4a4a4a;">
                                            Board of One is a AI-powered strategic advisor that assembles expert panels to deliberate on your toughest business decisions. Get multiple expert perspectives, structured debate, and actionable recommendations.
                                        </p>

                                        <p style="margin: 0 0 32px 0; font-size: 16px; line-height: 1.6; color: #4a4a4a;">
                                            Ready to try it out? Sign up with this email address (<strong>{email}</strong>) to get started.
                                        </p>

                                        <!-- CTA Button -->
                                        <table role="presentation" style="border-collapse: collapse;">
                                            <tr>
                                                <td align="center" style="border-radius: 8px; background: linear-gradient(180deg, {BRAND_COLOR} 0%, {BRAND_COLOR_DARK} 100%);">
                                                    <a href="https://boardof.one/auth" style="display: inline-block; padding: 16px 32px; font-size: 16px; font-weight: 600; color: white; text-decoration: none; border-radius: 8px;">
                                                        Get Started
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center" style="padding: 32px 20px;">
                            <p style="margin: 0 0 8px 0; font-size: 14px; color: #888888;">
                                Questions? Just reply to this email - we'd love to hear from you.
                            </p>
                            <p style="margin: 0; font-size: 14px; color: #888888;">
                                Board of One &bull; AI-Powered Strategic Decisions
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def _get_beta_welcome_text(email: str) -> str:
    """Generate plain text email for beta welcome.

    Args:
        email: Recipient email address

    Returns:
        Plain text string for the email body
    """
    return f"""You're in! Welcome to Board of One

Great news - your request for beta access has been approved!

Board of One is an AI-powered strategic advisor that assembles expert panels to deliberate on your toughest business decisions. Get multiple expert perspectives, structured debate, and actionable recommendations.

Ready to try it out? Sign up with this email address ({email}) to get started:

https://boardof.one/auth

Questions? Just reply to this email - we'd love to hear from you.

- The Board of One Team
"""


def send_beta_welcome_email(email: str) -> dict | None:
    """Send beta welcome email to approved waitlist user.

    Args:
        email: Recipient email address

    Returns:
        Resend API response dict on success, None on failure

    Example:
        >>> result = send_beta_welcome_email("alice@example.com")
        >>> if result:
        ...     print(f"Email sent: {result['id']}")
    """
    if not _get_resend_client():
        logger.warning(f"Skipping email to {email} - Resend not configured")
        return None

    try:
        result = resend.Emails.send(
            {
                "from": "Board of One <waitlist@boardof.one>",
                "to": [email],
                "subject": "You're in! Welcome to Board of One beta",
                "html": _get_beta_welcome_html(email),
                "text": _get_beta_welcome_text(email),
                "reply_to": "si@boardof.one",
            }
        )

        logger.info(f"Beta welcome email sent to {email}: {result.get('id', 'unknown')}")
        return result

    except resend.exceptions.ResendError as e:
        logger.error(f"Resend API error sending email to {email}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error sending beta welcome email to {email}: {e}", exc_info=True)
        return None


# =============================================================================
# Email Preferences API
# =============================================================================

router = APIRouter(tags=["email"])


class EmailPreferences(BaseModel):
    """User email notification preferences."""

    meeting_emails: bool = True
    reminder_emails: bool = True
    digest_emails: bool = True


class EmailPreferencesResponse(BaseModel):
    """Response for email preferences endpoint."""

    preferences: EmailPreferences


@router.get("/v1/user/email-preferences", response_model=EmailPreferencesResponse)
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("get email preferences")
async def get_email_preferences(
    request: Request, session: SessionContainer = Depends(verify_session())
) -> EmailPreferencesResponse:
    """Get current user's email notification preferences."""
    user_id = session.get_user_id()

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT email_preferences FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()

        if row and row.get("email_preferences"):
            prefs_data = row["email_preferences"]
            prefs = EmailPreferences(**prefs_data)
        else:
            prefs = EmailPreferences()  # Defaults

        return EmailPreferencesResponse(preferences=prefs)

    except Exception as e:
        logger.error(f"Failed to get email preferences for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get email preferences") from None


@router.patch("/v1/user/email-preferences", response_model=EmailPreferencesResponse)
@limiter.limit(AUTH_RATE_LIMIT)
@handle_api_errors("update email preferences")
async def update_email_preferences(
    request: Request,
    preferences: EmailPreferences,
    session_obj: SessionContainer = Depends(verify_session()),
) -> EmailPreferencesResponse:
    """Update current user's email notification preferences."""
    user_id = session_obj.get_user_id()

    try:
        prefs_json = json.dumps(preferences.model_dump())

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET email_preferences = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING email_preferences
                    """,
                    (prefs_json, user_id),
                )
                row = cur.fetchone()

        if row:
            return EmailPreferencesResponse(preferences=preferences)
        else:
            raise HTTPException(status_code=404, detail="User not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update email preferences for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update email preferences") from None


@router.get("/v1/email/unsubscribe", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def unsubscribe(
    request: Request,
    token: str = Query(..., description="Signed unsubscribe token"),
) -> HTMLResponse:
    """Handle email unsubscribe link.

    Validates the token and updates user's email preferences.
    Returns an HTML page confirming the unsubscribe action.
    """
    # Validate token
    result = validate_unsubscribe_token(token)
    if not result:
        logger.warning(f"Invalid unsubscribe token: {token[:20]}...")
        return HTMLResponse(
            content=_render_unsubscribe_page(
                success=False,
                message="Invalid or expired unsubscribe link. Please try again from a recent email.",
            ),
            status_code=400,
        )

    user_id, email_type = result

    try:
        # Update preferences based on email_type
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get current preferences
                cur.execute(
                    "SELECT email_preferences FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                prefs = (row.get("email_preferences") or {}) if row else {}

                # Update based on type
                if email_type == "all":
                    prefs["meeting_emails"] = False
                    prefs["reminder_emails"] = False
                    prefs["digest_emails"] = False
                    message = "You have been unsubscribed from all emails."
                elif email_type == "reminders":
                    prefs["reminder_emails"] = False
                    message = "You have been unsubscribed from action reminder emails."
                elif email_type == "digest":
                    prefs["digest_emails"] = False
                    message = "You have been unsubscribed from weekly digest emails."
                else:
                    prefs[f"{email_type}_emails"] = False
                    message = f"You have been unsubscribed from {email_type} emails."

                # Save updated preferences
                cur.execute(
                    """
                    UPDATE users
                    SET email_preferences = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (json.dumps(prefs), user_id),
                )

        logger.info(f"User {user_id} unsubscribed from {email_type} emails")
        return HTMLResponse(
            content=_render_unsubscribe_page(success=True, message=message),
            status_code=200,
        )

    except Exception as e:
        logger.error(f"Failed to unsubscribe user {user_id}: {e}")
        return HTMLResponse(
            content=_render_unsubscribe_page(
                success=False,
                message="An error occurred. Please try again later.",
            ),
            status_code=500,
        )


def _render_unsubscribe_page(success: bool, message: str) -> str:
    """Render simple HTML page for unsubscribe confirmation."""
    status_color = "#10b981" if success else "#ef4444"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unsubscribe - Board of One</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f5f5f5; }}
.container {{ max-width: 500px; margin: 80px auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
.icon {{ width: 60px; height: 60px; border-radius: 50%; background: {status_color}; color: white; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 20px; font-size: 30px; }}
h1 {{ margin: 0 0 10px 0; font-size: 24px; }}
p {{ color: #666; margin: 0 0 20px 0; }}
a {{ color: #2563eb; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">
<div class="icon">{"&#10003;" if success else "&#10007;"}</div>
<h1>{"Success" if success else "Error"}</h1>
<p>{message}</p>
<p><a href="https://boardof.one/settings">Manage email preferences</a></p>
</div>
</body>
</html>"""
