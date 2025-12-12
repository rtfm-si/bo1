"""Main Locust entry point for load testing.

Usage:
    # Start Locust web UI (recommended for interactive testing)
    locust -f tests/load/locustfile.py

    # Run headless with specific settings
    locust -f tests/load/locustfile.py --headless -u 10 -r 1 -t 5m

    # Run specific scenario
    locust -f tests/load/scenarios/normal.py --headless -u 10 -r 1 -t 5m

Environment variables:
    LOAD_TEST_BASE_URL: API base URL (default: http://localhost:8000)
    LOAD_TEST_USER_EMAIL: Test user email
    LOAD_TEST_USER_PASSWORD: Test user password
"""

from locust import HttpUser, between

from tests.load.config import BASE_URL
from tests.load.users.api_user import ActiveUser, BrowsingUser, DataAnalystUser
from tests.load.users.sse_user import SSEUser


class MixedLoadUser(HttpUser):
    """Default mixed workload for general load testing.

    Combines all user types with realistic weights:
    - 50% Browsing users (read-only)
    - 30% Data analyst users
    - 15% Active users (creates sessions)
    - 5% SSE users (streams deliberations)
    """

    host = BASE_URL
    wait_time = between(1, 5)

    tasks = {
        BrowsingUser: 5,
        DataAnalystUser: 3,
        ActiveUser: 1,
        # SSEUser excluded by default - enable for SSE-specific tests
    }


# Export for scenario imports
__all__ = [
    "MixedLoadUser",
    "BrowsingUser",
    "DataAnalystUser",
    "ActiveUser",
    "SSEUser",
]
