"""SSE user for testing deliberation streaming."""

import logging
import random
import time

from locust import between, events, task

from tests.load.config import SAMPLE_PROBLEMS, SSE_CONNECT_TIMEOUT, SSE_READ_TIMEOUT
from tests.load.users.base import AuthenticatedUser

logger = logging.getLogger(__name__)


class SSEUser(AuthenticatedUser):
    """User that tests SSE streaming for deliberations.

    WARNING: This triggers actual deliberations with LLM calls.
    Use sparingly and only for targeted SSE testing.
    """

    wait_time = between(30, 60)  # Long wait between sessions
    weight = 1  # Low weight - expensive operation

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._session_id: str | None = None

    @task
    def stream_deliberation(self) -> None:
        """Create a session and stream its events.

        Measures:
        - Session creation latency
        - Time to first SSE event
        - Event throughput
        - Connection stability
        """
        # Create session first
        session_id = self._create_session()
        if not session_id:
            return

        # Stream events
        self._stream_session_events(session_id)

    def _create_session(self) -> str | None:
        """Create a session and return its ID."""
        problem = random.choice(SAMPLE_PROBLEMS)  # noqa: S311

        start_time = time.time()
        response = self.client.post(
            f"{self.api_url}/sessions",
            json={
                "problem_statement": problem,
                "context": "SSE load test - measuring streaming performance.",
            },
            name="sse/create_session",
        )

        if response.status_code != 201:
            logger.error(f"Session creation failed: {response.status_code}")
            return None

        data = response.json()
        session_id = data.get("id")

        creation_time = (time.time() - start_time) * 1000
        events.request.fire(
            request_type="SESSION",
            name="sse/session_created",
            response_time=creation_time,
            response_length=len(response.content),
            context={"session_id": session_id},
        )

        self._session_id = session_id
        return session_id

    def _stream_session_events(self, session_id: str) -> None:
        """Connect to SSE stream and measure event delivery."""
        url = f"{self.api_url}/sessions/{session_id}/stream"

        try:
            start_time = time.time()
            first_event_time: float | None = None
            event_count = 0
            total_bytes = 0

            # Use streaming response
            with self.client.get(
                url,
                stream=True,
                timeout=(SSE_CONNECT_TIMEOUT, SSE_READ_TIMEOUT),
                name="sse/stream",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"SSE connect failed: {response.status_code}")
                    return

                # Record connection time
                connect_time = (time.time() - start_time) * 1000
                events.request.fire(
                    request_type="SSE",
                    name="sse/connected",
                    response_time=connect_time,
                    response_length=0,
                )

                # Read SSE events
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        total_bytes += len(line)

                        if line.startswith("data:"):
                            event_count += 1

                            if first_event_time is None:
                                first_event_time = time.time()
                                ttfe = (first_event_time - start_time) * 1000
                                events.request.fire(
                                    request_type="SSE",
                                    name="sse/first_event",
                                    response_time=ttfe,
                                    response_length=len(line),
                                )

                            # Check for completion
                            if '"event_type":"meeting_complete"' in line:
                                break
                            if '"event_type":"error"' in line:
                                logger.warning(f"SSE error event: {line[:200]}")
                                break

                # Record final metrics
                total_time = (time.time() - start_time) * 1000
                events.request.fire(
                    request_type="SSE",
                    name="sse/complete",
                    response_time=total_time,
                    response_length=total_bytes,
                    context={"event_count": event_count},
                )

                response.success()

        except Exception as e:
            logger.error(f"SSE streaming error: {e}")
            events.request.fire(
                request_type="SSE",
                name="sse/error",
                response_time=0,
                response_length=0,
                exception=e,
            )
