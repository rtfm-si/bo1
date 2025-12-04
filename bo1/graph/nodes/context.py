"""Context collection and clarification nodes.

This module contains nodes for collecting and managing context:
- context_collection_node: Collects business context before deliberation
- clarification_node: Handles clarification questions during deliberation
"""

import logging
from datetime import UTC, datetime
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

                # ISSUE #4 FIX: Include saved clarifications from previous meetings
                clarifications = saved_context.get("clarifications", {})
                if clarifications:
                    context_lines.append("\n### Previous Clarifications")
                    for question, answer_data in clarifications.items():
                        if isinstance(answer_data, dict):
                            answer = answer_data.get("answer", "N/A")
                        else:
                            answer = str(answer_data)
                        context_lines.append(f"- Q: {question}")
                        context_lines.append(f"  A: {answer}")
                    logger.info(
                        f"Injected {len(clarifications)} previous clarifications into context"
                    )

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
    1. In API mode (headless): Auto-pause and wait for user to answer via API
    2. In CLI mode: Interactive prompt for answer/pause/skip

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

    question = pending_clarification.get("question", "Unknown question")
    reason = pending_clarification.get("reason", "")

    # Check if we're running in headless mode (no stdin available)
    # In API/server mode, stdin is not connected, so we auto-pause
    import os
    import sys

    is_headless = not sys.stdin.isatty() or os.environ.get("BO1_HEADLESS", "").lower() in (
        "1",
        "true",
    )

    if is_headless:
        # API mode: Auto-pause session, user answers via API
        logger.info(
            f"clarification_node: Headless mode detected, pausing for API-based answer. "
            f"Question: {question[:50]}..."
        )
        return {
            "should_stop": True,
            "stop_reason": "clarification_needed",
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    # CLI mode: Interactive prompt
    from bo1.ui.console import Console

    console = Console()

    console.print("\n[bold yellow]Clarification Needed[/bold yellow]")
    console.print(f"Question: {question}")
    if reason:
        console.print(f"Reason: {reason}")

    console.print("\nOptions:")
    console.print("1. Answer now")
    console.print("2. Pause session (resume later)")
    console.print("3. Skip question")

    try:
        choice = console.input("\nYour choice (1-3): ").strip()
    except EOFError:
        # Fallback: If stdin fails, pause the session
        logger.warning("clarification_node: EOFError on input, pausing session")
        return {
            "should_stop": True,
            "stop_reason": "clarification_needed",
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    if choice == "1":
        # Collect answer
        try:
            answer = console.input("\nYour answer: ").strip()
        except EOFError:
            logger.warning("clarification_node: EOFError on answer input, pausing session")
            return {
                "should_stop": True,
                "stop_reason": "clarification_needed",
                "pending_clarification": pending_clarification,
                "current_node": "clarification",
            }

        # Store answer in pending_clarification for later injection
        answered_clarification = pending_clarification.copy()
        answered_clarification["answer"] = answer
        answered_clarification["answered"] = True

        logger.info(f"Clarification answered: {question[:50]}...")

        # Update business_context with clarification (with timestamp per TODO.md)
        business_context = state.get("business_context") or {}
        if not isinstance(business_context, dict):
            business_context = {}
        clarifications = business_context.get("clarifications", {})
        # Store with timestamp and round number
        clarifications[question] = {
            "answer": answer,
            "timestamp": datetime.now(UTC).isoformat(),
            "round_number": state.get("round_number", 0),
        }
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
            "stop_reason": "clarification_needed",
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
