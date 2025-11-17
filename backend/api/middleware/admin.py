"""Admin authentication middleware for Board of One API.

Provides simple API key-based authentication for admin endpoints.
For MVP: Uses environment variable ADMIN_API_KEY
For v2+: Will use role-based auth with Supabase
"""

import logging
import os

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

# Load admin API key from environment
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

if not ADMIN_API_KEY:
    logger.warning("ADMIN_API_KEY not set - admin endpoints will be disabled")


def require_admin(x_admin_key: str = Header(...)) -> str:
    """Dependency to require admin authentication.

    Checks the X-Admin-Key header against the ADMIN_API_KEY environment variable.

    Args:
        x_admin_key: Admin API key from X-Admin-Key header

    Returns:
        Admin API key if valid

    Raises:
        HTTPException: 401 if key not provided, 403 if key invalid
    """
    if not ADMIN_API_KEY:
        logger.error("Admin API key not configured - access denied")
        raise HTTPException(
            status_code=500,
            detail="Admin API not configured",
        )

    if not x_admin_key:
        logger.warning("Admin access attempted without API key")
        raise HTTPException(
            status_code=401,
            detail="Admin API key required",
        )

    if x_admin_key != ADMIN_API_KEY:
        # Security: Don't log the actual API key, even partially
        logger.warning("Invalid admin API key attempted")
        raise HTTPException(
            status_code=403,
            detail="Invalid admin API key",
        )

    logger.info("Admin access granted")
    return x_admin_key
