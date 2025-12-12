"""Load test configuration.

Environment variables:
- LOAD_TEST_BASE_URL: Base URL for the API (default: http://localhost:8000)
- LOAD_TEST_USER_EMAIL: Test user email for authentication
- LOAD_TEST_USER_PASSWORD: Test user password for authentication
"""

import os

# Base URL for API requests
BASE_URL = os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000")

# Test user credentials (must exist in database)
TEST_USER_EMAIL = os.getenv("LOAD_TEST_USER_EMAIL", "loadtest@example.com")
TEST_USER_PASSWORD = os.getenv("LOAD_TEST_USER_PASSWORD", "loadtest123")

# API version prefix
API_PREFIX = "/api/v1"

# Timeouts
DEFAULT_TIMEOUT = 30  # seconds
SSE_CONNECT_TIMEOUT = 10  # seconds
SSE_READ_TIMEOUT = 120  # seconds for deliberation events

# Sample problem statements for load testing
SAMPLE_PROBLEMS = [
    "Should we expand into the European market this quarter?",
    "What pricing strategy should we adopt for our new SaaS product?",
    "How should we structure our engineering team for the next project?",
    "Should we build or buy a CRM solution?",
    "What marketing channels should we prioritize for Q1?",
]

# Scenario defaults
SCENARIOS = {
    "normal": {
        "users": 10,
        "spawn_rate": 1,
        "run_time": "5m",
    },
    "peak": {
        "users": 50,
        "spawn_rate": 10,
        "run_time": "2m",
    },
    "sustained": {
        "users": 25,
        "spawn_rate": 2,
        "run_time": "30m",
    },
}
