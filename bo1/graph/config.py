"""LangGraph configuration and graph construction.

This module defines how to build the deliberation graph with nodes, edges,
and checkpointing configuration.
"""

import logging
import os
from typing import Any

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, StateGraph

from bo1.graph.nodes import (
    clarification_node,
    context_collection_node,
    decompose_node,
    initial_round_node,
    research_node,
    select_personas_node,
)
from bo1.graph.safety.loop_prevention import DELIBERATION_RECURSION_LIMIT
from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


def create_deliberation_graph(
    checkpointer: Any = None,  # RedisSaver, MemorySaver, or other BaseCheckpointSaver
) -> Any:  # Returns CompiledStateGraph but type not exported
    """Create and compile the deliberation graph.

    This creates a complete graph with multi-round deliberation loop:
    decompose -> select_personas -> initial_round -> facilitator_decide ->
    (persona_contribute | moderator_intervene) -> check_convergence -> (loop or END)

    Args:
        checkpointer: Optional checkpointer for pause/resume.
                     - None: Auto-create RedisSaver from REDIS_URL env var
                     - False: Disable checkpointing (for tests)
                     - Any BaseCheckpointSaver: Use provided checkpointer (RedisSaver, MemorySaver, etc.)

    Returns:
        Compiled LangGraph ready for execution

    Example:
        >>> graph = create_deliberation_graph()
        >>> result = await graph.ainvoke(initial_state, config={"thread_id": "123"})
    """
    logger.info("Creating deliberation graph with multi-round loop")

    # Handle checkpointer configuration
    actual_checkpointer: Any = None  # RedisSaver, MemorySaver, or other checkpointer
    if checkpointer is None:
        # Auto-create from environment
        # Construct URL from individual env vars to support Docker environments
        # where REDIS_HOST may differ from localhost
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure TTL: 7 days (604800 seconds) for checkpoint expiration
        # This prevents Redis from growing indefinitely with old checkpoints
        ttl_seconds = int(os.getenv("CHECKPOINT_TTL_SECONDS", "604800"))

        # Create AsyncRedisSaver - let it create its own Redis client
        # AsyncRedisSaver handles decode_responses internally
        actual_checkpointer = AsyncRedisSaver(redis_url)
        logger.info(f"Created Async Redis checkpointer: {redis_url} (TTL: {ttl_seconds}s)")
    elif checkpointer is False:
        # Explicitly disabled (for tests)
        actual_checkpointer = None
        logger.info("Checkpointing disabled")
    else:
        # Use provided checkpointer (any BaseCheckpointSaver implementation)
        # This accepts RedisSaver, MemorySaver, or any other compatible checkpointer
        actual_checkpointer = checkpointer
        logger.info(f"Using provided checkpointer: {type(checkpointer).__name__}")

    # Import nodes and routers
    from bo1.feature_flags import ENABLE_PARALLEL_ROUNDS
    from bo1.graph.nodes import (
        facilitator_decide_node,
        meta_synthesize_node,
        moderator_intervene_node,
        next_subproblem_node,
        persona_contribute_node,
        synthesize_node,
        vote_node,
    )

    # NEW PARALLEL ARCHITECTURE: Conditional import
    if ENABLE_PARALLEL_ROUNDS:
        from bo1.graph.nodes import parallel_round_node
    from bo1.graph.routers import (
        route_after_synthesis,
        route_clarification,
        route_convergence_check,
        route_facilitator_decision,
    )
    from bo1.graph.safety.loop_prevention import check_convergence_node

    # Initialize state graph
    workflow = StateGraph(DeliberationGraphState)

    # Add nodes
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("context_collection", context_collection_node)  # Day 37
    workflow.add_node("select_personas", select_personas_node)
    workflow.add_node("initial_round", initial_round_node)
    workflow.add_node("facilitator_decide", facilitator_decide_node)  # Day 29

    # NEW PARALLEL ARCHITECTURE: Conditional node addition (Day 38)
    if ENABLE_PARALLEL_ROUNDS:
        workflow.add_node("parallel_round", parallel_round_node)  # Multi-expert parallel
        logger.info("Using PARALLEL multi-expert architecture")
    else:
        workflow.add_node("persona_contribute", persona_contribute_node)  # Legacy serial
        logger.info("Using LEGACY serial architecture")

    workflow.add_node("moderator_intervene", moderator_intervene_node)  # Day 30
    workflow.add_node("research", research_node)  # Week 6: External research
    workflow.add_node("check_convergence", check_convergence_node)  # Day 24
    workflow.add_node("vote", vote_node)  # Day 31
    workflow.add_node("synthesize", synthesize_node)  # Day 31
    workflow.add_node("next_subproblem", next_subproblem_node)  # Day 36.5
    workflow.add_node("meta_synthesis", meta_synthesize_node)  # Day 36.5
    workflow.add_node("clarification", clarification_node)  # Day 37

    # Add edges - Linear setup phase
    # decompose -> context_collection (Day 37)
    workflow.add_edge("decompose", "context_collection")

    # context_collection -> select_personas (Day 37)
    workflow.add_edge("context_collection", "select_personas")

    # select_personas -> initial_round
    workflow.add_edge("select_personas", "initial_round")

    # initial_round -> facilitator_decide (Week 5 Day 29)
    workflow.add_edge("initial_round", "facilitator_decide")

    # Add conditional edges - Multi-round deliberation loop (Week 5 Day 30-31)
    # facilitator_decide -> (continue/vote/moderator/research/clarify)
    # NEW PARALLEL ARCHITECTURE: Route to parallel_round or persona_contribute based on feature flag
    contribute_node_name = "parallel_round" if ENABLE_PARALLEL_ROUNDS else "persona_contribute"

    workflow.add_conditional_edges(
        "facilitator_decide",
        route_facilitator_decision,
        {
            "persona_contribute": contribute_node_name,  # Routes to parallel_round OR persona_contribute
            "moderator_intervene": "moderator_intervene",
            "vote": "vote",  # Day 31: Route to vote node
            "research": "research",  # Week 6: Route to research node
            "clarification": "clarification",  # Day 37: Route to clarification node
            "END": END,
        },
    )

    # clarification -> (persona_contribute/parallel_round if answered/skipped, END if paused) (Day 37)
    # NEW PARALLEL ARCHITECTURE: Route to appropriate node based on feature flag
    workflow.add_conditional_edges(
        "clarification",
        route_clarification,
        {
            "persona_contribute": contribute_node_name,  # Routes to parallel_round OR persona_contribute
            "END": END,
        },
    )

    # research -> facilitator_decide (Week 6: Let facilitator decide next action after research)
    # Previously routed directly to persona_contribute, which caused crashes because
    # facilitator_decision still had action="research" with no next_speaker
    workflow.add_edge("research", "facilitator_decide")

    # NEW PARALLEL ARCHITECTURE: Conditional edges based on feature flag
    if ENABLE_PARALLEL_ROUNDS:
        # parallel_round -> check_convergence
        workflow.add_edge("parallel_round", "check_convergence")
    else:
        # persona_contribute -> check_convergence (legacy)
        workflow.add_edge("persona_contribute", "check_convergence")

    # moderator_intervene -> check_convergence
    workflow.add_edge("moderator_intervene", "check_convergence")

    # check_convergence -> (facilitator_decide if continue, vote if stop)
    workflow.add_conditional_edges(
        "check_convergence",
        route_convergence_check,
        {
            "facilitator_decide": "facilitator_decide",  # Loop back for next round
            "vote": "vote",  # Day 31: Route to voting when stopped
        },
    )

    # vote -> synthesize (Day 31)
    workflow.add_edge("vote", "synthesize")

    # synthesize -> (next_subproblem | meta_synthesis | END) (Day 36.5)
    workflow.add_conditional_edges(
        "synthesize",
        route_after_synthesis,
        {
            "next_subproblem": "next_subproblem",
            "meta_synthesis": "meta_synthesis",
            "END": END,
        },
    )

    # next_subproblem -> select_personas (loop back for next sub-problem) (Day 36.5)
    workflow.add_edge("next_subproblem", "select_personas")

    # meta_synthesis -> END (Day 36.5)
    workflow.add_edge("meta_synthesis", END)

    # Set entry point
    workflow.set_entry_point("decompose")

    # Compile graph
    # Note: recursion_limit is set in the config during execution, not compilation
    graph = workflow.compile(
        checkpointer=actual_checkpointer,
    )

    logger.info(
        f"Graph compiled successfully with multi-round loop "
        f"(recursion_limit={DELIBERATION_RECURSION_LIMIT})"
    )

    return graph
