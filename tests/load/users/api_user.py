"""API user behavior classes for load testing."""

import random

from locust import between, task

from tests.load.config import SAMPLE_PROBLEMS
from tests.load.users.base import AuthenticatedUser


class BrowsingUser(AuthenticatedUser):
    """User that performs read-only operations.

    Simulates users browsing sessions, actions, and datasets.
    """

    wait_time = between(1, 3)
    weight = 5  # Most common user type

    @task(5)
    def list_sessions(self) -> None:
        """List user's sessions."""
        self.client.get(f"{self.api_url}/sessions", name="sessions/list")

    @task(3)
    def list_actions(self) -> None:
        """List user's actions."""
        self.client.get(f"{self.api_url}/actions", name="actions/list")

    @task(2)
    def list_datasets(self) -> None:
        """List user's datasets."""
        self.client.get(f"{self.api_url}/datasets", name="datasets/list")

    @task(1)
    def get_action_stats(self) -> None:
        """Get action statistics."""
        self.client.get(f"{self.api_url}/actions/stats", name="actions/stats")

    @task(1)
    def check_health(self) -> None:
        """Check API health endpoint."""
        self.client.get("/api/health", name="health")


class ActiveUser(AuthenticatedUser):
    """User that creates sessions and performs deliberations.

    WARNING: This will invoke LLM calls. Use sparingly in load tests.
    """

    wait_time = between(5, 15)
    weight = 1  # Less common, expensive operations

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._created_sessions: list[str] = []

    @task(2)
    def list_sessions(self) -> None:
        """List sessions (read operation)."""
        self.client.get(f"{self.api_url}/sessions", name="sessions/list")

    @task(1)
    def create_session(self) -> None:
        """Create a new deliberation session.

        WARNING: This triggers LLM calls and incurs API costs.
        """
        problem = random.choice(SAMPLE_PROBLEMS)  # noqa: S311

        response = self.client.post(
            f"{self.api_url}/sessions",
            json={
                "problem_statement": problem,
                "context": "Load test context - please ignore this session.",
            },
            name="sessions/create",
        )

        if response.status_code == 201:
            data = response.json()
            session_id = data.get("id")
            if session_id:
                self._created_sessions.append(session_id)

    @task(2)
    def get_session_detail(self) -> None:
        """Get details of a created session."""
        if not self._created_sessions:
            # Fall back to listing sessions
            self.list_sessions()
            return

        session_id = random.choice(self._created_sessions)  # noqa: S311
        self.client.get(f"{self.api_url}/sessions/{session_id}", name="sessions/detail")


class DataAnalystUser(AuthenticatedUser):
    """User that interacts with datasets.

    Simulates data analysts uploading, querying, and asking questions.
    """

    wait_time = between(2, 5)
    weight = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._dataset_ids: list[str] = []

    def on_start(self) -> None:
        """Authenticate and fetch existing datasets."""
        super().on_start()
        self._fetch_datasets()

    def _fetch_datasets(self) -> None:
        """Fetch list of user's datasets."""
        response = self.client.get(f"{self.api_url}/datasets", name="datasets/list_init")
        if response.status_code == 200:
            data = response.json()
            self._dataset_ids = [d["id"] for d in data.get("datasets", [])]

    @task(3)
    def list_datasets(self) -> None:
        """List available datasets."""
        self.client.get(f"{self.api_url}/datasets", name="datasets/list")

    @task(2)
    def get_dataset_detail(self) -> None:
        """Get dataset with profile."""
        if not self._dataset_ids:
            self.list_datasets()
            return

        dataset_id = random.choice(self._dataset_ids)  # noqa: S311
        self.client.get(f"{self.api_url}/datasets/{dataset_id}", name="datasets/detail")

    @task(1)
    def query_dataset(self) -> None:
        """Run a simple query on a dataset."""
        if not self._dataset_ids:
            self.list_datasets()
            return

        dataset_id = random.choice(self._dataset_ids)  # noqa: S311
        self.client.post(
            f"{self.api_url}/datasets/{dataset_id}/query",
            json={
                "aggregate": [{"column": "*", "function": "count"}],
                "limit": 10,
            },
            name="datasets/query",
        )

    @task(1)
    def get_dataset_analyses(self) -> None:
        """Get analysis history for a dataset."""
        if not self._dataset_ids:
            self.list_datasets()
            return

        dataset_id = random.choice(self._dataset_ids)  # noqa: S311
        self.client.get(f"{self.api_url}/datasets/{dataset_id}/analyses", name="datasets/analyses")
