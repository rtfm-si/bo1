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
    clarification_node,  # Pre-meeting context collection
    context_collection_node,
    decompose_node,
    initial_round_node,
    research_node,  # Mid-meeting automated research (RESTORED)
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
        redis_password = os.getenv("REDIS_PASSWORD", "")

        # Build Redis URL with optional password authentication
        if redis_password:
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # Configure TTL: 7 days (604800 seconds) for checkpoint expiration
        # This prevents Redis from growing indefinitely with old checkpoints
        ttl_seconds = int(os.getenv("CHECKPOINT_TTL_SECONDS", "604800"))

        # Create AsyncRedisSaver - let it create its own Redis client
        # AsyncRedisSaver handles decode_responses internally
        actual_checkpointer = AsyncRedisSaver(redis_url)
        # Log without exposing password
        auth_status = " (with auth)" if redis_password else ""
        logger.info(
            f"Created Async Redis checkpointer: {redis_host}:{redis_port}/{redis_db}{auth_status} (TTL: {ttl_seconds}s)"
        )
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
    from bo1.feature_flags import ENABLE_PARALLEL_SUBPROBLEMS

    # TARGETED MODERATOR: Restored for premature consensus detection (rounds 1-2 only)
    from bo1.graph.nodes import (
        facilitator_decide_node,
        meta_synthesize_node,
        moderator_intervene_node,  # RESTORED: Premature consensus detection only
        next_subproblem_node,
        parallel_round_node,
        synthesize_node,
        vote_node,
    )

    # PARALLEL SUB-PROBLEMS: Conditional import
    if ENABLE_PARALLEL_SUBPROBLEMS:
        from bo1.graph.nodes import analyze_dependencies_node, parallel_subproblems_node

    from bo1.graph.routers import (
        route_after_synthesis,
        route_clarification,
        route_convergence_check,
        route_facilitator_decision,
        route_subproblem_execution,
    )
    from bo1.graph.safety.loop_prevention import (
        check_convergence_node,
        cost_guard_node,
        route_cost_guard,
    )

    # Initialize state graph
    workflow = StateGraph(DeliberationGraphState)

    # Add nodes
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("context_collection", context_collection_node)
    workflow.add_node("select_personas", select_personas_node)
    workflow.add_node("initial_round", initial_round_node)
    workflow.add_node("facilitator_decide", facilitator_decide_node)
    workflow.add_node("parallel_round", parallel_round_node)  # Multi-expert parallel rounds
    workflow.add_node(
        "moderator_intervene", moderator_intervene_node
    )  # RESTORED: Premature consensus detection
    workflow.add_node("research", research_node)  # Mid-meeting automated research (RESTORED)
    workflow.add_node("check_convergence", check_convergence_node)  # Day 24
    workflow.add_node("cost_guard", cost_guard_node)  # Cost budget check
    workflow.add_node("vote", vote_node)  # Day 31
    workflow.add_node("synthesize", synthesize_node)  # Day 31
    workflow.add_node("next_subproblem", next_subproblem_node)  # Day 36.5
    workflow.add_node("meta_synthesis", meta_synthesize_node)  # Day 36.5
    workflow.add_node("clarification", clarification_node)  # Day 37

    # Add edges - Linear setup phase
    # decompose -> analyze_dependencies (if parallel sub-problems enabled, else context_collection)
    if ENABLE_PARALLEL_SUBPROBLEMS:
        workflow.add_node("analyze_dependencies", analyze_dependencies_node)
        workflow.add_node("parallel_subproblems", parallel_subproblems_node)
        workflow.add_edge("decompose", "analyze_dependencies")

        # analyze_dependencies -> (parallel_subproblems | context_collection)
        workflow.add_conditional_edges(
            "analyze_dependencies",
            route_subproblem_execution,
            {
                "parallel_subproblems": "parallel_subproblems",
                "context_collection": "context_collection",
            },
        )

        # parallel_subproblems -> meta_synthesis
        workflow.add_edge("parallel_subproblems", "meta_synthesis")
    else:
        # Legacy: decompose -> context_collection (Day 37)
        workflow.add_edge("decompose", "context_collection")

    # context_collection -> select_personas (Day 37) - only used in sequential mode
    workflow.add_edge("context_collection", "select_personas")

    # select_personas -> initial_round
    workflow.add_edge("select_personas", "initial_round")

    # initial_round -> facilitator_decide (Week 5 Day 29)
    workflow.add_edge("initial_round", "facilitator_decide")

    # Add conditional edges - Multi-round deliberation loop (Week 5 Day 30-31)
    # facilitator_decide -> (continue/vote/research/moderator/clarify)
    workflow.add_conditional_edges(
        "facilitator_decide",
        route_facilitator_decision,
        {
            "persona_contribute": "parallel_round",  # Always use parallel multi-expert rounds
            "vote": "vote",
            "moderator_intervene": "moderator_intervene",  # RESTORED: Premature consensus detection
            "research": "research",  # Mid-meeting automated research (RESTORED)
            "clarification": "clarification",  # Request clarification from user
            "END": END,
        },
    )

    # clarification -> (parallel_round if answered/skipped, END if paused)
    workflow.add_conditional_edges(
        "clarification",
        route_clarification,
        {
            "persona_contribute": "parallel_round",  # Always use parallel multi-expert rounds
            "END": END,
        },
    )

    # research -> parallel_round (continue deliberation with research results)
    workflow.add_edge("research", "parallel_round")

    # parallel_round -> cost_guard (check budget before convergence)
    workflow.add_edge("parallel_round", "cost_guard")

    # moderator_intervene -> cost_guard (RESTORED: check budget after moderator intervention)
    workflow.add_edge("moderator_intervene", "cost_guard")

    # cost_guard -> (check_convergence if OK, vote if budget exceeded)
    workflow.add_conditional_edges(
        "cost_guard",
        route_cost_guard,
        {
            "continue": "check_convergence",  # Budget OK, check convergence
            "force_synthesis": "vote",  # Budget exceeded, skip to voting
        },
    )

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
