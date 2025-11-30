# test_stream_writer.py
"""Verify get_stream_writer() works for intra-node event streaming.

This test validates the approach from SUBGRAPH_DELIBERATION_PLAN.md Appendix B.
"""

import asyncio

import pytest
from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


class State(TypedDict):
    value: int
    results: list[int]


async def parallel_work_node(state: State) -> dict:
    """Simulate parallel work with per-item streaming."""
    writer = get_stream_writer()
    results = []

    async def do_work(item: int) -> int:
        # Emit start event
        writer(
            {
                "event_type": "work_started",
                "item": item,
            }
        )

        # Simulate work
        await asyncio.sleep(0.1 + item * 0.05)

        # Emit complete event
        writer(
            {
                "event_type": "work_complete",
                "item": item,
                "result": item * 2,
            }
        )

        return item * 2

    # Run in parallel
    tasks = [do_work(i) for i in range(3)]
    results = await asyncio.gather(*tasks)

    return {"results": list(results)}


# Build graph
def create_test_graph():
    graph = StateGraph(State)
    graph.add_node("parallel_work", parallel_work_node)
    graph.set_entry_point("parallel_work")
    graph.add_edge("parallel_work", END)
    return graph.compile()


@pytest.mark.asyncio
async def test_get_stream_writer_emits_custom_events():
    """Test that get_stream_writer() emits events during parallel execution."""
    compiled = create_test_graph()

    custom_events = []
    state_updates = []

    async for chunk in compiled.astream(
        {"value": 1, "results": []},
        stream_mode=["updates", "custom"],
    ):
        namespace, data = chunk

        if isinstance(data, dict) and "event_type" in data:
            custom_events.append(data)
        else:
            state_updates.append(data)

    # Verify custom events were emitted
    started = [e for e in custom_events if e["event_type"] == "work_started"]
    completed = [e for e in custom_events if e["event_type"] == "work_complete"]

    assert len(started) == 3, f"Should have 3 started events, got {len(started)}"
    assert len(completed) == 3, f"Should have 3 complete events, got {len(completed)}"

    # Verify state updates
    assert len(state_updates) > 0, "Should have state updates"


@pytest.mark.asyncio
async def test_events_stream_in_order():
    """Verify started events come before complete events for each item."""
    compiled = create_test_graph()

    events_with_order = []
    order = 0

    async for chunk in compiled.astream(
        {"value": 1, "results": []},
        stream_mode=["updates", "custom"],
    ):
        namespace, data = chunk

        if isinstance(data, dict) and "event_type" in data:
            events_with_order.append((order, data["event_type"], data.get("item")))
            order += 1

    # All started events should have lower order than their corresponding complete events
    for item in range(3):
        started_order = next(
            o for o, t, i in events_with_order if t == "work_started" and i == item
        )
        complete_order = next(
            o for o, t, i in events_with_order if t == "work_complete" and i == item
        )
        assert started_order < complete_order, f"Item {item}: started should come before complete"


if __name__ == "__main__":
    asyncio.run(test_get_stream_writer_emits_custom_events())
    print("✓ All tests passed!")
