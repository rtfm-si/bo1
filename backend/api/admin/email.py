"""Admin API endpoints for sending emails to users.

Provides:
- POST /api/admin/users/{user_id}/send-email - Send branded email to user
"""

from enum import Enum

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.api.admin.helpers import AdminQueryService, AdminUserService
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors, http_error
from backend.services.email import send_email
from backend.services.email_templates import render_admin_custom_email, render_welcome_email
from bo1.logging.errors import ErrorCode, log_error
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Email"])


class EmailTemplateType(str, Enum):
    """Available email template types for admin-sent emails."""

    welcome = "welcome"
    custom = "custom"


class SendEmailRequest(BaseModel):
    """Request model for sending admin email.

    Attributes:
        template_type: Type of email template to use
        subject: Custom subject (required for custom template)
        body: Custom body (required for custom template)
    """

    template_type: EmailTemplateType = Field(
        ...,
        description="Type of email template",
        examples=["welcome", "custom"],
    )
    subject: str | None = Field(
        None,
        description="Custom subject (required for custom template)",
        max_length=200,
        examples=["Important update about your account"],
    )
    body: str | None = Field(
        None,
        description="Custom body (required for custom template)",
        max_length=5000,
        examples=["Hi there, we wanted to let you know..."],
    )


class SendEmailResponse(BaseModel):
    """Response model for send email operation.

    Attributes:
        user_id: Target user ID
        email: Target email address
        template_type: Template used
        subject: Email subject
        sent: Whether email was sent successfully
        message: Human-readable message
    """

    user_id: str = Field(..., description="Target user ID")
    email: str = Field(..., description="Target email address")
    template_type: str = Field(..., description="Template used")
    subject: str = Field(..., description="Email subject")
    sent: bool = Field(..., description="Whether email sent successfully")
    message: str = Field(..., description="Human-readable message")


@router.post(
    "/users/{user_id}/send-email",
    response_model=SendEmailResponse,
    summary="Send email to user",
    description="Send a branded email to a user using available templates.",
    responses={
        200: {"description": "Email sent successfully"},
        400: {"description": "Invalid request (missing required fields)", "model": ErrorResponse},
        401: {"description": "Admin authentication required", "model": ErrorResponse},
        403: {"description": "Insufficient permissions", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Email send failed", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("send admin email")
async def send_user_email(
    request: Request,
    user_id: str,
    body: SendEmailRequest,
    admin_id: str = Depends(require_admin_any),
) -> SendEmailResponse:
    """Send a branded email to a user."""
    # Validate custom template requirements
    if body.template_type == EmailTemplateType.custom:
        if not body.subject or not body.body:
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "subject and body are required for custom template",
                status=400,
            )

    # Check if user exists and get email
    if not AdminQueryService.user_exists(user_id):
        raise http_error(ErrorCode.API_NOT_FOUND, f"User not found: {user_id}", status=404)

    # Get user email
    from backend.api.utils.db_helpers import execute_query

    row = execute_query(
        "SELECT email, COALESCE(email_preferences->>'name', '') as name FROM users WHERE id = %s",
        (user_id,),
        fetch="one",
    )

    if not row or not row.get("email"):
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "User does not have a valid email address", status=400
        )

    user_email = row["email"]
    user_name = row.get("name") or None

    # Check for placeholder email
    if user_email.endswith("@placeholder.local"):
        raise http_error(
            ErrorCode.VALIDATION_ERROR, "Cannot send email to placeholder address", status=400
        )

    # Render email based on template
    if body.template_type == EmailTemplateType.welcome:
        html, text = render_welcome_email(user_name=user_name, user_id=user_id)
        subject = "Welcome to Board of One"
    else:  # custom
        html, text = render_admin_custom_email(
            subject=body.subject,  # type: ignore[arg-type]
            body=body.body,  # type: ignore[arg-type]
            user_name=user_name,
        )
        subject = body.subject  # type: ignore[assignment]

    # Send email
    try:
        result = send_email(
            to=user_email,
            subject=subject,
            html=html,
            text=text,
            tags=[
                {"name": "email_type", "value": f"admin_{body.template_type.value}"},
                {"name": "sent_by", "value": admin_id},
            ],
        )
        sent = result is not None
    except Exception as e:
        log_error(
            logger,
            ErrorCode.EXT_EMAIL_ERROR,
            f"Failed to send admin email: {e}",
            exc_info=True,
            user_id=user_id,
            admin_id=admin_id,
        )
        sent = False

    # Log admin action (audit trail)
    AdminUserService.log_admin_action(
        admin_id=admin_id,
        action="email_sent",
        resource_type="user",
        resource_id=user_id,
        details={
            "template_type": body.template_type.value,
            "subject": subject,
            "sent": sent,
        },
    )

    logger.info(
        f"Admin {admin_id}: Sent {body.template_type.value} email to {user_id} "
        f"({user_email}), success={sent}"
    )

    return SendEmailResponse(
        user_id=user_id,
        email=user_email,
        template_type=body.template_type.value,
        subject=subject,
        sent=sent,
        message=f"Email {'sent' if sent else 'failed to send'} to {user_email}",
    )
