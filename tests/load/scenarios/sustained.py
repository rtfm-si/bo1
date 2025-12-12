"""Sustained load scenario - endurance testing.

Configuration:
- 25 users
- 2 user/s spawn rate
- 30 minute duration
- Steady mix of all user types
"""

from locust import HttpUser, between

from tests.load.config import BASE_URL, SCENARIOS
from tests.load.users.api_user import ActiveUser, BrowsingUser, DataAnalystUser
from tests.load.users.sse_user import SSEUser

# Scenario configuration
SCENARIO = SCENARIOS["sustained"]


class SustainedBrowsingUser(BrowsingUser):
    """Browsing user for sustained load scenario."""

    weight = 5


class SustainedDataUser(DataAnalystUser):
    """Data analyst user for sustained load scenario."""

    weight = 3


class SustainedActiveUser(ActiveUser):
    """Active user for sustained load scenario."""

    wait_time = between(30, 60)  # Slower to limit LLM costs
    weight = 1


class SustainedSSEUser(SSEUser):
    """SSE user for sustained load scenario."""

    wait_time = between(60, 120)  # Very slow - expensive operation
    weight = 1


class SustainedLoadTest(HttpUser):
    """Combined user for sustained load test.

    Run with:
        locust -f tests/load/scenarios/sustained.py --users 25 --spawn-rate 2 --run-time 30m
    """

    host = BASE_URL
    wait_time = between(2, 5)
    tasks = {
        SustainedBrowsingUser: 5,
        SustainedDataUser: 3,
        SustainedActiveUser: 1,
        SustainedSSEUser: 1,
    }
