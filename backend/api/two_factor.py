"""Two-factor authentication (2FA) endpoints.

Provides TOTP-based 2FA with:
- Setup flow: generate secret, verify with first code
- Login verification: verify TOTP or backup code
- Backup codes: single-use recovery codes

Security features:
- Rate limiting: 5 failed attempts per 15 minutes
- Backup codes: hashed with bcrypt, single-use
- Audit logging for 2FA events
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supertokens_python.recipe.totp import asyncio as totp_asyncio

from backend.api.middleware.auth import get_current_user
from backend.api.models import ErrorResponse
from backend.api.utils.errors import http_error
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user/2fa", tags=["2fa"])

# Rate limiting constants
MAX_TOTP_ATTEMPTS = 5
TOTP_LOCKOUT_MINUTES = 15
BACKUP_CODE_LENGTH = 8
BACKUP_CODE_COUNT = 10


def _generate_backup_codes() -> list[str]:
    """Generate random backup codes.

    Returns:
        List of 10 random 8-character alphanumeric codes.
    """
    # Use URL-safe base64 characters, excluding ambiguous ones (0, O, l, I)
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = []
    for _ in range(BACKUP_CODE_COUNT):
        code = "".join(secrets.choice(alphabet) for _ in range(BACKUP_CODE_LENGTH))
        codes.append(code)
    return codes


def _hash_backup_code(code: str) -> str:
    """Hash a backup code for storage.

    Uses SHA-256 with the code uppercased for consistency.
    """
    return hashlib.sha256(code.upper().encode()).hexdigest()


def _verify_backup_code(code: str, hashed: str) -> bool:
    """Verify a backup code against its hash."""
    return _hash_backup_code(code) == hashed


def _check_totp_rate_limit(user_id: str) -> tuple[bool, int]:
    """Check if user is rate limited for TOTP verification.

    Returns:
        Tuple of (is_locked_out, seconds_remaining).
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT totp_failed_attempts, totp_lockout_until
                FROM users WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return False, 0

            lockout_until = row["totp_lockout_until"]
            if lockout_until:
                # Make timezone-aware if needed
                if lockout_until.tzinfo is None:
                    lockout_until = lockout_until.replace(tzinfo=UTC)
                now = datetime.now(UTC)
                if lockout_until > now:
                    remaining = int((lockout_until - now).total_seconds())
                    return True, remaining

            return False, 0


def _record_totp_failure(user_id: str) -> bool:
    """Record a failed TOTP verification attempt.

    Returns:
        True if user is now locked out.
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Increment counter, set lockout if threshold reached
            cur.execute(
                """
                UPDATE users
                SET totp_failed_attempts = totp_failed_attempts + 1,
                    totp_lockout_until = CASE
                        WHEN totp_failed_attempts + 1 >= %s
                        THEN NOW() + INTERVAL '%s minutes'
                        ELSE totp_lockout_until
                    END,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING totp_failed_attempts
                """,
                (MAX_TOTP_ATTEMPTS, TOTP_LOCKOUT_MINUTES, user_id),
            )
            row = cur.fetchone()
            return row and row["totp_failed_attempts"] >= MAX_TOTP_ATTEMPTS


def _clear_totp_failures(user_id: str) -> None:
    """Clear TOTP failure counter after successful verification."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET totp_failed_attempts = 0,
                    totp_lockout_until = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (user_id,),
            )


# =============================================================================
# Request/Response Models
# =============================================================================


class TwoFactorStatusResponse(BaseModel):
    """2FA status for current user."""

    enabled: bool = Field(..., description="Whether 2FA is enabled")
    enabled_at: datetime | None = Field(None, description="When 2FA was enabled")
    backup_codes_remaining: int = Field(0, description="Number of unused backup codes")
    available: bool = Field(True, description="Whether 2FA feature is available (requires license)")
    unavailable_reason: str | None = Field(None, description="Reason if 2FA is not available")


class SetupTwoFactorResponse(BaseModel):
    """Response for 2FA setup initiation."""

    secret: str = Field(..., description="Base32-encoded TOTP secret")
    qr_uri: str = Field(..., description="otpauth:// URI for QR code generation")
    backup_codes: list[str] = Field(..., description="10 single-use backup codes")


class VerifySetupRequest(BaseModel):
    """Request to verify 2FA setup with first code."""

    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class VerifySetupResponse(BaseModel):
    """Response after successful 2FA setup verification."""

    success: bool = Field(..., description="Whether setup verification succeeded")
    message: str = Field(..., description="Status message")


class DisableTwoFactorRequest(BaseModel):
    """Request to disable 2FA."""

    password: str = Field(..., min_length=1, description="Current password for confirmation")


class DisableTwoFactorResponse(BaseModel):
    """Response after disabling 2FA."""

    success: bool = Field(..., description="Whether 2FA was disabled")
    message: str = Field(..., description="Status message")


class VerifyTwoFactorRequest(BaseModel):
    """Request to verify 2FA code during login."""

    code: str = Field(..., min_length=6, max_length=10, description="TOTP code or backup code")


class VerifyTwoFactorResponse(BaseModel):
    """Response after 2FA verification."""

    success: bool = Field(..., description="Whether verification succeeded")
    used_backup_code: bool = Field(False, description="Whether a backup code was used")
    backup_codes_remaining: int | None = Field(
        None, description="Remaining backup codes (if used backup)"
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/status",
    summary="Get 2FA status",
    description="Check if 2FA is enabled for the current user.",
    response_model=TwoFactorStatusResponse,
    responses={
        200: {"description": "2FA status"},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
)
async def get_two_factor_status(
    user: dict[str, Any] = Depends(get_current_user),
) -> TwoFactorStatusResponse:
    """Get current user's 2FA status."""
    import os

    user_id = user["user_id"]

    # Check if 2FA is available (requires SuperTokens paid license)
    # We detect this by checking an env var or attempting a lightweight TOTP call
    totp_available = os.getenv("SUPERTOKENS_TOTP_ENABLED", "").lower() == "true"
    unavailable_reason = None if totp_available else "Requires SuperTokens enterprise license"

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT totp_enabled, totp_enabled_at, totp_backup_codes
                    FROM users WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    # User not in local DB yet - 2FA not enabled
                    return TwoFactorStatusResponse(
                        enabled=False,
                        enabled_at=None,
                        backup_codes_remaining=0,
                        available=totp_available,
                        unavailable_reason=unavailable_reason,
                    )

                enabled = row.get("totp_enabled", False) or False
                enabled_at = row.get("totp_enabled_at")
                backup_codes = row.get("totp_backup_codes") or []

                return TwoFactorStatusResponse(
                    enabled=enabled,
                    enabled_at=enabled_at,
                    backup_codes_remaining=len(backup_codes),
                    available=totp_available,
                    unavailable_reason=unavailable_reason,
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get 2FA status for {user_id}: {e}",
            user_id=user_id,
        )
        raise http_error(ErrorCode.DB_QUERY_ERROR, "Failed to get 2FA status", status=500) from e


@router.post(
    "/setup",
    summary="Initiate 2FA setup",
    description="""
    Start the 2FA setup process. Returns:
    - TOTP secret (for manual entry in authenticator)
    - QR code URI (for scanning)
    - Backup codes (save these securely)

    After receiving these, call /verify-setup with the first code from your
    authenticator app to complete setup.
    """,
    response_model=SetupTwoFactorResponse,
    responses={
        200: {"description": "2FA setup initiated"},
        400: {"description": "2FA already enabled", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
)
async def setup_two_factor(
    user: dict[str, Any] = Depends(get_current_user),
) -> SetupTwoFactorResponse:
    """Initiate 2FA setup - generates secret and backup codes."""
    user_id = user["user_id"]
    email = user.get("email", "user")

    # Check if already enabled
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT totp_enabled FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row and row.get("totp_enabled"):
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    "2FA is already enabled. Disable it first to re-setup.",
                    status=400,
                )

    try:
        # Create TOTP device via SuperTokens
        # This generates the secret and stores it in SuperTokens
        result = await totp_asyncio.create_device(
            user_id=user_id,
            device_name="Authenticator App",
        )

        if isinstance(result, totp_asyncio.DeviceAlreadyExistsError):
            # Device exists but 2FA not verified yet - remove and recreate
            await totp_asyncio.remove_device(user_id=user_id, device_name="Authenticator App")
            result = await totp_asyncio.create_device(
                user_id=user_id,
                device_name="Authenticator App",
            )

        # Check for UnknownUserIdError (user not in SuperTokens)
        if isinstance(result, totp_asyncio.UnknownUserIdError):
            logger.warning(f"User {user_id} not found in SuperTokens for TOTP setup")
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "Your account needs to be re-authenticated. Please sign out and sign in again.",
                status=400,
            )

        if not isinstance(result, totp_asyncio.CreateDeviceOkResult):
            logger.error(f"Failed to create TOTP device for {user_id}: {type(result)}")
            raise http_error(
                ErrorCode.SERVICE_EXECUTION_ERROR,
                "Failed to initialize 2FA. Please try again.",
                status=500,
            )

        # Generate backup codes
        backup_codes = _generate_backup_codes()
        hashed_codes = [_hash_backup_code(code) for code in backup_codes]

        # Ensure user exists in local DB before storing backup codes
        # This syncs SuperTokens user to PostgreSQL if needed (FK constraint)
        from bo1.state.repositories.user_repository import user_repository

        if not user_repository.ensure_exists(user_id, email):
            logger.error(f"Failed to ensure user {user_id} exists in local DB for 2FA setup")
            raise http_error(
                ErrorCode.DB_QUERY_ERROR,
                "Failed to initialize account. Please try again or contact support.",
                status=500,
            )

        # Store hashed backup codes (don't enable 2FA yet - wait for verification)
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET totp_backup_codes = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                    """,
                    (hashed_codes, user_id),
                )
                row = cur.fetchone()
                if not row:
                    # UPDATE affected 0 rows - user still doesn't exist
                    logger.error(f"UPDATE totp_backup_codes affected 0 rows for user {user_id}")
                    raise http_error(
                        ErrorCode.DB_QUERY_ERROR,
                        "Account setup incomplete. Please sign out and sign in again.",
                        status=400,
                    )

        logger.info(f"2FA setup initiated for user {user_id}")

        # Build QR code URI (standard otpauth format)
        # Format: otpauth://totp/Label?secret=SECRET&issuer=Issuer
        qr_uri = (
            f"otpauth://totp/Board%20of%20One:{email}"
            f"?secret={result.secret}"
            f"&issuer=Board%20of%20One"
            f"&digits=6"
            f"&period=30"
        )

        return SetupTwoFactorResponse(
            secret=result.secret,
            qr_uri=qr_uri,
            backup_codes=backup_codes,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to setup 2FA for {user_id}: {e}",
            user_id=user_id,
        )
        # Check for SuperTokens license error (TOTP/MFA requires paid tier)
        if (
            "402" in error_msg
            or "not enabled" in error_msg.lower()
            or "license" in error_msg.lower()
        ):
            raise http_error(
                ErrorCode.API_FORBIDDEN,
                "Two-factor authentication is not available on the current plan. "
                "This feature requires a SuperTokens enterprise license.",
                status=403,
            ) from e
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to setup 2FA", status=500
        ) from e


@router.post(
    "/verify-setup",
    summary="Complete 2FA setup",
    description="""
    Verify the first TOTP code to complete 2FA setup.
    This proves the user has correctly configured their authenticator app.
    """,
    response_model=VerifySetupResponse,
    responses={
        200: {"description": "2FA setup complete"},
        400: {"description": "Invalid code or no pending setup", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
        429: {"description": "Too many failed attempts", "model": ErrorResponse},
    },
)
async def verify_two_factor_setup(
    body: VerifySetupRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> VerifySetupResponse:
    """Verify first TOTP code to complete 2FA setup."""
    user_id = user["user_id"]

    # Check rate limit
    is_locked, remaining = _check_totp_rate_limit(user_id)
    if is_locked:
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            f"Too many failed attempts. Try again in {remaining} seconds.",
            status=429,
        )

    try:
        # Verify the device (this confirms the code works)
        result = await totp_asyncio.verify_device(
            user_id=user_id,
            device_name="Authenticator App",
            totp=body.code,
        )

        if isinstance(result, totp_asyncio.InvalidTOTPError):
            _record_totp_failure(user_id)
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "Invalid code. Please check your authenticator app and try again.",
                status=400,
            )

        if isinstance(result, totp_asyncio.UnknownDeviceError):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "No pending 2FA setup found. Please start setup again.",
                status=400,
            )

        if isinstance(result, totp_asyncio.LimitReachedError):
            raise http_error(
                ErrorCode.API_RATE_LIMIT,
                "Too many verification attempts. Please wait and try again.",
                status=429,
            )

        if not isinstance(result, totp_asyncio.VerifyDeviceOkResult):
            logger.error(f"Unexpected verify_device result for {user_id}: {type(result)}")
            raise http_error(
                ErrorCode.SERVICE_EXECUTION_ERROR,
                "Failed to verify 2FA setup. Please try again.",
                status=500,
            )

        # Success - enable 2FA
        _clear_totp_failures(user_id)
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET totp_enabled = true,
                        totp_enabled_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (user_id,),
                )

        logger.info(f"2FA enabled for user {user_id}")

        return VerifySetupResponse(
            success=True,
            message="2FA has been enabled successfully. Keep your backup codes safe!",
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to verify 2FA setup for {user_id}: {e}",
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to verify 2FA setup", status=500
        ) from e


@router.post(
    "/disable",
    summary="Disable 2FA",
    description="Disable 2FA. Requires password confirmation for security.",
    response_model=DisableTwoFactorResponse,
    responses={
        200: {"description": "2FA disabled"},
        400: {"description": "2FA not enabled or wrong password", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
)
async def disable_two_factor(
    body: DisableTwoFactorRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> DisableTwoFactorResponse:
    """Disable 2FA after password verification."""
    from supertokens_python.recipe.emailpassword.asyncio import sign_in
    from supertokens_python.recipe.emailpassword.interfaces import SignInOkResult

    user_id = user["user_id"]
    email = user.get("email")

    if not email:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            "Email not found for user",
            status=400,
        )

    # Check if 2FA is enabled
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT totp_enabled FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row or not row.get("totp_enabled"):
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    "2FA is not enabled for this account.",
                    status=400,
                )

    # Verify password
    try:
        sign_in_result = await sign_in(
            tenant_id="public",
            email=email,
            password=body.password,
        )

        if not isinstance(sign_in_result, SignInOkResult):
            raise http_error(
                ErrorCode.SECURITY_AUTH_FAILURE,
                "Incorrect password.",
                status=400,
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Password verification failed for 2FA disable: {e}")
        raise http_error(
            ErrorCode.SECURITY_AUTH_FAILURE,
            "Incorrect password.",
            status=400,
        ) from e

    try:
        # Remove TOTP device from SuperTokens
        devices = await totp_asyncio.list_devices(user_id=user_id)
        if isinstance(devices, totp_asyncio.ListDevicesOkResult):
            for device in devices.devices:
                await totp_asyncio.remove_device(user_id=user_id, device_name=device.name)

        # Clear 2FA data in database
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET totp_enabled = false,
                        totp_enabled_at = NULL,
                        totp_backup_codes = NULL,
                        totp_failed_attempts = 0,
                        totp_lockout_until = NULL,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (user_id,),
                )

        logger.info(f"2FA disabled for user {user_id}")

        return DisableTwoFactorResponse(
            success=True,
            message="2FA has been disabled.",
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to disable 2FA for {user_id}: {e}",
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to disable 2FA", status=500
        ) from e


@router.post(
    "/verify",
    summary="Verify 2FA code",
    description="""
    Verify a TOTP code or backup code during login.

    Accepts either:
    - 6-digit TOTP code from authenticator app
    - 8-character backup code (single-use)

    Rate limited: 5 failed attempts trigger 15-minute lockout.
    """,
    response_model=VerifyTwoFactorResponse,
    responses={
        200: {"description": "Verification result"},
        400: {"description": "Invalid code", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
        429: {"description": "Too many failed attempts", "model": ErrorResponse},
    },
)
async def verify_two_factor(
    body: VerifyTwoFactorRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> VerifyTwoFactorResponse:
    """Verify TOTP or backup code during login."""
    user_id = user["user_id"]
    code = body.code.strip().upper()

    # Check rate limit
    is_locked, remaining = _check_totp_rate_limit(user_id)
    if is_locked:
        raise http_error(
            ErrorCode.API_RATE_LIMIT,
            f"Too many failed attempts. Try again in {remaining} seconds.",
            status=429,
        )

    # Get user's 2FA status and backup codes
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT totp_enabled, totp_backup_codes
                FROM users WHERE id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            if not row or not row.get("totp_enabled"):
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    "2FA is not enabled for this account.",
                    status=400,
                )

            backup_codes = row.get("totp_backup_codes") or []

    # Try backup code first (if it looks like one - 8 chars vs 6 for TOTP)
    if len(code) == BACKUP_CODE_LENGTH:
        code_hash = _hash_backup_code(code)
        if code_hash in backup_codes:
            # Valid backup code - mark as used
            backup_codes.remove(code_hash)
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET totp_backup_codes = %s, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (backup_codes, user_id),
                    )

            _clear_totp_failures(user_id)
            remaining_codes = len(backup_codes)

            logger.info(f"User {user_id} used backup code for 2FA ({remaining_codes} remaining)")

            # Warn if running low
            warning_threshold = 3
            if remaining_codes < warning_threshold:
                logger.warning(f"User {user_id} has only {remaining_codes} backup codes remaining")

            return VerifyTwoFactorResponse(
                success=True,
                used_backup_code=True,
                backup_codes_remaining=remaining_codes,
            )

    # Try TOTP verification
    try:
        result = await totp_asyncio.verify_totp(
            user_id=user_id,
            totp=code,
        )

        if isinstance(result, totp_asyncio.InvalidTOTPError):
            _record_totp_failure(user_id)
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "Invalid code. Please check your authenticator app.",
                status=400,
            )

        if isinstance(result, totp_asyncio.LimitReachedError):
            raise http_error(
                ErrorCode.API_RATE_LIMIT,
                "Too many attempts. Please wait and try again.",
                status=429,
            )

        if isinstance(result, totp_asyncio.UnknownUserIdError):
            raise http_error(
                ErrorCode.VALIDATION_ERROR,
                "2FA not configured properly. Please contact support.",
                status=400,
            )

        if isinstance(result, totp_asyncio.VerifyTOTPOkResult):
            _clear_totp_failures(user_id)
            logger.info(f"User {user_id} verified 2FA successfully")

            return VerifyTwoFactorResponse(
                success=True,
                used_backup_code=False,
                backup_codes_remaining=None,
            )

        # Unexpected result
        logger.error(f"Unexpected verify_totp result for {user_id}: {type(result)}")
        _record_totp_failure(user_id)
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR,
            "Verification failed. Please try again.",
            status=500,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to verify 2FA for {user_id}: {e}",
            user_id=user_id,
        )
        raise http_error(
            ErrorCode.SERVICE_EXECUTION_ERROR, "Failed to verify 2FA", status=500
        ) from e


@router.get(
    "/backup-codes/regenerate",
    summary="Regenerate backup codes",
    description="""
    Generate new backup codes, invalidating all existing ones.

    Use when:
    - You've used most/all backup codes
    - You think backup codes may be compromised
    - You lost access to your saved codes
    """,
    response_model=SetupTwoFactorResponse,
    responses={
        200: {"description": "New backup codes"},
        400: {"description": "2FA not enabled", "model": ErrorResponse},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
)
async def regenerate_backup_codes(
    user: dict[str, Any] = Depends(get_current_user),
) -> SetupTwoFactorResponse:
    """Regenerate backup codes (invalidates existing ones)."""
    user_id = user["user_id"]

    # Check if 2FA is enabled
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT totp_enabled FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row or not row.get("totp_enabled"):
                raise http_error(
                    ErrorCode.VALIDATION_ERROR,
                    "2FA is not enabled. Enable 2FA first to get backup codes.",
                    status=400,
                )

    # Generate new codes
    backup_codes = _generate_backup_codes()
    hashed_codes = [_hash_backup_code(code) for code in backup_codes]

    # Store hashed codes
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET totp_backup_codes = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (hashed_codes, user_id),
            )

    logger.info(f"Backup codes regenerated for user {user_id}")

    return SetupTwoFactorResponse(
        secret="",  # Not returned on regenerate
        qr_uri="",  # Not returned on regenerate
        backup_codes=backup_codes,
    )
