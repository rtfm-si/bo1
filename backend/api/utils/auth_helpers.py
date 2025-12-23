"""Authentication helper utilities.

Provides reusable functions for:
- User ID extraction from JWT tokens
- Token validation
- Authentication state checking
- Feature flag checks
"""

import logging

from fastapi import HTTPException

from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)


def extract_user_id(current_user: dict | None) -> str:
    """Extract user_id from JWT token claims.

    This function enforces strict authentication:
    - No fallback to hardcoded values
    - No silent failures
    - Clear error messages for debugging

    Args:
        current_user: User data dict from verify_jwt() dependency

    Returns:
        User ID string from token

    Raises:
        HTTPException: 401 if user not authenticated or user_id missing

    Examples:
        >>> user = await get_current_user(authorization)
        >>> user_id = extract_user_id(user)
        >>> # Use user_id for database queries
    """
    # Check if user is authenticated
    if not current_user:
        logger.warning("User ID extraction failed: current_user is None")
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    # Extract user_id from token claims
    user_id = current_user.get("user_id")

    if not user_id:
        # Missing user_id indicates malformed token
        log_error(
            logger,
            ErrorCode.AUTH_TOKEN_ERROR,
            "User ID extraction failed: token missing user_id claim",
            token_claims=list(current_user.keys()),
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token: missing user_id claim",
        )

    logger.debug(f"Extracted user_id: {user_id}")
    return user_id


def extract_user_email(current_user: dict | None) -> str:
    """Extract email from JWT token claims.

    Args:
        current_user: User data dict from verify_jwt()

    Returns:
        User email string

    Raises:
        HTTPException: 401 if user not authenticated or email missing
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    email = current_user.get("email")

    if not email:
        log_error(
            logger,
            ErrorCode.AUTH_TOKEN_ERROR,
            "Email extraction failed: token missing email claim",
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token: missing email claim",
        )

    return email


def is_admin(current_user: dict | None) -> bool:
    """Check if current user has admin privileges.

    Args:
        current_user: User data dict from verify_jwt()

    Returns:
        True if user is admin, False otherwise
    """
    if not current_user:
        return False

    return current_user.get("is_admin", False)


def require_admin_role(current_user: dict | None) -> None:
    """Require admin role or raise 403.

    Args:
        current_user: User data dict from verify_jwt()

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    if not is_admin(current_user):
        user_email = current_user.get("email", "unknown")
        logger.warning(
            f"Admin access denied: user {user_email} is not an admin "
            f"(is_admin={current_user.get('is_admin')})"
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )


def get_subscription_tier(current_user: dict | None) -> str:
    """Get user's subscription tier.

    Args:
        current_user: User data dict from verify_jwt()

    Returns:
        Subscription tier string (default: "free")
    """
    if not current_user:
        return "free"

    return current_user.get("subscription_tier", "free")


def require_feature(flag_name: str, current_user: dict | None) -> None:
    """Require a feature flag to be enabled or raise 403.

    Args:
        flag_name: Feature flag name
        current_user: User data dict from verify_jwt()

    Raises:
        HTTPException: 401 if not authenticated, 403 if feature disabled
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    from backend.services import feature_flags as ff

    user_id = current_user.get("user_id")
    tier = get_subscription_tier(current_user)

    if not ff.is_enabled(flag_name, user_id=user_id, tier=tier):
        logger.info(
            "Feature %s disabled for user %s (tier=%s)",
            flag_name,
            user_id,
            tier,
        )
        raise HTTPException(
            status_code=403,
            detail=f"Feature '{flag_name}' is not available for your account",
        )


def get_user_features(current_user: dict | None) -> dict[str, bool]:
    """Get all feature flags evaluated for current user.

    Args:
        current_user: User data dict from verify_jwt()

    Returns:
        Dict of flag_name -> enabled
    """
    if not current_user:
        return {}

    from backend.services import feature_flags as ff

    user_id = current_user.get("user_id")
    tier = get_subscription_tier(current_user)

    return ff.get_flags_for_user(user_id, tier) if user_id else {}
