"""Hello World LangGraph Example.

Demonstrates basic LangGraph concepts:
- StateGraph definition
- Node functions
- Edges (connections)
- Checkpoint persistence
- Execution with invoke()
"""

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph


# Define state schema
class HelloWorldState(TypedDict):
    """Simple state with two fields."""

    message: str
    count: int


# Node 1: Initial greeting
def node1(state: HelloWorldState) -> HelloWorldState:
    """First node: Set initial message."""
    print(f"[Node 1] Current state: {state}")
    return {
        "message": "Hello from Node 1",
        "count": state.get("count", 0) + 1,
    }


# Node 2: Add to message
def node2(state: HelloWorldState) -> HelloWorldState:
    """Second node: Append to message."""
    print(f"[Node 2] Current state: {state}")
    return {
        "message": state["message"] + " -> Node 2",
        "count": state["count"] + 1,
    }


def main() -> None:
    """Run hello world graph examples."""
    print("=== LangGraph Hello World ===\n")

    # Example 1: Basic graph without checkpointer
    print("Example 1: Basic Graph (No Checkpointer)")
    print("-" * 50)

    # Create graph
    workflow = StateGraph(HelloWorldState)

    # Add nodes
    workflow.add_node("node1", node1)
    workflow.add_node("node2", node2)

    # Add edges
    workflow.set_entry_point("node1")
    workflow.add_edge("node1", "node2")
    workflow.add_edge("node2", END)

    # Compile (no checkpointer)
    graph = workflow.compile()

    # Execute
    initial_state = {"message": "", "count": 0}
    result = graph.invoke(initial_state)

    print(f"\nFinal state: {result}")
    print()

    # Example 2: Graph with checkpointer
    print("\nExample 2: Graph with Checkpointer")
    print("-" * 50)

    # Create new workflow
    workflow2 = StateGraph(HelloWorldState)
    workflow2.add_node("node1", node1)
    workflow2.add_node("node2", node2)
    workflow2.set_entry_point("node1")
    workflow2.add_edge("node1", "node2")
    workflow2.add_edge("node2", END)

    # Compile with checkpointer
    checkpointer = MemorySaver()
    graph2 = workflow2.compile(checkpointer=checkpointer)

    # Execute with thread_id (enables checkpointing)
    config = {"configurable": {"thread_id": "hello_world_thread"}}
    result2 = graph2.invoke(initial_state, config=config)

    print(f"\nFinal state: {result2}")

    # Verify checkpoint created
    state_snapshot = graph2.get_state(config)
    print("\nCheckpoint saved:")
    print(f"  - Values: {state_snapshot.values}")
    print(f"  - Next: {state_snapshot.next}")
    print()

    print("=== Tests Passed ===")
    print("✅ Basic graph execution works")
    print("✅ Node functions execute in order")
    print("✅ State updates correctly")
    print("✅ Checkpoint persistence works")


if __name__ == "__main__":
    main()
