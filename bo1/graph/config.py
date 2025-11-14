"""LangGraph configuration and graph construction.

This module defines how to build the deliberation graph with nodes, edges,
and checkpointing configuration.
"""

import logging
import os
from typing import Any

from langgraph.checkpoint.redis import RedisSaver
from langgraph.graph import END, StateGraph

from bo1.graph.nodes import (
    decompose_node,
    initial_round_node,
    select_personas_node,
)
from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT
from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


def create_deliberation_graph(
    checkpointer: RedisSaver | None | bool = None,
) -> Any:  # Returns CompiledStateGraph but type not exported
    """Create and compile the deliberation graph.

    This creates a linear graph for Day 27 (Week 4):
    decompose -> select_personas -> initial_round -> END

    Week 5 will add:
    - facilitator_decide node
    - persona_contribute node (multi-round loop)
    - moderator_intervene node
    - vote node
    - synthesize node

    Args:
        checkpointer: Optional Redis checkpointer for pause/resume.
                     - None: Auto-create from REDIS_URL env var
                     - False: Disable checkpointing (for tests)
                     - RedisSaver: Use provided checkpointer

    Returns:
        Compiled LangGraph ready for execution

    Example:
        >>> graph = create_deliberation_graph()
        >>> result = await graph.ainvoke(initial_state, config={"thread_id": "123"})
    """
    logger.info("Creating deliberation graph (Day 27: Linear flow)")

    # Handle checkpointer configuration
    actual_checkpointer: RedisSaver | None = None
    if checkpointer is None:
        # Auto-create from environment
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        actual_checkpointer = RedisSaver(redis_url=redis_url)
        logger.info(f"Created Redis checkpointer: {redis_url}")
    elif checkpointer is False:
        # Explicitly disabled (for tests)
        actual_checkpointer = None
        logger.info("Checkpointing disabled")
    else:
        # Use provided checkpointer
        actual_checkpointer = checkpointer
        logger.info("Using provided checkpointer")

    # Initialize state graph
    workflow = StateGraph(DeliberationGraphState)

    # Add nodes
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("select_personas", select_personas_node)
    workflow.add_node("initial_round", initial_round_node)

    # Add edges (linear flow for now)
    # decompose -> select_personas
    workflow.add_edge("decompose", "select_personas")

    # select_personas -> initial_round
    workflow.add_edge("select_personas", "initial_round")

    # initial_round -> END (for now)
    # Week 5 will add conditional edge to facilitator_decide
    workflow.add_edge("initial_round", END)

    # Set entry point
    workflow.set_entry_point("decompose")

    # Compile graph
    graph = workflow.compile(checkpointer=actual_checkpointer)

    logger.info(
        f"Graph compiled successfully (recursion_limit will be {DELIBERATION_RECURSION_LIMIT} when invoked)"
    )

    return graph
