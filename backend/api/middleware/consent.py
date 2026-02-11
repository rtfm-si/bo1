"""Consent enforcement middleware for GDPR compliance.

Provides a dependency that checks if a user has consented to all required policies
(T&C, GDPR, Privacy) before allowing access to protected routes.

Usage:
    For routes that require all consents:
        @router.get("/sensitive", dependencies=[Depends(require_all_consents)])
        async def sensitive_endpoint(): ...

    For routes that need to check specific policies:
        @router.get("/data-processing", dependencies=[Depends(require_gdpr_consent)])
        async def data_processing_endpoint(): ...
"""

import logging
from typing import Any

from fastapi import Depends, HTTPException

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from bo1.state.repositories.terms_repository import terms_repository

logger = logging.getLogger(__name__)


async def require_all_consents(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Dependency that enforces all required consents (T&C, GDPR, Privacy).

    Returns:
        User dict if all consents present.

    Raises:
        HTTPException 403 if any consent is missing.
    """
    user_id = extract_user_id(user)

    # Check for missing policies
    missing = terms_repository.get_missing_policies(user_id)

    if missing:
        logger.info(f"User {user_id} blocked - missing consents: {missing}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "consent_required",
                "message": "You must accept all required policies to access this resource",
                "missing_policies": missing,
            },
        )

    return user


async def require_gdpr_consent(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Dependency that enforces GDPR consent specifically.

    Use for routes that process personal data.

    Returns:
        User dict if GDPR consent present.

    Raises:
        HTTPException 403 if GDPR consent missing.
    """
    user_id = extract_user_id(user)

    if not terms_repository.has_user_consented_to_current(user_id, "gdpr"):
        logger.info(f"User {user_id} blocked - missing GDPR consent")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "consent_required",
                "message": "GDPR consent required to access this resource",
                "missing_policies": ["gdpr"],
            },
        )

    return user


async def require_tc_consent(
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Dependency that enforces T&C consent.

    Returns:
        User dict if T&C consent present.

    Raises:
        HTTPException 403 if T&C consent missing.
    """
    user_id = extract_user_id(user)

    if not terms_repository.has_user_consented_to_current(user_id, "tc"):
        logger.info(f"User {user_id} blocked - missing T&C consent")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "consent_required",
                "message": "Terms & Conditions consent required",
                "missing_policies": ["tc"],
            },
        )

    return user
