#!/usr/bin/env python3
"""Test script to verify prompt caching is working."""

import asyncio

from bo1.llm.client import ClaudeClient


async def test_caching():
    """Test that prompt caching works with the ClaudeClient."""
    client = ClaudeClient()

    # Create a long system prompt (>1024 tokens for Sonnet)
    system_prompt = "This is a test system prompt for caching. " * 100

    print(f"System prompt: ~{len(system_prompt)} chars (~{len(system_prompt) // 4} tokens)\n")

    print("=" * 70)
    print("FIRST CALL (should create cache)")
    print("=" * 70)

    response1, usage1 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "What is 2+2?"}],
        cache_system=True,
        max_tokens=100,
    )

    print(f"Input tokens:         {usage1.input_tokens:,}")
    print(f"Cache creation:       {usage1.cache_creation_tokens:,}")
    print(f"Cache read:           {usage1.cache_read_tokens:,}")
    print(f"Output tokens:        {usage1.output_tokens:,}")
    print(f"Cost:                 ${usage1.calculate_cost('sonnet'):.6f}")

    print("\n" + "=" * 70)
    print("SECOND CALL (should hit cache)")
    print("=" * 70)

    response2, usage2 = await client.call(
        model="sonnet",
        system=system_prompt,
        messages=[{"role": "user", "content": "What is 3+3?"}],
        cache_system=True,
        max_tokens=100,
    )

    print(f"Input tokens:         {usage2.input_tokens:,}")
    print(f"Cache creation:       {usage2.cache_creation_tokens:,}")
    print(f"Cache read:           {usage2.cache_read_tokens:,}")
    print(f"Output tokens:        {usage2.output_tokens:,}")
    print(f"Cost:                 ${usage2.calculate_cost('sonnet'):.6f}")

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    # Check first call created cache
    if usage1.cache_creation_tokens > 0:
        print(f"✅ First call created cache: {usage1.cache_creation_tokens:,} tokens")
    else:
        print("❌ First call did NOT create cache")
        return False

    # Check second call hit cache
    if usage2.cache_read_tokens > 0:
        total_input = usage2.input_tokens + usage2.cache_read_tokens
        hit_rate = (usage2.cache_read_tokens / total_input) * 100

        # Calculate savings
        cost_without_cache = (usage2.cache_read_tokens / 1_000_000) * 3.00  # Regular input cost
        cost_with_cache = (usage2.cache_read_tokens / 1_000_000) * 0.30  # Cache read cost
        savings = cost_without_cache - cost_with_cache
        savings_pct = (savings / cost_without_cache) * 100

        print(f"✅ Second call hit cache: {usage2.cache_read_tokens:,} tokens ({hit_rate:.1f}%)")
        print(f"💰 Cache savings: ${savings:.6f} ({savings_pct:.1f}% reduction)")
        return True
    else:
        print("❌ Second call did NOT hit cache")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_caching())
    exit(0 if success else 1)
