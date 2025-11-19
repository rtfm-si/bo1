"""Security utilities for LLM API calls.

Provides certificate pinning and secure HTTP client configuration
for external API communications (Anthropic, Voyage AI, etc.).

SECURITY NOTE: Full certificate pinning requires custom SSL verification
and regular maintenance when certificates rotate. This module provides
the foundation with documented best practices.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Anthropic API certificate fingerprints (SHA256)
# NOTE: These would need to be updated when Anthropic rotates certificates
# To get current fingerprints: openssl s_client -connect api.anthropic.com:443 | openssl x509 -fingerprint -sha256
# FUTURE ENHANCEMENT: Implement automatic certificate monitoring and alerts
ANTHROPIC_CERT_FINGERPRINTS: list[str] = [
    # Primary certificate (placeholder - needs actual fingerprint)
    # "sha256/PRIMARY_CERT_FINGERPRINT_HERE",
    # Backup certificate for rotation period
    # "sha256/BACKUP_CERT_FINGERPRINT_HERE",
]

# Voyage AI certificate fingerprints (SHA256)
VOYAGE_CERT_FINGERPRINTS: list[str] = [
    # Primary certificate (placeholder - needs actual fingerprint)
    # "sha256/PRIMARY_CERT_FINGERPRINT_HERE",
]


def create_secure_client(
    verify_ssl: bool = True,
    cert_fingerprints: list[str] | None = None,
    timeout: float = 30.0,
    max_connections: int = 10,
) -> httpx.AsyncClient:
    """Create HTTP client with security best practices.

    Implements:
    - SSL/TLS verification (enabled by default)
    - Connection pooling limits
    - Timeout configuration
    - Foundation for certificate pinning

    Args:
        verify_ssl: Whether to verify SSL certificates (default: True)
        cert_fingerprints: Optional list of SHA256 certificate fingerprints for pinning
        timeout: Request timeout in seconds (default: 30.0)
        max_connections: Maximum keepalive connections (default: 10)

    Returns:
        Configured AsyncClient with security settings

    Note:
        Certificate pinning via fingerprints requires custom SSL context implementation.
        Current implementation logs a warning if fingerprints are provided but not yet
        implemented. This serves as a placeholder for future enhancement.

    Example:
        >>> client = create_secure_client(
        ...     cert_fingerprints=ANTHROPIC_CERT_FINGERPRINTS,
        ...     timeout=60.0
        ... )
        >>> # Use client for API calls
        >>> await client.get("https://api.anthropic.com/...")
    """
    if cert_fingerprints:
        # FUTURE ENHANCEMENT: Implement custom SSL context for fingerprint verification
        # This would involve:
        # 1. Creating custom SSL context with fingerprint validation callback
        # 2. Handling certificate rotation gracefully (multiple valid fingerprints)
        # 3. Logging certificate changes for monitoring
        # 4. Falling back or alerting on unexpected certificates
        logger.warning(
            "Certificate pinning requested but not yet fully implemented. "
            "Using standard SSL verification. "
            "For production deployment, implement custom SSL context with fingerprint validation."
        )

    # Create client with security best practices
    return httpx.AsyncClient(
        verify=verify_ssl,  # Always verify SSL in production
        timeout=httpx.Timeout(timeout),
        limits=httpx.Limits(
            max_keepalive_connections=max_connections,
            max_connections=max_connections * 2,  # Allow some headroom
            keepalive_expiry=60.0,  # Close idle connections after 60s
        ),
        # Additional security headers
        headers={
            "User-Agent": "BoardOfOne/1.0",  # Identify our application
        },
    )


def get_anthropic_client(**kwargs: Any) -> httpx.AsyncClient:
    """Create secure HTTP client configured for Anthropic API.

    Args:
        **kwargs: Additional arguments passed to create_secure_client()

    Returns:
        AsyncClient configured for Anthropic API calls

    Example:
        >>> client = get_anthropic_client(timeout=60.0)
    """
    return create_secure_client(
        cert_fingerprints=ANTHROPIC_CERT_FINGERPRINTS if ANTHROPIC_CERT_FINGERPRINTS else None,
        **kwargs,
    )


def get_voyage_client(**kwargs: Any) -> httpx.AsyncClient:
    """Create secure HTTP client configured for Voyage AI API.

    Args:
        **kwargs: Additional arguments passed to create_secure_client()

    Returns:
        AsyncClient configured for Voyage AI API calls

    Example:
        >>> client = get_voyage_client(timeout=30.0)
    """
    return create_secure_client(
        cert_fingerprints=VOYAGE_CERT_FINGERPRINTS if VOYAGE_CERT_FINGERPRINTS else None,
        **kwargs,
    )


# Documentation for future implementation
"""
CERTIFICATE PINNING IMPLEMENTATION GUIDE
========================================

To fully implement certificate pinning with fingerprint validation:

1. Get current certificate fingerprints:
   ```bash
   # Anthropic API
   echo | openssl s_client -connect api.anthropic.com:443 2>/dev/null | \
       openssl x509 -fingerprint -sha256 -noout

   # Voyage AI
   echo | openssl s_client -connect api.voyageai.com:443 2>/dev/null | \
       openssl x509 -fingerprint -sha256 -noout
   ```

2. Update ANTHROPIC_CERT_FINGERPRINTS and VOYAGE_CERT_FINGERPRINTS above

3. Implement custom SSL context:
   ```python
   import ssl
   from cryptography import x509
   from cryptography.hazmat.backends import default_backend
   import hashlib

   def verify_fingerprint(cert_der, expected_fingerprints):
       cert = x509.load_der_x509_certificate(cert_der, default_backend())
       fingerprint = hashlib.sha256(cert_der).hexdigest()
       return f"sha256/{fingerprint}" in expected_fingerprints

   # Create SSL context with callback
   ssl_context = ssl.create_default_context()
   ssl_context.check_hostname = True
   ssl_context.verify_mode = ssl.CERT_REQUIRED
   # Add custom verification callback here
   ```

4. Monitor certificate expiration and rotation:
   - Set up alerts 30 days before expiration
   - Test new fingerprints in staging before production
   - Maintain 2+ valid fingerprints during rotation periods

5. Handle certificate mismatch:
   - Log detailed error with actual vs expected fingerprints
   - Alert security team immediately
   - Fail safely (reject request, don't fall back to unverified)

TESTING:
--------
- Test with valid certificates (should succeed)
- Test with expired certificates (should fail)
- Test with self-signed certificates (should fail)
- Test during certificate rotation (both old and new should work)
- Test with wrong fingerprints (should fail)

MAINTENANCE:
-----------
- Review certificates quarterly
- Update fingerprints within 48 hours of provider certificate rotation
- Document all fingerprint changes in git history
- Maintain runbook for emergency certificate updates
"""
