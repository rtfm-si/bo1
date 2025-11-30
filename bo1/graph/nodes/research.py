"""Research node.

This module contains the research_node function that executes external
research requested by the facilitator or triggered proactively.
"""

import logging
from typing import Any, Literal

from bo1.graph.state import DeliberationGraphState

logger = logging.getLogger(__name__)


async def research_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Execute external research requested by facilitator or triggered proactively.

    Flow:
    1. Check for pending_research_queries from proactive detection
    2. If none, extract research query from facilitator decision
    3. Check semantic cache (PostgreSQL + Voyage embeddings)
    4. If cache miss: Brave Search (default) or Tavily (premium) + summarization
    5. Add research to deliberation context
    6. Continue to next round with enriched context

    Research Strategy:
    - Default: Brave Search + Haiku (~$0.025/query) for facts/statistics
    - Premium: Tavily ($0.001/query) for competitor/market/regulatory analysis

    Args:
        state: Current graph state

    Returns:
        State updates with research results
    """
    from bo1.agents.researcher import ResearcherAgent

    # PROACTIVE RESEARCH: Check for pending queries first
    pending_queries = state.get("pending_research_queries", [])

    if pending_queries:
        logger.info(f"[RESEARCH] Processing {len(pending_queries)} proactive research queries")

        # Execute all pending queries
        researcher = ResearcherAgent()

        # Convert pending queries to research format
        research_questions = []
        for query_data in pending_queries:
            research_questions.append(
                {
                    "question": query_data.get("question", ""),
                    "priority": query_data.get("priority", "MEDIUM"),
                    "reason": query_data.get("reason", ""),
                }
            )

        # Determine research depth based on query priorities
        has_high_priority = any(q.get("priority") == "HIGH" for q in pending_queries)
        research_depth: Literal["basic", "deep"] = "deep" if has_high_priority else "basic"

        # Perform research (uses cache if available)
        results = await researcher.research_questions(
            questions=research_questions,
            category="general",
            research_depth=research_depth,
        )

        # Add to state context
        research_results_obj = state.get("research_results", [])
        research_results = (
            list(research_results_obj) if isinstance(research_results_obj, list) else []
        )

        for result in results:
            research_results.append(
                {
                    "query": result["question"],
                    "summary": result["summary"],
                    "sources": result.get("sources", []),
                    "cached": result.get("cached", False),
                    "cost": result.get("cost", 0.0),
                    "round": state.get("round_number", 0),
                    "depth": research_depth,
                    "proactive": True,  # Mark as proactively triggered
                }
            )

        total_cost = sum(r.get("cost", 0.0) for r in results)
        logger.info(
            f"[RESEARCH] Proactive research complete - {len(results)} queries, "
            f"Total cost: ${total_cost:.4f}"
        )

        # Clear pending queries
        return {
            "research_results": research_results,
            "pending_research_queries": [],  # Clear after processing
            "facilitator_decision": None,  # Clear decision to prevent loops
            "current_node": "research",
            "sub_problem_index": state.get("sub_problem_index", 0),
        }

    # FALLBACK: Extract research query from facilitator decision
    facilitator_decision = state.get("facilitator_decision")

    if not facilitator_decision:
        logger.warning(
            "[RESEARCH] No facilitator decision found - marking as completed to prevent loop"
        )
        # Even without a decision, mark a placeholder to prevent re-triggering
        from bo1.llm.embeddings import generate_embedding

        # Use recent contributions to create a generic query marker
        recent_contributions = state.get("contributions", [])[-3:]
        fallback_query = "Research pattern detected but no specific query provided"
        if recent_contributions:
            # Use last contribution content as query marker
            fallback_query = f"Research needed based on: {recent_contributions[-1].content[:100]}"

        # Generate embedding for this fallback
        try:
            fallback_embedding = generate_embedding(fallback_query, input_type="query")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for fallback query: {e}")
            fallback_embedding = []

        # Mark as completed to prevent infinite loop
        completed_queries_obj = state.get("completed_research_queries", [])
        completed_queries = (
            list(completed_queries_obj) if isinstance(completed_queries_obj, list) else []
        )
        completed_queries.append(
            {
                "query": fallback_query,
                "embedding": fallback_embedding,
            }
        )

        return {
            "completed_research_queries": completed_queries,
            "facilitator_decision": None,
            "current_node": "research",
        }

    decision_reasoning = facilitator_decision.get("reasoning", "")

    if not decision_reasoning:
        logger.warning("[RESEARCH] Facilitator decision has no reasoning - using fallback")
        decision_reasoning = "General research requested"

    # Use the facilitator's reasoning as the research query
    research_query = f"Research needed: {decision_reasoning[:200]}"

    logger.info(f"[RESEARCH] Query extracted: {research_query[:80]}...")

    # Determine research depth based on keywords in reasoning
    deep_keywords = ["competitor", "market", "landscape", "regulation", "policy", "analysis"]
    facilitator_research_depth: Literal["basic", "deep"] = (
        "deep"
        if any(keyword in decision_reasoning.lower() for keyword in deep_keywords)
        else "basic"
    )

    logger.info(f"[RESEARCH] Depth: {facilitator_research_depth}")

    # P1-RESEARCH-2: Early cache check for cross-session deduplication
    # Check if similar research exists in cache before calling ResearcherAgent
    from bo1.llm.embeddings import generate_embedding
    from bo1.state.postgres_manager import find_similar_research

    try:
        query_embedding = generate_embedding(research_query, input_type="query")
        cached_results = find_similar_research(
            question_embedding=query_embedding,
            similarity_threshold=0.85,  # Same threshold as in-session dedup
            limit=1,
        )
        if cached_results:
            logger.info(
                f"[RESEARCH] Found similar cached research (similarity={cached_results[0].get('similarity', 0):.3f}). "
                f"ResearcherAgent will use this cached result."
            )
    except Exception as e:
        logger.debug(f"[RESEARCH] Cache pre-check failed (non-critical): {e}")

    # Perform research (uses cache if available)
    researcher = ResearcherAgent()
    results = await researcher.research_questions(
        questions=[
            {
                "question": research_query,
                "priority": "CRITICAL",  # Facilitator-requested = always critical
            }
        ],
        category="general",
        research_depth=facilitator_research_depth,
    )

    if not results:
        logger.warning("[RESEARCH] No results returned")
        return {"current_node": "research"}

    result = results[0]

    # Add to state context
    research_results_obj = state.get("research_results", [])
    # Ensure it's a list before appending
    if isinstance(research_results_obj, list):
        research_results = research_results_obj
    else:
        research_results = []

    research_results.append(
        {
            "query": research_query,
            "summary": result["summary"],
            "sources": result.get("sources", []),
            "cached": result.get("cached", False),
            "cost": result.get("cost", 0.0),
            "round": state.get("round_number", 0),
            "depth": facilitator_research_depth,
        }
    )

    logger.info(
        f"[RESEARCH] Complete - Cached: {result.get('cached', False)}, "
        f"Depth: {facilitator_research_depth}, Cost: ${result.get('cost', 0):.4f}"
    )

    # Mark this research query as completed to prevent infinite loops
    # Store query with embedding for semantic similarity matching
    from bo1.llm.embeddings import generate_embedding

    completed_queries_obj = state.get("completed_research_queries", [])
    completed_queries = (
        list(completed_queries_obj) if isinstance(completed_queries_obj, list) else []
    )

    # Generate embedding for this query (or extract from facilitator decision if available)
    try:
        query_embedding = generate_embedding(research_query, input_type="query")
    except Exception as e:
        logger.warning(f"Failed to generate embedding for research query: {e}")
        query_embedding = []  # Empty embedding for fallback

    # Check if this exact query already exists (avoid duplicates)
    query_exists = any(q.get("query") == research_query for q in completed_queries)

    if not query_exists:
        completed_queries.append(
            {
                "query": research_query,
                "embedding": query_embedding,
            }
        )
        logger.debug(f"Marked research query as completed: '{research_query[:50]}...'")

    return {
        "research_results": research_results,
        "completed_research_queries": completed_queries,  # Track completed research
        "facilitator_decision": None,  # Clear previous decision to prevent loops
        "current_node": "research",
        "sub_problem_index": state.get("sub_problem_index", 0),
    }
