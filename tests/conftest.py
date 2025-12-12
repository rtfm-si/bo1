"""Pytest configuration and fixtures."""

import os
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

# Load .env file for test environment (ignore encoding errors in CI)
try:
    load_dotenv()
except (UnicodeDecodeError, FileNotFoundError):
    # Skip if .env has encoding issues or doesn't exist
    # CI will use environment variables directly
    pass

# Set default environment variables for CI/testing if not already set
# This allows tests to run without real API keys (non-LLM tests)
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
os.environ.setdefault("VOYAGE_API_KEY", "test-key-placeholder")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("DATABASE_URL", "postgresql://bo1:bo1_dev_password@localhost:5432/boardofone")


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_llm: mark test as requiring LLM API keys (deselect with '-m \"not requires_llm\"')",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test",
    )
    config.addinivalue_line(
        "markers",
        "requires_redis: mark test as requiring Redis connection",
    )


@pytest.fixture
def personas_path() -> Path:
    """Get path to personas.json file."""
    bo1_dir = Path(__file__).parent.parent / "bo1"
    return bo1_dir / "data" / "personas.json"


@pytest.fixture
def sample_problem():
    """Create a simple test problem."""
    from bo1.models.problem import Problem

    return Problem(
        title="Test Investment Decision",
        description="Should we invest $500K in AI infrastructure?",
        context="Series A funded startup, 50 employees, need to scale",
    )


@pytest.fixture
def sample_persona():
    """Get a real persona from the catalog for testing."""
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    persona_data = get_persona_by_code("growth_hacker")
    if not persona_data:
        pytest.skip("growth_hacker persona not found in catalog")
    return PersonaProfile(**persona_data)


@pytest.fixture
def sample_personas():
    """Get multiple real personas from the catalog for testing."""
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    codes = ["growth_hacker", "finance_strategist"]
    personas = []
    for code in codes:
        persona_data = get_persona_by_code(code)
        if not persona_data:
            pytest.skip(f"{code} persona not found in catalog")
        personas.append(PersonaProfile(**persona_data))
    return personas


@pytest.fixture
def sample_problem_simple():
    """Create a minimal problem with no sub-problems (for simple tests)."""
    from bo1.models.problem import Problem

    return Problem(
        title="Test Investment Decision",
        description="Should we invest $500K in AI infrastructure?",
        context="Series A funded startup, 50 employees",
    )


@pytest.fixture
def sample_problem_marketing():
    """Create a marketing-focused problem (for specialized tests)."""
    from bo1.models.problem import Problem

    return Problem(
        title="Marketing Budget Decision",
        description="Should I invest $50K in SEO or paid ads?",
        context=(
            "Solo founder running a B2B SaaS with $100K ARR. "
            "Current customer acquisition is through word of mouth and organic traffic. "
            "Target market is small businesses in the US. "
            "Average deal size is $500/month with 12-month contracts. "
            "No dedicated marketing team, founder handles all marketing."
        ),
    )


@pytest.fixture
def load_personas_by_codes():
    """Factory function to load personas by codes.

    Returns:
        Callable that takes a list of persona codes and returns PersonaProfile list

    Example:
        def test_something(load_personas_by_codes):
            personas = load_personas_by_codes(["growth_hacker", "risk_officer"])
            # Use personas...
    """
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    def _load(codes: list[str]) -> list[PersonaProfile]:
        personas = []
        for code in codes:
            data = get_persona_by_code(code)
            if not data:
                pytest.skip(f"{code} persona not found in catalog")
            personas.append(PersonaProfile(**data))
        return personas

    return _load


@pytest.fixture
def state_builder(sample_problem, sample_personas):
    """Builder pattern for creating test states with fluent API.

    Returns:
        StateBuilder instance for constructing test states

    Example:
        def test_something(state_builder):
            state = (state_builder
                .with_round(3)
                .with_personas()
                .with_metrics(total_cost=0.05)
                .build())
    """
    from bo1.graph.state import create_initial_state
    from bo1.models.state import DeliberationMetrics

    class StateBuilder:
        def __init__(self):
            self.state = create_initial_state(
                session_id="test-session-builder",
                problem=sample_problem,
                max_rounds=5,
            )

        def with_session_id(self, session_id: str):
            """Set custom session ID."""
            self.state["session_id"] = session_id
            return self

        def with_problem(self, problem):
            """Set custom problem."""
            self.state["problem"] = problem
            return self

        def with_personas(self, personas=None):
            """Add personas to state (uses sample_personas if None)."""
            self.state["personas"] = personas if personas is not None else sample_personas
            return self

        def with_round(self, num: int):
            """Set round number."""
            self.state["round_number"] = num
            return self

        def with_max_rounds(self, num: int):
            """Set max rounds."""
            self.state["max_rounds"] = num
            return self

        def with_contributions(self, contributions: list):
            """Add contributions to state."""
            self.state["contributions"] = contributions
            return self

        def with_metrics(self, metrics=None, **kwargs):
            """Add metrics to state (create new if None, accepts kwargs for fields)."""
            if metrics is not None:
                self.state["metrics"] = metrics
            elif kwargs:
                self.state["metrics"] = DeliberationMetrics(**kwargs)
            return self

        def with_current_sub_problem(self, sub_problem):
            """Set current sub-problem."""
            self.state["current_sub_problem"] = sub_problem
            return self

        def build(self):
            """Return the constructed state."""
            return self.state

    return StateBuilder()


@pytest.fixture
def test_user_id():
    """Create a test user in the database and return their ID.

    Cleans up the user and related records after the test.
    """
    import uuid

    from bo1.state.database import db_session

    user_id = f"test-user-{uuid.uuid4().hex[:8]}"

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, auth_provider, created_at)
                VALUES (%s, %s, 'test', NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                (user_id, f"{user_id}@test.local"),
            )

    yield user_id

    # Cleanup - cascade should handle most, but be explicit
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workspace_members WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM workspaces WHERE owner_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


@pytest.fixture
def redis_url() -> str:
    """Get Redis URL from environment, with localhost fallback for local dev."""
    # Use Redis container in Docker, localhost for local dev
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def redis_manager(request) -> Any:
    """Provide Redis manager with behavior based on marker.

    - If test has @pytest.mark.requires_redis: Skip if Redis unavailable
    - Otherwise: Return None if Redis unavailable (for fallback testing)

    Usage:
        @pytest.mark.requires_redis
        def test_redis_feature(redis_manager):
            # redis_manager is guaranteed to be available or test is skipped
            manager = redis_manager
            # Use manager...

        def test_fallback_behavior(redis_manager):
            # redis_manager may be None, allowing fallback testing
            if redis_manager is None:
                # Test fallback behavior
            else:
                # Test with Redis
    """
    from bo1.state.redis_manager import RedisManager

    try:
        manager = RedisManager()
        if not manager.is_available:
            if request.node.get_closest_marker("requires_redis"):
                pytest.skip("Redis not available")
            return None
        return manager
    except Exception as e:
        if request.node.get_closest_marker("requires_redis"):
            pytest.skip(f"Redis not available: {e}")
        return None


# Common test fixtures for LLM responses and requests


@pytest.fixture
def sample_llm_request():
    """Create a sample PromptRequest for testing.

    Returns:
        PromptRequest with basic test data

    Example:
        def test_something(sample_llm_request):
            request = sample_llm_request
            # Modify or use as-is...
    """
    from bo1.llm.broker import PromptRequest

    return PromptRequest(
        system="test system prompt",
        user_message="test user message",
        model="test-model",
        phase="test",
        agent_type="TestAgent",
    )


@pytest.fixture
def sample_llm_response():
    """Create a sample LLMResponse for testing.

    Returns:
        LLMResponse with realistic token usage and cost

    Example:
        def test_something(sample_llm_response):
            response = sample_llm_response
            # response.cost_total is 0.003 (realistic for ~500 tokens)
    """
    from bo1.llm.response import LLMResponse, TokenUsage

    return LLMResponse(
        content="test response content",
        model="claude-sonnet-4-5-20250929",
        token_usage=TokenUsage(
            input_tokens=300,
            output_tokens=200,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        ),
        duration_ms=1500,
        retry_count=0,
        request_id="test-request-id",
        phase="test",
        agent_type="TestAgent",
    )


@pytest.fixture
def mock_broker(monkeypatch):
    """Mock LLM broker for testing without API calls.

    Returns a broker that returns sample LLM responses for all calls.
    Uses monkeypatch to avoid actual API requests.

    Example:
        def test_agent(mock_broker):
            agent = MyAgent(broker=mock_broker)
            response = await agent.run()
            # No actual API calls made
    """
    from bo1.llm.broker import PromptBroker, PromptRequest
    from bo1.llm.response import LLMResponse, TokenUsage

    async def mock_call(request: PromptRequest) -> LLMResponse:
        # Return fake response with known cost
        return LLMResponse(
            content="mocked response",
            model=request.model,
            token_usage=TokenUsage(
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
            ),
            duration_ms=1000,
            retry_count=0,
            request_id=request.request_id,
            phase=request.phase or "unknown",
            agent_type=request.agent_type or "Unknown",
        )

    broker = PromptBroker()
    monkeypatch.setattr(broker, "call", mock_call)
    return broker


@pytest.fixture
def capture_logs():
    """Capture log output to a string buffer for testing.

    Returns:
        Tuple of (log_buffer, handler) - read logs from log_buffer.getvalue()

    Example:
        def test_logging(capture_logs):
            log_buffer, handler = capture_logs
            logger = logging.getLogger("test")
            logger.addHandler(handler)
            logger.info("test message")
            assert "test message" in log_buffer.getvalue()
    """
    import logging
    from io import StringIO

    log_buffer = StringIO()
    handler = logging.StreamHandler(log_buffer)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(name)s - %(message)s"))

    yield log_buffer, handler

    handler.close()
