"""Constants for Board of One API.

Centralizes magic numbers and configuration values used across the API.
"""

# Pagination defaults
DEFAULT_PAGE_SIZE = 10
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100

# Text truncation defaults
DEFAULT_TRUNCATE_LENGTH = 100
TITLE_TRUNCATE_LENGTH = 100

# Session timeouts (seconds)
DEFAULT_SESSION_TIMEOUT = 3600  # 1 hour
MAX_SESSION_TIMEOUT = 7200  # 2 hours

# Monitoring defaults
DEFAULT_TOP_N_SESSIONS = 10
MIN_TOP_N_SESSIONS = 1
MAX_TOP_N_SESSIONS = 100

# SSE streaming
SSE_MAX_ITERATIONS = 100
SSE_POLL_INTERVAL_SECONDS = 1.0

# Redis TTL
REDIS_SESSION_TTL_SECONDS = 86400  # 24 hours
REDIS_CHECKPOINT_TTL_SECONDS = 604800  # 7 days

# PostgreSQL connection pool
DB_POOL_MIN_CONNECTIONS = 1
DB_POOL_MAX_CONNECTIONS = 20

# Research cache defaults
RESEARCH_CACHE_SIMILARITY_THRESHOLD = 0.85
RESEARCH_CACHE_DEFAULT_FRESHNESS_DAYS = 90

# Event persistence retry settings
EVENT_PERSISTENCE_MAX_ATTEMPTS = 3

# Competitor tier limits
TIER_LIMITS = {
    "free": {"max_competitors": 3, "data_depth": "basic"},
    "starter": {"max_competitors": 5, "data_depth": "standard"},
    "pro": {"max_competitors": 8, "data_depth": "deep"},
}
