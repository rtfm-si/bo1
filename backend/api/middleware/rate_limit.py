"""Rate limiting middleware for API endpoints.

Prevents abuse and brute force attacks using SlowAPI.

Rate limits by endpoint type:
- Auth endpoints (/api/auth/*): 10 requests per minute per IP
- Session creation: 30 requests per minute per IP
- Streaming (expensive): 5 requests per minute per IP
- General API endpoints: 60 requests per minute per IP

Storage: In-memory (for MVP). Will migrate to Redis for multi-instance deployments.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from bo1.constants import RateLimits

# Create limiter instance
# - key_func: Use IP address as the key (get_remote_address)
# - storage_uri: In-memory storage (default) for MVP
# - strategy: Fixed window (count resets at interval boundary)
limiter = Limiter(key_func=get_remote_address)

# Rate limit constants for different endpoint types
# Imported from constants for centralized configuration
AUTH_RATE_LIMIT = RateLimits.AUTH
SESSION_RATE_LIMIT = RateLimits.SESSION
STREAMING_RATE_LIMIT = RateLimits.STREAMING
GENERAL_RATE_LIMIT = RateLimits.GENERAL
CONTROL_RATE_LIMIT = RateLimits.CONTROL
