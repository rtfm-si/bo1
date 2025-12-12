"""Peak load scenario - burst testing.

Configuration:
- 50 users
- 10 user/s spawn rate
- 2 minute duration
- Heavy browsing with some active users
"""

from locust import HttpUser, between

from tests.load.config import BASE_URL, SCENARIOS
from tests.load.users.api_user import ActiveUser, BrowsingUser, DataAnalystUser

# Scenario configuration
SCENARIO = SCENARIOS["peak"]


class PeakBrowsingUser(BrowsingUser):
    """Browsing user for peak load scenario."""

    wait_time = between(0.5, 1.5)  # Faster requests during peak
    weight = 6


class PeakDataUser(DataAnalystUser):
    """Data analyst user for peak load scenario."""

    wait_time = between(1, 2)
    weight = 3


class PeakActiveUser(ActiveUser):
    """Active user for peak load scenario (limited)."""

    wait_time = between(10, 20)
    weight = 1  # Only 10% active users to limit LLM costs


class PeakLoadTest(HttpUser):
    """Combined user for peak load test.

    Run with:
        locust -f tests/load/scenarios/peak.py --users 50 --spawn-rate 10 --run-time 2m
    """

    host = BASE_URL
    wait_time = between(0.5, 2)
    tasks = {PeakBrowsingUser: 6, PeakDataUser: 3, PeakActiveUser: 1}
