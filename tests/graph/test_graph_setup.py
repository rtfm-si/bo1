"""
Tests for LangGraph setup and basic functionality.

Validates:
- LangGraph can be imported
- Basic graph creation works
- Checkpoint persistence works
- Module structure is correct
"""

from typing import TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph


class SimpleState(TypedDict):
    """Simple state for testing."""

    value: int


def increment_node(state: SimpleState) -> SimpleState:
    """Test node that increments value."""
    return {"value": state["value"] + 1}


def test_langgraph_import():
    """Test that LangGraph can be imported."""
    import langgraph

    assert langgraph is not None


def test_redis_saver_import():
    """Test that RedisSaver can be imported."""
    from langgraph.checkpoint.redis import RedisSaver

    assert RedisSaver is not None


def test_basic_graph_creation():
    """Test creating a basic StateGraph."""
    workflow = StateGraph(SimpleState)
    workflow.add_node("increment", increment_node)
    workflow.set_entry_point("increment")
    workflow.add_edge("increment", END)

    graph = workflow.compile()

    # Execute
    result = graph.invoke({"value": 0})
    assert result["value"] == 1


def test_graph_with_checkpointer():
    """Test graph execution with checkpointer."""
    workflow = StateGraph(SimpleState)
    workflow.add_node("increment", increment_node)
    workflow.set_entry_point("increment")
    workflow.add_edge("increment", END)

    # Compile with checkpointer
    checkpointer = MemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    # Execute with thread_id
    config = {"configurable": {"thread_id": "test-thread"}}
    result = graph.invoke({"value": 0}, config=config)

    assert result["value"] == 1

    # Verify checkpoint created
    snapshot = graph.get_state(config)
    assert snapshot.values["value"] == 1
    assert snapshot.next == ()


def test_multiple_nodes():
    """Test graph with multiple nodes."""
    workflow = StateGraph(SimpleState)

    # Add multiple nodes
    workflow.add_node("node1", increment_node)
    workflow.add_node("node2", increment_node)
    workflow.add_node("node3", increment_node)

    # Connect nodes
    workflow.set_entry_point("node1")
    workflow.add_edge("node1", "node2")
    workflow.add_edge("node2", "node3")
    workflow.add_edge("node3", END)

    graph = workflow.compile()

    # Execute
    result = graph.invoke({"value": 0})
    assert result["value"] == 3  # Incremented 3 times


def test_conditional_routing():
    """Test conditional edges."""

    def route_value(state: SimpleState) -> str:
        """Route based on value."""
        if state["value"] < 5:
            return "increment"
        else:
            return "finish"

    workflow = StateGraph(SimpleState)
    workflow.add_node("increment", increment_node)
    workflow.set_entry_point("increment")

    # Add conditional routing (loop until value >= 5)
    workflow.add_conditional_edges(
        "increment", route_value, {"increment": "increment", "finish": END}
    )

    graph = workflow.compile()

    # Execute
    result = graph.invoke({"value": 0})
    assert result["value"] == 5  # Loops until 5


def test_recursion_limit():
    """Test that recursion limit prevents infinite loops."""

    def always_increment(state: SimpleState) -> SimpleState:
        """Increments forever without stop condition."""
        return {"value": state["value"] + 1}

    def always_loop(state: SimpleState) -> str:
        """Always returns 'loop' - creates infinite loop."""
        return "loop"

    workflow = StateGraph(SimpleState)
    workflow.add_node("increment", always_increment)
    workflow.set_entry_point("increment")
    workflow.add_conditional_edges(
        "increment",
        always_loop,
        {"loop": "increment"},  # Infinite loop!
    )

    # Compile graph
    # Note: LangGraph has built-in recursion limit (default ~25)
    # We'll test that it prevents infinite loops
    graph = workflow.compile()

    # Should raise RecursionError or GraphRecursionError
    with pytest.raises((RecursionError, Exception)):
        graph.invoke({"value": 0})


def test_module_structure():
    """Test that graph module structure exists."""
    # These imports should work if structure is correct
    from bo1 import graph

    assert graph is not None

    # Check submodules exist


@pytest.mark.asyncio
async def test_async_graph_execution():
    """Test async graph execution."""

    async def async_increment_node(state: SimpleState) -> SimpleState:
        """Async version of increment node."""
        return {"value": state["value"] + 1}

    workflow = StateGraph(SimpleState)
    workflow.add_node("increment", async_increment_node)
    workflow.set_entry_point("increment")
    workflow.add_edge("increment", END)

    graph = workflow.compile()

    # Execute asynchronously
    result = await graph.ainvoke({"value": 0})
    assert result["value"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
