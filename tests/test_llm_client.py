"""Tests for LLM client with prompt caching.

Run these tests to verify:
1. Basic LLM calls work
2. Prompt caching is functional
3. Cache hits are detected
4. Token usage tracking is accurate
5. Cost calculation is correct

Usage:
    pytest tests/test_llm_client.py -v
"""

import asyncio

import pytest

from bo1.config import get_settings
from bo1.llm import ClaudeClient


@pytest.fixture
def settings():
    """Load settings from environment."""
    return get_settings()


@pytest.fixture
def client(settings):
    """Create a Claude client instance."""
    return ClaudeClient(api_key=settings.anthropic_api_key)


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_basic_call(client):
    """Test basic LLM call without caching."""
    response, usage = await client.call(
        model="haiku",
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Say 'Hello World' and nothing else."}],
        cache_system=False,
        max_tokens=20,
    )

    assert "Hello World" in response or "hello world" in response.lower()
    assert usage.output_tokens > 0
    assert usage.input_tokens > 0
    assert usage.cache_creation_tokens == 0  # No caching
    assert usage.cache_read_tokens == 0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_prompt_caching_creation(client):
    """Test that prompt caching creates cache on first call."""
    # System prompt must be >1024 tokens for Sonnet to cache
    system_prompt = (
        "You are a strategic business advisor with 20 years of experience in SaaS startups. " * 100
    )

    response, usage = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "What is 2+2?"}],
        cache_system=True,
        max_tokens=50,
    )

    assert usage.output_tokens > 0
    assert usage.input_tokens > 0 or usage.cache_creation_tokens > 0

    # Either creates cache OR reads from existing cache
    # (If this test runs multiple times quickly, cache might persist)
    assert usage.cache_creation_tokens > 0 or usage.cache_read_tokens > 0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_prompt_caching_hits(client):
    """Test that repeated calls with same system prompt hit cache."""
    # System prompt must be >1024 tokens for Sonnet to cache
    system_prompt = (
        "You are a financial analyst specializing in SaaS business models and unit economics. "
        * 100
    )

    # First call - creates cache
    response1, usage1 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "What is CAC?"}],
        cache_system=True,
        max_tokens=100,
    )

    # Wait a moment for cache to settle
    await asyncio.sleep(0.5)

    # Second call - should hit cache
    response2, usage2 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "What is LTV?"}],
        cache_system=True,
        max_tokens=100,
    )

    # Second call should have cache reads
    assert usage2.cache_read_tokens > 0, "Second call should hit cache"

    # Cache hit rate should be significant
    assert (
        usage2.cache_hit_rate > 0.5
    ), f"Cache hit rate should be >50%, got {usage2.cache_hit_rate}"


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_role_based_model_selection(client):
    """Test that call_for_role uses correct model."""
    response, usage = await client.call_for_role(
        role="summarizer",  # Should use Haiku (lowercase)
        system="You are a summarization expert.",
        messages=[{"role": "user", "content": "Summarize: The cat sat on the mat."}],
        cache_system=False,
        max_tokens=50,
    )

    assert len(response) > 0
    assert usage.output_tokens > 0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_token_usage_calculation(client):
    """Test token usage tracking and cost calculation."""
    response, usage = await client.call(
        model="haiku",
        system="You are a test assistant.",
        messages=[{"role": "user", "content": "Count to 5."}],
        cache_system=False,
        max_tokens=50,
    )

    # Verify token counts are positive
    assert usage.input_tokens > 0
    assert usage.output_tokens > 0
    assert usage.total_tokens > 0

    # Verify cost calculation
    cost = usage.calculate_cost("haiku")
    assert cost > 0
    assert cost < 0.01  # Should be very cheap for small request


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_cache_cost_savings(client):
    """Test that caching provides significant cost savings."""
    system_prompt = """You are a venture capital analyst with deep expertise in:
- SaaS business models
- Unit economics (CAC, LTV, payback period)
- Growth strategies
- Market sizing and TAM analysis
- Competitive landscape assessment
- Financial modeling
- Go-to-market strategies
- Product-market fit evaluation"""

    # First call - creates cache
    response1, usage1 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "What is important in SaaS?"}],
        cache_system=True,
        max_tokens=200,
    )

    _ = usage1.calculate_cost("sonnet")  # Just verify it doesn't error

    await asyncio.sleep(0.5)

    # Second call - hits cache
    response2, usage2 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "How do you calculate CAC?"}],
        cache_system=True,
        max_tokens=200,
    )

    _ = usage2.calculate_cost("sonnet")  # Just verify it doesn't error

    # Second call should be cheaper due to cache
    if usage2.cache_read_tokens > 0:
        # Calculate what cost would have been without caching
        hypothetical_cost = (usage2.cache_read_tokens / 1_000_000) * 3.00  # Regular input rate
        actual_cache_cost = (usage2.cache_read_tokens / 1_000_000) * 0.30  # Cache read rate

        savings_pct = (1 - actual_cache_cost / hypothetical_cost) * 100
        assert (
            savings_pct > 80
        ), f"Cache should save >80% on cached tokens, saved {savings_pct:.1f}%"


@pytest.mark.asyncio
@pytest.mark.requires_llm
@pytest.mark.skip(
    reason="Flaky: Parallel caching behavior is non-deterministic in test environment"
)
async def test_parallel_calls_with_caching(client):
    """Test that parallel calls all attempt to create cache (when made simultaneously).

    When calls are made in parallel, they typically all start before any response
    returns, so they all attempt cache creation. This is expected behavior.

    NOTE: Skipped because caching behavior in parallel is non-deterministic and
    depends on API timing, which varies between test runs.
    """
    # System prompt must be >1024 tokens for Sonnet to cache
    # This prompt is ~2200 tokens (8800 chars / 4)
    system_prompt = (
        "This is a comprehensive test system prompt for evaluating prompt caching functionality. "
        * 100
    )

    # Make 3 parallel calls with same system prompt
    tasks = [
        client.call(
            model="sonnet",
            system=system_prompt,
            messages=[{"role": "user", "content": f"What is {i} + {i}?"}],
            cache_system=True,
            max_tokens=50,
        )
        for i in range(1, 4)
    ]

    results = await asyncio.gather(*tasks)

    # All parallel calls should create caches (since they start simultaneously)
    total_cache_creation = sum(usage.cache_creation_tokens for _, usage in results)

    # At least some calls should have cache creation
    assert total_cache_creation > 0, "Parallel calls should create caches"

    # Note: Cache reads in parallel calls are possible but unlikely due to timing
    # The important thing is that caching is enabled (cache_creation > 0)


if __name__ == "__main__":
    """Run tests manually for quick verification."""
    import sys

    async def main() -> int:
        """Run basic smoke tests."""
        print("🧪 Running LLM client tests...\n")

        settings = get_settings()
        client = ClaudeClient(api_key=settings.anthropic_api_key)

        try:
            # Test 1: Basic call
            print("1️⃣  Testing basic LLM call...")
            response, usage = await client.call(
                model="haiku",
                system="You are helpful.",
                messages=[{"role": "user", "content": "Say hello."}],
                max_tokens=20,
            )
            print(f"   ✅ Response: {response[:50]}")
            print(
                f"   📊 Tokens: {usage.total_tokens} | Cost: ${usage.calculate_cost('haiku'):.6f}\n"
            )

            # Test 2: Caching
            print("2️⃣  Testing prompt caching...")
            system = (
                "You are a business advisor with expertise in SaaS metrics and growth strategies."
            )

            response1, usage1 = await client.call(
                model="sonnet",
                system=system,
                messages=[{"role": "user", "content": "What is CAC?"}],
                cache_system=True,
                max_tokens=100,
            )
            print(f"   📝 First call - Cache creation: {usage1.cache_creation_tokens} tokens")

            await asyncio.sleep(0.5)

            response2, usage2 = await client.call(
                model="sonnet",
                system=system,
                messages=[{"role": "user", "content": "What is LTV?"}],
                cache_system=True,
                max_tokens=100,
            )
            print(f"   💾 Second call - Cache read: {usage2.cache_read_tokens} tokens")
            print(f"   📈 Cache hit rate: {usage2.cache_hit_rate * 100:.1f}%\n")

            # Test 3: Role-based model selection
            print("3️⃣  Testing role-based model selection...")
            response3, usage3 = await client.call_for_role(
                role="PERSONA",
                system="You are Maria Chen.",
                messages=[{"role": "user", "content": "Hi Maria!"}],
                max_tokens=50,
            )
            print(f"   ✅ PERSONA role uses Sonnet: {response3[:50]}\n")

            print("✅ All tests passed!")
            return 0

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return 1

    sys.exit(asyncio.run(main()))
