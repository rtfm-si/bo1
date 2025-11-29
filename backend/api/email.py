"""Email service using Resend for transactional emails.

Handles:
- Waitlist approval notifications
- Welcome emails for beta users
"""

import logging

import resend

from bo1.config import get_settings

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

    except Exception as e:
        logger.error(f"Failed to send beta welcome email to {email}: {e}")
        return None
