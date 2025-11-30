"""Context collection and clarification nodes.

This module contains nodes for collecting and managing context:
- context_collection_node: Collects business context before deliberation
- clarification_node: Handles clarification questions during deliberation
"""

import logging
from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.state.postgres_manager import load_user_context

logger = logging.getLogger(__name__)


async def context_collection_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect business context and information gaps before deliberation.

    This node:
    1. Loads saved business context (if user_id exists)
    2. Injects context into problem.context dictionary
    3. Tracks cost in metrics.phase_costs["context_collection"] (data loading = $0)

    Note: Full context collection (prompts, information gaps, research) will be
    implemented in future iterations. Currently just loads saved context.

    Args:
        state: Current graph state (must have problem)

    Returns:
        Dictionary with state updates (problem with enriched context)
    """
    logger.info("context_collection_node: Starting context collection")

    problem = state.get("problem")
    if not problem:
        raise ValueError("context_collection_node called without problem")

    # Get user_id from state (optional)
    user_id = state.get("user_id")

    # Initialize metrics
    metrics = ensure_metrics(state)

    # Step 1: Load saved business context
    business_context = None
    if user_id:
        logger.info(f"Loading saved business context for user_id: {user_id}")
        try:
            saved_context = load_user_context(user_id)
            if saved_context:
                logger.info("Found saved business context")
                business_context = saved_context

                # Inject business context into problem.context (append to string)
                # Format business context as a readable addition
                context_lines = [
                    "\n\n## Business Context",
                ]
                if saved_context.get("business_model"):
                    context_lines.append(f"- Business Model: {saved_context['business_model']}")
                if saved_context.get("target_market"):
                    context_lines.append(f"- Target Market: {saved_context['target_market']}")
                if saved_context.get("revenue"):
                    context_lines.append(f"- Revenue: {saved_context['revenue']}")
                if saved_context.get("customers"):
                    context_lines.append(f"- Customers: {saved_context['customers']}")
                if saved_context.get("growth_rate"):
                    context_lines.append(f"- Growth Rate: {saved_context['growth_rate']}")

                # Append to existing context
                problem.context = problem.context + "\n".join(context_lines)
                logger.info("Injected business context into problem.context")
        except Exception as e:
            logger.warning(f"Failed to load business context: {e}")

    # Track cost in metrics (data loading = $0, no LLM calls)
    track_phase_cost(metrics, "context_collection", None)

    logger.info("context_collection_node: Complete")

    return {
        "problem": problem,
        "business_context": business_context,
        "metrics": metrics,
        "current_node": "context_collection",
    }


async def clarification_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Handle clarification questions from facilitator during deliberation.

    This node:
    1. Displays clarification question from facilitator
    2. Provides options: Answer now / Pause session / Skip
    3. If answer: Injects into context, continues
    4. If pause: Sets should_stop=True, saves pending_clarification
    5. If skip: Logs skip, continues with warning

    Args:
        state: Current graph state (must have pending_clarification)

    Returns:
        Dictionary with state updates (context with answer, or paused state)
    """
    logger.info("clarification_node: Handling clarification request")

    pending_clarification = state.get("pending_clarification")

    if not pending_clarification:
        logger.warning("clarification_node called without pending_clarification")
        return {
            "current_node": "clarification",
        }

    # For now, we'll implement a simple console-based clarification prompt
    # Full implementation will include web API support for async clarification

    from bo1.ui.console import Console

    console = Console()

    question = pending_clarification.get("question", "Unknown question")
    reason = pending_clarification.get("reason", "")

    console.print("\n[bold yellow]Clarification Needed[/bold yellow]")
    console.print(f"Question: {question}")
    if reason:
        console.print(f"Reason: {reason}")

    console.print("\nOptions:")
    console.print("1. Answer now")
    console.print("2. Pause session (resume later)")
    console.print("3. Skip question")

    choice = console.input("\nYour choice (1-3): ").strip()

    if choice == "1":
        # Collect answer
        answer = console.input("\nYour answer: ").strip()

        # Store answer in pending_clarification for later injection
        answered_clarification = pending_clarification.copy()
        answered_clarification["answer"] = answer
        answered_clarification["answered"] = True

        logger.info(f"Clarification answered: {question[:50]}...")

        # Update business_context with clarification
        business_context = state.get("business_context") or {}
        if not isinstance(business_context, dict):
            business_context = {}
        clarifications = business_context.get("clarifications", {})
        clarifications[question] = answer
        business_context["clarifications"] = clarifications

        return {
            "business_context": business_context,
            "pending_clarification": None,
            "current_node": "clarification",
        }

    elif choice == "2":
        # Pause session
        logger.info("User requested session pause for clarification")

        return {
            "should_stop": True,
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    else:
        # Skip question
        logger.info(f"User skipped clarification: {question[:50]}...")

        return {
            "pending_clarification": None,
            "current_node": "clarification",
        }
