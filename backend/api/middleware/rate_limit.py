"""Rate limiting middleware for auth endpoints.

Prevents brute force attacks on authentication endpoints using SlowAPI.

Rate limits:
- Auth endpoints (/api/auth/*): 10 requests per minute per IP
- General API endpoints: No limit (v1.0 MVP)

Storage: In-memory (for MVP). Will migrate to Redis for multi-instance deployments.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
# - key_func: Use IP address as the key (get_remote_address)
# - storage_uri: In-memory storage (default) for MVP
# - strategy: Fixed window (count resets at interval boundary)
limiter = Limiter(key_func=get_remote_address)

# Rate limit decorators for common use cases
AUTH_RATE_LIMIT = "10/minute"  # 10 requests per minute for auth endpoints
