"""Normal load scenario - baseline testing.

Configuration:
- 10 users
- 1 user/s spawn rate
- 5 minute duration
- Mix of browsing and light active users
"""

from locust import HttpUser, between

from tests.load.config import BASE_URL, SCENARIOS
from tests.load.users.api_user import BrowsingUser, DataAnalystUser

# Scenario configuration
SCENARIO = SCENARIOS["normal"]


class NormalBrowsingUser(BrowsingUser):
    """Browsing user for normal load scenario."""

    weight = 7  # 70% browsing users


class NormalDataUser(DataAnalystUser):
    """Data analyst user for normal load scenario."""

    weight = 3  # 30% data analysts


class NormalLoadTest(HttpUser):
    """Combined user for normal load test.

    Run with:
        locust -f tests/load/scenarios/normal.py --users 10 --spawn-rate 1 --run-time 5m
    """

    host = BASE_URL
    wait_time = between(1, 3)
    tasks = {NormalBrowsingUser: 7, NormalDataUser: 3}
