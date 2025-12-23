"""Constants for Board of One API.

Centralizes magic numbers and configuration values used across the API.
"""

import os

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
DB_POOL_MAX_CONNECTIONS = 75

# Research cache defaults
RESEARCH_CACHE_SIMILARITY_THRESHOLD = 0.85
RESEARCH_CACHE_DEFAULT_FRESHNESS_DAYS = 90

# Event persistence retry settings
EVENT_PERSISTENCE_MAX_ATTEMPTS = 3

# Graph execution timeout (wall-clock)
# Default 10 minutes - prevents runaway sessions from blocking resources
GRAPH_EXECUTION_TIMEOUT_SECONDS = int(os.environ.get("GRAPH_EXECUTION_TIMEOUT_SECONDS", "600"))

# Competitor tier limits
TIER_LIMITS = {
    "free": {"max_competitors": 3, "data_depth": "basic"},
    "starter": {"max_competitors": 5, "data_depth": "standard"},
    "pro": {"max_competitors": 8, "data_depth": "deep"},
}

# SSE Polling Fallback Configuration
# Used when Redis PubSub is unavailable (circuit breaker open)
SSE_POLLING_INTERVAL_MS = int(os.environ.get("SSE_POLLING_INTERVAL_MS", "500"))
SSE_POLLING_BATCH_SIZE = int(os.environ.get("SSE_POLLING_BATCH_SIZE", "50"))
SSE_CIRCUIT_CHECK_INTERVAL_MS = int(os.environ.get("SSE_CIRCUIT_CHECK_INTERVAL_MS", "5000"))

# Session Metadata Cache Configuration
# In-memory cache reduces Redis/PostgreSQL lookups during SSE reconnections
SESSION_METADATA_CACHE_TTL_SECONDS = int(
    os.environ.get("SESSION_METADATA_CACHE_TTL_SECONDS", "300")
)  # 5 minutes default
SESSION_METADATA_CACHE_MAX_SIZE = int(os.environ.get("SESSION_METADATA_CACHE_MAX_SIZE", "1000"))

# Cost data filtering for SSE events (admin-only data)
# Event types that should be completely hidden from non-admin users
COST_EVENT_TYPES: set[str] = {"phase_cost_breakdown", "cost_anomaly"}
# Fields within events that contain cost data and should be stripped for non-admin users
COST_FIELDS: set[str] = {"cost", "total_cost", "phase_costs", "by_provider"}
